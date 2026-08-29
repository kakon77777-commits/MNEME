# MNEME 0.5.0a1 Unified Profile Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce one synthetic-only `mneme-memory==0.5.0a1` candidate that combines remote-main Dry-Run/0.2 and EveMiss Markdown profile v0.2 with the independently accepted Claude global-memory consumer while preserving one MLF-RM/0.1 canonical store.

**Architecture:** Start from exact GitHub main `c21546a...`, preserve its profile/CPS/Dry-Run semantics, and replay the accepted Claude changes by semantic slice from exact `89bb150...`. Unify all validators on one installed schema-resource package, retain writer and record-ID hardening, and keep MNEME-MD, CPS, Dry-Run, Claude and SOACR as explicit profiles/sidecars/adapters rather than one monolithic mode.

**Tech Stack:** Python 3.11+, JSON Schema Draft 2020-12, `jsonschema>=4.23`, setuptools, file-first MLF-RM/0.1 storage, pytest, GitHub Actions on Windows and Ubuntu.

**Spec:** `docs/superpowers/specs/2026-08-29-mneme-unified-profile-integration-v0.5-design.md`

## Global Constraints

- Integration base is exact `c21546a263920e0f80701696e1857c203917d701` / tree `5ad5725ca685df334110b257e4004d9274e35674`.
- Accepted Claude input is exact `89bb1509f2bb96c4067d12c15094adacc2512b67` / tree `0fcac15cbccdde61013b8dfa6938ed19ca161ef8`.
- Target package version is exactly `0.5.0a1`; profile versions remain MLF-RM/0.1, MNEME-MD/0.1, MNEME-CPS/0.1, Dry-Run/0.2 and Claude Global Transition/0.1.
- Preserve one writable canonical `MemoryStore`; Markdown, CPS, Dry-Run, Claude and SOACR never become second canonical stores.
- The unified wheel contains exactly 21 canonical schema resources under `mneme.schemas`; root-level and vendored schema copies are forbidden.
- `evemiss-residence/0.1` remains frozen; `evemiss-residence/0.2` is explicit opt-in and is never inferred from prose.
- CPS and Dry-Run remain observation-only sidecars and are not automatically invoked during ordinary recall or Claude projection.
- Use synthetic fixtures only. Do not read a real Residence, real `MEMORY.md`, real `CLAUDE.md`, private source digest, resident list or provider credential.
- Do not activate, migrate, delete, tombstone, reconstruct, promote a seed/profile, push, create a PR, merge, release, deploy or publish.
- Use `PYTHONDONTWRITEBYTECODE=1` or an external `PYTHONPYCACHEPREFIX`; leave every worktree clean after each commit.
- Preserve the existing main-checkout untracked `__pycache__` directories; they are outside this isolated worktree and are not cleanup targets.
- Test-local builders shown in snippets are deterministic helpers defined in
  the named test file, never production APIs. `proposal`, `global_record`,
  `global_record_id`, `request`, `prepared_publication`, `prepared_import`,
  `bound_environment` and `synthetic_operation` create only sealed synthetic
  contracts beneath pytest `tmp_path`. `run_two_commit_processes` starts two
  local Python processes against one temporary store and returns only
  `success/conflict`. `installed_python` and `installed_candidate` build from a
  clean copied/archive tree, install to a temporary target and run with that
  target first on `sys.path`. `wrap_execute_run_with_real_synthetic_effect`,
  `observer_for` and `fixture_path` use loopback/subprocess/disposable-temp
  controls only. `imported_modules` parses AST imports without executing the
  module. `real_dialect_synthetic_fixture` points only to the checked-in
  synthetic v0.2 fixture.

## Input and reviewer matrix

| Slice | Primary writer | Required read-only reviewer | Review focus |
|---|---|---|---|
| Tasks 1–3 | current MNEME implementation task | internal inline review | schema/core/profile invariants |
| Task 4 | current MNEME implementation task | Lares | publication/import authority and exact defeated forgery |
| Tasks 5–6 | current MNEME implementation task | Lares after Task 6 | Claude client boundary and runtime effect observation |
| Tasks 7–8 | current MNEME implementation task | internal inline review | cross-profile ownership, packaging and CI |
| Task 9 | current MNEME implementation task | Lares final | exact integrated-tree adversarial acceptance |

Reviewers are read-only. No shared-file write authority is implied.

---

### Task 1: Canonical 21-Schema Installed Resource Union

**Files:**
- Create: `.gitattributes`
- Create: `src/mneme/schemas/__init__.py`
- Move: `schemas/*.schema.json` → `src/mneme/schemas/*.schema.json`
- Add from accepted Claude input: seven Claude schema resources under `src/mneme/schemas/`
- Modify: `src/mneme/records.py`
- Modify: `src/mneme/transactions.py`
- Modify: `src/mneme/routes.py`
- Modify: `src/mneme/markdown_profile.py`
- Modify: `src/mneme/cps/models.py`
- Modify: `src/mneme/cps/factorization.py`
- Modify: `src/mneme/cps/seed.py`
- Modify: `src/mneme/dry_run/policy.py`
- Modify: `src/mneme/dry_run/intents.py`
- Modify: `src/mneme/dry_run/report.py`
- Modify: `pyproject.toml`
- Create: `tests/test_packaged_schemas.py`
- Create: `tests/test_unified_schema_inventory.py`

**Interfaces:**
- Consumes: 14 remote-main schema bodies plus seven exact Claude schema bodies from `89bb150...`.
- Produces: `read_schema(name: str) -> dict[str, object]`, `schema_sha256(name: str) -> str`, and one 21-name installed resource inventory.

- [ ] **Step 1: Write the exact schema-inventory RED**

```python
EXPECTED = {
    "memory-record-0.1.schema.json",
    "transaction-0.1.schema.json",
    "route-0.1.schema.json",
    "projection-manifest-0.1.schema.json",
    "memory-markdown-profile-0.1.schema.json",
    "persistence-assessment-0.1.schema.json",
    "factorization-proposal-0.1.schema.json",
    "cognitive-seed-proposal-0.1.schema.json",
    "recomputation-reference-0.1.schema.json",
    "equivalence-contract-0.1.schema.json",
    "factorization-intent-0.1.schema.json",
    "seed-intent-0.1.schema.json",
    "persistence-policy-0.1.schema.json",
    "private-residence-dry-run-report-0.2.schema.json",
    "claude-global-projection-request-0.1.schema.json",
    "claude-global-projection-manifest-0.1.schema.json",
    "claude-publication-plan-0.1.schema.json",
    "claude-publication-receipt-0.1.schema.json",
    "claude-import-plan-0.1.schema.json",
    "claude-import-receipt-0.1.schema.json",
    "local-manual-write-authorization-0.1.schema.json",
}


def test_unified_schema_inventory_is_one_installed_resource_set():
    from importlib.resources import files

    observed = {
        item.name
        for item in files("mneme.schemas").iterdir()
        if item.name.endswith(".schema.json")
    }
    assert observed == EXPECTED
    assert not (ROOT / "schemas").exists()
```

- [ ] **Step 2: Write dry-run-loader REDs**

```python
@pytest.mark.parametrize(
    "module",
    [
        "mneme.dry_run.policy",
        "mneme.dry_run.intents",
        "mneme.dry_run.report",
    ],
)
def test_dry_run_validators_load_only_installed_resources(module, installed_python):
    result = installed_python(
        f"import {module}; from mneme.schemas import schema_sha256; "
        "print(schema_sha256('private-residence-dry-run-report-0.2.schema.json'))"
    )
    assert result.returncode == 0, result.stderr
    assert len(result.stdout.strip()) == 64
```

- [ ] **Step 3: Run the RED population**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
python -B -m pytest -q tests/test_unified_schema_inventory.py tests/test_packaged_schemas.py
```

Expected: FAIL because remote main still owns root-level schemas, has no
`mneme.schemas` package, and lacks the seven Claude resources.

- [ ] **Step 4: Create the shared loader and move existing schemas**

Implement:

```python
from __future__ import annotations

import hashlib
import json
from importlib.resources import files


def read_schema(name: str) -> dict[str, object]:
    if "/" in name or "\\" in name or not name.endswith(".schema.json"):
        raise ValueError("schema name must be one package-resource basename")
    raw = files(__package__).joinpath(name).read_bytes()
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("schema resource must decode to an object")
    return value


def schema_sha256(name: str) -> str:
    return hashlib.sha256(files(__package__).joinpath(name).read_bytes()).hexdigest()
```

Set package data:

```toml
[tool.setuptools.package-data]
mneme = ["schemas/*.json"]
```

- [ ] **Step 5: Add the exact Claude schemas and update every validator**

Use exact schema bodies from `89bb150...`. Replace every
`Path(...)/schemas/...` read with `read_schema("exact-name.schema.json")`.
Do not restore fallback path lookup.

- [ ] **Step 6: Normalize canonical text bytes**

Create:

```gitattributes
*.py text eol=lf
*.json text eol=lf
*.md text eol=lf
*.toml text eol=lf
*.yml text eol=lf
*.yaml text eol=lf
```

Add a raw-byte test asserting every schema contains LF only, has one terminal
LF, and source bytes equal installed-wheel bytes.

- [ ] **Step 7: Run schema and baseline GREEN gates**

Run:

```powershell
python -B -m pytest -q tests/test_unified_schema_inventory.py tests/test_packaged_schemas.py
python -B -m pytest -q tests/test_records.py tests/test_transactions.py tests/test_routes.py tests/test_markdown_profile.py tests/test_cps_models.py tests/test_dry_run_policy.py tests/test_dry_run_intents.py tests/test_dry_run_report.py
```

Expected: all pass; inventory is exactly 21; no root schema directory remains.

- [ ] **Step 8: Commit Task 1**

```powershell
git add .gitattributes pyproject.toml src/mneme/schemas src/mneme tests
git add -u -- schemas
git commit -m "fix: unify MNEME schema resources"
```

---

### Task 2: Retain Writer Serialization and Record-ID Hardening

**Files:**
- Create: `src/mneme/writer_lock.py`
- Modify: `src/mneme/store.py`
- Modify: `src/mneme/errors.py`
- Modify: `tests/test_store.py`
- Create: `tests/test_store_concurrency.py`

**Interfaces:**
- Consumes: existing `MemoryStore.commit(TransactionProposal)` and MLF-RM exact-head rules.
- Produces: cross-process `StoreWriterLock`, one-winner compare-and-swap commit behavior, and global canonical `record_id` uniqueness.

- [ ] **Step 1: Write concurrent-writer and ID-reuse REDs**

```python
def test_two_processes_at_one_head_have_exactly_one_success(tmp_path):
    results = run_two_commit_processes(
        tmp_path / "memory.mlfdir",
        proposal("transaction:a", "record:a"),
        proposal("transaction:b", "record:b"),
    )
    assert sorted(results) == ["conflict", "success"]


def test_record_id_cannot_be_reused_across_committed_history(tmp_path):
    store = MemoryStore(tmp_path / "memory.mlfdir")
    first = store.commit(proposal("transaction:first", "record:stable"))
    with pytest.raises(RecordIdConflictError):
        store.commit(
            proposal(
                "transaction:second",
                "record:stable",
                expected_head=first.new_head,
            )
        )
```

- [ ] **Step 2: Run RED and retain the counterexample output**

Run:

```powershell
python -B -m pytest -q tests/test_store.py tests/test_store_concurrency.py
```

Expected: two writers can both publish or ID reuse is not rejected on the
unhardened remote-main implementation.

- [ ] **Step 3: Implement the accepted writer-lock slice**

Replay the semantics of exact commits `e97c515...` and `404704c...` without
overwriting remote-main Dry-Run/profile files. Hold one writer lock across head
read, transaction validation, ID-population validation, immutable publication,
head replace and readback.

- [ ] **Step 4: Preserve read-only verification**

Implement a lock-free double-head readback for
`MemoryStore.verify_current_transaction(tx, receipt) -> bool`; it must not
initialize or mutate a missing store.

- [ ] **Step 5: Run GREEN and legacy gates**

Run:

```powershell
python -B -m pytest -q tests/test_store.py tests/test_store_concurrency.py tests/test_acceptance.py
python -B scripts/validate_fresh_memory_core.py --output "$env:TEMP/mneme-v05-fresh-task2.json"
```

- [ ] **Step 6: Commit Task 2**

```powershell
git add src/mneme/writer_lock.py src/mneme/store.py src/mneme/errors.py tests/test_store.py tests/test_store_concurrency.py
git commit -m "fix: serialize unified MNEME writers"
```

---

### Task 3: Claude Contracts and Provider-Neutral Global Read Adapter

**Files:**
- Create: `src/mneme/claude_contracts.py`
- Create: `src/mneme/adapters/claude.py`
- Modify: `src/mneme/adapters/__init__.py`
- Modify: `src/mneme/errors.py`
- Create: `tests/test_claude_contracts.py`
- Create: `tests/test_claude_adapter.py`

**Interfaces:**
- Consumes: installed Claude schemas, `MemoryStore`, `Route`, existing whole-record projection.
- Produces: sealed Claude request/manifest/plan/receipt contracts and `ClaudeGlobalMemoryAdapter.materialize(request) -> ClaudeGlobalProjectionResult`.

- [ ] **Step 1: Write contract and scope REDs**

```python
def test_claude_request_is_global_only_and_hard_bounded():
    request = ClaudeGlobalProjectionRequest.sealed(valid_request())
    assert request.byte_budget == 16000
    for scope in ("identity/x", "resident/x", "project/x", "task/x"):
        with pytest.raises(ClaudeContractError):
            ClaudeGlobalProjectionRequest.sealed(valid_request(allowed_scope_paths=[scope]))


def test_adapter_excludes_non_global_records_without_body_leak(tmp_path):
    store = committed_store(tmp_path, [global_record(), identity_record("SECRET")])
    result = ClaudeGlobalMemoryAdapter(store, global_route()).materialize(request(store))
    assert result.manifest.included_record_ids == (global_record_id(),)
    assert b"SECRET" not in result.content
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -B -m pytest -q tests/test_claude_contracts.py tests/test_claude_adapter.py
```

Expected: import failures because Claude contracts and adapter are absent.

- [ ] **Step 3: Implement exact accepted contracts**

Use final `89bb150...` contract shapes, including transaction/head evidence on
publication/import receipts and publication-plan evidence on import plans. Keep
all `not_claimed` values exact.

- [ ] **Step 4: Implement deterministic global adapter**

The adapter accepts only the closed global route and exact current store head,
uses whole-record budget accounting, and has no write API.

- [ ] **Step 5: Run GREEN plus profile regressions**

Run:

```powershell
python -B -m pytest -q tests/test_claude_contracts.py tests/test_claude_adapter.py tests/test_routes.py tests/test_projection.py tests/test_soacr_adapter.py
python -B -m pytest -q tests/test_markdown_profile_v02.py tests/test_cps_adapter.py tests/test_dry_run_compatibility.py
```

- [ ] **Step 6: Commit Task 3**

```powershell
git add src/mneme/claude_contracts.py src/mneme/adapters src/mneme/errors.py tests/test_claude_contracts.py tests/test_claude_adapter.py
git commit -m "feat: add unified Claude global contracts"
```

---

### Task 4: Structurally Enforced Publication and Managed Import

**Files:**
- Create: `src/mneme/claude_authority.py`
- Create: `src/mneme/claude_projection.py`
- Create: `src/mneme/claude_import.py`
- Create: `tests/test_claude_authority.py`
- Create: `tests/test_claude_projection.py`
- Create: `tests/test_claude_import.py`
- Create: `tests/fixtures/claude/user-memory-other-blocks-mixed-eol.md`
- Create: `tests/windows_junction.py`

**Interfaces:**
- Consumes: exact committed store context, Claude contracts and projection result.
- Produces: `VerifiedClaudeWriteContext.bind(...)`, `ClaudeProjectionPublisher.plan/publish`, `ClaudeManagedImport.plan`, `ClaudeManagedImport.apply(plan, context) -> ClaudePublishedImportResult`.

- [ ] **Step 1: Write exact authority and stale-target REDs**

```python
def test_raw_authorization_cannot_enter_publisher(tmp_path):
    publisher, plan, _, target = prepared_publication(tmp_path)
    with pytest.raises(ManualAuthorityError, match="context"):
        publisher.publish(plan, raw_authorization())
    assert not target.exists()


def test_hand_written_projection_after_plan_is_refused(tmp_path):
    importer, plan, context, user_memory = prepared_import(tmp_path)
    before = user_memory.read_bytes()
    plan.projection.write_bytes(plan.publication.content)
    with pytest.raises(StaleTargetError, match="changed after planning"):
        importer.apply(plan, context)
    assert user_memory.read_bytes() == before
```

- [ ] **Step 2: Write the permanent capability-forgery regression**

```python
def test_public_import_api_has_no_caller_publication_slot():
    assert tuple(inspect.signature(ClaudeManagedImport.apply).parameters) == (
        "self",
        "plan",
        "context",
    )
    assert not hasattr(claude_projection, "VerifiedClaudePublication")
    assert not hasattr(claude_projection, "_PUBLICATION_CAPABILITY_ISSUER")


def test_import_apply_invokes_exact_publisher_once(tmp_path, monkeypatch):
    importer, plan, context, _, _ = bound_environment(tmp_path)
    original = claude_projection.ClaudeProjectionPublisher.publish
    calls = 0

    def observed_publish(self, publication, selected_context):
        nonlocal calls
        calls += 1
        return original(self, publication, selected_context)

    monkeypatch.setattr(
        claude_projection.ClaudeProjectionPublisher,
        "publish",
        observed_publish,
    )
    result = importer.apply(plan, context)
    assert calls == 1
    assert result.import_receipt.publication_receipt_digest == result.publication_receipt.digest
```

- [ ] **Step 3: Run RED and preserve output**

Run:

```powershell
python -B -m pytest -q tests/test_claude_authority.py tests/test_claude_projection.py tests/test_claude_import.py
```

Expected: imports fail before the accepted implementation is introduced.

- [ ] **Step 4: Implement committed-context verification**

Bind store, transaction, commit receipt and manual authorization. Revalidate
current head, reachable transaction bytes, scope coverage and manifest source
head at every write primitive entry.

- [ ] **Step 5: Implement atomic publisher and byte-preserving importer**

Import apply must instantiate the real publisher internally, publish exactly
once, lock/reread projection bytes, and only then replace the exact MNEME block.
Do not add a caller capability or complete `_apply_locked` bypass helper.

- [ ] **Step 6: Run path, crash and reader GREEN gates**

Run:

```powershell
python -B -m pytest -q tests/test_claude_authority.py tests/test_claude_projection.py tests/test_claude_import.py -rs
```

Expected: all pass; Windows symlink may retain only the documented privilege
skip; junction, hardlink and concurrent-reader controls execute.

- [ ] **Step 7: Commit Task 4 and write Lares checkpoint**

```powershell
git add src/mneme/claude_authority.py src/mneme/claude_projection.py src/mneme/claude_import.py tests/test_claude_authority.py tests/test_claude_projection.py tests/test_claude_import.py tests/fixtures/claude tests/windows_junction.py
git commit -m "feat: enforce unified Claude publication flow"
```

Write an exact HEAD/tree/test checkpoint to the shared handoff directory. Stop
for Lares only if the integrated behavior differs from final `89bb150...`.

---

### Task 5: Synthetic Activation Orchestrator and CLI

**Files:**
- Create: `src/mneme/claude_activation.py`
- Create: `src/mneme/claude_cli.py`
- Create: `scripts/mneme_claude_global.py`
- Modify: `pyproject.toml`
- Create: `tests/test_claude_activation.py`
- Create: `tests/test_claude_cli.py`

**Interfaces:**
- Consumes: committed-context publisher/importer and global adapter.
- Produces: `ClaudeGlobalActivation.plan`, `apply_synthetic`, and CLI commands `verify`, `plan`, `apply-synthetic`, `status`.

- [ ] **Step 1: Write no-real-target and order REDs**

```python
def test_real_target_override_is_not_a_cli_argument(tmp_path):
    with pytest.raises(SystemExit):
        main(
            [
                "apply-synthetic",
                "--root",
                str(tmp_path / "synthetic-root"),
                "--claude-user-memory",
                str(tmp_path / "real-looking" / "CLAUDE.md"),
            ]
        )
    assert not (tmp_path / "real-looking").exists()


def test_activation_receipt_has_exact_step_order(tmp_path):
    activation, plan, authorization = synthetic_operation(tmp_path)
    receipt = activation.apply_synthetic(plan, authorization)
    assert receipt.steps == (
        "canonical_commit",
        "projection_publish",
        "managed_import",
    )
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -B -m pytest -q tests/test_claude_activation.py tests/test_claude_cli.py
```

- [ ] **Step 3: Implement exact accepted orchestration**

Derive every path beneath one caller-supplied new synthetic root. Bind activation
plan, transaction, request and configuration digests. Keep real target status
`NOT_AUTHORIZED`, Claude memory readback `NOT_RUN`, private Residence
`NOT_READ`, and production wave `NOT_APPLICABLE`.

- [ ] **Step 4: Run GREEN and installed-entrypoint smoke**

Run:

```powershell
python -B -m pytest -q tests/test_claude_activation.py tests/test_claude_cli.py
python -B scripts/mneme_claude_global.py verify
```

- [ ] **Step 5: Commit Task 5**

```powershell
git add pyproject.toml src/mneme/claude_activation.py src/mneme/claude_cli.py scripts/mneme_claude_global.py tests/test_claude_activation.py tests/test_claude_cli.py
git commit -m "feat: add unified Claude synthetic activation"
```

---

### Task 6: Runtime-Audited Claude Acceptance

**Files:**
- Create: `src/mneme/claude_effects.py`
- Create: `src/mneme/claude_acceptance.py`
- Create: `scripts/validate_claude_global_memory.py`
- Create: `tests/fixtures/claude/expected-effects.json`
- Create: `tests/test_claude_effects.py`
- Create: `tests/test_claude_acceptance.py`

**Interfaces:**
- Consumes: synthetic activation and all Claude primitives.
- Produces: `validate_claude_global_memory(root, injected_effect=None) -> ClaudeGlobalAcceptanceReport` and scoped CPython audit/profile evidence.

- [ ] **Step 1: Write the three original real-effect REDs**

```python
@pytest.mark.parametrize(
    ("effect_name", "field"),
    [
        ("network", "network_calls"),
        ("external_cli", "external_cli_calls"),
        ("production_write", "production_writes"),
    ],
)
def test_real_effect_inside_execute_run_turns_report_red(
    tmp_path, monkeypatch, effect_name, field
):
    wrap_execute_run_with_real_synthetic_effect(monkeypatch, tmp_path, effect_name)
    report = validate_claude_global_memory(tmp_path / "acceptance")
    assert report.status == "FAIL"
    assert getattr(report.effects, field) >= 1
    assert f"forbidden_effect:{effect_name}" in report.reason_codes
```

- [ ] **Step 2: Write observer isolation and false-positive REDs**

```python
def test_synthetic_root_write_is_allowed_but_outside_write_is_observed(tmp_path):
    observer = observer_for(tmp_path / "root", fixture_path(tmp_path))
    with observer:
        (tmp_path / "root" / "inside.txt").write_bytes(b"inside")
        (tmp_path / "outside.txt").write_bytes(b"outside")
    evidence = observer.evidence()
    assert evidence.private_writes == 0
    assert evidence.production_writes >= 1
```

- [ ] **Step 3: Run RED**

Run:

```powershell
python -B -m pytest -q tests/test_claude_effects.py tests/test_claude_acceptance.py
```

- [ ] **Step 4: Implement the accepted scoped observer**

Use CPython audit events for file/socket/subprocess effects and a scoped profile
hook for provider/MCP/Bridge module entrypoints. Serialize one active observer,
restore profile hooks, retain an inert global audit callback outside the
context, and report normalized categories/digest only.

- [ ] **Step 5: Implement deterministic CGM-001..028 ownership**

Execute CGM-001..022, 025 and 028 twice. Mark 023, 024, 026 and 027 exactly
`NOT_RUN_LOCAL_ACTIVATION_REQUIRED`. `injected_effect` must call monitored APIs,
never replace a counter field.

- [ ] **Step 6: Run acceptance and full GREEN gates**

Run:

```powershell
python -B -m pytest -q tests/test_claude_effects.py tests/test_claude_acceptance.py
python -B scripts/validate_claude_global_memory.py --root "$env:TEMP/mneme-v05-cgm-task6" --output "$env:TEMP/mneme-v05-cgm-task6.json"
python -B -m pytest -q
```

- [ ] **Step 7: Commit Task 6 and stop for Lares slice review**

```powershell
git add src/mneme/claude_effects.py src/mneme/claude_acceptance.py scripts/validate_claude_global_memory.py tests/test_claude_effects.py tests/test_claude_acceptance.py tests/fixtures/claude/expected-effects.json
git commit -m "test: audit unified Claude acceptance effects"
```

Provide exact HEAD/tree, the three real-effect controls, full tests and clean
state. Lares reviews capability/effect/path/junction/reader-lock carry-forward.

---

### Task 7: Cross-Profile Ownership and Opt-In Composition

**Files:**
- Create: `tests/test_unified_profile_boundaries.py`
- Modify: `src/mneme/__init__.py`
- Modify: `README.md`
- Verify unchanged: `profiles/memory-markdown/evemiss-residence-0.1.json`
- Verify unchanged: `profiles/memory-markdown/evemiss-residence-0.2.json`
- Verify unchanged: `src/mneme/cps/*`
- Verify unchanged except schema loader: `src/mneme/dry_run/*`
- Verify unchanged: `src/mneme/adapters/soacr.py`

**Interfaces:**
- Consumes: all integrated layers.
- Produces: machine-testable ownership/non-hot-path invariants and
  `load_builtin_evemiss_profile_by_id(profile_id: str) -> MemoryMarkdownProfile`.

- [ ] **Step 1: Write profile-selection and frozen-digest REDs**

```python
def test_v01_profile_remains_frozen_and_v02_is_explicit():
    v01 = load_builtin_evemiss_profile_by_id("evemiss-residence/0.1")
    v02 = load_builtin_evemiss_profile_by_id("evemiss-residence/0.2")
    assert v01.digest() == "0757299afd2d72d9cd0f3f3c7ff616f17836edff2b694afc0340d0eea055fdeb"
    assert v02.profile_id == "evemiss-residence/0.2"
    assert v02.digest() != v01.digest()
    with pytest.raises(MappingProfileError):
        load_builtin_evemiss_profile_by_id("auto")


def test_v01_never_guesses_v02_dialect(real_dialect_synthetic_fixture):
    proposal = propose_profiled_markdown_import(
        real_dialect_synthetic_fixture,
        load_builtin_evemiss_profile(),
    )
    reasons = [item["reason"] for item in proposal.loss_report["loss"]]
    assert reasons.count("unknown_heading") == 2
```

- [ ] **Step 2: Write sidecar and no-hot-path REDs**

```python
def test_claude_and_soacr_hot_paths_do_not_import_dry_run_or_cps():
    for module_path in (
        ROOT / "src/mneme/adapters/claude.py",
        ROOT / "src/mneme/adapters/soacr.py",
        ROOT / "src/mneme/claude_activation.py",
    ):
        imports = imported_modules(module_path)
        assert not any(name.startswith("mneme.dry_run") for name in imports)
        assert not any(name.startswith("mneme.cps") for name in imports)


def test_dry_run_has_no_writable_store_input():
    parameters = inspect.signature(PrivateResidenceDryRunAnalyzer.analyze).parameters
    assert "store" not in parameters
    assert "memory_store" not in parameters
```

- [ ] **Step 3: Run RED**

Run:

```powershell
python -B -m pytest -q tests/test_unified_profile_boundaries.py
```

- [ ] **Step 4: Add only the minimal selection surface**

Expose explicit profile-loader functions; do not add content-based auto
detection. `load_builtin_evemiss_profile_by_id` accepts only the two exact IDs
and raises `MappingProfileError` for every other string. Keep CPS and Dry-Run
callable only through their existing explicit APIs.

- [ ] **Step 5: Run all non-Claude profile acceptance suites**

Run:

```powershell
python -B -m pytest -q tests/test_markdown_profile.py tests/test_markdown_profile_acceptance.py tests/test_markdown_profile_v02.py tests/test_markdown_profile_v02_acceptance.py
python -B -m pytest -q tests/test_cps_models.py tests/test_cps_rules.py tests/test_cps_factorization.py tests/test_cps_seed.py tests/test_cps_adapter.py tests/test_cps_acceptance.py
python -B -m pytest -q tests/test_dry_run_analyzer.py tests/test_dry_run_bundle.py tests/test_dry_run_compatibility.py tests/test_dry_run_intents.py tests/test_dry_run_persistence.py tests/test_dry_run_policy.py tests/test_dry_run_report.py tests/test_private_residence_dry_run_acceptance.py
python -B -m pytest -q tests/test_soacr_adapter.py tests/test_unified_profile_boundaries.py
```

- [ ] **Step 6: Commit Task 7**

```powershell
git add README.md src/mneme/__init__.py tests/test_unified_profile_boundaries.py
git commit -m "test: enforce unified MNEME profile boundaries"
```

---

### Task 8: Package 0.5.0a1, Combined CI and Public Runbook

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/mneme/__init__.py`
- Modify: `README.md`
- Create: `.github/workflows/mneme-unified-profile-integration.yml`
- Create: `docs/runtime/MNEME_UNIFIED_PROFILE_INTEGRATION_V0.5.md`
- Create: `tests/test_unified_packaging.py`

**Interfaces:**
- Consumes: all implemented layers and CLIs.
- Produces: `mneme-memory==0.5.0a1`, one installed wheel, six named acceptance surfaces and a synthetic-only operator runbook.

- [ ] **Step 1: Write package/version/CI REDs**

```python
def test_unified_package_metadata_and_resources(installed_candidate):
    metadata = installed_candidate.metadata
    assert metadata["Name"] == "mneme-memory"
    assert metadata["Version"] == "0.5.0a1"
    assert installed_candidate.schema_names == EXPECTED_21_SCHEMAS
    assert installed_candidate.cli_exits == {"verify": 0, "apply-synthetic": 0, "status": 0}


def test_combined_ci_names_all_six_acceptance_surfaces():
    text = WORKFLOW.read_text(encoding="utf-8")
    for label in (
        "Fresh Memory Core",
        "MNEME-MD 0.1",
        "EveMiss profile 0.2",
        "MNEME-CPS 0.1",
        "Private Residence Dry-Run 0.2",
        "Claude Global Transition 0.1",
    ):
        assert label in text
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -B -m pytest -q tests/test_unified_packaging.py
```

- [ ] **Step 3: Set exact package metadata**

Set both `pyproject.toml` and `mneme.__version__` to `0.5.0a1`. Retain runtime
dependency `jsonschema>=4.23` and dev dependencies `pytest>=8.0`,
`setuptools>=68`, `wheel`.

- [ ] **Step 4: Add combined matrix CI**

Run Windows and Ubuntu, Python 3.11. Install dev dependencies before the
no-build-isolation wheel step. Run each acceptance script as a separately named
step. Do not use secrets or provider/network calls in tests.

- [ ] **Step 5: Write the public runbook**

Document capability selection, one-store ownership, profile opt-in, sidecar
non-authority, Claude consumer semantics, synthetic-only status and the later
RAL/LIMEN/private/local-activation gates. Include no real path, memory body,
resident ID, private digest or credential.

- [ ] **Step 6: Run packaging GREEN**

Run:

```powershell
python -B -m pytest -q tests/test_unified_packaging.py tests/test_packaged_schemas.py
python -B -m pytest -q
```

- [ ] **Step 7: Commit Task 8**

```powershell
git add pyproject.toml src/mneme/__init__.py README.md .github/workflows/mneme-unified-profile-integration.yml docs/runtime/MNEME_UNIFIED_PROFILE_INTEGRATION_V0.5.md tests/test_unified_packaging.py
git commit -m "docs: prepare MNEME 0.5.0a1 candidate"
```

---

### Task 9: Final Integrated Evidence and Independent Review

**Files:**
- Create: `docs/evidence/2026-08-29-mneme-v0.5-input-pins.json`
- Create: `docs/evidence/2026-08-29-mneme-v0.5-acceptance.json`
- Create outside Git: shared durable Lares final-review checkpoint

**Interfaces:**
- Consumes: exact final candidate and every prior acceptance surface.
- Produces: deterministic, digest-bound integrated candidate evidence; no release or activation.

- [ ] **Step 1: Write and verify exact input pins**

```json
{
  "schema": "mneme.unified-integration-input-pins/0.1",
  "remote_main": {
    "commit": "c21546a263920e0f80701696e1857c203917d701",
    "tree": "5ad5725ca685df334110b257e4004d9274e35674"
  },
  "claude_candidate": {
    "commit": "89bb1509f2bb96c4067d12c15094adacc2512b67",
    "tree": "0fcac15cbccdde61013b8dfa6938ed19ca161ef8",
    "acceptance_sha256": "50E7C5E999DE8BEAF80FF7B45856750CD9B398E28FC01F2BE279BB4185EADCCF"
  }
}
```

Add a test that reads Git objects and verifies commit→tree for both pins.

- [ ] **Step 2: Run the full exact-tree suite**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
python -B -m pytest -q -rs
```

Expected: zero failures. Record the one Windows symlink privilege skip only if
it remains; junction/hardlink/reader controls must execute.

- [ ] **Step 3: Run all six acceptance scripts separately**

Run:

```powershell
python -B scripts/validate_fresh_memory_core.py --output "$env:TEMP/mneme-v05-final-fresh.json"
python -B scripts/validate_memory_markdown_profile.py --output "$env:TEMP/mneme-v05-final-md.json"
python -B scripts/validate_memory_markdown_profile_v02.py --output "$env:TEMP/mneme-v05-final-md-v02.json"
python -B scripts/validate_cognitive_persistence_semantics.py --output "$env:TEMP/mneme-v05-final-cps.json"
python -B scripts/validate_private_residence_two_pass_dry_run.py --output "$env:TEMP/mneme-v05-final-dry-run.json"
python -B scripts/validate_claude_global_memory.py --root "$env:TEMP/mneme-v05-final-cgm-root" --output "$env:TEMP/mneme-v05-final-cgm.json"
```

Require every top-level report status to be exactly `PASS`. Dry-Run canonical
mutation/destructive actions remain false; Claude live cases remain NOT_RUN.

- [ ] **Step 4: Build and inspect a clean archive wheel**

Use `git archive HEAD`, `PIP_NO_INDEX=1`, `--no-deps`, and
`--no-build-isolation`. Install to a fresh target and verify:

```text
package version 0.5.0a1
21 exact schema resources
source schema bytes == installed schema bytes
Claude CLI verify/apply-synthetic/status exits 0/0/0
Dry-Run imports without root schema directory
old publication capability exports absent
```

- [ ] **Step 5: Run static and compile gates**

Run:

```powershell
$changedPython = git diff --name-only c21546a263920e0f80701696e1857c203917d701..HEAD -- '*.py'
python -B -m ruff check $changedPython
python -X pycache_prefix="$env:TEMP/mneme-v05-pycache" -m compileall -q src tests
git diff --check c21546a263920e0f80701696e1857c203917d701..HEAD
git status --short
```

Expected: ruff/diff/compile pass and worktree clean after evidence commit.

- [ ] **Step 6: Commit final evidence**

```powershell
git add docs/evidence/2026-08-29-mneme-v0.5-input-pins.json docs/evidence/2026-08-29-mneme-v0.5-acceptance.json
git commit -m "docs: record MNEME 0.5.0a1 acceptance"
```

- [ ] **Step 7: Stop for Lares independent final adversarial review**

Provide exact HEAD/tree, spec/plan hashes, full tests, six acceptance reports,
clean wheel/schema evidence and zero private/external effects. Lares must rerun
against the integrated tree:

```text
publication-capability forgery
publisher-executes-once proof
real UDP/subprocess/outside-root effect attacks
path escape / Windows junction / hardlink / reader-lock controls
no hot-path CPS/Dry-Run promotion
no real/private/local activation
```

Do not infer ACCEPT from ancestry or cherry-picked commits. Stop after the
review request. No push, PR, merge, release, deployment or activation.

## Spec coverage map

- One canonical core and ownership boundaries: Tasks 1, 2 and 7.
- Exact 21 installed schemas/no duplicates: Task 1.
- Remote-main profile v0.2/CPS/Dry-Run preservation: Tasks 1 and 7.
- Claude accepted contracts, authority, publisher/import and CLI: Tasks 3–5.
- Runtime-observed effect evidence and defeated attacks: Task 6.
- Package `0.5.0a1`, combined CI and public runbook: Task 8.
- Exact source pins, six acceptance surfaces, clean wheel and independent Twin: Task 9.
- Real private use and local activation remain excluded from every task.
