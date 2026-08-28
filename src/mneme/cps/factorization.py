from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator

from ..canonical import canonical_json_bytes, sha256_domain
from ..errors import CpsValidationError
from .models import PersistenceAssessment

_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "factorization-proposal-0.1.schema.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
_VALIDATOR = Draft202012Validator(_SCHEMA)


def _error_key(error) -> tuple[str, ...]:
    return tuple(str(part) for part in error.absolute_path)


def _validate_component_traceability(raw: dict[str, object]) -> None:
    memory_refs = (
        {str(x) for x in raw["source_refs"]}
        | {str(x) for x in raw["anchors"]}
        | {str(x) for x in raw["provenance_refs"]}
        | {str(x) for x in raw["unresolved_refs"]}
    )
    assessment_refs = {str(x) for x in raw["source_assessments"]}
    recompute_refs = {str(x) for x in raw["recompute_refs"]}

    trace_specs = {
        "source_ref": memory_refs,
        "provenance_ref": {str(x) for x in raw["provenance_refs"]},
        "assessment_ref": assessment_refs,
        "recompute_ref": recompute_refs,
    }
    for family in ("structure", "generators", "obligations"):
        for index, component in enumerate(raw[family]):
            if not isinstance(component, dict):
                raise CpsValidationError(f"{family}.{index}: component must be an object")
            present = [key for key in trace_specs if key in component]
            if not present:
                raise CpsValidationError(
                    f"{family}.{index}: factorized component lacks source/provenance/assessment/recompute trace reference"
                )
            for key in present:
                value = component[key]
                if not isinstance(value, str) or not value:
                    raise CpsValidationError(f"{family}.{index}.{key}: trace reference must be a non-empty string")
                if value not in trace_specs[key]:
                    raise CpsValidationError(f"{family}.{index}.{key}: unknown trace reference {value!r}")


@dataclass(frozen=True)
class FactorizationProposal:
    _raw: dict[str, Any]

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "FactorizationProposal":
        candidate = deepcopy(raw)
        errors = sorted(_VALIDATOR.iter_errors(candidate), key=_error_key)
        if errors:
            error = errors[0]
            path = ".".join(str(part) for part in error.absolute_path) or "$"
            raise CpsValidationError(f"{path}: {error.message}")
        _validate_component_traceability(candidate)
        return cls(candidate)

    def to_dict(self) -> dict[str, object]:
        return deepcopy(self._raw)

    def fingerprint(self) -> str:
        payload = self.to_dict()
        payload.pop("proposal_id", None)
        return sha256_domain(
            b"MNEME-CPS-FACTORIZATION-0.1",
            canonical_json_bytes(payload),
        )


def deterministic_factorization_id(proposal_without_id: dict[str, object]) -> str:
    payload = deepcopy(proposal_without_id)
    payload.pop("proposal_id", None)
    return "fp-" + sha256_domain(
        b"MNEME-CPS-FACTORIZATION-ID-0.1",
        canonical_json_bytes(payload),
    )


def build_factorization_proposal(
    *,
    assessments: Iterable[PersistenceAssessment],
    source_refs: list[str],
    anchors: list[str],
    structure: list[dict[str, object]],
    generators: list[dict[str, object]],
    obligations: list[dict[str, object]],
    provenance_refs: list[str],
    recompute_refs: list[str],
    unresolved_refs: list[str],
) -> FactorizationProposal:
    assessment_list = list(assessments)
    if not assessment_list:
        raise CpsValidationError("at least one source assessment is required")

    source_assessment_ids = [str(a.to_dict()["assessment_id"]) for a in assessment_list]
    coverage = set(anchors) | set(provenance_refs) | set(unresolved_refs)

    required: set[str] = set()
    for assessment in assessment_list:
        required.update(str(ref) for ref in assessment.to_dict()["required_preservations"])
    missing_required = sorted(required - coverage)
    if missing_required:
        raise CpsValidationError(
            "required preservation omitted from evidential floor: " + ", ".join(missing_required)
        )

    missing_sources = sorted(set(source_refs) - coverage)
    if missing_sources:
        raise CpsValidationError(
            "source reference omitted from anchor/provenance/unresolved coverage: " + ", ".join(missing_sources)
        )

    without_id: dict[str, object] = {
        "proposal_version": "mneme.factorization-proposal/0.1",
        "source_assessments": source_assessment_ids,
        "source_refs": list(source_refs),
        "anchors": list(anchors),
        "structure": deepcopy(structure),
        "generators": deepcopy(generators),
        "obligations": deepcopy(obligations),
        "provenance_refs": list(provenance_refs),
        "recompute_refs": list(recompute_refs),
        "unresolved_refs": list(unresolved_refs),
        "authority": False,
    }
    raw = {"proposal_id": deterministic_factorization_id(without_id), **without_id}
    proposal = FactorizationProposal.from_dict(raw)
    validate_factorization_sources(proposal, assessment_list)
    return proposal


def validate_factorization_sources(
    proposal: FactorizationProposal,
    assessments: Iterable[PersistenceAssessment],
) -> None:
    known = {str(a.to_dict()["assessment_id"]) for a in assessments}
    referenced = {str(x) for x in proposal.to_dict()["source_assessments"]}
    unknown = sorted(referenced - known)
    if unknown:
        raise CpsValidationError("unknown source assessment reference: " + ", ".join(unknown))
