from __future__ import annotations

from .errors import ProfileValidationError
from .markdown_profile import (
    MemoryMarkdownProfile,
    load_builtin_evemiss_profile,
    load_builtin_evemiss_profile_v02,
)

__version__ = "0.4.0a2"

MappingProfileError = ProfileValidationError


def load_builtin_evemiss_profile_by_id(
    profile_id: str,
) -> MemoryMarkdownProfile:
    if profile_id == "evemiss-residence/0.1":
        return load_builtin_evemiss_profile()
    if profile_id == "evemiss-residence/0.2":
        return load_builtin_evemiss_profile_v02()
    raise MappingProfileError(f"unsupported built-in EveMiss profile: {profile_id!r}")


__all__ = [
    "MappingProfileError",
    "__version__",
    "load_builtin_evemiss_profile_by_id",
]
