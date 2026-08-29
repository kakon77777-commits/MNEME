from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from email.parser import Parser
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "mneme-unified-profile-integration.yml"
EXPECTED_SCHEMA_NAMES = (
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
)
ACCEPTANCE_STEPS = (
    "Fresh Memory Core",
    "MNEME-MD 0.1",
    "EveMiss profile 0.2",
    "MNEME-CPS 0.1",
    "Private Residence Dry-Run 0.2",
    "Claude Global Transition 0.1",
)


@dataclass(frozen=True)
class InstalledCandidate:
    metadata: dict[str, str]
    schema_names: tuple[str, ...]
    cli_exits: dict[str, int]


def _run(*arguments: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    return subprocess.run(
        [sys.executable, *arguments],
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.fixture(scope="module")
def installed_candidate(tmp_path_factory: pytest.TempPathFactory) -> InstalledCandidate:
    temporary = tmp_path_factory.mktemp("mneme-v05-installed-candidate")
    source = temporary / "source"
    shutil.copytree(
        ROOT,
        source,
        ignore=shutil.ignore_patterns(
            ".git",
            ".worktrees",
            ".pytest_cache",
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
    wheel = wheels[0]

    with zipfile.ZipFile(wheel) as package:
        metadata_name = next(
            name for name in package.namelist() if name.endswith(".dist-info/METADATA")
        )
        parsed = Parser().parsestr(package.read(metadata_name).decode("utf-8"))
        metadata = {"Name": parsed["Name"], "Version": parsed["Version"]}
        schema_names = tuple(
            sorted(
                name.removeprefix("mneme/schemas/")
                for name in package.namelist()
                if name.startswith("mneme/schemas/")
                and name.endswith(".schema.json")
            )
        )

    install = temporary / "install"
    installed = _run(
        "-m",
        "pip",
        "install",
        "--no-deps",
        "--target",
        str(install),
        str(wheel),
        cwd=temporary,
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr

    isolated = temporary / "isolated"
    isolated.mkdir()
    synthetic_root = temporary / "synthetic-root"
    code = f"""
import json
import sys
sys.path.insert(0, {str(install)!r})
from mneme.claude_cli import main
root = {str(synthetic_root)!r}
exits = {{
    "verify": main(["verify"]),
    "apply-synthetic": main(["apply-synthetic", "--root", root]),
    "status": main(["status", "--root", root]),
}}
print("MNEME_INSTALLED_RESULT=" + json.dumps(exits, sort_keys=True))
"""
    exercised = _run("-I", "-B", "-c", code, cwd=isolated)
    assert exercised.returncode == 0, exercised.stdout + exercised.stderr
    result_line = next(
        line
        for line in exercised.stdout.splitlines()
        if line.startswith("MNEME_INSTALLED_RESULT=")
    )
    cli_exits = json.loads(result_line.split("=", 1)[1])
    return InstalledCandidate(metadata, schema_names, cli_exits)


def test_unified_package_metadata_resources_and_cli(installed_candidate):
    from mneme import __version__

    assert installed_candidate.metadata == {
        "Name": "mneme-memory",
        "Version": "0.5.0a1",
    }
    assert __version__ == "0.5.0a1"
    assert installed_candidate.schema_names == EXPECTED_SCHEMA_NAMES
    assert installed_candidate.cli_exits == {
        "verify": 0,
        "apply-synthetic": 0,
        "status": 0,
    }


def test_combined_ci_names_all_six_acceptance_surfaces():
    text = WORKFLOW.read_text(encoding="utf-8")

    for label in ACCEPTANCE_STEPS:
        assert f"name: {label}" in text
    assert "ubuntu-latest" in text
    assert "windows-latest" in text
    assert 'python: ["3.11"]' in text
    assert 'python -m pip install -e ".[dev]"' in text
    assert "pip wheel" in text
    assert "--no-build-isolation" in text
    assert "--no-deps" in text
    assert "name: Ruff changed Python" in text
    assert "c21546a263920e0f80701696e1857c203917d701" in text
    assert "secrets." not in text
