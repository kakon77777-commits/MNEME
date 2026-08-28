from __future__ import annotations

from dataclasses import asdict, is_dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping

from ..canonical import canonical_json_bytes, sha256_domain
from ..errors import DryRunValidationError
from .report import DryRunReport, render_private_report, render_sanitized_report, sanitized_alias


def bundle_manifest(files: Mapping[str, bytes]) -> dict[str, object]:
    entries=[]
    for path in sorted(files):
        data=files[path]
        entries.append({'path':path,'sha256':hashlib.sha256(data).hexdigest(),'byte_count':len(data)})
    return {'manifest_version':'mneme.private-residence-dry-run-bundle/0.2','files':entries}


def bundle_fingerprint(manifest: Mapping[str, object]) -> str:
    return sha256_domain(b'MNEME-DRYRUN-BUNDLE-0.2',canonical_json_bytes(manifest))


def verify_bundle(files: Mapping[str, bytes], manifest: Mapping[str, object]) -> bool:
    return canonical_json_bytes(bundle_manifest(files)) == canonical_json_bytes(manifest)


def _json_bytes(value) -> bytes:
    return canonical_json_bytes(value)+b'\n'


def _jsonl(items) -> bytes:
    return b''.join(canonical_json_bytes(item)+b'\n' for item in items)


def _intent_result_dict(result, id_field: str):
    value={id_field:getattr(result,id_field),'status':result.status,'error_code':result.error_code}
    if result.proposal is not None: value['proposal']=result.proposal.to_dict()
    return value


def build_evidence_files(*, report: DryRunReport, pass1, pass2, factorization_results, seed_results,
                         privacy_mode: str, salt: str | None, source_path: Path) -> dict[str, bytes]:
    summary=(f"# MNEME Private Residence Dry-Run\n\nStatus: {report.status}\n"
             f"Mapped records: {0 if pass1 is None else len(pass1.records)}\n"
             f"Assessments: {0 if pass2 is None else len(pass2.assessments)}\n").encode('utf-8')
    if pass1 is None or pass2 is None:
        rendered=render_private_report(report,{'source_path':str(source_path)}) if privacy_mode=='private' else render_sanitized_report({'report':report.to_dict(),'private':{}},salt=salt or '')
        return {'report.json':_json_bytes(rendered),'summary.md':summary}

    if privacy_mode=='private':
        rendered=render_private_report(report,{'source_path':str(source_path)})
        files={
          'report.json':_json_bytes(rendered),'summary.md':summary,
          'pass1/mapping-receipt.json':_json_bytes(pass1.mapping_receipt),
          'pass1/loss-inventory.json':_json_bytes(pass1.loss_report),
          'pass1/heading-inventory.json':_json_bytes([asdict(x) for x in pass1.heading_inventory]),
          'pass1/route-inventory.json':_json_bytes([asdict(x) for x in pass1.route_inventory]),
          'pass1/profile-candidates.json':_json_bytes([asdict(x) for x in pass1.profile_candidates]),
          'pass2/persistence-assessments.jsonl':_jsonl(a.to_dict() for a in pass2.assessments),
          'pass2/context-resolution.jsonl':_jsonl({'record_id':r.record_id,'provenance':r.provenance,'rule_ids':list(r.rule_ids),'context':asdict(r.context)} for r in pass2.resolutions),
          'pass2/evidential-floor.json':_json_bytes({k:list(v) for k,v in pass2.evidential_floor.items()}),
          'pass2/factorization-readiness.jsonl':_jsonl(x.to_dict() for x in pass2.factorization_readiness),
          'pass2/factorization-intent-results.jsonl':_jsonl(_intent_result_dict(x,'intent_id') for x in factorization_results),
          'pass2/seed-readiness.jsonl':_jsonl({'factorization_intent_id':x.intent_id,'state':'READY_FOR_SEED_REVIEW' if x.status=='ACCEPTED' else 'UNRESOLVED'} for x in factorization_results),
          'pass2/seed-intent-results.jsonl':_jsonl(_intent_result_dict(x,'seed_intent_id') for x in seed_results),
        }
        for preview in pass1.previews:
            budget=str(preview.manifest['byte_budget'])
            files[f'projections/{budget}.md']=preview.content
            files[f'projections/{budget}.manifest.json']=_json_bytes(preview.manifest)
        return files

    if not salt: raise DryRunValidationError('sanitized evidence requires caller-supplied salt')
    rendered=render_sanitized_report({'report':report.to_dict(),'private':{}},salt=salt)
    alias=lambda kind,value: sanitized_alias(kind,str(value),salt)
    assessments=[]
    for a in pass2.assessments:
        raw=a.to_dict(); assessments.append({
            'assessment_id':alias('assessment',raw['assessment_id']),
            'subject_refs':[alias('record',r) for r in raw['subject_refs']],
            'candidate':raw['candidate'],'risk':raw['risk'],'review_state':raw['review_state'],'authority':False,
            'reason_codes':list(raw['basis']['reason_codes']),
            'required_preservations':[alias('record',r) for r in raw['required_preservations']],
        })
    files={
      'report.json':_json_bytes(rendered),'summary.md':summary,
      'pass1/loss-inventory.json':_json_bytes([{'kind':x['kind'],'reason':x['reason'],'start_line':x['start_line'],'end_line':x['end_line']} for x in pass1.loss_report['loss']]),
      'pass1/heading-inventory.json':_json_bytes([{'heading_alias':alias('heading',x.normalized_heading),'matched':x.matched,'occurrences':x.occurrences,'line_numbers':list(x.line_numbers),'body_block_count':x.body_block_count} for x in pass1.heading_inventory]),
      'pass1/route-inventory.json':_json_bytes([asdict(x) for x in pass1.route_inventory]),
      'pass1/profile-candidates.json':_json_bytes([{'heading_alias':alias('heading',x.normalized_heading),'occurrences':x.occurrences,'suggested_action':x.suggested_action,'target_section':None} for x in pass1.profile_candidates]),
      'pass2/persistence-assessments.jsonl':_jsonl(assessments),
      'pass2/context-resolution.jsonl':_jsonl({'record_alias':alias('record',r.record_id),'provenance':r.provenance,'rule_ids':list(r.rule_ids)} for r in pass2.resolutions),
      'pass2/evidential-floor.json':_json_bytes({alias('record',k):[alias('assessment',v) for v in values] for k,values in pass2.evidential_floor.items()}),
      'pass2/factorization-readiness.jsonl':_jsonl({'record_alias':alias('record',x.record_id),'state':x.state,'assessment_alias':alias('assessment',x.assessment_id)} for x in pass2.factorization_readiness),
      'pass2/factorization-intent-results.jsonl':_jsonl({'intent_alias':alias('factorization-intent',x.intent_id),'status':x.status,'error_code':x.error_code} for x in factorization_results),
      'pass2/seed-readiness.jsonl':_jsonl({'factorization_intent_alias':alias('factorization-intent',x.intent_id),'state':'READY_FOR_SEED_REVIEW' if x.status=='ACCEPTED' else 'UNRESOLVED'} for x in factorization_results),
      'pass2/seed-intent-results.jsonl':_jsonl({'seed_intent_alias':alias('seed-intent',x.seed_intent_id),'status':x.status,'error_code':x.error_code} for x in seed_results),
    }
    return files


def write_evidence_bundle(files: Mapping[str, bytes], destination: Path, *, source_path: Path) -> dict[str, object]:
    destination=Path(destination); source_path=Path(source_path)
    if destination.resolve() == source_path.resolve(): raise DryRunValidationError('evidence destination cannot equal source path')
    if destination.exists() and destination.is_file(): raise DryRunValidationError('evidence destination must be a directory')
    source_bytes = source_path.read_bytes()
    if any(data == source_bytes for data in files.values()):
        raise DryRunValidationError('evidence bundle must not copy source bytes')
    destination.mkdir(parents=True,exist_ok=True)
    for rel,data in files.items():
        path=Path(rel)
        if path.is_absolute() or '..' in path.parts: raise DryRunValidationError('unsafe evidence path')
        target=destination/path; target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and target.read_bytes()!=data: raise DryRunValidationError(f'refusing to overwrite different evidence bytes: {rel}')
        target.write_bytes(data)
    manifest=bundle_manifest(files)
    check=destination/'checksums.json'; bytes_=_json_bytes(manifest)
    if check.exists() and check.read_bytes()!=bytes_: raise DryRunValidationError('refusing to overwrite different checksum bytes')
    check.write_bytes(bytes_)
    return manifest
