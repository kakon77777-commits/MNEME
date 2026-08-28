from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from mneme.adapters.claude import (
    ClaudeGlobalMemoryAdapter,
    ClaudeGlobalProjectionResult,
)
from mneme.claude_contracts import (
    CLAUDE_GLOBAL_NONCLAIMS,
    ClaudeGlobalProjectionRequest,
)
from mneme.errors import (
    ClaudeContractError,
    ClaudeRouteError,
    RequiredRecordOmittedError,
)
from mneme.records import MemoryRecord
from mneme.routes import Route
from mneme.store import MemoryStore
from mneme.transactions import TransactionProposal


def raw_record(
    record_id: str,
    scope: str,
    *,
    record_type: str = "fact",
    status: str = "active",
    text: str | None = None,
) -> dict[str, object]:
    kind, _, subject = scope.partition("/")
    return {
        "record_version": "mneme.memory-record/0.1",
        "record_id": record_id,
        "record_type": record_type,
        "scope": {"kind": kind, "subject": subject},
        "content": {"text": text if text is not None else f"Synthetic {record_id}."},
        "relations": [],
        "provenance": {
            "event_id": f"event-{record_id}",
            "source_ref": "synthetic:claude-adapter",
        },
        "status": status,
    }


def global_route(**changes) -> Route:
    value = {
        "route_version": "mneme.route/0.1",
        "route_id": "route://global/tier0",
        "scope_prefixes": ["global"],
        "record_types": ["instruction", "fact", "lesson"],
    }
    value.update(changes)
    return Route.from_dict(value)


def request_for(head: str, **changes) -> ClaudeGlobalProjectionRequest:
    value = {
        "request_version": "mneme.claude-global-projection-request/0.1",
        "request_id": "request:synthetic:adapter",
        "expected_source_head": head,
        "route_id": "route://global/tier0",
        "allowed_scope_paths": [
            "global/core",
            "global/collaboration",
            "global/verification",
            "global/machine",
        ],
        "required_record_ids": [],
        "byte_budget": 16000,
        "target_kind": "claude_code_user_memory_import",
        "projection_ref": "projection:synthetic:adapter",
        "not_claimed": list(CLAUDE_GLOBAL_NONCLAIMS),
    }
    value.update(changes)
    return ClaudeGlobalProjectionRequest.sealed(value)


def store_with_records(tmp_path, *records: dict[str, object]) -> MemoryStore:
    store = MemoryStore(tmp_path / "memory.mlfdir")
    proposal = TransactionProposal.from_dict(
        {
            "transaction_version": "mneme.transaction/0.1",
            "transaction_id": "transaction:synthetic:adapter",
            "expected_source_head": "GENESIS",
            "declared_record_count": len(records),
            "record_digests": [
                MemoryRecord.from_dict(record).digest() for record in records
            ],
            "records": list(records),
            "authority_ref": "synthetic-authority:claude-adapter",
            "commit_marker": "MNEME_COMMIT/0.1",
        }
    )
    store.commit(proposal)
    return store


def adapter_with_records(tmp_path, *records: dict[str, object]):
    store = store_with_records(tmp_path, *records)
    return ClaudeGlobalMemoryAdapter(store, global_route()), store


def omission_map(result: ClaudeGlobalProjectionResult) -> dict[str, str]:
    return {item["record_id"]: item["reason"] for item in result.manifest.omitted}


def test_adapter_surface_is_strictly_read_only():
    assert not hasattr(ClaudeGlobalMemoryAdapter, "commit")
    assert not hasattr(ClaudeGlobalMemoryAdapter, "write")
    assert not hasattr(ClaudeGlobalMemoryAdapter, "writeback")


def test_adapter_includes_only_declared_global_scopes(tmp_path):
    selected, store = adapter_with_records(
        tmp_path,
        raw_record("core", "global/core"),
        raw_record("collaboration", "global/collaboration"),
        raw_record("machine", "global/machine"),
        raw_record("identity", "identity/example", text="PRIVATE IDENTITY BODY"),
        raw_record("project", "project/example", text="PRIVATE PROJECT BODY"),
    )
    request = request_for(
        store.head(),
        allowed_scope_paths=["global/core", "global/collaboration"],
        required_record_ids=["core"],
    )

    result = selected.materialize(request)

    assert result.manifest.included_record_ids == ("core", "collaboration")
    assert omission_map(result) == {
        "machine": "scope_not_allowed",
        "identity": "scope_not_allowed",
        "project": "scope_not_allowed",
    }
    rendered = result.content.decode("utf-8")
    assert "PRIVATE IDENTITY BODY" not in rendered
    assert "PRIVATE PROJECT BODY" not in rendered
    assert "PRIVATE IDENTITY BODY" not in json.dumps(
        result.manifest.to_dict(), ensure_ascii=False
    )


def test_status_and_record_type_are_closed_without_body_leak(tmp_path):
    selected, store = adapter_with_records(
        tmp_path,
        raw_record("active", "global/core", record_type="lesson"),
        raw_record(
            "inactive",
            "global/core",
            status="withdrawn",
            text="INACTIVE PRIVATE-LIKE BODY",
        ),
        raw_record(
            "episode",
            "global/core",
            record_type="episode",
            text="EPISODE BODY",
        ),
    )

    result = selected.materialize(request_for(store.head()))

    assert result.manifest.included_record_ids == ("active",)
    assert omission_map(result) == {
        "inactive": "status_not_active",
        "episode": "record_type_not_allowed",
    }
    evidence = json.dumps(result.manifest.to_dict(), ensure_ascii=False)
    assert "INACTIVE PRIVATE-LIKE BODY" not in evidence
    assert "EPISODE BODY" not in evidence


@pytest.mark.parametrize(
    ("records", "required_id", "budget"),
    [
        ((raw_record("identity", "identity/example"),), "identity", 16000),
        ((raw_record("large", "global/core", text="x" * 1000),), "large", 100),
        ((raw_record("other", "global/core"),), "missing", 16000),
    ],
)
def test_required_record_omission_refuses_projection(
    tmp_path,
    records,
    required_id,
    budget,
):
    selected, store = adapter_with_records(tmp_path, *records)
    request = request_for(
        store.head(),
        required_record_ids=[required_id],
        byte_budget=budget,
    )

    with pytest.raises(RequiredRecordOmittedError, match=required_id):
        selected.materialize(request)


def test_projection_is_deterministic_digest_bound_and_bounded(tmp_path):
    records = tuple(
        raw_record(f"record-{index:03d}", "global/core", text="記憶" * 30)
        for index in range(80)
    )
    selected, store = adapter_with_records(tmp_path, *records)
    request = request_for(store.head(), required_record_ids=["record-000"])

    first = selected.materialize(request)
    second = selected.materialize(request)

    assert first == second
    assert first.manifest.digest == second.manifest.digest
    assert len(first.content) <= 16000
    assert first.manifest.content_bytes == len(first.content)
    assert first.manifest.content_sha256 == hashlib.sha256(first.content).hexdigest()
    assert first.manifest.request_ref == request.request_id
    assert first.manifest.request_digest == request.digest
    assert first.manifest.source_head == store.head()
    assert first.manifest.required_record_ids == ("record-000",)
    assert any(item["reason"] == "budget_exceeded" for item in first.manifest.omitted)


def test_stale_request_head_refuses_before_materialization(tmp_path):
    selected, _ = adapter_with_records(tmp_path, raw_record("core", "global/core"))
    stale = request_for("GENESIS")

    with pytest.raises(ClaudeRouteError, match="source head"):
        selected.materialize(stale)


@pytest.mark.parametrize(
    "route",
    [
        global_route(route_id="route://global/other"),
        global_route(scope_prefixes=["identity/example"]),
        global_route(record_types=["instruction", "fact", "lesson", "episode"]),
        global_route(record_types=["fact"]),
    ],
)
def test_route_profile_must_be_exact_global_tier0(tmp_path, route):
    store = store_with_records(tmp_path, raw_record("core", "global/core"))
    with pytest.raises(ClaudeRouteError):
        ClaudeGlobalMemoryAdapter(store, route)


def test_route_is_revalidated_at_each_materialization(tmp_path):
    route = global_route()
    store = store_with_records(tmp_path, raw_record("core", "global/core"))
    selected = ClaudeGlobalMemoryAdapter(store, route)
    route._raw["scope_prefixes"] = ["identity/example"]

    with pytest.raises(ClaudeRouteError):
        selected.materialize(request_for(store.head()))


def test_result_rejects_content_manifest_mismatch(tmp_path):
    selected, store = adapter_with_records(tmp_path, raw_record("core", "global/core"))
    result = selected.materialize(request_for(store.head()))

    with pytest.raises(ClaudeContractError, match="content"):
        replace(result, content=result.content + b"tampered")


def test_source_head_change_during_read_refuses_result():
    record = MemoryRecord.from_dict(raw_record("core", "global/core"))

    class DriftingStore:
        def __init__(self):
            self.calls = 0

        def head(self):
            self.calls += 1
            return SOURCE_HEADS[min(self.calls - 1, 1)]

        def iter_committed_records(self):
            return iter((record,))

    SOURCE_HEADS = ("a" * 64, "b" * 64)
    selected = ClaudeGlobalMemoryAdapter(DriftingStore(), global_route())

    with pytest.raises(ClaudeRouteError, match="changed during materialization"):
        selected.materialize(request_for(SOURCE_HEADS[0]))
