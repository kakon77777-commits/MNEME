from copy import deepcopy
from pathlib import Path

import pytest

from mneme.canonical import canonical_json_bytes
from mneme.errors import RecordIdConflictError, StoreConflictError, StoreIntegrityError
from mneme.records import MemoryRecord
from mneme.store import MemoryStore
from mneme.transactions import TransactionProposal


def record(record_id="rec-001"):
    return {
        "record_version": "mneme.memory-record/0.1",
        "record_id": record_id,
        "record_type": "lesson",
        "scope": {"kind": "global", "subject": "verification"},
        "content": {"text": "Synthetic lesson."},
        "relations": [],
        "provenance": {"event_id": f"evt-{record_id}", "source_ref": "synthetic:test"},
        "status": "active",
    }


def transaction_dict(*, transaction_id="tx-001", expected_head="GENESIS", record_id="rec-001"):
    raw_record = record(record_id)
    digest = MemoryRecord.from_dict(raw_record).digest()
    return {
        "transaction_version": "mneme.transaction/0.1",
        "transaction_id": transaction_id,
        "expected_source_head": expected_head,
        "declared_record_count": 1,
        "record_digests": [digest],
        "records": [raw_record],
        "authority_ref": "synthetic-authority:test",
        "commit_marker": "MNEME_COMMIT/0.1",
    }


def test_fresh_store_starts_at_genesis(tmp_path: Path):
    store = MemoryStore(tmp_path / "memory.mlfdir")
    store.initialize()
    assert store.head() == "GENESIS"


def test_commit_advances_head_and_is_replay_idempotent(tmp_path: Path):
    store = MemoryStore(tmp_path / "memory.mlfdir")
    store.initialize()
    tx = TransactionProposal.from_dict(transaction_dict())
    first = store.commit(tx)
    second = store.commit(tx)
    assert first.new_head != "GENESIS"
    assert second.new_head == first.new_head
    assert second.idempotent is True
    assert list(store.iter_committed_transactions()) == [tx.to_dict()]


def test_stale_expected_head_is_rejected_without_new_commit(tmp_path: Path):
    store = MemoryStore(tmp_path / "memory.mlfdir")
    store.initialize()
    first = TransactionProposal.from_dict(transaction_dict())
    store.commit(first)
    stale = TransactionProposal.from_dict(transaction_dict(transaction_id="tx-stale", record_id="rec-stale"))
    with pytest.raises(StoreConflictError):
        store.commit(stale)
    assert len(list(store.iter_committed_transactions())) == 1


@pytest.mark.parametrize("corrupt", [b"\xff\n", b"not-a-head\n", b"a" * 64])
def test_corrupt_head_fails_closed(tmp_path: Path, corrupt: bytes):
    store = MemoryStore(tmp_path / "memory.mlfdir")
    store.initialize()
    (store.root / "HEAD").write_bytes(corrupt)
    with pytest.raises(StoreIntegrityError):
        store.head()


def test_mutated_committed_transaction_is_rejected_on_iteration(tmp_path: Path):
    store = MemoryStore(tmp_path / "memory.mlfdir")
    store.initialize()
    tx = TransactionProposal.from_dict(transaction_dict())
    store.commit(tx)
    tx_path = store.root / "transactions" / "committed" / f"{tx.digest()}.json"
    mutated = deepcopy(tx.to_dict())
    mutated["transaction_id"] = "tampered-but-readable"
    tx_path.write_bytes(canonical_json_bytes(mutated) + b"\n")
    with pytest.raises(StoreIntegrityError):
        list(store.iter_committed_transactions())


def test_existing_record_id_cannot_be_reused(tmp_path: Path):
    store = MemoryStore(tmp_path / "memory.mlfdir")
    first = store.commit(
        TransactionProposal.from_dict(
            transaction_dict(transaction_id="tx-first", record_id="rec-shared")
        )
    )
    changed = transaction_dict(
        transaction_id="tx-second",
        expected_head=first.new_head,
        record_id="rec-shared",
    )
    changed["records"][0]["content"]["text"] = "Conflicting content."
    changed["record_digests"] = [
        MemoryRecord.from_dict(changed["records"][0]).digest()
    ]

    proposal = TransactionProposal.from_dict(changed)
    with pytest.raises(RecordIdConflictError, match="record_id"):
        store.validate_record_id_population(proposal)
    with pytest.raises(RecordIdConflictError, match="record_id"):
        store.commit(proposal)

    assert len(list(store.iter_committed_records())) == 1
    assert len(tuple((store.root / "transactions" / "receipts").glob("*.json"))) == 1


def test_duplicate_record_id_inside_one_transaction_is_rejected(tmp_path: Path):
    first = record("rec-duplicate")
    second = deepcopy(first)
    second["content"]["text"] = "Second conflicting body."
    proposal = TransactionProposal.from_dict(
        {
            "transaction_version": "mneme.transaction/0.1",
            "transaction_id": "tx-duplicate",
            "expected_source_head": "GENESIS",
            "declared_record_count": 2,
            "record_digests": [
                MemoryRecord.from_dict(first).digest(),
                MemoryRecord.from_dict(second).digest(),
            ],
            "records": [first, second],
            "authority_ref": "synthetic-authority:test",
            "commit_marker": "MNEME_COMMIT/0.1",
        }
    )

    with pytest.raises(RecordIdConflictError, match="record_id"):
        MemoryStore(tmp_path / "memory.mlfdir").commit(proposal)

    transaction_root = tmp_path / "memory.mlfdir" / "transactions"
    assert not tuple((transaction_root / "committed").glob("*.json"))
    assert not tuple((transaction_root / "receipts").glob("*.json"))
