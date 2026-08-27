from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .canonical import canonical_json_bytes, sha256_domain
from .errors import RecordValidationError, TransactionValidationError
from .records import MemoryRecord

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "transaction-0.1.schema.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
_VALIDATOR = Draft202012Validator(_SCHEMA)


def _error_key(error) -> tuple[str, ...]:
    return tuple(str(part) for part in error.absolute_path)


@dataclass(frozen=True)
class TransactionProposal:
    _raw: dict[str, Any]

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "TransactionProposal":
        candidate = deepcopy(raw)
        errors = sorted(_VALIDATOR.iter_errors(candidate), key=_error_key)
        if errors:
            error = errors[0]
            path = ".".join(str(part) for part in error.absolute_path) or "$"
            raise TransactionValidationError(f"{path}: {error.message}")
        return cls(candidate)

    def to_dict(self) -> dict[str, object]:
        return deepcopy(self._raw)

    def digest(self) -> str:
        return sha256_domain(b"MNEME-TX-0.1", canonical_json_bytes(self._raw))

    def validate_for_head(self, actual_head: str) -> None:
        expected_head = self._raw["expected_source_head"]
        if expected_head != actual_head:
            raise TransactionValidationError(
                f"expected_source_head {expected_head!r} does not match actual head {actual_head!r}"
            )

        records = self._raw["records"]
        digests = self._raw["record_digests"]
        declared_count = self._raw["declared_record_count"]
        if declared_count != len(records) or declared_count != len(digests):
            raise TransactionValidationError(
                "declared_record_count must equal both records and record_digests lengths"
            )

        for index, (raw_record, declared_digest) in enumerate(zip(records, digests, strict=True)):
            try:
                actual_digest = MemoryRecord.from_dict(raw_record).digest()
            except RecordValidationError as exc:
                raise TransactionValidationError(f"records.{index}: {exc}") from exc
            if actual_digest != declared_digest:
                raise TransactionValidationError(f"record_digests.{index}: digest mismatch")

        authority_ref = self._raw["authority_ref"]
        if not isinstance(authority_ref, str) or not authority_ref:
            raise TransactionValidationError("authority_ref must be a non-empty string")

        if self._raw["commit_marker"] != "MNEME_COMMIT/0.1":
            raise TransactionValidationError("commit_marker is not exact")
