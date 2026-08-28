from __future__ import annotations

from dataclasses import dataclass

from ..records import MemoryRecord
from .models import PersistenceAssessment, deterministic_assessment_id


@dataclass(frozen=True)
class AssessmentContext:
    explicit_decision: bool = False
    identity_or_authority_evidence: bool = False
    historical_observation: bool = False
    structural_dependency: bool = False
    structural_state: bool = False
    derivable_explanation: bool = False
    reconstruction_recipe_ref: str | None = None
    obligation_set_ref: str | None = None
    freshness_required: bool = False
    external_source_ref: str | None = None
    previous_observation_ref: str | None = None
    ephemeral_working_state: bool = False
    superseded_materialization: bool = False
    conflicting_evidence: bool = False


def assess_record(record: MemoryRecord, context: AssessmentContext) -> PersistenceAssessment:
    record_id = str(record.to_dict()["record_id"])

    if context.conflicting_evidence:
        return _assessment(
            record_id,
            candidate="UNKNOWN",
            method="EXPLICIT_RULE",
            reasons=["CONFLICTING_EVIDENCE"],
            required_preservations=_preservation_refs(record_id, context),
            risk="BLOCKED",
        )

    if context.identity_or_authority_evidence:
        return _assessment(
            record_id,
            candidate="PRESERVE",
            method="EXPLICIT_RULE",
            reasons=["IDENTITY_OR_AUTHORITY_EVIDENCE"],
            required_preservations=[record_id],
            risk="LOW",
        )

    if context.explicit_decision:
        return _assessment(
            record_id,
            candidate="PRESERVE",
            method="EXPLICIT_RULE",
            reasons=["EXPLICIT_DECISION"],
            required_preservations=[record_id],
            risk="LOW",
        )

    if context.historical_observation and not context.freshness_required:
        return _assessment(
            record_id,
            candidate="PRESERVE",
            method="EXPLICIT_RULE",
            reasons=["HISTORICAL_OBSERVATION"],
            required_preservations=_preservation_refs(record_id, context),
            risk="LOW",
        )

    if context.freshness_required:
        if context.external_source_ref:
            reasons = ["FRESHNESS_REQUIRED", "EXTERNAL_SOURCE_AVAILABLE"]
            if context.historical_observation or context.previous_observation_ref:
                reasons.append("HISTORICAL_OBSERVATION")
            return _assessment(
                record_id,
                candidate="RECOMPUTE",
                method="STRUCTURAL_RULE",
                reasons=reasons,
                required_preservations=_preservation_refs(record_id, context),
                risk="MEDIUM",
            )
        return _unknown(record_id, context)

    if context.structural_dependency or context.structural_state:
        reasons = []
        if context.structural_dependency:
            reasons.append("STRUCTURAL_DEPENDENCY")
        if context.structural_state:
            reasons.append("STRUCTURAL_STATE")
        return _assessment(
            record_id,
            candidate="STRUCTURALIZE",
            method="STRUCTURAL_RULE",
            reasons=reasons,
            required_preservations=_preservation_refs(record_id, context),
            risk="MEDIUM",
        )

    if context.derivable_explanation:
        if context.reconstruction_recipe_ref and context.obligation_set_ref:
            return _assessment(
                record_id,
                candidate="GENERATIZE",
                method="STRUCTURAL_RULE",
                reasons=[
                    "DERIVABLE_EXPLANATION",
                    "RECONSTRUCTION_RECIPE_AVAILABLE",
                    "OBLIGATION_SET_AVAILABLE",
                ],
                required_preservations=_preservation_refs(record_id, context),
                risk="HIGH",
            )
        return _unknown(record_id, context)

    if context.ephemeral_working_state or context.superseded_materialization:
        reasons = []
        if context.ephemeral_working_state:
            reasons.append("EPHEMERAL_WORKING_STATE")
        if context.superseded_materialization:
            reasons.append("SUPERSEDED_MATERIALIZATION")
        return _assessment(
            record_id,
            candidate="DISCARD",
            method="STRUCTURAL_RULE",
            reasons=reasons,
            required_preservations=_preservation_refs(record_id, context),
            risk="HIGH",
        )

    return _unknown(record_id, context)


def _preservation_refs(record_id: str, context: AssessmentContext) -> list[str]:
    refs: list[str] = []
    if context.historical_observation:
        refs.append(record_id)
    if context.previous_observation_ref and context.previous_observation_ref not in refs:
        refs.append(context.previous_observation_ref)
    return refs


def _unknown(record_id: str, context: AssessmentContext) -> PersistenceAssessment:
    return _assessment(
        record_id,
        candidate="UNKNOWN",
        method="STRUCTURAL_RULE",
        reasons=["INSUFFICIENT_EVIDENCE"],
        required_preservations=_preservation_refs(record_id, context),
        risk="BLOCKED",
    )


def _assessment(
    record_id: str,
    *,
    candidate: str,
    method: str,
    reasons: list[str],
    required_preservations: list[str],
    risk: str,
) -> PersistenceAssessment:
    without_id: dict[str, object] = {
        "assessment_version": "mneme.persistence-assessment/0.1",
        "subject_refs": [record_id],
        "candidate": candidate,
        "basis": {
            "method": method,
            "deterministic": True,
            "reason_codes": reasons,
            "evidence_refs": [record_id],
        },
        "required_preservations": required_preservations,
        "risk": risk,
        "review_state": "UNREVIEWED",
        "authority": False,
    }
    raw = {"assessment_id": deterministic_assessment_id(without_id), **without_id}
    return PersistenceAssessment.from_dict(raw)
