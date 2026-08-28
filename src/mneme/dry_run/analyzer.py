from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
from pathlib import Path
from typing import Mapping

from ..errors import DryRunValidationError
from ..markdown_profile import MemoryMarkdownProfile
from .bundle import build_evidence_files, bundle_fingerprint, bundle_manifest
from .compatibility import run_compatibility_pass
from .intents import FactorizationIntent, SeedIntent, evaluate_factorization_intents, evaluate_seed_intents
from .persistence import run_persistence_pass
from .policy import PersistencePolicy
from .report import DryRunReport, build_report


@dataclass(frozen=True)
class DryRunRequest:
    source_path: Path
    markdown_profile: MemoryMarkdownProfile
    privacy_mode: str
    projection_budgets: tuple[int,...]
    expected_source_sha256: str|None=None
    persistence_policy: PersistencePolicy|None=None
    exact_record_context_overrides: Mapping[str,dict[str,object]]|None=None
    factorization_intents: tuple[FactorizationIntent,...]=()
    seed_intents: tuple[SeedIntent,...]=()
    sanitization_salt: str|None=None
    canonical_head_snapshot: str|None=None

    def validate(self):
        if self.privacy_mode not in {'private','sanitized'}: raise DryRunValidationError('privacy_mode must be private or sanitized')
        if not self.projection_budgets or any(not isinstance(x,int) or isinstance(x,bool) or x<=0 for x in self.projection_budgets): raise DryRunValidationError('projection budgets must be positive integers')
        if self.privacy_mode=='sanitized' and not self.sanitization_salt: raise DryRunValidationError('sanitized mode requires caller salt')
        if not Path(self.source_path).is_file(): raise DryRunValidationError('source_path must be an existing file')
        return self


@dataclass(frozen=True)
class DryRunResult:
    report: DryRunReport
    pass1: object|None
    pass2: object|None
    factorization_results: tuple
    seed_results: tuple
    evidence_files: dict[str,bytes]
    bundle_manifest: dict[str,object]
    bundle_fingerprint: str
    deterministic_verified: bool=False


def _policy_summary(policy):
    if policy is None: return {'policy_id':'NO_POLICY','policy_digest':None,'rule_count':0}
    return {'policy_id':policy.policy_id,'policy_digest':policy.digest(),'rule_count':len(policy.rules)}


def _blocked_report(*, source_sha:str, byte_count:int, line_count:int, profile, policy, reasons):
    raw={
      'report_version':'mneme.private-residence-dry-run/0.2','status':'BLOCKED',
      'source':{'sha256':source_sha,'byte_count':byte_count,'line_count':line_count,'mutated':'SOURCE_MUTATED' in reasons},
      'markdown_profile':{'profile_id':profile.profile_id,'profile_digest':profile.digest()},
      'persistence_policy':_policy_summary(policy),
      'pass1':{'mapped_record_count':0,'loss_count':0,'unknown_heading_count':0,'route_hint_counts':{}},
      'pass2':{'assessment_count':0,'candidate_counts':{},'context_provenance_counts':{},'required_preservation_count':0,'factorization_readiness_counts':{},'factorization_intent_count':0,'factorization_proposal_count':0,'seed_intent_count':0,'seed_proposal_count':0,'unknown_count':0},
      'risk':{'compatibility':'BLOCKED','persistence':'BLOCKED','overall':'BLOCKED','reasons':sorted(set(reasons))},
      'blocking_reasons':sorted(set(reasons)),'canonical_mutation':False,'destructive_actions':False,
    }
    return DryRunReport.from_dict(raw)


class PrivateResidenceDryRunAnalyzer:
    def analyze(self, request: DryRunRequest) -> DryRunResult:
        request.validate(); path=Path(request.source_path)
        try:
            initial=path.read_bytes(); text=initial.decode('utf-8')
        except UnicodeDecodeError:
            report=_blocked_report(source_sha='',byte_count=0,line_count=0,profile=request.markdown_profile,policy=request.persistence_policy,reasons=['UTF8_DECODE_FAILURE'])
            files=build_evidence_files(report=report,pass1=None,pass2=None,factorization_results=(),seed_results=(),privacy_mode=request.privacy_mode,salt=request.sanitization_salt,source_path=path)
            manifest=bundle_manifest(files); return DryRunResult(report,None,None,(),(),files,manifest,bundle_fingerprint(manifest))
        source_sha=hashlib.sha256(initial).hexdigest(); lines=len(text.splitlines())
        if request.expected_source_sha256 is not None and request.expected_source_sha256 != source_sha:
            report=_blocked_report(source_sha=source_sha,byte_count=len(initial),line_count=lines,profile=request.markdown_profile,policy=request.persistence_policy,reasons=['SOURCE_DIGEST_MISMATCH'])
            files=build_evidence_files(report=report,pass1=None,pass2=None,factorization_results=(),seed_results=(),privacy_mode=request.privacy_mode,salt=request.sanitization_salt,source_path=path)
            manifest=bundle_manifest(files); return DryRunResult(report,None,None,(),(),files,manifest,bundle_fingerprint(manifest))
        pass1=run_compatibility_pass(path,request.markdown_profile,request.projection_budgets)
        if pass1.source_sha256 != source_sha:
            report=_blocked_report(source_sha=source_sha,byte_count=len(initial),line_count=lines,profile=request.markdown_profile,policy=request.persistence_policy,reasons=['PASS1_SOURCE_BINDING_MISMATCH'])
            files=build_evidence_files(report=report,pass1=None,pass2=None,factorization_results=(),seed_results=(),privacy_mode=request.privacy_mode,salt=request.sanitization_salt,source_path=path)
            manifest=bundle_manifest(files); return DryRunResult(report,pass1,None,(),(),files,manifest,bundle_fingerprint(manifest))
        expected_profile_id=request.markdown_profile.profile_id
        expected_profile_digest=request.markdown_profile.digest()
        receipt_profile_id=str(pass1.mapping_receipt.get('profile_id',''))
        receipt_profile_digest=str(pass1.mapping_receipt.get('profile_digest',''))
        if (receipt_profile_id != expected_profile_id or receipt_profile_digest != expected_profile_digest or
            any(m.profile_id != expected_profile_id or m.profile_digest != expected_profile_digest for m in pass1.metadata)):
            report=_blocked_report(source_sha=source_sha,byte_count=len(initial),line_count=lines,profile=request.markdown_profile,policy=request.persistence_policy,reasons=['PASS1_PROFILE_BINDING_MISMATCH'])
            files=build_evidence_files(report=report,pass1=None,pass2=None,factorization_results=(),seed_results=(),privacy_mode=request.privacy_mode,salt=request.sanitization_salt,source_path=path)
            manifest=bundle_manifest(files); return DryRunResult(report,pass1,None,(),(),files,manifest,bundle_fingerprint(manifest))
        try:
            pass2=run_persistence_pass(pass1.records,pass1.metadata,policy=request.persistence_policy,exact_overrides=request.exact_record_context_overrides)
            assessments={str(a.to_dict()['subject_refs'][0]):a for a in pass2.assessments}
            fresults=evaluate_factorization_intents(request.factorization_intents,pass1_record_ids={m.record_id for m in pass1.metadata},assessments_by_record=assessments)
            accepted={r.intent_id:r.proposal for r in fresults if r.status=='ACCEPTED' and r.proposal is not None}
            sresults=evaluate_seed_intents(request.seed_intents,accepted_factorizations=accepted)
        except DryRunValidationError as exc:
            report=_blocked_report(source_sha=source_sha,byte_count=len(initial),line_count=lines,profile=request.markdown_profile,policy=request.persistence_policy,reasons=['DRY_RUN_VALIDATION_ERROR'])
            files=build_evidence_files(report=report,pass1=None,pass2=None,factorization_results=(),seed_results=(),privacy_mode=request.privacy_mode,salt=request.sanitization_salt,source_path=path)
            manifest=bundle_manifest(files); return DryRunResult(report,pass1,None,(),(),files,manifest,bundle_fingerprint(manifest))
        final=path.read_bytes(); final_sha=hashlib.sha256(final).hexdigest(); blockers=[]
        if final_sha != source_sha: blockers.append('SOURCE_MUTATED')
        report=build_report(source_sha256=source_sha,source_byte_count=len(initial),source_line_count=lines,source_mutated=bool(blockers),
            profile_id=request.markdown_profile.profile_id,profile_digest=request.markdown_profile.digest(),policy_summary=_policy_summary(request.persistence_policy),
            pass1=pass1,pass2=pass2,factorization_results=fresults,seed_results=sresults,blocking_reasons=blockers)
        files=build_evidence_files(report=report,pass1=pass1,pass2=pass2,factorization_results=fresults,seed_results=sresults,privacy_mode=request.privacy_mode,salt=request.sanitization_salt,source_path=path)
        manifest=bundle_manifest(files)
        return DryRunResult(report,pass1,pass2,fresults,sresults,files,manifest,bundle_fingerprint(manifest))

    def verify_deterministic(self, request: DryRunRequest) -> DryRunResult:
        first=self.analyze(request); second=self.analyze(request)
        if first.bundle_fingerprint == second.bundle_fingerprint:
            return replace(first,deterministic_verified=True)
        raw=first.report.to_dict(); reasons=sorted(set(raw['blocking_reasons'])|{'DETERMINISTIC_REPLAY_MISMATCH'})
        raw['status']='BLOCKED'; raw['blocking_reasons']=reasons; raw['risk']={'compatibility':'BLOCKED','persistence':'BLOCKED','overall':'BLOCKED','reasons':reasons}
        report = DryRunReport.from_dict(raw)
        files = build_evidence_files(
            report=report,
            pass1=first.pass1,
            pass2=first.pass2,
            factorization_results=first.factorization_results,
            seed_results=first.seed_results,
            privacy_mode=request.privacy_mode,
            salt=request.sanitization_salt,
            source_path=Path(request.source_path),
        )
        manifest = bundle_manifest(files)
        return replace(
            first,
            report=report,
            evidence_files=files,
            bundle_manifest=manifest,
            bundle_fingerprint=bundle_fingerprint(manifest),
            deterministic_verified=False,
        )
