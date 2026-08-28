from __future__ import annotations

from pathlib import Path

from mneme.dry_run.compatibility import run_compatibility_pass
from mneme.markdown_compat import scan_markdown_blocks
from mneme.markdown_profile import load_profile


PROFILE = Path('profiles/memory-markdown/evemiss-residence-0.1.json')


def profile():
    return load_profile(PROFILE)


def write_memory(tmp_path, text):
    path = tmp_path / 'MEMORY.md'
    path.write_text(text, encoding='utf-8')
    return path


def test_public_scanner_matches_importer_block_structure():
    text = '# Standing Instructions\n- A\n\n# Unknown\n```\nnoop\n```\n'
    blocks = scan_markdown_blocks(text)
    assert [(b.kind, b.start_line, b.end_line) for b in blocks] == [
        ('heading', 1, 1),
        ('unordered_list_item', 2, 2),
        ('heading', 4, 4),
        ('code_fence', 5, 7),
    ]


def test_pass1_metadata_is_bound_to_mapping_receipt(tmp_path):
    p = profile()
    path = write_memory(tmp_path, '# Standing Instructions\n- Keep exact evidence.\n')
    result = run_compatibility_pass(path, p, projection_budgets=(20000,))
    assert len(result.records) == 1
    meta = result.metadata[0]
    mapping = result.mapping_receipt['mappings'][0]
    assert meta.record_id == mapping['record_id']
    assert meta.section_id == mapping['section_id']
    assert meta.block_kind == mapping['block_kind']
    assert (meta.start_line, meta.end_line) == (mapping['start_line'], mapping['end_line'])
    assert meta.profile_digest == p.digest()


def test_heading_inventory_includes_empty_unknown_heading(tmp_path):
    p = profile()
    path = write_memory(tmp_path, '# Standing Instructions\n- A\n\n# Strange Future Section\n\n# Verification Lessons\n- B\n')
    result = run_compatibility_pass(path, p, projection_budgets=(20000,))
    item = next(x for x in result.heading_inventory if x.matched is False)
    assert item.line_numbers == (4,)
    assert item.occurrences == 1
    assert item.body_block_count == 0


def test_repeated_unknown_heading_becomes_review_candidate_only(tmp_path):
    p = profile()
    path = write_memory(tmp_path, '# Mystery\n- one\n\n# Mystery\n- two\n')
    result = run_compatibility_pass(path, p, projection_budgets=(20000,))
    assert result.loss_reason_counts['unknown_heading'] == 2
    candidate = result.profile_candidates[0]
    assert candidate.suggested_action == 'REVIEW_FOR_PROFILE_EXTENSION'
    assert candidate.target_section is None
    assert candidate.occurrences == 2


def test_route_inventory_comes_only_from_mapping_receipt(tmp_path):
    p = profile()
    path = write_memory(tmp_path, '# Verification Lessons\n- Verify first.\n')
    result = run_compatibility_pass(path, p, projection_budgets=(20000,))
    assert {route.route_id for route in result.route_inventory} == set(result.mapping_receipt['mappings'][0]['route_hints'])


def test_projection_budgets_change_preview_not_records(tmp_path):
    p = profile()
    lines = ['# Standing Instructions'] + [f'- item {i:03d} ' + ('x' * 30) for i in range(120)]
    path = write_memory(tmp_path, '\n'.join(lines) + '\n')
    result = run_compatibility_pass(path, p, projection_budgets=(2000, 20000))
    before_ids = tuple(r.to_dict()['record_id'] for r in result.records)
    assert result.previews[0].manifest['included_ids'] != result.previews[1].manifest['included_ids']
    assert tuple(r.to_dict()['record_id'] for r in result.records) == before_ids
    assert all(preview.manifest['source_head'].startswith('dryrun:') for preview in result.previews)


def test_projection_failure_is_explicit_finding_not_pass1_exception(tmp_path):
    p = profile()
    path = write_memory(tmp_path, '# Standing Instructions\n- A\n')
    result = run_compatibility_pass(path, p, projection_budgets=(1,))
    assert result.previews == ()
    assert len(result.preview_failures) == 1
    assert result.preview_failures[0].byte_budget == 1
