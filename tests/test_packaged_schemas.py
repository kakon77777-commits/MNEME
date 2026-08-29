from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).parents[1]
DIGEST_MANIFEST_NAME = "unified-schema-digests-v0.5.json"
SCHEMA_NAMES = (
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


def _run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def _build_wheel(tmp_path: Path) -> Path:
    source = tmp_path / "source"
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
    wheelhouse = tmp_path / "wheelhouse"
    result = _run(
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
    assert result.returncode == 0, result.stdout + result.stderr
    wheels = tuple(wheelhouse.glob("*.whl"))
    assert len(wheels) == 1
    return wheels[0]


def _install_wheel(wheel: Path, tmp_path: Path) -> Path:
    target = tmp_path / "install"
    result = _run(
        "-m",
        "pip",
        "install",
        "--no-deps",
        "--target",
        str(target),
        str(wheel),
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return target


def _source_schema_hashes() -> dict[str, str]:
    schema_root = ROOT / "src" / "mneme" / "schemas"
    return {
        name: hashlib.sha256((schema_root / name).read_bytes()).hexdigest()
        for name in SCHEMA_NAMES
    }


def _pinned_schema_hashes() -> dict[str, str]:
    manifest = json.loads(
        (ROOT / "src" / "mneme" / "schemas" / DIGEST_MANIFEST_NAME).read_text(
            encoding="utf-8"
        )
    )
    return manifest["schema_sha256"]


def test_all_source_schema_resources_use_canonical_lf_bytes():
    schema_root = ROOT / "src" / "mneme" / "schemas"
    for name in SCHEMA_NAMES:
        raw = (schema_root / name).read_bytes()
        assert b"\r" not in raw, f"{name} contains noncanonical CR bytes"
        assert raw.endswith(b"\n"), f"{name} lacks one terminal LF"
        assert not raw.endswith(b"\n\n"), f"{name} has duplicate terminal LF"


def test_dev_extra_declares_no_build_isolation_prerequisites():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dev = set(project["project"]["optional-dependencies"]["dev"])

    assert {"pytest>=8.0", "setuptools>=68", "wheel"} <= dev


def test_clean_wheel_contains_one_canonical_schema_set(tmp_path: Path):
    wheel = _build_wheel(tmp_path)
    with zipfile.ZipFile(wheel) as package:
        schema_entries = sorted(
            name.removeprefix("mneme/schemas/")
            for name in package.namelist()
            if name.startswith("mneme/schemas/") and name.endswith(".schema.json")
        )

    assert schema_entries == sorted(SCHEMA_NAMES)
    assert not (ROOT / "schemas").exists()


def test_clean_installed_runtime_loads_exact_pinned_schema_hashes(tmp_path: Path):
    wheel = _build_wheel(tmp_path)
    install = _install_wheel(wheel, tmp_path)
    isolated = tmp_path / "isolated"
    isolated.mkdir()
    code = (
        "import json\n"
        "from mneme.schemas import schema_digest_manifest, schema_sha256\n"
        "from mneme.records import MemoryRecord\n"
        "from mneme.transactions import TransactionProposal\n"
        "from mneme.routes import Route\n"
        "from mneme.markdown_profile import MemoryMarkdownProfile\n"
        "from mneme.cps.models import PersistenceAssessment\n"
        "from mneme.dry_run.policy import PersistencePolicy\n"
        "from mneme.dry_run.intents import FactorizationIntent, SeedIntent\n"
        "from mneme.dry_run.report import DryRunReport\n"
        f"names = {SCHEMA_NAMES!r}\n"
        "observed = {name: schema_sha256(name) for name in names}\n"
        "print(json.dumps({'observed': observed, 'pinned': schema_digest_manifest()}, sort_keys=True))\n"
    )
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = str(install)
    result = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=isolated,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["observed"] == _pinned_schema_hashes()
    assert payload["pinned"] == _pinned_schema_hashes()
    assert _source_schema_hashes() == _pinned_schema_hashes()
