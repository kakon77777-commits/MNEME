from __future__ import annotations

import json
import os
import tempfile
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, replace
from pathlib import Path

from .canonical import canonical_json_bytes, sha256_domain
from .errors import (
    RecordIdConflictError,
    StoreConflictError,
    StoreIntegrityError,
    TransactionValidationError,
)
from .transactions import TransactionProposal
from .writer_lock import StoreWriterLock

_HEAD_DOMAIN = b"MNEME-HEAD-0.1"
_RECEIPT_VERSION = "mneme.commit-receipt/0.1"


@dataclass(frozen=True)
class CommitReceipt:
    transaction_digest: str
    previous_head: str
    new_head: str
    idempotent: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": _RECEIPT_VERSION,
            "transaction_digest": self.transaction_digest,
            "previous_head": self.previous_head,
            "new_head": self.new_head,
        }


class MemoryStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self._committed = self.root / "transactions" / "committed"
        self._receipts = self.root / "transactions" / "receipts"
        self._head_path = self.root / "HEAD"
        self._writer_lock_path = self.root / ".writer.lock"

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with StoreWriterLock(self._writer_lock_path):
            self._initialize_unlocked()

    def _initialize_unlocked(self) -> None:
        self._committed.mkdir(parents=True, exist_ok=True)
        self._receipts.mkdir(parents=True, exist_ok=True)
        if not self._head_path.exists():
            self._atomic_write_head("GENESIS")
        else:
            self.head()

    def head(self) -> str:
        try:
            raw = self._head_path.read_bytes()
        except FileNotFoundError as exc:
            raise StoreIntegrityError("HEAD is missing") from exc
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError as exc:
            raise StoreIntegrityError("HEAD is not ASCII") from exc
        if not text.endswith("\n") or text.count("\n") != 1:
            raise StoreIntegrityError("HEAD must contain exactly one terminal LF")
        value = text[:-1]
        if value != "GENESIS" and not _is_digest(value):
            raise StoreIntegrityError("HEAD must be GENESIS or a lowercase SHA-256 digest")
        return value

    def commit(self, tx: TransactionProposal) -> CommitReceipt:
        self.root.mkdir(parents=True, exist_ok=True)
        with StoreWriterLock(self._writer_lock_path):
            self._initialize_unlocked()
            tx_digest = tx.digest()
            tx_path = self._committed / f"{tx_digest}.json"
            receipt_path = self._receipts / f"{tx_digest}.json"
            canonical_tx = canonical_json_bytes(tx.to_dict()) + b"\n"

            if tx_path.exists() or receipt_path.exists():
                return self._verify_existing_replay(tx, canonical_tx, tx_path, receipt_path)

            current_head = self.head()
            try:
                tx.validate_for_head(current_head)
            except TransactionValidationError as exc:
                raise StoreConflictError(str(exc)) from exc
            self._validate_record_id_population_unlocked(tx)

            new_head = _next_head(current_head, tx_digest)
            receipt = CommitReceipt(tx_digest, current_head, new_head)
            canonical_receipt = canonical_json_bytes(receipt.to_dict()) + b"\n"

            self._publish_immutable(tx_path, canonical_tx)
            self._publish_immutable(receipt_path, canonical_receipt)

            if self.head() != current_head:
                raise StoreConflictError("HEAD changed during commit")
            self._atomic_write_head(new_head)
            if self.head() != new_head:
                raise StoreIntegrityError("HEAD readback mismatch after commit")
            committed = list(self._iter_committed_transactions_unlocked())
            if not committed or committed[-1] != tx.to_dict():
                raise StoreIntegrityError("committed transaction is not reachable from HEAD")
            stored_receipt = self._load_receipt(receipt_path)
            if stored_receipt != receipt:
                raise StoreIntegrityError("receipt readback mismatch after commit")
            return receipt

    def iter_committed_transactions(self) -> Iterator[dict[str, object]]:
        self.initialize()
        yield from self._iter_committed_transactions_unlocked()

    def verify_current_transaction(
        self,
        tx: TransactionProposal,
        receipt: CommitReceipt,
    ) -> bool:
        if not self.root.exists() or not self._head_path.exists():
            raise StoreIntegrityError("committed store evidence is unavailable")
        before = self.head()
        if before != receipt.new_head:
            raise StoreIntegrityError("commit receipt is not the current head")
        reachable = list(self._iter_committed_transactions_unlocked())
        after = self.head()
        if after != before:
            raise StoreIntegrityError("HEAD changed during committed readback")
        if not reachable or reachable[-1] != tx.to_dict():
            raise StoreIntegrityError("current transaction readback mismatch")
        return True

    def _iter_committed_transactions_unlocked(self) -> Iterator[dict[str, object]]:
        target_head = self.head()
        if target_head == "GENESIS":
            return

        by_new_head: dict[str, tuple[CommitReceipt, Path]] = {}
        for receipt_path in self._receipts.glob("*.json"):
            receipt = self._load_receipt(receipt_path)
            if receipt.new_head in by_new_head:
                raise StoreIntegrityError("multiple receipts claim the same new_head")
            by_new_head[receipt.new_head] = (receipt, receipt_path)

        chain: list[CommitReceipt] = []
        cursor = target_head
        seen: set[str] = set()
        while cursor != "GENESIS":
            if cursor in seen:
                raise StoreIntegrityError("receipt chain cycle detected")
            seen.add(cursor)
            item = by_new_head.get(cursor)
            if item is None:
                raise StoreIntegrityError("HEAD is not reachable from receipts")
            receipt, _ = item
            if _next_head(receipt.previous_head, receipt.transaction_digest) != receipt.new_head:
                raise StoreIntegrityError("receipt head transition digest mismatch")
            chain.append(receipt)
            cursor = receipt.previous_head

        for receipt in reversed(chain):
            tx_path = self._committed / f"{receipt.transaction_digest}.json"
            yield self._load_transaction(tx_path, expected_digest=receipt.transaction_digest)

    def validate_record_id_population(self, tx: TransactionProposal) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with StoreWriterLock(self._writer_lock_path):
            self._initialize_unlocked()
            self._validate_record_id_population_unlocked(tx)

    def _validate_record_id_population_unlocked(self, tx: TransactionProposal) -> None:
        proposed_ids = [record["record_id"] for record in tx.to_dict()["records"]]
        duplicate_ids = {
            record_id for record_id, count in Counter(proposed_ids).items() if count > 1
        }
        if duplicate_ids:
            joined = ", ".join(sorted(duplicate_ids))
            raise RecordIdConflictError(f"duplicate record_id in transaction: {joined}")

        existing_ids = {
            record.to_dict()["record_id"]
            for record in self._iter_committed_records_unlocked()
        }
        conflicting_ids = existing_ids.intersection(proposed_ids)
        if conflicting_ids:
            joined = ", ".join(sorted(conflicting_ids))
            raise RecordIdConflictError(f"record_id already committed: {joined}")

    def iter_committed_records(self):
        self.initialize()
        yield from self._iter_committed_records_unlocked()

    def _iter_committed_records_unlocked(self):
        from .records import MemoryRecord

        for tx in self._iter_committed_transactions_unlocked():
            for raw in tx["records"]:
                yield MemoryRecord.from_dict(raw)

    def _verify_existing_replay(
        self,
        tx: TransactionProposal,
        canonical_tx: bytes,
        tx_path: Path,
        receipt_path: Path,
    ) -> CommitReceipt:
        if not tx_path.exists() or not receipt_path.exists():
            raise StoreIntegrityError("partial existing transaction/receipt publication")
        if tx_path.read_bytes() != canonical_tx:
            raise StoreIntegrityError("existing transaction bytes do not match proposal")
        receipt = self._load_receipt(receipt_path)
        if receipt.transaction_digest != tx.digest():
            raise StoreIntegrityError("receipt transaction digest mismatch")
        if _next_head(receipt.previous_head, receipt.transaction_digest) != receipt.new_head:
            raise StoreIntegrityError("receipt new_head mismatch")
        current = self.head()
        if current != receipt.new_head:
            raise StoreConflictError("transaction already exists but is not current HEAD")
        return replace(receipt, idempotent=True)

    def _load_transaction(self, path: Path, *, expected_digest: str) -> dict[str, object]:
        try:
            raw = path.read_bytes()
        except FileNotFoundError as exc:
            raise StoreIntegrityError("committed transaction file is missing") from exc
        if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
            raise StoreIntegrityError("committed transaction must have one terminal LF")
        try:
            value = json.loads(raw[:-1].decode("utf-8"))
            tx = TransactionProposal.from_dict(value)
        except Exception as exc:
            raise StoreIntegrityError("committed transaction cannot be validated") from exc
        if canonical_json_bytes(tx.to_dict()) + b"\n" != raw:
            raise StoreIntegrityError("committed transaction is not canonical bytes")
        if tx.digest() != expected_digest:
            raise StoreIntegrityError("committed transaction digest mismatch")
        return tx.to_dict()

    def _load_receipt(self, path: Path) -> CommitReceipt:
        try:
            raw = path.read_bytes()
            if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
                raise StoreIntegrityError("receipt must have one terminal LF")
            value = json.loads(raw[:-1].decode("utf-8"))
        except StoreIntegrityError:
            raise
        except Exception as exc:
            raise StoreIntegrityError("receipt is unreadable") from exc
        required = {"receipt_version", "transaction_digest", "previous_head", "new_head"}
        if set(value) != required or value.get("receipt_version") != _RECEIPT_VERSION:
            raise StoreIntegrityError("receipt shape/version mismatch")
        receipt = CommitReceipt(
            transaction_digest=value["transaction_digest"],
            previous_head=value["previous_head"],
            new_head=value["new_head"],
        )
        if not _is_digest(receipt.transaction_digest):
            raise StoreIntegrityError("receipt transaction digest invalid")
        if receipt.previous_head != "GENESIS" and not _is_digest(receipt.previous_head):
            raise StoreIntegrityError("receipt previous head invalid")
        if not _is_digest(receipt.new_head):
            raise StoreIntegrityError("receipt new head invalid")
        if canonical_json_bytes(receipt.to_dict()) + b"\n" != raw:
            raise StoreIntegrityError("receipt is not canonical bytes")
        return receipt

    def _publish_immutable(self, final: Path, content: bytes) -> None:
        final.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{final.name}.", dir=final.parent)
        temp = Path(temp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temp, final)
            except FileExistsError:
                if final.read_bytes() != content:
                    raise StoreIntegrityError("immutable publication collision")
            finally:
                temp.unlink(missing_ok=True)
        except Exception:
            temp.unlink(missing_ok=True)
            raise

    def _atomic_write_head(self, head: str) -> None:
        if head != "GENESIS" and not _is_digest(head):
            raise StoreIntegrityError("refusing to write invalid HEAD")
        self.root.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=".HEAD.", dir=self.root)
        temp = Path(temp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(head.encode("ascii") + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self._head_path)
        finally:
            temp.unlink(missing_ok=True)


def _is_digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _next_head(previous_head: str, transaction_digest: str) -> str:
    payload = previous_head.encode("ascii") + b"\0" + transaction_digest.encode("ascii")
    return sha256_domain(_HEAD_DOMAIN, payload)
