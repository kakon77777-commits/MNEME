# MNEME Fresh Memory Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build MNEME v0.1 Fresh Memory Core as a deterministic, file-first, fail-closed canonical memory runtime that rejects truncated writes and materializes budget-bounded Markdown/model projections without coupling memory capacity to context size.

**Architecture:** The runtime stores typed `MemoryRecord` objects through complete transaction envelopes. A transaction is canonical only after parsing, schema validation, digest/count/head checks, authority-reference shape validation, staging, and an explicit final commit marker succeed. Retrieval uses auditable routes over canonical records; Markdown and model-context views are deterministic projections bound to a canonical head. Existing Markdown is imported non-destructively into proposals plus an explicit import-loss report.

**Tech Stack:** Python 3.11+, standard library (`dataclasses`, `json`, `hashlib`, `pathlib`, `tempfile`, `os`), `jsonschema>=4.23`, `pytest>=8.0`.

**Spec:** `docs/superpowers/specs/2026-08-27-mneme-v0.1-design.md`

## Global Constraints

- MNEME v0.1 is file-first; no production dynamic database backend is implemented in this milestone.
- Tests use synthetic residents and synthetic memory only; no real Residence path or private data is required.
- Core validation has no network dependency.
- `IDENTITY != MEMORY`, `MEMORY != CONTEXT`, `MEMORY != MARKDOWN`, and `PROPOSAL != COMMIT` are enforced boundaries.
- Read authority never implies write authority.
- Incomplete or truncated output produces zero canonical commit.
- Silent tail truncation is forbidden for successful projections.
- Source Markdown is never overwritten during import.
- Storage backend choice must not redefine record, route, transaction, or projection semantics.
- New semantic fields or record types are not accepted silently; profile evolution is explicit.
- Every positive acceptance path has at least one corrupted or unauthorized negative counterpart.

---

## Planned File Structure

```text
MNEME/
├── pyproject.toml
├── src/mneme/
│   ├── __init__.py                  package version and public exports
│   ├── canonical.py                 deterministic UTF-8 JSON bytes and domain-separated digests
│   ├── errors.py                    typed fail-closed runtime exceptions
│   ├── records.py                   MemoryRecord parsing, validation, canonical digest
│   ├── transactions.py              transaction envelope validation and commit eligibility
│   ├── store.py                     file-first immutable transaction publication and HEAD handling
│   ├── routes.py                    auditable route declarations and scope isolation
│   ├── projection.py                budgeted Markdown/model projection and manifest
│   ├── markdown_import.py           non-destructive Markdown proposal/import-loss generation
│   └── adapters/
│       ├── __init__.py
│       └── soacr.py                 synthetic read-only SOACR-facing adapter contract
├── schemas/
│   ├── memory-record-0.1.schema.json
│   ├── transaction-0.1.schema.json
│   ├── route-0.1.schema.json
│   └── projection-manifest-0.1.schema.json
├── fixtures/synthetic/
│   ├── memory.md
│   └── records.jsonl
├── scripts/
│   └── validate_fresh_memory_core.py
└── tests/
    ├── test_canonical.py
    ├── test_records.py
    ├── test_transactions.py
    ├── test_store.py
    ├── test_routes.py
    ├── test_projection.py
    ├── test_markdown_import.py
    ├── test_soacr_adapter.py
    └── test_acceptance.py
```

The physical v0.1 commit mechanism uses immutable transaction documents under `transactions/committed/` plus an atomically replaced UTF-8 `HEAD` file. Rebuildable record/route/projection views may be derived from committed transactions. This avoids treating a partially appended multi-file index as proof of canonical commit.

Canonical digest rules used throughout the plan:

```python
canonical_json_bytes(value) = json.dumps(
    value,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
    allow_nan=False,
).encode("utf-8")

record_digest = sha256(b"MNEME-RECORD-0.1\0" + canonical_json_bytes(record)).hexdigest()
transaction_digest = sha256(b"MNEME-TX-0.1\0" + canonical_json_bytes(transaction_without_digest)).hexdigest()
head_digest = sha256(
    b"MNEME-HEAD-0.1\0" + previous_head.encode("ascii") + b"\0" + transaction_digest.encode("ascii")
).hexdigest()
```

`GENESIS` is the only empty-store source head spelling in v0.1.

---

### Task 1: Package Baseline and Canonical Byte Contract

**Files:**
- Create: `pyproject.toml`
- Create: `src/mneme/__init__.py`
- Create: `src/mneme/errors.py`
- Create: `src/mneme/canonical.py`
- Test: `tests/test_canonical.py`

**Interfaces:**
- Produces: `canonical_json_bytes(value: object) -> bytes`
- Produces: `sha256_domain(domain: bytes, payload: bytes) -> str`
- Produces: `CanonicalizationError(ValueError)`
- Later tasks consume these exact helpers for every digest and canonical file payload.

- [ ] **Step 1: Write the failing canonicalization tests**

```python
# tests/test_canonical.py
import math
import pytest

from mneme.canonical import canonical_json_bytes, sha256_domain
from mneme.errors import CanonicalizationError


def test_canonical_json_is_sorted_compact_utf8_and_stable():
    left = {"z": 1, "a": "記憶", "nested": {"b": 2, "a": 1}}
    right = {"nested": {"a": 1, "b": 2}, "a": "記憶", "z": 1}
    expected = b'{"a":"\xe8\xa8\x98\xe6\x86\xb6","nested":{"a":1,"b":2},"z":1}'
    assert canonical_json_bytes(left) == expected
    assert canonical_json_bytes(right) == expected


def test_canonical_json_rejects_nan():
    with pytest.raises(CanonicalizationError):
        canonical_json_bytes({"bad": math.nan})


def test_domain_hash_changes_when_domain_changes():
    payload = b"same"
    assert sha256_domain(b"A", payload) != sha256_domain(b"B", payload)
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
python -m pytest tests/test_canonical.py -q
```

Expected: collection/import failure because `mneme.canonical` does not exist yet.

- [ ] **Step 3: Add the minimal package and canonical helpers**

```python
# src/mneme/errors.py
class MnemeError(Exception):
    """Base MNEME error."""


class CanonicalizationError(MnemeError, ValueError):
    """Input cannot be represented by the canonical JSON contract."""
```

```python
# src/mneme/canonical.py
from __future__ import annotations

import hashlib
import json

from .errors import CanonicalizationError


def canonical_json_bytes(value: object) -> bytes:
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise CanonicalizationError(str(exc)) from exc
    return text.encode("utf-8")


def sha256_domain(domain: bytes, payload: bytes) -> str:
    return hashlib.sha256(domain + b"\0" + payload).hexdigest()
```

```python
# src/mneme/__init__.py
__version__ = "0.1.0a1"
```

`pyproject.toml` must declare Python `>=3.11`, package discovery from `src`, runtime dependency `jsonschema>=4.23`, and dev extra `pytest>=8.0`.

- [ ] **Step 4: Run the focused tests and verify GREEN**

```bash
python -m pytest tests/test_canonical.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Commit Task 1**

```bash
git add pyproject.toml src/mneme tests/test_canonical.py
git commit -m "feat: establish MNEME canonical byte contract"
```

---

### Task 2: Typed MemoryRecord and JSON Schema

**Files:**
- Create: `schemas/memory-record-0.1.schema.json`
- Create: `src/mneme/records.py`
- Modify: `src/mneme/errors.py`
- Test: `tests/test_records.py`

**Interfaces:**
- Consumes: `canonical_json_bytes`, `sha256_domain`
- Produces: `MemoryRecord.from_dict(raw: dict[str, object]) -> MemoryRecord`
- Produces: `MemoryRecord.to_dict() -> dict[str, object]`
- Produces: `MemoryRecord.digest() -> str`
- Produces: `RecordValidationError(MnemeError, ValueError)`

- [ ] **Step 1: Write failing MemoryRecord tests**

```python
# tests/test_records.py
import pytest

from mneme.records import MemoryRecord
from mneme.errors import RecordValidationError


def valid_record():
    return {
        "record_version": "mneme.memory-record/0.1",
        "record_id": "rec-001",
        "record_type": "lesson",
        "scope": {"kind": "global", "subject": "verification"},
        "content": {"text": "A verifier must itself be validated."},
        "relations": [],
        "provenance": {"event_id": "evt-001", "source_ref": "synthetic:test"},
        "status": "active",
    }


def test_record_round_trip_and_digest_are_deterministic():
    first = MemoryRecord.from_dict(valid_record())
    second = MemoryRecord.from_dict(dict(reversed(list(valid_record().items()))))
    assert first.to_dict() == second.to_dict()
    assert first.digest() == second.digest()
    assert len(first.digest()) == 64


def test_unknown_record_type_is_rejected():
    raw = valid_record()
    raw["record_type"] = "invented"
    with pytest.raises(RecordValidationError):
        MemoryRecord.from_dict(raw)


def test_missing_provenance_is_rejected():
    raw = valid_record()
    del raw["provenance"]
    with pytest.raises(RecordValidationError):
        MemoryRecord.from_dict(raw)
```

- [ ] **Step 2: Run the focused tests and verify RED**

```bash
python -m pytest tests/test_records.py -q
```

Expected: import failure for `mneme.records`.

- [ ] **Step 3: Add the schema and minimal typed validator**

The schema must require exactly these top-level semantic fields: `record_version`, `record_id`, `record_type`, `scope`, `content`, `relations`, `provenance`, `status`; set `additionalProperties` to `false`; restrict `record_type` to `identity|instruction|fact|lesson|episode|project|relation|current`; restrict `status` to `active|superseded|withdrawn|tombstoned`.

`MemoryRecord.from_dict` must validate against the checked-in schema using `jsonschema.Draft202012Validator`, copy nested input so later caller mutation does not change the record, and raise `RecordValidationError` with the first deterministic validation error path.

`MemoryRecord.digest()` must return:

```python
sha256_domain(b"MNEME-RECORD-0.1", canonical_json_bytes(self.to_dict()))
```

- [ ] **Step 4: Run record tests and canonical regression**

```bash
python -m pytest tests/test_records.py tests/test_canonical.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 2**

```bash
git add schemas/memory-record-0.1.schema.json src/mneme tests/test_records.py
git commit -m "feat: add typed canonical memory records"
```

---

### Task 3: Transaction Envelope and Truncation-Rejection Semantics

**Files:**
- Create: `schemas/transaction-0.1.schema.json`
- Create: `src/mneme/transactions.py`
- Modify: `src/mneme/errors.py`
- Test: `tests/test_transactions.py`

**Interfaces:**
- Consumes: `MemoryRecord`, canonical JSON helpers
- Produces: `TransactionProposal.from_dict(raw: dict[str, object]) -> TransactionProposal`
- Produces: `TransactionProposal.digest() -> str`
- Produces: `TransactionProposal.validate_for_head(actual_head: str) -> None`
- Produces: `TransactionValidationError(MnemeError, ValueError)`
- Exact final marker: `MNEME_COMMIT/0.1`

- [ ] **Step 1: Write failing complete/partial transaction tests**

```python
# tests/test_transactions.py
import pytest

from mneme.transactions import TransactionProposal
from mneme.errors import TransactionValidationError


def record():
    return {
        "record_version": "mneme.memory-record/0.1",
        "record_id": "rec-001",
        "record_type": "lesson",
        "scope": {"kind": "global", "subject": "verification"},
        "content": {"text": "Synthetic lesson."},
        "relations": [],
        "provenance": {"event_id": "evt-001", "source_ref": "synthetic:test"},
        "status": "active",
    }


def transaction_dict():
    from mneme.records import MemoryRecord
    digest = MemoryRecord.from_dict(record()).digest()
    return {
        "transaction_version": "mneme.transaction/0.1",
        "transaction_id": "tx-001",
        "expected_source_head": "GENESIS",
        "declared_record_count": 1,
        "record_digests": [digest],
        "records": [record()],
        "authority_ref": "synthetic-authority:test",
        "commit_marker": "MNEME_COMMIT/0.1",
    }


def test_complete_transaction_is_valid_for_expected_head():
    tx = TransactionProposal.from_dict(transaction_dict())
    tx.validate_for_head("GENESIS")
    assert len(tx.digest()) == 64


@pytest.mark.parametrize("mutation", ["missing_marker", "wrong_count", "wrong_digest", "wrong_head"])
def test_corrupt_transaction_is_rejected(mutation):
    raw = transaction_dict()
    if mutation == "missing_marker":
        del raw["commit_marker"]
    elif mutation == "wrong_count":
        raw["declared_record_count"] = 2
    elif mutation == "wrong_digest":
        raw["record_digests"] = ["0" * 64]
    tx = TransactionProposal.from_dict(raw) if mutation != "missing_marker" else None
    with pytest.raises(TransactionValidationError):
        if mutation == "missing_marker":
            TransactionProposal.from_dict(raw)
        elif mutation == "wrong_head":
            tx.validate_for_head("f" * 64)
        else:
            tx.validate_for_head("GENESIS")
```

- [ ] **Step 2: Run tests and verify RED**

```bash
python -m pytest tests/test_transactions.py -q
```

Expected: import failure for `mneme.transactions`.

- [ ] **Step 3: Implement minimal transaction validation**

The schema must require `transaction_version`, `transaction_id`, `expected_source_head`, `declared_record_count`, `record_digests`, `records`, `authority_ref`, `commit_marker`, with `additionalProperties: false` and exact marker/version constants.

`validate_for_head(actual_head)` must check, in order:

1. exact expected-head match;
2. `declared_record_count == len(records) == len(record_digests)`;
3. each parsed `MemoryRecord.digest()` equals the corresponding declared digest;
4. `authority_ref` is a non-empty string;
5. commit marker is exact.

`digest()` hashes the canonical transaction dictionary without any self-referential digest field:

```python
sha256_domain(b"MNEME-TX-0.1", canonical_json_bytes(self.to_dict()))
```

- [ ] **Step 4: Add explicit parser-truncation negative test**

```python
def test_truncated_json_never_becomes_transaction():
    import json
    raw = '{"transaction_version":"mneme.transaction/0.1","transaction_id":"tx-001"'
    with pytest.raises(json.JSONDecodeError):
        json.loads(raw)
```

This test establishes that a syntactically incomplete model write cannot enter transaction validation at all.

- [ ] **Step 5: Run transaction + record regressions**

```bash
python -m pytest tests/test_transactions.py tests/test_records.py tests/test_canonical.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit Task 3**

```bash
git add schemas/transaction-0.1.schema.json src/mneme tests/test_transactions.py
git commit -m "feat: reject incomplete memory transactions"
```

---

### Task 4: File-First Canonical Store, Exact HEAD, and Idempotent Commit

**Files:**
- Create: `src/mneme/store.py`
- Modify: `src/mneme/errors.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Consumes: `TransactionProposal`
- Produces: `MemoryStore(root: Path)`
- Produces: `MemoryStore.initialize() -> None`
- Produces: `MemoryStore.head() -> str`
- Produces: `MemoryStore.commit(tx: TransactionProposal) -> CommitReceipt`
- Produces: `MemoryStore.iter_committed_transactions() -> Iterator[dict[str, object]]`
- Produces: `CommitReceipt(transaction_digest: str, previous_head: str, new_head: str, idempotent: bool)`
- Produces: `StoreConflictError`, `StoreIntegrityError`

- [ ] **Step 1: Write failing store tests**

```python
# tests/test_store.py
from pathlib import Path
import pytest

from mneme.store import MemoryStore
from mneme.transactions import TransactionProposal
from mneme.errors import StoreConflictError
from tests.test_transactions import transaction_dict


def test_fresh_store_starts_at_genesis(tmp_path: Path):
    store = MemoryStore(tmp_path / "memory.mlfdir")
    store.initialize()
    assert store.head() == "GENESIS"


def test_commit_advances_head_and_is_replay_idempotent(tmp_path: Path):
    store = MemoryStore(tmp_path / "memory.mlfdir")
    store.initialize()
    tx = TransactionProposal.from_dict(transaction_dict())
    first = store.commit(tx)
    second = store.commit(tx)
    assert first.new_head != "GENESIS"
    assert second.new_head == first.new_head
    assert second.idempotent is True
    assert list(store.iter_committed_transactions()) == [tx.to_dict()]


def test_stale_expected_head_is_rejected_without_new_commit(tmp_path: Path):
    store = MemoryStore(tmp_path / "memory.mlfdir")
    store.initialize()
    tx = TransactionProposal.from_dict(transaction_dict())
    store.commit(tx)
    with pytest.raises(StoreConflictError):
        store.commit(TransactionProposal.from_dict(transaction_dict() | {"transaction_id": "tx-stale"}))
    assert len(list(store.iter_committed_transactions())) == 1
```

- [ ] **Step 2: Run tests and verify RED**

```bash
python -m pytest tests/test_store.py -q
```

Expected: import failure for `mneme.store`.

- [ ] **Step 3: Implement immutable transaction publication**

The store layout for the Fresh Memory Core is:

```text
memory.mlfdir/
├── HEAD
└── transactions/
    └── committed/
        └── <transaction-digest>.json
```

Commit algorithm:

1. read current HEAD;
2. if transaction digest already exists, verify the existing bytes equal the canonical proposal and return its existing receipt as idempotent;
3. validate transaction against current HEAD;
4. compute `new_head = sha256_domain(b"MNEME-HEAD-0.1", current_head.encode("ascii") + b"\0" + tx.digest().encode("ascii"))`;
5. write canonical transaction bytes plus one terminal LF to a temporary file in `transactions/committed/`;
6. `os.replace` the temporary file to `<transaction-digest>.json` only if the final path is not already present; if it appeared concurrently, verify byte equality or fail closed;
7. replace `HEAD` through a same-directory temporary file containing `<new_head>\n`;
8. return a `CommitReceipt`.

`iter_committed_transactions()` follows logical history from commit metadata stored inside a sidecar receipt or transaction index; do not use lexical filename order as causal order.

- [ ] **Step 4: Add corruption checks**

Add tests that manually alter `HEAD` to invalid UTF-8/invalid digest text and alter a committed transaction file after commit. `head()` or iteration must raise `StoreIntegrityError`; readable-but-mutated bytes are not accepted.

- [ ] **Step 5: Run store and transaction regressions**

```bash
python -m pytest tests/test_store.py tests/test_transactions.py tests/test_records.py tests/test_canonical.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit Task 4**

```bash
git add src/mneme tests/test_store.py
git commit -m "feat: add exact-head file-first memory store"
```

---

### Task 5: Auditable Routes and Scope Isolation

**Files:**
- Create: `schemas/route-0.1.schema.json`
- Create: `src/mneme/routes.py`
- Test: `tests/test_routes.py`

**Interfaces:**
- Consumes: committed `MemoryRecord` objects
- Produces: `Route.from_dict(raw: dict[str, object]) -> Route`
- Produces: `RouteResolver.resolve(route: Route, records: Iterable[MemoryRecord], authorized_scopes: set[str]) -> RouteResult`
- Produces: `RouteResult(records: tuple[MemoryRecord, ...], included_ids: tuple[str, ...], omitted: tuple[Omission, ...])`
- `Omission` includes `record_id` and machine-readable `reason`.

- [ ] **Step 1: Write failing route tests**

```python
# tests/test_routes.py
from mneme.records import MemoryRecord
from mneme.routes import Route, RouteResolver


def rec(record_id, scope):
    return MemoryRecord.from_dict({
        "record_version": "mneme.memory-record/0.1",
        "record_id": record_id,
        "record_type": "fact",
        "scope": {"kind": scope.split("/", 1)[0], "subject": scope.split("/", 1)[1] if "/" in scope else "core"},
        "content": {"text": record_id},
        "relations": [],
        "provenance": {"event_id": f"evt-{record_id}", "source_ref": "synthetic:test"},
        "status": "active",
    })


def test_identity_route_cannot_cross_identity_scope_without_authorization():
    route = Route.from_dict({
        "route_version": "mneme.route/0.1",
        "route_id": "route://identity/a/bootstrap",
        "scope_prefixes": ["identity/a"],
        "record_types": ["fact"],
    })
    records = [rec("a1", "identity/a"), rec("b1", "identity/b")]
    result = RouteResolver().resolve(route, records, {"identity/a"})
    assert result.included_ids == ("a1",)
    assert any(o.record_id == "b1" for o in result.omitted)
```

- [ ] **Step 2: Run tests and verify RED**

```bash
python -m pytest tests/test_routes.py -q
```

Expected: import failure for `mneme.routes`.

- [ ] **Step 3: Implement deterministic route filtering**

Routes select only active records whose normalized scope path begins with one declared `scope_prefix`, whose type is allowed when `record_types` is non-empty, and whose scope is in `authorized_scopes` or is `global`. Preserve canonical input order and explain every omission with one of: `scope_mismatch`, `unauthorized_scope`, `type_mismatch`, `inactive`.

- [ ] **Step 4: Add global + project route positive/negative cases**

Tests must prove:

- global records can be included by a global route;
- project A route excludes project B;
- adding explicit `project/b` to `authorized_scopes` alone does not override a route whose declared prefix is only `project/a`;
- changing a route does not mutate the underlying records.

- [ ] **Step 5: Run route regression suite**

```bash
python -m pytest tests/test_routes.py tests/test_records.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit Task 5**

```bash
git add schemas/route-0.1.schema.json src/mneme/routes.py tests/test_routes.py
git commit -m "feat: add auditable scoped memory routes"
```

---

### Task 6: Budgeted Markdown and Model Projection

**Files:**
- Create: `schemas/projection-manifest-0.1.schema.json`
- Create: `src/mneme/projection.py`
- Test: `tests/test_projection.py`

**Interfaces:**
- Consumes: `RouteResult`, canonical source head
- Produces: `project_markdown(records, *, source_head: str, route_id: str, byte_budget: int) -> ProjectionResult`
- Produces: `ProjectionResult(content: bytes, manifest: dict[str, object])`
- Manifest fields: source head, route, byte budget, included IDs, omitted IDs/reasons, content SHA-256, exact byte count.

- [ ] **Step 1: Write failing budget tests**

```python
# tests/test_projection.py
from mneme.projection import project_markdown
from tests.test_routes import rec


def test_projection_never_exceeds_hard_byte_budget():
    records = [rec(f"r{i}", "global/core") for i in range(20)]
    result = project_markdown(records, source_head="a" * 64, route_id="route://global/tier0", byte_budget=180)
    assert len(result.content) <= 180
    assert result.manifest["byte_count"] == len(result.content)
    assert result.manifest["source_head"] == "a" * 64
    assert result.manifest["omitted"]


def test_different_budgets_bind_to_same_canonical_head_without_mutation():
    records = [rec(f"r{i}", "global/core") for i in range(5)]
    before = [r.to_dict() for r in records]
    small = project_markdown(records, source_head="b" * 64, route_id="route://global/tier0", byte_budget=100)
    large = project_markdown(records, source_head="b" * 64, route_id="route://global/tier0", byte_budget=500)
    assert small.content != large.content
    assert small.manifest["source_head"] == large.manifest["source_head"]
    assert [r.to_dict() for r in records] == before
```

- [ ] **Step 2: Run tests and verify RED**

```bash
python -m pytest tests/test_projection.py -q
```

Expected: import failure for `mneme.projection`.

- [ ] **Step 3: Implement whole-record bounded materialization**

Render each record as a complete block:

```text
## <record_id> [<record_type>]
<content.text>

```

Never slice UTF-8 bytes or a rendered record block to satisfy the budget. Add whole blocks until the next whole block would exceed `byte_budget`; then omit that record and all later records with reason `budget_exceeded`. If even the fixed projection header cannot fit, raise `ProjectionBudgetError` instead of returning a truncated header.

Manifest content digest must bind exact returned bytes.

- [ ] **Step 4: Add multibyte UTF-8 boundary test**

Use Chinese text and a byte budget one byte smaller than the next complete block. Assert the result decodes as UTF-8 and either contains the whole block or omits it; never accept a cut multibyte sequence or half block.

- [ ] **Step 5: Run projection + route regressions**

```bash
python -m pytest tests/test_projection.py tests/test_routes.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit Task 6**

```bash
git add schemas/projection-manifest-0.1.schema.json src/mneme/projection.py tests/test_projection.py
git commit -m "feat: add bounded rebuildable memory projections"
```

---

### Task 7: Non-Destructive Markdown Import Proposals

**Files:**
- Create: `src/mneme/markdown_import.py`
- Create: `fixtures/synthetic/memory.md`
- Test: `tests/test_markdown_import.py`

**Interfaces:**
- Produces: `propose_markdown_import(path: Path) -> ImportProposal`
- `ImportProposal.records` is a tuple of uncommitted record dictionaries.
- `ImportProposal.loss_report` contains `source_sha256`, block count, mapped count, uncertain count, unmapped blocks with source line ranges.
- Import never returns write authority and never modifies `path`.

- [ ] **Step 1: Write failing non-destruction and loss-report tests**

```python
# tests/test_markdown_import.py
import hashlib

from mneme.markdown_import import propose_markdown_import


def test_markdown_import_never_mutates_source_and_reports_uncertain_blocks(tmp_path):
    source = tmp_path / "MEMORY.md"
    source.write_text("# Memory\n\n- Keep this rule.\n\nFree prose with unclear scope.\n", encoding="utf-8")
    before = source.read_bytes()
    proposal = propose_markdown_import(source)
    assert source.read_bytes() == before
    assert proposal.loss_report["source_sha256"] == hashlib.sha256(before).hexdigest()
    assert proposal.loss_report["block_count"] >= 2
    assert proposal.loss_report["uncertain_count"] >= 1
    assert proposal.committed is False
```

- [ ] **Step 2: Run tests and verify RED**

```bash
python -m pytest tests/test_markdown_import.py -q
```

Expected: import failure for `mneme.markdown_import`.

- [ ] **Step 3: Implement a bounded structural parser, not semantic guessing**

For v0.1, recognize only:

- ATX headings (`#` through `######`) as section context;
- unordered list items beginning `- ` as `instruction` proposals when under a heading whose normalized text is exactly `standing instructions` or `rules`;
- all other non-empty paragraph blocks as `unmapped` or `uncertain` entries in the loss report.

Do not infer resident identity, authority, relation, or dates from prose. Proposed records use synthetic/import provenance pointing to source SHA-256 and line range.

- [ ] **Step 4: Add silent-loss red control**

Create a source containing a fenced code block and table. Assert both appear in the loss report if the importer does not map them. The acceptance condition is explicit loss accounting, not fake completeness.

- [ ] **Step 5: Run import + canonical regression suite**

```bash
python -m pytest tests/test_markdown_import.py tests/test_records.py tests/test_canonical.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit Task 7**

```bash
git add src/mneme/markdown_import.py fixtures/synthetic/memory.md tests/test_markdown_import.py
git commit -m "feat: add non-destructive Markdown memory import proposals"
```

---

### Task 8: Read-Only SOACR Adapter Contract

**Files:**
- Create: `src/mneme/adapters/__init__.py`
- Create: `src/mneme/adapters/soacr.py`
- Test: `tests/test_soacr_adapter.py`

**Interfaces:**
- Produces: `MemoryNeedRequest(identity_scope: str, route_id: str, byte_budget: int)`
- Produces: `MnemeReadAdapter(store: MemoryStore, routes: Mapping[str, Route])`
- Produces: `MnemeReadAdapter.materialize(request: MemoryNeedRequest, authorized_scopes: set[str]) -> ProjectionResult`
- No write method exists in v0.1 adapter.

- [ ] **Step 1: Write failing adapter tests**

```python
# tests/test_soacr_adapter.py
import pytest

from mneme.adapters.soacr import MemoryNeedRequest, MnemeReadAdapter


def test_adapter_surface_is_read_only():
    assert not hasattr(MnemeReadAdapter, "commit")
    assert not hasattr(MnemeReadAdapter, "write")


def test_invalid_budget_is_rejected_before_materialization():
    with pytest.raises(ValueError):
        MemoryNeedRequest(identity_scope="identity/a", route_id="route://identity/a/bootstrap", byte_budget=0)
```

- [ ] **Step 2: Run tests and verify RED**

```bash
python -m pytest tests/test_soacr_adapter.py -q
```

Expected: import failure for `mneme.adapters.soacr`.

- [ ] **Step 3: Implement the minimal read contract**

The adapter must:

1. read only committed records from `MemoryStore`;
2. resolve only the named route;
3. pass `authorized_scopes` into `RouteResolver`;
4. call `project_markdown` with the exact current canonical head and request budget;
5. expose no canonical mutation method.

- [ ] **Step 4: Add scope-leak negative integration test**

Construct synthetic identity A and B records. Ask through identity A route while authorizing only A. Assert B content is absent from content and appears only as a machine-readable omission reason where policy permits reporting the ID; private content text itself must never appear in the omission metadata.

- [ ] **Step 5: Run adapter + route + projection regressions**

```bash
python -m pytest tests/test_soacr_adapter.py tests/test_routes.py tests/test_projection.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit Task 8**

```bash
git add src/mneme/adapters tests/test_soacr_adapter.py
git commit -m "feat: expose read-only SOACR memory adapter"
```

---

### Task 9: Fresh Memory Core Acceptance Gate

**Files:**
- Create: `fixtures/synthetic/records.jsonl`
- Create: `scripts/validate_fresh_memory_core.py`
- Create: `tests/test_acceptance.py`
- Modify: `README.md`

**Interfaces:**
- Produces CLI validation script exit `0` only when A0-A6 pass.
- Produces JSON receipt with `profile`, `status`, `cases`, `controls`, `canonical_head`, and `source_commit` when available.
- Does not read real Residence data and does not access network.

- [ ] **Step 1: Write failing acceptance test**

```python
# tests/test_acceptance.py
import json
import subprocess
import sys


def test_fresh_memory_core_acceptance_gate(tmp_path):
    output = tmp_path / "receipt.json"
    proc = subprocess.run(
        [sys.executable, "scripts/validate_fresh_memory_core.py", "--output", str(output)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["profile"] == "MLF-RM/0.1"
    assert receipt["status"] == "PASS"
    assert set(receipt["cases"]) >= {"A0", "A1", "A2", "A3", "A4", "A5", "A6"}
    assert all(receipt["cases"][case] == "PASS" for case in ["A0", "A1", "A2", "A3", "A4", "A5", "A6"])
```

- [ ] **Step 2: Run test and verify RED**

```bash
python -m pytest tests/test_acceptance.py -q
```

Expected: failure because the validation script does not exist.

- [ ] **Step 3: Implement the deterministic acceptance runner**

The runner must create its own temporary synthetic store and execute:

- A0: repeat the same canonical input twice and compare canonical bytes/digests;
- A1: inject truncated JSON, missing marker, wrong count, wrong digest, and stale head, confirming zero additional canonical commit for every control;
- A2: create two different-budget projections bound to one canonical head and verify source records unchanged;
- A3: assert every returned projection byte length is within hard budget and explicit overflow path is tested;
- A4: verify identity A route cannot retrieve identity B private record;
- A5: import a temporary Markdown source, verify source hash unchanged, and verify explicit loss report;
- A6: count at least one negative control for every A0-A5 positive family.

Receipt JSON uses `canonical_json_bytes(receipt) + b"\n"` and never includes local private paths.

- [ ] **Step 4: Add README verification commands**

Document exactly:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts/validate_fresh_memory_core.py --output fresh-memory-core.json
```

State that this is synthetic/local evidence only and grants no production Residence write authority.

- [ ] **Step 5: Run full verification**

```bash
python -m pytest -q
python scripts/validate_fresh_memory_core.py --output fresh-memory-core.json
```

Expected: pytest exits `0`; acceptance script exits `0`; receipt status is `PASS` with A0-A6 all `PASS`.

- [ ] **Step 6: Corrupt one fixture and prove the gate turns red**

Temporarily alter one declared record digest in the synthetic fixture, run the acceptance script, and confirm non-zero exit or `status: FAIL`. Restore the fixture and rerun the full verification to PASS before commit.

- [ ] **Step 7: Commit Task 9**

```bash
git add fixtures/synthetic/records.jsonl scripts/validate_fresh_memory_core.py tests/test_acceptance.py README.md
git commit -m "test: close MNEME Fresh Memory Core acceptance gate"
```

---

## Plan Self-Review

### Spec coverage

- Canonical typed memory records: Task 2.
- Deterministic canonical bytes/digests: Tasks 1-4, acceptance A0.
- Proposal-only, complete-transaction commit: Tasks 3-4.
- Truncation rejection: Task 3, acceptance A1.
- Exact-head/idempotent file-first state: Task 4.
- Global/identity/project route isolation: Task 5, acceptance A4.
- Budget-bounded Markdown/model projection: Task 6, acceptance A2-A3.
- Non-destructive Markdown migration with loss accounting: Task 7, acceptance A5.
- Synthetic SOACR-facing provider/read boundary: Task 8.
- Positive + corrupted negative evidence: every task plus acceptance A6.
- Dynamic DB, vector routing, real Residence, live LIMEN, full SOACR writeback, federation, UI: explicitly deferred.

### Placeholder scan

No `TBD`, `TODO`, or unspecified implementation step is permitted by this plan. Exact interfaces, constants, failure cases, test commands, and commit boundaries are named above.

### Type consistency

The plan uses one record type (`MemoryRecord`), one transaction type (`TransactionProposal`), one store (`MemoryStore`), one routing result (`RouteResult`), one projection result (`ProjectionResult`), and one SOACR request (`MemoryNeedRequest`) consistently across downstream tasks.

## Execution Order

Execute Tasks 1 through 9 strictly in order. Do not begin live LIMEN integration, real Residence migration, a dynamic database backend, vector search, or background autonomous writeback during this plan.
