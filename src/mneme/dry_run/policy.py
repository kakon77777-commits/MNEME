from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
from dataclasses import dataclass

from jsonschema import Draft202012Validator

from ..canonical import canonical_json_bytes, sha256_domain
from ..cps.rules import AssessmentContext
from ..errors import DryRunValidationError
from ..schemas import read_schema
from .models import ContextResolution, MappedRecordMetadata

_VALIDATOR = Draft202012Validator(read_schema("persistence-policy-0.1.schema.json"))
_CONTEXT_FIELDS = (
    "explicit_decision",
    "identity_or_authority_evidence",
    "historical_observation",
    "structural_dependency",
    "structural_state",
    "derivable_explanation",
    "reconstruction_recipe_ref",
    "obligation_set_ref",
    "freshness_required",
    "external_source_ref",
    "previous_observation_ref",
    "ephemeral_working_state",
    "superseded_materialization",
    "conflicting_evidence",
)


def _error_key(error) -> tuple[str, ...]:
    return tuple(str(part) for part in error.absolute_path)


@dataclass(frozen=True)
class PersistencePolicy:
    _raw: dict[str, object]

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> PersistencePolicy:
        candidate = deepcopy(raw)
        errors = sorted(_VALIDATOR.iter_errors(candidate), key=_error_key)
        if errors:
            error = errors[0]
            path = ".".join(str(part) for part in error.absolute_path) or "$"
            raise DryRunValidationError(f"{path}: {error.message}")
        ids = [str(rule["rule_id"]) for rule in candidate["rules"]]
        if len(ids) != len(set(ids)):
            raise DryRunValidationError("duplicate persistence-policy rule_id")
        for rule in candidate["rules"]:
            context_from_dict(rule["context"])
        return cls(candidate)

    def to_dict(self) -> dict[str, object]:
        return deepcopy(self._raw)

    @property
    def policy_id(self) -> str:
        return str(self._raw["policy_id"])

    @property
    def rules(self) -> tuple[dict[str, object], ...]:
        return tuple(deepcopy(self._raw["rules"]))

    def digest(self) -> str:
        return sha256_domain(
            b"MNEME-DRYRUN-POLICY-0.1",
            canonical_json_bytes(self.to_dict()),
        )


def context_from_dict(raw: Mapping[str, object]) -> AssessmentContext:
    if set(raw) != set(_CONTEXT_FIELDS):
        missing = sorted(set(_CONTEXT_FIELDS) - set(raw))
        extra = sorted(set(raw) - set(_CONTEXT_FIELDS))
        raise DryRunValidationError(f"invalid AssessmentContext fields; missing={missing}, extra={extra}")

    boolean_fields = {
        "explicit_decision",
        "identity_or_authority_evidence",
        "historical_observation",
        "structural_dependency",
        "structural_state",
        "derivable_explanation",
        "freshness_required",
        "ephemeral_working_state",
        "superseded_materialization",
        "conflicting_evidence",
    }
    reference_fields = {
        "reconstruction_recipe_ref",
        "obligation_set_ref",
        "external_source_ref",
        "previous_observation_ref",
    }
    for field in sorted(boolean_fields):
        if type(raw[field]) is not bool:
            raise DryRunValidationError(f"AssessmentContext.{field} must be boolean")
    for field in sorted(reference_fields):
        value = raw[field]
        if value is not None and not isinstance(value, str):
            raise DryRunValidationError(f"AssessmentContext.{field} must be string or null")

    return AssessmentContext(**{name: raw[name] for name in _CONTEXT_FIELDS})


def _context_dict(ctx: AssessmentContext) -> dict[str, object]:
    return {name: getattr(ctx, name) for name in _CONTEXT_FIELDS}


def _matches(metadata: MappedRecordMetadata, selector: Mapping[str, object]) -> bool:
    for key, expected in selector.items():
        if key == "route_hint":
            if expected not in metadata.route_hints:
                return False
        elif getattr(metadata, key) != expected:
            return False
    return True


def resolve_contexts(
    metadata: Iterable[MappedRecordMetadata],
    *,
    policy: PersistencePolicy | None = None,
    exact_overrides: Mapping[str, Mapping[str, object]] | None = None,
) -> tuple[ContextResolution, ...]:
    items = tuple(metadata)
    known_ids = {item.record_id for item in items}
    overrides = dict(exact_overrides or {})
    unknown_overrides = sorted(set(overrides) - known_ids)
    if unknown_overrides:
        raise DryRunValidationError("exact context override references unmapped record: " + ", ".join(unknown_overrides))

    output: list[ContextResolution] = []
    rules = policy.rules if policy is not None else ()
    for item in items:
        if item.record_id in overrides:
            output.append(ContextResolution(
                record_id=item.record_id,
                provenance="EXACT_RECORD_OVERRIDE",
                rule_ids=(),
                context=context_from_dict(overrides[item.record_id]),
            ))
            continue

        matches: list[tuple[str, AssessmentContext]] = []
        for rule in rules:
            if _matches(item, rule["selector"]):
                matches.append((str(rule["rule_id"]), context_from_dict(rule["context"])))
        if not matches:
            output.append(ContextResolution(item.record_id, "DEFAULT_UNKNOWN", (), AssessmentContext()))
            continue

        rule_ids = tuple(sorted(rule_id for rule_id, _ in matches))
        unique_contexts = {canonical_json_bytes(_context_dict(ctx)) for _, ctx in matches}
        if len(unique_contexts) > 1:
            output.append(ContextResolution(
                item.record_id,
                "POLICY_CONFLICT",
                rule_ids,
                AssessmentContext(conflicting_evidence=True),
            ))
        else:
            output.append(ContextResolution(item.record_id, "POLICY_RULE", rule_ids, matches[0][1]))
    return tuple(output)
