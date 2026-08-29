from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import sysconfig
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from importlib.resources import files
from pathlib import Path
from types import FunctionType

from .adapters.claude import ClaudeGlobalMemoryAdapter
from .canonical import canonical_json_bytes, sha256_domain
from .claude_activation import _global_route
from .claude_authority import VerifiedClaudeWriteContext
from .claude_cli import _synthetic_operation
from .claude_contracts import (
    CLAUDE_GLOBAL_NONCLAIMS,
    ClaudeGlobalProjectionRequest,
    LocalManualWriteAuthorization,
)
from .claude_effects import ClaudeRuntimeEffectObserver
from .claude_import import BEGIN, END, ClaudeManagedImport
from .claude_projection import ClaudeProjectionPublisher
from .errors import (
    AtomicReplaceUnavailableError,
    ClaudeContractError,
    ClaudePathBoundaryError,
    InjectedCrash,
    RecordIdConflictError,
    RequiredRecordOmittedError,
    StaleTargetError,
    StoreConflictError,
)
from .records import MemoryRecord
from .schemas import (
    SCHEMA_DIGEST_MANIFEST_NAME,
    UNIFIED_SCHEMA_NAMES,
    read_schema_bytes,
    schema_digest_manifest,
    schema_names,
)
from .store import MemoryStore
from .transactions import TransactionProposal

_REPORT_DOMAIN = b"MNEME-CLAUDE-GLOBAL-ACCEPTANCE-REPORT-0.1"
_RUN_DOMAIN = b"MNEME-CLAUDE-GLOBAL-ACCEPTANCE-RUN-0.1"
_CASE_DOMAIN = b"MNEME-CLAUDE-GLOBAL-ACCEPTANCE-CASE-0.1"
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_EXPECTED_EFFECTS_PATH = (
    _PROJECT_ROOT / "tests" / "fixtures" / "claude" / "expected-effects.json"
)
_LOCAL_CASES = ("CGM-023", "CGM-024", "CGM-026", "CGM-027")
_RUNTIME_SCAN_NAMES = (
    "claude_activation.py",
    "claude_cli.py",
    "claude_projection.py",
    "claude_import.py",
    "adapters/claude.py",
)
_FORBIDDEN_EFFECT_FIELDS = {
    "private_read": "private_reads",
    "private_write": "private_writes",
    "production_read": "production_reads",
    "production_write": "production_writes",
    "network": "network_calls",
    "provider": "provider_calls",
    "mcp": "mcp_calls",
    "bridge": "bridge_calls",
    "external_cli": "external_cli_calls",
}


@dataclass(frozen=True)
class ClaudeGlobalAcceptanceCase:
    case_id: str
    status: str
    executed: bool
    passed: bool
    evidence_digest: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "status": self.status,
            "executed": self.executed,
            "passed": self.passed,
            "evidence_digest": self.evidence_digest,
        }


@dataclass(frozen=True)
class ClaudeGlobalEffectCounters:
    fixture_reads: int
    synthetic_runs: int
    synthetic_writes: int
    synthetic_write_refs: tuple[str, ...]
    observation_mode: str
    observed_events_digest: str
    private_reads: int = 0
    private_writes: int = 0
    production_reads: int = 0
    production_writes: int = 0
    network_calls: int = 0
    provider_calls: int = 0
    mcp_calls: int = 0
    bridge_calls: int = 0
    external_cli_calls: int = 0
    observer_errors: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "fixture_reads": self.fixture_reads,
            "synthetic_runs": self.synthetic_runs,
            "synthetic_writes": self.synthetic_writes,
            "synthetic_write_refs": list(self.synthetic_write_refs),
            "observation_mode": self.observation_mode,
            "observed_events_digest": self.observed_events_digest,
            "private_reads": self.private_reads,
            "private_writes": self.private_writes,
            "production_reads": self.production_reads,
            "production_writes": self.production_writes,
            "network_calls": self.network_calls,
            "provider_calls": self.provider_calls,
            "mcp_calls": self.mcp_calls,
            "bridge_calls": self.bridge_calls,
            "external_cli_calls": self.external_cli_calls,
            "observer_errors": self.observer_errors,
        }

    def forbidden_total(self) -> int:
        return sum(
            (
                self.private_reads,
                self.private_writes,
                self.production_reads,
                self.production_writes,
                self.network_calls,
                self.provider_calls,
                self.mcp_calls,
                self.bridge_calls,
                self.external_cli_calls,
                self.observer_errors,
            )
        )


@dataclass(frozen=True)
class ClaudeGlobalAcceptanceReport:
    status: str
    cases: tuple[ClaudeGlobalAcceptanceCase, ...]
    effects: ClaudeGlobalEffectCounters
    deterministic: bool
    run_fingerprints: tuple[str, str]
    artifact_runs: tuple[dict[str, str], dict[str, str]]
    expected_effects_ref: str
    expected_effects_sha256: str
    reason_codes: tuple[str, ...]
    report_digest: str

    def _material(self) -> dict[str, object]:
        return {
            "report_version": "mneme.claude-global-acceptance-report/0.1",
            "status": self.status,
            "cases": [case.to_dict() for case in self.cases],
            "effects": self.effects.to_dict(),
            "deterministic": self.deterministic,
            "run_fingerprints": list(self.run_fingerprints),
            "artifact_runs": list(self.artifact_runs),
            "expected_effects_ref": self.expected_effects_ref,
            "expected_effects_sha256": self.expected_effects_sha256,
            "reason_codes": list(self.reason_codes),
            "real_claude_user_memory": "NOT_TOUCHED",
            "private_residence": "NOT_READ",
            "claude_memory_readback": "NOT_RUN",
        }

    def verify(self) -> bool:
        expected = sha256_domain(_REPORT_DOMAIN, canonical_json_bytes(self._material()))
        if self.report_digest != expected:
            raise ClaudeContractError("Claude acceptance report digest mismatch")
        if len(self.cases) != 28 or len({case.case_id for case in self.cases}) != 28:
            raise ClaudeContractError("Claude acceptance case population mismatch")
        return True

    def to_dict(self) -> dict[str, object]:
        self.verify()
        return {**self._material(), "report_digest": self.report_digest}


@dataclass(frozen=True)
class _RunEvidence:
    cases: tuple[ClaudeGlobalAcceptanceCase, ...]
    artifacts: dict[str, str]
    fingerprint: str
    activation_steps: int


def validate_claude_global_memory(
    root: Path,
    *,
    injected_effect: str | None = None,
) -> ClaudeGlobalAcceptanceReport:
    selected_root = Path(root)
    if not selected_root.is_absolute():
        raise ClaudeContractError("acceptance root must be absolute")
    if selected_root.exists():
        raise ClaudeContractError("acceptance root must not already exist")
    private_read_probe = _prepare_private_read_probe(selected_root, injected_effect)
    observer = ClaudeRuntimeEffectObserver(
        selected_root,
        fixture_path=_EXPECTED_EFFECTS_PATH,
        allowed_read_paths=_acceptance_allowed_read_paths(),
        allowed_read_roots=_python_runtime_read_roots(),
    )
    cleanup_paths: tuple[Path, ...] = ()
    with observer:
        selected_root.mkdir(exist_ok=True)
        expected_bytes = _EXPECTED_EFFECTS_PATH.read_bytes()
        expected = json.loads(expected_bytes.decode("utf-8"))
        expected_effects = expected["positive_effects"]
        cleanup_paths = _run_injected_effect_probe(
            selected_root,
            injected_effect,
            private_read_probe=private_read_probe,
        )

        repeat_root = selected_root / "mneme-cgm-repeat"
        first = _execute_run(repeat_root)
        _remove_exact_synthetic_run(repeat_root, selected_root)
        second = _execute_run(repeat_root)
    for cleanup_path in cleanup_paths:
        cleanup_path.unlink(missing_ok=True)
    deterministic = (
        first.fingerprint == second.fingerprint
        and first.cases == second.cases
        and first.artifacts == second.artifacts
    )
    observed = observer.evidence()
    effects = ClaudeGlobalEffectCounters(
        fixture_reads=observed.fixture_reads,
        synthetic_runs=2,
        synthetic_writes=first.activation_steps + second.activation_steps,
        synthetic_write_refs=(
            "canonical_commit",
            "managed_import",
            "projection_publish",
        ),
        observation_mode=observed.observation_mode,
        observed_events_digest=observed.observed_events_digest,
        private_reads=observed.private_reads,
        private_writes=observed.private_writes,
        production_reads=observed.production_reads,
        production_writes=observed.production_writes,
        network_calls=observed.network_calls,
        provider_calls=observed.provider_calls,
        mcp_calls=observed.mcp_calls,
        bridge_calls=observed.bridge_calls,
        external_cli_calls=observed.external_cli_calls,
        observer_errors=observed.observer_errors,
    )
    if not _effects_match_expected_positive(effects, expected_effects):
        raise ClaudeContractError("measured effects do not match expected fixture")
    reason_codes = _effect_reason_codes(effects)

    local_cases = tuple(
        ClaudeGlobalAcceptanceCase(
            case_id=case_id,
            status="NOT_RUN_LOCAL_ACTIVATION_REQUIRED",
            executed=False,
            passed=False,
            evidence_digest=None,
        )
        for case_id in _LOCAL_CASES
    )
    cases = tuple(sorted((*second.cases, *local_cases), key=lambda case: case.case_id))
    passed = deterministic and all(case.passed for case in second.cases)
    status = "PASS" if passed and effects.forbidden_total() == 0 else "FAIL"
    provisional = ClaudeGlobalAcceptanceReport(
        status=status,
        cases=cases,
        effects=effects,
        deterministic=deterministic,
        run_fingerprints=(first.fingerprint, second.fingerprint),
        artifact_runs=(first.artifacts, second.artifacts),
        expected_effects_ref=str(expected["fixture_ref"]),
        expected_effects_sha256=hashlib.sha256(expected_bytes).hexdigest(),
        reason_codes=reason_codes,
        report_digest="",
    )
    digest = sha256_domain(_REPORT_DOMAIN, canonical_json_bytes(provisional._material()))
    report = replace(provisional, report_digest=digest)
    report.verify()
    return report


def _prepare_private_read_probe(root: Path, injected_effect: str | None) -> Path | None:
    if injected_effect is not None and injected_effect not in _FORBIDDEN_EFFECT_FIELDS:
        raise ValueError(f"unknown injected effect: {injected_effect}")
    if injected_effect != "private_read":
        return None
    probe = root / "private" / "synthetic-read-probe.txt"
    probe.parent.mkdir(parents=True)
    probe.write_bytes(b"synthetic private read probe")
    return probe


def _acceptance_allowed_read_paths() -> tuple[Path, ...]:
    schema_paths = tuple(
        Path(str(item))
        for item in files("mneme.schemas").iterdir()
        if item.name.endswith(".schema.json")
        or item.name == SCHEMA_DIGEST_MANIFEST_NAME
    )
    source_paths = tuple(Path(__file__).parent / name for name in _RUNTIME_SCAN_NAMES)
    return (_EXPECTED_EFFECTS_PATH, *schema_paths, *source_paths)


def _python_runtime_read_roots() -> tuple[Path, ...]:
    selected = {
        Path(value)
        for key in ("stdlib", "platstdlib", "purelib", "platlib")
        if (value := sysconfig.get_path(key))
    }
    return tuple(sorted(selected, key=lambda path: str(path).casefold()))


def _run_injected_effect_probe(
    root: Path,
    injected_effect: str | None,
    *,
    private_read_probe: Path | None,
) -> tuple[Path, ...]:
    if injected_effect is None:
        return ()
    if injected_effect == "private_read":
        if private_read_probe is None:
            raise ClaudeContractError("private read probe was not prepared")
        private_read_probe.read_bytes()
        return ()
    if injected_effect == "private_write":
        target = root / "private" / "synthetic-write-probe.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"synthetic private write probe")
        return ()
    if injected_effect == "production_read":
        (_PROJECT_ROOT / "pyproject.toml").read_bytes()
        return ()
    if injected_effect == "production_write":
        target = root.parent / f".{root.name}.synthetic-production-write-probe"
        target.write_bytes(b"synthetic production write probe")
        return (target,)
    if injected_effect == "network":
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as selected:
            selected.sendto(b"synthetic", ("127.0.0.1", 9))
        return ()
    if injected_effect == "external_cli":
        subprocess.run([sys.executable, "-c", "pass"], check=True)
        return ()
    module_names = {
        "provider": "anthropic.synthetic_probe",
        "mcp": "mcp.synthetic_probe",
        "bridge": "eml_bridge.synthetic_probe",
    }
    module_name = module_names.get(injected_effect)
    if module_name is None:
        raise ValueError(f"unknown injected effect: {injected_effect}")
    entrypoint = FunctionType(
        _synthetic_effect_entrypoint.__code__,
        {"__name__": module_name},
        "synthetic_entrypoint",
    )
    entrypoint()
    return ()


def _synthetic_effect_entrypoint() -> None:
    return None


def _effects_match_expected_positive(
    effects: ClaudeGlobalEffectCounters,
    expected: dict[str, object],
) -> bool:
    actual = effects.to_dict()
    if set(actual) != set(expected):
        return False
    ignored_when_red = {
        *_FORBIDDEN_EFFECT_FIELDS.values(),
        "observer_errors",
        "observed_events_digest",
    }
    for key, expected_value in expected.items():
        if effects.forbidden_total() and key in ignored_when_red:
            continue
        if actual[key] != expected_value:
            return False
    return True


def _effect_reason_codes(effects: ClaudeGlobalEffectCounters) -> tuple[str, ...]:
    reasons = tuple(
        f"forbidden_effect:{effect}"
        for effect, field in _FORBIDDEN_EFFECT_FIELDS.items()
        if getattr(effects, field) > 0
    )
    if effects.observer_errors:
        return (*reasons, "effect_observer_error")
    return reasons


def _execute_run(root: Path) -> _RunEvidence:
    root.mkdir()
    activation, plan, authorization = _synthetic_operation(root / "activation")
    activation_receipt = activation.apply_synthetic(plan, authorization)
    store = MemoryStore(plan.config.store_root)
    context = VerifiedClaudeWriteContext.bind(
        store,
        plan.transaction,
        activation_receipt.commit_receipt,
        authorization,
    )
    materialized = ClaudeGlobalMemoryAdapter(store, _global_route()).materialize(
        plan.request
    )
    repeated = ClaudeGlobalMemoryAdapter(store, _global_route()).materialize(plan.request)
    publisher = ClaudeProjectionPublisher(plan.config.runtime_root)
    repeated_publication_plan = publisher.plan(
        materialized,
        plan.config.projection_target,
        hashlib.sha256(materialized.content).hexdigest(),
    )

    evidence: dict[str, object] = {}
    evidence["CGM-001"] = materialized == repeated
    evidence["CGM-002"] = materialized.manifest.included_record_ids == (
        "record:synthetic:activation",
    )
    evidence["CGM-003"] = _case_scope_exclusion(root / "case-003")
    evidence["CGM-004"] = _case_required_overflow(root / "case-004")
    evidence["CGM-005"] = _case_optional_overflow(root / "case-005")
    evidence["CGM-006"] = len(materialized.content) <= 16000
    evidence["CGM-007"] = _case_budget_16001_refusal()
    evidence["CGM-008"] = _case_schema_resources()
    evidence["CGM-009"] = _case_concurrent_writers(root / "case-009")
    evidence["CGM-010"] = _case_duplicate_ids(root / "case-010")
    evidence["CGM-011"] = _case_reused_id(root / "case-011")
    evidence["CGM-012"] = _case_authority_mismatch(root / "case-012")
    evidence["CGM-013"] = activation_receipt.import_receipt.outcome == "inserted"
    evidence["CGM-014"] = _case_idempotent_import(
        plan,
        context,
        repeated_publication_plan,
        materialized,
    )
    evidence["CGM-015"] = _case_marker_conflict(
        root / "case-015",
        materialized,
        context,
    )
    outside_preserved = _case_outside_preservation(
        root / "case-016",
        materialized,
        context,
    )
    evidence["CGM-016"] = outside_preserved
    evidence["CGM-017"] = _case_stale_user(
        root / "case-017",
        materialized,
        context,
    )
    evidence["CGM-018"] = _case_stale_projection(
        root / "case-018",
        materialized,
        context,
    )
    evidence["CGM-019"] = _case_crash_before(
        root / "case-019",
        materialized,
        context,
    )
    evidence["CGM-020"] = _case_crash_after(
        root / "case-020",
        materialized,
        context,
    )
    evidence["CGM-021"] = _case_private_and_runtime_scan(root / "case-021", materialized)
    evidence["CGM-022"] = _case_model_authority(root / "case-022")
    evidence["CGM-025"] = outside_preserved
    evidence["CGM-028"] = _case_concurrent_reader(
        root / "case-028",
        materialized,
        context,
    )
    if not all(evidence.values()):
        failed = sorted(case_id for case_id, passed in evidence.items() if not passed)
        raise ClaudeContractError(f"synthetic CGM case failed: {failed}")

    cases = tuple(
        _pass_case(case_id, {"control": case_id, "result": "PASS"})
        for case_id in sorted(evidence)
    )
    artifacts = {
        "store_head": store.head(),
        "projection_sha256": hashlib.sha256(materialized.content).hexdigest(),
        "manifest_digest": materialized.manifest.digest,
        "projection_receipt_digest": activation_receipt.projection_receipt.digest,
        "import_receipt_digest": activation_receipt.import_receipt.digest,
        "activation_receipt_digest": activation_receipt.digest,
    }
    fingerprint_material = {
        "cases": [case.to_dict() for case in cases],
        "artifacts": artifacts,
    }
    fingerprint = sha256_domain(_RUN_DOMAIN, canonical_json_bytes(fingerprint_material))
    return _RunEvidence(cases, artifacts, fingerprint, len(activation_receipt.steps))


def _pass_case(case_id: str, evidence: dict[str, object]) -> ClaudeGlobalAcceptanceCase:
    digest = sha256_domain(_CASE_DOMAIN, canonical_json_bytes(evidence))
    return ClaudeGlobalAcceptanceCase(case_id, "PASS", True, True, digest)


def _record(
    record_id: str,
    scope: str,
    *,
    text: str = "Synthetic acceptance record.",
    record_type: str = "fact",
) -> dict[str, object]:
    kind, _, subject = scope.partition("/")
    return {
        "record_version": "mneme.memory-record/0.1",
        "record_id": record_id,
        "record_type": record_type,
        "scope": {"kind": kind, "subject": subject},
        "content": {"text": text},
        "relations": [],
        "provenance": {
            "event_id": f"event:{record_id}",
            "source_ref": "synthetic:acceptance",
        },
        "status": "active",
    }


def _transaction(
    transaction_id: str,
    records: list[dict[str, object]],
    *,
    expected_head: str = "GENESIS",
) -> TransactionProposal:
    return TransactionProposal.from_dict(
        {
            "transaction_version": "mneme.transaction/0.1",
            "transaction_id": transaction_id,
            "expected_source_head": expected_head,
            "declared_record_count": len(records),
            "record_digests": [MemoryRecord.from_dict(record).digest() for record in records],
            "records": records,
            "authority_ref": "synthetic-authority:acceptance",
            "commit_marker": "MNEME_COMMIT/0.1",
        }
    )


def _request(
    store: MemoryStore,
    *,
    required: list[str],
    budget: int = 16000,
) -> ClaudeGlobalProjectionRequest:
    return ClaudeGlobalProjectionRequest.sealed(
        {
            "request_version": "mneme.claude-global-projection-request/0.1",
            "request_id": "request:synthetic:acceptance",
            "expected_source_head": store.head(),
            "route_id": "route://global/tier0",
            "allowed_scope_paths": ["global/core"],
            "required_record_ids": required,
            "byte_budget": budget,
            "target_kind": "claude_code_user_memory_import",
            "projection_ref": "projection:synthetic:acceptance",
            "not_claimed": list(CLAUDE_GLOBAL_NONCLAIMS),
        }
    )


def _store_with_records(root: Path, records: list[dict[str, object]]) -> MemoryStore:
    store = MemoryStore(root / "memory.mlfdir")
    store.commit(_transaction("transaction:synthetic:acceptance", records))
    return store


def _case_scope_exclusion(root: Path) -> bool:
    store = _store_with_records(
        root,
        [
            _record("global", "global/core"),
            _record("identity", "identity/synthetic", text="IDENTITY-BODY"),
        ],
    )
    result = ClaudeGlobalMemoryAdapter(store, _global_route()).materialize(
        _request(store, required=["global"])
    )
    return (
        result.manifest.included_record_ids == ("global",)
        and any(item["record_id"] == "identity" for item in result.manifest.omitted)
        and b"IDENTITY-BODY" not in result.content
    )


def _case_required_overflow(root: Path) -> bool:
    store = _store_with_records(
        root,
        [_record("required-large", "global/core", text="x" * 1000)],
    )
    try:
        ClaudeGlobalMemoryAdapter(store, _global_route()).materialize(
            _request(store, required=["required-large"], budget=100)
        )
    except RequiredRecordOmittedError:
        return True
    return False


def _case_optional_overflow(root: Path) -> bool:
    store = _store_with_records(
        root,
        [
            _record("required-small", "global/core", text="small"),
            _record("optional-large", "global/core", text="x" * 1000),
        ],
    )
    result = ClaudeGlobalMemoryAdapter(store, _global_route()).materialize(
        _request(store, required=["required-small"], budget=160)
    )
    return (
        "required-small" in result.manifest.included_record_ids
        and any(
            item == {"record_id": "optional-large", "reason": "budget_exceeded"}
            for item in result.manifest.omitted
        )
        and len(list(store.iter_committed_records())) == 2
    )


def _case_budget_16001_refusal() -> bool:
    material = {
        "request_version": "mneme.claude-global-projection-request/0.1",
        "request_id": "request:invalid-budget",
        "expected_source_head": "a" * 64,
        "route_id": "route://global/tier0",
        "allowed_scope_paths": ["global/core"],
        "required_record_ids": [],
        "byte_budget": 16001,
        "target_kind": "claude_code_user_memory_import",
        "projection_ref": "projection:invalid-budget",
        "not_claimed": list(CLAUDE_GLOBAL_NONCLAIMS),
    }
    try:
        ClaudeGlobalProjectionRequest.sealed(material)
    except ClaudeContractError:
        return True
    return False


def _case_schema_resources() -> bool:
    try:
        names = schema_names()
        pinned = schema_digest_manifest()
    except (OSError, TypeError, ValueError):
        return False
    return names == UNIFIED_SCHEMA_NAMES and all(
        hashlib.sha256(read_schema_bytes(name)).hexdigest() == pinned[name]
        for name in names
    )


def _case_concurrent_writers(root: Path) -> bool:
    store = MemoryStore(root / "memory.mlfdir")
    store.initialize()
    proposals = tuple(
        _transaction(
            f"transaction:writer:{label}",
            [_record(f"record:writer:{label}", "global/core")],
        )
        for label in ("a", "b")
    )

    def commit(proposal: TransactionProposal) -> str:
        try:
            store.commit(proposal)
        except StoreConflictError:
            return "refused"
        return "success"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = tuple(pool.map(commit, proposals))
    return outcomes.count("success") == 1 and outcomes.count("refused") == 1


def _case_duplicate_ids(root: Path) -> bool:
    first = _record("duplicate", "global/core", text="one")
    second = _record("duplicate", "global/core", text="two")
    try:
        MemoryStore(root / "memory.mlfdir").commit(
            _transaction("transaction:duplicate", [first, second])
        )
    except RecordIdConflictError:
        return True
    return False


def _case_reused_id(root: Path) -> bool:
    store = MemoryStore(root / "memory.mlfdir")
    first = store.commit(
        _transaction("transaction:first", [_record("reused", "global/core")])
    )
    try:
        store.commit(
            _transaction(
                "transaction:second",
                [_record("reused", "global/core", text="changed")],
                expected_head=first.new_head,
            )
        )
    except RecordIdConflictError:
        return True
    return False


def _case_authority_mismatch(root: Path) -> bool:
    root.mkdir()
    activation, plan, authorization = _synthetic_operation(root / "activation")
    raw = authorization.to_dict()
    raw["transaction_digest"] = "f" * 64
    changed = LocalManualWriteAuthorization.sealed(raw)
    try:
        activation.apply_synthetic(plan, changed)
    except ClaudeContractError:
        return not plan.config.sandbox_root.exists()
    return False


def _case_idempotent_import(plan, context, publication_plan, materialized) -> bool:
    importer = ClaudeManagedImport(
        plan.config.runtime_root,
        plan.config.user_memory_root,
        materialized.manifest,
    )
    before = plan.config.user_memory_target.read_bytes()
    prepared = importer.plan(
        plan.config.user_memory_target,
        publication_plan,
        hashlib.sha256(before).hexdigest(),
    )
    receipt = importer.apply(prepared, context).import_receipt
    return receipt.outcome == "idempotent" and plan.config.user_memory_target.read_bytes() == before


def _setup_import_case(root: Path, materialized, user_bytes: bytes, context):
    runtime = root / "runtime"
    projection = runtime / "claude" / "MNEME_GLOBAL.md"
    projection.parent.mkdir(parents=True)
    publisher = ClaudeProjectionPublisher(runtime)
    publication_plan = publisher.plan(materialized, projection, None)
    user_root = root / "synthetic-user"
    user_memory = user_root / ".claude" / "CLAUDE.md"
    user_memory.parent.mkdir(parents=True)
    user_memory.write_bytes(user_bytes)
    importer = ClaudeManagedImport(runtime, user_root, materialized.manifest)
    return importer, projection, user_memory, publication_plan


def _case_marker_conflict(root: Path, materialized, context) -> bool:
    block = BEGIN + b"\n@C:\\synthetic\\one.md\n" + END + b"\n"
    importer, _, user, publication_plan = _setup_import_case(
        root,
        materialized,
        block + block,
        context,
    )
    try:
        importer.plan(
            user,
            publication_plan,
            hashlib.sha256(user.read_bytes()).hexdigest(),
        )
    except ClaudeContractError:
        return True
    return False


def _case_outside_preservation(root: Path, materialized, context) -> bool:
    before = (
        b"\xef\xbb\xbfHeader\r\n<!-- BEGIN EML TOOL -->\nbody\r\n"
        b"<!-- END EML TOOL -->\nTail\r\n"
    )
    importer, _, user, publication_plan = _setup_import_case(
        root,
        materialized,
        before,
        context,
    )
    prepared = importer.plan(user, publication_plan, hashlib.sha256(before).hexdigest())
    receipt = importer.apply(prepared, context).import_receipt
    after = user.read_bytes()
    return receipt.outside_bytes_preserved and after.startswith(before)


def _case_stale_user(root: Path, materialized, context) -> bool:
    importer, _, user, publication_plan = _setup_import_case(
        root,
        materialized,
        b"old",
        context,
    )
    prepared = importer.plan(user, publication_plan, hashlib.sha256(b"old").hexdigest())
    user.write_bytes(b"newer")
    try:
        importer.apply(prepared, context)
    except StaleTargetError:
        return user.read_bytes() == b"newer"
    return False


def _publisher_case(root: Path, materialized, before: bytes):
    runtime = root / "runtime"
    target = runtime / "claude" / "MNEME_GLOBAL.md"
    target.parent.mkdir(parents=True)
    target.write_bytes(before)
    return runtime, target


def _case_stale_projection(root: Path, materialized, context) -> bool:
    runtime, target = _publisher_case(root, materialized, b"old")
    publisher = ClaudeProjectionPublisher(runtime)
    prepared = publisher.plan(materialized, target, hashlib.sha256(b"old").hexdigest())
    target.write_bytes(b"changed")
    try:
        publisher.publish(prepared, context)
    except StaleTargetError:
        return target.read_bytes() == b"changed"
    return False


def _case_crash_before(root: Path, materialized, context) -> bool:
    runtime, target = _publisher_case(root, materialized, b"old")
    publisher = ClaudeProjectionPublisher(runtime, crash_at="before_replace")
    prepared = publisher.plan(materialized, target, hashlib.sha256(b"old").hexdigest())
    try:
        publisher.publish(prepared, context)
    except InjectedCrash:
        return target.read_bytes() == b"old"
    return False


def _case_crash_after(root: Path, materialized, context) -> bool:
    runtime, target = _publisher_case(root, materialized, b"old")
    publisher = ClaudeProjectionPublisher(runtime, crash_at="after_replace")
    prepared = publisher.plan(materialized, target, hashlib.sha256(b"old").hexdigest())
    try:
        publisher.publish(prepared, context)
    except InjectedCrash:
        return target.read_bytes() == materialized.content
    return False


def _case_private_and_runtime_scan(root: Path, materialized) -> bool:
    runtime = root / "runtime"
    target = runtime / "AI_HOME" / "projection.md"
    runtime.mkdir(parents=True)
    try:
        ClaudeProjectionPublisher(runtime).plan(
            materialized,
            target,
            None,
        )
    except ClaudePathBoundaryError:
        return _runtime_ast_scan_is_clean()
    return False


def _runtime_ast_scan_is_clean() -> bool:
    forbidden_modules = {"requests", "httpx", "socket", "urllib", "subprocess"}
    for name in _RUNTIME_SCAN_NAMES:
        path = Path(__file__).parent / name
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(
                alias.name.split(".")[0] in forbidden_modules for alias in node.names
            ):
                return False
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.split(".")[0] in forbidden_modules
            ):
                return False
    return True


def _case_model_authority(root: Path) -> bool:
    root.mkdir()
    activation, plan, authorization = _synthetic_operation(root / "activation")
    raw = authorization.to_dict()
    raw["source_role"] = "assistant"
    forged = LocalManualWriteAuthorization(canonical_json_bytes(raw))
    try:
        activation.apply_synthetic(plan, forged)
    except ClaudeContractError:
        return not plan.config.sandbox_root.exists()
    return False


def _case_concurrent_reader(root: Path, materialized, context) -> bool:
    importer, _, user, publication_plan = _setup_import_case(
        root,
        materialized,
        b"old",
        context,
    )
    prepared = importer.plan(user, publication_plan, hashlib.sha256(b"old").hexdigest())
    handles = [user.open("rb") for _ in range(4)] if os.name == "nt" else []
    try:
        try:
            importer.apply(prepared, context)
        except AtomicReplaceUnavailableError:
            return os.name == "nt" and user.read_bytes() == b"old"
    finally:
        for handle in handles:
            handle.close()
    after = user.read_bytes()
    return after.startswith(b"old") and BEGIN in after and END in after


def _remove_exact_synthetic_run(run_root: Path, owner_root: Path) -> None:
    resolved_run = run_root.resolve(strict=True)
    resolved_owner = owner_root.resolve(strict=True)
    if resolved_run.parent != resolved_owner or resolved_run.name != "mneme-cgm-repeat":
        raise ClaudeContractError("refusing to remove unexpected acceptance run root")
    shutil.rmtree(resolved_run)
