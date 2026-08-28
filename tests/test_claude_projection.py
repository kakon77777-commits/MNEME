from __future__ import annotations

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Barrier, BrokenBarrierError, Event, Lock

import pytest

from mneme.adapters.claude import ClaudeGlobalProjectionResult
from mneme.claude_authority import VerifiedClaudeWriteContext
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
    AtomicReplaceUnavailableError,
    ClaudeContractError,
    ClaudePathBoundaryError,
    InjectedCrash,
    ManualAuthorityError,
    StaleTargetError,
    StoreConflictError,
)
from mneme.store import MemoryStore
from tests.test_claude_authority import (
    authorization as bound_authorization,
)
from tests.test_claude_authority import (
    committed_context,
)
from tests.test_claude_authority import (
    record as authority_record,
)
from tests.test_claude_authority import (
    transaction as authority_transaction,
)
from tests.windows_junction import create_windows_junction


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


def projection_for_context(
    context: VerifiedClaudeWriteContext,
    content: bytes = b"# MNEME Projection\n\nSynthetic global memory.\n",
) -> ClaudeGlobalProjectionResult:
    record_id = str(context.transaction.to_dict()["records"][0]["record_id"])
    manifest = ClaudeGlobalProjectionManifest.sealed(
        {
            "manifest_version": "mneme.claude-global-projection-manifest/0.1",
            "projection_ref": "projection:synthetic:publisher-bound",
            "request_ref": "request:synthetic:publisher-bound",
            "request_digest": "a" * 64,
            "source_head": context.committed_head,
            "route_id": "route://global/tier0",
            "byte_budget": 16000,
            "content_bytes": len(content),
            "content_sha256": sha256(content),
            "included_record_ids": [record_id],
            "omitted": [],
            "required_record_ids": [record_id],
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


def bound_publication(
    tmp_path: Path,
    *,
    before: bytes | None = None,
    crash_at: str | None = None,
):
    _, _, _, context = committed_context(tmp_path / "context")
    root, target = runtime_fixture(tmp_path)
    if before is not None:
        target.write_bytes(before)
    result = projection_for_context(context)
    publisher = ClaudeProjectionPublisher(root, crash_at=crash_at)
    expected = sha256(before) if before is not None else None
    plan = publisher.plan(result, target, expected)
    return publisher, plan, context, result, target


def test_publish_requires_verified_committed_context(tmp_path):
    publisher, plan, context, result, target = bound_publication(tmp_path)

    publication = publisher.publish(plan, context)

    assert publication.verify(context, plan) is True
    assert publication.receipt.transaction_ref == context.transaction_ref
    assert publication.receipt.transaction_digest == context.transaction_digest
    assert publication.receipt.committed_head == context.committed_head
    assert publication.receipt.commit_receipt_digest == context.commit_receipt_digest
    assert publication.receipt.target_after_sha256 == sha256(result.content)
    assert target.read_bytes() == result.content


def test_raw_authorization_cannot_enter_publication_primitive(tmp_path):
    publisher, plan, _, _, target = bound_publication(tmp_path)

    with pytest.raises(ManualAuthorityError, match="context"):
        publisher.publish(plan, authorization())

    assert not target.exists()


def test_unrelated_committed_context_cannot_publish(tmp_path):
    publisher, plan, _, _, target = bound_publication(tmp_path / "first")
    store = MemoryStore(tmp_path / "second" / "memory.mlfdir")
    transaction = authority_transaction(
        transaction_id="transaction:synthetic:unrelated-publisher",
        selected_record=authority_record("record:synthetic:unrelated-publisher"),
    )
    receipt = store.commit(transaction)
    unrelated = VerifiedClaudeWriteContext.bind(
        store,
        transaction,
        receipt,
        bound_authorization(transaction),
    )

    with pytest.raises(ManualAuthorityError, match="source head"):
        publisher.publish(plan, unrelated)

    assert not target.exists()


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
    publisher, selected, context, result, target = bound_publication(
        tmp_path,
        before=b"old projection",
    )

    publication = publisher.publish(selected, context)
    receipt = publication.receipt

    assert target.read_bytes() == result.content
    assert receipt.publication_plan_ref == selected.contract.plan_id
    assert receipt.publication_plan_digest == selected.contract.digest
    assert receipt.authorization_ref == context.authorization.authorization_id
    assert receipt.authorization_digest == context.authorization.digest
    assert receipt.projection_ref == result.manifest.projection_ref
    assert receipt.projection_digest == result.manifest.digest
    assert receipt.target_before_sha256 == sha256(b"old projection")
    assert receipt.target_after_sha256 == sha256(result.content)
    assert receipt.readback_sha256 == sha256(result.content)
    assert receipt.outcome == "published"
    assert not tuple(target.parent.glob(f".{target.name}.*"))


def test_missing_target_is_created_and_fresh_same_content_plan_is_idempotent(tmp_path):
    publisher, first_plan, context, result, target = bound_publication(tmp_path)

    first = publisher.publish(first_plan, context).receipt
    second_plan = publisher.plan(result, target, sha256(result.content))
    second = publisher.publish(second_plan, context).receipt

    assert target.read_bytes() == result.content
    assert first.target_before_sha256 is None
    assert first.outcome == "published"
    assert second.outcome == "idempotent"
    assert second.target_before_sha256 == sha256(result.content)


def test_stale_projection_target_refuses_without_mutation(tmp_path):
    publisher, selected, context, _, target = bound_publication(
        tmp_path,
        before=b"old",
    )
    target.write_bytes(b"changed by another writer")

    with pytest.raises(StaleTargetError):
        publisher.publish(selected, context)

    assert target.read_bytes() == b"changed by another writer"
    assert not tuple(target.parent.glob(f".{target.name}.*"))


def test_two_publishers_cannot_both_win_one_preimage_cas(tmp_path, monkeypatch):
    publisher, selected, context, _, _ = bound_publication(
        tmp_path,
        before=b"old",
    )
    root = publisher._runtime_root
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
                context,
            )
        except (StoreConflictError, StaleTargetError) as error:
            return "refused", type(error).__name__
        first_publish_done.set()
        return "success", receipt.receipt.digest

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
    publisher, selected, context, _, target = bound_publication(
        tmp_path,
        before=b"old",
        crash_at="before_replace",
    )

    with pytest.raises(InjectedCrash, match="before_replace"):
        publisher.publish(selected, context)

    assert target.read_bytes() == b"old"
    assert not tuple(target.parent.glob(f".{target.name}.*"))


def test_crash_after_replace_has_new_bytes_but_no_success_receipt(tmp_path):
    publisher, selected, context, result, target = bound_publication(
        tmp_path,
        before=b"old",
        crash_at="after_replace",
    )

    with pytest.raises(InjectedCrash, match="after_replace"):
        publisher.publish(selected, context)

    assert target.read_bytes() == result.content
    assert not tuple(target.parent.glob(f".{target.name}.*"))


@pytest.mark.parametrize("status", ["revoked", "expired", "suspended"])
def test_inactive_manual_authority_refuses_before_mutation(tmp_path, status):
    store, transaction, receipt, _ = committed_context(tmp_path / "context")
    _, target = runtime_fixture(tmp_path)
    target.write_bytes(b"old")
    raw = bound_authorization(transaction).to_dict()
    raw["status"] = status
    inactive = LocalManualWriteAuthorization.sealed(raw)

    with pytest.raises(ManualAuthorityError, match="active"):
        VerifiedClaudeWriteContext.bind(store, transaction, receipt, inactive)

    assert target.read_bytes() == b"old"


def test_tampered_prepared_content_refuses_before_mutation(tmp_path):
    publisher, selected, context, _, target = bound_publication(
        tmp_path,
        before=b"old",
    )
    tampered = replace(selected, content=selected.content + b"tampered")

    with pytest.raises(ClaudeContractError, match="content"):
        publisher.publish(tampered, context)

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


def test_ai_home_component_is_refused_as_private(tmp_path):
    root, _ = runtime_fixture(tmp_path)
    target = root / "AI_HOME" / "projection.md"
    target.parent.mkdir()
    target.write_bytes(b"old")

    with pytest.raises(ClaudePathBoundaryError, match="private"):
        ClaudeProjectionPublisher(root).plan(projection(), target, sha256(b"old"))


def test_projection_target_control_character_is_refused_directly(tmp_path):
    root, _ = runtime_fixture(tmp_path)
    controlled = root / ("bell" + chr(7)) / "projection.md"

    with pytest.raises(ClaudePathBoundaryError, match="control"):
        ClaudeProjectionPublisher(root).plan(projection(), controlled, None)


@pytest.mark.skipif(os.name != "nt", reason="Windows junction control")
def test_windows_junction_inside_runtime_is_refused(tmp_path):
    root, _ = runtime_fixture(tmp_path)
    real = root / "real"
    real.mkdir()
    (real / "projection.md").write_bytes(b"old")
    junction = root / "junction"
    create_windows_junction(junction, real)

    with pytest.raises(ClaudePathBoundaryError, match="reparse"):
        ClaudeProjectionPublisher(root).plan(
            projection(),
            junction / "projection.md",
            sha256(b"old"),
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows junction control")
def test_windows_junction_runtime_root_is_refused(tmp_path):
    real_root = tmp_path / "real-runtime"
    target = real_root / "claude" / "MNEME_GLOBAL.md"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"old")
    junction_root = tmp_path / "junction-runtime"
    create_windows_junction(junction_root, real_root)

    with pytest.raises(ClaudePathBoundaryError, match="reparse"):
        ClaudeProjectionPublisher(junction_root).plan(
            projection(),
            junction_root / "claude" / "MNEME_GLOBAL.md",
            sha256(b"old"),
        )


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
    publisher, selected, context, _, target = bound_publication(
        tmp_path,
        before=b"old",
    )
    root = publisher._runtime_root
    lock_path = root / ".claude-projection.writer.lock"
    lock_path.write_bytes(b"\0")
    os.link(lock_path, root / "lock-hardlink-copy")

    with pytest.raises(ClaudePathBoundaryError, match="writer lock"):
        publisher.publish(selected, context)

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


@pytest.mark.skipif(os.name != "nt", reason="Windows sharing behavior")
def test_open_reader_handle_returns_typed_replace_refusal(tmp_path):
    publisher, selected, context, _, target = bound_publication(
        tmp_path,
        before=b"old",
    )
    handles = [target.open("rb") for _ in range(4)]
    try:
        with pytest.raises(AtomicReplaceUnavailableError) as captured:
            publisher.publish(selected, context)
    finally:
        for handle in handles:
            handle.close()

    assert isinstance(captured.value.__cause__, OSError)
    assert target.read_bytes() == b"old"
    assert not tuple(target.parent.glob(f".{target.name}.*"))


def test_atomic_replace_failure_is_not_retried(tmp_path, monkeypatch):
    publisher, selected, context, _, target = bound_publication(
        tmp_path,
        before=b"old",
    )
    calls = 0

    def refuse_replace(source, destination):
        nonlocal calls
        calls += 1
        raise PermissionError(13, "synthetic replace refusal", destination)

    monkeypatch.setattr(os, "replace", refuse_replace)

    with pytest.raises(AtomicReplaceUnavailableError) as captured:
        publisher.publish(selected, context)

    assert calls == 1
    assert isinstance(captured.value.__cause__, PermissionError)
    assert "errno=13" in str(captured.value)
    assert target.read_bytes() == b"old"
    assert not tuple(target.parent.glob(f".{target.name}.*"))
