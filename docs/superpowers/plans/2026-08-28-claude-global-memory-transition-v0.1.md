# MNEME Claude Global Memory Transition v0.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` inline. Execute tasks sequentially with TDD.
> Lares is the read-only Claude-client reviewer after Task 4 and at the final
> candidate gate; do not give another worker shared write authority.

**Goal:** Build a provider-neutral, global-only MNEME canonical-memory slice
that emits a deterministic 16,000-byte-or-smaller Claude Code user-memory
projection through one byte-preserving managed `@import` block.

**Architecture:** Harden the existing file-first core before adding the Claude
consumer: package one canonical schema set, serialize writers, and reject
record-ID reuse. Add closed Claude request/result/receipt contracts, a read-only
global adapter, atomic projection publisher, byte-preserving managed-import
editor and synthetic acceptance runner. Real global records, runtime paths and
the real Claude user-memory mutation remain a separately authorized local
activation after this code candidate is accepted.

**Tech Stack:** Python 3.11+, JSON Schema Draft 2020-12, `importlib.resources`,
standard-library Windows/POSIX file locks, pytest, setuptools, UTF-8 canonical
JSON and existing MNEME MLF-RM/0.1 routes/projection/store.

**Spec:**
`docs/superpowers/specs/2026-08-28-claude-global-memory-transition-v0.1-design.md`

## Global Constraints

- Exact accepted spec commit:
  `6d64c1885fe43186c38f61ade19499334036d3fe`.
- Exact spec tree:
  `d9b5500f398916949bb0fd65985503eb63d56f05`.
- Exact spec SHA-256:
  `C01F095DCBA2EBAFA19194E29E3D5FA836435CDAF776D0ED2936426373F2E67E`.
- Canonical memory profile remains `MLF-RM/0.1`; Claude transition profile is
  `mneme.claude-global/0.1`.
- Allowed canonical scopes are exactly `global/core`,
  `global/collaboration`, `global/verification` and `global/machine`.
- Claude projection hard maximum is exactly 16,000 UTF-8 bytes and includes
  only whole records.
- Claude is a read-only consumer. Model/relay output is never commit authority.
- No identity route, private Residence, provider/network/MCP/Bridge call,
  automatic writeback, background service, CPS mutation or Codex activation.
- Code and tests use synthetic paths and records only. Do not read or modify the
  real Claude file or create the real runtime root in this implementation plan.
- Do not push, PR, merge, release, deploy or publish.
- Use `python -B` or `PYTHONDONTWRITEBYTECODE=1` for verification so generated
  bytecode does not dirty the worktree.
- Helper builders shown in snippets (`record`, `tx`, `request`, `store`,
  `projection`, `plan`, `authorization`, `fixture_file`) are deterministic
  functions local to the named test file, not public production APIs.

## Writer/reviewer matrix

| Slice | Primary writer | Required reviewer | Reviewer authority |
|---|---|---|---|
| Tasks 1–4 | current task-local 溯棧 | Claude-side Lares after Task 4 | read-only Claude-client review |
| Tasks 5–9 | current task-local 溯棧 | Claude-side Lares at final candidate | read-only final review |

Lares review is evidence, not Neo.K activation authority. A Bridge outage uses
the existing non-private shared handoff directory and never authorizes a new
Claude worker or private-memory read.

---

### Task 1: Canonical Installed Schema Resources and LF Policy

**Files:**
- Create: `.gitattributes`
- Create: `src/mneme/schemas/__init__.py`
- Move: `schemas/*.schema.json` to `src/mneme/schemas/*.schema.json`
- Modify: `pyproject.toml`
- Modify: `src/mneme/records.py`
- Modify: `src/mneme/transactions.py`
- Modify: `src/mneme/routes.py`
- Modify: `src/mneme/markdown_profile.py`
- Modify: `src/mneme/cps/models.py`
- Modify: `src/mneme/cps/factorization.py`
- Modify: `src/mneme/cps/seed.py`
- Modify: tests that open `schemas/` directly
- Create: `tests/test_packaged_schemas.py`

**Interfaces:**
- Produces `mneme.schemas.read_schema_bytes(name: str) -> bytes`.
- Produces `mneme.schemas.read_schema(name: str) -> dict[str, object]`.
- Produces `mneme.schemas.schema_sha256(name: str) -> str`.
- Every runtime validator consumes the same installed resource bytes.

- [ ] **Step 1: Write installed-resource RED tests**

```python
def test_all_runtime_schemas_are_single_installed_resources(tmp_path):
    wheel = build_wheel(tmp_path)
    install = install_wheel(wheel, tmp_path / "install")
    observed = isolated_python(
        install,
        "from mneme.schemas import schema_sha256; "
        "from mneme.records import MemoryRecord; "
        "print(schema_sha256('memory-record-0.1.schema.json'))",
    )
    assert observed.returncode == 0, observed.stderr
    assert observed.stdout.strip() == source_schema_sha256(
        "memory-record-0.1.schema.json"
    )


def test_wheel_has_no_second_schema_body(tmp_path):
    wheel = build_wheel(tmp_path)
    assert wheel_schema_names(wheel) == source_schema_names()
    assert not repository_root_schema_directory().exists()
```

- [ ] **Step 2: Run RED and prove the current wheel failure**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
python -B -m pytest -q tests/test_packaged_schemas.py
```

Expected: FAIL because installed wheel imports cannot find root-level schemas.

- [ ] **Step 3: Move the canonical assets and implement the resource loader**

```python
# src/mneme/schemas/__init__.py
from __future__ import annotations

import hashlib
import json
from importlib.resources import files


def read_schema_bytes(name: str) -> bytes:
    if "/" in name or "\\" in name or not name.endswith(".schema.json"):
        raise ValueError("schema name must be one local schema filename")
    return files(__package__).joinpath(name).read_bytes()


def read_schema(name: str) -> dict[str, object]:
    value = json.loads(read_schema_bytes(name).decode("utf-8"))
    if not isinstance(value, dict):
        raise TypeError("schema resource must be an object")
    return value


def schema_sha256(name: str) -> str:
    return hashlib.sha256(read_schema_bytes(name)).hexdigest()
```

Add exact package data and LF policy:

```toml
[tool.setuptools.package-data]
mneme = ["schemas/*.json"]
```

```gitattributes
* text=auto
*.py text eol=lf
*.json text eol=lf
*.md text eol=lf
*.toml text eol=lf
```

Update every validator to call `read_schema()`; do not keep fallback filesystem
searches or copied bodies.

- [ ] **Step 4: Run schema, full and clean-wheel GREEN gates**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
python -B -m pytest -q tests/test_packaged_schemas.py tests/test_records.py tests/test_transactions.py tests/test_routes.py tests/test_markdown_profile.py tests/test_cps_models.py
python -B -m pytest -q
```

Expected: all pass; clean installed imports work; source and wheel schema hashes
match.

- [ ] **Step 5: Commit Task 1**

```text
git add .gitattributes pyproject.toml src/mneme/schemas src/mneme tests
git add -u -- schemas
git commit -m "fix: package canonical MNEME schemas"
```

---

### Task 2: Single-Writer Commit Lock and Record-ID Conflicts

**Files:**
- Create: `src/mneme/writer_lock.py`
- Modify: `src/mneme/store.py`
- Modify: `src/mneme/errors.py`
- Modify: `tests/test_store.py`
- Create: `tests/test_store_concurrency.py`

**Interfaces:**
- Produces `StoreWriterLock(path: Path, *, blocking: bool = False)` context
  manager.
- `MemoryStore.commit(tx)` acquires the internal writer lock before reading
  current HEAD and holds it through post-write readback.
- Produces `MemoryStore.validate_record_id_population(tx) -> None`.
- Adds typed `StoreWriterBusyError` and `RecordIdConflictError`.

- [ ] **Step 1: Write concurrency and record-ID RED tests**

```python
def test_two_writers_at_genesis_return_exactly_one_success(tmp_path):
    root = tmp_path / "memory.mlfdir"
    MemoryStore(root).initialize()
    outcomes = run_two_commits_simultaneously(
        root,
        tx("a", expected_head="GENESIS", record_id="record-a"),
        tx("b", expected_head="GENESIS", record_id="record-b"),
    )
    assert count_success(outcomes) == 1
    assert count_conflict_or_busy(outcomes) == 1
    assert len(list(MemoryStore(root).iter_committed_transactions())) == 1


def test_existing_record_id_cannot_be_reused(tmp_path):
    selected = store(tmp_path)
    first = selected.commit(tx("a", record_id="record-1"))
    with pytest.raises(RecordIdConflictError):
        selected.commit(
            tx(
                "b",
                expected_head=first.new_head,
                record_id="record-1",
                text="different",
            )
        )


def test_duplicate_record_id_inside_one_transaction_is_rejected(tmp_path):
    with pytest.raises(RecordIdConflictError):
        store(tmp_path).commit(tx_with_duplicate_record_ids())
```

- [ ] **Step 2: Run RED and retain the two-success counterexample output**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
python -B -m pytest -q tests/test_store_concurrency.py tests/test_store.py
```

Expected: the concurrent test shows the current two-success/one-reachable bug;
record-ID tests fail because duplicates are accepted.

- [ ] **Step 3: Implement cross-platform lock and closed ID validation**

```python
class StoreWriterLock:
    def __enter__(self) -> "StoreWriterLock":
        self._handle = self._path.open("a+b")
        _lock_one_byte(self._handle, blocking=self._blocking)
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        _unlock_one_byte(self._handle)
        self._handle.close()
```

Use `msvcrt.locking` on Windows and `fcntl.flock` on POSIX. Do not delete the
lock file. The RED uses two spawned processes, not only two threads. Create only
the store directory and lock file before acquisition; initialize/read canonical
HEAD while the lock is held. Hold the lock around the complete existing commit
sequence and run a final reachable-head/readback verification before returning
success.

Build the reachable record-ID index from `iter_committed_records()` while the
lock is held. Any reused ID is an error even when record bytes are equal.

- [ ] **Step 4: Run RED populations, store suite and full suite GREEN**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
python -B -m pytest -q tests/test_store_concurrency.py tests/test_store.py
python -B -m pytest -q
```

Expected: exactly one concurrent success; duplicates fail before transaction or
receipt publication; existing store behavior remains green.

- [ ] **Step 5: Commit Task 2**

```text
git add src/mneme/writer_lock.py src/mneme/store.py src/mneme/errors.py tests/test_store.py tests/test_store_concurrency.py
git commit -m "fix: serialize MNEME writers and record IDs"
```

---

### Task 3: Closed Claude Transition Contracts

**Files:**
- Create: `src/mneme/claude_contracts.py`
- Modify: `src/mneme/errors.py`
- Create: `src/mneme/schemas/claude-global-projection-request-0.1.schema.json`
- Create: `src/mneme/schemas/claude-global-projection-manifest-0.1.schema.json`
- Create: `src/mneme/schemas/claude-publication-plan-0.1.schema.json`
- Create: `src/mneme/schemas/claude-publication-receipt-0.1.schema.json`
- Create: `src/mneme/schemas/claude-import-plan-0.1.schema.json`
- Create: `src/mneme/schemas/claude-import-receipt-0.1.schema.json`
- Create: `src/mneme/schemas/local-manual-write-authorization-0.1.schema.json`
- Create: `tests/test_claude_contracts.py`

**Interfaces:**
- Produces frozen, digest-bound `ClaudeGlobalProjectionRequest`.
- Produces frozen, digest-bound `ClaudeGlobalProjectionManifest`.
- Produces `ClaudePublicationPlan`, `ClaudePublicationReceipt`.
- Produces `ClaudeImportPlan`, `ClaudeImportReceipt`.
- Produces `LocalManualWriteAuthorization`.
- Adds `ClaudeContractError` and `ManualAuthorityError` in `mneme.errors`.
- Every type exposes `sealed()`, `from_dict()`, `to_dict()`, `digest` and
  `verify()`.

- [ ] **Step 1: Write contract RED tests**

```python
def test_request_is_global_only_and_has_exact_hard_budget():
    valid = ClaudeGlobalProjectionRequest.from_dict(request())
    assert valid.byte_budget == 16000
    for changed in (
        request(byte_budget=16001),
        request(allowed_scope_paths=["identity/example"]),
        request(route_id="route://identity/example/bootstrap"),
    ):
        with pytest.raises(ClaudeContractError):
            ClaudeGlobalProjectionRequest.from_dict(changed)


def test_receipts_cannot_claim_model_authority():
    with pytest.raises(ClaudeContractError):
        LocalManualWriteAuthorization.from_dict(
            authorization(principal_ref="model:claude")
        )
```

- [ ] **Step 2: Run RED**

Run: `python -B -m pytest -q tests/test_claude_contracts.py`

Expected: import errors because contracts and schemas do not exist.

- [ ] **Step 3: Implement canonical contract base and exact schema semantics**

```python
@dataclass(frozen=True)
class _ClaudeContract:
    _canonical: bytes

    @classmethod
    def sealed(cls, material: Mapping[str, object]):
        value = canonical_object(material)
        value[cls.digest_field] = sha256_domain(cls.domain, canonical_json_bytes(value))
        return cls.from_dict(value)
```

Use closed schemas, exact global-scope enums, unique required IDs, exact
16,000 maximum, ref/digest atomic pairs and explicit nonclaims. Authority
status is `active | revoked | expired | suspended`; only
`principal:neo.k` is accepted by the local profile.

- [ ] **Step 4: Run contract and installed-resource GREEN gates**

Run:

```powershell
python -B -m pytest -q tests/test_claude_contracts.py tests/test_packaged_schemas.py
```

Expected: pass with strict unknown-field/digest/cross-binding negatives.

- [ ] **Step 5: Commit Task 3**

```text
git add src/mneme/claude_contracts.py src/mneme/errors.py src/mneme/schemas tests/test_claude_contracts.py
git commit -m "feat: define Claude global memory contracts"
```

---

### Task 4: Provider-Neutral Claude Global Read Adapter

**Files:**
- Create: `src/mneme/adapters/claude.py`
- Modify: `src/mneme/adapters/__init__.py`
- Modify: `src/mneme/errors.py`
- Create: `tests/test_claude_adapter.py`

**Interfaces:**
- Produces `ClaudeGlobalMemoryAdapter(store: MemoryStore, route: Route)`.
- Produces `materialize(request: ClaudeGlobalProjectionRequest) ->
  ClaudeGlobalProjectionResult`.
- Result carries content bytes plus sealed manifest; it has no write method.
- Adds `ClaudeRouteError` and `RequiredRecordOmittedError` in `mneme.errors`.

- [ ] **Step 1: Write global-scope, required-record and budget RED tests**

```python
def test_adapter_includes_only_declared_global_scopes(tmp_path):
    selected = adapter_with_records(
        tmp_path,
        record("core", "global/core"),
        record("identity", "identity/example"),
        record("project", "project/example"),
    )
    result = selected.materialize(request(required_record_ids=["core"]))
    assert result.manifest.included_record_ids == ("core",)
    assert omission_reason(result, "identity") == "scope_not_allowed"
    assert omission_reason(result, "project") == "scope_not_allowed"


def test_required_record_omission_refuses_projection(tmp_path):
    selected = adapter_with_records(tmp_path, oversized_required_record())
    with pytest.raises(RequiredRecordOmittedError):
        selected.materialize(request(required_record_ids=["required-large"]))


def test_projection_is_deterministic_and_never_exceeds_16000(tmp_path):
    first = adapter(tmp_path).materialize(request())
    second = adapter(tmp_path).materialize(request())
    assert first.content == second.content
    assert first.manifest.digest == second.manifest.digest
    assert len(first.content) <= 16000
```

- [ ] **Step 2: Run RED**

Run: `python -B -m pytest -q tests/test_claude_adapter.py`

Expected: missing adapter/result errors.

- [ ] **Step 3: Implement route validation and whole-record materialization**

```python
class ClaudeGlobalMemoryAdapter:
    def materialize(self, request: ClaudeGlobalProjectionRequest):
        request.verify()
        if self._route.route_id != "route://global/tier0":
            raise ClaudeRouteError("Claude route must be global tier0")
        records = tuple(self._store.iter_committed_records())
        allowed = tuple(
            record for record in records
            if scope_path(record) in request.allowed_scope_paths
        )
        projection = project_markdown(
            allowed,
            source_head=self._store.head(),
            route_id=request.route_id,
            byte_budget=request.byte_budget,
            omissions=closed_scope_omissions(records, allowed),
        )
        return seal_claude_result(request, projection)
```

Check every required record after projection. The result never exposes private
path discovery, identity inference or writeback.

- [ ] **Step 4: Run adapter, route, SOACR and full GREEN suites**

Run:

```powershell
python -B -m pytest -q tests/test_claude_adapter.py tests/test_routes.py tests/test_projection.py tests/test_soacr_adapter.py
python -B -m pytest -q
```

Expected: all pass with exact deterministic bytes and no scope leakage.

- [ ] **Step 5: Commit Task 4 and stop for Lares read-only review**

```text
git add src/mneme/adapters/claude.py src/mneme/adapters/__init__.py src/mneme/errors.py tests/test_claude_adapter.py
git commit -m "feat: add Claude global read adapter"
```

Checkpoint exact head/tree, focused/full tests, installed resources and zero
private/network/provider effects. Send the durable checkpoint to Lares; do not
start Task 5 until the required Claude-client review returns no blocking issue.

---

### Task 5: Atomic Projection Publisher

**Files:**
- Create: `src/mneme/claude_projection.py`
- Modify: `src/mneme/errors.py`
- Create: `tests/test_claude_projection.py`

**Interfaces:**
- Produces `ClaudeProjectionPublisher.plan(result, target, expected_digest)`.
- Produces `ClaudeProjectionPublisher.publish(plan, authorization) ->
  ClaudePublicationReceipt`.
- Planning is read-only; publish requires exact target pre-image and local
  manual authority.
- Adds `StaleTargetError` and `ClaudePathBoundaryError` in `mneme.errors`.

- [ ] **Step 1: Write stale-target/crash/path RED tests**

```python
def test_stale_projection_target_refuses_without_mutation(tmp_path):
    target = fixture_file(tmp_path, b"old")
    selected_plan = publisher(tmp_path).plan(
        projection(), target, sha256_hex(b"old")
    )
    target.write_bytes(b"changed")
    with pytest.raises(StaleTargetError):
        publisher(tmp_path).publish(selected_plan, authorization())
    assert target.read_bytes() == b"changed"


def test_crash_before_replace_retains_old_projection(tmp_path):
    target = fixture_file(tmp_path, b"old")
    with pytest.raises(InjectedCrash):
        publisher(tmp_path, crash_at="before_replace").publish(
            plan(target), authorization()
        )
    assert target.read_bytes() == b"old"


def test_private_temp_repo_and_network_paths_are_refused(tmp_path):
    for target in forbidden_targets(tmp_path):
        with pytest.raises(ClaudePathBoundaryError):
            publisher(tmp_path).plan(projection(), target, None)
```

- [ ] **Step 2: Run RED**

Run: `python -B -m pytest -q tests/test_claude_projection.py`

Expected: missing publisher and error types.

- [ ] **Step 3: Implement explicit-root CAS publication**

Use caller-supplied allowed runtime root, no path discovery, same-volume temp,
flush/fsync, atomic replace, exact post-readback and create-new receipt. Reject
links, hardlinks, ADS, private markers, Git roots and target escapes before
content reads/writes. Do not retry automatically.

- [ ] **Step 4: Run RED populations and GREEN publisher suite**

Run:

```powershell
python -B -m pytest -q tests/test_claude_projection.py
```

Expected: atomic positive passes; stale/crash/path/tamper populations preserve
the old target and produce no success receipt.

- [ ] **Step 5: Commit Task 5**

```text
git add src/mneme/claude_projection.py src/mneme/errors.py tests/test_claude_projection.py
git commit -m "feat: publish bounded Claude projections atomically"
```

---

### Task 6: Byte-Preserving Managed Claude Import

**Files:**
- Create: `src/mneme/claude_import.py`
- Modify: `src/mneme/errors.py`
- Create: `tests/fixtures/claude/user-memory-other-blocks-mixed-eol.md`
- Create: `tests/test_claude_import.py`

**Interfaces:**
- Produces `ClaudeManagedImport.plan(user_memory, projection, expected_digest)`.
- Produces `ClaudeManagedImport.apply(plan, authorization) ->
  ClaudeImportReceipt`.
- The managed block delimiters are exact constants and never generic HTML
  comment patterns.
- Adds `ManagedBlockConflictError` in `mneme.errors`.

- [ ] **Step 1: Write byte-preservation and marker RED tests**

```python
def test_unrelated_managed_blocks_and_mixed_eol_are_byte_preserved(tmp_path):
    target = copy_fixture(
        tmp_path, "user-memory-other-blocks-mixed-eol.md"
    )
    before = target.read_bytes()
    result = managed_import(tmp_path).apply(
        plan_for(target, projection_path(tmp_path)), authorization()
    )
    after = target.read_bytes()
    prefix, block, suffix = split_exact_mneme_block(after)
    expected_prefix, expected_suffix = expected_outside_bytes(before)
    assert prefix == expected_prefix
    assert suffix == expected_suffix
    assert block == canonical_lf_mneme_block(projection_path(tmp_path))
    assert result.outside_bytes_preserved is True


@pytest.mark.parametrize("fixture", ["partial-begin.md", "partial-end.md", "duplicate.md", "nested.md"])
def test_malformed_mneme_markers_refuse_without_mutation(tmp_path, fixture):
    target = copy_fixture(tmp_path, fixture)
    before = target.read_bytes()
    with pytest.raises(ManagedBlockConflictError):
        managed_import(tmp_path).apply(
            plan_for(target, projection_path(tmp_path)), authorization()
        )
    assert target.read_bytes() == before
```

- [ ] **Step 2: Run RED**

Run: `python -B -m pytest -q tests/test_claude_import.py`

Expected: missing import editor and fixtures.

- [ ] **Step 3: Implement exact-byte parser and CAS editor**

Parse raw bytes, not normalized text. Match only:

```python
BEGIN = b"<!-- BEGIN MNEME GLOBAL PROJECTION v0.1 -->"
END = b"<!-- END MNEME GLOBAL PROJECTION v0.1 -->"
```

Preserve all preexisting bytes outside the block, including BOM state and mixed
line endings. Insert one canonical-LF block at the end when absent. Replacement
requires exact pre-image digest and atomic readback. Unrelated `BEGIN/END EML`
blocks are ordinary preserved bytes.

- [ ] **Step 4: Run import, publisher and cross-platform GREEN gates**

Run:

```powershell
python -B -m pytest -q tests/test_claude_import.py tests/test_claude_projection.py
```

Expected: CGM-013 through CGM-020 plus CGM-025 pass; actual user memory is
never opened.

- [ ] **Step 5: Commit Task 6**

```text
git add src/mneme/claude_import.py src/mneme/errors.py tests/fixtures/claude tests/test_claude_import.py
git commit -m "feat: manage Claude memory import without byte loss"
```

---

### Task 7: Synthetic Activation Orchestrator and CLI

**Files:**
- Create: `src/mneme/claude_activation.py`
- Create: `src/mneme/claude_cli.py`
- Create: `scripts/mneme_claude_global.py`
- Create: `tests/test_claude_activation.py`
- Create: `tests/test_claude_cli.py`

**Interfaces:**
- Produces `ClaudeGlobalActivation.plan(config, transaction, request) ->
  activation_plan`.
- Produces `ClaudeGlobalActivation.apply_synthetic(plan, authorization) ->
  activation_receipt`.
- CLI commands: `verify`, `plan`, `apply-synthetic`, `status`.
- `scripts/mneme_claude_global.py` is a thin source-tree wrapper around
  `mneme.claude_cli.main`; Task 9 installs the same entrypoint.
- No command mutates the real runtime root or real Claude user memory in this
  implementation plan.

- [ ] **Step 1: Write authority/order/no-real-target RED tests**

```python
def test_model_or_relay_cannot_authorize_activation(tmp_path):
    for source_role in ("assistant", "relay"):
        with pytest.raises(ManualAuthorityError):
            activation(tmp_path).apply_synthetic(
                plan(tmp_path), authorization(source_role=source_role)
            )


def test_real_target_is_hard_stopped_in_code_candidate(tmp_path):
    result = run_cli("apply-synthetic", *real_target_arguments(tmp_path))
    assert result.exit_code == 2
    assert result.json["reason_codes"] == ["real_activation_not_authorized"]


def test_activation_order_binds_store_projection_and_import_receipts(tmp_path):
    receipt = activation(tmp_path).apply_synthetic(
        plan(tmp_path), authorization()
    )
    assert receipt.steps == (
        "canonical_commit",
        "projection_publish",
        "managed_import",
    )
    assert receipt.production_wave_run == "NOT_APPLICABLE"
    assert receipt.claude_memory_readback == "NOT_RUN"
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -B -m pytest -q tests/test_claude_activation.py tests/test_claude_cli.py
```

Expected: missing orchestrator/CLI.

- [ ] **Step 3: Implement synthetic-only orchestration and typed exits**

Validate all plans and authority before the first write. Synthetic apply uses
one disposable root and fixture Claude file. Transport/input errors exit 1;
readable policy/authority/boundary refusals exit 2; success exits 0. CLI output
is canonical JSON and contains no memory body.

- [ ] **Step 4: Run activation/CLI and existing acceptance GREEN gates**

Run:

```powershell
python -B -m pytest -q tests/test_claude_activation.py tests/test_claude_cli.py
python -B scripts/validate_fresh_memory_core.py --output "$env:TEMP/mneme-cgm-fresh.json"
python -B scripts/validate_memory_markdown_profile.py --output "$env:TEMP/mneme-cgm-md.json"
python -B scripts/validate_cognitive_persistence_semantics.py --output "$env:TEMP/mneme-cgm-cps.json"
```

Expected: pass; all legacy profile fingerprints remain exact.

- [ ] **Step 5: Commit Task 7**

```text
git add src/mneme/claude_activation.py src/mneme/claude_cli.py scripts/mneme_claude_global.py tests/test_claude_activation.py tests/test_claude_cli.py
git commit -m "feat: orchestrate synthetic Claude global activation"
```

---

### Task 8: CGM Acceptance Matrix and Effect Evidence

**Files:**
- Create: `src/mneme/claude_acceptance.py`
- Create: `scripts/validate_claude_global_memory.py`
- Create: `tests/fixtures/claude/expected-effects.json`
- Create: `tests/test_claude_acceptance.py`

**Interfaces:**
- Produces `validate_claude_global_memory(root: Path) ->
  ClaudeGlobalAcceptanceReport`.
- Executes CGM-001 through CGM-022 and CGM-025.
- Records CGM-023, CGM-024, CGM-026 and CGM-027 as
  `NOT_RUN_LOCAL_ACTIVATION_REQUIRED`.

- [ ] **Step 1: Write completeness, determinism and injected-effect RED tests**

```python
def test_cgm_acceptance_has_exact_case_ownership(tmp_path):
    report = validate_claude_global_memory(tmp_path)
    synthetic = {f"CGM-{index:03d}" for index in range(1, 23)} | {"CGM-025"}
    local = {"CGM-023", "CGM-024", "CGM-026", "CGM-027"}
    assert {case.case_id for case in report.cases} == synthetic | local
    assert all(case.executed and case.passed for case in report.cases if case.case_id in synthetic)
    assert {
        case.case_id: case.status for case in report.cases if case.case_id in local
    } == {case_id: "NOT_RUN_LOCAL_ACTIVATION_REQUIRED" for case_id in local}


def test_injected_forbidden_effect_turns_acceptance_red(tmp_path):
    report = validate_claude_global_memory(
        tmp_path, injected_effect="private_read"
    )
    assert report.status == "FAIL"
    assert report.effects.private_reads == 1
```

- [ ] **Step 2: Run RED**

Run: `python -B -m pytest -q tests/test_claude_acceptance.py`

Expected: missing acceptance module/script/fixture.

- [ ] **Step 3: Implement two-run deterministic synthetic acceptance**

Run every synthetic case twice with supplied fixture IDs. Compare report,
projection, manifest, store head and receipt digests. Instrument fixture reads,
synthetic writes, private/production reads/writes, network, provider, MCP,
Bridge and external CLI. Positive refs/counts must equal the independent
fixture; every injected forbidden effect must turn the gate red.

- [ ] **Step 4: Run acceptance script and full suite GREEN**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
python -B -m pytest -q tests/test_claude_acceptance.py
python -B scripts/validate_claude_global_memory.py --output "$env:TEMP/mneme-cgm.json"
python -B -m pytest -q
```

Expected: all synthetic CGM cases pass; four local cases are explicit NOT_RUN;
repeated digests match; forbidden effects are zero in the positive.

- [ ] **Step 5: Commit Task 8**

```text
git add src/mneme/claude_acceptance.py scripts/validate_claude_global_memory.py tests/fixtures/claude/expected-effects.json tests/test_claude_acceptance.py
git commit -m "test: validate Claude global memory transition"
```

---

### Task 9: Packaging, CI, Runbook and Final Candidate Gate

**Files:**
- Modify: `pyproject.toml` version `0.3.0a1` to `0.4.0a1`
- Create: `.github/workflows/claude-global-memory.yml`
- Create: `docs/runtime/CLAUDE_GLOBAL_MEMORY_TRANSITION_V0.1.md`
- Create: `tests/test_claude_packaging.py`

**Interfaces:**
- Produces an installed `mneme-memory==0.4.0a1` local candidate.
- Produces a public, synthetic-only runbook and exact evidence manifest.
- Does not publish the wheel or activate the real Claude consumer.
- Adds installed entrypoint
  `mneme-claude-global = "mneme.claude_cli:main"`.

- [ ] **Step 1: Write final installed-wheel and runbook RED tests**

```python
def test_clean_installed_candidate_runs_all_claude_entrypoints(tmp_path):
    install = install_clean_wheel(tmp_path)
    assert isolated_imports(install, [
        "mneme.schemas",
        "mneme.adapters.claude",
        "mneme.claude_projection",
        "mneme.claude_import",
        "mneme.claude_activation",
    ])
    assert installed_cli(install, "verify").exit_code == 0


def test_runbook_preserves_activation_nonclaims():
    text = runbook_text()
    assert "real_claude_user_memory = NOT_TOUCHED" in text
    assert "private_residence = NOT_READ" in text
    assert "claude_memory_readback = NOT_RUN" in text
```

- [ ] **Step 2: Run RED**

Run: `python -B -m pytest -q tests/test_claude_packaging.py`

Expected: version/resources/runbook/workflow missing.

- [ ] **Step 3: Add candidate metadata, CI and activation boundary runbook**

CI runs Windows and Ubuntu focused/full/acceptance/clean-wheel gates. The
runbook explains the later local activation sequence, exact manual authority,
real path evidence, 16,000-byte empirical import test, `/memory` readback and
long-running-session restart/reload state. It contains no real user paths,
memory bodies, credentials or resident identifiers.

- [ ] **Step 4: Run final candidate verification**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
python -B -m pytest -q -rs
python -B scripts/validate_fresh_memory_core.py --output "$env:TEMP/mneme-final-fresh.json"
python -B scripts/validate_memory_markdown_profile.py --output "$env:TEMP/mneme-final-md.json"
python -B scripts/validate_cognitive_persistence_semantics.py --output "$env:TEMP/mneme-final-cps.json"
python -B scripts/validate_claude_global_memory.py --output "$env:TEMP/mneme-final-cgm.json"
python -B -m compileall -q src tests
git diff --check 84b9b0ee94115902d7a9e6acfdc48372e60fd673..HEAD
```

Build a clean wheel with no build isolation/network, install to a new temp
target, rerun installed imports and CLI, and record wheel/schema bytes/SHA256.
Remove generated bytecode before the final clean-state check.

Expected: every test/gate passes; legacy fingerprints match; CGM local cases
remain NOT_RUN; worktree clean after commit; no real external effect.

- [ ] **Step 5: Commit Task 9**

```text
git add pyproject.toml .github/workflows/claude-global-memory.yml docs/runtime/CLAUDE_GLOBAL_MEMORY_TRANSITION_V0.1.md tests/test_claude_packaging.py
git commit -m "docs: record Claude global memory candidate"
```

- [ ] **Step 6: Stop for final Lares review**

Provide exact head/tree, full/focused tests, four acceptance reports, installed
wheel hashes, source/installed schema hashes, effect evidence and clean state.
Do not write the real runtime root or Claude user memory. After Lares and Neo.K
accept the code candidate, write a separate local activation plan for
CGM-023/024/026/027 and the first exact global transaction.

## Spec coverage map

- Provider-neutral ownership/global-only scopes: Tasks 3 and 4.
- Installed schema resource repair and LF stability: Task 1.
- Single-writer and record-ID counterexamples: Task 2.
- 16,000-byte whole-record projection and required records: Task 4.
- Atomic projection target publication: Task 5.
- Exact MNEME marker, unrelated managed blocks and mixed line endings: Task 6.
- Manual authority and no-real-target hard stop: Task 7.
- CGM-001..CGM-027 ownership, deterministic evidence and effect controls:
  Task 8.
- Installed candidate, CI, runbook and final no-live gate: Task 9.

## Post-plan local activation gate

This implementation plan ends with a synthetic code candidate. A later local
activation plan must bind:

1. exact runtime root and path boundary evidence;
2. first provider-neutral global record proposal and transaction digest;
3. Neo.K's exact manual write authorization;
4. canonical commit receipt and new MNEME head;
5. real projection target pre/post digests;
6. real Claude user-memory pre/post digests and byte-preservation proof;
7. empirical 16,000-byte import/load result;
8. `/memory` readback or explicit unmeasured status;
9. pre-activation long-running session staleness and restart/reload observation.

No code-candidate result substitutes for those nine activation facts.
