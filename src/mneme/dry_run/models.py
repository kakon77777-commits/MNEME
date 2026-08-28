from __future__ import annotations

from dataclasses import dataclass

from ..cps.rules import AssessmentContext


@dataclass(frozen=True)
class MappedRecordMetadata:
    record_id: str
    section_id: str
    record_type: str
    scope_kind: str
    scope_subject: str
    block_kind: str
    route_hints: tuple[str, ...]
    start_line: int
    end_line: int
    profile_id: str
    profile_digest: str


@dataclass(frozen=True)
class ContextResolution:
    record_id: str
    provenance: str
    rule_ids: tuple[str, ...]
    context: AssessmentContext
