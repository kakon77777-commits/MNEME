from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from ..canonical import canonical_json_bytes, sha256_domain
from ..errors import CpsValidationError

_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "persistence-assessment-0.1.schema.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
_VALIDATOR = Draft202012Validator(_SCHEMA)


class PersistenceCandidate(str, Enum):
    PRESERVE = "PRESERVE"
    STRUCTURALIZE = "STRUCTURALIZE"
    GENERATIZE = "GENERATIZE"
    RECOMPUTE = "RECOMPUTE"
    DISCARD = "DISCARD"
    UNKNOWN = "UNKNOWN"


class AssessmentMethod(str, Enum):
    EXPLICIT_RULE = "EXPLICIT_RULE"
    STRUCTURAL_RULE = "STRUCTURAL_RULE"
    MODEL_PROPOSAL = "MODEL_PROPOSAL"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class RiskClass(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    BLOCKED = "BLOCKED"


class ReviewState(str, Enum):
    UNREVIEWED = "UNREVIEWED"
    ACCEPTED_FOR_EXPERIMENT = "ACCEPTED_FOR_EXPERIMENT"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


def _error_key(error) -> tuple[str, ...]:
    return tuple(str(part) for part in error.absolute_path)


def _validate(raw: dict[str, object]) -> dict[str, Any]:
    candidate = deepcopy(raw)
    errors = sorted(_VALIDATOR.iter_errors(candidate), key=_error_key)
    if errors:
        error = errors[0]
        path = ".".join(str(part) for part in error.absolute_path) or "$"
        raise CpsValidationError(f"{path}: {error.message}")
    return candidate


def deterministic_assessment_id(assessment_without_id: dict[str, object]) -> str:
    candidate = deepcopy(assessment_without_id)
    candidate.pop("assessment_id", None)
    digest = sha256_domain(
        b"MNEME-CPS-ASSESSMENT-ID-0.1",
        canonical_json_bytes(candidate),
    )
    return "pa-" + digest


@dataclass(frozen=True)
class PersistenceAssessment:
    _raw: dict[str, Any]

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "PersistenceAssessment":
        return cls(_validate(raw))

    def to_dict(self) -> dict[str, object]:
        return deepcopy(self._raw)

    def fingerprint(self) -> str:
        payload = self.to_dict()
        payload.pop("assessment_id", None)
        return sha256_domain(
            b"MNEME-CPS-ASSESSMENT-0.1",
            canonical_json_bytes(payload),
        )

_RECOMPUTATION_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "recomputation-reference-0.1.schema.json"
_RECOMPUTATION_VALIDATOR = Draft202012Validator(json.loads(_RECOMPUTATION_SCHEMA_PATH.read_text(encoding="utf-8")))
_EQUIVALENCE_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "equivalence-contract-0.1.schema.json"
_EQUIVALENCE_VALIDATOR = Draft202012Validator(json.loads(_EQUIVALENCE_SCHEMA_PATH.read_text(encoding="utf-8")))


def _validate_with(validator: Draft202012Validator, raw: dict[str, object]) -> dict[str, Any]:
    candidate = deepcopy(raw)
    errors = sorted(validator.iter_errors(candidate), key=_error_key)
    if errors:
        error = errors[0]
        path = ".".join(str(part) for part in error.absolute_path) or "$"
        raise CpsValidationError(f"{path}: {error.message}")
    return candidate


@dataclass(frozen=True)
class RecomputationReference:
    _raw: dict[str, Any]

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "RecomputationReference":
        return cls(_validate_with(_RECOMPUTATION_VALIDATOR, raw))

    def to_dict(self) -> dict[str, object]:
        return deepcopy(self._raw)

    def fingerprint(self) -> str:
        payload = self.to_dict()
        payload.pop("reference_id", None)
        return sha256_domain(
            b"MNEME-CPS-RECOMPUTATION-0.1",
            canonical_json_bytes(payload),
        )


@dataclass(frozen=True)
class EquivalenceContract:
    _raw: dict[str, Any]

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "EquivalenceContract":
        return cls(_validate_with(_EQUIVALENCE_VALIDATOR, raw))

    def to_dict(self) -> dict[str, object]:
        return deepcopy(self._raw)

    def fingerprint(self) -> str:
        payload = self.to_dict()
        payload.pop("contract_id", None)
        return sha256_domain(
            b"MNEME-CPS-EQUIVALENCE-0.1",
            canonical_json_bytes(payload),
        )
