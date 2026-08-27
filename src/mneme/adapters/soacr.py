from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ..projection import ProjectionResult, project_markdown
from ..routes import Route, RouteResolver
from ..store import MemoryStore


@dataclass(frozen=True)
class MemoryNeedRequest:
    identity_scope: str
    route_id: str
    byte_budget: int

    def __post_init__(self) -> None:
        if not isinstance(self.identity_scope, str) or not self.identity_scope.startswith("identity/") or len(self.identity_scope.split("/", 1)[1]) == 0:
            raise ValueError("identity_scope must be identity/<id>")
        if not isinstance(self.route_id, str) or not self.route_id.startswith("route://"):
            raise ValueError("route_id must start with route://")
        if not isinstance(self.byte_budget, int) or isinstance(self.byte_budget, bool) or self.byte_budget <= 0:
            raise ValueError("byte_budget must be a positive integer")


class MnemeReadAdapter:
    def __init__(self, store: MemoryStore, routes: Mapping[str, Route]):
        self._store = store
        self._routes = dict(routes)
        self._resolver = RouteResolver()

    def materialize(self, request: MemoryNeedRequest, authorized_scopes: set[str]) -> ProjectionResult:
        route = self._routes.get(request.route_id)
        if route is None:
            raise KeyError(f"unknown route: {request.route_id}")
        identity_route_prefix = f"route://{request.identity_scope}"
        if request.route_id.startswith("route://identity/") and not (
            request.route_id == identity_route_prefix or request.route_id.startswith(identity_route_prefix + "/")
        ):
            raise ValueError("identity request cannot name another identity route")
        if request.identity_scope not in authorized_scopes:
            raise ValueError("identity scope is not authorized")

        records = tuple(self._store.iter_committed_records())
        routed = self._resolver.resolve(route, records, authorized_scopes)
        return project_markdown(
            routed.records,
            source_head=self._store.head(),
            route_id=route.route_id,
            byte_budget=request.byte_budget,
            omissions=routed.omitted,
        )
