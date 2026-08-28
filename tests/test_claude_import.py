from __future__ import annotations

import hashlib
import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import pytest

from mneme.claude_contracts import (
    CLAUDE_GLOBAL_NONCLAIMS,
    ClaudeGlobalProjectionManifest,
    LocalManualWriteAuthorization,
)
from mneme.claude_import import (
    BEGIN,
    END,
    ClaudeManagedImport,
    PreparedClaudeImport,
)
from mneme.errors import (
    ClaudePathBoundaryError,
    InjectedCrash,
    ManagedBlockConflictError,
    ManualAuthorityError,
    StaleTargetError,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "claude"
PROJECTION_BYTES = b"# MNEME Projection\n\nSynthetic global memory.\n"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest(content: bytes = PROJECTION_BYTES) -> ClaudeGlobalProjectionManifest:
    return ClaudeGlobalProjectionManifest.sealed(
        {
            "manifest_version": "mneme.claude-global-projection-manifest/0.1",
            "projection_ref": "projection:synthetic:managed-import",
            "request_ref": "request:synthetic:managed-import",
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


def authorization(*, status: str = "active") -> LocalManualWriteAuthorization:
    return LocalManualWriteAuthorization.sealed(
        {
            "authorization_version": "mneme.local-manual-write-authorization/0.1",
            "authorization_id": "authorization:synthetic:managed-import",
            "principal_ref": "principal:neo.k",
            "transaction_ref": "transaction:synthetic:managed-import",
            "transaction_digest": "c" * 64,
            "expected_source_head": "GENESIS",
            "allowed_scope_paths": ["global/core"],
            "status": status,
            "source_role": "user",
            "source_user_item_ref": "user-item:synthetic:managed-import",
            "source_user_item_digest": "d" * 64,
            "not_claimed": list(CLAUDE_GLOBAL_NONCLAIMS),
        }
    )


def environment(tmp_path: Path, *, user_bytes: bytes | None = b"Hand-authored.\n"):
    runtime_root = tmp_path / "runtime"
    projection = runtime_root / "claude" / "MNEME_GLOBAL.md"
    projection.parent.mkdir(parents=True)
    projection.write_bytes(PROJECTION_BYTES)
    user_root = tmp_path / "synthetic-user"
    user_memory = user_root / ".claude" / "CLAUDE.md"
    user_memory.parent.mkdir(parents=True)
    if user_bytes is not None:
        user_memory.write_bytes(user_bytes)
    selected = ClaudeManagedImport(runtime_root, user_root, manifest())
    return selected, projection, user_memory, runtime_root, user_root


def expected_block(projection: Path) -> bytes:
    return BEGIN + b"\n@" + str(projection).encode("utf-8") + b"\n" + END + b"\n"


def expected_insert(before: bytes, projection: Path) -> bytes:
    separator = b"" if not before or before.endswith(b"\n") else b"\n"
    return before + separator + expected_block(projection)


def plan_for(selected: ClaudeManagedImport, user_memory: Path, projection: Path):
    expected = sha256(user_memory.read_bytes()) if user_memory.exists() else None
    return selected.plan(user_memory, projection, expected)


def file_snapshot(root: Path) -> dict[str, bytes]:
    return {
        item.relative_to(root).as_posix(): item.read_bytes()
        for item in root.rglob("*")
        if item.is_file()
    }


def test_plan_is_read_only_and_binds_projection_user_preimage(tmp_path):
    selected, projection, user_memory, _, _ = environment(tmp_path)
    before_projection = projection.read_bytes()
    before_user = user_memory.read_bytes()
    before_tree = file_snapshot(tmp_path)

    prepared = plan_for(selected, user_memory, projection)

    assert isinstance(prepared, PreparedClaudeImport)
    assert file_snapshot(tmp_path) == before_tree
    assert projection.read_bytes() == before_projection
    assert user_memory.read_bytes() == before_user
    assert prepared.contract.projection_ref == manifest().projection_ref
    assert prepared.contract.projection_digest == manifest().digest
    assert prepared.contract.projection_content_sha256 == sha256(PROJECTION_BYTES)
    assert prepared.contract.user_memory_preimage_sha256 == sha256(before_user)
    assert prepared.verify() is True


def test_unrelated_managed_blocks_bom_and_mixed_eol_are_byte_preserved(tmp_path):
    selected, projection, user_memory, _, _ = environment(tmp_path, user_bytes=None)
    shutil.copyfile(
        FIXTURE_ROOT / "user-memory-other-blocks-mixed-eol.md",
        user_memory,
    )
    before = user_memory.read_bytes()
    assert before.startswith(b"\xef\xbb\xbf")
    assert before.count(b"\r\n") == 4
    assert before.replace(b"\r\n", b"").count(b"\n") == 2

    receipt = selected.apply(
        plan_for(selected, user_memory, projection),
        authorization(),
    )

    after = user_memory.read_bytes()
    assert after == expected_insert(before, projection)
    assert b"<!-- BEGIN EML TOOLING -->" in after
    assert b"@/synthetic/existing.md\r\n" in after
    assert receipt.outside_bytes_preserved is True
    assert receipt.outcome == "inserted"
    assert receipt.claude_memory_readback == "NOT_RUN"


def test_existing_exact_block_is_replaced_without_touching_outside_bytes(tmp_path):
    selected, projection, user_memory, _, _ = environment(tmp_path)
    old_projection = tmp_path / "old" / "MNEME_GLOBAL.md"
    prefix = b"\xef\xbb\xbfHeader\r\n<!-- BEGIN EML X -->\nbody\r\n<!-- END EML X -->\n"
    suffix = b"Tail\r\n"
    before = prefix + expected_block(old_projection) + suffix
    user_memory.write_bytes(before)

    receipt = selected.apply(
        plan_for(selected, user_memory, projection),
        authorization(),
    )

    assert user_memory.read_bytes() == prefix + expected_block(projection) + suffix
    assert receipt.outcome == "replaced"
    assert receipt.outside_bytes_preserved is True


def test_existing_exact_same_block_is_idempotent(tmp_path):
    selected, projection, user_memory, _, _ = environment(tmp_path)
    before = b"Header\r\n" + expected_block(projection) + b"Tail\n"
    user_memory.write_bytes(before)

    receipt = selected.apply(
        plan_for(selected, user_memory, projection),
        authorization(),
    )

    assert user_memory.read_bytes() == before
    assert receipt.outcome == "idempotent"
    assert receipt.user_memory_before_sha256 == sha256(before)
    assert receipt.user_memory_after_sha256 == sha256(before)


@pytest.mark.parametrize(
    "malformed",
    [
        BEGIN + b"\n@C:\\synthetic\\projection.md\n",
        b"@C:\\synthetic\\projection.md\n" + END + b"\n",
        expected_block(Path("C:/synthetic/one.md"))
        + expected_block(Path("C:/synthetic/two.md")),
        BEGIN + b"\n" + BEGIN + b"\n@C:\\synthetic\\projection.md\n" + END + b"\n" + END + b"\n",
        b"<!-- BEGIN MNEME GLOBAL PROJECTION v0.2 -->\n@C:\\synthetic\\projection.md\n<!-- END MNEME GLOBAL PROJECTION v0.2 -->\n",
        b"prefix " + BEGIN + b"\n@C:\\synthetic\\projection.md\n" + END + b"\n",
    ],
)
def test_malformed_partial_duplicate_nested_or_near_markers_refuse(
    tmp_path,
    malformed,
):
    selected, projection, user_memory, _, _ = environment(
        tmp_path,
        user_bytes=malformed,
    )
    before_projection = projection.read_bytes()
    before_user = user_memory.read_bytes()

    with pytest.raises(ManagedBlockConflictError):
        plan_for(selected, user_memory, projection)

    assert projection.read_bytes() == before_projection
    assert user_memory.read_bytes() == before_user


@pytest.mark.parametrize(
    "body",
    [
        b"```text\nunterminated code fence\n",
        b"```text\nstill fenced\n```not-a-closing-fence\n",
        b"```text\n" + expected_block(Path("C:/synthetic/old.md")) + b"```\n",
    ],
)
def test_import_cannot_be_inserted_or_found_inside_code_fence(tmp_path, body):
    selected, projection, user_memory, _, _ = environment(tmp_path, user_bytes=body)
    with pytest.raises(ManagedBlockConflictError, match="fence"):
        plan_for(selected, user_memory, projection)
    assert user_memory.read_bytes() == body


def test_stale_user_memory_refuses_without_overwriting_newer_bytes(tmp_path):
    selected, projection, user_memory, _, _ = environment(tmp_path)
    prepared = plan_for(selected, user_memory, projection)
    user_memory.write_bytes(b"newer hand-authored bytes")

    with pytest.raises(StaleTargetError, match="user memory"):
        selected.apply(prepared, authorization())

    assert user_memory.read_bytes() == b"newer hand-authored bytes"


def test_changed_projection_refuses_without_mutating_user_memory(tmp_path):
    selected, projection, user_memory, _, _ = environment(tmp_path)
    prepared = plan_for(selected, user_memory, projection)
    before_user = user_memory.read_bytes()
    projection.write_bytes(b"changed projection")

    with pytest.raises(StaleTargetError, match="projection"):
        selected.apply(prepared, authorization())

    assert projection.read_bytes() == b"changed projection"
    assert user_memory.read_bytes() == before_user


@pytest.mark.parametrize("status", ["revoked", "expired", "suspended"])
def test_inactive_authority_refuses_before_user_memory_mutation(tmp_path, status):
    selected, projection, user_memory, _, _ = environment(tmp_path)
    before = user_memory.read_bytes()
    with pytest.raises(ManualAuthorityError, match="active"):
        selected.apply(
            plan_for(selected, user_memory, projection),
            authorization(status=status),
        )
    assert user_memory.read_bytes() == before


def test_new_user_memory_file_can_be_created_inside_explicit_root(tmp_path):
    selected, projection, user_memory, _, _ = environment(tmp_path, user_bytes=None)
    prepared = selected.plan(user_memory, projection, None)

    receipt = selected.apply(prepared, authorization())

    assert user_memory.read_bytes() == expected_block(projection)
    assert receipt.user_memory_before_sha256 is None
    assert receipt.outcome == "inserted"


def test_crash_before_replace_retains_old_user_memory_and_cleans_temp(tmp_path):
    _, projection, user_memory, runtime_root, user_root = environment(tmp_path)
    before = user_memory.read_bytes()
    crashing = ClaudeManagedImport(
        runtime_root,
        user_root,
        manifest(),
        crash_at="before_replace",
    )

    with pytest.raises(InjectedCrash, match="before_replace"):
        crashing.apply(
            plan_for(crashing, user_memory, projection),
            authorization(),
        )

    assert user_memory.read_bytes() == before
    assert not tuple(user_memory.parent.glob(f".{user_memory.name}.*"))


def test_crash_after_replace_has_new_bytes_and_no_success_receipt(tmp_path):
    _, projection, user_memory, runtime_root, user_root = environment(tmp_path)
    before = user_memory.read_bytes()
    crashing = ClaudeManagedImport(
        runtime_root,
        user_root,
        manifest(),
        crash_at="after_replace",
    )

    with pytest.raises(InjectedCrash, match="after_replace"):
        crashing.apply(
            plan_for(crashing, user_memory, projection),
            authorization(),
        )

    assert user_memory.read_bytes() == expected_insert(before, projection)
    assert not tuple(user_memory.parent.glob(f".{user_memory.name}.*"))


def test_concurrent_reader_sees_only_complete_old_or_new_bytes(tmp_path, monkeypatch):
    selected, projection, user_memory, _, _ = environment(tmp_path)
    prepared = plan_for(selected, user_memory, projection)
    old_bytes = user_memory.read_bytes()
    new_bytes = expected_insert(old_bytes, projection)
    original_replace = os.replace
    replace_ready = Event()
    allow_replace = Event()

    def paused_replace(source, destination):
        replace_ready.set()
        assert allow_replace.wait(timeout=2)
        original_replace(source, destination)

    monkeypatch.setattr(os, "replace", paused_replace)
    observations: list[bytes] = []

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(selected.apply, prepared, authorization())
        assert replace_ready.wait(timeout=2)
        observations.extend(user_memory.read_bytes() for _ in range(50))
        allow_replace.set()
        future.result(timeout=5)
        observations.extend(user_memory.read_bytes() for _ in range(50))

    assert old_bytes in observations
    assert new_bytes in observations
    assert set(observations) == {old_bytes, new_bytes}


def test_receipt_contains_digests_not_user_memory_body(tmp_path):
    body = b"SYNTHETIC-SENSITIVE-HAND-AUTHORED-BODY\n"
    selected, projection, user_memory, _, _ = environment(tmp_path, user_bytes=body)
    receipt = selected.apply(
        plan_for(selected, user_memory, projection),
        authorization(),
    )
    evidence = json.dumps(receipt.to_dict(), sort_keys=True)
    assert "SYNTHETIC-SENSITIVE-HAND-AUTHORED-BODY" not in evidence
    assert receipt.managed_block_sha256 == sha256(expected_block(projection))


def test_projection_and_user_memory_must_stay_inside_explicit_roots(tmp_path):
    selected, projection, user_memory, runtime_root, user_root = environment(tmp_path)
    outside_projection = tmp_path / "outside-projection.md"
    outside_projection.write_bytes(PROJECTION_BYTES)
    outside_user = tmp_path / "outside-user" / "CLAUDE.md"
    outside_user.parent.mkdir()
    outside_user.write_bytes(b"outside")
    private_user = user_root / "private" / "CLAUDE.md"

    with pytest.raises(ClaudePathBoundaryError):
        selected.plan(user_memory, outside_projection, sha256(user_memory.read_bytes()))
    with pytest.raises(ClaudePathBoundaryError):
        selected.plan(outside_user, projection, sha256(outside_user.read_bytes()))
    with pytest.raises(ClaudePathBoundaryError):
        selected.plan(private_user, projection, None)
    with pytest.raises(ClaudePathBoundaryError):
        selected.plan(user_root / "NOT_CLAUDE.md", projection, None)

    (runtime_root / ".git").mkdir()
    with pytest.raises(ClaudePathBoundaryError, match="Git"):
        selected.plan(user_memory, projection, sha256(user_memory.read_bytes()))


def test_projection_path_control_character_is_rejected_during_plan(tmp_path):
    selected, _, user_memory, runtime_root, _ = environment(tmp_path)
    controlled = runtime_root / "line\nbreak" / "MNEME_GLOBAL.md"

    with pytest.raises(ClaudePathBoundaryError, match="control"):
        selected.plan(
            user_memory,
            controlled,
            sha256(user_memory.read_bytes()),
        )


def test_hardlinked_user_memory_is_refused_without_mutation(tmp_path):
    selected, projection, user_memory, _, _ = environment(tmp_path)
    sibling = user_memory.with_name("CLAUDE-copy.md")
    os.link(user_memory, sibling)
    before = user_memory.read_bytes()

    with pytest.raises(ClaudePathBoundaryError, match="hardlink"):
        selected.plan(user_memory, projection, sha256(before))

    assert user_memory.read_bytes() == before
    assert sibling.read_bytes() == before


def test_hardlinked_import_writer_lock_is_refused_before_mutation(tmp_path):
    selected, projection, user_memory, _, user_root = environment(tmp_path)
    prepared = plan_for(selected, user_memory, projection)
    before = user_memory.read_bytes()
    lock_path = user_root / ".mneme-claude-import.writer.lock"
    lock_path.write_bytes(b"\0")
    os.link(lock_path, user_root / "import-lock-copy")

    with pytest.raises(ClaudePathBoundaryError, match="writer lock"):
        selected.apply(prepared, authorization())

    assert user_memory.read_bytes() == before


def test_invalid_utf8_user_memory_refuses_without_mutation(tmp_path):
    body = b"valid prefix\n\xff\xfeinvalid"
    selected, projection, user_memory, _, _ = environment(tmp_path, user_bytes=body)
    with pytest.raises(ManagedBlockConflictError, match="UTF-8"):
        plan_for(selected, user_memory, projection)
    assert user_memory.read_bytes() == body
