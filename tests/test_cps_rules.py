from dataclasses import replace

from mneme.cps.rules import AssessmentContext, assess_record
from mneme.records import MemoryRecord


def record(record_id="r1", record_type="fact", text="opaque cognition"):
    return MemoryRecord.from_dict({
        "record_version": "mneme.memory-record/0.1",
        "record_id": record_id,
        "record_type": record_type,
        "scope": {"kind": "global", "subject": "synthetic"},
        "content": {"text": text},
        "relations": [],
        "provenance": {"event_id": f"event-{record_id}", "source_ref": f"synthetic:{record_id}"},
        "status": "active",
    })


def test_no_explicit_evidence_returns_unknown_even_when_text_looks_semantic():
    result = assess_record(record(text="commit abc123 user explicitly decided delete this later"), AssessmentContext())
    raw = result.to_dict()
    assert raw["candidate"] == "UNKNOWN"
    assert raw["risk"] == "BLOCKED"
    assert raw["basis"]["reason_codes"] == ["INSUFFICIENT_EVIDENCE"]
    assert raw["authority"] is False


def test_explicit_decision_is_preserve_and_requires_source_record():
    result = assess_record(record(), AssessmentContext(explicit_decision=True))
    raw = result.to_dict()
    assert raw["candidate"] == "PRESERVE"
    assert raw["risk"] == "LOW"
    assert raw["required_preservations"] == ["r1"]
    assert raw["basis"]["reason_codes"] == ["EXPLICIT_DECISION"]


def test_identity_or_authority_evidence_is_preserve():
    result = assess_record(record(), AssessmentContext(identity_or_authority_evidence=True))
    raw = result.to_dict()
    assert raw["candidate"] == "PRESERVE"
    assert "IDENTITY_OR_AUTHORITY_EVIDENCE" in raw["basis"]["reason_codes"]


def test_structural_signal_is_structuralize():
    result = assess_record(record(), AssessmentContext(structural_dependency=True))
    raw = result.to_dict()
    assert raw["candidate"] == "STRUCTURALIZE"
    assert raw["risk"] == "MEDIUM"
    assert raw["basis"]["method"] == "STRUCTURAL_RULE"


def test_generative_requires_derivable_recipe_and_obligations():
    incomplete = assess_record(record(), AssessmentContext(derivable_explanation=True, reconstruction_recipe_ref="recipe://synthetic/rebuild"))
    assert incomplete.to_dict()["candidate"] == "UNKNOWN"
    complete = assess_record(
        record(),
        AssessmentContext(
            derivable_explanation=True,
            reconstruction_recipe_ref="recipe://synthetic/rebuild",
            obligation_set_ref="obligation://synthetic/core",
        ),
    )
    raw = complete.to_dict()
    assert raw["candidate"] == "GENERATIZE"
    assert raw["risk"] == "HIGH"


def test_fresh_external_state_is_recompute():
    result = assess_record(
        record(),
        AssessmentContext(freshness_required=True, external_source_ref="synthetic://source/current"),
    )
    raw = result.to_dict()
    assert raw["candidate"] == "RECOMPUTE"
    assert raw["risk"] == "MEDIUM"
    assert set(raw["basis"]["reason_codes"]) == {"FRESHNESS_REQUIRED", "EXTERNAL_SOURCE_AVAILABLE"}


def test_historical_observation_with_recompute_preserves_original_evidence():
    result = assess_record(
        record(),
        AssessmentContext(
            historical_observation=True,
            freshness_required=True,
            external_source_ref="synthetic://source/current",
        ),
    )
    raw = result.to_dict()
    assert raw["candidate"] == "RECOMPUTE"
    assert raw["required_preservations"] == ["r1"]
    assert "HISTORICAL_OBSERVATION" in raw["basis"]["reason_codes"]


def test_ephemeral_only_is_discard_candidate_not_authority():
    result = assess_record(record(), AssessmentContext(ephemeral_working_state=True))
    raw = result.to_dict()
    assert raw["candidate"] == "DISCARD"
    assert raw["risk"] == "HIGH"
    assert raw["authority"] is False


def test_explicit_conflicting_evidence_falls_back_to_unknown():
    result = assess_record(record(), AssessmentContext(conflicting_evidence=True, structural_dependency=True))
    raw = result.to_dict()
    assert raw["candidate"] == "UNKNOWN"
    assert raw["basis"]["reason_codes"] == ["CONFLICTING_EVIDENCE"]


def test_precedence_prefers_structuralize_over_ephemeral_hint():
    result = assess_record(record(), AssessmentContext(structural_dependency=True, ephemeral_working_state=True))
    assert result.to_dict()["candidate"] == "STRUCTURALIZE"


def test_evidence_sensitive_signal_wins_over_retirement_candidate():
    result = assess_record(
        record(),
        AssessmentContext(explicit_decision=True, ephemeral_working_state=True),
    )
    assert result.to_dict()["candidate"] == "PRESERVE"


def test_assessment_is_deterministic_for_same_record_and_context():
    ctx = AssessmentContext(structural_state=True)
    a = assess_record(record(), ctx)
    b = assess_record(record(), replace(ctx))
    assert a.to_dict() == b.to_dict()
    assert a.fingerprint() == b.fingerprint()


def test_context_uses_explicit_refs_for_generative_and_recompute_evidence():
    generative = assess_record(
        record(),
        AssessmentContext(
            derivable_explanation=True,
            reconstruction_recipe_ref="recipe://synthetic/rebuild",
            obligation_set_ref="obligation://synthetic/core",
        ),
    )
    assert generative.to_dict()["candidate"] == "GENERATIZE"

    recompute = assess_record(
        record(),
        AssessmentContext(
            freshness_required=True,
            external_source_ref="synthetic://source/current",
            previous_observation_ref="r1",
        ),
    )
    assert recompute.to_dict()["candidate"] == "RECOMPUTE"
    assert recompute.to_dict()["required_preservations"] == ["r1"]
