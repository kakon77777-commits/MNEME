from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
from typing import Iterable

from .canonical import canonical_json_bytes, sha256_domain
from .markdown_profile import MemoryMarkdownProfile, SectionRule
from .errors import ProjectionBudgetError
from .records import MemoryRecord

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_SECTION_RELATION = "mneme-md.section/0.1"
_RECORD_ID_DOMAIN = b"MNEME-MD-RECORD-ID-0.1"


@dataclass(frozen=True)
class MarkdownBlock:
    kind: str
    text: str
    start_line: int
    end_line: int
    heading_text: str | None = None


@dataclass(frozen=True)
class ProfiledImportProposal:
    records: tuple[dict[str, object], ...]
    loss_report: dict[str, object]
    mapping_receipt: dict[str, object]
    committed: bool = False


def propose_profiled_markdown_import(path: Path, profile: MemoryMarkdownProfile) -> ProfiledImportProposal:
    path = Path(path)
    source = path.read_bytes()
    source_sha = hashlib.sha256(source).hexdigest()
    text = source.decode("utf-8")
    blocks = tuple(_scan_markdown(text))

    active_rule: SectionRule | None = None
    active_heading_state = "none"
    records: list[dict[str, object]] = []
    loss: list[dict[str, object]] = []
    mappings: list[dict[str, object]] = []
    route_hints: list[str] = []

    for block in blocks:
        if block.kind == "heading":
            matched = profile.match_heading(block.heading_text or "")
            if matched is None:
                active_rule = None
                active_heading_state = "unknown"
            else:
                active_rule = matched
                active_heading_state = "known"
            continue

        if block.kind in {"code_fence", "table"}:
            loss.append(_loss(block, "unsupported_block_kind"))
            continue

        if active_heading_state == "none":
            loss.append(_loss(block, "no_active_section"))
            continue
        if active_heading_state == "unknown" or active_rule is None:
            loss.append(_loss(block, "unknown_section"))
            continue

        record_type = active_rule.block_rules.get(block.kind)
        if record_type is None:
            loss.append(_loss(block, "block_kind_not_mapped", section_id=active_rule.section_id))
            continue

        record_id = _record_id(
            profile_digest=profile.digest(),
            source_sha=source_sha,
            section_id=active_rule.section_id,
            block_kind=block.kind,
            start_line=block.start_line,
            end_line=block.end_line,
            text=block.text,
        )
        raw = {
            "record_version": "mneme.memory-record/0.1",
            "record_id": record_id,
            "record_type": record_type,
            "scope": active_rule.scope,
            "content": {"text": block.text},
            "relations": [
                {"relation_type": _SECTION_RELATION, "target": active_rule.section_id}
            ],
            "provenance": {
                "event_id": f"mneme-md-import-{record_id[3:35]}",
                "source_ref": (
                    f"mneme-md:{profile.profile_id}:{source_sha}:"
                    f"L{block.start_line}-L{block.end_line}"
                ),
            },
            "status": "active",
        }
        canonical = MemoryRecord.from_dict(raw).to_dict()
        records.append(canonical)
        mappings.append(
            {
                "record_id": record_id,
                "start_line": block.start_line,
                "end_line": block.end_line,
                "section_id": active_rule.section_id,
                "block_kind": block.kind,
                "record_type": record_type,
                "scope": active_rule.scope,
                "route_hints": list(active_rule.route_hints),
            }
        )
        for route in active_rule.route_hints:
            if route not in route_hints:
                route_hints.append(route)

    reason_counts: dict[str, int] = {}
    for item in loss:
        reason = str(item["reason"])
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    loss_report = {
        "source_sha256": source_sha,
        "profile_id": profile.profile_id,
        "profile_digest": profile.digest(),
        "block_count": sum(1 for block in blocks if block.kind != "heading"),
        "mapped_count": len(records),
        "unknown_section_count": reason_counts.get("unknown_section", 0),
        "unsupported_block_count": reason_counts.get("unsupported_block_kind", 0),
        "unmapped_count": len(loss),
        "loss": loss,
        "generated_record_ids": [str(r["record_id"]) for r in records],
        "route_hints": route_hints,
        "committed": False,
    }
    mapping_receipt = {
        "receipt_version": "mneme.memory-markdown-mapping/0.1",
        "source_sha256": source_sha,
        "profile_id": profile.profile_id,
        "profile_digest": profile.digest(),
        "mappings": mappings,
    }
    return ProfiledImportProposal(
        records=tuple(records),
        loss_report=loss_report,
        mapping_receipt=mapping_receipt,
        committed=False,
    )


def _record_id(
    *,
    profile_digest: str,
    source_sha: str,
    section_id: str,
    block_kind: str,
    start_line: int,
    end_line: int,
    text: str,
) -> str:
    payload = {
        "profile_digest": profile_digest,
        "source_sha256": source_sha,
        "section_id": section_id,
        "block_kind": block_kind,
        "start_line": start_line,
        "end_line": end_line,
        "text": text,
    }
    return "md-" + sha256_domain(_RECORD_ID_DOMAIN, canonical_json_bytes(payload))


def _scan_markdown(text: str) -> Iterable[MarkdownBlock]:
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            yield MarkdownBlock(
                kind="heading",
                text=heading.group(2),
                start_line=i + 1,
                end_line=i + 1,
                heading_text=heading.group(2),
            )
            i += 1
            continue

        if line.lstrip().startswith("```"):
            start = i
            i += 1
            while i < len(lines) and not lines[i].lstrip().startswith("```"):
                i += 1
            if i < len(lines):
                i += 1
            yield MarkdownBlock(
                kind="code_fence",
                text="\n".join(lines[start:i]),
                start_line=start + 1,
                end_line=i,
            )
            continue

        if _looks_like_table_line(line):
            start = i
            i += 1
            while i < len(lines) and lines[i].strip() and _looks_like_table_line(lines[i]):
                i += 1
            yield MarkdownBlock(
                kind="table",
                text="\n".join(lines[start:i]),
                start_line=start + 1,
                end_line=i,
            )
            continue

        if line.startswith("- "):
            yield MarkdownBlock(
                kind="unordered_list_item",
                text=line[2:].strip(),
                start_line=i + 1,
                end_line=i + 1,
            )
            i += 1
            continue

        start = i
        i += 1
        while i < len(lines):
            candidate = lines[i]
            if not candidate.strip():
                break
            if (
                _HEADING_RE.match(candidate)
                or candidate.startswith("- ")
                or candidate.lstrip().startswith("```")
                or _looks_like_table_line(candidate)
            ):
                break
            i += 1
        yield MarkdownBlock(
            kind="paragraph",
            text="\n".join(lines[start:i]),
            start_line=start + 1,
            end_line=i,
        )


def _looks_like_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def _loss(block: MarkdownBlock, reason: str, *, section_id: str | None = None) -> dict[str, object]:
    item: dict[str, object] = {
        "kind": block.kind,
        "reason": reason,
        "start_line": block.start_line,
        "end_line": block.end_line,
    }
    if section_id is not None:
        item["section_id"] = section_id
    return item


_PROFILE_HEADER = b"# MEMORY\n\n"


@dataclass(frozen=True)
class ProfiledProjectionResult:
    content: bytes
    manifest: dict[str, object]


def project_profiled_markdown(
    records: Iterable[MemoryRecord],
    *,
    profile: MemoryMarkdownProfile,
    source_head: str,
    byte_budget: int,
) -> ProfiledProjectionResult:
    if not isinstance(byte_budget, int) or isinstance(byte_budget, bool) or byte_budget <= 0:
        raise ProjectionBudgetError("byte_budget must be a positive integer")
    if len(_PROFILE_HEADER) > byte_budget:
        raise ProjectionBudgetError("fixed MEMORY header exceeds byte_budget")

    omitted: list[dict[str, str]] = []
    section_order: list[str] = []
    groups: dict[str, list[tuple[MemoryRecord, SectionRule, str]]] = {}

    for record in records:
        raw = record.to_dict()
        record_id = str(raw["record_id"])
        targets = _section_targets(raw)
        if not targets:
            omitted.append({"record_id": record_id, "reason": "profile_unmapped"})
            continue
        if len(targets) != 1:
            omitted.append({"record_id": record_id, "reason": "ambiguous_section_relation"})
            continue
        section_id = targets[0]
        rule = profile.section_by_id(section_id)
        if rule is None:
            omitted.append({"record_id": record_id, "reason": "unknown_section_relation"})
            continue
        render_kind = _render_kind(rule, str(raw["record_type"]))
        if render_kind is None:
            omitted.append({"record_id": record_id, "reason": "record_type_not_renderable"})
            continue
        item = (record, rule, render_kind)
        if section_id not in groups:
            groups[section_id] = []
            section_order.append(section_id)
        groups[section_id].append(item)

    content = bytearray(_PROFILE_HEADER)
    included_ids: list[str] = []
    for section_id in section_order:
        items = groups[section_id]
        rule = items[0][1]
        preamble = f"## {rule.render_heading}\n".encode("utf-8")
        section_bytes = bytearray(preamble)
        section_included: list[str] = []
        for record, _, render_kind in items:
            raw = record.to_dict()
            record_id = str(raw["record_id"])
            block = _render_profile_record(raw, render_kind)
            if len(content) + len(section_bytes) + len(block) + 1 > byte_budget:
                omitted.append({"record_id": record_id, "reason": "budget_exceeded"})
                continue
            section_bytes.extend(block)
            section_included.append(record_id)
        if section_included:
            section_bytes.extend(b"\n")
            content.extend(section_bytes)
            included_ids.extend(section_included)

    exact = bytes(content)
    manifest: dict[str, object] = {
        "manifest_version": "mneme.memory-markdown-projection/0.1",
        "profile_id": profile.profile_id,
        "profile_digest": profile.digest(),
        "source_head": source_head,
        "byte_budget": byte_budget,
        "included_ids": included_ids,
        "omitted": omitted,
        "content_sha256": hashlib.sha256(exact).hexdigest(),
        "byte_count": len(exact),
    }
    return ProfiledProjectionResult(content=exact, manifest=manifest)


def compatibility_entries(
    records: Iterable[MemoryRecord],
) -> tuple[tuple[str, str, str, str, str], ...]:
    entries: list[tuple[str, str, str, str, str]] = []
    for record in records:
        raw = record.to_dict()
        targets = _section_targets(raw)
        if len(targets) != 1:
            raise ValueError("compatibility entry requires exactly one MNEME-MD section relation")
        scope = raw["scope"]
        content = raw["content"]
        entries.append(
            (
                targets[0],
                str(raw["record_type"]),
                str(scope["kind"]),
                str(scope["subject"]),
                str(content["text"]),
            )
        )
    return tuple(entries)


def _section_targets(raw: dict[str, object]) -> list[str]:
    targets: list[str] = []
    for relation in raw.get("relations", []):
        if not isinstance(relation, dict):
            continue
        if relation.get("relation_type") == _SECTION_RELATION and isinstance(relation.get("target"), str):
            targets.append(relation["target"])
    return targets


def _render_kind(rule: SectionRule, record_type: str) -> str | None:
    if rule.block_rules.get("unordered_list_item") == record_type:
        return "unordered_list_item"
    if rule.block_rules.get("paragraph") == record_type:
        return "paragraph"
    return None


def _render_profile_record(raw: dict[str, object], render_kind: str) -> bytes:
    text = str(raw["content"]["text"])
    if render_kind == "unordered_list_item":
        return f"- {text}\n".encode("utf-8")
    if render_kind == "paragraph":
        return f"{text}\n".encode("utf-8")
    raise ValueError(f"unsupported render kind: {render_kind}")
