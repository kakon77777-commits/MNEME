from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .adapters.claude import ClaudeGlobalMemoryAdapter
from .canonical import canonical_json_bytes, sha256_domain
from .claude_authority import VerifiedClaudeWriteContext, commit_receipt_digest
from .claude_contracts import (
    CLAUDE_GLOBAL_SCOPE_PATHS,
    ClaudeGlobalProjectionRequest,
    ClaudeImportReceipt,
    ClaudePublicationReceipt,
    LocalManualWriteAuthorization,
)
from .claude_import import ClaudeManagedImport
from .claude_projection import (
    ClaudeProjectionPublisher,
    _file_ref,
    _has_git_ancestor,
    _reject_ads,
    _reject_control_characters,
    _reject_network_or_uri,
    _reject_strong_private_parts,
    _reject_symlink_chain,
    _sha256_bytes,
)
from .errors import ClaudeContractError, ManualAuthorityError
from .routes import Route
from .store import CommitReceipt, MemoryStore, _next_head
from .transactions import TransactionProposal

_PLAN_DOMAIN = b"MNEME-CLAUDE-SYNTHETIC-ACTIVATION-PLAN-0.1"
_RECEIPT_DOMAIN = b"MNEME-CLAUDE-SYNTHETIC-ACTIVATION-RECEIPT-0.1"
_SYNTHETIC_USER_MEMORY = b"# Synthetic Claude user memory.\n"
_ALLOWED_RECORD_TYPES = frozenset(("instruction", "fact", "lesson"))


@dataclass(frozen=True)
class ClaudeSyntheticActivationConfig:
    sandbox_root: Path
    execution_mode: str = "synthetic_test"

    def __post_init__(self) -> None:
        object.__setattr__(self, "sandbox_root", Path(self.sandbox_root))
        self.verify()

    def verify(self) -> bool:
        root = self.sandbox_root
        if self.execution_mode != "synthetic_test":
            raise ClaudeContractError("activation execution mode must be synthetic_test")
        if not root.is_absolute():
            raise ClaudeContractError("synthetic sandbox root must be absolute")
        _reject_control_characters(root, label="synthetic sandbox root")
        _reject_network_or_uri(root)
        _reject_ads(root)
        _reject_strong_private_parts(root)
        if not root.parent.exists() or not root.parent.is_dir():
            raise ClaudeContractError("synthetic sandbox parent must already exist")
        _reject_symlink_chain(root.parent, stop=root.parent)
        if _has_git_ancestor(root.parent):
            raise ClaudeContractError("synthetic sandbox cannot be inside a Git tree")
        return True

    @property
    def runtime_root(self) -> Path:
        return self.sandbox_root / "runtime"

    @property
    def store_root(self) -> Path:
        return self.runtime_root / "shared-global" / "memory.mlfdir"

    @property
    def projection_target(self) -> Path:
        return self.runtime_root / "claude" / "MNEME_GLOBAL.md"

    @property
    def user_memory_root(self) -> Path:
        return self.sandbox_root / "synthetic-user"

    @property
    def user_memory_target(self) -> Path:
        return self.user_memory_root / ".claude" / "CLAUDE.md"

    def to_dict(self) -> dict[str, object]:
        self.verify()
        return {
            "execution_mode": self.execution_mode,
            "sandbox_root_ref": _file_ref(self.sandbox_root),
            "store_root_ref": _file_ref(self.store_root),
            "projection_target_ref": _file_ref(self.projection_target),
            "user_memory_target_ref": _file_ref(self.user_memory_target),
        }


@dataclass(frozen=True)
class ClaudeSyntheticActivationPlan:
    config: ClaudeSyntheticActivationConfig
    transaction: TransactionProposal
    request: ClaudeGlobalProjectionRequest
    expected_final_head: str
    plan_digest: str

    @property
    def transaction_ref(self) -> str:
        return str(self.transaction.to_dict()["transaction_id"])

    @property
    def transaction_digest(self) -> str:
        return self.transaction.digest()

    @property
    def request_ref(self) -> str:
        return self.request.request_id

    @property
    def request_digest(self) -> str:
        return self.request.digest

    def _material(self) -> dict[str, object]:
        return {
            "activation_plan_version": "mneme.claude-synthetic-activation-plan/0.1",
            **self.config.to_dict(),
            "transaction_ref": self.transaction_ref,
            "transaction_digest": self.transaction_digest,
            "request_ref": self.request_ref,
            "request_digest": self.request_digest,
            "expected_final_head": self.expected_final_head,
            "production_wave_run": "NOT_APPLICABLE",
        }

    def verify(self) -> bool:
        _validate_plan_inputs(self.config, self.transaction, self.request)
        predicted = _next_head("GENESIS", self.transaction_digest)
        if self.expected_final_head != predicted:
            raise ClaudeContractError("activation expected final head mismatch")
        expected = sha256_domain(_PLAN_DOMAIN, canonical_json_bytes(self._material()))
        if self.plan_digest != expected:
            raise ClaudeContractError("activation plan digest mismatch")
        return True

    def to_dict(self) -> dict[str, object]:
        self.verify()
        return {
            "status": "PLANNED",
            **self._material(),
            "plan_digest": self.plan_digest,
        }


@dataclass(frozen=True)
class ClaudeSyntheticActivationReceipt:
    activation_id: str
    plan_digest: str
    steps: tuple[str, ...]
    commit_receipt: CommitReceipt
    projection_receipt: ClaudePublicationReceipt
    import_receipt: ClaudeImportReceipt
    final_head: str
    production_wave_run: str
    claude_memory_readback: str
    real_claude_user_memory: str
    private_residence: str
    digest: str

    def _material(self) -> dict[str, object]:
        return {
            "activation_receipt_version": "mneme.claude-synthetic-activation-receipt/0.1",
            "activation_id": self.activation_id,
            "plan_digest": self.plan_digest,
            "steps": list(self.steps),
            "commit_receipt": self.commit_receipt.to_dict(),
            "projection_receipt": self.projection_receipt.to_dict(),
            "import_receipt": self.import_receipt.to_dict(),
            "final_head": self.final_head,
            "production_wave_run": self.production_wave_run,
            "claude_memory_readback": self.claude_memory_readback,
            "real_claude_user_memory": self.real_claude_user_memory,
            "private_residence": self.private_residence,
            "status": "PASS",
        }

    def verify(self) -> bool:
        self.projection_receipt.verify()
        self.import_receipt.verify()
        if (
            self.projection_receipt.authorization_ref,
            self.projection_receipt.authorization_digest,
        ) != (
            self.import_receipt.authorization_ref,
            self.import_receipt.authorization_digest,
        ):
            raise ClaudeContractError("activation receipt authorization binding mismatch")
        if (
            self.projection_receipt.projection_ref,
            self.projection_receipt.projection_digest,
        ) != (
            self.import_receipt.projection_ref,
            self.import_receipt.projection_digest,
        ):
            raise ClaudeContractError("activation receipt projection binding mismatch")
        if (
            self.projection_receipt.transaction_ref,
            self.projection_receipt.transaction_digest,
            self.projection_receipt.committed_head,
            self.projection_receipt.commit_receipt_digest,
        ) != (
            self.import_receipt.transaction_ref,
            self.import_receipt.transaction_digest,
            self.import_receipt.committed_head,
            self.import_receipt.commit_receipt_digest,
        ):
            raise ClaudeContractError("activation receipt transaction binding mismatch")
        if (
            self.import_receipt.publication_receipt_ref,
            self.import_receipt.publication_receipt_digest,
        ) != (
            self.projection_receipt.receipt_id,
            self.projection_receipt.digest,
        ):
            raise ClaudeContractError("activation receipt publication binding mismatch")
        if self.projection_receipt.transaction_digest != self.commit_receipt.transaction_digest:
            raise ClaudeContractError("activation receipt commit transaction mismatch")
        if self.projection_receipt.committed_head != self.commit_receipt.new_head:
            raise ClaudeContractError("activation receipt commit head mismatch")
        if self.projection_receipt.commit_receipt_digest != commit_receipt_digest(
            self.commit_receipt
        ):
            raise ClaudeContractError("activation receipt commit evidence mismatch")
        if self.steps != (
            "canonical_commit",
            "projection_publish",
            "managed_import",
        ):
            raise ClaudeContractError("activation receipt step order mismatch")
        if self.commit_receipt.new_head != self.final_head:
            raise ClaudeContractError("activation receipt final head mismatch")
        if self.production_wave_run != "NOT_APPLICABLE":
            raise ClaudeContractError("production wave status must be NOT_APPLICABLE")
        if self.claude_memory_readback != "NOT_RUN":
            raise ClaudeContractError("Claude memory readback must be NOT_RUN")
        if self.real_claude_user_memory != "NOT_TOUCHED":
            raise ClaudeContractError("real Claude user memory must be NOT_TOUCHED")
        if self.private_residence != "NOT_READ":
            raise ClaudeContractError("private Residence must be NOT_READ")
        expected = sha256_domain(_RECEIPT_DOMAIN, canonical_json_bytes(self._material()))
        if self.digest != expected:
            raise ClaudeContractError("activation receipt digest mismatch")
        return True

    def to_dict(self) -> dict[str, object]:
        self.verify()
        return {**self._material(), "receipt_digest": self.digest}


class ClaudeGlobalActivation:
    def plan(
        self,
        config: ClaudeSyntheticActivationConfig,
        transaction: TransactionProposal,
        request: ClaudeGlobalProjectionRequest,
    ) -> ClaudeSyntheticActivationPlan:
        _validate_plan_inputs(config, transaction, request)
        expected_final_head = _next_head("GENESIS", transaction.digest())
        provisional = ClaudeSyntheticActivationPlan(
            config=config,
            transaction=transaction,
            request=request,
            expected_final_head=expected_final_head,
            plan_digest="",
        )
        digest = sha256_domain(_PLAN_DOMAIN, canonical_json_bytes(provisional._material()))
        selected = ClaudeSyntheticActivationPlan(
            config=config,
            transaction=transaction,
            request=request,
            expected_final_head=expected_final_head,
            plan_digest=digest,
        )
        selected.verify()
        return selected

    def apply_synthetic(
        self,
        plan: ClaudeSyntheticActivationPlan,
        authorization: LocalManualWriteAuthorization,
    ) -> ClaudeSyntheticActivationReceipt:
        if not isinstance(plan, ClaudeSyntheticActivationPlan):
            raise ClaudeContractError("synthetic activation plan type is invalid")
        plan.verify()
        _validate_authorization(plan, authorization)
        root = plan.config.sandbox_root
        if root.exists():
            raise ClaudeContractError("synthetic sandbox root already exists")

        root.mkdir()
        plan.config.projection_target.parent.mkdir(parents=True)
        plan.config.user_memory_target.parent.mkdir(parents=True)
        plan.config.user_memory_target.write_bytes(_SYNTHETIC_USER_MEMORY)

        store = MemoryStore(plan.config.store_root)
        commit_receipt = store.commit(plan.transaction)
        if commit_receipt.new_head != plan.expected_final_head:
            raise ClaudeContractError("canonical commit head differs from activation plan")
        context = VerifiedClaudeWriteContext.bind(
            store,
            plan.transaction,
            commit_receipt,
            authorization,
        )

        route = _global_route()
        result = ClaudeGlobalMemoryAdapter(store, route).materialize(plan.request)
        publisher = ClaudeProjectionPublisher(plan.config.runtime_root)
        publication_plan = publisher.plan(
            result,
            plan.config.projection_target,
            None,
        )
        publication = publisher.publish(publication_plan, context)
        projection_receipt = publication.receipt

        managed_import = ClaudeManagedImport(
            plan.config.runtime_root,
            plan.config.user_memory_root,
            result.manifest,
        )
        import_plan = managed_import.plan(
            plan.config.user_memory_target,
            plan.config.projection_target,
            _sha256_bytes(_SYNTHETIC_USER_MEMORY),
        )
        import_receipt = managed_import.apply(import_plan, context, publication)

        receipt_material = {
            "activation_id": "activation:" + plan.plan_digest,
            "plan_digest": plan.plan_digest,
            "steps": [
                "canonical_commit",
                "projection_publish",
                "managed_import",
            ],
            "commit_receipt": commit_receipt.to_dict(),
            "projection_receipt": projection_receipt.to_dict(),
            "import_receipt": import_receipt.to_dict(),
            "final_head": commit_receipt.new_head,
            "production_wave_run": "NOT_APPLICABLE",
            "claude_memory_readback": "NOT_RUN",
            "real_claude_user_memory": "NOT_TOUCHED",
            "private_residence": "NOT_READ",
            "status": "PASS",
        }
        receipt_digest = sha256_domain(
            _RECEIPT_DOMAIN,
            canonical_json_bytes(
                {
                    "activation_receipt_version": "mneme.claude-synthetic-activation-receipt/0.1",
                    **receipt_material,
                }
            ),
        )
        receipt = ClaudeSyntheticActivationReceipt(
            activation_id=str(receipt_material["activation_id"]),
            plan_digest=plan.plan_digest,
            steps=tuple(receipt_material["steps"]),
            commit_receipt=commit_receipt,
            projection_receipt=projection_receipt,
            import_receipt=import_receipt,
            final_head=commit_receipt.new_head,
            production_wave_run="NOT_APPLICABLE",
            claude_memory_readback="NOT_RUN",
            real_claude_user_memory="NOT_TOUCHED",
            private_residence="NOT_READ",
            digest=receipt_digest,
        )
        receipt.verify()
        return receipt


def _validate_plan_inputs(
    config: ClaudeSyntheticActivationConfig,
    transaction: TransactionProposal,
    request: ClaudeGlobalProjectionRequest,
) -> None:
    if not isinstance(config, ClaudeSyntheticActivationConfig):
        raise ClaudeContractError("synthetic activation config type is invalid")
    if not isinstance(transaction, TransactionProposal):
        raise ClaudeContractError("activation transaction type is invalid")
    if not isinstance(request, ClaudeGlobalProjectionRequest):
        raise ClaudeContractError("activation request type is invalid")
    config.verify()
    transaction.validate_for_head("GENESIS")
    request.verify()

    raw = transaction.to_dict()
    record_ids: list[str] = []
    for record in raw["records"]:
        scope = record["scope"]
        scope_path = f"{scope['kind']}/{scope['subject']}"
        if scope_path not in CLAUDE_GLOBAL_SCOPE_PATHS:
            raise ClaudeContractError("activation transaction must use exact global scopes")
        if record["record_type"] not in _ALLOWED_RECORD_TYPES:
            raise ClaudeContractError("activation transaction record type is not allowed")
        if record["status"] != "active":
            raise ClaudeContractError("activation transaction records must be active")
        record_ids.append(str(record["record_id"]))
    if len(record_ids) != len(set(record_ids)):
        raise ClaudeContractError("activation transaction has duplicate record_id")
    if not set(request.required_record_ids).issubset(record_ids):
        raise ClaudeContractError("activation required record is absent from transaction")
    expected_final_head = _next_head("GENESIS", transaction.digest())
    if request.expected_source_head != expected_final_head:
        raise ClaudeContractError("activation request source head mismatch")


def _validate_authorization(
    plan: ClaudeSyntheticActivationPlan,
    authorization: LocalManualWriteAuthorization,
) -> None:
    if not isinstance(authorization, LocalManualWriteAuthorization):
        raise ManualAuthorityError("local manual authorization type is invalid")
    authorization.verify()
    if not authorization.is_active:
        raise ManualAuthorityError("local manual authorization is not active")
    if authorization.transaction_ref != plan.transaction_ref:
        raise ManualAuthorityError("authorization transaction ref mismatch")
    if authorization.transaction_digest != plan.transaction_digest:
        raise ManualAuthorityError("authorization transaction digest mismatch")
    if authorization.expected_source_head != "GENESIS":
        raise ManualAuthorityError("authorization expected source head mismatch")
    allowed = set(authorization.allowed_scope_paths)
    if not set(plan.request.allowed_scope_paths).issubset(allowed):
        raise ManualAuthorityError("authorization scopes do not cover request")
    transaction_scopes = {
        f"{record['scope']['kind']}/{record['scope']['subject']}"
        for record in plan.transaction.to_dict()["records"]
    }
    if not transaction_scopes.issubset(allowed):
        raise ManualAuthorityError("authorization does not cover transaction scopes")
    if plan.transaction.to_dict()["authority_ref"] != authorization.authorization_id:
        raise ManualAuthorityError("transaction authority ref mismatch")


def _global_route() -> Route:
    return Route.from_dict(
        {
            "route_version": "mneme.route/0.1",
            "route_id": "route://global/tier0",
            "scope_prefixes": ["global"],
            "record_types": ["instruction", "fact", "lesson"],
        }
    )
