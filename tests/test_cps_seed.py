import pytest

from mneme.cps.factorization import build_factorization_proposal
from mneme.cps.models import EquivalenceContract, RecomputationReference
from mneme.cps.rules import AssessmentContext, assess_record
from mneme.cps.seed import CognitiveSeedProposal, build_cognitive_seed_proposal
from mneme.errors import CpsValidationError
from mneme.records import MemoryRecord


def record(record_id):
    return MemoryRecord.from_dict({
        "record_version": "mneme.memory-record/0.1",
        "record_id": record_id,
        "record_type": "lesson",
        "scope": {"kind": "method", "subject": "synthetic"},
        "content": {"text": "Synthetic cognition."},
        "relations": [],
        "provenance": {"event_id": f"event-{record_id}", "source_ref": f"synthetic:{record_id}"},
        "status": "active",
    })


def eq_contract():
    return EquivalenceContract.from_dict({
        "contract_version": "mneme.equivalence-contract/0.1",
        "contract_id": "eq-synthetic",
        "observation_surfaces": [
            {"kind": "ANCHOR_MUST_MATCH", "subject_ref": "r-a"},
            {"kind": "AUTHORITY_MUST_NOT_ESCALATE", "subject_ref": "r-a"},
        ],
        "forbidden_equalities": ["TOKEN_EQUALITY", "TRACE_EQUALITY"],
        "authority": False,
    })


def recompute_ref():
    return RecomputationReference.from_dict({
        "reference_version": "mneme.recomputation-reference/0.1",
        "reference_id": "rr-current",
        "source_kind": "synthetic",
        "source_ref": "synthetic://current",
        "query_or_operation": "read-current",
        "freshness_requirement": "before-use",
        "previous_observation_ref": "r-a",
        "failure_policy": "FAIL_CLOSED",
        "authority": False,
    })


def generative_factorization():
    assessment = assess_record(
        record("r-a"),
        AssessmentContext(
            derivable_explanation=True,
            reconstruction_recipe_ref="synthetic://recipe/1",
            obligation_set_ref="synthetic://obligation/core",
        ),
    )
    return build_factorization_proposal(
        assessments=[assessment],
        source_refs=["r-a"],
        anchors=["r-a"],
        structure=[{"relation": "depends_on", "source_ref": "r-a", "target_ref": "r-b"}],
        generators=[{"kind": "RECONSTRUCTION_RECIPE", "generator_ref": "synthetic://recipe/1"}],
        obligations=[{"kind": "ANCHOR_MUST_MATCH", "subject_ref": "r-a"}],
        provenance_refs=["r-a"],
        recompute_refs=["rr-current"],
        unresolved_refs=[],
    )


def test_high_risk_seed_requires_anchor_and_equivalence_contract():
    with pytest.raises(CpsValidationError):
        build_cognitive_seed_proposal(
            factorization=generative_factorization(),
            anchors=[],
            structure=[{"relation": "depends_on", "source_ref": "r-a", "target_ref": "r-b"}],
            generators=[{"kind": "RECONSTRUCTION_RECIPE", "generator_ref": "synthetic://recipe/1"}],
            obligations=[{"kind": "ANCHOR_MUST_MATCH", "subject_ref": "r-a"}],
            provenance_refs=["r-a"],
            recomputation_refs=[recompute_ref()],
            unresolved_components=[],
            equivalence_contract=None,
        )


def test_seed_requires_all_factorization_anchors_and_provenance():
    f = generative_factorization()
    with pytest.raises(CpsValidationError):
        build_cognitive_seed_proposal(
            factorization=f,
            anchors=[],
            structure=f.to_dict()["structure"],
            generators=f.to_dict()["generators"],
            obligations=f.to_dict()["obligations"],
            provenance_refs=["r-a"],
            recomputation_refs=[recompute_ref()],
            unresolved_components=[],
            equivalence_contract=eq_contract(),
        )


def test_unknown_recomputation_reference_is_rejected():
    f = generative_factorization()
    with pytest.raises(CpsValidationError):
        build_cognitive_seed_proposal(
            factorization=f,
            anchors=["r-a"],
            structure=f.to_dict()["structure"],
            generators=f.to_dict()["generators"],
            obligations=f.to_dict()["obligations"],
            provenance_refs=["r-a"],
            recomputation_refs=[],
            unresolved_components=[],
            equivalence_contract=eq_contract(),
        )


def test_valid_seed_is_deterministic_and_non_authoritative():
    f = generative_factorization()
    kwargs = dict(
        factorization=f,
        anchors=["r-a"],
        structure=f.to_dict()["structure"],
        generators=f.to_dict()["generators"],
        obligations=f.to_dict()["obligations"],
        provenance_refs=["r-a"],
        recomputation_refs=[recompute_ref()],
        unresolved_components=[],
        equivalence_contract=eq_contract(),
    )
    a = build_cognitive_seed_proposal(**kwargs)
    b = build_cognitive_seed_proposal(**kwargs)
    raw = a.to_dict()
    assert raw == b.to_dict()
    assert raw["authority"] is False
    assert raw["seed_fingerprint"] == a.fingerprint()
    assert raw["source_factorization"] == f.to_dict()["proposal_id"]
    assert raw["equivalence_contract"] == "eq-synthetic"


def test_seed_shape_rejects_authority_grant():
    f = generative_factorization()
    seed = build_cognitive_seed_proposal(
        factorization=f,
        anchors=["r-a"], structure=f.to_dict()["structure"], generators=f.to_dict()["generators"],
        obligations=f.to_dict()["obligations"], provenance_refs=["r-a"],
        recomputation_refs=[recompute_ref()], unresolved_components=[], equivalence_contract=eq_contract(),
    )
    raw = seed.to_dict()
    raw["authority"] = True
    with pytest.raises(CpsValidationError):
        CognitiveSeedProposal.from_dict(raw)


def test_unresolved_factorization_refs_must_remain_explicit_or_be_resolved():
    assessment = assess_record(record("r-u"), AssessmentContext())
    f = build_factorization_proposal(
        assessments=[assessment], source_refs=["r-u"], anchors=[], structure=[], generators=[], obligations=[],
        provenance_refs=[], recompute_refs=[], unresolved_refs=["r-u"]
    )
    with pytest.raises(CpsValidationError):
        build_cognitive_seed_proposal(
            factorization=f, anchors=[], structure=[], generators=[], obligations=[], provenance_refs=[],
            recomputation_refs=[], unresolved_components=[], equivalence_contract=None
        )
    seed = build_cognitive_seed_proposal(
        factorization=f, anchors=[], structure=[], generators=[], obligations=[], provenance_refs=[],
        recomputation_refs=[], unresolved_components=["r-u"], equivalence_contract=None
    )
    assert seed.to_dict()["unresolved_components"] == ["r-u"]
