from copy import deepcopy

from mneme.cps.adapter import CpsObservationAdapter
from mneme.cps.models import EquivalenceContract, RecomputationReference
from mneme.cps.rules import AssessmentContext
from mneme.records import MemoryRecord


def record(record_id="r1"):
    return MemoryRecord.from_dict({
        "record_version": "mneme.memory-record/0.1",
        "record_id": record_id,
        "record_type": "fact",
        "scope": {"kind": "global", "subject": "synthetic"},
        "content": {"text": "Synthetic source memory."},
        "relations": [],
        "provenance": {"event_id": f"event-{record_id}", "source_ref": f"synthetic:{record_id}"},
        "status": "active",
    })


def eq_contract():
    return EquivalenceContract.from_dict({
        "contract_version": "mneme.equivalence-contract/0.1",
        "contract_id": "eq-a",
        "observation_surfaces": [{"kind": "ANCHOR_MUST_MATCH", "subject_ref": "r1"}],
        "forbidden_equalities": ["TOKEN_EQUALITY", "TRACE_EQUALITY"],
        "authority": False,
    })


def test_cps_adapter_has_no_destructive_or_commit_api():
    forbidden = {
        "commit", "delete", "tombstone", "rewrite", "archive_move",
        "update_store", "replace_record", "commit_factorization", "promote_seed",
    }
    public = {name for name in dir(CpsObservationAdapter) if not name.startswith("_")}
    assert forbidden.isdisjoint(public)


def test_adapter_assessment_does_not_mutate_source_record():
    source = record()
    before = deepcopy(source.to_dict())
    before_digest = source.digest()
    adapter = CpsObservationAdapter()
    assessments = adapter.assess([source], [AssessmentContext(explicit_decision=True)])
    assert assessments[0].to_dict()["candidate"] == "PRESERVE"
    assert source.to_dict() == before
    assert source.digest() == before_digest


def test_adapter_factorize_and_seed_are_observation_only():
    source = record()
    before = deepcopy(source.to_dict())
    adapter = CpsObservationAdapter()
    assessments = adapter.assess(
        [source],
        [AssessmentContext(
            derivable_explanation=True,
            reconstruction_recipe_ref="synthetic://recipe/1",
            obligation_set_ref="synthetic://obligation/1",
        )],
    )
    factorization = adapter.factorize(
        assessments=assessments,
        source_refs=["r1"],
        anchors=["r1"],
        structure=[],
        generators=[{"kind": "RECONSTRUCTION_RECIPE", "generator_ref": "synthetic://recipe/1"}],
        obligations=[{"kind": "ANCHOR_MUST_MATCH", "subject_ref": "r1"}],
        provenance_refs=["r1"],
        recompute_refs=[],
        unresolved_refs=[],
    )
    seed = adapter.propose_seed(
        factorization=factorization,
        anchors=["r1"],
        structure=[],
        generators=factorization.to_dict()["generators"],
        obligations=factorization.to_dict()["obligations"],
        provenance_refs=["r1"],
        recomputation_refs=[],
        unresolved_components=[],
        equivalence_contract=eq_contract(),
    )
    assert seed.to_dict()["authority"] is False
    assert source.to_dict() == before
