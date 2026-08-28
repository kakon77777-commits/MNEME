from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCHEMA_NAMES = (
    "cognitive-seed-proposal-0.1.schema.json",
    "equivalence-contract-0.1.schema.json",
    "factorization-proposal-0.1.schema.json",
    "memory-markdown-profile-0.1.schema.json",
    "memory-record-0.1.schema.json",
    "persistence-assessment-0.1.schema.json",
    "projection-manifest-0.1.schema.json",
    "recomputation-reference-0.1.schema.json",
    "route-0.1.schema.json",
    "transaction-0.1.schema.json",
)


def _run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
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


def test_clean_installed_runtime_loads_exact_source_schema_hashes(tmp_path: Path):
    wheel = _build_wheel(tmp_path)
    install = _install_wheel(wheel, tmp_path)
    isolated = tmp_path / "isolated"
    isolated.mkdir()
    code = (
        "import json\n"
        "from mneme.schemas import schema_sha256\n"
        "from mneme.records import MemoryRecord\n"
        "from mneme.transactions import TransactionProposal\n"
        "from mneme.routes import Route\n"
        "from mneme.markdown_profile import MemoryMarkdownProfile\n"
        "from mneme.cps.models import PersistenceAssessment\n"
        f"names = {SCHEMA_NAMES!r}\n"
        "print(json.dumps({name: schema_sha256(name) for name in names}, sort_keys=True))\n"
    )
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = str(install)
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=isolated,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == _source_schema_hashes()
