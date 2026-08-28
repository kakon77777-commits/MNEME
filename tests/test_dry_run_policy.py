from __future__ import annotations

from copy import deepcopy

import pytest

from mneme.cps.rules import AssessmentContext
from mneme.errors import DryRunValidationError
from mneme.dry_run.models import MappedRecordMetadata
from mneme.dry_run.policy import PersistencePolicy, context_from_dict, resolve_contexts


CONTEXT_FIELDS = {
    "explicit_decision": False,
    "identity_or_authority_evidence": False,
    "historical_observation": False,
    "structural_dependency": False,
    "structural_state": False,
    "derivable_explanation": False,
    "reconstruction_recipe_ref": None,
    "obligation_set_ref": None,
    "freshness_required": False,
    "external_source_ref": None,
    "previous_observation_ref": None,
    "ephemeral_working_state": False,
    "superseded_materialization": False,
    "conflicting_evidence": False,
}


def context_dict(**changes):
    raw = dict(CONTEXT_FIELDS)
    raw.update(changes)
    return raw


def mapped_metadata(**changes):
    raw = dict(
        record_id="r1",
        section_id="standing_instructions",
        record_type="instruction",
        scope_kind="global",
        scope_subject="core",
        block_kind="unordered_list_item",
        route_hints=("route://global/tier0",),
        start_line=2,
        end_line=2,
        profile_id="evemiss-residence/0.1",
        profile_digest="0" * 64,
    )
    raw.update(changes)
    return MappedRecordMetadata(**raw)


def policy_with_rule(selector=None, context=None, rule_id="rule-1"):
    return {
        "policy_version": "mneme.persistence-policy/0.1",
        "policy_id": "synthetic/0.1",
        "rules": [{
            "rule_id": rule_id,
            "selector": selector or {"section_id": "standing_instructions"},
            "context": context or context_dict(structural_state=True),
        }],
    }


def valid_policy_dict():
    return policy_with_rule()


def policy_with_two_conflicting_rules():
    raw = policy_with_rule(rule_id="z-rule")
    raw["rules"].append({
        "rule_id": "a-rule",
        "selector": {"section_id": "standing_instructions"},
        "context": context_dict(explicit_decision=True),
    })
    return raw


def test_policy_rejects_content_selector():
    raw = policy_with_rule(selector={"content.text": "delete me"}, context=context_dict())
    with pytest.raises(DryRunValidationError):
        PersistencePolicy.from_dict(raw)


def test_policy_rejects_unknown_context_field():
    raw = valid_policy_dict()
    raw["rules"][0]["context"]["grant_authority"] = True
    with pytest.raises(DryRunValidationError):
        PersistencePolicy.from_dict(raw)


def test_policy_rejects_duplicate_rule_ids():
    raw = valid_policy_dict()
    raw["rules"].append(deepcopy(raw["rules"][0]))
    with pytest.raises(DryRunValidationError):
        PersistencePolicy.from_dict(raw)


def test_context_from_dict_uses_exact_current_cps_fields():
    ctx = context_from_dict(context_dict(explicit_decision=True, reconstruction_recipe_ref="recipe://1"))
    assert ctx == AssessmentContext(explicit_decision=True, reconstruction_recipe_ref="recipe://1")


def test_selector_matches_only_declared_metadata_fields():
    metadata = mapped_metadata(
        section_id="verification_lessons",
        record_type="lesson",
        scope_kind="global",
        scope_subject="verification",
        block_kind="unordered_list_item",
        route_hints=("route://method/verification",),
    )
    policy = PersistencePolicy.from_dict(policy_with_rule(
        selector={
            "section_id": "verification_lessons",
            "route_hint": "route://method/verification",
        },
        context=context_dict(
            derivable_explanation=True,
            reconstruction_recipe_ref="recipe://v1",
            obligation_set_ref="obligation://v1",
        ),
    ))
    resolution = resolve_contexts([metadata], policy=policy)[0]
    assert resolution.provenance == "POLICY_RULE"
    assert resolution.context.derivable_explanation is True
    assert resolution.rule_ids == ("rule-1",)


def test_route_selector_is_exact_membership_not_substring():
    metadata = mapped_metadata(route_hints=("route://method/verification",))
    policy = PersistencePolicy.from_dict(policy_with_rule(
        selector={"route_hint": "verification"},
        context=context_dict(explicit_decision=True),
    ))
    resolution = resolve_contexts([metadata], policy=policy)[0]
    assert resolution.provenance == "DEFAULT_UNKNOWN"


def test_exact_override_precedes_policy():
    metadata = mapped_metadata(record_id="r1", section_id="standing_instructions")
    policy = PersistencePolicy.from_dict(policy_with_rule(
        selector={"section_id": "standing_instructions"},
        context=context_dict(structural_state=True),
    ))
    override = {"r1": context_dict(explicit_decision=True)}
    resolution = resolve_contexts([metadata], policy=policy, exact_overrides=override)[0]
    assert resolution.provenance == "EXACT_RECORD_OVERRIDE"
    assert resolution.context.explicit_decision is True
    assert resolution.context.structural_state is False
    assert resolution.rule_ids == ()


def test_no_match_returns_empty_context():
    resolution = resolve_contexts([mapped_metadata(record_id="r1")])[0]
    assert resolution.provenance == "DEFAULT_UNKNOWN"
    assert resolution.context == AssessmentContext()


def test_nonidentical_matching_rules_become_conflict():
    policy = PersistencePolicy.from_dict(policy_with_two_conflicting_rules())
    resolution = resolve_contexts([mapped_metadata(record_id="r1")], policy=policy)[0]
    assert resolution.provenance == "POLICY_CONFLICT"
    assert resolution.context == AssessmentContext(conflicting_evidence=True)
    assert resolution.rule_ids == ("a-rule", "z-rule")


def test_identical_matching_rules_are_accepted_once_with_sorted_rule_ids():
    raw = valid_policy_dict()
    raw["rules"] = [
        {"rule_id": "z-rule", "selector": {"section_id": "standing_instructions"}, "context": context_dict(structural_state=True)},
        {"rule_id": "a-rule", "selector": {"record_type": "instruction"}, "context": context_dict(structural_state=True)},
    ]
    policy = PersistencePolicy.from_dict(raw)
    resolution = resolve_contexts([mapped_metadata()], policy=policy)[0]
    assert resolution.provenance == "POLICY_RULE"
    assert resolution.context == AssessmentContext(structural_state=True)
    assert resolution.rule_ids == ("a-rule", "z-rule")


def test_override_for_unmapped_record_is_rejected():
    with pytest.raises(DryRunValidationError):
        resolve_contexts(
            [mapped_metadata(record_id="mapped")],
            exact_overrides={"not-mapped": context_dict(explicit_decision=True)},
        )


def test_policy_digest_and_resolution_are_deterministic():
    metadata = [mapped_metadata(), mapped_metadata(record_id="r2", section_id="other")]
    a = PersistencePolicy.from_dict(valid_policy_dict())
    b = PersistencePolicy.from_dict(valid_policy_dict())
    assert a.digest() == b.digest()
    assert a.to_dict() == b.to_dict()
    assert resolve_contexts(metadata, policy=a) == resolve_contexts(metadata, policy=b)


def test_exact_override_rejects_non_boolean_context_value():
    bad = context_dict()
    bad["explicit_decision"] = "false"
    with pytest.raises(DryRunValidationError):
        resolve_contexts([mapped_metadata(record_id="r1")], exact_overrides={"r1": bad})


def test_exact_override_rejects_non_string_reference_value():
    bad = context_dict()
    bad["external_source_ref"] = 123
    with pytest.raises(DryRunValidationError):
        resolve_contexts([mapped_metadata(record_id="r1")], exact_overrides={"r1": bad})
