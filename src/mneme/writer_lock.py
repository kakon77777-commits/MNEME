from __future__ import annotations

import os
import threading
from pathlib import Path
from types import TracebackType
from typing import Self

from .errors import StoreWriterBusyError

_REGISTRY_GUARD = threading.Lock()
_LOCAL_LOCKS: dict[str, threading.Lock] = {}


def _lock_key(path: Path) -> str:
    return os.path.normcase(str(path.resolve(strict=False)))


def _local_lock(path: Path) -> threading.Lock:
    key = _lock_key(path)
    with _REGISTRY_GUARD:
        return _LOCAL_LOCKS.setdefault(key, threading.Lock())


class StoreWriterLock:
    def __init__(self, path: Path, *, blocking: bool = False):
        self.path = Path(path)
        self.blocking = blocking
        self._thread_lock: threading.Lock | None = None
        self._handle = None

    def __enter__(self) -> Self:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        thread_lock = _local_lock(self.path)
        if not thread_lock.acquire(blocking=self.blocking):
            raise StoreWriterBusyError("store writer lock is busy")
        self._thread_lock = thread_lock
        try:
            handle = self.path.open("a+b", buffering=0)
            if handle.seek(0, os.SEEK_END) == 0:
                handle.write(b"\0")
                handle.flush()
                os.fsync(handle.fileno())
            handle.seek(0)
            self._lock_handle(handle)
            self._handle = handle
        except Exception:
            if "handle" in locals():
                handle.close()
            thread_lock.release()
            self._thread_lock = None
            raise
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if self._handle is not None:
                try:
                    self._unlock_handle(self._handle)
                finally:
                    self._handle.close()
        finally:
            self._handle = None
            if self._thread_lock is not None:
                self._thread_lock.release()
                self._thread_lock = None

    def _lock_handle(self, handle) -> None:
        try:
            if os.name == "nt":
                import msvcrt

                mode = msvcrt.LK_LOCK if self.blocking else msvcrt.LK_NBLCK
                msvcrt.locking(handle.fileno(), mode, 1)
            else:
                import fcntl

                mode = fcntl.LOCK_EX
                if not self.blocking:
                    mode |= fcntl.LOCK_NB
                fcntl.flock(handle.fileno(), mode)
        except OSError as error:
            raise StoreWriterBusyError("store writer lock is busy") from error

    @staticmethod
    def _unlock_handle(handle) -> None:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
