from __future__ import annotations

import hashlib
import json
from importlib.resources import files

UNIFIED_SCHEMA_NAMES = (
    "claude-global-projection-manifest-0.1.schema.json",
    "claude-global-projection-request-0.1.schema.json",
    "claude-import-plan-0.1.schema.json",
    "claude-import-receipt-0.1.schema.json",
    "claude-publication-plan-0.1.schema.json",
    "claude-publication-receipt-0.1.schema.json",
    "cognitive-seed-proposal-0.1.schema.json",
    "equivalence-contract-0.1.schema.json",
    "factorization-intent-0.1.schema.json",
    "factorization-proposal-0.1.schema.json",
    "local-manual-write-authorization-0.1.schema.json",
    "memory-markdown-profile-0.1.schema.json",
    "memory-record-0.1.schema.json",
    "persistence-assessment-0.1.schema.json",
    "persistence-policy-0.1.schema.json",
    "private-residence-dry-run-report-0.2.schema.json",
    "projection-manifest-0.1.schema.json",
    "recomputation-reference-0.1.schema.json",
    "route-0.1.schema.json",
    "seed-intent-0.1.schema.json",
    "transaction-0.1.schema.json",
)


def schema_names() -> tuple[str, ...]:
    return tuple(
        sorted(
            item.name
            for item in files(__package__).iterdir()
            if item.name.endswith(".schema.json")
        )
    )


def read_schema_bytes(name: str) -> bytes:
    if (
        not isinstance(name, str)
        or not name.endswith(".schema.json")
        or "/" in name
        or "\\" in name
    ):
        raise ValueError("schema name must be one local schema filename")
    return files(__package__).joinpath(name).read_bytes()


def read_schema(name: str) -> dict[str, object]:
    value = json.loads(read_schema_bytes(name).decode("utf-8"))
    if not isinstance(value, dict):
        raise TypeError("schema resource must be an object")
    return value


def schema_sha256(name: str) -> str:
    return hashlib.sha256(read_schema_bytes(name)).hexdigest()
