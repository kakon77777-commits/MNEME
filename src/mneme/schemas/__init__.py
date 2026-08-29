from __future__ import annotations

import hashlib
import json
from importlib.resources import files


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
