import pytest

from mneme.records import MemoryRecord
from mneme.errors import RecordValidationError


def valid_record():
    return {
        "record_version": "mneme.memory-record/0.1",
        "record_id": "rec-001",
        "record_type": "lesson",
        "scope": {"kind": "global", "subject": "verification"},
        "content": {"text": "A verifier must itself be validated."},
        "relations": [],
        "provenance": {"event_id": "evt-001", "source_ref": "synthetic:test"},
        "status": "active",
    }


def test_record_round_trip_and_digest_are_deterministic():
    first = MemoryRecord.from_dict(valid_record())
    second = MemoryRecord.from_dict(dict(reversed(list(valid_record().items()))))
    assert first.to_dict() == second.to_dict()
    assert first.digest() == second.digest()
    assert len(first.digest()) == 64


def test_unknown_record_type_is_rejected():
    raw = valid_record()
    raw["record_type"] = "invented"
    with pytest.raises(RecordValidationError):
        MemoryRecord.from_dict(raw)


def test_missing_provenance_is_rejected():
    raw = valid_record()
    del raw["provenance"]
    with pytest.raises(RecordValidationError):
        MemoryRecord.from_dict(raw)
