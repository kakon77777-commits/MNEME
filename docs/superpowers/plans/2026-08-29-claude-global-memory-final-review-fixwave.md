# MNEME Claude Global Memory Transition v0.1 — Final Review Fixwave Plan

> Execute inline and sequentially with TDD. Lares remains the required
> read-only final reviewer. Do not access real Claude memory, private Residence
> or real global records, and do not push, merge, release or deploy.

**Base candidate:** `2d0ba32295429c54a764917a3fe3cfe6db60e7a2`

**Design authority:**
`docs/superpowers/specs/2026-08-29-claude-global-memory-final-review-delta-001.md`

## Task F1: Freeze the review delta

**Files**

- Add the design delta above.
- Add this plan.

**Gate**

- Confirm both Lares counterexamples reproduce on the exact base candidate.
- Scan both files for placeholders, contradictory authority, real paths and
  activation language.
- Commit documentation only before implementation.

## Task F2: Make write primitives self-defending

**Files**

- Add `src/mneme/claude_authority.py`.
- Modify `src/mneme/claude_projection.py`.
- Modify `src/mneme/claude_import.py`.
- Modify `src/mneme/claude_activation.py`.
- Modify the publication/import receipt schemas and contract properties.
- Modify Claude projection/import/activation/contract tests.

### RED

Write and run focused tests proving:

- publisher refuses a write context whose authorization belongs to another
  valid transaction;
- publisher refuses a stale or noncurrent commit context before target write;
- publisher no longer accepts raw `LocalManualWriteAuthorization`;
- importer refuses a hand-written projection when no verified publication
  capability exists;
- importer refuses a self-sealed publication receipt and a capability from
  another projection/transaction;
- every refusal leaves projection and user-memory bytes unchanged.

Retain the failing output before production edits.

### GREEN

Implement:

- `VerifiedClaudeWriteContext.bind(store, transaction, commit_receipt,
  authorization)` with full store/transaction/head/scope/readback checks;
- `VerifiedClaudePublication`, issued only after publisher readback;
- `publish(plan, context) -> VerifiedClaudePublication`;
- `apply(plan, context, publication) -> ClaudeImportReceipt`;
- durable transaction/head bindings on both receipts and publication-receipt
  bindings on import receipts;
- activation wrapper construction and cross-receipt verification.

Update every synthetic helper to construct an actual committed transaction and
verified context. Do not retain a legacy raw-authorization overload.

### Verify and commit

Run contract, projection, import, activation and CLI suites, then the full suite.
Commit only after RED becomes GREEN and the worktree diff is scoped.

## Task F3: Replace default counters with runtime observation

**Files**

- Add `src/mneme/claude_effects.py`.
- Modify `src/mneme/claude_acceptance.py`.
- Modify `tests/test_claude_acceptance.py`.
- Add `tests/test_claude_effects.py` if isolation improves clarity.
- Modify `tests/fixtures/claude/expected-effects.json`.

### RED

Against the unchanged acceptance implementation, wrap the real `_execute_run`
path and independently perform:

1. one loopback UDP `sendto`;
2. one local Python subprocess;
3. one disposable write outside the exact acceptance root.

Each current test must fail because the report incorrectly remains `PASS` with
the relevant counter at zero. Add private read/write plus provider/MCP/Bridge
module-entry controls using synthetic-only paths and functions.

### GREEN

Implement one scoped observer using CPython audit events and a call profiler.
It must:

- classify exact synthetic-root operations separately;
- classify private markers before root allowlisting;
- allow only closed read-only fixture/schema/source-scan resources;
- count outside-root content access as production;
- count socket and external-CLI audit events;
- count known provider/MCP/Bridge module entries;
- restore profile hooks and deactivate the global audit callback after the
  acceptance context;
- serialize concurrent acceptance contexts;
- return only normalized counts/digest, never raw paths or payloads.

Change `injected_effect` so it invokes a monitored synthetic probe and never
directly replaces a counter. Preserve deterministic positive evidence and the
four local-activation `NOT_RUN` cases.

### Verify and commit

Run effect-observer, acceptance, CLI and full suites. Run the acceptance script
twice and compare canonical report bytes/digests. Commit only after all real
counterexample populations are GREEN.

## Task F4: Close the development build prerequisite gap

**Files**

- Modify `pyproject.toml`.
- Modify `.github/workflows/claude-global-memory.yml` if its setup order is not
  already sufficient.
- Modify `tests/test_claude_packaging.py`.
- Modify the public runbook wording about wheel SHA reproducibility.

### RED/GREEN

- RED: a fresh environment installing only the declared dev extra cannot run
  the no-build-isolation wheel step.
- GREEN: dev metadata includes `setuptools>=68` and `wheel`; a fresh local
  environment installs the declared local prerequisites without network during
  the wheel build, then builds and installs the wheel.
- Assert the project does not claim universal byte-identical wheel SHA across
  unspecified toolchains.

## Task F5: Final verification and Lares re-review

Run, at minimum:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
python -B -m pytest -q tests/test_claude_contracts.py tests/test_claude_projection.py tests/test_claude_import.py tests/test_claude_activation.py tests/test_claude_cli.py
python -B -m pytest -q tests/test_claude_effects.py tests/test_claude_acceptance.py
python -B -m pytest -q tests/test_claude_packaging.py tests/test_packaged_schemas.py
python -B -m pytest -q
python -B scripts/validate_fresh_memory_core.py --output "$env:TEMP/mneme-fixwave-fresh.json"
python -B scripts/validate_memory_markdown_profile.py --output "$env:TEMP/mneme-fixwave-md.json"
python -B scripts/validate_cognitive_persistence_semantics.py --output "$env:TEMP/mneme-fixwave-cps.json"
python -B scripts/validate_claude_global_memory.py --output "$env:TEMP/mneme-fixwave-cgm.json"
python -B -m compileall -q src tests
git diff --check 84b9b0ee94115902d7a9e6acfdc48372e60fd673..HEAD
```

Also:

- build from a clean `git archive` using the declared local build prerequisites;
- install into a fresh target and run all installed Claude entrypoints;
- compare all source and installed schema bytes;
- run the static runtime-boundary scan;
- confirm real/private/provider/network/Bridge effects remain absent from the
  positive run;
- confirm worktree clean, no upstream and no push;
- write a durable checkpoint with exact HEAD/tree/file hashes;
- request Lares to re-test the original two blocking populations and the build
  prerequisite note.

Stop after sending the review request. Local activation remains unauthorized.
