from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .canonical import canonical_json_bytes, sha256_domain
from .errors import RecordValidationError

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "memory-record-0.1.schema.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
_VALIDATOR = Draft202012Validator(_SCHEMA)


def _error_key(error) -> tuple[str, ...]:
    return tuple(str(part) for part in error.absolute_path)


@dataclass(frozen=True)
class MemoryRecord:
    _raw: dict[str, Any]

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "MemoryRecord":
        candidate = deepcopy(raw)
        errors = sorted(_VALIDATOR.iter_errors(candidate), key=_error_key)
        if errors:
            error = errors[0]
            path = ".".join(str(part) for part in error.absolute_path) or "$"
            raise RecordValidationError(f"{path}: {error.message}")
        return cls(candidate)

    def to_dict(self) -> dict[str, object]:
        return deepcopy(self._raw)

    def digest(self) -> str:
        return sha256_domain(b"MNEME-RECORD-0.1", canonical_json_bytes(self._raw))
