from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
RUNBOOK = ROOT / "docs" / "runtime" / "CLAUDE_GLOBAL_MEMORY_TRANSITION_V0.1.md"
WORKFLOW = ROOT / ".github" / "workflows" / "claude-global-memory.yml"
PYPROJECT = ROOT / "pyproject.toml"


def _run(*arguments: str, cwd: Path, pythonpath: Path | None = None):
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    if pythonpath is not None:
        environment["PYTHONPATH"] = str(pythonpath)
    return subprocess.run(
        [sys.executable, *arguments],
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.fixture(scope="module")
def installed_candidate(tmp_path_factory):
    temporary = tmp_path_factory.mktemp("mneme-installed-candidate")
    source = temporary / "source"
    shutil.copytree(
        ROOT,
        source,
        ignore=shutil.ignore_patterns(
            ".git",
            ".worktrees",
            "__pycache__",
            "*.pyc",
            "build",
            "*.egg-info",
        ),
    )
    wheelhouse = temporary / "wheelhouse"
    built = _run(
        "-m",
        "pip",
        "wheel",
        ".",
        "--no-deps",
        "--no-build-isolation",
        "--wheel-dir",
        str(wheelhouse),
        cwd=source,
    )
    assert built.returncode == 0, built.stdout + built.stderr
    wheels = tuple(wheelhouse.glob("*.whl"))
    assert len(wheels) == 1
    install = temporary / "install"
    installed = _run(
        "-m",
        "pip",
        "install",
        "--no-deps",
        "--target",
        str(install),
        str(wheels[0]),
        cwd=temporary,
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr
    isolated = temporary / "isolated"
    isolated.mkdir()
    return temporary, wheels[0], install, isolated


def test_clean_installed_candidate_imports_and_entrypoint(installed_candidate):
    _, _, install, isolated = installed_candidate
    code = """
import json
from importlib.metadata import distribution
import mneme.schemas
import mneme.adapters.claude
import mneme.claude_projection
import mneme.claude_import
import mneme.claude_activation
import mneme.claude_acceptance
dist = distribution('mneme-memory')
entries = [ep for ep in dist.entry_points if ep.name == 'mneme-claude-global']
print(json.dumps({'version': dist.version, 'entrypoints': [ep.value for ep in entries]}, sort_keys=True))
raise SystemExit(entries[0].load()(['verify']))
"""
    result = _run("-B", "-c", code, cwd=isolated, pythonpath=install)
    assert result.returncode == 0, result.stdout + result.stderr
    lines = result.stdout.splitlines()
    assert json.loads(lines[0]) == {
        "entrypoints": ["mneme.claude_cli:main"],
        "version": "0.4.0a1",
    }
    assert json.loads(lines[1]) == {
        "profile": "mneme.claude-global/0.1",
        "real_activation": "NOT_AUTHORIZED",
        "status": "PASS",
    }


def test_clean_installed_entrypoint_runs_synthetic_activation(installed_candidate):
    temporary, _, install, isolated = installed_candidate
    synthetic_root = temporary / "installed-synthetic-root"
    code = """
import json
import os
from importlib.metadata import distribution
entry = next(ep for ep in distribution('mneme-memory').entry_points if ep.name == 'mneme-claude-global')
main = entry.load()
root = os.environ['MNEME_INSTALLED_SYNTHETIC_ROOT']
apply_code = main(['apply-synthetic', '--root', root])
status_code = main(['status', '--root', root])
raise SystemExit(0 if (apply_code, status_code) == (0, 0) else 9)
"""
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = str(install)
    environment["MNEME_INSTALLED_SYNTHETIC_ROOT"] = str(synthetic_root)
    result = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=isolated,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payloads = [json.loads(line) for line in result.stdout.splitlines()]
    assert payloads[0]["status"] == "PASS"
    assert payloads[0]["real_claude_user_memory"] == "NOT_TOUCHED"
    assert payloads[1]["status"] == "PRESENT"
    assert payloads[1]["claude_memory_readback"] == "NOT_RUN"


def test_runbook_preserves_activation_nonclaims_and_later_gate():
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "real_claude_user_memory = NOT_TOUCHED" in text
    assert "private_residence = NOT_READ" in text
    assert "claude_memory_readback = NOT_RUN" in text
    assert "CGM-023" in text
    assert "CGM-024" in text
    assert "CGM-026" in text
    assert "CGM-027" in text
    assert "separate local activation plan" in text
    assert "cpython_audit_and_profile_v0.1" in text
    assert "not a cross-toolchain reproducibility claim" in " ".join(text.split())
    for forbidden in ("AI_RESIDENCE", "USERPROFILE", "C:\\Users\\", "sk-"):
        assert forbidden not in text


def test_ci_has_windows_ubuntu_full_acceptance_and_clean_wheel_gates():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "windows-latest" in text
    assert "ubuntu-latest" in text
    assert "python -B -m pytest -q -rs" in text
    assert "validate_claude_global_memory.py" in text
    assert "pip wheel" in text
    assert "--no-build-isolation" in text
    assert "--no-deps" in text


def test_dev_extra_declares_no_build_isolation_prerequisites():
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    dev = set(project["project"]["optional-dependencies"]["dev"])

    assert "pytest>=8.0" in dev
    assert "setuptools>=68" in dev
    assert "wheel" in dev
