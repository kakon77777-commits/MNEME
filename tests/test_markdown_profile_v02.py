from pathlib import Path

from mneme.markdown_compat import compatibility_entries, project_profiled_markdown, propose_profiled_markdown_import
from mneme.markdown_profile import load_builtin_evemiss_profile, load_builtin_evemiss_profile_v02
from mneme.records import MemoryRecord

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "synthetic" / "memory-markdown-real-dialect-v02.md"


def test_v01_digest_remains_frozen():
    assert load_builtin_evemiss_profile().digest() == "0757299afd2d72d9cd0f3f3c7ff616f17836edff2b694afc0340d0eea055fdeb"


def test_v02_loads_observed_memory_index_and_tier1_identity_alias():
    profile = load_builtin_evemiss_profile_v02()
    assert profile.profile_id == "evemiss-residence/0.2"
    assert profile.match_heading("Memory Index").section_id == "memory_index"
    assert profile.match_heading("Named Identities (Tier 1 Residences)").section_id == "named_identities"
    assert profile.match_heading("Named Identities").section_id == "named_identities"


def test_v02_maps_synthetic_real_dialect_and_keeps_mixed_registry_paragraph_unresolved():
    profile = load_builtin_evemiss_profile_v02()
    result = propose_profiled_markdown_import(FIXTURE, profile)
    assert len(result.records) == 6
    assert len(result.loss_report["loss"]) == 1
    assert [item["reason"] for item in result.loss_report["loss"]] == ["block_kind_not_mapped"]
    assert result.loss_report["loss"][0]["section_id"] == "named_identities"
    assert result.loss_report["loss"][0]["kind"] == "paragraph"


def test_v01_does_not_guess_v02_only_headings():
    profile = load_builtin_evemiss_profile()
    result = propose_profiled_markdown_import(FIXTURE, profile)
    reasons = [item["reason"] for item in result.loss_report["loss"]]
    assert reasons.count("unknown_heading") == 2
    assert len(result.records) < 6


def test_v02_still_rejects_undeclared_identity_synonym(tmp_path):
    path = tmp_path / "MEMORY.md"
    path.write_text("## Named Residents\n- Synthetic resident.\n", encoding="utf-8")
    result = propose_profiled_markdown_import(path, load_builtin_evemiss_profile_v02())
    assert len(result.records) == 0
    assert any(item["reason"] == "unknown_heading" for item in result.loss_report["loss"])


def test_v02_projection_reimports_to_same_compatibility_entries(tmp_path):
    profile = load_builtin_evemiss_profile_v02()
    first = propose_profiled_markdown_import(FIXTURE, profile)
    records = tuple(MemoryRecord.from_dict(raw) for raw in first.records)
    projection = project_profiled_markdown(records, profile=profile, source_head="synthetic-v02", byte_budget=64000)
    projected = tmp_path / "MEMORY.md"
    projected.write_bytes(projection.content)
    second = propose_profiled_markdown_import(projected, profile)
    second_records = tuple(MemoryRecord.from_dict(raw) for raw in second.records)
    assert compatibility_entries(records) == compatibility_entries(second_records)
