from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator

from ..canonical import canonical_json_bytes, sha256_domain
from ..errors import CpsValidationError
from ..schemas import read_schema
from .factorization import FactorizationProposal
from .models import EquivalenceContract, RecomputationReference

_VALIDATOR = Draft202012Validator(read_schema("cognitive-seed-proposal-0.1.schema.json"))


def _error_key(error) -> tuple[str, ...]:
    return tuple(str(part) for part in error.absolute_path)


def _seed_fingerprint(raw: dict[str, object]) -> str:
    payload = deepcopy(raw)
    payload.pop("seed_id", None)
    payload.pop("seed_fingerprint", None)
    return sha256_domain(b"MNEME-CPS-SEED-0.1", canonical_json_bytes(payload))


def _seed_id(raw: dict[str, object]) -> str:
    payload = deepcopy(raw)
    payload.pop("seed_id", None)
    payload.pop("seed_fingerprint", None)
    return "cs-" + sha256_domain(b"MNEME-CPS-SEED-ID-0.1", canonical_json_bytes(payload))


@dataclass(frozen=True)
class CognitiveSeedProposal:
    _raw: dict[str, Any]

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> CognitiveSeedProposal:
        candidate = deepcopy(raw)
        errors = sorted(_VALIDATOR.iter_errors(candidate), key=_error_key)
        if errors:
            error = errors[0]
            path = ".".join(str(part) for part in error.absolute_path) or "$"
            raise CpsValidationError(f"{path}: {error.message}")
        expected = _seed_fingerprint(candidate)
        if candidate["seed_fingerprint"] != expected:
            raise CpsValidationError("seed_fingerprint does not match canonical seed payload")
        return cls(candidate)

    def to_dict(self) -> dict[str, object]:
        return deepcopy(self._raw)

    def fingerprint(self) -> str:
        return _seed_fingerprint(self._raw)


def build_cognitive_seed_proposal(
    *,
    factorization: FactorizationProposal,
    anchors: list[str],
    structure: list[dict[str, object]],
    generators: list[dict[str, object]],
    obligations: list[dict[str, object]],
    provenance_refs: list[str],
    recomputation_refs: Iterable[RecomputationReference],
    unresolved_components: list[str],
    equivalence_contract: EquivalenceContract | None,
) -> CognitiveSeedProposal:
    fact = factorization.to_dict()

    missing_anchors = sorted(set(fact["anchors"]) - set(anchors))
    if missing_anchors:
        raise CpsValidationError("mandatory factorization anchors omitted: " + ", ".join(missing_anchors))

    missing_provenance = sorted(set(fact["provenance_refs"]) - set(provenance_refs))
    if missing_provenance:
        raise CpsValidationError("factorization provenance omitted: " + ", ".join(missing_provenance))

    for name, supplied in (("structure", structure), ("generators", generators), ("obligations", obligations)):
        if canonical_json_bytes(supplied) != canonical_json_bytes(fact[name]):
            raise CpsValidationError(f"seed {name} must exactly preserve source factorization components")

    resolved_refs = set(anchors) | set(provenance_refs) | set(unresolved_components)
    missing_unresolved = sorted(set(fact["unresolved_refs"]) - resolved_refs)
    if missing_unresolved:
        raise CpsValidationError(
            "factorization unresolved refs disappeared from seed: " + ", ".join(missing_unresolved)
        )

    recompute_list = list(recomputation_refs)
    recompute_by_id = {str(item.to_dict()["reference_id"]): item for item in recompute_list}
    missing_recompute = sorted(set(fact["recompute_refs"]) - set(recompute_by_id))
    if missing_recompute:
        raise CpsValidationError("unknown recomputation reference: " + ", ".join(missing_recompute))

    generative = bool(fact["generators"])
    if generative and not anchors:
        raise CpsValidationError("generative seed requires at least one anchor")
    if generative and equivalence_contract is None:
        raise CpsValidationError("generative seed requires an equivalence contract")

    without_fingerprint: dict[str, object] = {
        "seed_version": "mneme.cognitive-seed-proposal/0.1",
        "source_factorization": str(fact["proposal_id"]),
        "anchors": list(anchors),
        "structure": deepcopy(structure),
        "generators": deepcopy(generators),
        "obligations": deepcopy(obligations),
        "provenance_refs": list(provenance_refs),
        "recomputation_refs": list(recompute_by_id),
        "unresolved_components": list(unresolved_components),
        "equivalence_contract": (
            str(equivalence_contract.to_dict()["contract_id"]) if equivalence_contract is not None else None
        ),
        "authority": False,
    }
    fingerprint = _seed_fingerprint(without_fingerprint)
    seed_id = _seed_id(without_fingerprint)
    raw = {"seed_id": seed_id, **without_fingerprint, "seed_fingerprint": fingerprint}
    return CognitiveSeedProposal.from_dict(raw)
