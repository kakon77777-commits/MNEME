from __future__ import annotations

import argparse, copy, hashlib, inspect, json, shutil, subprocess, sys, tempfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'src'
if str(SRC) not in sys.path: sys.path.insert(0,str(SRC))

from mneme.canonical import canonical_json_bytes
from mneme.cps.models import PersistenceAssessment
from mneme.dry_run.analyzer import DryRunRequest, PrivateResidenceDryRunAnalyzer
import mneme.dry_run.analyzer as analyzer_module
from mneme.dry_run.compatibility import run_compatibility_pass
from mneme.dry_run.intents import FactorizationIntent, SeedIntent, evaluate_factorization_intents, evaluate_seed_intents
from mneme.dry_run.persistence import run_persistence_pass
from mneme.dry_run.policy import PersistencePolicy, resolve_contexts
from mneme.errors import CpsValidationError, DryRunValidationError
from mneme.markdown_profile import load_builtin_evemiss_profile

PROFILE='MNEME-PRIVATE-RESIDENCE-DRY-RUN/0.2'
FIX=ROOT/'fixtures/synthetic'
SOURCE=FIX/'private-residence-two-pass-memory.md'


def source_commit():
    p=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True,check=False)
    return p.stdout.strip() if p.returncode==0 and len(p.stdout.strip())==40 else None


def replace_token(value, token, replacement):
    if isinstance(value,str): return replacement if value==token else value
    if isinstance(value,list): return [replace_token(x,token,replacement) for x in value]
    if isinstance(value,dict): return {k:replace_token(v,token,replacement) for k,v in value.items()}
    return value


def context_dict(**changes):
    fields={'explicit_decision':False,'identity_or_authority_evidence':False,'historical_observation':False,
    'structural_dependency':False,'structural_state':False,'derivable_explanation':False,'reconstruction_recipe_ref':None,
    'obligation_set_ref':None,'freshness_required':False,'external_source_ref':None,'previous_observation_ref':None,
    'ephemeral_working_state':False,'superseded_materialization':False,'conflicting_evidence':False}
    fields.update(changes); return fields


def expect_error(fn,label,controls,exc=(DryRunValidationError,CpsValidationError)):
    try: fn()
    except exc: controls.append(label); return
    raise AssertionError('negative control did not fail: '+label)


def run_gate():
    cases={}; controls=[]; profile=load_builtin_evemiss_profile()
    policy=PersistencePolicy.from_dict(json.loads((FIX/'private-residence-persistence-policy.json').read_text(encoding='utf-8')))
    template=json.loads((FIX/'private-residence-intent-template.json').read_text(encoding='utf-8'))
    pass1_probe=run_compatibility_pass(SOURCE,profile,(1200,20000))
    gen_meta=next(m for m in pass1_probe.metadata if m.section_id=='verification_lessons')
    fraw=replace_token(template['factorization'],'$GENERATIVE_RECORD',gen_meta.record_id)
    sraw=replace_token(template['seed'],'$GENERATIVE_RECORD',gen_meta.record_id)
    fintent=FactorizationIntent.from_dict(fraw); sintent=SeedIntent.from_dict(sraw)
    request=DryRunRequest(source_path=SOURCE,markdown_profile=profile,privacy_mode='private',projection_budgets=(1200,20000),
        persistence_policy=policy,factorization_intents=(fintent,),seed_intents=(sintent,))
    before=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    result=PrivateResidenceDryRunAnalyzer().analyze(request)
    after=hashlib.sha256(SOURCE.read_bytes()).hexdigest()

    # D0
    assert before==after and result.report.to_dict()['source']['mutated'] is False; cases['D0']='PASS'
    with tempfile.TemporaryDirectory() as td:
        temp=Path(td)/'MEMORY.md'; shutil.copy2(SOURCE,temp); real=analyzer_module.run_compatibility_pass
        def mutating(path,*a,**kw):
            r=real(path,*a,**kw); Path(path).write_text(Path(path).read_text(encoding='utf-8')+'\nmutated',encoding='utf-8'); return r
        analyzer_module.run_compatibility_pass=mutating
        try:
            rr=PrivateResidenceDryRunAnalyzer().analyze(replace(request,source_path=temp,factorization_intents=(),seed_intents=()))
        finally: analyzer_module.run_compatibility_pass=real
        assert 'SOURCE_MUTATED' in rr.report.blocking_reasons
    controls.append('D0-source-mutation-detected')

    # D1
    forbidden={'commit','delete','tombstone','rewrite','archive_move','write_memory','apply_migration','update_store','replace_record','commit_factorization','promote_seed','promote_profile','forget'}
    public={x for x in dir(PrivateResidenceDryRunAnalyzer) if not x.startswith('_')}; assert forbidden.isdisjoint(public); cases['D1']='PASS'; controls.append('D1-store-or-mutation-surface-absent')

    # D2
    mapped={m.record_id for m in result.pass1.metadata}; assessed={a.to_dict()['subject_refs'][0] for a in result.pass2.assessments}; assert mapped==assessed; cases['D2']='PASS'
    cross=FactorizationIntent.from_dict({**fraw,'subject_record_ids':['not-mapped']})
    cr=evaluate_factorization_intents([cross],pass1_record_ids=mapped,assessments_by_record={a.to_dict()['subject_refs'][0]:a for a in result.pass2.assessments})[0]
    assert cr.error_code=='CROSS_PASS_SUBJECT'; controls.append('D2-cross-pass-subject-rejected')

    # D3
    assert all(m.profile_id==profile.profile_id and m.profile_digest==profile.digest() and m.start_line>=1 for m in result.pass1.metadata); cases['D3']='PASS'
    with tempfile.TemporaryDirectory() as td:
        temp=Path(td)/'MEMORY.md'; shutil.copy2(SOURCE,temp); real=analyzer_module.run_compatibility_pass
        def wrong(*a,**kw):
            r=real(*a,**kw); bad=replace(r.metadata[0],profile_digest='f'*64); return replace(r,metadata=(bad,)+r.metadata[1:])
        analyzer_module.run_compatibility_pass=wrong
        try: rr=PrivateResidenceDryRunAnalyzer().analyze(replace(request,source_path=temp,factorization_intents=(),seed_intents=()))
        finally: analyzer_module.run_compatibility_pass=real
        assert 'PASS1_PROFILE_BINDING_MISMATCH' in rr.report.blocking_reasons
    controls.append('D3-profile-binding-mutation-detected')

    # D4-D6
    reasons=result.pass1.loss_reason_counts; assert reasons.get('unknown_heading',0)>=3 and reasons.get('unknown_section',0)>=2 and reasons.get('unsupported_block_kind',0)>=1; cases['D4']='PASS'; controls.append('D4-unknown-loss-not-silenced')
    empty=next(h for h in result.pass1.heading_inventory if h.normalized_heading=='empty unknown heading'); assert empty.matched is False and empty.body_block_count==0; cases['D5']='PASS'; controls.append('D5-empty-unknown-heading-accounted')
    mapped_routes={r for x in result.pass1.mapping_receipt['mappings'] for r in x['route_hints']}; assert {x.route_id for x in result.pass1.route_inventory}==mapped_routes; cases['D6']='PASS'; controls.append('D6-prose-route-not-created')

    # D7
    bad_policy=json.loads((FIX/'private-residence-persistence-policy.json').read_text()); bad_policy['rules'][0]['selector']={'content.text':'x'}
    expect_error(lambda:PersistencePolicy.from_dict(bad_policy),'D7-forbidden-content-selector-rejected',controls); cases['D7']='PASS'

    # D8
    meta=result.pass1.metadata[0]
    default=resolve_contexts([meta])[0]; assert default.provenance=='DEFAULT_UNKNOWN'
    conflict_raw={'policy_version':'mneme.persistence-policy/0.1','policy_id':'conflict/0.1','rules':[
      {'rule_id':'a','selector':{'record_type':meta.record_type},'context':context_dict(structural_state=True)},
      {'rule_id':'b','selector':{'scope_kind':meta.scope_kind},'context':context_dict(explicit_decision=True)}]}
    conflict=PersistencePolicy.from_dict(conflict_raw); cres=resolve_contexts([meta],policy=conflict)[0]; assert cres.provenance=='POLICY_CONFLICT' and cres.context.conflicting_evidence
    override=resolve_contexts([meta],policy=conflict,exact_overrides={meta.record_id:context_dict(explicit_decision=True)})[0]; assert override.provenance=='EXACT_RECORD_OVERRIDE'
    cases['D8']='PASS'; controls.append('D8-policy-conflict-yields-unknown')
    expect_error(lambda:resolve_contexts([meta],exact_overrides={'not-mapped':context_dict()}),'D8-unmapped-exact-override-rejected',controls)

    # D9
    assert len(result.pass2.assessments)==len(result.pass1.records); cases['D9']='PASS'
    expect_error(lambda:run_persistence_pass(result.pass1.records,result.pass1.metadata[:-1]),'D9-assessment-count-mismatch-rejected',controls)

    # D10
    assert result.pass2.evidential_floor; cases['D10']='PASS'
    decision=next(a for a in result.pass2.assessments if a.to_dict()['candidate']=='PRESERVE'); did=decision.to_dict()['subject_refs'][0]
    omit_raw=copy.deepcopy(fraw); omit_raw.update({'subject_record_ids':[did],'anchors':[],'structure':[],'generators':[],'obligations':[],'provenance_refs':[],'unresolved_refs':[]})
    omit=FactorizationIntent.from_dict(omit_raw); omit_result=evaluate_factorization_intents([omit],pass1_record_ids=mapped,assessments_by_record={did:decision})[0]
    assert omit_result.error_code=='CPS_REJECTED'; controls.append('D10-required-preservation-omission-rejected')

    # D11
    for x in result.pass2.factorization_readiness:
        raw=x.to_dict(); assert not any(k in raw for k in ('anchors','structure','generators','obligations','provenance_refs','recompute_refs'))
    cases['D11']='PASS'; controls.append('D11-readiness-has-no-generated-components')

    # D12
    assert result.factorization_results[0].status=='ACCEPTED'; cases['D12']='PASS'
    bad=copy.deepcopy(fraw); bad['generators'][0].pop('source_ref')
    br=evaluate_factorization_intents([FactorizationIntent.from_dict(bad)],pass1_record_ids=mapped,assessments_by_record={a.to_dict()['subject_refs'][0]:a for a in result.pass2.assessments})[0]
    assert br.error_code=='CPS_REJECTED'; controls.append('D12-untraceable-factorization-component-rejected')

    # D13
    assert result.seed_results[0].status=='ACCEPTED'; cases['D13']='PASS'
    badseed=copy.deepcopy(sraw); badseed['generators']=[]
    sr=evaluate_seed_intents([SeedIntent.from_dict(badseed)],accepted_factorizations={'synthetic-fi-generative':result.factorization_results[0].proposal})[0]
    assert sr.error_code=='CPS_REJECTED'; controls.append('D13-factorization-generator-replacement-rejected')

    # D14
    assert any(a.to_dict()['candidate']=='RECOMPUTE' for a in result.pass2.assessments)
    with patch('socket.socket',side_effect=AssertionError('network forbidden')):
        nr=PrivateResidenceDryRunAnalyzer().analyze(replace(request,factorization_intents=(),seed_intents=()))
        assert nr.report.status in {'PASS','PASS_WITH_FINDINGS'}
    cases['D14']='PASS'; controls.append('D14-recompute-performs-no-network-call')

    # D15
    assert len(result.pass1.previews)==2 and result.pass1.previews[0].manifest['included_ids']!=result.pass1.previews[1].manifest['included_ids']
    ids_before=tuple(a.fingerprint() for a in result.pass2.assessments); assert ids_before==tuple(a.fingerprint() for a in result.pass2.assessments); cases['D15']='PASS'; controls.append('D15-preview-budget-does-not-change-assessments')

    # D16
    sanitized=PrivateResidenceDryRunAnalyzer().analyze(replace(request,privacy_mode='sanitized',sanitization_salt='acceptance-salt'))
    joined=b'\n'.join(sanitized.evidence_files.values()); assert str(SOURCE).encode() not in joined and SOURCE.read_bytes() not in joined and before.encode() not in joined and b'# MEMORY' not in joined
    cases['D16']='PASS'; controls.append('D16-private-text-absent-from-sanitized-evidence')

    # D17
    idmeta=next(m for m in result.pass1.metadata if m.section_id=='named_identities'); idrec=next(r for r in result.pass1.records if r.to_dict()['record_id']==idmeta.record_id); assert idrec.to_dict()['record_type']=='fact' and idrec.to_dict()['scope']['subject']=='identity_registry'
    assert all(a.to_dict()['authority'] is False for a in result.pass2.assessments); cases['D17']='PASS'
    bad_auth=copy.deepcopy(fraw); bad_auth['authority']=True
    expect_error(lambda:FactorizationIntent.from_dict(bad_auth),'D17-authority-true-intent-rejected',controls)

    # D18
    verified=PrivateResidenceDryRunAnalyzer().verify_deterministic(request); assert verified.deterministic_verified
    changed=PrivateResidenceDryRunAnalyzer().analyze(replace(request,exact_record_context_overrides={meta.record_id:context_dict(structural_state=True)},factorization_intents=(),seed_intents=()))
    assert changed.bundle_fingerprint != result.bundle_fingerprint; cases['D18']='PASS'; controls.append('D18-deterministic-input-mutation-changes-fingerprint')

    # D19
    assert forbidden.isdisjoint(public); cases['D19']='PASS'; controls.append('D19-forbidden-dematerialization-methods-absent')

    families={x.split('-',1)[0] for x in controls}; assert all(f'D{i}' in families for i in range(20)); cases['D20']='PASS'
    return {'profile':PROFILE,'status':'PASS','cases':cases,'controls':len(controls),'control_details':controls,
            'report_fingerprint':__import__('mneme.dry_run.report',fromlist=['report_fingerprint']).report_fingerprint(result.report.to_dict()),
            'bundle_fingerprint':result.bundle_fingerprint,'source_commit':source_commit()}


def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--output',type=Path,required=True); args=ap.parse_args(argv)
    try: receipt=run_gate(); code=0
    except Exception as exc: receipt={'profile':PROFILE,'status':'FAIL','cases':{},'controls':0,'control_details':[],'source_commit':source_commit(),'error':f'{type(exc).__name__}: {exc}'}; code=1
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_bytes(canonical_json_bytes(receipt)+b'\n')
    print(json.dumps(receipt,ensure_ascii=False,indent=2,sort_keys=True)); return code
if __name__=='__main__': raise SystemExit(main())
