from __future__ import annotations

import hashlib
import json

from .errors import CanonicalizationError


def canonical_json_bytes(value: object) -> bytes:
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise CanonicalizationError(str(exc)) from exc
    return text.encode("utf-8")


def sha256_domain(domain: bytes, payload: bytes) -> str:
    return hashlib.sha256(domain + b"\0" + payload).hexdigest()
