from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from mneme.canonical import canonical_json_bytes, sha256_domain
from mneme.claude_activation import (
    _RECEIPT_DOMAIN,
    ClaudeGlobalActivation,
    ClaudeSyntheticActivationConfig,
    ClaudeSyntheticActivationReceipt,
)
from mneme.claude_contracts import (
    CLAUDE_GLOBAL_NONCLAIMS,
    ClaudeGlobalProjectionRequest,
    ClaudeImportReceipt,
    LocalManualWriteAuthorization,
)
from mneme.errors import ClaudeContractError, ManualAuthorityError
from mneme.records import MemoryRecord
from mneme.store import MemoryStore, _next_head
from mneme.transactions import TransactionProposal


def raw_record(
    record_id: str = "record:synthetic:activation",
    *,
    scope: str = "global/core",
    text: str = "Synthetic provider-neutral activation memory.",
) -> dict[str, object]:
    kind, _, subject = scope.partition("/")
    return {
        "record_version": "mneme.memory-record/0.1",
        "record_id": record_id,
        "record_type": "instruction",
        "scope": {"kind": kind, "subject": subject},
        "content": {"text": text},
        "relations": [],
        "provenance": {
            "event_id": "event:synthetic:activation",
            "source_ref": "synthetic:activation-test",
        },
        "status": "active",
    }


def transaction(*, record: dict[str, object] | None = None) -> TransactionProposal:
    selected = record or raw_record()
    return transaction_from_records([selected])


def transaction_from_records(records: list[dict[str, object]]) -> TransactionProposal:
    return TransactionProposal.from_dict(
        {
            "transaction_version": "mneme.transaction/0.1",
            "transaction_id": "transaction:synthetic:activation",
            "expected_source_head": "GENESIS",
            "declared_record_count": len(records),
            "record_digests": [MemoryRecord.from_dict(record).digest() for record in records],
            "records": records,
            "authority_ref": "authorization:synthetic:activation",
            "commit_marker": "MNEME_COMMIT/0.1",
        }
    )


def request(tx: TransactionProposal) -> ClaudeGlobalProjectionRequest:
    expected_head = _next_head("GENESIS", tx.digest())
    return ClaudeGlobalProjectionRequest.sealed(
        {
            "request_version": "mneme.claude-global-projection-request/0.1",
            "request_id": "request:synthetic:activation",
            "expected_source_head": expected_head,
            "route_id": "route://global/tier0",
            "allowed_scope_paths": ["global/core"],
            "required_record_ids": ["record:synthetic:activation"],
            "byte_budget": 16000,
            "target_kind": "claude_code_user_memory_import",
            "projection_ref": "projection:synthetic:activation",
            "not_claimed": list(CLAUDE_GLOBAL_NONCLAIMS),
        }
    )


def authorization(
    tx: TransactionProposal,
    *,
    transaction_ref: str | None = None,
    transaction_digest: str | None = None,
) -> LocalManualWriteAuthorization:
    return LocalManualWriteAuthorization.sealed(
        {
            "authorization_version": "mneme.local-manual-write-authorization/0.1",
            "authorization_id": "authorization:synthetic:activation",
            "principal_ref": "principal:neo.k",
            "transaction_ref": transaction_ref or tx.to_dict()["transaction_id"],
            "transaction_digest": transaction_digest or tx.digest(),
            "expected_source_head": "GENESIS",
            "allowed_scope_paths": ["global/core"],
            "status": "active",
            "source_role": "user",
            "source_user_item_ref": "user-item:synthetic:activation",
            "source_user_item_digest": "e" * 64,
            "not_claimed": list(CLAUDE_GLOBAL_NONCLAIMS),
        }
    )


def forged_role_authorization(
    tx: TransactionProposal,
    source_role: str,
) -> LocalManualWriteAuthorization:
    raw = authorization(tx).to_dict()
    raw["source_role"] = source_role
    return LocalManualWriteAuthorization(canonical_json_bytes(raw))


def prepared_activation(tmp_path: Path):
    root = tmp_path / "mneme-synthetic-activation"
    config = ClaudeSyntheticActivationConfig(root)
    tx = transaction()
    selected_request = request(tx)
    activation = ClaudeGlobalActivation()
    plan = activation.plan(config, tx, selected_request)
    return activation, plan, tx, root


def test_plan_is_read_only_and_binds_fresh_transaction_request(tmp_path):
    activation, plan, tx, root = prepared_activation(tmp_path)

    assert not root.exists()
    assert plan.verify() is True
    assert plan.transaction_digest == tx.digest()
    assert plan.request_digest == request(tx).digest
    assert plan.expected_final_head == _next_head("GENESIS", tx.digest())
    assert plan.config.sandbox_root == root
    assert activation.plan(plan.config, tx, request(tx)) == plan


@pytest.mark.parametrize("source_role", ["assistant", "relay"])
def test_model_or_relay_cannot_authorize_activation(tmp_path, source_role):
    activation, plan, tx, root = prepared_activation(tmp_path)

    with pytest.raises(ManualAuthorityError):
        activation.apply_synthetic(
            plan,
            forged_role_authorization(tx, source_role),
        )

    assert not root.exists()


@pytest.mark.parametrize(
    "changed_authorization",
    [
        {"transaction_ref": "transaction:other"},
        {"transaction_digest": "f" * 64},
    ],
)
def test_authorization_must_bind_exact_transaction_before_first_write(
    tmp_path,
    changed_authorization,
):
    activation, plan, tx, root = prepared_activation(tmp_path)
    approved = authorization(tx, **changed_authorization)

    with pytest.raises(ManualAuthorityError, match="transaction"):
        activation.apply_synthetic(plan, approved)

    assert not root.exists()


def test_authorization_must_cover_every_transaction_scope(tmp_path):
    root = tmp_path / "mneme-synthetic-activation"
    tx = transaction_from_records(
        [
            raw_record(),
            raw_record(
                "record:synthetic:machine",
                scope="global/machine",
                text="Synthetic machine-level memory.",
            ),
        ]
    )
    selected_request = request(tx)
    activation = ClaudeGlobalActivation()
    plan = activation.plan(
        ClaudeSyntheticActivationConfig(root),
        tx,
        selected_request,
    )

    with pytest.raises(ManualAuthorityError, match="transaction scopes"):
        activation.apply_synthetic(plan, authorization(tx))

    assert not root.exists()


def test_duplicate_record_ids_refuse_during_read_only_plan(tmp_path):
    root = tmp_path / "mneme-synthetic-activation"
    tx = transaction_from_records(
        [
            raw_record(),
            raw_record(text="Same ID, different synthetic body."),
        ]
    )

    with pytest.raises(ClaudeContractError, match="duplicate record_id"):
        ClaudeGlobalActivation().plan(
            ClaudeSyntheticActivationConfig(root),
            tx,
            request(tx),
        )

    assert not root.exists()


def test_non_global_transaction_is_refused_during_read_only_plan(tmp_path):
    root = tmp_path / "mneme-synthetic-activation"
    tx = transaction(record=raw_record(scope="identity/synthetic"))
    selected_request = request(tx)

    with pytest.raises(ClaudeContractError, match="global"):
        ClaudeGlobalActivation().plan(
            ClaudeSyntheticActivationConfig(root),
            tx,
            selected_request,
        )

    assert not root.exists()


def test_tampered_activation_plan_refuses_before_first_write(tmp_path):
    activation, plan, tx, root = prepared_activation(tmp_path)
    tampered = replace(plan, plan_digest="0" * 64)

    with pytest.raises(ClaudeContractError, match="plan digest"):
        activation.apply_synthetic(tampered, authorization(tx))

    assert not root.exists()


def test_activation_order_binds_store_projection_and_import_receipts(tmp_path):
    activation, plan, tx, _ = prepared_activation(tmp_path)

    receipt = activation.apply_synthetic(plan, authorization(tx))

    assert isinstance(receipt, ClaudeSyntheticActivationReceipt)
    assert receipt.verify() is True
    assert receipt.steps == (
        "canonical_commit",
        "projection_publish",
        "managed_import",
    )
    assert receipt.production_wave_run == "NOT_APPLICABLE"
    assert receipt.claude_memory_readback == "NOT_RUN"
    assert receipt.real_claude_user_memory == "NOT_TOUCHED"
    assert receipt.private_residence == "NOT_READ"
    assert receipt.plan_digest == plan.plan_digest
    assert receipt.commit_receipt.new_head == plan.expected_final_head
    assert receipt.projection_receipt.authorization_digest == authorization(tx).digest
    assert receipt.import_receipt.authorization_digest == authorization(tx).digest
    assert receipt.import_receipt.projection_digest == receipt.projection_receipt.projection_digest

    store = MemoryStore(plan.config.store_root)
    assert store.head() == receipt.final_head
    assert len(list(store.iter_committed_transactions())) == 1
    assert plan.config.projection_target.read_bytes().startswith(b"# MNEME Projection")
    user_bytes = plan.config.user_memory_target.read_bytes()
    assert b"<!-- BEGIN MNEME GLOBAL PROJECTION v0.1 -->" in user_bytes
    assert str(plan.config.projection_target).encode("utf-8") in user_bytes


def test_activation_receipt_contains_no_memory_body(tmp_path):
    activation, plan, tx, _ = prepared_activation(tmp_path)
    receipt = activation.apply_synthetic(plan, authorization(tx))
    evidence = json.dumps(receipt.to_dict(), ensure_ascii=False, sort_keys=True)

    assert "Synthetic provider-neutral activation memory" not in evidence
    assert "Synthetic Claude user memory" not in evidence
    assert receipt.digest in evidence


def test_activation_receipt_rejects_valid_but_cross_binding_swapped_receipt(tmp_path):
    activation, plan, tx, _ = prepared_activation(tmp_path)
    receipt = activation.apply_synthetic(plan, authorization(tx))
    changed_import = receipt.import_receipt.to_dict()
    changed_import["authorization_digest"] = "f" * 64
    swapped_import = ClaudeImportReceipt.sealed(changed_import)
    provisional = replace(receipt, import_receipt=swapped_import, digest="")
    forged_digest = sha256_domain(
        _RECEIPT_DOMAIN,
        canonical_json_bytes(provisional._material()),
    )
    forged = replace(provisional, digest=forged_digest)

    with pytest.raises(ClaudeContractError, match="authorization binding"):
        forged.verify()


def test_existing_sandbox_root_refuses_without_mutation(tmp_path):
    activation, plan, tx, root = prepared_activation(tmp_path)
    root.mkdir()
    sentinel = root / "sentinel.txt"
    sentinel.write_bytes(b"keep")

    with pytest.raises(ClaudeContractError, match="already exists"):
        activation.apply_synthetic(plan, authorization(tx))

    assert sentinel.read_bytes() == b"keep"
