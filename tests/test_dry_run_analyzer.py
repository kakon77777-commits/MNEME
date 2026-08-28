from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import inspect
from pathlib import Path

import pytest

import mneme.dry_run.analyzer as analyzer_module
from mneme.dry_run.analyzer import DryRunRequest, PrivateResidenceDryRunAnalyzer
from mneme.markdown_profile import load_builtin_evemiss_profile


def request(tmp_path, privacy='private'):
    path=tmp_path/'MEMORY.md'; path.write_text('# Standing Instructions\n- A\n\n# Verification Lessons\n- B\n',encoding='utf-8')
    return DryRunRequest(source_path=path,markdown_profile=load_builtin_evemiss_profile(),privacy_mode=privacy,
                         projection_budgets=(20000,),sanitization_salt='test-salt' if privacy=='sanitized' else None)


def test_request_validation_rejects_invalid_privacy_budget_or_missing_salt(tmp_path):
    base=request(tmp_path)
    with pytest.raises(ValueError): replace(base,privacy_mode='public').validate()
    with pytest.raises(ValueError): replace(base,projection_budgets=(0,)).validate()
    with pytest.raises(ValueError): replace(base,privacy_mode='sanitized',sanitization_salt=None).validate()


def test_expected_digest_mismatch_blocks_before_pass1(monkeypatch,tmp_path):
    req=request(tmp_path); called=False
    def forbidden(*args,**kwargs):
        nonlocal called; called=True; raise AssertionError('PASS 1 must not run')
    monkeypatch.setattr(analyzer_module,'run_compatibility_pass',forbidden)
    bad=replace(req,expected_source_sha256='0'*64)
    result=PrivateResidenceDryRunAnalyzer().analyze(bad)
    assert result.report.status=='BLOCKED'
    assert 'SOURCE_DIGEST_MISMATCH' in result.report.blocking_reasons
    assert called is False


def test_source_mutation_detected(monkeypatch,tmp_path):
    req=request(tmp_path); real=analyzer_module.run_compatibility_pass
    def mutating(path,*args,**kwargs):
        result=real(path,*args,**kwargs); Path(path).write_text(Path(path).read_text()+'\nchanged',encoding='utf-8'); return result
    monkeypatch.setattr(analyzer_module,'run_compatibility_pass',mutating)
    result=PrivateResidenceDryRunAnalyzer().analyze(req)
    assert result.report.status=='BLOCKED'
    assert 'SOURCE_MUTATED' in result.report.blocking_reasons


def test_pass1_source_binding_mismatch_blocks(monkeypatch,tmp_path):
    req=request(tmp_path); real=analyzer_module.run_compatibility_pass
    def wrong(*args,**kwargs): return replace(real(*args,**kwargs),source_sha256='f'*64)
    monkeypatch.setattr(analyzer_module,'run_compatibility_pass',wrong)
    result=PrivateResidenceDryRunAnalyzer().analyze(req)
    assert 'PASS1_SOURCE_BINDING_MISMATCH' in result.report.blocking_reasons


def test_analyzer_pass2_subjects_equal_pass1_mapped_ids(tmp_path):
    result=PrivateResidenceDryRunAnalyzer().analyze(request(tmp_path))
    mapped={m.record_id for m in result.pass1.metadata}
    assessed={a.to_dict()['subject_refs'][0] for a in result.pass2.assessments}
    assert assessed==mapped


def test_analyzer_public_api_has_no_mutation_surface():
    forbidden={'commit','delete','tombstone','rewrite','archive_move','write_memory','apply_migration','update_store','replace_record','commit_factorization','promote_seed','promote_profile','forget'}
    public={name for name in dir(PrivateResidenceDryRunAnalyzer) if not name.startswith('_')}
    assert forbidden.isdisjoint(public)
    params=set(inspect.signature(PrivateResidenceDryRunAnalyzer.analyze).parameters)
    assert {'store','writer','callback','mutation'}.isdisjoint(params)


def test_sanitized_evidence_omits_projection_bodies_and_source_path(tmp_path):
    req=request(tmp_path,privacy='sanitized')
    result=PrivateResidenceDryRunAnalyzer().analyze(req)
    joined=b'\n'.join(result.evidence_files.values())
    assert str(req.source_path).encode() not in joined
    assert b'# MEMORY' not in joined
    assert hashlib.sha256(req.source_path.read_bytes()).hexdigest().encode() not in joined


def test_verify_deterministic_repeats_same_bundle_fingerprint(tmp_path):
    result=PrivateResidenceDryRunAnalyzer().verify_deterministic(request(tmp_path))
    assert result.deterministic_verified is True
    assert result.report.status in {'PASS','PASS_WITH_FINDINGS'}


def test_pass1_profile_binding_mismatch_blocks(monkeypatch,tmp_path):
    req=request(tmp_path); real=analyzer_module.run_compatibility_pass
    def wrong(*args,**kwargs):
        result=real(*args,**kwargs)
        bad=replace(result.metadata[0],profile_digest='f'*64)
        return replace(result,metadata=(bad,)+result.metadata[1:])
    monkeypatch.setattr(analyzer_module,'run_compatibility_pass',wrong)
    result=PrivateResidenceDryRunAnalyzer().analyze(req)
    assert 'PASS1_PROFILE_BINDING_MISMATCH' in result.report.blocking_reasons


def test_deterministic_mismatch_rebuilds_blocked_evidence(monkeypatch, tmp_path):
    analyzer = PrivateResidenceDryRunAnalyzer()
    req = request(tmp_path)
    first = analyzer.analyze(req)
    second = replace(first, bundle_fingerprint="f" * 64)
    results = iter((first, second))
    monkeypatch.setattr(analyzer, "analyze", lambda _request: next(results))

    result = analyzer.verify_deterministic(req)

    assert result.report.status == "BLOCKED"
    assert "DETERMINISTIC_REPLAY_MISMATCH" in result.report.blocking_reasons
    rendered = json.loads(result.evidence_files["report.json"].decode("utf-8"))
    assert rendered["report"]["status"] == "BLOCKED"
    assert "DETERMINISTIC_REPLAY_MISMATCH" in rendered["report"]["blocking_reasons"]
    from mneme.dry_run.bundle import bundle_fingerprint, verify_bundle
    assert verify_bundle(result.evidence_files, result.bundle_manifest) is True
    assert result.bundle_fingerprint == bundle_fingerprint(result.bundle_manifest)
