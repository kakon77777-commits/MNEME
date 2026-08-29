from __future__ import annotations

import socket
import subprocess
import sys
from pathlib import Path
from types import FunctionType

import pytest

from mneme.claude_acceptance import _remove_exact_synthetic_run
from mneme.claude_effects import ClaudeRuntimeEffectObserver


def call_synthetic_module(module_name: str) -> None:
    entrypoint = FunctionType(
        _synthetic_entrypoint.__code__,
        {"__name__": module_name},
        "synthetic_entrypoint",
    )
    entrypoint()


def _synthetic_entrypoint() -> None:
    return None


def test_observer_measures_real_forbidden_runtime_apis(tmp_path):
    root = tmp_path / "acceptance"
    root.mkdir()
    fixture = tmp_path / "fixture.json"
    fixture.write_text("{}", encoding="utf-8")
    private = root / "private" / "probe.txt"
    private.parent.mkdir()
    private.write_bytes(b"synthetic private fixture")
    outside = tmp_path / "outside.txt"
    observer = ClaudeRuntimeEffectObserver(
        root,
        fixture_path=fixture,
        allowed_read_paths=(fixture,),
    )

    with observer:
        fixture.read_bytes()
        private.read_bytes()
        private.write_bytes(b"synthetic private write")
        Path(__file__).read_bytes()
        outside.write_bytes(b"synthetic production write")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as selected:
            selected.sendto(b"synthetic", ("127.0.0.1", 9))
        subprocess.run([sys.executable, "-c", "pass"], check=True)
        call_synthetic_module("anthropic.synthetic")
        call_synthetic_module("mcp.synthetic")
        call_synthetic_module("eml_bridge.synthetic")

    evidence = observer.evidence()
    assert evidence.fixture_reads == 1
    assert evidence.private_reads >= 1
    assert evidence.private_writes >= 1
    assert evidence.production_reads >= 1
    assert evidence.production_writes >= 1
    assert evidence.network_calls >= 1
    assert evidence.external_cli_calls >= 1
    assert evidence.provider_calls >= 1
    assert evidence.mcp_calls >= 1
    assert evidence.bridge_calls >= 1
    assert evidence.forbidden_total() >= 9
    assert evidence.observation_mode == "cpython_audit_and_profile_v0.1"
    assert len(evidence.observed_events_digest) == 64
    assert str(tmp_path) not in repr(evidence)


def test_synthetic_root_and_closed_resource_reads_are_allowed(tmp_path):
    root = tmp_path / "acceptance"
    root.mkdir()
    fixture = tmp_path / "fixture.json"
    fixture.write_text("{}", encoding="utf-8")
    resource = tmp_path / "schema.json"
    resource.write_text("{}", encoding="utf-8")
    observer = ClaudeRuntimeEffectObserver(
        root,
        fixture_path=fixture,
        allowed_read_paths=(fixture, resource),
    )

    with observer:
        fixture.read_bytes()
        resource.read_bytes()
        target = root / "synthetic.txt"
        target.write_bytes(b"synthetic")
        target.read_bytes()

    evidence = observer.evidence()
    assert evidence.fixture_reads == 1
    assert evidence.forbidden_total() == 0


def test_repeat_cleanup_stays_inside_synthetic_root_on_all_platforms(tmp_path):
    owner = tmp_path / "acceptance"
    run = owner / "mneme-cgm-repeat"
    nested = run / "runtime" / "memory.mlfdir"
    nested.mkdir(parents=True)
    (nested / "HEAD").write_text("synthetic", encoding="utf-8")
    fixture = tmp_path / "fixture.json"
    fixture.write_text("{}", encoding="utf-8")
    observer = ClaudeRuntimeEffectObserver(
        owner,
        fixture_path=fixture,
        allowed_read_paths=(fixture,),
    )

    with observer:
        _remove_exact_synthetic_run(run, owner)

    assert not run.exists()
    assert observer.evidence().forbidden_total() == 0


def test_observer_is_inactive_after_context_exit(tmp_path):
    root = tmp_path / "acceptance"
    root.mkdir()
    fixture = tmp_path / "fixture.json"
    fixture.write_text("{}", encoding="utf-8")
    observer = ClaudeRuntimeEffectObserver(
        root,
        fixture_path=fixture,
        allowed_read_paths=(fixture,),
    )

    with observer:
        fixture.read_bytes()
    before = observer.evidence()
    (tmp_path / "after.txt").write_bytes(b"outside observer")

    assert observer.evidence() == before


def test_nested_observer_is_refused(tmp_path):
    root = tmp_path / "acceptance"
    root.mkdir()
    fixture = tmp_path / "fixture.json"
    fixture.write_text("{}", encoding="utf-8")
    first = ClaudeRuntimeEffectObserver(
        root,
        fixture_path=fixture,
        allowed_read_paths=(fixture,),
    )
    second = ClaudeRuntimeEffectObserver(
        root,
        fixture_path=fixture,
        allowed_read_paths=(fixture,),
    )

    with first, pytest.raises(RuntimeError, match="already active"), second:
        pass
