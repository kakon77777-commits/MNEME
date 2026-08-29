from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

from mneme.canonical import canonical_json_bytes, sha256_domain

ROOT = Path(__file__).parents[1]
INPUT_PINS = ROOT / "docs" / "evidence" / "2026-08-29-mneme-v0.5-input-pins.json"
ACCEPTANCE = ROOT / "docs" / "evidence" / "2026-08-29-mneme-v0.5-acceptance.json"
WORKFLOW = ROOT / ".github" / "workflows" / "mneme-unified-profile-integration.yml"
PINNED_HISTORY_WORKFLOWS = (
    WORKFLOW,
    ROOT / ".github" / "workflows" / "fresh-memory-core.yml",
    ROOT / ".github" / "workflows" / "memory-markdown-profile.yml",
    ROOT / ".github" / "workflows" / "cognitive-persistence-semantics.yml",
    ROOT / ".github" / "workflows" / "private-residence-two-pass-dry-run.yml",
)
ACCEPTANCE_DOMAIN = b"MNEME-UNIFIED-INTEGRATION-ACCEPTANCE-0.1"
CLAUDE_SEMANTIC_DOMAIN = b"MNEME-CLAUDE-GLOBAL-SEMANTIC-REPORT-0.1"
DRY_RUN_SEMANTIC_DOMAIN = (
    b"MNEME-PRIVATE-RESIDENCE-DRY-RUN-SEMANTIC-REPORT-0.2"
)
CLAUDE_ROOT_SENSITIVE_FIELDS = (
    "artifact_runs[].activation_receipt_digest",
    "artifact_runs[].import_receipt_digest",
    "artifact_runs[].projection_receipt_digest",
    "run_fingerprints[]",
    "report_digest",
)
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


def _run_validation(
    checkout: Path,
    script: str,
    arguments: list[str],
) -> None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-B", script, *arguments],
        cwd=checkout,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _clone_pinned_candidate(
    source_repository: Path,
    destination: Path,
    selected_head: str,
) -> None:
    cloned = subprocess.run(
        [
            "git",
            "clone",
            "--no-local",
            "--no-checkout",
            str(source_repository),
            str(destination),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert cloned.returncode == 0, cloned.stdout + cloned.stderr
    checked_out = subprocess.run(
        ["git", "checkout", "--detach", selected_head],
        cwd=destination,
        text=True,
        capture_output=True,
        check=False,
    )
    assert checked_out.returncode == 0, checked_out.stdout + checked_out.stderr


def _normalized_claude_report(payload: dict[str, object]) -> dict[str, object]:
    normalized = deepcopy(payload)
    for run in normalized["artifact_runs"]:
        run["activation_receipt_digest"] = "<synthetic-root-sensitive>"
        run["import_receipt_digest"] = "<synthetic-root-sensitive>"
        run["projection_receipt_digest"] = "<synthetic-root-sensitive>"
    normalized["run_fingerprints"] = [
        "<synthetic-root-sensitive>"
        for _ in normalized["run_fingerprints"]
    ]
    normalized["report_digest"] = "<synthetic-root-sensitive>"
    return normalized


def _normalized_dry_run_report(payload: dict[str, object]) -> dict[str, object]:
    normalized = deepcopy(payload)
    normalized["bundle_fingerprint"] = "<checkout-root-sensitive>"
    return normalized


def test_input_pins_bind_exact_git_commit_trees():
    observed = json.loads(INPUT_PINS.read_text(encoding="utf-8"))

    assert observed == EXPECTED_PINS
    for label in ("remote_main", "claude_candidate"):
        pin = observed[label]
        assert _git("cat-file", "-t", pin["commit"]) == "commit"
        assert _git("rev-parse", f"{pin['commit']}^{{tree}}") == pin["tree"]


def test_combined_ci_fetches_history_required_by_git_object_pins():
    for workflow in PINNED_HISTORY_WORKFLOWS:
        text = workflow.read_text(encoding="utf-8")
        assert "fetch-depth: 0" in text, workflow.name
        assert "name: Fetch pinned evidence history" in text, workflow.name
        assert 'command.append("--unshallow")' in text, workflow.name
        assert "refs/heads/main:refs/heads/evidence-main" in text, workflow.name
        assert (
            "refs/heads/feat/claude-global-memory-transition-v0.1:"
            "refs/heads/evidence-claude-candidate"
        ) in text, workflow.name


def test_final_acceptance_is_digest_bound_and_preserves_nonclaims():
    payload = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
    observed_digest = payload.pop("evidence_digest")

    assert observed_digest == sha256_domain(
        ACCEPTANCE_DOMAIN,
        canonical_json_bytes(payload),
    )
    assert payload["candidate"]["verified_head"] == (
        "a8aa6bc7e320a15191a9061848603f38d254e065"
    )
    assert payload["candidate"]["verified_tree"] == (
        "7a2d387427a3c4f4b03a19fdb86315664c7c1c42"
    )
    assert payload["tests"]["full"] == {
        "passed": 350,
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


def test_six_acceptance_surfaces_reproduce_from_pinned_candidate(tmp_path):
    evidence = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
    claude_evidence = evidence["acceptance_surfaces"]["claude_global_transition"]

    assert claude_evidence["byte_reproducibility"] == (
        "NOT_CLAIMED_SYNTHETIC_ROOT_SENSITIVE"
    )
    assert tuple(claude_evidence["root_sensitive_fields"]) == (
        CLAUDE_ROOT_SENSITIVE_FIELDS
    )
    assert claude_evidence["sha256"] is None

    common_git_dir = Path(
        _git("rev-parse", "--path-format=absolute", "--git-common-dir")
    )
    source_repository = common_git_dir.parent
    selected_head = evidence["candidate"]["verified_head"]
    checkout = tmp_path / "pinned-candidate"
    _clone_pinned_candidate(source_repository, checkout, selected_head)

    deterministic = {
        "fresh_memory_core": "validate_fresh_memory_core.py",
        "memory_markdown_v01": "validate_memory_markdown_profile.py",
        "evemiss_profile_v02": "validate_memory_markdown_profile_v02.py",
        "cognitive_persistence": "validate_cognitive_persistence_semantics.py",
    }
    for key, script_name in deterministic.items():
        output = tmp_path / f"{key}.json"
        _run_validation(
            checkout,
            str(Path("scripts") / script_name),
            ["--output", str(output)],
        )
        expected = evidence["acceptance_surfaces"][key]
        assert output.stat().st_size == expected["bytes"]
        assert hashlib.sha256(output.read_bytes()).hexdigest().upper() == (
            expected["sha256"]
        )

    dry_run_evidence = evidence["acceptance_surfaces"][
        "private_residence_dry_run"
    ]
    assert dry_run_evidence["byte_reproducibility"] == (
        "NOT_CLAIMED_CHECKOUT_ROOT_SENSITIVE"
    )
    assert dry_run_evidence["root_sensitive_fields"] == ["bundle_fingerprint"]
    assert dry_run_evidence["sha256"] is None
    second_checkout = tmp_path / "pinned-candidate-second-root"
    _clone_pinned_candidate(source_repository, second_checkout, selected_head)
    dry_run_reports: list[dict[str, object]] = []
    dry_run_hashes: list[str] = []
    for label, selected_checkout in (("a", checkout), ("b", second_checkout)):
        output = tmp_path / f"dry-run-{label}.json"
        _run_validation(
            selected_checkout,
            str(Path("scripts") / "validate_private_residence_two_pass_dry_run.py"),
            ["--output", str(output)],
        )
        dry_run_reports.append(json.loads(output.read_text(encoding="utf-8")))
        dry_run_hashes.append(hashlib.sha256(output.read_bytes()).hexdigest())
        assert output.stat().st_size == dry_run_evidence["bytes"]

    assert dry_run_hashes[0] != dry_run_hashes[1]
    normalized_dry_run = tuple(
        _normalized_dry_run_report(report) for report in dry_run_reports
    )
    assert normalized_dry_run[0] == normalized_dry_run[1]
    dry_run_semantic_sha256 = sha256_domain(
        DRY_RUN_SEMANTIC_DOMAIN,
        canonical_json_bytes(normalized_dry_run[0]),
    )
    assert dry_run_semantic_sha256 == dry_run_evidence["semantic_sha256"]

    claude_reports: list[dict[str, object]] = []
    claude_hashes: list[str] = []
    for label in ("a", "b"):
        output = tmp_path / f"claude-{label}.json"
        _run_validation(
            checkout,
            str(Path("scripts") / "validate_claude_global_memory.py"),
            [
                "--root",
                str(tmp_path / f"claude-root-{label}"),
                "--output",
                str(output),
            ],
        )
        claude_reports.append(json.loads(output.read_text(encoding="utf-8")))
        claude_hashes.append(hashlib.sha256(output.read_bytes()).hexdigest())
        assert output.stat().st_size == claude_evidence["bytes"]

    assert claude_hashes[0] != claude_hashes[1]
    normalized = tuple(_normalized_claude_report(report) for report in claude_reports)
    assert normalized[0] == normalized[1]
    semantic_sha256 = sha256_domain(
        CLAUDE_SEMANTIC_DOMAIN,
        canonical_json_bytes(normalized[0]),
    )
    assert semantic_sha256 == claude_evidence["semantic_sha256"]
