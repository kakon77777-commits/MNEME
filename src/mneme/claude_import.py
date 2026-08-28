from __future__ import annotations

import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from .canonical import canonical_json_bytes, sha256_domain
from .claude_contracts import (
    CLAUDE_GLOBAL_NONCLAIMS,
    ClaudeGlobalProjectionManifest,
    ClaudeImportPlan,
    ClaudeImportReceipt,
    LocalManualWriteAuthorization,
)
from .claude_projection import (
    _file_ref,
    _fsync_directory,
    _has_git_ancestor,
    _reject_ads,
    _reject_network_or_uri,
    _reject_strong_private_parts,
    _reject_symlink_chain,
    _same_file_state,
    _sha256_bytes,
    _validate_optional_digest,
)
from .errors import (
    ClaudeContractError,
    ClaudePathBoundaryError,
    InjectedCrash,
    ManagedBlockConflictError,
    ManualAuthorityError,
    StaleTargetError,
)
from .writer_lock import StoreWriterLock

BEGIN = b"<!-- BEGIN MNEME GLOBAL PROJECTION v0.1 -->"
END = b"<!-- END MNEME GLOBAL PROJECTION v0.1 -->"

_BLOCK_VERSION = "MNEME_GLOBAL_PROJECTION/0.1"
_PLAN_ID_DOMAIN = b"MNEME-CLAUDE-IMPORT-PLAN-ID-0.1"
_RECEIPT_ID_DOMAIN = b"MNEME-CLAUDE-IMPORT-RECEIPT-ID-0.1"
_RELATIVE_FORBIDDEN = frozenset(("private", "secrets", "temp", "tmp", ".git"))
_CRASH_POINTS = frozenset(("before_replace", "after_replace"))


@dataclass(frozen=True)
class _ParsedUserMemory:
    prefix: bytes
    block: bytes | None
    suffix: bytes


@dataclass(frozen=True)
class PreparedClaudeImport:
    contract: ClaudeImportPlan
    user_memory: Path
    projection: Path
    manifest: ClaudeGlobalProjectionManifest

    def verify(self) -> bool:
        if not isinstance(self.contract, ClaudeImportPlan):
            raise ClaudeContractError("import plan contract type is invalid")
        if not isinstance(self.user_memory, Path) or not self.user_memory.is_absolute():
            raise ClaudeContractError("user memory target must be an absolute Path")
        if not isinstance(self.projection, Path) or not self.projection.is_absolute():
            raise ClaudeContractError("projection target must be an absolute Path")
        if not isinstance(self.manifest, ClaudeGlobalProjectionManifest):
            raise ClaudeContractError("import manifest type is invalid")
        self.contract.verify()
        self.manifest.verify()
        if self.contract.projection_ref != self.manifest.projection_ref:
            raise ClaudeContractError("import projection ref mismatch")
        if self.contract.projection_digest != self.manifest.digest:
            raise ClaudeContractError("import projection digest mismatch")
        if self.contract.projection_content_sha256 != self.manifest.content_sha256:
            raise ClaudeContractError("import projection content digest mismatch")
        if self.contract.projection_content_bytes != self.manifest.content_bytes:
            raise ClaudeContractError("import projection byte count mismatch")
        if self.contract.projection_path_ref != _file_ref(self.projection):
            raise ClaudeContractError("import projection path ref mismatch")
        if self.contract.user_memory_ref != _file_ref(self.user_memory):
            raise ClaudeContractError("import user memory ref mismatch")
        return True


class ClaudeManagedImport:
    def __init__(
        self,
        runtime_root: Path,
        user_memory_root: Path,
        projection_manifest: ClaudeGlobalProjectionManifest,
        *,
        crash_at: str | None = None,
    ):
        runtime = Path(runtime_root)
        user_root = Path(user_memory_root)
        if not runtime.is_absolute() or not user_root.is_absolute():
            raise ClaudePathBoundaryError("managed import roots must be explicit absolute paths")
        if not isinstance(projection_manifest, ClaudeGlobalProjectionManifest):
            raise ClaudeContractError("managed import requires a sealed projection manifest")
        projection_manifest.verify()
        if crash_at is not None and crash_at not in _CRASH_POINTS:
            raise ValueError(f"unknown crash point: {crash_at}")
        self._runtime_root = runtime
        self._user_memory_root = user_root
        self._manifest = projection_manifest
        self._crash_at = crash_at
        self._projection_lock = runtime / ".claude-projection.writer.lock"
        self._import_lock = user_root / ".mneme-claude-import.writer.lock"

    def plan(
        self,
        user_memory: Path,
        projection: Path,
        expected_digest: str | None,
    ) -> PreparedClaudeImport:
        self._manifest.verify()
        selected_projection = self._validate_projection(Path(projection))
        selected_user_memory = self._validate_user_memory(Path(user_memory))
        projection_bytes, projection_digest = self._read_file(
            selected_projection,
            allow_missing=False,
            label="projection",
        )
        self._require_projection_match(projection_bytes, projection_digest)
        _validate_optional_digest(expected_digest, field="expected_digest")
        user_bytes, observed_user_digest = self._read_file(
            selected_user_memory,
            allow_missing=True,
            label="user memory",
        )
        if observed_user_digest != expected_digest:
            raise StaleTargetError("user memory pre-image digest mismatch")
        _parse_user_memory(user_bytes or b"")

        identity_material = {
            "projection_ref": self._manifest.projection_ref,
            "projection_digest": self._manifest.digest,
            "projection_path_ref": _file_ref(selected_projection),
            "projection_content_sha256": self._manifest.content_sha256,
            "projection_content_bytes": self._manifest.content_bytes,
            "user_memory_ref": _file_ref(selected_user_memory),
            "user_memory_preimage_sha256": observed_user_digest,
            "managed_block_version": _BLOCK_VERSION,
        }
        plan_id = "import-plan:" + sha256_domain(
            _PLAN_ID_DOMAIN,
            canonical_json_bytes(identity_material),
        )
        contract = ClaudeImportPlan.sealed(
            {
                "import_plan_version": "mneme.claude-import-plan/0.1",
                "plan_id": plan_id,
                **identity_material,
                "not_claimed": list(CLAUDE_GLOBAL_NONCLAIMS),
            }
        )
        prepared = PreparedClaudeImport(
            contract=contract,
            user_memory=selected_user_memory,
            projection=selected_projection,
            manifest=self._manifest,
        )
        prepared.verify()
        return prepared

    def apply(
        self,
        plan: PreparedClaudeImport,
        authorization: LocalManualWriteAuthorization,
    ) -> ClaudeImportReceipt:
        if not isinstance(plan, PreparedClaudeImport):
            raise ClaudeContractError("prepared import type is invalid")
        plan.verify()
        self._validate_authorization(authorization)
        projection = self._validate_projection(plan.projection)
        user_memory = self._validate_user_memory(plan.user_memory)
        if _file_ref(projection) != plan.contract.projection_path_ref:
            raise ClaudeContractError("projection path changed after planning")
        if _file_ref(user_memory) != plan.contract.user_memory_ref:
            raise ClaudeContractError("user memory path changed after planning")
        self._validate_lock_path(self._projection_lock, "projection writer lock")
        self._validate_lock_path(self._import_lock, "managed import writer lock")

        with (
            StoreWriterLock(self._projection_lock),
            StoreWriterLock(self._import_lock),
        ):
            return self._apply_locked(plan, authorization)

    def _apply_locked(
        self,
        plan: PreparedClaudeImport,
        authorization: LocalManualWriteAuthorization,
    ) -> ClaudeImportReceipt:
        projection = self._validate_projection(plan.projection)
        user_memory = self._validate_user_memory(plan.user_memory)
        projection_bytes, projection_digest = self._read_file(
            projection,
            allow_missing=False,
            label="projection",
        )
        self._require_projection_match(projection_bytes, projection_digest)
        if projection_digest != plan.contract.projection_content_sha256:
            raise StaleTargetError("projection changed after planning")

        user_bytes, before_digest = self._read_file(
            user_memory,
            allow_missing=True,
            label="user memory",
        )
        if before_digest != plan.contract.user_memory_preimage_sha256:
            raise StaleTargetError("user memory changed after planning")
        before = user_bytes or b""
        parsed = _parse_user_memory(before)
        block = _managed_block(projection)
        desired, outcome = _render_user_memory(before, parsed, block)

        second_projection, second_projection_digest = self._read_file(
            projection,
            allow_missing=False,
            label="projection",
        )
        self._require_projection_match(second_projection, second_projection_digest)
        if second_projection_digest != projection_digest:
            raise StaleTargetError("projection changed before managed import")

        if outcome != "idempotent":
            self._replace_atomically(
                user_memory,
                desired,
                expected_preimage=before_digest,
            )
        readback, after_digest = self._read_file(
            user_memory,
            allow_missing=False,
            label="user memory",
        )
        if readback != desired or after_digest != _sha256_bytes(desired):
            raise ClaudeContractError("managed import readback mismatch")

        receipt_identity = {
            "import_plan_ref": plan.contract.plan_id,
            "import_plan_digest": plan.contract.digest,
            "authorization_ref": authorization.authorization_id,
            "authorization_digest": authorization.digest,
            "projection_ref": plan.contract.projection_ref,
            "projection_digest": plan.contract.projection_digest,
            "user_memory_ref": plan.contract.user_memory_ref,
            "user_memory_before_sha256": before_digest,
            "user_memory_after_sha256": after_digest,
            "readback_sha256": after_digest,
            "managed_block_sha256": _sha256_bytes(block),
            "outside_bytes_preserved": True,
            "outcome": outcome,
            "claude_memory_readback": "NOT_RUN",
        }
        receipt_id = "import-receipt:" + sha256_domain(
            _RECEIPT_ID_DOMAIN,
            canonical_json_bytes(receipt_identity),
        )
        return ClaudeImportReceipt.sealed(
            {
                "import_receipt_version": "mneme.claude-import-receipt/0.1",
                "receipt_id": receipt_id,
                **receipt_identity,
                "not_claimed": list(CLAUDE_GLOBAL_NONCLAIMS),
            }
        )

    @staticmethod
    def _validate_authorization(
        authorization: LocalManualWriteAuthorization,
    ) -> None:
        if not isinstance(authorization, LocalManualWriteAuthorization):
            raise ManualAuthorityError("local manual authorization type is invalid")
        authorization.verify()
        if not authorization.is_active:
            raise ManualAuthorityError("local manual authorization is not active")

    def _validate_projection(self, projection: Path) -> Path:
        root = self._validate_root(self._runtime_root, "runtime root")
        selected = self._validate_bounded_path(
            projection,
            root,
            must_exist=True,
            label="projection",
        )
        if selected.name != "MNEME_GLOBAL.md":
            raise ClaudePathBoundaryError("projection filename must be MNEME_GLOBAL.md")
        return selected

    def _validate_user_memory(self, user_memory: Path) -> Path:
        root = self._validate_root(self._user_memory_root, "user memory root")
        selected = self._validate_bounded_path(
            user_memory,
            root,
            must_exist=False,
            label="user memory",
        )
        if selected.name != "CLAUDE.md":
            raise ClaudePathBoundaryError("user memory filename must be CLAUDE.md")
        return selected

    @staticmethod
    def _validate_root(root: Path, label: str) -> Path:
        _reject_network_or_uri(root)
        _reject_ads(root)
        if root.is_symlink():
            raise ClaudePathBoundaryError(f"{label} cannot be a symlink")
        try:
            resolved = root.resolve(strict=True)
        except (FileNotFoundError, OSError) as error:
            raise ClaudePathBoundaryError(f"{label} must already exist") from error
        if not resolved.is_dir():
            raise ClaudePathBoundaryError(f"{label} must be a directory")
        _reject_strong_private_parts(resolved)
        if _has_git_ancestor(resolved):
            raise ClaudePathBoundaryError(f"{label} cannot be inside a Git tree")
        return resolved

    @staticmethod
    def _validate_bounded_path(
        path: Path,
        root: Path,
        *,
        must_exist: bool,
        label: str,
    ) -> Path:
        if any(ord(character) < 32 or ord(character) == 127 for character in str(path)):
            raise ClaudePathBoundaryError(f"{label} path contains a control character")
        _reject_network_or_uri(path)
        _reject_ads(path)
        if not path.is_absolute():
            raise ClaudePathBoundaryError(f"{label} path must be absolute")
        if ".." in path.parts:
            raise ClaudePathBoundaryError(f"{label} path cannot contain traversal")
        _reject_symlink_chain(path, stop=root)
        try:
            resolved = path.resolve(strict=False)
        except OSError as error:
            raise ClaudePathBoundaryError(f"{label} path cannot be resolved") from error
        if resolved == root or not resolved.is_relative_to(root):
            raise ClaudePathBoundaryError(f"{label} path escapes its explicit root")
        _reject_strong_private_parts(resolved)
        relative = {part.casefold() for part in resolved.relative_to(root).parts}
        if relative.intersection(_RELATIVE_FORBIDDEN):
            raise ClaudePathBoundaryError(f"{label} path uses a forbidden class")
        if _has_git_ancestor(resolved.parent):
            raise ClaudePathBoundaryError(f"{label} path cannot be inside a Git tree")
        if not resolved.parent.exists() or not resolved.parent.is_dir():
            raise ClaudePathBoundaryError(f"{label} parent must already exist")
        if must_exist and not resolved.exists():
            raise ClaudePathBoundaryError(f"{label} file must already exist")
        if resolved.exists():
            metadata = resolved.lstat()
            if not stat.S_ISREG(metadata.st_mode):
                raise ClaudePathBoundaryError(f"{label} must be a regular file")
            if metadata.st_nlink != 1:
                raise ClaudePathBoundaryError(f"{label} hardlink count must be one")
        elif resolved.is_symlink():
            raise ClaudePathBoundaryError(f"{label} cannot be a symlink")
        return resolved

    @staticmethod
    def _validate_lock_path(path: Path, label: str) -> None:
        if path.is_symlink():
            raise ClaudePathBoundaryError(f"{label} cannot be a symlink")
        if path.exists():
            metadata = path.lstat()
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise ClaudePathBoundaryError(f"{label} must be one regular file")

    def _require_projection_match(
        self,
        content: bytes | None,
        digest: str | None,
    ) -> None:
        if content is None or digest is None:
            raise StaleTargetError("projection file is unavailable")
        if len(content) != self._manifest.content_bytes:
            raise StaleTargetError("projection byte count does not match manifest")
        if digest != self._manifest.content_sha256:
            raise StaleTargetError("projection digest does not match manifest")

    @staticmethod
    def _read_file(
        path: Path,
        *,
        allow_missing: bool,
        label: str,
    ) -> tuple[bytes | None, str | None]:
        try:
            before = path.lstat()
        except FileNotFoundError:
            if allow_missing:
                return None, None
            raise StaleTargetError(f"{label} file is missing") from None
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ClaudePathBoundaryError(f"{label} must remain one regular file")
        try:
            with path.open("rb") as handle:
                opened = os.fstat(handle.fileno())
                if not _same_file_state(before, opened):
                    raise StaleTargetError(f"{label} changed before read")
                content = handle.read()
                finished = os.fstat(handle.fileno())
        except FileNotFoundError as error:
            raise StaleTargetError(f"{label} disappeared during read") from error
        try:
            after = path.lstat()
        except FileNotFoundError as error:
            raise StaleTargetError(f"{label} disappeared after read") from error
        if not _same_file_state(opened, finished) or not _same_file_state(finished, after):
            raise StaleTargetError(f"{label} changed during read")
        return content, _sha256_bytes(content)

    def _replace_atomically(
        self,
        target: Path,
        content: bytes,
        *,
        expected_preimage: str | None,
    ) -> None:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=target.parent,
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            if self._crash_at == "before_replace":
                raise InjectedCrash("injected crash at before_replace")
            _, observed = self._read_file(
                target,
                allow_missing=True,
                label="user memory",
            )
            if observed != expected_preimage:
                raise StaleTargetError("user memory changed before atomic replace")
            os.replace(temporary, target)
            _fsync_directory(target.parent)
            if self._crash_at == "after_replace":
                raise InjectedCrash("injected crash at after_replace")
        finally:
            temporary.unlink(missing_ok=True)


def _parse_user_memory(content: bytes) -> _ParsedUserMemory:
    try:
        content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ManagedBlockConflictError("Claude user memory must be valid UTF-8") from error

    _reject_near_markers(content)
    begin_count = content.count(BEGIN)
    end_count = content.count(END)
    if begin_count == 0 and end_count == 0:
        if _fence_is_open(content):
            raise ManagedBlockConflictError("cannot insert MNEME import inside open fence")
        return _ParsedUserMemory(prefix=content, block=None, suffix=b"")
    if begin_count != 1 or end_count != 1:
        raise ManagedBlockConflictError("MNEME managed markers must occur exactly once")

    begin_at = content.index(BEGIN)
    end_at = content.index(END)
    if end_at <= begin_at:
        raise ManagedBlockConflictError("MNEME managed marker order is invalid")
    if _fence_is_open(content[:begin_at]):
        raise ManagedBlockConflictError("MNEME managed block cannot be inside a fence")
    if begin_at > 0 and content[begin_at - 1] != 0x0A:
        raise ManagedBlockConflictError("MNEME begin marker is not a complete line")
    begin_end = begin_at + len(BEGIN)
    if content[begin_end : begin_end + 1] != b"\n":
        raise ManagedBlockConflictError("MNEME begin marker must use canonical LF")
    if end_at > 0 and content[end_at - 1] != 0x0A:
        raise ManagedBlockConflictError("MNEME end marker is not a complete line")

    import_line = content[begin_end + 1 : end_at - 1]
    if b"\n" in import_line or b"\r" in import_line or not import_line.startswith(b"@"):
        raise ManagedBlockConflictError("MNEME managed block must contain one import line")
    try:
        import_path = import_line[1:].decode("utf-8")
    except UnicodeDecodeError as error:
        raise ManagedBlockConflictError("MNEME import path must be UTF-8") from error
    _validate_import_path(import_path)

    end_end = end_at + len(END)
    if end_end == len(content):
        block_end = end_end
    elif content[end_end : end_end + 1] == b"\n":
        block_end = end_end + 1
    else:
        raise ManagedBlockConflictError("MNEME end marker must use canonical LF")
    return _ParsedUserMemory(
        prefix=content[:begin_at],
        block=content[begin_at:block_end],
        suffix=content[block_end:],
    )


def _reject_near_markers(content: bytes) -> None:
    for line in content.splitlines():
        candidate = line.rstrip(b"\r")
        if b"MNEME GLOBAL PROJECTION" not in candidate:
            continue
        if b"BEGIN" not in candidate and b"END" not in candidate:
            continue
        if candidate not in (BEGIN, END):
            raise ManagedBlockConflictError("malformed MNEME managed marker")


def _fence_is_open(content: bytes) -> bool:
    active: tuple[int, int] | None = None
    for line in content.splitlines():
        stripped = line.lstrip(b" ")
        if not stripped or stripped[0] not in (0x60, 0x7E):
            continue
        marker = stripped[0]
        length = 0
        while length < len(stripped) and stripped[length] == marker:
            length += 1
        if length < 3:
            continue
        if active is None:
            active = (marker, length)
        elif (
            active[0] == marker
            and length >= active[1]
            and not stripped[length:].strip(b" \t")
        ):
            active = None
    return active is not None


def _validate_import_path(value: str) -> None:
    if not value or any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ManagedBlockConflictError("MNEME import path contains a control character")
    if value.startswith(("\\\\", "//")) or "://" in value:
        raise ManagedBlockConflictError("MNEME import path must be local")
    if not Path(value).is_absolute() and not PureWindowsPath(value).is_absolute():
        raise ManagedBlockConflictError("MNEME import path must be absolute")


def _managed_block(projection: Path) -> bytes:
    text = str(projection)
    _validate_import_path(text)
    return BEGIN + b"\n@" + text.encode("utf-8") + b"\n" + END + b"\n"


def _render_user_memory(
    before: bytes,
    parsed: _ParsedUserMemory,
    block: bytes,
) -> tuple[bytes, str]:
    if parsed.block is None:
        separator = b"" if not before or before.endswith(b"\n") else b"\n"
        return before + separator + block, "inserted"
    desired = parsed.prefix + block + parsed.suffix
    if desired == before:
        return before, "idempotent"
    return desired, "replaced"
