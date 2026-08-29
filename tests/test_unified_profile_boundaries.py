from __future__ import annotations

import ast
import hashlib
import inspect
from pathlib import Path

import pytest

from mneme.dry_run.analyzer import PrivateResidenceDryRunAnalyzer
from mneme.markdown_compat import propose_profiled_markdown_import
from mneme.markdown_profile import load_builtin_evemiss_profile

ROOT = Path(__file__).parents[1]
REAL_DIALECT_SYNTHETIC_FIXTURE = (
    ROOT / "fixtures" / "synthetic" / "memory-markdown-real-dialect-v02.md"
)
PROFILE_BYTES = {
    "evemiss-residence-0.1.json": "4e2daa27ac79f0c50d965efbb340a67e71dd4a731f5b44f9015c36ed70174b35",
    "evemiss-residence-0.2.json": "9896ee3464f203d2d0f8f0f9b23951bb471f90b833cba97382f7877f6b5153ba",
}


def _import_targets(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = "." * node.level + (node.module or "")
            targets.append(base)
            targets.extend(
                f"{base}.{alias.name}" if node.module else f"{base}{alias.name}"
                for alias in node.names
            )
    return tuple(targets)


def test_v01_profile_remains_frozen_and_v02_requires_exact_selection():
    from mneme import MappingProfileError, load_builtin_evemiss_profile_by_id

    v01 = load_builtin_evemiss_profile_by_id("evemiss-residence/0.1")
    v02 = load_builtin_evemiss_profile_by_id("evemiss-residence/0.2")

    assert v01.digest() == (
        "0757299afd2d72d9cd0f3f3c7ff616f17836edff2b694afc0340d0eea055fdeb"
    )
    assert v02.profile_id == "evemiss-residence/0.2"
    assert v02.digest() == (
        "eff793c64a251da93b8f2256ce5cf33381c3a58129e854c312d5e13b3b9521d9"
    )
    for unsupported in (
        "auto",
        "",
        "evemiss-residence/0.3",
        "EVEMISS-RESIDENCE/0.2",
    ):
        with pytest.raises(MappingProfileError):
            load_builtin_evemiss_profile_by_id(unsupported)


def test_v01_never_guesses_v02_dialect():
    proposal = propose_profiled_markdown_import(
        REAL_DIALECT_SYNTHETIC_FIXTURE,
        load_builtin_evemiss_profile(),
    )

    reasons = [item["reason"] for item in proposal.loss_report["loss"]]
    assert reasons.count("unknown_heading") == 2


def test_builtin_profile_source_bytes_remain_frozen():
    profile_root = ROOT / "profiles" / "memory-markdown"

    for name, expected_sha256 in PROFILE_BYTES.items():
        working_bytes = (profile_root / name).read_bytes()
        canonical_lf = working_bytes.replace(b"\r\n", b"\n")
        assert b"\r" not in canonical_lf
        assert hashlib.sha256(canonical_lf).hexdigest() == expected_sha256


def test_claude_and_soacr_hot_paths_do_not_import_dry_run_or_cps():
    for module_path in (
        ROOT / "src" / "mneme" / "adapters" / "claude.py",
        ROOT / "src" / "mneme" / "adapters" / "soacr.py",
        ROOT / "src" / "mneme" / "claude_activation.py",
    ):
        targets = tuple(target.lstrip(".") for target in _import_targets(module_path))
        assert not any(
            target in {"dry_run", "cps"}
            or target.startswith(
                ("dry_run.", "cps.", "mneme.dry_run", "mneme.cps")
            )
            for target in targets
        )


def test_dry_run_has_no_writable_store_input():
    parameters = inspect.signature(PrivateResidenceDryRunAnalyzer.analyze).parameters

    assert "store" not in parameters
    assert "memory_store" not in parameters
