from __future__ import annotations

import hashlib
import os
import sys
import threading
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from types import FrameType
from typing import Any, Self

_OBSERVATION_MODE = "cpython_audit_and_profile_v0.1"
_PRIVATE_PARTS = frozenset(
    {
        "ai_residence",
        "ai_home",
        "00_residence",
        "private",
        "secrets",
        ".ssh",
        ".gnupg",
    }
)
_NETWORK_EVENTS = frozenset(
    {
        "socket.bind",
        "socket.connect",
        "socket.connect_ex",
        "socket.getaddrinfo",
        "socket.gethostbyaddr",
        "socket.gethostbyname",
        "socket.gethostbyname_ex",
        "socket.getnameinfo",
        "socket.getservbyname",
        "socket.getservbyport",
        "socket.sendmsg",
        "socket.sendto",
    }
)
_EXTERNAL_CLI_EVENTS = frozenset(
    {
        "os.exec",
        "os.posix_spawn",
        "os.spawn",
        "os.startfile",
        "os.system",
        "subprocess.Popen",
    }
)
_WRITE_PATH_EVENTS = frozenset(
    {
        "os.chdir",
        "os.chmod",
        "os.chown",
        "os.link",
        "os.mkdir",
        "os.remove",
        "os.rename",
        "os.rmdir",
        "os.symlink",
        "os.truncate",
        "os.unlink",
        "os.utime",
    }
)
_PROVIDER_PREFIXES = (
    "anthropic",
    "openai",
    "google.genai",
    "google.generativeai",
)
_MCP_PREFIXES = ("mcp", "fastmcp")
_BRIDGE_PREFIXES = ("eml_bridge", "eml_handoff", "eml_wake", "herdr")

_STATE_LOCK = threading.RLock()
_ACTIVE_OBSERVER: ClaudeRuntimeEffectObserver | None = None
_AUDIT_HOOK_INSTALLED = False


@dataclass(frozen=True)
class ClaudeRuntimeEffectEvidence:
    fixture_reads: int
    private_reads: int
    private_writes: int
    production_reads: int
    production_writes: int
    network_calls: int
    provider_calls: int
    mcp_calls: int
    bridge_calls: int
    external_cli_calls: int
    observer_errors: int
    observation_mode: str
    observed_events_digest: str

    def forbidden_total(self) -> int:
        return sum(
            (
                self.private_reads,
                self.private_writes,
                self.production_reads,
                self.production_writes,
                self.network_calls,
                self.provider_calls,
                self.mcp_calls,
                self.bridge_calls,
                self.external_cli_calls,
                self.observer_errors,
            )
        )


class ClaudeRuntimeEffectObserver:
    def __init__(
        self,
        synthetic_root: Path,
        *,
        fixture_path: Path,
        allowed_read_paths: Iterable[Path],
        allowed_read_roots: Iterable[Path] = (),
    ) -> None:
        root = Path(synthetic_root)
        fixture = Path(fixture_path)
        if not root.is_absolute() or not fixture.is_absolute():
            raise ValueError("effect observer paths must be explicit absolute paths")
        self._root = _normalized_path(root)
        self._fixture = _normalized_path(fixture)
        self._allowed_reads = frozenset(
            _normalized_path(Path(path)) for path in allowed_read_paths
        )
        self._allowed_read_roots = tuple(
            _normalized_path(Path(path)) for path in allowed_read_roots
        )
        if self._fixture not in self._allowed_reads:
            raise ValueError("fixture path must be in the closed read allowlist")
        self._counts: Counter[str] = Counter()
        self._events: list[str] = []
        self._event_lock = threading.Lock()
        self._entered = False
        self._previous_sys_profile = None
        self._previous_thread_profile = None

    def __enter__(self) -> Self:
        global _ACTIVE_OBSERVER

        _STATE_LOCK.acquire()
        if _ACTIVE_OBSERVER is not None:
            _STATE_LOCK.release()
            raise RuntimeError("a Claude runtime effect observer is already active")
        _install_audit_hook()
        self._previous_sys_profile = sys.getprofile()
        self._previous_thread_profile = threading.getprofile()
        _ACTIVE_OBSERVER = self
        self._entered = True
        sys.setprofile(_profile_hook)
        threading.setprofile(_profile_hook)
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        global _ACTIVE_OBSERVER

        try:
            sys.setprofile(self._previous_sys_profile)
            threading.setprofile(self._previous_thread_profile)
            _ACTIVE_OBSERVER = None
            self._entered = False
        finally:
            _STATE_LOCK.release()

    def evidence(self) -> ClaudeRuntimeEffectEvidence:
        with self._event_lock:
            counts = self._counts.copy()
            events = tuple(self._events)
        digest = hashlib.sha256("\n".join(events).encode("utf-8")).hexdigest()
        return ClaudeRuntimeEffectEvidence(
            fixture_reads=counts["fixture_reads"],
            private_reads=counts["private_reads"],
            private_writes=counts["private_writes"],
            production_reads=counts["production_reads"],
            production_writes=counts["production_writes"],
            network_calls=counts["network_calls"],
            provider_calls=counts["provider_calls"],
            mcp_calls=counts["mcp_calls"],
            bridge_calls=counts["bridge_calls"],
            external_cli_calls=counts["external_cli_calls"],
            observer_errors=counts["observer_errors"],
            observation_mode=_OBSERVATION_MODE,
            observed_events_digest=digest,
        )

    def _record(self, category: str) -> None:
        with self._event_lock:
            self._counts[category] += 1
            self._events.append(category)

    def _record_audit(self, event: str, args: tuple[object, ...]) -> None:
        if event == "open":
            self._record_open(args)
            return
        if event in _NETWORK_EVENTS:
            self._record("network_calls")
            return
        if event in _EXTERNAL_CLI_EVENTS or event.startswith("subprocess."):
            self._record("external_cli_calls")
            return
        if event in _WRITE_PATH_EVENTS:
            self._record_write_event(event, args)

    def _record_open(self, args: tuple[object, ...]) -> None:
        if not args:
            return
        selected = _event_path(args[0])
        if selected is None:
            return
        mode = args[1] if len(args) > 1 else None
        flags = args[2] if len(args) > 2 else 0
        write = _open_is_write(mode, flags)
        self._record_path(selected, write=write)

    def _record_write_event(self, event: str, args: tuple[object, ...]) -> None:
        if not args:
            return
        if event == "os.link" and len(args) >= 2:
            source = _event_path(args[0])
            target = _event_path(args[1])
            if source is not None:
                self._record_path(source, write=False)
            if target is not None:
                self._record_path(target, write=True)
            return
        if event == "os.rename" and len(args) >= 2:
            source = _event_path(args[0])
            target = _event_path(args[1])
            if source is not None:
                self._record_path(source, write=True)
            if target is not None:
                self._record_path(target, write=True)
            return
        selected = _event_path(args[0])
        if selected is not None:
            self._record_path(selected, write=True)

    def _record_path(self, path: str, *, write: bool) -> None:
        parts = _path_parts(path)
        if parts.intersection(_PRIVATE_PARTS):
            self._record("private_writes" if write else "private_reads")
            return
        if _is_within(path, self._root):
            return
        if not write and path in self._allowed_reads:
            if path == self._fixture:
                self._record("fixture_reads")
            return
        if not write and any(
            _is_within(path, allowed_root)
            for allowed_root in self._allowed_read_roots
        ):
            return
        self._record("production_writes" if write else "production_reads")

    def _record_profile(self, frame: FrameType, event: str, arg: Any) -> None:
        module_name = ""
        if event == "call":
            module_name = str(frame.f_globals.get("__name__", ""))
        elif event == "c_call":
            module_name = str(getattr(arg, "__module__", ""))
        else:
            return
        if _module_matches(module_name, _PROVIDER_PREFIXES):
            self._record("provider_calls")
        elif _module_matches(module_name, _MCP_PREFIXES):
            self._record("mcp_calls")
        elif _module_matches(module_name, _BRIDGE_PREFIXES):
            self._record("bridge_calls")


def _install_audit_hook() -> None:
    global _AUDIT_HOOK_INSTALLED

    if not _AUDIT_HOOK_INSTALLED:
        sys.addaudithook(_audit_hook)
        _AUDIT_HOOK_INSTALLED = True


def _audit_hook(event: str, args: tuple[object, ...]) -> None:
    observer = _ACTIVE_OBSERVER
    if observer is None:
        return
    try:
        observer._record_audit(event, args)
    except Exception:  # noqa: BLE001 - an audit observer must not block the event
        observer._record("observer_errors")


def _profile_hook(frame: FrameType, event: str, arg: Any) -> None:
    observer = _ACTIVE_OBSERVER
    if observer is None:
        return
    try:
        observer._record_profile(frame, event, arg)
    except Exception:  # noqa: BLE001 - a profile observer must not block the call
        observer._record("observer_errors")


def _normalized_path(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def _event_path(value: object) -> str | None:
    if isinstance(value, int):
        return None
    try:
        raw = os.fsdecode(os.fspath(value))
    except TypeError:
        return None
    return os.path.normcase(os.path.abspath(raw))


def _path_parts(path: str) -> set[str]:
    return {
        part.casefold()
        for part in path.replace("\\", "/").split("/")
        if part
    }


def _is_within(path: str, root: str) -> bool:
    try:
        return os.path.commonpath((path, root)) == root
    except ValueError:
        return False


def _open_is_write(mode: object, flags: object) -> bool:
    if isinstance(mode, str):
        return any(marker in mode for marker in ("w", "a", "x", "+"))
    if isinstance(flags, int):
        write_flags = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC
        return bool(flags & write_flags)
    return False


def _module_matches(module_name: str, prefixes: tuple[str, ...]) -> bool:
    return any(
        module_name == prefix or module_name.startswith(prefix + ".")
        for prefix in prefixes
    )
