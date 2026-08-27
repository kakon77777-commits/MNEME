from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
import re
import unicodedata

from jsonschema import Draft202012Validator

from .canonical import canonical_json_bytes, sha256_domain
from .errors import ProfileValidationError

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "memory-markdown-profile-0.1.schema.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
_VALIDATOR = Draft202012Validator(_SCHEMA)
_WS_RE = re.compile(r"\s+")


def _error_key(error) -> tuple[str, ...]:
    return tuple(str(part) for part in error.absolute_path)


def normalize_heading(text: str) -> str:
    if not isinstance(text, str):
        raise ProfileValidationError("heading must be a string")
    return _WS_RE.sub(" ", unicodedata.normalize("NFC", text).strip()).casefold()


@dataclass(frozen=True)
class SectionRule:
    section_id: str
    aliases: tuple[str, ...]
    render_heading: str
    scope_kind: str
    scope_subject: str
    block_rules: dict[str, str]
    route_hints: tuple[str, ...]

    @property
    def scope(self) -> dict[str, str]:
        return {"kind": self.scope_kind, "subject": self.scope_subject}


@dataclass(frozen=True)
class MemoryMarkdownProfile:
    _raw: dict[str, object]
    _sections: tuple[SectionRule, ...]
    _alias_table: dict[str, SectionRule]

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "MemoryMarkdownProfile":
        candidate = deepcopy(raw)
        errors = sorted(_VALIDATOR.iter_errors(candidate), key=_error_key)
        if errors:
            error = errors[0]
            path = ".".join(str(part) for part in error.absolute_path) or "$"
            raise ProfileValidationError(f"{path}: {error.message}")

        seen_section_ids: set[str] = set()
        alias_table: dict[str, SectionRule] = {}
        sections: list[SectionRule] = []
        for raw_section in candidate["sections"]:
            section_id = raw_section["section_id"]
            if section_id in seen_section_ids:
                raise ProfileValidationError(f"duplicate section_id: {section_id}")
            seen_section_ids.add(section_id)
            rule = SectionRule(
                section_id=section_id,
                aliases=tuple(raw_section["aliases"]),
                render_heading=raw_section["render_heading"],
                scope_kind=raw_section["scope"]["kind"],
                scope_subject=raw_section["scope"]["subject"],
                block_rules=dict(raw_section["block_rules"]),
                route_hints=tuple(raw_section["route_hints"]),
            )
            for alias in rule.aliases:
                normalized = normalize_heading(alias)
                if normalized in alias_table:
                    other = alias_table[normalized]
                    raise ProfileValidationError(
                        f"normalized alias collision: {alias!r} maps to both {other.section_id!r} and {rule.section_id!r}"
                    )
                alias_table[normalized] = rule
            sections.append(rule)
        return cls(candidate, tuple(sections), alias_table)

    @property
    def profile_id(self) -> str:
        return str(self._raw["profile_id"])

    @property
    def title(self) -> str:
        return str(self._raw["title"])

    @property
    def sections(self) -> tuple[SectionRule, ...]:
        return self._sections

    def to_dict(self) -> dict[str, object]:
        return deepcopy(self._raw)

    def digest(self) -> str:
        return sha256_domain(b"MNEME-MD-PROFILE-0.1", canonical_json_bytes(self._raw))

    def match_heading(self, text: str) -> SectionRule | None:
        return self._alias_table.get(normalize_heading(text))

    def section_by_id(self, section_id: str) -> SectionRule | None:
        for section in self._sections:
            if section.section_id == section_id:
                return section
        return None


def load_profile(path: Path) -> MemoryMarkdownProfile:
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProfileValidationError(f"profile cannot be read: {exc}") from exc
    if not isinstance(raw, dict):
        raise ProfileValidationError("profile root must be an object")
    return MemoryMarkdownProfile.from_dict(raw)


def load_builtin_evemiss_profile() -> MemoryMarkdownProfile:
    root = Path(__file__).resolve().parents[2]
    return load_profile(root / "profiles" / "memory-markdown" / "evemiss-residence-0.1.json")
