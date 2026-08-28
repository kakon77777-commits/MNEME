from copy import deepcopy

import pytest

from mneme.cps.models import (
    AssessmentMethod,
    PersistenceAssessment,
    PersistenceCandidate,
    ReviewState,
    RiskClass,
    deterministic_assessment_id,
)
from mneme.errors import CpsValidationError


def base_assessment():
    return {
        "assessment_version": "mneme.persistence-assessment/0.1",
        "assessment_id": "pa-placeholder",
        "subject_refs": ["record-decision-1"],
        "candidate": "PRESERVE",
        "basis": {
            "method": "EXPLICIT_RULE",
            "deterministic": True,
            "reason_codes": ["EXPLICIT_DECISION"],
            "evidence_refs": ["record-decision-1"],
        },
        "required_preservations": ["record-decision-1"],
        "risk": "LOW",
        "review_state": "UNREVIEWED",
        "authority": False,
    }


def test_enums_match_cps_vocabulary():
    assert {item.value for item in PersistenceCandidate} == {
        "PRESERVE", "STRUCTURALIZE", "GENERATIZE", "RECOMPUTE", "DISCARD", "UNKNOWN"
    }
    assert {item.value for item in AssessmentMethod} == {
        "EXPLICIT_RULE", "STRUCTURAL_RULE", "MODEL_PROPOSAL", "HUMAN_REVIEW"
    }
    assert {item.value for item in RiskClass} == {"LOW", "MEDIUM", "HIGH", "BLOCKED"}
    assert {item.value for item in ReviewState} == {
        "UNREVIEWED", "ACCEPTED_FOR_EXPERIMENT", "REJECTED", "SUPERSEDED"
    }


def test_assessment_requires_authority_false():
    raw = base_assessment()
    raw["authority"] = True
    with pytest.raises(CpsValidationError):
        PersistenceAssessment.from_dict(raw)


def test_deterministic_assessment_fingerprint_ignores_assessment_id_only():
    a = base_assessment()
    b = deepcopy(a)
    b["assessment_id"] = "different-id"
    assert PersistenceAssessment.from_dict(a).fingerprint() == PersistenceAssessment.from_dict(b).fingerprint()


def test_fingerprint_changes_when_candidate_changes():
    a = base_assessment()
    b = deepcopy(a)
    b["candidate"] = "UNKNOWN"
    b["risk"] = "BLOCKED"
    assert PersistenceAssessment.from_dict(a).fingerprint() != PersistenceAssessment.from_dict(b).fingerprint()


def test_assessment_roundtrip_is_deep_copied():
    raw = base_assessment()
    model = PersistenceAssessment.from_dict(raw)
    raw["subject_refs"].append("mutated")
    out = model.to_dict()
    assert out["subject_refs"] == ["record-decision-1"]
    out["subject_refs"].append("mutated-again")
    assert model.to_dict()["subject_refs"] == ["record-decision-1"]


def test_deterministic_assessment_id_is_stable_and_content_sensitive():
    raw = base_assessment()
    raw.pop("assessment_id")
    a = deterministic_assessment_id(raw)
    b = deterministic_assessment_id(deepcopy(raw))
    assert a == b
    assert a.startswith("pa-") and len(a) == 67
    changed = deepcopy(raw)
    changed["candidate"] = "UNKNOWN"
    changed["risk"] = "BLOCKED"
    assert deterministic_assessment_id(changed) != a


@pytest.mark.parametrize(
    "mutator",
    [
        lambda r: r.__setitem__("candidate", "DELETE"),
        lambda r: r["basis"].__setitem__("method", "MAGIC"),
        lambda r: r.__setitem__("subject_refs", []),
        lambda r: r["basis"].__setitem__("reason_codes", []),
        lambda r: r.__setitem__("risk", "SAFE"),
        lambda r: r.__setitem__("review_state", "APPROVED"),
        lambda r: r.__setitem__("authority", True),
        lambda r: r.__setitem__("extra", "not allowed"),
    ],
)
def test_invalid_assessment_shapes_are_rejected(mutator):
    raw = base_assessment()
    mutator(raw)
    with pytest.raises(CpsValidationError):
        PersistenceAssessment.from_dict(raw)


def base_recomputation_reference():
    return {
        "reference_version": "mneme.recomputation-reference/0.1",
        "reference_id": "rr-x",
        "source_kind": "web",
        "source_ref": "synthetic://source/current-version",
        "query_or_operation": "fetch-current-version",
        "freshness_requirement": "before-use",
        "previous_observation_ref": "record-version-1",
        "failure_policy": "FAIL_CLOSED",
        "authority": False,
    }


def base_equivalence_contract():
    return {
        "contract_version": "mneme.equivalence-contract/0.1",
        "contract_id": "eq-x",
        "observation_surfaces": [
            {"kind": "DECISION_MUST_NOT_REVERSE", "subject_ref": "record-decision-1"},
            {"kind": "AUTHORITY_MUST_NOT_ESCALATE", "subject_ref": "record-authority-1"},
        ],
        "forbidden_equalities": ["TOKEN_EQUALITY", "TRACE_EQUALITY"],
        "authority": False,
    }


def test_recompute_requires_freshness_and_failure_policy():
    from mneme.cps.models import RecomputationReference

    model = RecomputationReference.from_dict(base_recomputation_reference())
    assert model.to_dict()["freshness_requirement"] == "before-use"
    assert len(model.fingerprint()) == 64


def test_equivalence_contract_uses_observation_surfaces_not_token_equality():
    from mneme.cps.models import EquivalenceContract

    contract = EquivalenceContract.from_dict(base_equivalence_contract())
    assert "TOKEN_EQUALITY" in contract.to_dict()["forbidden_equalities"]
    assert len(contract.fingerprint()) == 64


def test_recomputation_previous_observation_ref_may_be_null():
    from mneme.cps.models import RecomputationReference

    raw = base_recomputation_reference()
    raw["previous_observation_ref"] = None
    assert RecomputationReference.from_dict(raw).to_dict()["previous_observation_ref"] is None


@pytest.mark.parametrize("field", ["freshness_requirement", "failure_policy"])
def test_recomputation_rejects_missing_or_empty_safety_semantics(field):
    from mneme.cps.models import RecomputationReference

    raw = base_recomputation_reference()
    raw[field] = ""
    with pytest.raises(CpsValidationError):
        RecomputationReference.from_dict(raw)


def test_recomputation_rejects_authority_true():
    from mneme.cps.models import RecomputationReference

    raw = base_recomputation_reference()
    raw["authority"] = True
    with pytest.raises(CpsValidationError):
        RecomputationReference.from_dict(raw)


def test_equivalence_rejects_unknown_observation_kind_and_authority():
    from mneme.cps.models import EquivalenceContract

    raw = base_equivalence_contract()
    raw["observation_surfaces"][0]["kind"] = "SAME_WORDS"
    with pytest.raises(CpsValidationError):
        EquivalenceContract.from_dict(raw)
    raw = base_equivalence_contract()
    raw["authority"] = True
    with pytest.raises(CpsValidationError):
        EquivalenceContract.from_dict(raw)


def test_equivalence_contract_is_deterministic_and_id_independent():
    from mneme.cps.models import EquivalenceContract

    a = base_equivalence_contract()
    b = deepcopy(a)
    b["contract_id"] = "eq-other"
    assert EquivalenceContract.from_dict(a).fingerprint() == EquivalenceContract.from_dict(b).fingerprint()
