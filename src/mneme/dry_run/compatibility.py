from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections import Counter, defaultdict

from ..markdown_compat import (
    ProfiledProjectionResult,
    project_profiled_markdown,
    propose_profiled_markdown_import,
    scan_markdown_blocks,
)
from ..markdown_profile import MemoryMarkdownProfile, normalize_heading
from ..errors import ProjectionBudgetError
from ..records import MemoryRecord
from .models import MappedRecordMetadata


@dataclass(frozen=True)
class HeadingInventoryItem:
    normalized_heading: str
    matched: bool
    matched_section_id: str | None
    occurrences: int
    line_numbers: tuple[int, ...]
    body_block_count: int


@dataclass(frozen=True)
class ProfileExtensionCandidate:
    normalized_heading: str
    occurrences: int
    line_numbers: tuple[int, ...]
    body_block_count: int
    suggested_action: str = "REVIEW_FOR_PROFILE_EXTENSION"
    target_section: None = None


@dataclass(frozen=True)
class RouteInventoryItem:
    route_id: str
    record_count: int
    contributing_section_ids: tuple[str, ...]


@dataclass(frozen=True)
class PreviewFailure:
    byte_budget: int
    error: str


@dataclass(frozen=True)
class CompatibilityPassResult:
    records: tuple[MemoryRecord, ...]
    metadata: tuple[MappedRecordMetadata, ...]
    mapping_receipt: dict[str, object]
    loss_report: dict[str, object]
    loss_reason_counts: dict[str, int]
    heading_inventory: tuple[HeadingInventoryItem, ...]
    profile_candidates: tuple[ProfileExtensionCandidate, ...]
    route_inventory: tuple[RouteInventoryItem, ...]
    previews: tuple[ProfiledProjectionResult, ...]
    preview_failures: tuple[PreviewFailure, ...]
    source_sha256: str


def _heading_inventory(text: str, profile: MemoryMarkdownProfile) -> tuple[HeadingInventoryItem, ...]:
    blocks = scan_markdown_blocks(text)
    aggregate: dict[tuple[str, bool, str | None], dict[str, object]] = {}
    active_key: tuple[str, bool, str | None] | None = None
    for block in blocks:
        if block.kind == "heading":
            normalized = normalize_heading(block.heading_text or block.text)
            matched_rule = profile.match_heading(block.heading_text or block.text)
            key = (normalized, matched_rule is not None, matched_rule.section_id if matched_rule else None)
            data = aggregate.setdefault(key, {"lines": [], "body": 0})
            data["lines"].append(block.start_line)
            active_key = key
        elif active_key is not None:
            aggregate[active_key]["body"] += 1
    items = [
        HeadingInventoryItem(
            normalized_heading=key[0],
            matched=key[1],
            matched_section_id=key[2],
            occurrences=len(value["lines"]),
            line_numbers=tuple(value["lines"]),
            body_block_count=int(value["body"]),
        )
        for key, value in aggregate.items()
    ]
    return tuple(sorted(items, key=lambda item: (item.line_numbers[0], item.normalized_heading)))


def run_compatibility_pass(
    source_path: Path,
    profile: MemoryMarkdownProfile,
    projection_budgets: tuple[int, ...],
) -> CompatibilityPassResult:
    source_path = Path(source_path)
    proposal = propose_profiled_markdown_import(source_path, profile)
    records = tuple(MemoryRecord.from_dict(raw) for raw in proposal.records)
    mappings = proposal.mapping_receipt["mappings"]
    metadata: list[MappedRecordMetadata] = []
    by_id = {str(record.to_dict()["record_id"]): record for record in records}
    for mapping in mappings:
        record_id = str(mapping["record_id"])
        raw = by_id[record_id].to_dict()
        scope = raw["scope"]
        metadata.append(MappedRecordMetadata(
            record_id=record_id,
            section_id=str(mapping["section_id"]),
            record_type=str(mapping["record_type"]),
            scope_kind=str(scope["kind"]),
            scope_subject=str(scope["subject"]),
            block_kind=str(mapping["block_kind"]),
            route_hints=tuple(str(x) for x in mapping["route_hints"]),
            start_line=int(mapping["start_line"]),
            end_line=int(mapping["end_line"]),
            profile_id=profile.profile_id,
            profile_digest=profile.digest(),
        ))

    reasons = Counter(str(item["reason"]) for item in proposal.loss_report["loss"])
    headings = _heading_inventory(source_path.read_text(encoding="utf-8"), profile)
    candidates = tuple(
        ProfileExtensionCandidate(
            normalized_heading=item.normalized_heading,
            occurrences=item.occurrences,
            line_numbers=item.line_numbers,
            body_block_count=item.body_block_count,
        )
        for item in headings if not item.matched and item.occurrences >= 2
    )

    route_counts: Counter[str] = Counter()
    route_sections: dict[str, set[str]] = defaultdict(set)
    for mapping in mappings:
        for route in mapping["route_hints"]:
            route_counts[str(route)] += 1
            route_sections[str(route)].add(str(mapping["section_id"]))
    routes = tuple(
        RouteInventoryItem(route, route_counts[route], tuple(sorted(route_sections[route])))
        for route in sorted(route_counts)
    )

    source_sha = str(proposal.mapping_receipt["source_sha256"])
    source_head = f"dryrun:{source_sha[:16]}:{profile.digest()[:16]}"
    preview_items: list[ProfiledProjectionResult] = []
    preview_failures: list[PreviewFailure] = []
    for budget in projection_budgets:
        try:
            preview_items.append(project_profiled_markdown(records, profile=profile, source_head=source_head, byte_budget=budget))
        except ProjectionBudgetError as exc:
            preview_failures.append(PreviewFailure(int(budget), str(exc)))
    return CompatibilityPassResult(
        records=records,
        metadata=tuple(metadata),
        mapping_receipt=proposal.mapping_receipt,
        loss_report=proposal.loss_report,
        loss_reason_counts=dict(sorted(reasons.items())),
        heading_inventory=headings,
        profile_candidates=candidates,
        route_inventory=routes,
        previews=tuple(preview_items),
        preview_failures=tuple(preview_failures),
        source_sha256=source_sha,
    )
