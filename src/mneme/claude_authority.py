from __future__ import annotations

from dataclasses import dataclass

from .canonical import canonical_json_bytes, sha256_domain
from .claude_contracts import (
    ClaudeGlobalProjectionManifest,
    LocalManualWriteAuthorization,
)
from .errors import ManualAuthorityError
from .store import CommitReceipt, MemoryStore, _next_head
from .transactions import TransactionProposal

_COMMIT_RECEIPT_DOMAIN = b"MNEME-COMMIT-RECEIPT-EVIDENCE-0.1"


def commit_receipt_digest(receipt: CommitReceipt) -> str:
    if not isinstance(receipt, CommitReceipt):
        raise ManualAuthorityError("commit receipt type is invalid")
    return sha256_domain(_COMMIT_RECEIPT_DOMAIN, canonical_json_bytes(receipt.to_dict()))


@dataclass(frozen=True)
class VerifiedClaudeWriteContext:
    store: MemoryStore
    transaction: TransactionProposal
    commit_receipt: CommitReceipt
    authorization: LocalManualWriteAuthorization

    @classmethod
    def bind(
        cls,
        store: MemoryStore,
        transaction: TransactionProposal,
        commit_receipt: CommitReceipt,
        authorization: LocalManualWriteAuthorization,
    ) -> VerifiedClaudeWriteContext:
        selected = cls(store, transaction, commit_receipt, authorization)
        selected.verify()
        return selected

    @property
    def transaction_ref(self) -> str:
        return str(self.transaction.to_dict()["transaction_id"])

    @property
    def transaction_digest(self) -> str:
        return self.transaction.digest()

    @property
    def committed_head(self) -> str:
        return self.commit_receipt.new_head

    @property
    def commit_receipt_digest(self) -> str:
        return commit_receipt_digest(self.commit_receipt)

    def verify(self) -> bool:
        if not isinstance(self.store, MemoryStore):
            raise ManualAuthorityError("memory store type is invalid")
        if not isinstance(self.transaction, TransactionProposal):
            raise ManualAuthorityError("transaction type is invalid")
        if not isinstance(self.commit_receipt, CommitReceipt):
            raise ManualAuthorityError("commit receipt type is invalid")
        if not isinstance(self.authorization, LocalManualWriteAuthorization):
            raise ManualAuthorityError("local manual authorization type is invalid")
        if not self.store.root.is_absolute() or not self.store.root.exists():
            raise ManualAuthorityError("committed store evidence is unavailable")

        try:
            self.authorization.verify()
            if not self.authorization.is_active:
                raise ManualAuthorityError("local manual authorization is not active")

            transaction = self.transaction.to_dict()
            transaction_ref = str(transaction["transaction_id"])
            transaction_digest = self.transaction.digest()
            expected_head = self.authorization.expected_source_head
            self.transaction.validate_for_head(expected_head)

            if self.authorization.transaction_ref != transaction_ref:
                raise ManualAuthorityError("authorization transaction ref mismatch")
            if self.authorization.transaction_digest != transaction_digest:
                raise ManualAuthorityError("authorization transaction digest mismatch")
            if transaction["authority_ref"] != self.authorization.authorization_id:
                raise ManualAuthorityError("transaction authority ref mismatch")

            transaction_scopes = {
                f"{record['scope']['kind']}/{record['scope']['subject']}"
                for record in transaction["records"]
            }
            if not transaction_scopes.issubset(
                set(self.authorization.allowed_scope_paths)
            ):
                raise ManualAuthorityError(
                    "authorization does not cover transaction scopes"
                )

            receipt = self.commit_receipt
            if receipt.transaction_digest != transaction_digest:
                raise ManualAuthorityError("commit receipt transaction digest mismatch")
            if receipt.previous_head != expected_head:
                raise ManualAuthorityError("commit receipt previous head mismatch")
            if receipt.new_head != _next_head(expected_head, transaction_digest):
                raise ManualAuthorityError("commit receipt new head mismatch")

            before = self.store.head()
            if before != receipt.new_head:
                raise ManualAuthorityError("committed store current head mismatch")
            self.store.verify_current_transaction(self.transaction, receipt)
            commit_receipt_digest(receipt)
        except ManualAuthorityError:
            raise
        except Exception as error:
            raise ManualAuthorityError(
                f"committed write context cannot be verified: {error}"
            ) from error
        return True

    def verify_projection(self, manifest: ClaudeGlobalProjectionManifest) -> bool:
        self.verify()
        if not isinstance(manifest, ClaudeGlobalProjectionManifest):
            raise ManualAuthorityError("projection manifest type is invalid")
        manifest.verify()
        if manifest.source_head != self.committed_head:
            raise ManualAuthorityError("projection source head is not the committed head")
        transaction = self.transaction.to_dict()
        record_ids = {str(record["record_id"]) for record in transaction["records"]}
        if not set(manifest.included_record_ids).issubset(record_ids):
            raise ManualAuthorityError(
                "projection includes a record outside the committed transaction"
            )
        if not set(manifest.required_record_ids).issubset(record_ids):
            raise ManualAuthorityError(
                "projection requires a record outside the committed transaction"
            )
        return True
