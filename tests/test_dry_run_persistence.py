from __future__ import annotations

import pytest

from mneme.cps.rules import AssessmentContext
from mneme.dry_run.models import MappedRecordMetadata
from mneme.dry_run.policy import PersistencePolicy
from mneme.dry_run.persistence import run_persistence_pass, readiness_for
from mneme.errors import DryRunValidationError
from mneme.records import MemoryRecord


CONTEXT_FIELDS = {
    "explicit_decision": False,
    "identity_or_authority_evidence": False,
    "historical_observation": False,
    "structural_dependency": False,
    "structural_state": False,
    "derivable_explanation": False,
    "reconstruction_recipe_ref": None,
    "obligation_set_ref": None,
    "freshness_required": False,
    "external_source_ref": None,
    "previous_observation_ref": None,
    "ephemeral_working_state": False,
    "superseded_materialization": False,
    "conflicting_evidence": False,
}

def context_dict(**changes):
    raw = dict(CONTEXT_FIELDS); raw.update(changes); return raw


def record(record_id):
    return MemoryRecord.from_dict({
        "record_version": "mneme.memory-record/0.1",
        "record_id": record_id,
        "record_type": "fact",
        "scope": {"kind": "global", "subject": "synthetic"},
        "content": {"text": "Synthetic source."},
        "relations": [],
        "provenance": {"event_id": f"event-{record_id}", "source_ref": f"synthetic:{record_id}"},
        "status": "active",
    })


def metadata(record_id, section_id="standing_instructions"):
    return MappedRecordMetadata(
        record_id=record_id,
        section_id=section_id,
        record_type="fact",
        scope_kind="global",
        scope_subject="synthetic",
        block_kind="unordered_list_item",
        route_hints=("route://global/tier0",),
        start_line=1,
        end_line=1,
        profile_id="evemiss-residence/0.1",
        profile_digest="0" * 64,
    )


def policy_for(selector, context, rule_id="r1"):
    return PersistencePolicy.from_dict({
        "policy_version": "mneme.persistence-policy/0.1",
        "policy_id": "synthetic/0.1",
        "rules": [{"rule_id": rule_id, "selector": selector, "context": context}],
    })


def test_pass2_requires_metadata_for_every_and_only_mapped_record():
    with pytest.raises(DryRunValidationError):
        run_persistence_pass((record("r1"), record("r2")), (metadata("r1"),))


def test_pass2_rejects_duplicate_record_or_metadata_ids():
    with pytest.raises(DryRunValidationError):
        run_persistence_pass((record("r1"), record("r1")), (metadata("r1"), metadata("r1")))


def test_pass2_produces_exactly_one_assessment_per_record():
    records = (record("r1"), record("r2"))
    metas = (metadata("r1"), metadata("r2", section_id="verification_lessons"))
    policy = policy_for({"section_id": "standing_instructions"}, context_dict(structural_state=True))
    result = run_persistence_pass(records, metas, policy=policy)
    assert len(result.assessments) == len(records)
    assert {a.to_dict()["subject_refs"][0] for a in result.assessments} == {"r1", "r2"}


def test_default_resolution_becomes_unknown():
    result = run_persistence_pass((record("r1"),), (metadata("r1"),))
    assert result.assessments[0].to_dict()["candidate"] == "UNKNOWN"
    assert result.resolutions[0].provenance == "DEFAULT_UNKNOWN"


def test_policy_conflict_becomes_unknown_blocked():
    raw = {
        "policy_version": "mneme.persistence-policy/0.1",
        "policy_id": "conflict/0.1",
        "rules": [
            {"rule_id": "a", "selector": {"record_type": "fact"}, "context": context_dict(structural_state=True)},
            {"rule_id": "b", "selector": {"scope_kind": "global"}, "context": context_dict(explicit_decision=True)},
        ],
    }
    result = run_persistence_pass((record("r1"),), (metadata("r1"),), policy=PersistencePolicy.from_dict(raw))
    assessed = result.assessments[0].to_dict()
    assert assessed["candidate"] == "UNKNOWN"
    assert assessed["risk"] == "BLOCKED"


@pytest.mark.parametrize("candidate,state", [
    ("PRESERVE", "PRESERVE_ONLY"),
    ("STRUCTURALIZE", "READY_FOR_STRUCTURAL_REVIEW"),
    ("GENERATIZE", "READY_FOR_GENERATIVE_REVIEW"),
    ("RECOMPUTE", "READY_FOR_RECOMPUTE_REVIEW"),
    ("DISCARD", "DISCARD_REQUIRES_REVIEW"),
    ("UNKNOWN", "UNRESOLVED"),
])
def test_readiness_mapping(candidate, state):
    from mneme.cps.models import PersistenceAssessment
    raw = {
        "assessment_version": "mneme.persistence-assessment/0.1",
        "assessment_id": f"pa-{candidate.lower()}",
        "subject_refs": ["r1"],
        "candidate": candidate,
        "basis": {"method": "EXPLICIT_RULE", "deterministic": True, "reason_codes": ["X"], "evidence_refs": ["r1"]},
        "required_preservations": [],
        "risk": "LOW" if candidate == "PRESERVE" else ("BLOCKED" if candidate == "UNKNOWN" else "MEDIUM"),
        "review_state": "UNREVIEWED",
        "authority": False,
    }
    item = readiness_for(PersistenceAssessment.from_dict(raw))
    assert item.state == state


def test_readiness_contains_no_generated_cognitive_components():
    result = run_persistence_pass(
        (record("r1"),), (metadata("r1"),),
        exact_overrides={"r1": context_dict(derivable_explanation=True, reconstruction_recipe_ref="recipe://1", obligation_set_ref="obligation://1")},
    )
    raw = result.factorization_readiness[0].to_dict()
    for forbidden in ("anchors", "structure", "generators", "obligations", "provenance_refs", "recompute_refs"):
        assert forbidden not in raw


def test_required_preservations_are_visible():
    result = run_persistence_pass(
        (record("r1"),), (metadata("r1"),),
        exact_overrides={"r1": context_dict(explicit_decision=True)},
    )
    assessment_id = result.assessments[0].to_dict()["assessment_id"]
    assert result.evidential_floor == {"r1": (assessment_id,)}


def test_recompute_candidate_reports_readiness_without_network():
    result = run_persistence_pass(
        (record("r1"),), (metadata("r1"),),
        exact_overrides={"r1": context_dict(
            historical_observation=True,
            freshness_required=True,
            external_source_ref="synthetic://current",
            previous_observation_ref="r1",
        )},
    )
    assert result.recompute_readiness[0].state == "RECOMPUTE_CANDIDATE"
