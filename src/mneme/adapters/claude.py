from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ..claude_contracts import (
    CLAUDE_GLOBAL_NONCLAIMS,
    ClaudeGlobalProjectionManifest,
    ClaudeGlobalProjectionRequest,
)
from ..errors import (
    ClaudeContractError,
    ClaudeRouteError,
    RequiredRecordOmittedError,
)
from ..projection import project_markdown
from ..records import MemoryRecord
from ..routes import Omission, Route, scope_path
from ..store import MemoryStore

_ROUTE_ID = "route://global/tier0"
_ROUTE_PREFIXES = ("global",)
_RECORD_TYPES = frozenset(("instruction", "fact", "lesson"))
_GENERATOR_VERSION = "mneme.claude-projection/0.1"


@dataclass(frozen=True)
class ClaudeGlobalProjectionResult:
    content: bytes
    manifest: ClaudeGlobalProjectionManifest

    def __post_init__(self) -> None:
        if not isinstance(self.content, bytes):
            raise ClaudeContractError("projection content must be immutable bytes")
        if not isinstance(self.manifest, ClaudeGlobalProjectionManifest):
            raise ClaudeContractError("projection manifest type is invalid")
        self.manifest.verify()
        if len(self.content) != self.manifest.content_bytes:
            raise ClaudeContractError("projection content byte count mismatch")
        observed = hashlib.sha256(self.content).hexdigest()
        if observed != self.manifest.content_sha256:
            raise ClaudeContractError("projection content digest mismatch")


class ClaudeGlobalMemoryAdapter:
    def __init__(self, store: MemoryStore, route: Route):
        self._validate_route(route)
        self._store = store
        self._route = route

    @staticmethod
    def _validate_route(route: Route) -> None:
        if not isinstance(route, Route):
            raise ClaudeRouteError("Claude route must be a validated Route")
        if route.route_id != _ROUTE_ID:
            raise ClaudeRouteError("Claude route must be route://global/tier0")
        if route.scope_prefixes != _ROUTE_PREFIXES:
            raise ClaudeRouteError("Claude route must have the exact global scope prefix")
        if set(route.record_types) != _RECORD_TYPES or len(route.record_types) != len(
            _RECORD_TYPES
        ):
            raise ClaudeRouteError("Claude route must have the exact global record types")

    def materialize(
        self,
        request: ClaudeGlobalProjectionRequest,
    ) -> ClaudeGlobalProjectionResult:
        self._validate_route(self._route)
        if not isinstance(request, ClaudeGlobalProjectionRequest):
            raise ClaudeRouteError("Claude projection request type is invalid")
        request.verify()
        if request.route_id != self._route.route_id:
            raise ClaudeRouteError("request route does not match configured route")

        source_head = self._store.head()
        if request.expected_source_head != source_head:
            raise ClaudeRouteError("request source head is stale")

        records = tuple(self._store.iter_committed_records())
        self._require_stable_head(source_head)
        selected, omissions = self._select_records(request, records)
        projected = project_markdown(
            selected,
            source_head=source_head,
            route_id=request.route_id,
            byte_budget=request.byte_budget,
            omissions=omissions,
        )
        self._require_stable_head(source_head)

        included_ids = tuple(projected.manifest["included_ids"])
        missing_required = sorted(set(request.required_record_ids).difference(included_ids))
        if missing_required:
            joined = ", ".join(missing_required)
            raise RequiredRecordOmittedError(f"required record omitted: {joined}")

        manifest = ClaudeGlobalProjectionManifest.sealed(
            {
                "manifest_version": "mneme.claude-global-projection-manifest/0.1",
                "projection_ref": request.projection_ref,
                "request_ref": request.request_id,
                "request_digest": request.digest,
                "source_head": source_head,
                "route_id": request.route_id,
                "byte_budget": request.byte_budget,
                "content_bytes": projected.manifest["byte_count"],
                "content_sha256": projected.manifest["content_sha256"],
                "included_record_ids": list(included_ids),
                "omitted": projected.manifest["omitted"],
                "required_record_ids": list(request.required_record_ids),
                "generator_version": _GENERATOR_VERSION,
                "not_claimed": list(CLAUDE_GLOBAL_NONCLAIMS),
            }
        )
        return ClaudeGlobalProjectionResult(content=projected.content, manifest=manifest)

    def _require_stable_head(self, expected: str) -> None:
        if self._store.head() != expected:
            raise ClaudeRouteError("source head changed during materialization")

    @staticmethod
    def _select_records(
        request: ClaudeGlobalProjectionRequest,
        records: tuple[MemoryRecord, ...],
    ) -> tuple[tuple[MemoryRecord, ...], tuple[Omission, ...]]:
        selected: list[MemoryRecord] = []
        omitted: list[Omission] = []
        allowed_scopes = set(request.allowed_scope_paths)
        for record in records:
            raw = record.to_dict()
            record_id = str(raw["record_id"])
            if scope_path(record) not in allowed_scopes:
                omitted.append(Omission(record_id, "scope_not_allowed"))
            elif raw["status"] != "active":
                omitted.append(Omission(record_id, "status_not_active"))
            elif raw["record_type"] not in _RECORD_TYPES:
                omitted.append(Omission(record_id, "record_type_not_allowed"))
            else:
                selected.append(record)
        return tuple(selected), tuple(omitted)
