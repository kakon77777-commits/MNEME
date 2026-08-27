from copy import deepcopy

import pytest

from mneme.errors import ProfileValidationError
from mneme.markdown_profile import MemoryMarkdownProfile, normalize_heading


def base_profile():
    return {
        "profile_version": "mneme.memory-markdown-profile/0.1",
        "profile_id": "synthetic/0.1",
        "title": "Synthetic",
        "sections": [
            {
                "section_id": "rules",
                "aliases": ["Standing Instructions"],
                "render_heading": "Standing Instructions",
                "scope": {"kind": "global", "subject": "core"},
                "block_rules": {"unordered_list_item": "instruction"},
                "route_hints": ["route://global/tier0"],
            }
        ],
    }


def test_heading_normalization_is_nfc_whitespace_casefold_only():
    assert normalize_heading("  Standing   Instructions  ") == "standing instructions"
    assert normalize_heading("Standing-Instructions") != normalize_heading("Standing Instructions")
    assert normalize_heading("Cafe\u0301") == normalize_heading("Café")


def test_profile_digest_is_stable_across_dict_key_order():
    raw = base_profile()
    reordered = {key: raw[key] for key in reversed(list(raw))}
    a = MemoryMarkdownProfile.from_dict(raw)
    b = MemoryMarkdownProfile.from_dict(reordered)
    assert a.digest() == b.digest()


def test_normalized_alias_collision_is_rejected():
    raw = deepcopy(base_profile())
    raw["sections"].append(
        {
            **deepcopy(raw["sections"][0]),
            "section_id": "other",
            "aliases": [" standing   instructions "],
        }
    )
    with pytest.raises(ProfileValidationError):
        MemoryMarkdownProfile.from_dict(raw)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r["sections"][0]["block_rules"].__setitem__("unordered_list_item", "unknown-type"),
        lambda r: r["sections"][0]["route_hints"].__setitem__(0, "not-a-route"),
        lambda r: r["sections"][0].__setitem__("render_heading", ""),
        lambda r: r["sections"].append({**deepcopy(r["sections"][0]), "aliases": ["Other"]}),
    ],
)
def test_invalid_profile_shapes_are_rejected(mutate):
    raw = deepcopy(base_profile())
    mutate(raw)
    with pytest.raises(ProfileValidationError):
        MemoryMarkdownProfile.from_dict(raw)


def test_builtin_evemiss_profile_has_only_observed_section_mappings():
    from mneme.markdown_profile import load_builtin_evemiss_profile

    profile = load_builtin_evemiss_profile()
    expected = {
        "standing instructions": ("standing_instructions", "instruction", "global", "core"),
        "verification lessons": ("verification_lessons", "lesson", "global", "verification"),
        "who / how we work": ("who_how_we_work", "instruction", "global", "collaboration"),
        "named identities": ("named_identities", "fact", "global", "identity_registry"),
        "this machine": ("this_machine", "fact", "global", "machine"),
    }
    for heading, (section_id, record_type, kind, subject) in expected.items():
        rule = profile.match_heading(heading)
        assert rule is not None
        assert rule.section_id == section_id
        assert rule.scope == {"kind": kind, "subject": subject}
        assert record_type in set(rule.block_rules.values())

    assert profile.match_heading("固定規則") is None


def test_explicit_unicode_alias_maps_only_when_declared():
    raw = base_profile()
    raw["sections"][0]["aliases"] = ["固定規則"]
    profile = MemoryMarkdownProfile.from_dict(raw)
    assert profile.match_heading("固定規則").section_id == "rules"
    assert profile.match_heading("常駐規則") is None
