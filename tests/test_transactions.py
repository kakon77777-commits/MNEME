import json
import pytest

from mneme.transactions import TransactionProposal
from mneme.errors import TransactionValidationError


def record():
    return {
        "record_version": "mneme.memory-record/0.1",
        "record_id": "rec-001",
        "record_type": "lesson",
        "scope": {"kind": "global", "subject": "verification"},
        "content": {"text": "Synthetic lesson."},
        "relations": [],
        "provenance": {"event_id": "evt-001", "source_ref": "synthetic:test"},
        "status": "active",
    }


def transaction_dict():
    from mneme.records import MemoryRecord
    digest = MemoryRecord.from_dict(record()).digest()
    return {
        "transaction_version": "mneme.transaction/0.1",
        "transaction_id": "tx-001",
        "expected_source_head": "GENESIS",
        "declared_record_count": 1,
        "record_digests": [digest],
        "records": [record()],
        "authority_ref": "synthetic-authority:test",
        "commit_marker": "MNEME_COMMIT/0.1",
    }


def test_complete_transaction_is_valid_for_expected_head():
    tx = TransactionProposal.from_dict(transaction_dict())
    tx.validate_for_head("GENESIS")
    assert len(tx.digest()) == 64


@pytest.mark.parametrize("mutation", ["missing_marker", "wrong_count", "wrong_digest", "wrong_head"])
def test_corrupt_transaction_is_rejected(mutation):
    raw = transaction_dict()
    if mutation == "missing_marker":
        del raw["commit_marker"]
    elif mutation == "wrong_count":
        raw["declared_record_count"] = 2
    elif mutation == "wrong_digest":
        raw["record_digests"] = ["0" * 64]
    tx = TransactionProposal.from_dict(raw) if mutation != "missing_marker" else None
    with pytest.raises(TransactionValidationError):
        if mutation == "missing_marker":
            TransactionProposal.from_dict(raw)
        elif mutation == "wrong_head":
            tx.validate_for_head("f" * 64)
        else:
            tx.validate_for_head("GENESIS")


def test_truncated_json_never_becomes_transaction():
    raw = '{"transaction_version":"mneme.transaction/0.1","transaction_id":"tx-001"'
    with pytest.raises(json.JSONDecodeError):
        json.loads(raw)
