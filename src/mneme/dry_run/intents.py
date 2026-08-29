from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator

from ..cps.adapter import CpsObservationAdapter
from ..cps.factorization import FactorizationProposal
from ..cps.models import (
    EquivalenceContract,
    PersistenceAssessment,
    RecomputationReference,
)
from ..cps.seed import CognitiveSeedProposal
from ..errors import CpsValidationError, DryRunValidationError
from ..schemas import read_schema

_F_VALIDATOR = Draft202012Validator(
    read_schema("factorization-intent-0.1.schema.json")
)
_S_VALIDATOR = Draft202012Validator(read_schema("seed-intent-0.1.schema.json"))


def _validate(validator, raw):
    errors=sorted(validator.iter_errors(raw), key=lambda e: tuple(str(x) for x in e.absolute_path))
    if errors:
        e=errors[0]; path='.'.join(str(x) for x in e.absolute_path) or '$'
        raise DryRunValidationError(f'{path}: {e.message}')


@dataclass(frozen=True)
class FactorizationIntent:
    _raw: dict[str, Any]
    @classmethod
    def from_dict(cls, raw):
        candidate=deepcopy(raw); _validate(_F_VALIDATOR,candidate); return cls(candidate)
    def to_dict(self): return deepcopy(self._raw)
    @property
    def intent_id(self): return str(self._raw['intent_id'])


@dataclass(frozen=True)
class SeedIntent:
    _raw: dict[str, Any]
    @classmethod
    def from_dict(cls, raw):
        candidate=deepcopy(raw); _validate(_S_VALIDATOR,candidate); return cls(candidate)
    def to_dict(self): return deepcopy(self._raw)
    @property
    def seed_intent_id(self): return str(self._raw['seed_intent_id'])


@dataclass(frozen=True)
class FactorizationIntentResult:
    intent_id: str
    status: str
    error_code: str | None = None
    error_message: str | None = None
    proposal: FactorizationProposal | None = None


@dataclass(frozen=True)
class SeedIntentResult:
    seed_intent_id: str
    status: str
    error_code: str | None = None
    error_message: str | None = None
    proposal: CognitiveSeedProposal | None = None


def evaluate_factorization_intents(
    intents: Iterable[FactorizationIntent], *, pass1_record_ids: set[str],
    assessments_by_record: Mapping[str, PersistenceAssessment],
) -> tuple[FactorizationIntentResult,...]:
    intent_list=tuple(intents); counts=Counter(intent.intent_id for intent in intent_list)
    out=[]; adapter=CpsObservationAdapter()
    for intent in intent_list:
        if counts[intent.intent_id] > 1:
            out.append(FactorizationIntentResult(intent.intent_id,'REJECTED','DUPLICATE_INTENT_ID','duplicate factorization intent_id')); continue
        raw=intent.to_dict(); subjects=[str(x) for x in raw['subject_record_ids']]
        if not set(subjects).issubset(pass1_record_ids):
            out.append(FactorizationIntentResult(intent.intent_id,'REJECTED','CROSS_PASS_SUBJECT','subject not in PASS 1')); continue
        if any(s not in assessments_by_record for s in subjects):
            out.append(FactorizationIntentResult(intent.intent_id,'REJECTED','MISSING_ASSESSMENT','missing PASS 2 assessment')); continue
        try:
            proposal=adapter.factorize(
                assessments=[assessments_by_record[s] for s in subjects], source_refs=subjects,
                anchors=list(raw['anchors']), structure=deepcopy(raw['structure']), generators=deepcopy(raw['generators']),
                obligations=deepcopy(raw['obligations']), provenance_refs=list(raw['provenance_refs']),
                recompute_refs=list(raw['recompute_refs']), unresolved_refs=list(raw['unresolved_refs']))
        except CpsValidationError as exc:
            out.append(FactorizationIntentResult(intent.intent_id,'REJECTED','CPS_REJECTED',str(exc))); continue
        out.append(FactorizationIntentResult(intent.intent_id,'ACCEPTED',proposal=proposal))
    return tuple(out)


def evaluate_seed_intents(
    intents: Iterable[SeedIntent], *, accepted_factorizations: Mapping[str, FactorizationProposal],
) -> tuple[SeedIntentResult,...]:
    intent_list=tuple(intents); counts=Counter(intent.seed_intent_id for intent in intent_list)
    out=[]; adapter=CpsObservationAdapter()
    for intent in intent_list:
        if counts[intent.seed_intent_id] > 1:
            out.append(SeedIntentResult(intent.seed_intent_id,'REJECTED','DUPLICATE_INTENT_ID','duplicate seed intent_id')); continue
        raw=intent.to_dict(); fid=str(raw['factorization_intent_id'])
        factorization=accepted_factorizations.get(fid)
        if factorization is None:
            out.append(SeedIntentResult(intent.seed_intent_id,'REJECTED','UNKNOWN_FACTORIZATION_INTENT','accepted factorization not found')); continue
        try:
            recompute=[RecomputationReference.from_dict(item) for item in raw['recomputation_references']]
            eq=EquivalenceContract.from_dict(raw['equivalence_contract']) if raw['equivalence_contract'] is not None else None
            proposal=adapter.propose_seed(
                factorization=factorization, anchors=list(raw['anchors']), structure=deepcopy(raw['structure']),
                generators=deepcopy(raw['generators']), obligations=deepcopy(raw['obligations']),
                provenance_refs=list(raw['provenance_refs']), recomputation_refs=recompute,
                unresolved_components=list(raw['unresolved_components']), equivalence_contract=eq)
        except CpsValidationError as exc:
            out.append(SeedIntentResult(intent.seed_intent_id,'REJECTED','CPS_REJECTED',str(exc))); continue
        out.append(SeedIntentResult(intent.seed_intent_id,'ACCEPTED',proposal=proposal))
    return tuple(out)
