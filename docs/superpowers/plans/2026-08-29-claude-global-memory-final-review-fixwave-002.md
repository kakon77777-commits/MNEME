# MNEME Claude Global Memory Transition v0.1 — Final Review Fixwave 002 Plan

> Execute inline with TDD. This plan closes only the residual
> `VerifiedClaudePublication` forgery. Lares remains the final read-only
> reviewer. No real activation, private access, push, merge, release or deploy.

## Task G1: Freeze Delta 002

- Add the design delta and this plan as append-only evidence.
- Preserve the prior review and Delta 001 unchanged.
- Verify placeholder, scope, contradiction and diff checks.
- Commit documentation only.

## Task G2: Write the exact residual RED

- Add a test that imports `_PUBLICATION_CAPABILITY_ISSUER`, constructs
  `VerifiedClaudePublication` through `object.__new__`/`object.__setattr__`,
  wraps a self-sealed attacker receipt and proves current `apply` mutates the
  synthetic user-memory target.
- Add desired-interface REDs proving import planning consumes a prepared
  publication and import apply accepts no caller publication evidence.
- Retain the failing output before implementation.

## Task G3: Remove the capability boundary

- Remove `_PUBLICATION_CAPABILITY_ISSUER` and
  `VerifiedClaudePublication`.
- Return `ClaudePublicationReceipt` directly from publisher.
- Add publication plan ref/digest to the import plan schema and properties.
- Store exact `PreparedClaudePublication` inside `PreparedClaudeImport`.
- Make import planning read-only even when the projection target is absent.
- Make import apply instantiate and invoke the exact publisher internally.
- Return `ClaudePublishedImportResult` containing both receipts.
- Revalidate receipt/plan/context/projection equality before user-memory write.

Run contract, publisher and importer focused GREEN tests.

## Task G4: Migrate the orchestrator and acceptance cases

- Activation plans publication but does not publish separately.
- Import apply performs publication then import and returns both receipts.
- Activation receipt retains the same external step order and durable receipt
  bindings.
- Acceptance helpers create publication plans rather than caller capabilities.
- Update crash, stale, idempotent, mixed-EOL and concurrent-reader controls.
- Update clean installed API tests and public runbook wording if needed.

Run activation, CLI, acceptance and packaging focused suites.

## Task G5: Final verification and re-review

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
python -B -m pytest -q tests/test_claude_contracts.py tests/test_claude_authority.py tests/test_claude_projection.py tests/test_claude_import.py tests/test_claude_activation.py tests/test_claude_cli.py
python -B -m pytest -q tests/test_claude_effects.py tests/test_claude_acceptance.py
python -B -m pytest -q tests/test_claude_packaging.py tests/test_packaged_schemas.py
python -B -m pytest -q -rs
```

Then rerun all four acceptance scripts, same-root deterministic CGM comparison,
compile/ruff/diff checks and a clean `git archive` wheel/install/schema check.

Commit the code fix, write a durable checkpoint with exact HEAD/tree/hashes and
ask Lares to rerun the original `object.__new__` attack. Stop for review; do not
activate, push, merge, release or deploy.
