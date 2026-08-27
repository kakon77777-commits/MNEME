import hashlib

from mneme.markdown_import import propose_markdown_import


def test_markdown_import_never_mutates_source_and_reports_uncertain_blocks(tmp_path):
    source = tmp_path / "MEMORY.md"
    source.write_text("# Rules\n\n- Keep this rule.\n\nFree prose with unclear scope.\n", encoding="utf-8")
    before = source.read_bytes()
    proposal = propose_markdown_import(source)
    assert source.read_bytes() == before
    assert proposal.loss_report["source_sha256"] == hashlib.sha256(before).hexdigest()
    assert proposal.loss_report["block_count"] >= 2
    assert proposal.loss_report["mapped_count"] == 1
    assert proposal.loss_report["uncertain_count"] >= 1
    assert proposal.committed is False
    assert proposal.records[0]["record_type"] == "instruction"
    assert proposal.records[0]["content"]["text"] == "Keep this rule."


def test_non_rule_list_is_not_guessed_as_instruction(tmp_path):
    source = tmp_path / "MEMORY.md"
    source.write_text("# Notes\n\n- Maybe important.\n", encoding="utf-8")
    proposal = propose_markdown_import(source)
    assert proposal.records == ()
    assert proposal.loss_report["uncertain_count"] == 1


def test_code_fence_and_table_are_explicitly_accounted_as_unmapped(tmp_path):
    source = tmp_path / "MEMORY.md"
    source.write_text("# Rules\n\n```text\nopaque\n```\n\n| A | B |\n|---|---|\n| 1 | 2 |\n", encoding="utf-8")
    proposal = propose_markdown_import(source)
    kinds = {item["kind"] for item in proposal.loss_report["unmapped"]}
    assert "code_fence" in kinds
    assert "table" in kinds
    assert proposal.loss_report["unmapped_count"] >= 2


def test_import_record_provenance_binds_source_hash_and_line_range(tmp_path):
    source = tmp_path / "MEMORY.md"
    source.write_text("# Standing Instructions\n\n- Be deterministic.\n", encoding="utf-8")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    proposal = propose_markdown_import(source)
    record = proposal.records[0]
    assert digest in record["provenance"]["source_ref"]
    assert "L3-L3" in record["provenance"]["source_ref"]
    assert record["scope"] == {"kind": "global", "subject": "import"}
