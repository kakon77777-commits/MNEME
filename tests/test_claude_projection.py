from __future__ import annotations

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Barrier, BrokenBarrierError, Event, Lock

import pytest

from mneme.adapters.claude import ClaudeGlobalProjectionResult
from mneme.claude_contracts import (
    CLAUDE_GLOBAL_NONCLAIMS,
    ClaudeGlobalProjectionManifest,
    LocalManualWriteAuthorization,
)
from mneme.claude_projection import (
    ClaudeProjectionPublisher,
    PreparedClaudePublication,
)
from mneme.errors import (
    ClaudeContractError,
    ClaudePathBoundaryError,
    InjectedCrash,
    ManualAuthorityError,
    StaleTargetError,
    StoreConflictError,
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def projection(content: bytes = b"# MNEME Projection\n\nSynthetic global memory.\n"):
    manifest = ClaudeGlobalProjectionManifest.sealed(
        {
            "manifest_version": "mneme.claude-global-projection-manifest/0.1",
            "projection_ref": "projection:synthetic:publisher",
            "request_ref": "request:synthetic:publisher",
            "request_digest": "a" * 64,
            "source_head": "b" * 64,
            "route_id": "route://global/tier0",
            "byte_budget": 16000,
            "content_bytes": len(content),
            "content_sha256": sha256(content),
            "included_record_ids": ["record:synthetic:core"],
            "omitted": [],
            "required_record_ids": ["record:synthetic:core"],
            "generator_version": "mneme.claude-projection/0.1",
            "not_claimed": list(CLAUDE_GLOBAL_NONCLAIMS),
        }
    )
    return ClaudeGlobalProjectionResult(content=content, manifest=manifest)


def authorization(*, status: str = "active") -> LocalManualWriteAuthorization:
    return LocalManualWriteAuthorization.sealed(
        {
            "authorization_version": "mneme.local-manual-write-authorization/0.1",
            "authorization_id": "authorization:synthetic:publisher",
            "principal_ref": "principal:neo.k",
            "transaction_ref": "transaction:synthetic:publisher",
            "transaction_digest": "c" * 64,
            "expected_source_head": "GENESIS",
            "allowed_scope_paths": ["global/core"],
            "status": status,
            "source_role": "user",
            "source_user_item_ref": "user-item:synthetic:publisher",
            "source_user_item_digest": "d" * 64,
            "not_claimed": list(CLAUDE_GLOBAL_NONCLAIMS),
        }
    )


def runtime_fixture(tmp_path: Path):
    root = tmp_path / "runtime"
    target = root / "claude" / "MNEME_GLOBAL.md"
    target.parent.mkdir(parents=True)
    return root, target


def test_plan_is_read_only_and_binds_exact_result_and_target(tmp_path):
    root, target = runtime_fixture(tmp_path)
    target.write_bytes(b"old projection")
    before = {
        item.relative_to(root).as_posix(): item.read_bytes()
        for item in root.rglob("*")
        if item.is_file()
    }
    result = projection()

    selected = ClaudeProjectionPublisher(root).plan(
        result,
        target,
        sha256(b"old projection"),
    )

    after = {
        item.relative_to(root).as_posix(): item.read_bytes()
        for item in root.rglob("*")
        if item.is_file()
    }
    assert isinstance(selected, PreparedClaudePublication)
    assert before == after
    assert selected.content == result.content
    assert selected.contract.projection_ref == result.manifest.projection_ref
    assert selected.contract.projection_digest == result.manifest.digest
    assert selected.contract.content_sha256 == sha256(result.content)
    assert selected.contract.target_preimage_sha256 == sha256(b"old projection")
    assert selected.verify() is True


def test_publish_atomically_replaces_and_returns_bound_receipt(tmp_path):
    root, target = runtime_fixture(tmp_path)
    target.write_bytes(b"old projection")
    result = projection()
    approved = authorization()
    publisher = ClaudeProjectionPublisher(root)
    selected = publisher.plan(result, target, sha256(b"old projection"))

    receipt = publisher.publish(selected, approved)

    assert target.read_bytes() == result.content
    assert receipt.publication_plan_ref == selected.contract.plan_id
    assert receipt.publication_plan_digest == selected.contract.digest
    assert receipt.authorization_ref == approved.authorization_id
    assert receipt.authorization_digest == approved.digest
    assert receipt.projection_ref == result.manifest.projection_ref
    assert receipt.projection_digest == result.manifest.digest
    assert receipt.target_before_sha256 == sha256(b"old projection")
    assert receipt.target_after_sha256 == sha256(result.content)
    assert receipt.readback_sha256 == sha256(result.content)
    assert receipt.outcome == "published"
    assert not tuple(target.parent.glob(f".{target.name}.*"))


def test_missing_target_is_created_and_fresh_same_content_plan_is_idempotent(tmp_path):
    root, target = runtime_fixture(tmp_path)
    result = projection()
    publisher = ClaudeProjectionPublisher(root)

    first_plan = publisher.plan(result, target, None)
    first = publisher.publish(first_plan, authorization())
    second_plan = publisher.plan(result, target, sha256(result.content))
    second = publisher.publish(second_plan, authorization())

    assert target.read_bytes() == result.content
    assert first.target_before_sha256 is None
    assert first.outcome == "published"
    assert second.outcome == "idempotent"
    assert second.target_before_sha256 == sha256(result.content)


def test_stale_projection_target_refuses_without_mutation(tmp_path):
    root, target = runtime_fixture(tmp_path)
    target.write_bytes(b"old")
    publisher = ClaudeProjectionPublisher(root)
    selected = publisher.plan(projection(), target, sha256(b"old"))
    target.write_bytes(b"changed by another writer")

    with pytest.raises(StaleTargetError):
        publisher.publish(selected, authorization())

    assert target.read_bytes() == b"changed by another writer"
    assert not tuple(target.parent.glob(f".{target.name}.*"))


def test_two_publishers_cannot_both_win_one_preimage_cas(tmp_path, monkeypatch):
    root, target = runtime_fixture(tmp_path)
    target.write_bytes(b"old")
    selected = ClaudeProjectionPublisher(root).plan(
        projection(),
        target,
        sha256(b"old"),
    )
    original_replace = os.replace
    barrier = Barrier(2)
    order_guard = Lock()
    replace_count = [0]
    first_publish_done = Event()

    def synchronized_replace(source, destination):
        try:
            barrier.wait(timeout=1)
        except BrokenBarrierError:
            pass
        with order_guard:
            order = replace_count[0]
            replace_count[0] += 1
        if order == 1:
            assert first_publish_done.wait(timeout=2)
        original_replace(source, destination)

    monkeypatch.setattr(os, "replace", synchronized_replace)

    def publish_once():
        try:
            receipt = ClaudeProjectionPublisher(root).publish(
                selected,
                authorization(),
            )
        except (StoreConflictError, StaleTargetError) as error:
            return "refused", type(error).__name__
        first_publish_done.set()
        return "success", receipt.digest

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = tuple(pool.map(lambda _: publish_once(), range(2)))

    assert sum(kind == "success" for kind, _ in outcomes) == 1
    assert sum(kind == "refused" for kind, _ in outcomes) == 1


@pytest.mark.parametrize(
    "expected",
    [None, "0" * 64, "not-a-digest"],
)
def test_existing_target_requires_its_exact_preimage_digest(tmp_path, expected):
    root, target = runtime_fixture(tmp_path)
    target.write_bytes(b"old")

    with pytest.raises(StaleTargetError):
        ClaudeProjectionPublisher(root).plan(projection(), target, expected)

    assert target.read_bytes() == b"old"


def test_missing_target_refuses_non_null_preimage(tmp_path):
    root, target = runtime_fixture(tmp_path)
    with pytest.raises(StaleTargetError):
        ClaudeProjectionPublisher(root).plan(projection(), target, "0" * 64)
    assert not target.exists()


def test_crash_before_replace_retains_old_projection_and_cleans_temp(tmp_path):
    root, target = runtime_fixture(tmp_path)
    target.write_bytes(b"old")
    publisher = ClaudeProjectionPublisher(root, crash_at="before_replace")
    selected = publisher.plan(projection(), target, sha256(b"old"))

    with pytest.raises(InjectedCrash, match="before_replace"):
        publisher.publish(selected, authorization())

    assert target.read_bytes() == b"old"
    assert not tuple(target.parent.glob(f".{target.name}.*"))


def test_crash_after_replace_has_new_bytes_but_no_success_receipt(tmp_path):
    root, target = runtime_fixture(tmp_path)
    target.write_bytes(b"old")
    result = projection()
    publisher = ClaudeProjectionPublisher(root, crash_at="after_replace")
    selected = publisher.plan(result, target, sha256(b"old"))

    with pytest.raises(InjectedCrash, match="after_replace"):
        publisher.publish(selected, authorization())

    assert target.read_bytes() == result.content
    assert not tuple(target.parent.glob(f".{target.name}.*"))


@pytest.mark.parametrize("status", ["revoked", "expired", "suspended"])
def test_inactive_manual_authority_refuses_before_mutation(tmp_path, status):
    root, target = runtime_fixture(tmp_path)
    target.write_bytes(b"old")
    publisher = ClaudeProjectionPublisher(root)
    selected = publisher.plan(projection(), target, sha256(b"old"))

    with pytest.raises(ManualAuthorityError, match="active"):
        publisher.publish(selected, authorization(status=status))

    assert target.read_bytes() == b"old"


def test_tampered_prepared_content_refuses_before_mutation(tmp_path):
    root, target = runtime_fixture(tmp_path)
    target.write_bytes(b"old")
    publisher = ClaudeProjectionPublisher(root)
    selected = publisher.plan(projection(), target, sha256(b"old"))
    tampered = replace(selected, content=selected.content + b"tampered")

    with pytest.raises(ClaudeContractError, match="content"):
        publisher.publish(tampered, authorization())

    assert target.read_bytes() == b"old"


def test_escape_private_temp_ads_and_network_targets_are_refused(tmp_path):
    root, _ = runtime_fixture(tmp_path)
    forbidden = (
        root.parent / "outside.md",
        root / "private" / "projection.md",
        root / "temp" / "projection.md",
        root / "network" / "projection.md",
        root / "claude" / "projection.md:stream",
        Path(r"\\synthetic-server\share\projection.md"),
        root,
    )

    for target in forbidden:
        with pytest.raises(ClaudePathBoundaryError):
            ClaudeProjectionPublisher(root).plan(projection(), target, None)


def test_git_worktree_target_is_refused(tmp_path):
    root, target = runtime_fixture(tmp_path)
    (root / ".git").mkdir()

    with pytest.raises(ClaudePathBoundaryError, match="Git"):
        ClaudeProjectionPublisher(root).plan(projection(), target, None)


def test_existing_hardlink_target_is_refused_without_mutation(tmp_path):
    root, target = runtime_fixture(tmp_path)
    target.write_bytes(b"old")
    sibling = target.with_name("hardlink-copy.md")
    os.link(target, sibling)

    with pytest.raises(ClaudePathBoundaryError, match="hardlink"):
        ClaudeProjectionPublisher(root).plan(
            projection(),
            target,
            sha256(b"old"),
        )

    assert target.read_bytes() == b"old"
    assert sibling.read_bytes() == b"old"


def test_hardlinked_writer_lock_is_refused_before_target_mutation(tmp_path):
    root, target = runtime_fixture(tmp_path)
    target.write_bytes(b"old")
    publisher = ClaudeProjectionPublisher(root)
    selected = publisher.plan(projection(), target, sha256(b"old"))
    lock_path = root / ".claude-projection.writer.lock"
    lock_path.write_bytes(b"\0")
    os.link(lock_path, root / "lock-hardlink-copy")

    with pytest.raises(ClaudePathBoundaryError, match="writer lock"):
        publisher.publish(selected, authorization())

    assert target.read_bytes() == b"old"


def test_symlink_target_is_refused_without_following_it(tmp_path):
    root, target = runtime_fixture(tmp_path)
    outside = tmp_path / "outside-source.md"
    outside.write_bytes(b"outside")
    try:
        target.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"symlink creation unavailable: {error}")

    with pytest.raises(ClaudePathBoundaryError, match="symlink"):
        ClaudeProjectionPublisher(root).plan(projection(), target, None)

    assert outside.read_bytes() == b"outside"


def test_relative_runtime_root_is_refused_without_discovery(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ClaudePathBoundaryError, match="absolute"):
        ClaudeProjectionPublisher(Path("runtime"))
