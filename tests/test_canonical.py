import math
import pytest

from mneme.canonical import canonical_json_bytes, sha256_domain
from mneme.errors import CanonicalizationError


def test_canonical_json_is_sorted_compact_utf8_and_stable():
    left = {"z": 1, "a": "記憶", "nested": {"b": 2, "a": 1}}
    right = {"nested": {"a": 1, "b": 2}, "a": "記憶", "z": 1}
    expected = b'{"a":"\xe8\xa8\x98\xe6\x86\xb6","nested":{"a":1,"b":2},"z":1}'
    assert canonical_json_bytes(left) == expected
    assert canonical_json_bytes(right) == expected


def test_canonical_json_rejects_nan():
    with pytest.raises(CanonicalizationError):
        canonical_json_bytes({"bad": math.nan})


def test_domain_hash_changes_when_domain_changes():
    payload = b"same"
    assert sha256_domain(b"A", payload) != sha256_domain(b"B", payload)
