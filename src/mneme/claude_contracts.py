from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from functools import cache
from typing import Any, ClassVar, Self, cast

from jsonschema import Draft202012Validator

from .canonical import canonical_json_bytes, sha256_domain
from .errors import ClaudeContractError, ManualAuthorityError
from .schemas import read_schema

CLAUDE_GLOBAL_SCOPE_PATHS = (
    "global/core",
    "global/collaboration",
    "global/verification",
    "global/machine",
)
CLAUDE_GLOBAL_NONCLAIMS = (
    "resident_identity",
    "private_memory_access",
    "provider_continuity",
    "autonomous_write_authority",
    "cognitive_reconstruction",
    "claude_memory_readback",
)


def _error_key(error) -> tuple[str, ...]:
    return tuple(str(part) for part in error.absolute_path)


@cache
def _validator_for(schema_name: str) -> Draft202012Validator:
    schema = read_schema(schema_name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@dataclass(frozen=True)
class _ClaudeContract:
    _canonical: bytes

    schema_name: ClassVar[str]
    digest_field: ClassVar[str]
    domain: ClassVar[bytes]
    error_type: ClassVar[type[ClaudeContractError]] = ClaudeContractError

    @classmethod
    def sealed(cls, material: Mapping[str, object]) -> Self:
        value = cls._canonicalize_mapping(material)
        value.pop(cls.digest_field, None)
        value[cls.digest_field] = sha256_domain(
            cls.domain,
            canonical_json_bytes(value),
        )
        return cls.from_dict(value)

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> Self:
        value = cls._canonicalize_mapping(raw)
        cls._validate_value(value)
        canonical = canonical_json_bytes(value)
        selected = cls(canonical)
        selected.verify()
        return selected

    @classmethod
    def _canonicalize_mapping(cls, raw: Mapping[str, object]) -> dict[str, Any]:
        if not isinstance(raw, Mapping):
            raise cls.error_type("contract input must be a mapping")
        try:
            encoded = canonical_json_bytes(dict(raw))
            value = json.loads(encoded.decode("utf-8"))
        except Exception as error:
            raise cls.error_type(f"contract cannot be canonicalized: {error}") from error
        if not isinstance(value, dict):
            raise cls.error_type("contract must canonicalize to an object")
        return value

    @classmethod
    def _validate_value(cls, value: dict[str, Any]) -> None:
        errors = sorted(_validator_for(cls.schema_name).iter_errors(value), key=_error_key)
        if errors:
            error = errors[0]
            path = ".".join(str(part) for part in error.absolute_path) or "$"
            raise cls.error_type(f"{path}: {error.message}")
        cls._validate_semantics(value)

    @classmethod
    def _validate_semantics(cls, value: dict[str, Any]) -> None:
        del value

    def _decode(self) -> dict[str, Any]:
        try:
            value = json.loads(self._canonical.decode("utf-8"))
        except Exception as error:
            raise self.error_type(f"contract bytes are unreadable: {error}") from error
        if not isinstance(value, dict):
            raise self.error_type("contract bytes do not encode an object")
        return value

    def verify(self) -> bool:
        value = self._decode()
        if canonical_json_bytes(value) != self._canonical:
            raise self.error_type("contract bytes are not canonical JSON")
        self._validate_value(value)
        observed = value.pop(self.digest_field)
        expected = sha256_domain(self.domain, canonical_json_bytes(value))
        if observed != expected:
            raise self.error_type(f"{self.digest_field}: digest mismatch")
        return True

    def to_dict(self) -> dict[str, object]:
        self.verify()
        return deepcopy(self._decode())

    @property
    def digest(self) -> str:
        self.verify()
        return cast(str, self._decode()[self.digest_field])

    def _field(self, name: str) -> Any:
        self.verify()
        return deepcopy(self._decode()[name])


@dataclass(frozen=True)
class ClaudeGlobalProjectionRequest(_ClaudeContract):
    schema_name = "claude-global-projection-request-0.1.schema.json"
    digest_field = "request_digest"
    domain = b"MNEME-CLAUDE-GLOBAL-PROJECTION-REQUEST-0.1"

    @property
    def request_id(self) -> str:
        return cast(str, self._field("request_id"))

    @property
    def expected_source_head(self) -> str:
        return cast(str, self._field("expected_source_head"))

    @property
    def route_id(self) -> str:
        return cast(str, self._field("route_id"))

    @property
    def allowed_scope_paths(self) -> tuple[str, ...]:
        return tuple(self._field("allowed_scope_paths"))

    @property
    def required_record_ids(self) -> tuple[str, ...]:
        return tuple(self._field("required_record_ids"))

    @property
    def byte_budget(self) -> int:
        return cast(int, self._field("byte_budget"))

    @property
    def target_kind(self) -> str:
        return cast(str, self._field("target_kind"))

    @property
    def projection_ref(self) -> str:
        return cast(str, self._field("projection_ref"))


@dataclass(frozen=True)
class ClaudeGlobalProjectionManifest(_ClaudeContract):
    schema_name = "claude-global-projection-manifest-0.1.schema.json"
    digest_field = "projection_digest"
    domain = b"MNEME-CLAUDE-GLOBAL-PROJECTION-MANIFEST-0.1"

    @classmethod
    def _validate_semantics(cls, value: dict[str, Any]) -> None:
        if value["content_bytes"] > value["byte_budget"]:
            raise cls.error_type("content_bytes exceeds byte_budget")
        included = set(value["included_record_ids"])
        required = set(value["required_record_ids"])
        if not required.issubset(included):
            raise cls.error_type("required_record_ids must all be included")
        omitted_ids = [item["record_id"] for item in value["omitted"]]
        if len(omitted_ids) != len(set(omitted_ids)):
            raise cls.error_type("omitted record_id values must be unique")
        if included.intersection(omitted_ids):
            raise cls.error_type("record_id cannot be both included and omitted")

    @property
    def projection_ref(self) -> str:
        return cast(str, self._field("projection_ref"))

    @property
    def request_ref(self) -> str:
        return cast(str, self._field("request_ref"))

    @property
    def request_digest(self) -> str:
        return cast(str, self._field("request_digest"))

    @property
    def source_head(self) -> str:
        return cast(str, self._field("source_head"))

    @property
    def route_id(self) -> str:
        return cast(str, self._field("route_id"))

    @property
    def byte_budget(self) -> int:
        return cast(int, self._field("byte_budget"))

    @property
    def content_bytes(self) -> int:
        return cast(int, self._field("content_bytes"))

    @property
    def content_sha256(self) -> str:
        return cast(str, self._field("content_sha256"))

    @property
    def included_record_ids(self) -> tuple[str, ...]:
        return tuple(self._field("included_record_ids"))

    @property
    def omitted(self) -> tuple[dict[str, str], ...]:
        return tuple(self._field("omitted"))

    @property
    def required_record_ids(self) -> tuple[str, ...]:
        return tuple(self._field("required_record_ids"))

    @property
    def generator_version(self) -> str:
        return cast(str, self._field("generator_version"))


@dataclass(frozen=True)
class ClaudePublicationPlan(_ClaudeContract):
    schema_name = "claude-publication-plan-0.1.schema.json"
    digest_field = "plan_digest"
    domain = b"MNEME-CLAUDE-PUBLICATION-PLAN-0.1"

    @property
    def plan_id(self) -> str:
        return cast(str, self._field("plan_id"))

    @property
    def projection_ref(self) -> str:
        return cast(str, self._field("projection_ref"))

    @property
    def projection_digest(self) -> str:
        return cast(str, self._field("projection_digest"))

    @property
    def content_bytes(self) -> int:
        return cast(int, self._field("content_bytes"))

    @property
    def content_sha256(self) -> str:
        return cast(str, self._field("content_sha256"))

    @property
    def target_ref(self) -> str:
        return cast(str, self._field("target_ref"))

    @property
    def target_preimage_sha256(self) -> str | None:
        return cast(str | None, self._field("target_preimage_sha256"))


@dataclass(frozen=True)
class ClaudePublicationReceipt(_ClaudeContract):
    schema_name = "claude-publication-receipt-0.1.schema.json"
    digest_field = "receipt_digest"
    domain = b"MNEME-CLAUDE-PUBLICATION-RECEIPT-0.1"

    @classmethod
    def _validate_semantics(cls, value: dict[str, Any]) -> None:
        if value["target_after_sha256"] != value["readback_sha256"]:
            raise cls.error_type("publication readback does not match target after digest")


@dataclass(frozen=True)
class ClaudeImportPlan(_ClaudeContract):
    schema_name = "claude-import-plan-0.1.schema.json"
    digest_field = "plan_digest"
    domain = b"MNEME-CLAUDE-IMPORT-PLAN-0.1"

    @property
    def plan_id(self) -> str:
        return cast(str, self._field("plan_id"))

    @property
    def projection_ref(self) -> str:
        return cast(str, self._field("projection_ref"))

    @property
    def projection_digest(self) -> str:
        return cast(str, self._field("projection_digest"))

    @property
    def projection_path_ref(self) -> str:
        return cast(str, self._field("projection_path_ref"))

    @property
    def projection_content_sha256(self) -> str:
        return cast(str, self._field("projection_content_sha256"))

    @property
    def projection_content_bytes(self) -> int:
        return cast(int, self._field("projection_content_bytes"))

    @property
    def user_memory_ref(self) -> str:
        return cast(str, self._field("user_memory_ref"))

    @property
    def user_memory_preimage_sha256(self) -> str | None:
        return cast(str | None, self._field("user_memory_preimage_sha256"))


@dataclass(frozen=True)
class ClaudeImportReceipt(_ClaudeContract):
    schema_name = "claude-import-receipt-0.1.schema.json"
    digest_field = "receipt_digest"
    domain = b"MNEME-CLAUDE-IMPORT-RECEIPT-0.1"

    @classmethod
    def _validate_semantics(cls, value: dict[str, Any]) -> None:
        if value["user_memory_after_sha256"] != value["readback_sha256"]:
            raise cls.error_type("import readback does not match user memory after digest")


@dataclass(frozen=True)
class LocalManualWriteAuthorization(_ClaudeContract):
    schema_name = "local-manual-write-authorization-0.1.schema.json"
    digest_field = "authorization_digest"
    domain = b"MNEME-LOCAL-MANUAL-WRITE-AUTHORIZATION-0.1"
    error_type = ManualAuthorityError

    @property
    def authorization_id(self) -> str:
        return cast(str, self._field("authorization_id"))

    @property
    def principal_ref(self) -> str:
        return cast(str, self._field("principal_ref"))

    @property
    def transaction_ref(self) -> str:
        return cast(str, self._field("transaction_ref"))

    @property
    def transaction_digest(self) -> str:
        return cast(str, self._field("transaction_digest"))

    @property
    def expected_source_head(self) -> str:
        return cast(str, self._field("expected_source_head"))

    @property
    def allowed_scope_paths(self) -> tuple[str, ...]:
        return tuple(self._field("allowed_scope_paths"))

    @property
    def status(self) -> str:
        return cast(str, self._field("status"))

    @property
    def source_role(self) -> str:
        return cast(str, self._field("source_role"))

    @property
    def source_user_item_ref(self) -> str:
        return cast(str, self._field("source_user_item_ref"))

    @property
    def source_user_item_digest(self) -> str:
        return cast(str, self._field("source_user_item_digest"))

    @property
    def is_active(self) -> bool:
        return self.status == "active"


def _install_simple_properties(cls: type[_ClaudeContract], names: tuple[str, ...]) -> None:
    for name in names:
        setattr(cls, name, property(lambda self, selected=name: self._field(selected)))


_install_simple_properties(
    ClaudePublicationReceipt,
    (
        "receipt_id",
        "publication_plan_ref",
        "publication_plan_digest",
        "authorization_ref",
        "authorization_digest",
        "projection_ref",
        "projection_digest",
        "target_ref",
        "target_before_sha256",
        "target_after_sha256",
        "readback_sha256",
        "content_bytes",
        "outcome",
    ),
)
_install_simple_properties(
    ClaudeImportReceipt,
    (
        "receipt_id",
        "import_plan_ref",
        "import_plan_digest",
        "authorization_ref",
        "authorization_digest",
        "projection_ref",
        "projection_digest",
        "user_memory_ref",
        "user_memory_before_sha256",
        "user_memory_after_sha256",
        "readback_sha256",
        "managed_block_sha256",
        "outside_bytes_preserved",
        "outcome",
        "claude_memory_readback",
    ),
)
