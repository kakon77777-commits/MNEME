from __future__ import annotations

import json
import subprocess
from pathlib import Path

from mneme.canonical import canonical_json_bytes, sha256_domain

ROOT = Path(__file__).parents[1]
INPUT_PINS = ROOT / "docs" / "evidence" / "2026-08-29-mneme-v0.5-input-pins.json"
ACCEPTANCE = ROOT / "docs" / "evidence" / "2026-08-29-mneme-v0.5-acceptance.json"
WORKFLOW = ROOT / ".github" / "workflows" / "mneme-unified-profile-integration.yml"
ACCEPTANCE_DOMAIN = b"MNEME-UNIFIED-INTEGRATION-ACCEPTANCE-0.1"
EXPECTED_PINS = {
    "schema": "mneme.unified-integration-input-pins/0.1",
    "remote_main": {
        "commit": "c21546a263920e0f80701696e1857c203917d701",
        "tree": "5ad5725ca685df334110b257e4004d9274e35674",
    },
    "claude_candidate": {
        "commit": "89bb1509f2bb96c4067d12c15094adacc2512b67",
        "tree": "0fcac15cbccdde61013b8dfa6938ed19ca161ef8",
        "acceptance_sha256": (
            "50E7C5E999DE8BEAF80FF7B45856750CD9B398E28FC01F2BE279BB4185EADCCF"
        ),
    },
}


def _git(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout.strip()


def test_input_pins_bind_exact_git_commit_trees():
    observed = json.loads(INPUT_PINS.read_text(encoding="utf-8"))

    assert observed == EXPECTED_PINS
    for label in ("remote_main", "claude_candidate"):
        pin = observed[label]
        assert _git("cat-file", "-t", pin["commit"]) == "commit"
        assert _git("rev-parse", f"{pin['commit']}^{{tree}}") == pin["tree"]


def test_combined_ci_fetches_history_required_by_git_object_pins():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "fetch-depth: 0" in text


def test_final_acceptance_is_digest_bound_and_preserves_nonclaims():
    payload = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
    observed_digest = payload.pop("evidence_digest")

    assert observed_digest == sha256_domain(
        ACCEPTANCE_DOMAIN,
        canonical_json_bytes(payload),
    )
    assert payload["candidate"]["verified_head"] == (
        "d9a1e008a50a23ddeaf247a78c3e520ef44dcba7"
    )
    assert payload["candidate"]["verified_tree"] == (
        "76c090c655a670b692140758fd2587b32c3ffc7a"
    )
    assert payload["tests"]["full"] == {
        "passed": 348,
        "skipped": 1,
        "failed": 0,
    }
    assert all(
        report["status"] == "PASS"
        for report in payload["acceptance_surfaces"].values()
    )
    assert payload["dry_run_boundaries"]["canonical_store_mutated"] is False
    assert payload["dry_run_boundaries"]["destructive_actions_performed"] is False
    assert payload["claude_boundaries"]["effect_observation_scope"] == (
        "cpython_audited_api_surface"
    )
    assert payload["claude_boundaries"]["effect_observation_not_claimed"] == [
        "native_ffi_containment",
        "os_level_sandbox",
    ]
    assert set(payload["claude_boundaries"]["local_activation_cases"].values()) == {
        "NOT_RUN_LOCAL_ACTIVATION_REQUIRED"
    }
    for field, value in payload["claude_boundaries"]["effects"].items():
        assert value == 0, field
    encoded = canonical_json_bytes(payload).decode("utf-8")
    for forbidden in ("C:\\\\Users\\\\", "D:\\\\", "AI_RESIDENCE", "USERPROFILE", "sk-"):
        assert forbidden not in encoded
