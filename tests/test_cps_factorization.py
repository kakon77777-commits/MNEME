from copy import deepcopy

import pytest

from mneme.cps.factorization import (
    FactorizationProposal,
    build_factorization_proposal,
    validate_factorization_sources,
)
from mneme.cps.rules import AssessmentContext, assess_record
from mneme.errors import CpsValidationError
from mneme.records import MemoryRecord


def record(record_id="record-decision-1"):
    return MemoryRecord.from_dict({
        "record_version": "mneme.memory-record/0.1",
        "record_id": record_id,
        "record_type": "fact",
        "scope": {"kind": "global", "subject": "synthetic"},
        "content": {"text": "Synthetic evidence."},
        "relations": [],
        "provenance": {"event_id": f"event-{record_id}", "source_ref": f"synthetic:{record_id}"},
        "status": "active",
    })


def preserve_assessment(record_id="record-decision-1"):
    return assess_record(record(record_id), AssessmentContext(explicit_decision=True))


def test_factorization_cannot_drop_required_preservations():
    assessment = preserve_assessment()
    with pytest.raises(CpsValidationError):
        build_factorization_proposal(
            assessments=[assessment],
            source_refs=["record-decision-1"],
            anchors=[],
            structure=[],
            generators=[],
            obligations=[],
            provenance_refs=[],
            recompute_refs=[],
            unresolved_refs=[],
        )


def test_evidential_floor_may_be_covered_by_provenance_reference():
    assessment = preserve_assessment()
    proposal = build_factorization_proposal(
        assessments=[assessment],
        source_refs=["record-decision-1"],
        anchors=[],
        structure=[],
        generators=[],
        obligations=[],
        provenance_refs=["record-decision-1"],
        recompute_refs=[],
        unresolved_refs=[],
    )
    assert proposal.to_dict()["provenance_refs"] == ["record-decision-1"]


def test_every_source_ref_requires_anchor_provenance_or_unresolved_coverage():
    assessment = assess_record(record("r-struct"), AssessmentContext(structural_dependency=True))
    with pytest.raises(CpsValidationError):
        build_factorization_proposal(
            assessments=[assessment],
            source_refs=["r-struct"],
            anchors=[],
            structure=[{"relation": "depends_on", "source_ref": "r-struct", "target_ref": "r-base"}],
            generators=[],
            obligations=[],
            provenance_refs=[],
            recompute_refs=[],
            unresolved_refs=[],
        )


def test_factorization_builder_binds_assessment_ids_and_is_deterministic():
    assessment = assess_record(record("r-struct"), AssessmentContext(structural_dependency=True))
    kwargs = dict(
        assessments=[assessment],
        source_refs=["r-struct"],
        anchors=["r-struct"],
        structure=[{"relation": "depends_on", "source_ref": "r-struct", "target_ref": "r-base"}],
        generators=[],
        obligations=[],
        provenance_refs=["r-struct"],
        recompute_refs=[],
        unresolved_refs=[],
    )
    a = build_factorization_proposal(**kwargs)
    b = build_factorization_proposal(**kwargs)
    assert a.to_dict() == b.to_dict()
    assert a.fingerprint() == b.fingerprint()
    assert a.to_dict()["source_assessments"] == [assessment.to_dict()["assessment_id"]]
    assert a.to_dict()["authority"] is False


def test_factorization_fingerprint_ignores_proposal_id_only():
    assessment = preserve_assessment()
    p = build_factorization_proposal(
        assessments=[assessment], source_refs=["record-decision-1"], anchors=["record-decision-1"],
        structure=[], generators=[], obligations=[], provenance_refs=["record-decision-1"],
        recompute_refs=[], unresolved_refs=[]
    )
    raw = p.to_dict()
    raw2 = deepcopy(raw)
    raw2["proposal_id"] = "fp-other"
    assert FactorizationProposal.from_dict(raw).fingerprint() == FactorizationProposal.from_dict(raw2).fingerprint()


def test_unknown_assessment_reference_is_rejected_against_source_set():
    assessment = preserve_assessment()
    p = build_factorization_proposal(
        assessments=[assessment], source_refs=["record-decision-1"], anchors=["record-decision-1"],
        structure=[], generators=[], obligations=[], provenance_refs=["record-decision-1"],
        recompute_refs=[], unresolved_refs=[]
    )
    raw = p.to_dict()
    raw["source_assessments"] = ["pa-unknown"]
    tampered = FactorizationProposal.from_dict(raw)
    with pytest.raises(CpsValidationError):
        validate_factorization_sources(tampered, [assessment])


@pytest.mark.parametrize("mutator", [
    lambda r: r.__setitem__("authority", True),
    lambda r: r.__setitem__("extra", "no"),
])
def test_factorization_shape_rejects_authority_or_unknown_fields(mutator):
    assessment = preserve_assessment()
    p = build_factorization_proposal(
        assessments=[assessment], source_refs=["record-decision-1"], anchors=["record-decision-1"],
        structure=[], generators=[], obligations=[], provenance_refs=["record-decision-1"],
        recompute_refs=[], unresolved_refs=[]
    )
    raw = p.to_dict()
    mutator(raw)
    with pytest.raises(CpsValidationError):
        FactorizationProposal.from_dict(raw)


def test_factorization_rejects_untraceable_components():
    assessment = assess_record(record("r-struct"), AssessmentContext(structural_dependency=True))
    with pytest.raises(CpsValidationError):
        build_factorization_proposal(
            assessments=[assessment],
            source_refs=["r-struct"],
            anchors=["r-struct"],
            structure=[{"relation": "depends_on", "target_ref": "r-base"}],
            generators=[],
            obligations=[],
            provenance_refs=["r-struct"],
            recompute_refs=[],
            unresolved_refs=[],
        )


def test_factorization_rejects_component_source_ref_outside_declared_sources():
    assessment = assess_record(record("r-struct"), AssessmentContext(structural_dependency=True))
    with pytest.raises(CpsValidationError):
        build_factorization_proposal(
            assessments=[assessment],
            source_refs=["r-struct"],
            anchors=["r-struct"],
            structure=[{"relation": "depends_on", "source_ref": "r-other", "target_ref": "r-base"}],
            generators=[],
            obligations=[],
            provenance_refs=["r-struct"],
            recompute_refs=[],
            unresolved_refs=[],
        )
