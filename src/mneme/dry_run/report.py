from __future__ import annotations

from copy import deepcopy
from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable, Mapping, Any

from jsonschema import Draft202012Validator

from ..canonical import canonical_json_bytes, sha256_domain
from ..errors import DryRunValidationError

_RISK_ORDER = {"LOW":0,"MEDIUM":1,"HIGH":2,"BLOCKED":3}
_SCHEMA_PATH = Path(__file__).resolve().parents[3] / 'schemas/private-residence-dry-run-report-0.2.schema.json'
_VALIDATOR=Draft202012Validator(json.loads(_SCHEMA_PATH.read_text()))


def max_risk(a:str,b:str)->str:
    return max((a,b), key=_RISK_ORDER.__getitem__)


def compatibility_risk(pass1)->str:
    total=int(pass1.loss_report.get('block_count',0))
    unresolved_nonheading=sum(1 for item in pass1.loss_report.get('loss',[]) if item.get('kind')!='heading')
    preview_failures=len(getattr(pass1,'preview_failures',()))
    if getattr(pass1,'records',()) and preview_failures and not getattr(pass1,'previews',()):
        return 'HIGH'
    if unresolved_nonheading == 0:
        return 'LOW'
    if total and unresolved_nonheading/total >= .25:
        return 'HIGH'
    if any(getattr(c,'body_block_count',0) * 2 >= unresolved_nonheading for c in getattr(pass1,'profile_candidates',())):
        return 'HIGH'
    return 'MEDIUM'


def persistence_risk(pass2, *, factorization_results:Iterable=(), seed_results:Iterable=())->str:
    assessments=tuple(pass2.assessments)
    total=len(assessments)
    candidates=[str(a.to_dict()['candidate']) for a in assessments]
    if any(getattr(r,'provenance',None)=='POLICY_CONFLICT' for r in pass2.resolutions): return 'HIGH'
    if any(getattr(r,'status',None)=='REJECTED' for r in tuple(factorization_results)+tuple(seed_results)): return 'HIGH'
    if any(c in {'GENERATIZE','DISCARD'} for c in candidates): return 'HIGH'
    unknown=candidates.count('UNKNOWN')
    if total and unknown/total >= .25: return 'HIGH'
    if unknown: return 'MEDIUM'
    if any(c in {'STRUCTURALIZE','RECOMPUTE'} for c in candidates): return 'MEDIUM'
    return 'LOW'


@dataclass(frozen=True)
class DryRunReport:
    _raw: dict[str,Any]
    @classmethod
    def from_dict(cls,raw):
        candidate=deepcopy(raw); errors=list(_VALIDATOR.iter_errors(candidate))
        if errors: raise DryRunValidationError(errors[0].message)
        return cls(candidate)
    def to_dict(self): return deepcopy(self._raw)
    @property
    def status(self): return str(self._raw['status'])
    @property
    def blocking_reasons(self): return tuple(self._raw['blocking_reasons'])


def _result_counts(results):
    return dict(sorted(Counter(getattr(r,'status','UNKNOWN') for r in results).items()))


def build_report(*,source_sha256:str,source_byte_count:int,source_line_count:int,source_mutated:bool,
                 profile_id:str,profile_digest:str,policy_summary:Mapping[str,object],pass1,pass2,
                 factorization_results:Iterable=(),seed_results:Iterable=(),blocking_reasons:Iterable[str]=())->DryRunReport:
    fr=tuple(factorization_results); sr=tuple(seed_results); blockers=tuple(sorted(set(blocking_reasons)))
    cr='BLOCKED' if blockers else compatibility_risk(pass1)
    pr='BLOCKED' if blockers else persistence_risk(pass2,factorization_results=fr,seed_results=sr)
    overall=max_risk(cr,pr)
    candidate_counts=Counter(str(a.to_dict()['candidate']) for a in pass2.assessments)
    provenance_counts=Counter(r.provenance for r in pass2.resolutions)
    readiness_counts=Counter(r.state for r in pass2.factorization_readiness)
    loss_count=len(pass1.loss_report.get('loss',[]))
    unknown_count=candidate_counts.get('UNKNOWN',0)
    finding = bool(loss_count or unknown_count or provenance_counts.get('POLICY_CONFLICT',0) or
                   any(getattr(r,'status',None)=='REJECTED' for r in fr+sr) or overall!='LOW')
    status='BLOCKED' if blockers else ('PASS_WITH_FINDINGS' if finding else 'PASS')
    raw={
      'report_version':'mneme.private-residence-dry-run/0.2','status':status,
      'source':{'sha256':source_sha256,'byte_count':source_byte_count,'line_count':source_line_count,'mutated':bool(source_mutated)},
      'markdown_profile':{'profile_id':profile_id,'profile_digest':profile_digest},
      'persistence_policy':dict(policy_summary),
      'pass1':{'mapped_record_count':len(pass1.records),'loss_count':loss_count,'unknown_heading_count':int(pass1.loss_reason_counts.get('unknown_heading',0)),
               'route_hint_counts':{r.route_id:r.record_count for r in pass1.route_inventory}},
      'pass2':{'assessment_count':len(pass2.assessments),'candidate_counts':dict(sorted(candidate_counts.items())),
               'context_provenance_counts':dict(sorted(provenance_counts.items())),
               'required_preservation_count':len(pass2.evidential_floor),'factorization_readiness_counts':dict(sorted(readiness_counts.items())),
               'factorization_intent_count':len(fr),'factorization_proposal_count':sum(getattr(r,'status',None)=='ACCEPTED' for r in fr),
               'seed_intent_count':len(sr),'seed_proposal_count':sum(getattr(r,'status',None)=='ACCEPTED' for r in sr),'unknown_count':unknown_count},
      'risk':{'compatibility':cr,'persistence':pr,'overall':overall,'reasons':list(blockers)},
      'blocking_reasons':list(blockers),'canonical_mutation':False,'destructive_actions':False,
    }
    return DryRunReport.from_dict(raw)


def sanitized_alias(kind:str,value:str,salt:str)->str:
    digest=sha256_domain(b'MNEME-DRYRUN-SANITIZED-ALIAS-0.2',canonical_json_bytes({'kind':kind,'value':value,'salt':salt}))
    return f'{kind}-{digest[:24]}'


def render_private_report(report:DryRunReport, private_material:Mapping[str,object]|None=None)->dict[str,object]:
    return {'report':report.to_dict(),'private':deepcopy(dict(private_material or {}))}


def render_sanitized_report(private_report:Mapping[str,object],*,salt:str)->dict[str,object]:
    if not salt: raise DryRunValidationError('sanitized report requires caller-supplied salt')
    raw=deepcopy(private_report['report'])
    source=raw.get('source',{})
    if source.get('sha256'):
        source['sha256_alias']=sanitized_alias('source',str(source['sha256']),salt)
        source.pop('sha256',None)
    return {'report':raw,'privacy_mode':'sanitized'}


def report_fingerprint(report_dict:Mapping[str,object])->str:
    return sha256_domain(b'MNEME-DRYRUN-REPORT-0.2',canonical_json_bytes(report_dict))
