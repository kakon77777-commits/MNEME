from __future__ import annotations

import hashlib
from importlib.resources import files
from pathlib import Path

EXPECTED_SCHEMA_NAMES = {
    "claude-global-projection-manifest-0.1.schema.json",
    "claude-global-projection-request-0.1.schema.json",
    "claude-import-plan-0.1.schema.json",
    "claude-import-receipt-0.1.schema.json",
    "claude-publication-plan-0.1.schema.json",
    "claude-publication-receipt-0.1.schema.json",
    "cognitive-seed-proposal-0.1.schema.json",
    "equivalence-contract-0.1.schema.json",
    "factorization-intent-0.1.schema.json",
    "factorization-proposal-0.1.schema.json",
    "local-manual-write-authorization-0.1.schema.json",
    "memory-markdown-profile-0.1.schema.json",
    "memory-record-0.1.schema.json",
    "persistence-assessment-0.1.schema.json",
    "persistence-policy-0.1.schema.json",
    "private-residence-dry-run-report-0.2.schema.json",
    "projection-manifest-0.1.schema.json",
    "recomputation-reference-0.1.schema.json",
    "route-0.1.schema.json",
    "seed-intent-0.1.schema.json",
    "transaction-0.1.schema.json",
}

ROOT = Path(__file__).parents[1]


def test_unified_schema_inventory_is_one_package_resource_set():
    from mneme.schemas import schema_names

    observed = {
        item.name
        for item in files("mneme.schemas").iterdir()
        if item.name.endswith(".schema.json")
    }

    assert observed == EXPECTED_SCHEMA_NAMES
    assert set(schema_names()) == EXPECTED_SCHEMA_NAMES
    assert not (ROOT / "schemas").exists()


def test_unified_schema_digest_manifest_pins_every_resource_byte():
    from mneme.schemas import schema_digest_manifest

    pinned = schema_digest_manifest()

    assert set(pinned) == EXPECTED_SCHEMA_NAMES
    for name, expected_sha256 in pinned.items():
        observed_sha256 = hashlib.sha256(
            files("mneme.schemas").joinpath(name).read_bytes()
        ).hexdigest()
        assert observed_sha256 == expected_sha256


def test_all_dry_run_contracts_load_from_the_installed_resource_set():
    from mneme.dry_run.intents import FactorizationIntent, SeedIntent
    from mneme.dry_run.policy import PersistencePolicy
    from mneme.dry_run.report import DryRunReport
    from mneme.schemas import schema_sha256

    assert FactorizationIntent is not None
    assert SeedIntent is not None
    assert PersistencePolicy is not None
    assert DryRunReport is not None
    for name in (
        "factorization-intent-0.1.schema.json",
        "seed-intent-0.1.schema.json",
        "persistence-policy-0.1.schema.json",
        "private-residence-dry-run-report-0.2.schema.json",
    ):
        assert len(schema_sha256(name)) == 64
