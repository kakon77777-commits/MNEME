from __future__ import annotations

import hashlib
from copy import deepcopy

import pytest

from mneme.claude_contracts import (
    ClaudeGlobalProjectionManifest,
    ClaudeGlobalProjectionRequest,
    ClaudeImportPlan,
    ClaudeImportReceipt,
    ClaudePublicationPlan,
    ClaudePublicationReceipt,
    LocalManualWriteAuthorization,
)
from mneme.errors import ClaudeContractError, ManualAuthorityError

NONCLAIMS = [
    "resident_identity",
    "private_memory_access",
    "provider_continuity",
    "autonomous_write_authority",
    "cognitive_reconstruction",
    "claude_memory_readback",
]
SOURCE_HEAD = "a" * 64
CONTENT = b"# MNEME Global Memory\n\nSynthetic content.\n"
CONTENT_SHA256 = hashlib.sha256(CONTENT).hexdigest()


def request_material(**changes):
    value = {
        "request_version": "mneme.claude-global-projection-request/0.1",
        "request_id": "request:synthetic:one",
        "expected_source_head": SOURCE_HEAD,
        "route_id": "route://global/tier0",
        "allowed_scope_paths": [
            "global/core",
            "global/collaboration",
            "global/verification",
            "global/machine",
        ],
        "required_record_ids": ["record-core"],
        "byte_budget": 16000,
        "target_kind": "claude_code_user_memory_import",
        "projection_ref": "projection:synthetic:one",
        "not_claimed": NONCLAIMS,
    }
    value.update(changes)
    return value


def authorization_material(**changes):
    value = {
        "authorization_version": "mneme.local-manual-write-authorization/0.1",
        "authorization_id": "authorization:synthetic:one",
        "principal_ref": "principal:neo.k",
        "transaction_ref": "transaction:synthetic:one",
        "transaction_digest": "b" * 64,
        "expected_source_head": SOURCE_HEAD,
        "allowed_scope_paths": ["global/core"],
        "status": "active",
        "source_role": "user",
        "source_user_item_ref": "user-item:synthetic:one",
        "source_user_item_digest": "c" * 64,
        "not_claimed": NONCLAIMS,
    }
    value.update(changes)
    return value


def manifest_material(request, **changes):
    value = {
        "manifest_version": "mneme.claude-global-projection-manifest/0.1",
        "projection_ref": request.projection_ref,
        "request_ref": request.request_id,
        "request_digest": request.digest,
        "source_head": SOURCE_HEAD,
        "route_id": "route://global/tier0",
        "byte_budget": 16000,
        "content_bytes": len(CONTENT),
        "content_sha256": CONTENT_SHA256,
        "included_record_ids": ["record-core"],
        "omitted": [{"record_id": "record-optional", "reason": "budget_exceeded"}],
        "required_record_ids": ["record-core"],
        "generator_version": "mneme.claude-projection/0.1",
        "not_claimed": NONCLAIMS,
    }
    value.update(changes)
    return value


def publication_plan_material(manifest, **changes):
    value = {
        "publication_plan_version": "mneme.claude-publication-plan/0.1",
        "plan_id": "publication-plan:synthetic:one",
        "projection_ref": manifest.projection_ref,
        "projection_digest": manifest.digest,
        "content_bytes": manifest.content_bytes,
        "content_sha256": manifest.content_sha256,
        "target_ref": "file-ref:synthetic:MNEME_GLOBAL.md",
        "target_preimage_sha256": None,
        "not_claimed": NONCLAIMS,
    }
    value.update(changes)
    return value


def publication_receipt_material(plan, authorization, **changes):
    value = {
        "publication_receipt_version": "mneme.claude-publication-receipt/0.1",
        "receipt_id": "publication-receipt:synthetic:one",
        "publication_plan_ref": plan.plan_id,
        "publication_plan_digest": plan.digest,
        "authorization_ref": authorization.authorization_id,
        "authorization_digest": authorization.digest,
        "projection_ref": plan.projection_ref,
        "projection_digest": plan.projection_digest,
        "target_ref": plan.target_ref,
        "target_before_sha256": plan.target_preimage_sha256,
        "target_after_sha256": plan.content_sha256,
        "readback_sha256": plan.content_sha256,
        "content_bytes": plan.content_bytes,
        "outcome": "published",
        "not_claimed": NONCLAIMS,
    }
    value.update(changes)
    return value


def import_plan_material(manifest, **changes):
    value = {
        "import_plan_version": "mneme.claude-import-plan/0.1",
        "plan_id": "import-plan:synthetic:one",
        "projection_ref": manifest.projection_ref,
        "projection_digest": manifest.digest,
        "projection_path_ref": "file-ref:synthetic:MNEME_GLOBAL.md",
        "projection_content_sha256": manifest.content_sha256,
        "projection_content_bytes": manifest.content_bytes,
        "user_memory_ref": "file-ref:synthetic:CLAUDE.md",
        "user_memory_preimage_sha256": "d" * 64,
        "managed_block_version": "MNEME_GLOBAL_PROJECTION/0.1",
        "not_claimed": NONCLAIMS,
    }
    value.update(changes)
    return value


def import_receipt_material(plan, authorization, **changes):
    value = {
        "import_receipt_version": "mneme.claude-import-receipt/0.1",
        "receipt_id": "import-receipt:synthetic:one",
        "import_plan_ref": plan.plan_id,
        "import_plan_digest": plan.digest,
        "authorization_ref": authorization.authorization_id,
        "authorization_digest": authorization.digest,
        "projection_ref": plan.projection_ref,
        "projection_digest": plan.projection_digest,
        "user_memory_ref": plan.user_memory_ref,
        "user_memory_before_sha256": plan.user_memory_preimage_sha256,
        "user_memory_after_sha256": "e" * 64,
        "readback_sha256": "e" * 64,
        "managed_block_sha256": "f" * 64,
        "outside_bytes_preserved": True,
        "outcome": "inserted",
        "claude_memory_readback": "NOT_RUN",
        "not_claimed": NONCLAIMS,
    }
    value.update(changes)
    return value


def _valid_contracts():
    request = ClaudeGlobalProjectionRequest.sealed(request_material())
    manifest = ClaudeGlobalProjectionManifest.sealed(manifest_material(request))
    authorization = LocalManualWriteAuthorization.sealed(authorization_material())
    publication_plan = ClaudePublicationPlan.sealed(
        publication_plan_material(manifest)
    )
    publication_receipt = ClaudePublicationReceipt.sealed(
        publication_receipt_material(publication_plan, authorization)
    )
    import_plan = ClaudeImportPlan.sealed(import_plan_material(manifest))
    import_receipt = ClaudeImportReceipt.sealed(
        import_receipt_material(import_plan, authorization)
    )
    return (
        request,
        manifest,
        publication_plan,
        publication_receipt,
        import_plan,
        import_receipt,
        authorization,
    )


def test_request_is_global_only_and_has_exact_hard_budget():
    valid = ClaudeGlobalProjectionRequest.sealed(request_material())
    assert valid.byte_budget == 16000
    assert valid.allowed_scope_paths == (
        "global/core",
        "global/collaboration",
        "global/verification",
        "global/machine",
    )
    assert ClaudeGlobalProjectionRequest.sealed(
        request_material(byte_budget=8000)
    ).byte_budget == 8000

    for changed in (
        {"byte_budget": 16001},
        {"allowed_scope_paths": ["identity/example"]},
        {"route_id": "route://identity/example/bootstrap"},
        {"required_record_ids": ["same", "same"]},
    ):
        with pytest.raises(ClaudeContractError):
            ClaudeGlobalProjectionRequest.sealed(request_material(**changed))


def test_every_contract_is_canonical_digest_bound_and_round_trips():
    for contract in _valid_contracts():
        cls = type(contract)
        assert contract.verify() is True
        assert cls.from_dict(contract.to_dict()) == contract
        assert len(contract.digest) == 64
        assert contract.to_dict()[cls.digest_field] == contract.digest

        tampered = contract.to_dict()
        field = next(
            name
            for name in tampered
            if name not in {cls.digest_field, "not_claimed"}
            and isinstance(tampered[name], str)
            and not name.endswith("version")
        )
        tampered[field] = str(tampered[field]) + ":tampered"
        with pytest.raises(ClaudeContractError):
            cls.from_dict(tampered)


def test_contracts_are_closed_and_require_exact_nonclaims():
    request = ClaudeGlobalProjectionRequest.sealed(request_material())
    raw = request.to_dict()
    raw["unexpected"] = True
    with pytest.raises(ClaudeContractError):
        ClaudeGlobalProjectionRequest.from_dict(raw)

    for nonclaims in (NONCLAIMS[:-1], list(reversed(NONCLAIMS))):
        with pytest.raises(ClaudeContractError):
            ClaudeGlobalProjectionRequest.sealed(
                request_material(not_claimed=nonclaims)
            )


def test_manifest_requires_whole_consistent_record_population():
    request = ClaudeGlobalProjectionRequest.sealed(request_material())
    valid = ClaudeGlobalProjectionManifest.sealed(manifest_material(request))
    assert valid.included_record_ids == ("record-core",)
    assert valid.required_record_ids == ("record-core",)
    assert valid.omitted == (
        {"record_id": "record-optional", "reason": "budget_exceeded"},
    )

    invalid_changes = (
        {"content_bytes": 16001},
        {"required_record_ids": ["record-missing"]},
        {
            "omitted": [
                {"record_id": "record-core", "reason": "scope_not_allowed"}
            ]
        },
        {
            "omitted": [
                {"record_id": "record-optional", "reason": "budget_exceeded"},
                {"record_id": "record-optional", "reason": "status_not_active"},
            ]
        },
    )
    for changed in invalid_changes:
        with pytest.raises(ClaudeContractError):
            ClaudeGlobalProjectionManifest.sealed(
                manifest_material(request, **changed)
            )


def test_ref_digest_pairs_and_receipt_readback_are_atomic():
    (
        _,
        manifest,
        publication_plan,
        publication_receipt,
        import_plan,
        import_receipt,
        authorization,
    ) = _valid_contracts()
    assert publication_receipt.readback_sha256 == publication_plan.content_sha256
    assert import_receipt.readback_sha256 == import_receipt.user_memory_after_sha256

    for cls, material, missing in (
        (
            ClaudePublicationPlan,
            publication_plan_material(manifest),
            "projection_digest",
        ),
        (
            ClaudePublicationReceipt,
            publication_receipt_material(publication_plan, authorization),
            "authorization_digest",
        ),
        (
            ClaudeImportReceipt,
            import_receipt_material(import_plan, authorization),
            "import_plan_digest",
        ),
    ):
        del material[missing]
        with pytest.raises(ClaudeContractError):
            cls.sealed(material)

    with pytest.raises(ClaudeContractError):
        ClaudePublicationReceipt.sealed(
            publication_receipt_material(
                publication_plan,
                authorization,
                readback_sha256="0" * 64,
            )
        )
    with pytest.raises(ClaudeContractError):
        ClaudeImportReceipt.sealed(
            import_receipt_material(
                import_plan,
                authorization,
                readback_sha256="0" * 64,
            )
        )
    with pytest.raises(ClaudeContractError):
        ClaudeImportReceipt.sealed(
            import_receipt_material(
                import_plan,
                authorization,
                claude_memory_readback="observed",
            )
        )


def test_manual_authority_is_human_exact_and_status_is_explicit():
    active = LocalManualWriteAuthorization.sealed(authorization_material())
    assert active.principal_ref == "principal:neo.k"
    assert active.status == "active"
    assert active.is_active is True

    for status in ("revoked", "expired", "suspended"):
        inactive = LocalManualWriteAuthorization.sealed(
            authorization_material(status=status)
        )
        assert inactive.is_active is False

    for changed in (
        {"principal_ref": "model:claude"},
        {"source_role": "assistant"},
        {"source_role": "relay"},
        {"allowed_scope_paths": ["identity/example"]},
    ):
        with pytest.raises(ManualAuthorityError):
            LocalManualWriteAuthorization.sealed(
                authorization_material(**changed)
            )


def test_to_dict_returns_detached_material():
    request = ClaudeGlobalProjectionRequest.sealed(request_material())
    detached = request.to_dict()
    detached["allowed_scope_paths"].append("identity/tamper")
    detached["not_claimed"].clear()
    assert request.verify() is True
    assert "identity/tamper" not in request.allowed_scope_paths
    assert request.to_dict()["not_claimed"] == NONCLAIMS


def test_same_material_seals_to_same_bytes_and_digest():
    first_material = request_material()
    second_material = deepcopy(first_material)
    second_material["allowed_scope_paths"] = list(
        reversed(second_material["allowed_scope_paths"])
    )
    first = ClaudeGlobalProjectionRequest.sealed(first_material)
    same = ClaudeGlobalProjectionRequest.sealed(deepcopy(first_material))
    reordered = ClaudeGlobalProjectionRequest.sealed(second_material)

    assert first == same
    assert first.digest == same.digest
    assert first.digest != reordered.digest
