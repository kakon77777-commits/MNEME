from __future__ import annotations

import pytest

from mneme.cps.models import PersistenceAssessment
from mneme.dry_run.intents import (
    FactorizationIntent, SeedIntent,
    evaluate_factorization_intents, evaluate_seed_intents,
)
from mneme.errors import DryRunValidationError


def assessment(record_id='r1', candidate='STRUCTURALIZE', required=()):
    risk = 'LOW' if candidate == 'PRESERVE' else ('BLOCKED' if candidate == 'UNKNOWN' else 'MEDIUM')
    return PersistenceAssessment.from_dict({
        'assessment_version':'mneme.persistence-assessment/0.1','assessment_id':f'pa-{record_id}',
        'subject_refs':[record_id],'candidate':candidate,
        'basis':{'method':'EXPLICIT_RULE','deterministic':True,'reason_codes':['X'],'evidence_refs':[record_id]},
        'required_preservations':list(required),'risk':risk,'review_state':'UNREVIEWED','authority':False,
    })


def factorization_intent_dict(**changes):
    raw = {
        'intent_version':'mneme.factorization-intent/0.1','intent_id':'fi-1','subject_record_ids':['r1'],
        'anchors':['r1'],'structure':[{'relation':'depends_on','source_ref':'r1','target_ref':'r2'}],
        'generators':[],'obligations':[],'provenance_refs':['r1'],'recompute_refs':[],'unresolved_refs':[],
        'authority':False,
    }
    raw.update(changes); return raw


def eq_contract_dict():
    return {'contract_version':'mneme.equivalence-contract/0.1','contract_id':'eq-1',
            'observation_surfaces':[{'kind':'ANCHOR_MUST_MATCH','subject_ref':'r1'}],
            'forbidden_equalities':['TOKEN_EQUALITY','TRACE_EQUALITY'],'authority':False}


def seed_intent_dict(**changes):
    raw = {
        'intent_version':'mneme.seed-intent/0.1','seed_intent_id':'si-1','factorization_intent_id':'fi-1',
        'anchors':['r1'],'structure':[{'relation':'depends_on','source_ref':'r1','target_ref':'r2'}],
        'generators':[],'obligations':[],'provenance_refs':['r1'],'recomputation_references':[],
        'unresolved_components':[],'equivalence_contract':eq_contract_dict(),'authority':False,
    }
    raw.update(changes); return raw


def test_factorization_intent_shape_rejects_authority_and_unknown_field():
    for changes in ({'authority':True}, {'extra':'no'}):
        raw = factorization_intent_dict(**changes)
        with pytest.raises(DryRunValidationError): FactorizationIntent.from_dict(raw)


def test_seed_intent_shape_rejects_authority_and_unknown_field():
    for changes in ({'authority':True}, {'extra':'no'}):
        with pytest.raises(DryRunValidationError): SeedIntent.from_dict(seed_intent_dict(**changes))


def test_factorization_intent_rejects_unmapped_subject():
    intent = FactorizationIntent.from_dict(factorization_intent_dict(subject_record_ids=['not-mapped']))
    result = evaluate_factorization_intents([intent], pass1_record_ids={'mapped'}, assessments_by_record={'mapped':assessment('mapped')})[0]
    assert (result.status, result.error_code) == ('REJECTED','CROSS_PASS_SUBJECT')


def test_factorization_intent_cannot_omit_required_preservation():
    intent = FactorizationIntent.from_dict(factorization_intent_dict(
        subject_record_ids=['decision'], anchors=[], provenance_refs=[], unresolved_refs=[], structure=[]))
    result = evaluate_factorization_intents([intent], pass1_record_ids={'decision'}, assessments_by_record={'decision':assessment('decision','PRESERVE',('decision',))})[0]
    assert (result.status, result.error_code) == ('REJECTED','CPS_REJECTED')


def test_untraceable_factorization_component_is_rejected():
    intent = FactorizationIntent.from_dict(factorization_intent_dict(structure=[{'relation':'depends_on','target_ref':'r2'}]))
    result = evaluate_factorization_intents([intent], pass1_record_ids={'r1'}, assessments_by_record={'r1':assessment()})[0]
    assert result.error_code == 'CPS_REJECTED'


def test_valid_intent_returns_cps_factorization_proposal():
    intent = FactorizationIntent.from_dict(factorization_intent_dict())
    result = evaluate_factorization_intents([intent], pass1_record_ids={'r1'}, assessments_by_record={'r1':assessment()})[0]
    assert result.status == 'ACCEPTED'
    assert result.proposal.to_dict()['authority'] is False
    assert set(result.proposal.to_dict()['source_refs']) == {'r1'}


def test_seed_intent_requires_accepted_factorization():
    result = evaluate_seed_intents([SeedIntent.from_dict(seed_intent_dict(factorization_intent_id='missing'))], accepted_factorizations={})[0]
    assert (result.status, result.error_code) == ('REJECTED','UNKNOWN_FACTORIZATION_INTENT')


def test_seed_intent_cannot_replace_factorization_structure():
    fi = FactorizationIntent.from_dict(factorization_intent_dict())
    fr = evaluate_factorization_intents([fi], pass1_record_ids={'r1'}, assessments_by_record={'r1':assessment()})[0]
    intent = SeedIntent.from_dict(seed_intent_dict(structure=[]))
    result = evaluate_seed_intents([intent], accepted_factorizations={'fi-1':fr.proposal})[0]
    assert (result.status, result.error_code) == ('REJECTED','CPS_REJECTED')


def test_invalid_recomputation_or_equivalence_authority_is_cps_rejected():
    fi = FactorizationIntent.from_dict(factorization_intent_dict())
    fr = evaluate_factorization_intents([fi], pass1_record_ids={'r1'}, assessments_by_record={'r1':assessment()})[0]
    bad_eq = eq_contract_dict(); bad_eq['authority'] = True
    result = evaluate_seed_intents([SeedIntent.from_dict(seed_intent_dict(equivalence_contract=bad_eq))], accepted_factorizations={'fi-1':fr.proposal})[0]
    assert result.error_code == 'CPS_REJECTED'
