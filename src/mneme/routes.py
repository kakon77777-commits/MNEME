from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

from jsonschema import Draft202012Validator

from .errors import RouteValidationError
from .records import MemoryRecord

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "route-0.1.schema.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
_VALIDATOR = Draft202012Validator(_SCHEMA)


def _error_key(error) -> tuple[str, ...]:
    return tuple(str(part) for part in error.absolute_path)


def scope_path(record: MemoryRecord) -> str:
    raw = record.to_dict()["scope"]
    return f"{raw['kind']}/{raw['subject']}"


def _prefix_matches(scope: str, prefix: str) -> bool:
    return scope == prefix or scope.startswith(prefix + "/")


@dataclass(frozen=True)
class Route:
    _raw: dict[str, object]

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "Route":
        candidate = deepcopy(raw)
        errors = sorted(_VALIDATOR.iter_errors(candidate), key=_error_key)
        if errors:
            error = errors[0]
            path = ".".join(str(part) for part in error.absolute_path) or "$"
            raise RouteValidationError(f"{path}: {error.message}")
        return cls(candidate)

    def to_dict(self) -> dict[str, object]:
        return deepcopy(self._raw)

    @property
    def route_id(self) -> str:
        return str(self._raw["route_id"])

    @property
    def scope_prefixes(self) -> tuple[str, ...]:
        return tuple(self._raw["scope_prefixes"])

    @property
    def record_types(self) -> tuple[str, ...]:
        return tuple(self._raw["record_types"])


@dataclass(frozen=True)
class Omission:
    record_id: str
    reason: str


@dataclass(frozen=True)
class RouteResult:
    records: tuple[MemoryRecord, ...]
    included_ids: tuple[str, ...]
    omitted: tuple[Omission, ...]


class RouteResolver:
    def resolve(
        self,
        route: Route,
        records: Iterable[MemoryRecord],
        authorized_scopes: set[str],
    ) -> RouteResult:
        included: list[MemoryRecord] = []
        omitted: list[Omission] = []
        for record in records:
            raw = record.to_dict()
            record_id = str(raw["record_id"])
            scope = scope_path(record)
            if not any(_prefix_matches(scope, prefix) for prefix in route.scope_prefixes):
                omitted.append(Omission(record_id, "scope_mismatch"))
                continue
            if raw["status"] != "active":
                omitted.append(Omission(record_id, "inactive"))
                continue
            if route.record_types and raw["record_type"] not in route.record_types:
                omitted.append(Omission(record_id, "type_mismatch"))
                continue
            if not scope.startswith("global/") and not any(
                _prefix_matches(scope, authorized) for authorized in authorized_scopes
            ):
                omitted.append(Omission(record_id, "unauthorized_scope"))
                continue
            included.append(record)
        return RouteResult(
            records=tuple(included),
            included_ids=tuple(str(r.to_dict()["record_id"]) for r in included),
            omitted=tuple(omitted),
        )
