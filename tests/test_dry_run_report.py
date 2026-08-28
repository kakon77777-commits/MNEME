from __future__ import annotations

from types import SimpleNamespace

import pytest

from mneme.canonical import canonical_json_bytes
from mneme.cps.models import PersistenceAssessment
from mneme.dry_run.models import ContextResolution
from mneme.dry_run.persistence import FactorizationReadiness, PersistencePassResult, RecomputeReadiness
from mneme.dry_run.report import (
    build_report, compatibility_risk, max_risk, persistence_risk,
    render_private_report, render_sanitized_report, report_fingerprint, sanitized_alias,
)


def pass1(unresolved=0,total=20,candidate_body=0,records=1,preview_failures=0):
    loss=[]
    for i in range(unresolved): loss.append({'kind':'paragraph','reason':'unknown_section','start_line':i+1,'end_line':i+1})
    candidates=() if not candidate_body else (SimpleNamespace(body_block_count=candidate_body),)
    return SimpleNamespace(
        loss_report={'block_count':total,'loss':loss}, profile_candidates=candidates,
        records=tuple(range(records)), previews=() if preview_failures else (object(),),
        preview_failures=tuple('x' for _ in range(preview_failures)),
        loss_reason_counts={'unknown_section':unresolved} if unresolved else {},
        route_inventory=(), heading_inventory=(), metadata=(), mapping_receipt={'mappings':[]},
    )


def assessment(record_id,candidate,risk='LOW'):
    return PersistenceAssessment.from_dict({
        'assessment_version':'mneme.persistence-assessment/0.1','assessment_id':f'pa-{record_id}',
        'subject_refs':[record_id],'candidate':candidate,
        'basis':{'method':'EXPLICIT_RULE','deterministic':True,'reason_codes':['X'],'evidence_refs':[record_id]},
        'required_preservations':[],'risk':risk,'review_state':'UNREVIEWED','authority':False})


def pass2(candidates=('PRESERVE',), provenances=None):
    if provenances is None: provenances=['EXACT_RECORD_OVERRIDE']*len(candidates)
    assessments=tuple(assessment(f'r{i}',c,'HIGH' if c in {'GENERATIZE','DISCARD'} else ('BLOCKED' if c=='UNKNOWN' else 'LOW')) for i,c in enumerate(candidates))
    resolutions=tuple(ContextResolution(f'r{i}',p,(),__import__('mneme.cps.rules',fromlist=['AssessmentContext']).AssessmentContext()) for i,p in enumerate(provenances))
    readiness=tuple(FactorizationReadiness(f'r{i}', {'PRESERVE':'PRESERVE_ONLY','STRUCTURALIZE':'READY_FOR_STRUCTURAL_REVIEW','RECOMPUTE':'READY_FOR_RECOMPUTE_REVIEW','GENERATIZE':'READY_FOR_GENERATIVE_REVIEW','DISCARD':'DISCARD_REQUIRES_REVIEW','UNKNOWN':'UNRESOLVED'}[c], f'pa-r{i}') for i,c in enumerate(candidates))
    recompute=tuple(RecomputeReadiness(f'r{i}','RECOMPUTE_CANDIDATE' if c=='RECOMPUTE' else 'NOT_RECOMPUTE') for i,c in enumerate(candidates))
    return PersistencePassResult(assessments,resolutions,readiness,recompute,{})


@pytest.mark.parametrize(('unresolved','total','expected'),[(0,20,'LOW'),(1,20,'MEDIUM'),(5,20,'HIGH')])
def test_compatibility_risk_ratio(unresolved,total,expected):
    assert compatibility_risk(pass1(unresolved,total)) == expected


def test_compatibility_high_for_dominant_repeated_unknown_or_all_preview_failures():
    assert compatibility_risk(pass1(unresolved=2,total=20,candidate_body=1)) == 'HIGH'
    assert compatibility_risk(pass1(unresolved=0,total=20,records=2,preview_failures=2)) == 'HIGH'


def test_persistence_low_and_high_rules():
    assert persistence_risk(pass2(('PRESERVE',))) == 'LOW'
    assert persistence_risk(pass2(('GENERATIZE',))) == 'HIGH'
    assert persistence_risk(pass2(('DISCARD',))) == 'HIGH'
    assert persistence_risk(pass2(('PRESERVE',),provenances=['POLICY_CONFLICT'])) == 'HIGH'
    rejected=SimpleNamespace(status='REJECTED')
    assert persistence_risk(pass2(('PRESERVE',)),factorization_results=[rejected]) == 'HIGH'
    assert persistence_risk(pass2(('UNKNOWN','PRESERVE','PRESERVE','PRESERVE'))) == 'HIGH'
    assert persistence_risk(pass2(('UNKNOWN','PRESERVE','PRESERVE','PRESERVE','PRESERVE'))) == 'MEDIUM'
    assert persistence_risk(pass2(('STRUCTURALIZE',))) == 'MEDIUM'


def test_max_risk_ordering():
    assert max_risk('LOW','BLOCKED') == 'BLOCKED'
    assert max_risk('HIGH','MEDIUM') == 'HIGH'


def test_build_report_has_exact_non_destructive_contract():
    report=build_report(
        source_sha256='a'*64, source_byte_count=10, source_line_count=2, source_mutated=False,
        profile_id='evemiss-residence/0.1', profile_digest='b'*64,
        policy_summary={'policy_id':'NO_POLICY','policy_digest':None,'rule_count':0},
        pass1=pass1(), pass2=pass2(('PRESERVE',)), factorization_results=(), seed_results=(), blocking_reasons=())
    raw=report.to_dict()
    assert raw['report_version']=='mneme.private-residence-dry-run/0.2'
    assert raw['status']=='PASS'
    assert raw['canonical_mutation'] is False and raw['destructive_actions'] is False
    assert set(raw)=={'report_version','status','source','markdown_profile','persistence_policy','pass1','pass2','risk','blocking_reasons','canonical_mutation','destructive_actions'}


def test_sanitized_report_excludes_private_material():
    report=build_report(
        source_sha256='a'*64, source_byte_count=10, source_line_count=2, source_mutated=False,
        profile_id='evemiss-residence/0.1', profile_digest='b'*64,
        policy_summary={'policy_id':'NO_POLICY','policy_digest':None,'rule_count':0},
        pass1=pass1(), pass2=pass2(('PRESERVE',)), factorization_results=(), seed_results=(), blocking_reasons=())
    private=render_private_report(report, {'source_path':'/private/Residence/MEMORY.md','heading':'Secret Person','content':'private fact','projection':'# MEMORY\nprivate fact'})
    sanitized=render_sanitized_report(private,salt='caller-supplied-test-salt')
    encoded=canonical_json_bytes(sanitized)
    for secret in (b'/private/Residence/MEMORY.md',b'Secret Person',b'private fact',('a'*64).encode(),b'# MEMORY'):
        assert secret not in encoded


def test_sanitized_alias_and_report_fingerprint_are_deterministic_and_sensitive():
    assert sanitized_alias('record','r1','salt') == sanitized_alias('record','r1','salt')
    assert sanitized_alias('record','r1','salt') != sanitized_alias('record','r1','other')
    a={'report_version':'mneme.private-residence-dry-run/0.2','x':1}
    b={'report_version':'mneme.private-residence-dry-run/0.2','x':2}
    assert report_fingerprint(a)==report_fingerprint(dict(a))
    assert report_fingerprint(a)!=report_fingerprint(b)


def test_report_schema_rejects_unknown_nested_fields():
    from mneme.dry_run.report import DryRunReport
    from mneme.errors import DryRunValidationError

    report = build_report(
        source_sha256='a'*64, source_byte_count=10, source_line_count=2, source_mutated=False,
        profile_id='evemiss-residence/0.1', profile_digest='b'*64,
        policy_summary={'policy_id':'NO_POLICY','policy_digest':None,'rule_count':0},
        pass1=pass1(), pass2=pass2(('PRESERVE',)), factorization_results=(), seed_results=(), blocking_reasons=()
    )
    raw = report.to_dict()
    raw['pass1']['private_text'] = 'must-not-be-accepted'
    with pytest.raises(DryRunValidationError):
        DryRunReport.from_dict(raw)


def test_sanitized_renderer_rejects_nested_private_field_in_report():
    from mneme.errors import DryRunValidationError

    report = build_report(
        source_sha256='a'*64, source_byte_count=10, source_line_count=2, source_mutated=False,
        profile_id='evemiss-residence/0.1', profile_digest='b'*64,
        policy_summary={'policy_id':'NO_POLICY','policy_digest':None,'rule_count':0},
        pass1=pass1(), pass2=pass2(('PRESERVE',)), factorization_results=(), seed_results=(), blocking_reasons=()
    )
    private = render_private_report(report, {})
    private['report']['pass2']['private_text'] = 'secret nested text'
    with pytest.raises(DryRunValidationError):
        render_sanitized_report(private, salt='caller-supplied-test-salt')
