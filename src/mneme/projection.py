from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Iterable

from .errors import ProjectionBudgetError
from .records import MemoryRecord
from .routes import Omission


_HEADER = b"# MNEME Projection\n\n"


@dataclass(frozen=True)
class ProjectionResult:
    content: bytes
    manifest: dict[str, object]


def project_markdown(
    records: Iterable[MemoryRecord],
    *,
    source_head: str,
    route_id: str,
    byte_budget: int,
    omissions: Iterable[Omission] = (),
) -> ProjectionResult:
    if not isinstance(byte_budget, int) or isinstance(byte_budget, bool) or byte_budget <= 0:
        raise ProjectionBudgetError("byte_budget must be a positive integer")
    if len(_HEADER) > byte_budget:
        raise ProjectionBudgetError("fixed projection header exceeds byte_budget")

    content = bytearray(_HEADER)
    included_ids: list[str] = []
    omitted = [{"record_id": o.record_id, "reason": o.reason} for o in omissions]
    budget_exhausted = False

    for record in records:
        raw = record.to_dict()
        record_id = str(raw["record_id"])
        if budget_exhausted:
            omitted.append({"record_id": record_id, "reason": "budget_exceeded"})
            continue
        block = _render_record(raw)
        if len(content) + len(block) > byte_budget:
            budget_exhausted = True
            omitted.append({"record_id": record_id, "reason": "budget_exceeded"})
            continue
        content.extend(block)
        included_ids.append(record_id)

    exact = bytes(content)
    manifest: dict[str, object] = {
        "manifest_version": "mneme.projection-manifest/0.1",
        "source_head": source_head,
        "route_id": route_id,
        "byte_budget": byte_budget,
        "included_ids": included_ids,
        "omitted": omitted,
        "content_sha256": hashlib.sha256(exact).hexdigest(),
        "byte_count": len(exact),
    }
    return ProjectionResult(content=exact, manifest=manifest)


def _render_record(raw: dict[str, object]) -> bytes:
    record_id = str(raw["record_id"])
    record_type = str(raw["record_type"])
    content = raw["content"]
    text = str(content["text"])
    return f"## {record_id} [{record_type}]\n{text}\n\n".encode("utf-8")
