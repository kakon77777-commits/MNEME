from pathlib import Path

from mneme.markdown_compat import propose_profiled_markdown_import
from mneme.markdown_profile import load_builtin_evemiss_profile


def test_profiled_import_maps_only_explicit_sections_and_preserves_source(tmp_path: Path):
    source = tmp_path / "MEMORY.md"
    source.write_text(
        "Prelude without section.\n\n"
        "# MEMORY\n\n"
        "## Standing instructions\n"
        "- Keep exact state.\n"
        "This paragraph is not mapped in this section.\n\n"
        "## Named Identities\n"
        "- Synthetic-A -> synthetic path -> test label\n\n"
        "## Unknown Section\n"
        "- Never guess this.\n\n"
        "## Verification lessons\n"
        "- Validators need negative controls.\n\n"
        "```text\nopaque\n```\n",
        encoding="utf-8",
    )
    before = source.read_bytes()
    profile = load_builtin_evemiss_profile()
    proposal = propose_profiled_markdown_import(source, profile)

    assert source.read_bytes() == before
    assert len(proposal.records) == 3
    types = [r["record_type"] for r in proposal.records]
    assert types == ["instruction", "fact", "lesson"]
    assert proposal.records[1]["scope"] == {"kind": "global", "subject": "identity_registry"}
    assert proposal.records[1]["record_type"] == "fact"
    assert all(r["record_type"] != "identity" for r in proposal.records)

    reasons = {entry["reason"] for entry in proposal.loss_report["loss"]}
    assert "no_active_section" in reasons
    assert "block_kind_not_mapped" in reasons
    assert "unknown_section" in reasons
    assert "unsupported_block_kind" in reasons
    assert proposal.committed is False


def test_profiled_import_ids_and_receipts_are_deterministic(tmp_path: Path):
    source = tmp_path / "MEMORY.md"
    source.write_text("## Standing instructions\n- Keep exact state.\n", encoding="utf-8")
    profile = load_builtin_evemiss_profile()
    first = propose_profiled_markdown_import(source, profile)
    second = propose_profiled_markdown_import(source, profile)
    assert [r["record_id"] for r in first.records] == [r["record_id"] for r in second.records]
    assert first.mapping_receipt == second.mapping_receipt
    relation = first.records[0]["relations"][0]
    assert relation == {"relation_type": "mneme-md.section/0.1", "target": "standing_instructions"}
    assert first.loss_report["profile_id"] == profile.profile_id
    assert first.loss_report["profile_digest"] == profile.digest()


def test_profiled_projection_groups_by_section_and_binds_manifest(tmp_path: Path):
    from mneme.markdown_compat import project_profiled_markdown
    from mneme.records import MemoryRecord

    source = tmp_path / "MEMORY.md"
    source.write_text(
        "## Standing instructions\n- Keep exact state.\n\n"
        "## Verification lessons\n- Use negative controls.\n",
        encoding="utf-8",
    )
    profile = load_builtin_evemiss_profile()
    proposal = propose_profiled_markdown_import(source, profile)
    records = [MemoryRecord.from_dict(raw) for raw in proposal.records]
    result = project_profiled_markdown(records, profile=profile, source_head="a" * 64, byte_budget=1000)
    text = result.content.decode("utf-8")
    assert text.startswith("# MEMORY\n\n")
    assert "## Standing Instructions\n- Keep exact state.\n" in text
    assert "## Verification Lessons\n- Use negative controls.\n" in text
    assert result.manifest["profile_id"] == profile.profile_id
    assert result.manifest["profile_digest"] == profile.digest()
    assert result.manifest["source_head"] == "a" * 64
    assert result.manifest["byte_count"] == len(result.content)
    assert result.manifest["included_ids"] == [r.to_dict()["record_id"] for r in records]


def test_profiled_projection_never_cuts_multibyte_or_partial_record(tmp_path: Path):
    from mneme.markdown_compat import project_profiled_markdown
    from mneme.records import MemoryRecord

    source = tmp_path / "MEMORY.md"
    source.write_text(
        "## Standing instructions\n"
        "- 第一條完整規則。\n"
        "- 第二條完整規則而且比較長。\n",
        encoding="utf-8",
    )
    profile = load_builtin_evemiss_profile()
    proposal = propose_profiled_markdown_import(source, profile)
    records = [MemoryRecord.from_dict(raw) for raw in proposal.records]
    full = project_profiled_markdown(records, profile=profile, source_head="b" * 64, byte_budget=1000)
    marker = "- 第二條完整規則而且比較長。\n".encode("utf-8")
    second_start = full.content.index(marker)
    budget = second_start + len(marker) - 1
    bounded = project_profiled_markdown(records, profile=profile, source_head="b" * 64, byte_budget=budget)
    assert len(bounded.content) <= budget
    assert bounded.content.decode("utf-8")
    assert "第一條完整規則。" in bounded.content.decode("utf-8")
    assert "第二條完整規則而且比較長。" not in bounded.content.decode("utf-8")
    assert any(item["reason"] == "budget_exceeded" for item in bounded.manifest["omitted"])


def test_compatibility_entries_ignore_import_ids_but_preserve_semantic_order(tmp_path: Path):
    from mneme.markdown_compat import compatibility_entries
    from mneme.records import MemoryRecord

    source = tmp_path / "MEMORY.md"
    source.write_text("## Standing instructions\n- Keep exact state.\n", encoding="utf-8")
    profile = load_builtin_evemiss_profile()
    proposal = propose_profiled_markdown_import(source, profile)
    records = [MemoryRecord.from_dict(raw) for raw in proposal.records]
    assert compatibility_entries(records) == (("standing_instructions", "instruction", "global", "core", "Keep exact state."),)


def test_profiled_import_store_projection_reimport_roundtrip(tmp_path: Path):
    from mneme.markdown_compat import compatibility_entries, project_profiled_markdown
    from mneme.records import MemoryRecord
    from mneme.store import MemoryStore
    from mneme.transactions import TransactionProposal

    source = tmp_path / "MEMORY.md"
    source.write_text(
        "## Standing instructions\n"
        "- Keep exact state.\n"
        "- Reject silent truncation.\n\n"
        "## Verification lessons\n"
        "- Use negative controls.\n",
        encoding="utf-8",
    )
    profile = load_builtin_evemiss_profile()
    proposal = propose_profiled_markdown_import(source, profile)
    original_records = [MemoryRecord.from_dict(raw) for raw in proposal.records]

    store = MemoryStore(tmp_path / "memory.mlfdir")
    store.initialize()
    tx = TransactionProposal.from_dict({
        "transaction_version": "mneme.transaction/0.1",
        "transaction_id": "tx-md-roundtrip",
        "expected_source_head": "GENESIS",
        "declared_record_count": len(original_records),
        "record_digests": [record.digest() for record in original_records],
        "records": [record.to_dict() for record in original_records],
        "authority_ref": "synthetic-authority:md-roundtrip",
        "commit_marker": "MNEME_COMMIT/0.1",
    })
    receipt = store.commit(tx)
    projected = project_profiled_markdown(tuple(store.iter_committed_records()), profile=profile, source_head=receipt.new_head, byte_budget=10_000)
    projected_path = tmp_path / "PROJECTED_MEMORY.md"
    projected_path.write_bytes(projected.content)
    reimported = propose_profiled_markdown_import(projected_path, profile)
    reimported_records = [MemoryRecord.from_dict(raw) for raw in reimported.records]

    assert compatibility_entries(original_records) == compatibility_entries(reimported_records)
    assert [r.to_dict()["record_id"] for r in original_records] != [r.to_dict()["record_id"] for r in reimported_records]
