from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from mneme.canonical import canonical_json_bytes
from tests.windows_junction import create_windows_junction

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "mneme_claude_global.py"


def run_cli(*arguments: str):
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-B", str(SCRIPT), *arguments],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    payload = json.loads(result.stdout) if result.stdout else None
    return result, payload


def assert_canonical_stdout(result, payload):
    assert result.stdout == canonical_json_bytes(payload).decode("utf-8") + "\n"


def test_verify_command_is_read_only_and_canonical():
    result, payload = run_cli("verify")
    assert result.returncode == 0, result.stderr
    assert payload == {
        "profile": "mneme.claude-global/0.1",
        "real_activation": "NOT_AUTHORIZED",
        "status": "PASS",
    }
    assert_canonical_stdout(result, payload)


def test_plan_command_does_not_create_sandbox(tmp_path):
    root = tmp_path / "mneme-synthetic-cli"
    result, payload = run_cli("plan", "--root", str(root))

    assert result.returncode == 0, result.stderr
    assert payload["status"] == "PLANNED"
    assert payload["execution_mode"] == "synthetic_test"
    assert payload["production_wave_run"] == "NOT_APPLICABLE"
    assert "plan_digest" in payload
    assert not root.exists()
    assert_canonical_stdout(result, payload)


def test_apply_synthetic_and_status_commands(tmp_path):
    root = tmp_path / "mneme-synthetic-cli"
    applied, receipt = run_cli("apply-synthetic", "--root", str(root))
    assert applied.returncode == 0, applied.stderr
    assert receipt["status"] == "PASS"
    assert receipt["steps"] == [
        "canonical_commit",
        "projection_publish",
        "managed_import",
    ]
    assert receipt["real_claude_user_memory"] == "NOT_TOUCHED"
    assert "Synthetic provider-neutral activation memory" not in applied.stdout
    assert_canonical_stdout(applied, receipt)

    status_result, status = run_cli("status", "--root", str(root))
    assert status_result.returncode == 0, status_result.stderr
    assert status["status"] == "PRESENT"
    assert status["claude_memory_readback"] == "NOT_RUN"
    assert status["real_claude_user_memory"] == "NOT_TOUCHED"
    assert "head" in status
    assert_canonical_stdout(status_result, status)


def test_real_target_override_is_hard_stopped_without_opening_target(tmp_path):
    root = tmp_path / "mneme-synthetic-cli"
    outside = tmp_path / "real-looking" / ".claude" / "CLAUDE.md"
    outside.parent.mkdir(parents=True)
    outside.write_bytes(b"must remain untouched")

    result, payload = run_cli(
        "apply-synthetic",
        "--root",
        str(root),
        "--claude-user-memory",
        str(outside),
    )

    assert result.returncode == 2
    assert payload["reason_codes"] == ["real_activation_not_authorized"]
    assert outside.read_bytes() == b"must remain untouched"
    assert not root.exists()
    assert_canonical_stdout(result, payload)


def test_non_synthetic_execution_mode_is_policy_refusal(tmp_path):
    root = tmp_path / "mneme-synthetic-cli"
    result, payload = run_cli(
        "apply-synthetic",
        "--root",
        str(root),
        "--execution-mode",
        "real",
    )
    assert result.returncode == 2
    assert payload["reason_codes"] == ["real_activation_not_authorized"]
    assert not root.exists()


def test_input_error_has_exit_one_and_no_traceback():
    result, payload = run_cli("apply-synthetic")
    assert result.returncode == 1
    assert payload["reason_codes"] == ["input_error"]
    assert "Traceback" not in result.stderr
    assert_canonical_stdout(result, payload)


@pytest.mark.skipif(os.name != "nt", reason="Windows junction control")
def test_status_refuses_junctioned_projection_without_reading_outside(tmp_path):
    root = tmp_path / "mneme-synthetic-cli"
    applied, _ = run_cli("apply-synthetic", "--root", str(root))
    assert applied.returncode == 0, applied.stderr
    projection_directory = root / "runtime" / "claude"
    (projection_directory / "MNEME_GLOBAL.md").unlink()
    projection_directory.rmdir()
    outside = tmp_path / "outside-projection"
    outside.mkdir()
    (outside / "MNEME_GLOBAL.md").write_bytes(b"OUTSIDE-SYNTHETIC-CONTENT")
    create_windows_junction(projection_directory, outside)

    result, payload = run_cli("status", "--root", str(root))

    assert result.returncode == 2
    assert payload["reason_codes"] == ["policy_refusal"]
    assert "OUTSIDE-SYNTHETIC-CONTENT" not in result.stdout


def test_status_refuses_hardlinked_projection_without_reading_outside(tmp_path):
    root = tmp_path / "mneme-synthetic-cli"
    applied, _ = run_cli("apply-synthetic", "--root", str(root))
    assert applied.returncode == 0, applied.stderr
    projection = root / "runtime" / "claude" / "MNEME_GLOBAL.md"
    projection.unlink()
    outside = tmp_path / "outside-hardlink-content.md"
    outside.write_bytes(b"OUTSIDE-HARDLINK-SYNTHETIC-CONTENT")
    os.link(outside, projection)

    result, payload = run_cli("status", "--root", str(root))

    assert result.returncode == 2
    assert payload["reason_codes"] == ["policy_refusal"]
    assert "OUTSIDE-HARDLINK-SYNTHETIC-CONTENT" not in result.stdout
