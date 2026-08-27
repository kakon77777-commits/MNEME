from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re

from .records import MemoryRecord


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_RULE_SECTIONS = {"rules", "standing instructions"}


@dataclass(frozen=True)
class ImportProposal:
    records: tuple[dict[str, object], ...]
    loss_report: dict[str, object]
    committed: bool = False


def propose_markdown_import(path: Path) -> ImportProposal:
    path = Path(path)
    source = path.read_bytes()
    source_sha = hashlib.sha256(source).hexdigest()
    text = source.decode("utf-8")
    lines = text.splitlines()

    section: str | None = None
    records: list[dict[str, object]] = []
    uncertain: list[dict[str, object]] = []
    unmapped: list[dict[str, object]] = []
    block_count = 0
    i = 0

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            section = _normalize_heading(heading.group(2))
            i += 1
            continue

        if line.lstrip().startswith("```"):
            start = i + 1
            i += 1
            while i < len(lines) and not lines[i].lstrip().startswith("```"):
                i += 1
            if i < len(lines):
                i += 1
            end = i
            block_count += 1
            unmapped.append(_loss("code_fence", start, end))
            continue

        if _looks_like_table_line(line):
            start = i + 1
            i += 1
            while i < len(lines) and lines[i].strip() and _looks_like_table_line(lines[i]):
                i += 1
            end = i
            block_count += 1
            unmapped.append(_loss("table", start, end))
            continue

        if line.startswith("- "):
            start = end = i + 1
            content = line[2:].strip()
            block_count += 1
            if section in _RULE_SECTIONS and content:
                raw = {
                    "record_version": "mneme.memory-record/0.1",
                    "record_id": f"import-{source_sha[:12]}-L{start}",
                    "record_type": "instruction",
                    "scope": {"kind": "global", "subject": "import"},
                    "content": {"text": content},
                    "relations": [],
                    "provenance": {
                        "event_id": f"import-event-{source_sha[:12]}-L{start}",
                        "source_ref": f"markdown:sha256:{source_sha}:L{start}-L{end}",
                    },
                    "status": "active",
                }
                records.append(MemoryRecord.from_dict(raw).to_dict())
            else:
                uncertain.append(_loss("list_item", start, end))
            i += 1
            continue

        start = i + 1
        i += 1
        while i < len(lines):
            candidate = lines[i]
            if not candidate.strip():
                break
            if _HEADING_RE.match(candidate) or candidate.startswith("- ") or candidate.lstrip().startswith("```") or _looks_like_table_line(candidate):
                break
            i += 1
        end = i
        block_count += 1
        uncertain.append(_loss("paragraph", start, end))

    loss_report: dict[str, object] = {
        "source_sha256": source_sha,
        "block_count": block_count,
        "mapped_count": len(records),
        "uncertain_count": len(uncertain),
        "unmapped_count": len(unmapped),
        "uncertain": uncertain,
        "unmapped": unmapped,
    }
    return ImportProposal(records=tuple(records), loss_report=loss_report, committed=False)


def _normalize_heading(text: str) -> str:
    return " ".join(text.strip().casefold().split())


def _looks_like_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def _loss(kind: str, start: int, end: int) -> dict[str, object]:
    return {"kind": kind, "start_line": start, "end_line": end}
