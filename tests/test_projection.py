import hashlib

import pytest

from mneme.errors import ProjectionBudgetError
from mneme.projection import project_markdown
from mneme.routes import Omission
from tests.test_routes import rec


def test_projection_never_exceeds_hard_byte_budget():
    records = [rec(f"r{i}", "global/core") for i in range(20)]
    result = project_markdown(records, source_head="a" * 64, route_id="route://global/tier0", byte_budget=180)
    assert len(result.content) <= 180
    assert result.manifest["byte_count"] == len(result.content)
    assert result.manifest["source_head"] == "a" * 64
    assert result.manifest["omitted"]
    assert result.manifest["content_sha256"] == hashlib.sha256(result.content).hexdigest()


def test_different_budgets_bind_to_same_canonical_head_without_mutation():
    records = [rec(f"r{i}", "global/core") for i in range(5)]
    before = [r.to_dict() for r in records]
    small = project_markdown(records, source_head="b" * 64, route_id="route://global/tier0", byte_budget=100)
    large = project_markdown(records, source_head="b" * 64, route_id="route://global/tier0", byte_budget=500)
    assert small.content != large.content
    assert small.manifest["source_head"] == large.manifest["source_head"]
    assert [r.to_dict() for r in records] == before


def test_projection_never_slices_multibyte_record_block():
    first = rec("zh1", "global/core", text="記憶完整區塊")
    second = rec("zh2", "global/core", text="第二個中文區塊")
    one = project_markdown([first], source_head="c" * 64, route_id="route://global/tier0", byte_budget=500)
    exact_first_size = len(one.content)
    result = project_markdown([first, second], source_head="c" * 64, route_id="route://global/tier0", byte_budget=exact_first_size + 1)
    decoded = result.content.decode("utf-8")
    assert "記憶完整區塊" in decoded
    assert "第二個中文區塊" not in decoded
    assert any(item["record_id"] == "zh2" and item["reason"] == "budget_exceeded" for item in result.manifest["omitted"])


def test_header_that_cannot_fit_fails_explicitly():
    with pytest.raises(ProjectionBudgetError):
        project_markdown([], source_head="d" * 64, route_id="route://global/tier0", byte_budget=3)


def test_route_omissions_are_preserved_without_private_content():
    result = project_markdown([], source_head="e" * 64, route_id="route://identity/a/bootstrap", byte_budget=100, omissions=[Omission("b1", "scope_mismatch")])
    assert result.manifest["omitted"] == [{"record_id": "b1", "reason": "scope_mismatch"}]
