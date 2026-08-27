import json

import pytest

from mneme.adapters.soacr import MemoryNeedRequest, MnemeReadAdapter
from mneme.records import MemoryRecord
from mneme.routes import Route
from mneme.store import MemoryStore
from mneme.transactions import TransactionProposal


def raw_record(record_id, scope, text):
    kind, _, subject = scope.partition("/")
    return {
        "record_version": "mneme.memory-record/0.1",
        "record_id": record_id,
        "record_type": "fact",
        "scope": {"kind": kind, "subject": subject},
        "content": {"text": text},
        "relations": [],
        "provenance": {"event_id": f"evt-{record_id}", "source_ref": "synthetic:test"},
        "status": "active",
    }


def two_identity_tx():
    records = [raw_record("a1", "identity/a", "A private content"), raw_record("b1", "identity/b", "B SECRET CONTENT")]
    return TransactionProposal.from_dict({
        "transaction_version": "mneme.transaction/0.1",
        "transaction_id": "tx-ab",
        "expected_source_head": "GENESIS",
        "declared_record_count": 2,
        "record_digests": [MemoryRecord.from_dict(r).digest() for r in records],
        "records": records,
        "authority_ref": "synthetic-authority:test",
        "commit_marker": "MNEME_COMMIT/0.1",
    })


def route_a():
    return Route.from_dict({
        "route_version": "mneme.route/0.1",
        "route_id": "route://identity/a/bootstrap",
        "scope_prefixes": ["identity/a"],
        "record_types": [],
    })


def test_adapter_surface_is_read_only():
    assert not hasattr(MnemeReadAdapter, "commit")
    assert not hasattr(MnemeReadAdapter, "write")


def test_invalid_budget_is_rejected_before_materialization():
    with pytest.raises(ValueError):
        MemoryNeedRequest(identity_scope="identity/a", route_id="route://identity/a/bootstrap", byte_budget=0)


def test_scope_leak_is_blocked_and_omission_never_contains_private_text(tmp_path):
    store = MemoryStore(tmp_path / "memory.mlfdir")
    store.initialize()
    store.commit(two_identity_tx())
    route = route_a()
    adapter = MnemeReadAdapter(store, {route.route_id: route})
    result = adapter.materialize(MemoryNeedRequest("identity/a", route.route_id, 500), {"identity/a"})
    text = result.content.decode("utf-8")
    assert "A private content" in text
    assert "B SECRET CONTENT" not in text
    assert any(item["record_id"] == "b1" for item in result.manifest["omitted"])
    assert "B SECRET CONTENT" not in json.dumps(result.manifest, ensure_ascii=False)
    assert result.manifest["source_head"] == store.head()


def test_identity_request_cannot_name_another_identity_route(tmp_path):
    store = MemoryStore(tmp_path / "memory.mlfdir")
    store.initialize()
    route = Route.from_dict({
        "route_version": "mneme.route/0.1",
        "route_id": "route://identity/b/bootstrap",
        "scope_prefixes": ["identity/b"],
        "record_types": [],
    })
    adapter = MnemeReadAdapter(store, {route.route_id: route})
    with pytest.raises(ValueError):
        adapter.materialize(MemoryNeedRequest("identity/a", route.route_id, 100), {"identity/a", "identity/b"})
