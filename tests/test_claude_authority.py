from __future__ import annotations

from pathlib import Path

import pytest

from mneme.claude_authority import VerifiedClaudeWriteContext
from mneme.claude_contracts import (
    CLAUDE_GLOBAL_NONCLAIMS,
    LocalManualWriteAuthorization,
)
from mneme.errors import ManualAuthorityError
from mneme.records import MemoryRecord
from mneme.store import MemoryStore
from mneme.transactions import TransactionProposal


def record(record_id: str = "record:synthetic:authority") -> dict[str, object]:
    return {
        "record_version": "mneme.memory-record/0.1",
        "record_id": record_id,
        "record_type": "instruction",
        "scope": {"kind": "global", "subject": "core"},
        "content": {"text": "Synthetic authority binding evidence."},
        "relations": [],
        "provenance": {
            "event_id": f"event:{record_id}",
            "source_ref": "synthetic:authority-test",
        },
        "status": "active",
    }


def transaction(
    *,
    transaction_id: str = "transaction:synthetic:authority",
    expected_head: str = "GENESIS",
    selected_record: dict[str, object] | None = None,
) -> TransactionProposal:
    selected = selected_record or record()
    return TransactionProposal.from_dict(
        {
            "transaction_version": "mneme.transaction/0.1",
            "transaction_id": transaction_id,
            "expected_source_head": expected_head,
            "declared_record_count": 1,
            "record_digests": [MemoryRecord.from_dict(selected).digest()],
            "records": [selected],
            "authority_ref": "authorization:synthetic:authority",
            "commit_marker": "MNEME_COMMIT/0.1",
        }
    )


def authorization(tx: TransactionProposal) -> LocalManualWriteAuthorization:
    raw = tx.to_dict()
    return LocalManualWriteAuthorization.sealed(
        {
            "authorization_version": "mneme.local-manual-write-authorization/0.1",
            "authorization_id": "authorization:synthetic:authority",
            "principal_ref": "principal:neo.k",
            "transaction_ref": raw["transaction_id"],
            "transaction_digest": tx.digest(),
            "expected_source_head": raw["expected_source_head"],
            "allowed_scope_paths": ["global/core"],
            "status": "active",
            "source_role": "user",
            "source_user_item_ref": "user-item:synthetic:authority",
            "source_user_item_digest": "e" * 64,
            "not_claimed": list(CLAUDE_GLOBAL_NONCLAIMS),
        }
    )


def committed_context(root: Path):
    store = MemoryStore(root / "memory.mlfdir")
    tx = transaction()
    receipt = store.commit(tx)
    context = VerifiedClaudeWriteContext.bind(store, tx, receipt, authorization(tx))
    return store, tx, receipt, context


def test_context_binds_exact_committed_transaction_and_authorization(tmp_path):
    store, tx, receipt, context = committed_context(tmp_path)

    assert context.verify() is True
    assert context.store is store
    assert context.transaction == tx
    assert context.commit_receipt == receipt
    assert context.authorization.digest == authorization(tx).digest
    assert context.transaction_ref == tx.to_dict()["transaction_id"]
    assert context.transaction_digest == tx.digest()
    assert context.committed_head == receipt.new_head


def test_unrelated_valid_authorization_is_rejected(tmp_path):
    store = MemoryStore(tmp_path / "memory.mlfdir")
    tx = transaction()
    receipt = store.commit(tx)
    unrelated = transaction(
        transaction_id="transaction:synthetic:unrelated",
        selected_record=record("record:synthetic:unrelated"),
    )

    with pytest.raises(ManualAuthorityError, match="transaction"):
        VerifiedClaudeWriteContext.bind(store, tx, receipt, authorization(unrelated))


def test_context_becomes_stale_when_store_head_advances(tmp_path):
    store, _, first_receipt, context = committed_context(tmp_path)
    second = transaction(
        transaction_id="transaction:synthetic:second",
        expected_head=first_receipt.new_head,
        selected_record=record("record:synthetic:second"),
    )
    store.commit(second)

    with pytest.raises(ManualAuthorityError, match="current head"):
        context.verify()


def test_missing_store_evidence_refuses_without_creating_store(tmp_path):
    store = MemoryStore(tmp_path / "missing" / "memory.mlfdir")
    tx = transaction()
    fake_receipt = type("Receipt", (), {})()

    with pytest.raises(ManualAuthorityError, match="commit receipt"):
        VerifiedClaudeWriteContext.bind(store, tx, fake_receipt, authorization(tx))

    assert not store.root.exists()
