from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from mneme import claude_acceptance
from mneme.canonical import canonical_json_bytes
from mneme.claude_acceptance import validate_claude_global_memory

ROOT = Path(__file__).parents[1]
EXPECTED_EFFECTS = ROOT / "tests" / "fixtures" / "claude" / "expected-effects.json"
SCRIPT = ROOT / "scripts" / "validate_claude_global_memory.py"
SYNTHETIC_CASES = {f"CGM-{index:03d}" for index in range(1, 23)} | {
    "CGM-025",
    "CGM-028",
}
LOCAL_CASES = {"CGM-023", "CGM-024", "CGM-026", "CGM-027"}


def test_cgm_acceptance_has_exact_case_ownership(tmp_path):
    report = validate_claude_global_memory(tmp_path / "acceptance")
    assert {case.case_id for case in report.cases} == SYNTHETIC_CASES | LOCAL_CASES
    assert all(
        case.executed and case.passed and case.status == "PASS"
        for case in report.cases
        if case.case_id in SYNTHETIC_CASES
    )
    assert {
        case.case_id: case.status
        for case in report.cases
        if case.case_id in LOCAL_CASES
    } == {
        case_id: "NOT_RUN_LOCAL_ACTIVATION_REQUIRED" for case_id in LOCAL_CASES
    }
    assert report.status == "PASS"


def test_two_runs_are_byte_and_digest_deterministic(tmp_path):
    report = validate_claude_global_memory(tmp_path / "acceptance")
    assert report.deterministic is True
    assert report.run_fingerprints[0] == report.run_fingerprints[1]
    assert report.artifact_runs[0] == report.artifact_runs[1]
    assert report.artifact_runs[0]["store_head"] != "GENESIS"
    assert len(report.artifact_runs[0]["projection_sha256"]) == 64
    assert len(report.artifact_runs[0]["manifest_digest"]) == 64
    assert len(report.artifact_runs[0]["activation_receipt_digest"]) == 64


def test_positive_effects_equal_independent_fixture(tmp_path):
    expected = json.loads(EXPECTED_EFFECTS.read_text(encoding="utf-8"))
    report = validate_claude_global_memory(tmp_path / "acceptance")
    assert report.effects.to_dict() == expected["positive_effects"]
    assert report.expected_effects_ref == expected["fixture_ref"]
    assert report.expected_effects_sha256 == hashlib.sha256(
        EXPECTED_EFFECTS.read_bytes()
    ).hexdigest()


@pytest.mark.parametrize(
    ("injected", "field"),
    [
        ("private_read", "private_reads"),
        ("private_write", "private_writes"),
        ("production_read", "production_reads"),
        ("production_write", "production_writes"),
        ("network", "network_calls"),
        ("provider", "provider_calls"),
        ("mcp", "mcp_calls"),
        ("bridge", "bridge_calls"),
        ("external_cli", "external_cli_calls"),
    ],
)
def test_each_injected_forbidden_effect_turns_acceptance_red(
    tmp_path,
    injected,
    field,
):
    report = validate_claude_global_memory(
        tmp_path / f"acceptance-{injected}",
        injected_effect=injected,
    )
    assert report.status == "FAIL"
    assert getattr(report.effects, field) >= 1
    assert report.reason_codes == (f"forbidden_effect:{injected}",)


@pytest.mark.parametrize(
    ("effect_name", "field"),
    [
        ("network", "network_calls"),
        ("external_cli", "external_cli_calls"),
        ("production_write", "production_writes"),
    ],
)
def test_real_runtime_effect_in_exercised_path_turns_acceptance_red(
    tmp_path,
    monkeypatch,
    effect_name,
    field,
):
    original = claude_acceptance._execute_run
    outside = tmp_path / "outside-acceptance.txt"

    def execute_effect():
        if effect_name == "network":
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as selected:
                selected.sendto(b"synthetic", ("127.0.0.1", 9))
        elif effect_name == "external_cli":
            subprocess.run([sys.executable, "-c", "pass"], check=True)
        else:
            outside.write_bytes(b"synthetic outside write")

    def wrapped(root):
        execute_effect()
        return original(root)

    monkeypatch.setattr(claude_acceptance, "_execute_run", wrapped)
    report = validate_claude_global_memory(tmp_path / f"acceptance-{effect_name}")

    assert report.status == "FAIL"
    assert getattr(report.effects, field) >= 1
    assert f"forbidden_effect:{effect_name}" in report.reason_codes


def test_report_contains_no_memory_body_or_host_absolute_path(tmp_path):
    report = validate_claude_global_memory(tmp_path / "acceptance")
    encoded = canonical_json_bytes(report.to_dict()).decode("utf-8")
    assert "Synthetic provider-neutral activation memory" not in encoded
    assert "Synthetic Claude user memory" not in encoded
    assert str(tmp_path) not in encoded
    assert "AI_RESIDENCE" not in encoded
    assert "USERPROFILE" not in encoded


def test_acceptance_script_writes_canonical_report(tmp_path):
    output = tmp_path / "report.json"
    root = tmp_path / "acceptance-script"
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(SCRIPT),
            "--root",
            str(root),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "PASS"
    assert output.read_bytes() == canonical_json_bytes(payload) + b"\n"
    assert json.loads(result.stdout)["status"] == "PASS"
