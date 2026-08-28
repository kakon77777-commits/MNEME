from __future__ import annotations

from dataclasses import asdict, dataclass
from collections import defaultdict
from typing import Mapping

from ..cps.adapter import CpsObservationAdapter
from ..cps.models import PersistenceAssessment
from ..errors import DryRunValidationError
from ..records import MemoryRecord
from .models import ContextResolution, MappedRecordMetadata
from .policy import PersistencePolicy, resolve_contexts

_READINESS = {
    "PRESERVE": "PRESERVE_ONLY",
    "STRUCTURALIZE": "READY_FOR_STRUCTURAL_REVIEW",
    "GENERATIZE": "READY_FOR_GENERATIVE_REVIEW",
    "RECOMPUTE": "READY_FOR_RECOMPUTE_REVIEW",
    "DISCARD": "DISCARD_REQUIRES_REVIEW",
    "UNKNOWN": "UNRESOLVED",
}


@dataclass(frozen=True)
class FactorizationReadiness:
    record_id: str
    state: str
    assessment_id: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RecomputeReadiness:
    record_id: str
    state: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PersistencePassResult:
    assessments: tuple[PersistenceAssessment, ...]
    resolutions: tuple[ContextResolution, ...]
    factorization_readiness: tuple[FactorizationReadiness, ...]
    recompute_readiness: tuple[RecomputeReadiness, ...]
    evidential_floor: dict[str, tuple[str, ...]]


def readiness_for(assessment: PersistenceAssessment) -> FactorizationReadiness:
    raw = assessment.to_dict()
    candidate = str(raw["candidate"])
    return FactorizationReadiness(
        record_id=str(raw["subject_refs"][0]),
        state=_READINESS[candidate],
        assessment_id=str(raw["assessment_id"]),
    )


def run_persistence_pass(
    records: tuple[MemoryRecord, ...],
    metadata: tuple[MappedRecordMetadata, ...],
    *,
    policy: PersistencePolicy | None = None,
    exact_overrides: Mapping[str, Mapping[str, object]] | None = None,
) -> PersistencePassResult:
    record_ids = [str(record.to_dict()["record_id"]) for record in records]
    metadata_ids = [item.record_id for item in metadata]
    if len(record_ids) != len(set(record_ids)):
        raise DryRunValidationError("duplicate PASS 2 record_id")
    if len(metadata_ids) != len(set(metadata_ids)):
        raise DryRunValidationError("duplicate PASS 1 metadata record_id")
    if set(record_ids) != set(metadata_ids):
        raise DryRunValidationError("PASS 2 record set must exactly equal PASS 1 mapped metadata set")

    resolved = resolve_contexts(metadata, policy=policy, exact_overrides=exact_overrides)
    resolution_by_id = {item.record_id: item for item in resolved}
    ordered_resolutions = tuple(resolution_by_id[record_id] for record_id in record_ids)
    assessments = CpsObservationAdapter().assess(records, tuple(item.context for item in ordered_resolutions))
    readiness = tuple(readiness_for(assessment) for assessment in assessments)
    recompute = tuple(
        RecomputeReadiness(
            record_id=str(assessment.to_dict()["subject_refs"][0]),
            state="RECOMPUTE_CANDIDATE" if assessment.to_dict()["candidate"] == "RECOMPUTE" else "NOT_RECOMPUTE",
        )
        for assessment in assessments
    )
    floor: dict[str, list[str]] = defaultdict(list)
    for assessment in assessments:
        raw = assessment.to_dict()
        assessment_id = str(raw["assessment_id"])
        for ref in raw["required_preservations"]:
            if assessment_id not in floor[str(ref)]:
                floor[str(ref)].append(assessment_id)
    canonical_floor = {ref: tuple(sorted(ids)) for ref, ids in sorted(floor.items())}
    return PersistencePassResult(
        assessments=assessments,
        resolutions=ordered_resolutions,
        factorization_readiness=readiness,
        recompute_readiness=recompute,
        evidential_floor=canonical_floor,
    )
