from __future__ import annotations

import hashlib
import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from .adapters.claude import ClaudeGlobalProjectionResult
from .canonical import canonical_json_bytes, sha256_domain
from .claude_contracts import (
    CLAUDE_GLOBAL_NONCLAIMS,
    ClaudeGlobalProjectionManifest,
    ClaudePublicationPlan,
    ClaudePublicationReceipt,
    LocalManualWriteAuthorization,
)
from .errors import (
    ClaudeContractError,
    ClaudePathBoundaryError,
    InjectedCrash,
    ManualAuthorityError,
    StaleTargetError,
)
from .writer_lock import StoreWriterLock

_PLAN_ID_DOMAIN = b"MNEME-CLAUDE-PUBLICATION-PLAN-ID-0.1"
_RECEIPT_ID_DOMAIN = b"MNEME-CLAUDE-PUBLICATION-RECEIPT-ID-0.1"
_STRONG_PRIVATE_PARTS = frozenset(
    ("ai_residence", "00_residence", "private", "secrets", ".ssh", ".gnupg")
)
_FORBIDDEN_RELATIVE_PARTS = frozenset(("temp", "tmp", "network", "repo", ".git"))
_CRASH_POINTS = frozenset(("before_replace", "after_replace"))


@dataclass(frozen=True)
class PreparedClaudePublication:
    contract: ClaudePublicationPlan
    content: bytes
    target: Path
    manifest: ClaudeGlobalProjectionManifest

    def verify(self) -> bool:
        if not isinstance(self.contract, ClaudePublicationPlan):
            raise ClaudeContractError("publication plan contract type is invalid")
        if not isinstance(self.content, bytes):
            raise ClaudeContractError("publication content must be immutable bytes")
        if not isinstance(self.target, Path) or not self.target.is_absolute():
            raise ClaudeContractError("publication target must be an absolute Path")
        if not isinstance(self.manifest, ClaudeGlobalProjectionManifest):
            raise ClaudeContractError("publication manifest type is invalid")
        self.contract.verify()
        self.manifest.verify()
        if self.contract.projection_ref != self.manifest.projection_ref:
            raise ClaudeContractError("publication projection ref mismatch")
        if self.contract.projection_digest != self.manifest.digest:
            raise ClaudeContractError("publication projection digest mismatch")
        if self.contract.content_bytes != len(self.content):
            raise ClaudeContractError("publication content byte count mismatch")
        if self.contract.content_sha256 != _sha256_bytes(self.content):
            raise ClaudeContractError("publication content digest mismatch")
        if self.contract.content_bytes != self.manifest.content_bytes:
            raise ClaudeContractError("publication content/manifest byte count mismatch")
        if self.contract.content_sha256 != self.manifest.content_sha256:
            raise ClaudeContractError("publication content/manifest digest mismatch")
        if self.contract.target_ref != _file_ref(self.target):
            raise ClaudeContractError("publication target ref mismatch")
        return True


class ClaudeProjectionPublisher:
    def __init__(self, runtime_root: Path, *, crash_at: str | None = None):
        root = Path(runtime_root)
        if not root.is_absolute():
            raise ClaudePathBoundaryError("runtime root must be caller-supplied absolute")
        if crash_at is not None and crash_at not in _CRASH_POINTS:
            raise ValueError(f"unknown crash point: {crash_at}")
        self._runtime_root = root
        self._crash_at = crash_at
        self._writer_lock_path = root / ".claude-projection.writer.lock"

    def plan(
        self,
        result: ClaudeGlobalProjectionResult,
        target: Path,
        expected_digest: str | None,
    ) -> PreparedClaudePublication:
        self._validate_result(result)
        selected_target = self._validate_target(Path(target))
        _validate_optional_digest(expected_digest, field="expected_digest")
        observed = self._observe_target(selected_target)
        if observed != expected_digest:
            raise StaleTargetError("projection target pre-image digest mismatch")

        identity_material = {
            "projection_ref": result.manifest.projection_ref,
            "projection_digest": result.manifest.digest,
            "content_bytes": len(result.content),
            "content_sha256": _sha256_bytes(result.content),
            "target_ref": _file_ref(selected_target),
            "target_preimage_sha256": observed,
        }
        plan_id = "publication-plan:" + sha256_domain(
            _PLAN_ID_DOMAIN,
            canonical_json_bytes(identity_material),
        )
        contract = ClaudePublicationPlan.sealed(
            {
                "publication_plan_version": "mneme.claude-publication-plan/0.1",
                "plan_id": plan_id,
                **identity_material,
                "not_claimed": list(CLAUDE_GLOBAL_NONCLAIMS),
            }
        )
        prepared = PreparedClaudePublication(
            contract=contract,
            content=result.content,
            target=selected_target,
            manifest=result.manifest,
        )
        prepared.verify()
        return prepared

    def publish(
        self,
        plan: PreparedClaudePublication,
        authorization: LocalManualWriteAuthorization,
    ) -> ClaudePublicationReceipt:
        if not isinstance(plan, PreparedClaudePublication):
            raise ClaudeContractError("prepared publication type is invalid")
        plan.verify()
        self._validate_authorization(authorization)
        target = self._validate_target(plan.target)
        if _file_ref(target) != plan.contract.target_ref:
            raise ClaudeContractError("publication target changed after planning")

        self._validate_writer_lock_path()
        with StoreWriterLock(self._writer_lock_path):
            return self._publish_locked(plan, authorization)

    def _publish_locked(
        self,
        plan: PreparedClaudePublication,
        authorization: LocalManualWriteAuthorization,
    ) -> ClaudePublicationReceipt:
        target = self._validate_target(plan.target)
        if _file_ref(target) != plan.contract.target_ref:
            raise ClaudeContractError("publication target changed after planning")

        before_digest = self._observe_target(target)
        if before_digest != plan.contract.target_preimage_sha256:
            raise StaleTargetError("projection target changed after planning")

        content_digest = _sha256_bytes(plan.content)
        if before_digest == content_digest:
            outcome = "idempotent"
        else:
            self._replace_atomically(
                target,
                plan.content,
                expected_preimage=before_digest,
            )
            outcome = "published"

        readback_digest = self._observe_target(target)
        if readback_digest != content_digest:
            raise ClaudeContractError("projection target readback digest mismatch")

        receipt_identity = {
            "publication_plan_ref": plan.contract.plan_id,
            "publication_plan_digest": plan.contract.digest,
            "authorization_ref": authorization.authorization_id,
            "authorization_digest": authorization.digest,
            "projection_ref": plan.contract.projection_ref,
            "projection_digest": plan.contract.projection_digest,
            "target_ref": plan.contract.target_ref,
            "target_before_sha256": before_digest,
            "target_after_sha256": content_digest,
            "readback_sha256": readback_digest,
            "content_bytes": len(plan.content),
            "outcome": outcome,
        }
        receipt_id = "publication-receipt:" + sha256_domain(
            _RECEIPT_ID_DOMAIN,
            canonical_json_bytes(receipt_identity),
        )
        return ClaudePublicationReceipt.sealed(
            {
                "publication_receipt_version": "mneme.claude-publication-receipt/0.1",
                "receipt_id": receipt_id,
                **receipt_identity,
                "not_claimed": list(CLAUDE_GLOBAL_NONCLAIMS),
            }
        )

    def _validate_writer_lock_path(self) -> None:
        path = self._writer_lock_path
        if path.is_symlink():
            raise ClaudePathBoundaryError("publication writer lock cannot be a symlink")
        if path.exists():
            metadata = path.lstat()
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise ClaudePathBoundaryError(
                    "publication writer lock must be one regular file"
                )

    @staticmethod
    def _validate_result(result: ClaudeGlobalProjectionResult) -> None:
        if not isinstance(result, ClaudeGlobalProjectionResult):
            raise ClaudeContractError("projection result type is invalid")
        result.manifest.verify()
        if len(result.content) != result.manifest.content_bytes:
            raise ClaudeContractError("projection result byte count mismatch")
        if _sha256_bytes(result.content) != result.manifest.content_sha256:
            raise ClaudeContractError("projection result digest mismatch")

    @staticmethod
    def _validate_authorization(
        authorization: LocalManualWriteAuthorization,
    ) -> None:
        if not isinstance(authorization, LocalManualWriteAuthorization):
            raise ManualAuthorityError("local manual authorization type is invalid")
        authorization.verify()
        if not authorization.is_active:
            raise ManualAuthorityError("local manual authorization is not active")

    def _validate_runtime_root(self) -> Path:
        root = self._runtime_root
        _reject_network_or_uri(root)
        _reject_ads(root)
        if root.is_symlink():
            raise ClaudePathBoundaryError("runtime root cannot be a symlink")
        try:
            resolved = root.resolve(strict=True)
        except (FileNotFoundError, OSError) as error:
            raise ClaudePathBoundaryError("runtime root must already exist") from error
        if not resolved.is_dir():
            raise ClaudePathBoundaryError("runtime root must be a directory")
        _reject_strong_private_parts(resolved)
        if _has_git_ancestor(resolved):
            raise ClaudePathBoundaryError("runtime root cannot be inside a Git tree")
        return resolved

    def _validate_target(self, target: Path) -> Path:
        root = self._validate_runtime_root()
        _reject_network_or_uri(target)
        _reject_ads(target)
        if not target.is_absolute():
            raise ClaudePathBoundaryError("projection target must be absolute")
        if ".." in target.parts:
            raise ClaudePathBoundaryError("projection target cannot contain traversal")
        _reject_symlink_chain(target, stop=root)
        try:
            resolved = target.resolve(strict=False)
        except OSError as error:
            raise ClaudePathBoundaryError("projection target cannot be resolved") from error
        if resolved == root or not resolved.is_relative_to(root):
            raise ClaudePathBoundaryError("projection target escapes runtime root")
        _reject_strong_private_parts(resolved)
        relative_parts = {part.casefold() for part in resolved.relative_to(root).parts}
        if relative_parts.intersection(_FORBIDDEN_RELATIVE_PARTS):
            raise ClaudePathBoundaryError("projection target uses a forbidden path class")
        if _has_git_ancestor(resolved.parent):
            raise ClaudePathBoundaryError("projection target cannot be inside a Git tree")
        if not resolved.parent.exists() or not resolved.parent.is_dir():
            raise ClaudePathBoundaryError("projection target parent must already exist")
        if resolved.exists():
            metadata = resolved.lstat()
            if not stat.S_ISREG(metadata.st_mode):
                raise ClaudePathBoundaryError("projection target must be a regular file")
            if metadata.st_nlink != 1:
                raise ClaudePathBoundaryError("projection target hardlink count must be one")
        elif resolved.is_symlink():
            raise ClaudePathBoundaryError("projection target cannot be a symlink")
        return resolved

    def _observe_target(self, target: Path) -> str | None:
        try:
            before = target.lstat()
        except FileNotFoundError:
            return None
        if not stat.S_ISREG(before.st_mode):
            raise ClaudePathBoundaryError("projection target must remain a regular file")
        if before.st_nlink != 1:
            raise ClaudePathBoundaryError("projection target hardlink count must remain one")

        digest = hashlib.sha256()
        try:
            with target.open("rb") as handle:
                opened = os.fstat(handle.fileno())
                if not _same_file_state(before, opened):
                    raise StaleTargetError("projection target changed before read")
                while chunk := handle.read(65536):
                    digest.update(chunk)
                finished = os.fstat(handle.fileno())
        except FileNotFoundError as error:
            raise StaleTargetError("projection target disappeared during read") from error
        try:
            after = target.lstat()
        except FileNotFoundError as error:
            raise StaleTargetError("projection target disappeared after read") from error
        if not _same_file_state(opened, finished) or not _same_file_state(finished, after):
            raise StaleTargetError("projection target changed during read")
        return digest.hexdigest()

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
            if self._observe_target(target) != expected_preimage:
                raise StaleTargetError("projection target changed before atomic replace")
            os.replace(temporary, target)
            _fsync_directory(target.parent)
            if self._crash_at == "after_replace":
                raise InjectedCrash("injected crash at after_replace")
        finally:
            temporary.unlink(missing_ok=True)


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _file_ref(path: Path) -> str:
    if not path.is_absolute():
        raise ClaudeContractError("local file ref requires an absolute path")
    return path.as_uri()


def _validate_optional_digest(value: str | None, *, field: str) -> None:
    if value is None:
        return
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise StaleTargetError(f"{field} must be null or lowercase SHA-256")


def _reject_network_or_uri(path: Path) -> None:
    raw = str(path)
    if raw.startswith(("\\\\", "//")) or "://" in raw:
        raise ClaudePathBoundaryError("network and URI paths are forbidden")


def _reject_ads(path: Path) -> None:
    raw = str(path)
    drive = PureWindowsPath(raw).drive
    remainder = raw[len(drive) :]
    if ":" in remainder:
        raise ClaudePathBoundaryError("alternate data stream paths are forbidden")


def _reject_strong_private_parts(path: Path) -> None:
    parts = {part.casefold() for part in path.parts}
    if parts.intersection(_STRONG_PRIVATE_PARTS):
        raise ClaudePathBoundaryError("private path markers are forbidden")


def _reject_symlink_chain(path: Path, *, stop: Path) -> None:
    current = path
    while True:
        if current.is_symlink():
            raise ClaudePathBoundaryError("projection path cannot contain a symlink")
        if current == stop or current.parent == current:
            return
        current = current.parent


def _has_git_ancestor(path: Path) -> bool:
    current = path
    while True:
        if (current / ".git").exists():
            return True
        if current.parent == current:
            return False
        current = current.parent


def _same_file_state(first: os.stat_result, second: os.stat_result) -> bool:
    return (
        first.st_dev,
        first.st_ino,
        first.st_size,
        first.st_mtime_ns,
        first.st_nlink,
    ) == (
        second.st_dev,
        second.st_ino,
        second.st_size,
        second.st_mtime_ns,
        second.st_nlink,
    )


def _fsync_directory(directory: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
