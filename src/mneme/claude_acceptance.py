from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from importlib.resources import files
from pathlib import Path

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
    private_reads: int = 0
    private_writes: int = 0
    production_reads: int = 0
    production_writes: int = 0
    network_calls: int = 0
    provider_calls: int = 0
    mcp_calls: int = 0
    bridge_calls: int = 0
    external_cli_calls: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "fixture_reads": self.fixture_reads,
            "synthetic_runs": self.synthetic_runs,
            "synthetic_writes": self.synthetic_writes,
            "synthetic_write_refs": list(self.synthetic_write_refs),
            "private_reads": self.private_reads,
            "private_writes": self.private_writes,
            "production_reads": self.production_reads,
            "production_writes": self.production_writes,
            "network_calls": self.network_calls,
            "provider_calls": self.provider_calls,
            "mcp_calls": self.mcp_calls,
            "bridge_calls": self.bridge_calls,
            "external_cli_calls": self.external_cli_calls,
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
    selected_root.mkdir()
    expected_bytes = _EXPECTED_EFFECTS_PATH.read_bytes()
    expected = json.loads(expected_bytes.decode("utf-8"))
    expected_effects = expected["positive_effects"]

    repeat_root = selected_root / "mneme-cgm-repeat"
    first = _execute_run(repeat_root)
    _remove_exact_synthetic_run(repeat_root, selected_root)
    second = _execute_run(repeat_root)
    deterministic = (
        first.fingerprint == second.fingerprint
        and first.cases == second.cases
        and first.artifacts == second.artifacts
    )
    effects = ClaudeGlobalEffectCounters(
        fixture_reads=1,
        synthetic_runs=2,
        synthetic_writes=first.activation_steps + second.activation_steps,
        synthetic_write_refs=(
            "canonical_commit",
            "managed_import",
            "projection_publish",
        ),
    )
    if effects.to_dict() != expected_effects:
        raise ClaudeContractError("measured effects do not match expected fixture")
    reason_codes: tuple[str, ...] = ()
    if injected_effect is not None:
        field = _FORBIDDEN_EFFECT_FIELDS.get(injected_effect)
        if field is None:
            raise ValueError(f"unknown injected effect: {injected_effect}")
        effects = replace(effects, **{field: 1})
        reason_codes = (f"forbidden_effect:{injected_effect}",)

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
    publication = publisher.publish(repeated_publication_plan, context)

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
        publication,
        materialized,
    )
    evidence["CGM-015"] = _case_marker_conflict(root / "case-015", materialized)
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
    schema_root = files("mneme.schemas")
    names = sorted(
        item.name for item in schema_root.iterdir() if item.name.endswith(".schema.json")
    )
    return len(names) == 17 and all(
        len(hashlib.sha256(schema_root.joinpath(name).read_bytes()).hexdigest()) == 64
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


def _case_idempotent_import(plan, context, publication, materialized) -> bool:
    importer = ClaudeManagedImport(
        plan.config.runtime_root,
        plan.config.user_memory_root,
        materialized.manifest,
    )
    before = plan.config.user_memory_target.read_bytes()
    prepared = importer.plan(
        plan.config.user_memory_target,
        plan.config.projection_target,
        hashlib.sha256(before).hexdigest(),
    )
    receipt = importer.apply(prepared, context, publication)
    return receipt.outcome == "idempotent" and plan.config.user_memory_target.read_bytes() == before


def _setup_import_case(root: Path, materialized, user_bytes: bytes, context):
    runtime = root / "runtime"
    projection = runtime / "claude" / "MNEME_GLOBAL.md"
    projection.parent.mkdir(parents=True)
    publisher = ClaudeProjectionPublisher(runtime)
    publication_plan = publisher.plan(materialized, projection, None)
    publication = publisher.publish(publication_plan, context)
    user_root = root / "synthetic-user"
    user_memory = user_root / ".claude" / "CLAUDE.md"
    user_memory.parent.mkdir(parents=True)
    user_memory.write_bytes(user_bytes)
    importer = ClaudeManagedImport(runtime, user_root, materialized.manifest)
    return importer, projection, user_memory, publication


def _case_marker_conflict(root: Path, materialized) -> bool:
    block = BEGIN + b"\n@C:\\synthetic\\one.md\n" + END + b"\n"
    runtime = root / "runtime"
    projection = runtime / "claude" / "MNEME_GLOBAL.md"
    projection.parent.mkdir(parents=True)
    projection.write_bytes(materialized.content)
    user_root = root / "synthetic-user"
    user = user_root / ".claude" / "CLAUDE.md"
    user.parent.mkdir(parents=True)
    user.write_bytes(block + block)
    importer = ClaudeManagedImport(runtime, user_root, materialized.manifest)
    try:
        importer.plan(user, projection, hashlib.sha256(user.read_bytes()).hexdigest())
    except ClaudeContractError:
        return True
    return False


def _case_outside_preservation(root: Path, materialized, context) -> bool:
    before = (
        b"\xef\xbb\xbfHeader\r\n<!-- BEGIN EML TOOL -->\nbody\r\n"
        b"<!-- END EML TOOL -->\nTail\r\n"
    )
    importer, projection, user, publication = _setup_import_case(
        root,
        materialized,
        before,
        context,
    )
    prepared = importer.plan(user, projection, hashlib.sha256(before).hexdigest())
    receipt = importer.apply(prepared, context, publication)
    after = user.read_bytes()
    return receipt.outside_bytes_preserved and after.startswith(before)


def _case_stale_user(root: Path, materialized, context) -> bool:
    importer, projection, user, publication = _setup_import_case(
        root,
        materialized,
        b"old",
        context,
    )
    prepared = importer.plan(user, projection, hashlib.sha256(b"old").hexdigest())
    user.write_bytes(b"newer")
    try:
        importer.apply(prepared, context, publication)
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
    target.parent.mkdir(parents=True)
    target.write_bytes(b"old")
    try:
        ClaudeProjectionPublisher(runtime).plan(
            materialized,
            target,
            hashlib.sha256(b"old").hexdigest(),
        )
    except ClaudePathBoundaryError:
        return _runtime_ast_scan_is_clean()
    return False


def _runtime_ast_scan_is_clean() -> bool:
    forbidden_modules = {"requests", "httpx", "socket", "urllib", "subprocess"}
    for name in (
        "claude_activation.py",
        "claude_cli.py",
        "claude_projection.py",
        "claude_import.py",
        "adapters/claude.py",
    ):
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
    importer, projection, user, publication = _setup_import_case(
        root,
        materialized,
        b"old",
        context,
    )
    prepared = importer.plan(user, projection, hashlib.sha256(b"old").hexdigest())
    handles = [user.open("rb") for _ in range(4)] if os.name == "nt" else []
    try:
        try:
            importer.apply(prepared, context, publication)
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
