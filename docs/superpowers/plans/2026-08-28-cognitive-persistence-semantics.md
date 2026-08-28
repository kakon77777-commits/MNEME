# MNEME-CPS/0.1 Cognitive Persistence Semantics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an observation-only CPS/0.1 sidecar runtime that classifies persistence candidates conservatively, preserves an evidential floor, produces non-authoritative factorization and cognitive-seed proposals, and proves C0–C13 without mutating MLF-RM/0.1 canonical memory.

**Architecture:** Keep `MemoryRecord`, `MemoryStore`, MLF-RM/0.1, and MNEME-MD/0.1 unchanged. New CPS objects live in focused modules under `src/mneme/cps/` and refer to existing records by ID/reference; deterministic rule-based assessment is separated from proposal packaging, while model-assisted semantics remain out of the first implementation. The acceptance runner uses synthetic public fixtures and explicitly proves that CPS has no delete/commit/de-materialization path.

**Tech Stack:** Python 3.11+, standard library (`dataclasses`, `enum`, `hashlib`, `json`, `pathlib`, `typing`), existing `jsonschema>=4.23`, `pytest>=8.0`.

**Spec:** `docs/superpowers/specs/2026-08-28-cognitive-persistence-semantics-design.md`

## Global Constraints

- Base canonical format remains `MLF-RM/0.1`; CPS/0.1 is additive and must not modify `MemoryRecord` schema or canonical transaction semantics.
- Markdown compatibility remains `MNEME-MD/0.1`; CPS consumes resulting records/proposals but does not alter Markdown mapping semantics.
- Candidate dispositions are exactly `PRESERVE`, `STRUCTURALIZE`, `GENERATIZE`, `RECOMPUTE`, `DISCARD`, and `UNKNOWN`.
- Every CPS/0.1 public object that carries `authority` must require `authority: false`.
- `UNKNOWN` is a successful conservative result and defaults to preserve/review behavior.
- `GENERATIZE != SAFE_TO_DELETE`; `DISCARD` means active-memory-retirement candidate only.
- No public CPS API may delete, tombstone, rewrite, archive-move, replace canonical records, commit factorization, or promote a seed.
- Public tests and fixtures use synthetic data only; no real Residence content, path, resident list, identity evidence, or private source digest is committed.
- Model-assisted classification is outside the first implementation milestone.
- Deterministic CPS outputs use canonical JSON and domain-separated SHA-256 fingerprints.
- Existing Fresh Memory Core and MNEME-MD tests must remain green.

---

## Planned Files

```text
schemas/persistence-assessment-0.1.schema.json
schemas/factorization-proposal-0.1.schema.json
schemas/cognitive-seed-proposal-0.1.schema.json
schemas/recomputation-reference-0.1.schema.json
schemas/equivalence-contract-0.1.schema.json
src/mneme/cps/__init__.py
src/mneme/cps/models.py
src/mneme/cps/rules.py
src/mneme/cps/factorization.py
src/mneme/cps/seed.py
src/mneme/cps/adapter.py
fixtures/synthetic/cps-records.jsonl
scripts/validate_cognitive_persistence_semantics.py
tests/test_cps_models.py
tests/test_cps_rules.py
tests/test_cps_factorization.py
tests/test_cps_seed.py
tests/test_cps_adapter.py
tests/test_cps_acceptance.py
.github/workflows/cognitive-persistence-semantics.yml
README.md
pyproject.toml
src/mneme/__init__.py
```

---

### Task 1: PersistenceAssessment Schema, Model, and Deterministic Fingerprint

**Files:**
- Create: `schemas/persistence-assessment-0.1.schema.json`
- Create: `src/mneme/cps/__init__.py`
- Create: `src/mneme/cps/models.py`
- Modify: `src/mneme/errors.py`
- Test: `tests/test_cps_models.py`

**Interfaces:**
- Consumes: `mneme.canonical.canonical_json_bytes`, `mneme.canonical.sha256_domain`.
- Produces:
  - `PersistenceCandidate(str, Enum)` with six exact values.
  - `AssessmentMethod(str, Enum)` with `EXPLICIT_RULE`, `STRUCTURAL_RULE`, `MODEL_PROPOSAL`, `HUMAN_REVIEW`.
  - `RiskClass(str, Enum)` with `LOW`, `MEDIUM`, `HIGH`, `BLOCKED`.
  - `ReviewState(str, Enum)` with `UNREVIEWED`, `ACCEPTED_FOR_EXPERIMENT`, `REJECTED`, `SUPERSEDED`.
  - `PersistenceAssessment.from_dict(raw) -> PersistenceAssessment`.
  - `PersistenceAssessment.to_dict() -> dict[str, object]`.
  - `PersistenceAssessment.fingerprint() -> str`.
  - `CpsValidationError(MnemeError, ValueError)`.

- [ ] **Step 1: Write failing assessment tests**

```python
from copy import deepcopy
import pytest

from mneme.cps.models import PersistenceAssessment
from mneme.errors import CpsValidationError


def base_assessment():
    return {
        "assessment_version": "mneme.persistence-assessment/0.1",
        "assessment_id": "pa-placeholder",
        "subject_refs": ["record-decision-1"],
        "candidate": "PRESERVE",
        "basis": {
            "method": "EXPLICIT_RULE",
            "deterministic": True,
            "reason_codes": ["EXPLICIT_DECISION"],
            "evidence_refs": ["record-decision-1"],
        },
        "required_preservations": ["record-decision-1"],
        "risk": "LOW",
        "review_state": "UNREVIEWED",
        "authority": False,
    }


def test_assessment_requires_authority_false():
    raw = base_assessment()
    raw["authority"] = True
    with pytest.raises(CpsValidationError):
        PersistenceAssessment.from_dict(raw)


def test_deterministic_assessment_fingerprint_ignores_assessment_id_only():
    a = base_assessment()
    b = deepcopy(a)
    b["assessment_id"] = "different-id"
    assert PersistenceAssessment.from_dict(a).fingerprint() == PersistenceAssessment.from_dict(b).fingerprint()


def test_fingerprint_changes_when_candidate_changes():
    a = base_assessment()
    b = deepcopy(a)
    b["candidate"] = "UNKNOWN"
    b["risk"] = "BLOCKED"
    assert PersistenceAssessment.from_dict(a).fingerprint() != PersistenceAssessment.from_dict(b).fingerprint()
```

- [ ] **Step 2: Run and verify RED**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_cps_models.py -q
```

Expected: import failure because `mneme.cps.models` does not exist.

- [ ] **Step 3: Add the assessment JSON schema**

The schema must use `additionalProperties: false`, require every field shown above, require non-empty `subject_refs`, and constrain all enums to the CPS/0.1 vocabulary. `authority` must be `const: false`.

- [ ] **Step 4: Implement minimal immutable model and fingerprint**

Fingerprint input is the assessment dictionary with `assessment_id` removed. Use:

```python
sha256_domain(
    b"MNEME-CPS-ASSESSMENT-0.1",
    canonical_json_bytes(fingerprint_input),
)
```

For deterministic assessments, expose helper:

```python
def deterministic_assessment_id(assessment_without_id: dict[str, object]) -> str:
    return "pa-" + sha256_domain(
        b"MNEME-CPS-ASSESSMENT-ID-0.1",
        canonical_json_bytes(assessment_without_id),
    )
```

The model must deep-copy inbound/outbound dictionaries.

- [ ] **Step 5: Add negative shape tests**

Require `CpsValidationError` for:

```text
unknown candidate
unknown method
empty subject_refs
empty reason_codes
invalid risk
invalid review_state
authority=true
additional field
```

- [ ] **Step 6: Run focused regression**

```bash
PYTHONPATH=src python -m pytest tests/test_cps_models.py tests/test_canonical.py tests/test_records.py -q
```

- [ ] **Step 7: Commit Task 1**

```bash
git add schemas/persistence-assessment-0.1.schema.json src/mneme/cps src/mneme/errors.py tests/test_cps_models.py
git commit -m "feat: add CPS persistence assessment model"
```

---

### Task 2: Conservative Deterministic Rule Engine and UNKNOWN Fallback

**Files:**
- Create: `src/mneme/cps/rules.py`
- Test: `tests/test_cps_rules.py`
- Create: `fixtures/synthetic/cps-records.jsonl`

**Interfaces:**
- Consumes: `MemoryRecord`, `PersistenceAssessment`, deterministic assessment-ID helper.
- Produces:
  - `AssessmentContext` dataclass with explicit optional evidence flags and recomputation policy input.
  - `assess_record(record: MemoryRecord, context: AssessmentContext) -> PersistenceAssessment`.
  - deterministic reason-code mapping only; no free-text semantic inference.

- [ ] **Step 1: Write failing explicit-rule tests**

```python
from mneme.cps.rules import AssessmentContext, assess_record
from mneme.records import MemoryRecord


def record(record_id, record_type, text):
    return MemoryRecord.from_dict({
        "record_version": "mneme.memory-record/0.1",
        "record_id": record_id,
        "record_type": record_type,
        "scope": {"kind": "global", "subject": "synthetic"},
        "content": {"text": text},
        "relations": [],
        "provenance": {"event_id": "event-" + record_id, "source_ref": "synthetic:" + record_id},
        "status": "active",
    })


def test_explicit_decision_is_preserve_candidate():
    result = assess_record(
        record("r1", "fact", "Synthetic accepted decision."),
        AssessmentContext(explicit_decision=True),
    )
    assert result.to_dict()["candidate"] == "PRESERVE"
    assert "EXPLICIT_DECISION" in result.to_dict()["basis"]["reason_codes"]


def test_insufficient_evidence_falls_back_to_unknown():
    result = assess_record(record("r2", "fact", "Ambiguous material."), AssessmentContext())
    raw = result.to_dict()
    assert raw["candidate"] == "UNKNOWN"
    assert raw["risk"] == "BLOCKED"
    assert "INSUFFICIENT_EVIDENCE" in raw["basis"]["reason_codes"]
```

- [ ] **Step 2: Run and verify RED**

```bash
PYTHONPATH=src python -m pytest tests/test_cps_rules.py -q
```

Expected: import failure because `mneme.cps.rules` does not exist.

- [ ] **Step 3: Implement `AssessmentContext`**

Fields are explicit booleans/references only:

```python
@dataclass(frozen=True)
class AssessmentContext:
    explicit_decision: bool = False
    identity_or_authority_evidence: bool = False
    historical_observation: bool = False
    structural_dependency: bool = False
    structural_state: bool = False
    derivable_explanation: bool = False
    reconstruction_recipe_ref: str | None = None
    obligation_set_ref: str | None = None
    freshness_required: bool = False
    external_source_ref: str | None = None
    previous_observation_ref: str | None = None
    ephemeral_working_state: bool = False
    superseded_materialization: bool = False
    conflicting_evidence: bool = False
```

No text classifier, regex keyword classifier, embedding, LLM, or similarity matcher is allowed.

- [ ] **Step 4: Implement conservative precedence**

Use this exact safety precedence:

```text
conflicting_evidence -> UNKNOWN / BLOCKED
identity_or_authority_evidence -> PRESERVE / LOW
explicit_decision -> PRESERVE / LOW
historical_observation without freshness_required -> PRESERVE / LOW
freshness_required + external_source_ref -> RECOMPUTE / MEDIUM
structural_dependency or structural_state -> STRUCTURALIZE / MEDIUM
derivable_explanation + reconstruction_recipe_ref + obligation_set_ref -> GENERATIZE / HIGH
ephemeral_working_state + no evidence flags -> DISCARD / HIGH
otherwise -> UNKNOWN / BLOCKED
```

If `freshness_required` is true but `external_source_ref` is absent, return `UNKNOWN/BLOCKED` with `INSUFFICIENT_EVIDENCE` rather than `RECOMPUTE`.

- [ ] **Step 5: Add deterministic replay and destructive-order controls**

Test identical `(record, context)` twice and require identical canonical assessment bytes and fingerprint. Also assert evidence-sensitive flags win over `ephemeral_working_state=True`.

- [ ] **Step 6: Add synthetic fixture records**

`fixtures/synthetic/cps-records.jsonl` contains at least:

```text
synthetic explicit decision
synthetic authority-sensitive fact
synthetic dependency fact
synthetic derivable explanation
synthetic freshness-sensitive observation
synthetic ephemeral scratch fact
synthetic ambiguous fact
```

Each line is standalone JSON and contains no real user/Residence content.

- [ ] **Step 7: Run focused regression**

```bash
PYTHONPATH=src python -m pytest tests/test_cps_rules.py tests/test_cps_models.py -q
```

- [ ] **Step 8: Commit Task 2**

```bash
git add src/mneme/cps/rules.py tests/test_cps_rules.py fixtures/synthetic/cps-records.jsonl
git commit -m "feat: add conservative CPS rule assessment"
```

---

### Task 3: Evidential Floor and FactorizationProposal

**Files:**
- Create: `schemas/factorization-proposal-0.1.schema.json`
- Create: `src/mneme/cps/factorization.py`
- Test: `tests/test_cps_factorization.py`

**Interfaces:**
- Consumes: validated `PersistenceAssessment` objects and source record IDs.
- Produces:
  - `FactorizationProposal.from_dict(raw) -> FactorizationProposal`.
  - `FactorizationProposal.to_dict()`.
  - `FactorizationProposal.fingerprint()`.
  - `build_factorization_proposal(...) -> FactorizationProposal`.

- [ ] **Step 1: Write failing evidential-floor tests**

```python
import pytest

from mneme.cps.factorization import build_factorization_proposal
from mneme.errors import CpsValidationError


def test_factorization_cannot_drop_required_preservations(preserve_assessment):
    with pytest.raises(CpsValidationError):
        build_factorization_proposal(
            assessments=[preserve_assessment],
            source_refs=["record-decision-1"],
            anchors=[],
            structure=[],
            generators=[],
            obligations=[],
            provenance_refs=["record-decision-1"],
            recompute_refs=[],
            unresolved_refs=[],
        )
```

- [ ] **Step 2: Run and verify RED**

```bash
PYTHONPATH=src python -m pytest tests/test_cps_factorization.py -q
```

- [ ] **Step 3: Define factorization schema**

Required fields:

```text
proposal_version
proposal_id
source_assessments
source_refs
anchors
structure
generators
obligations
provenance_refs
recompute_refs
unresolved_refs
authority=false
```

All collections are explicit arrays. An empty array is allowed where semantically valid; omission of a field is not.

- [ ] **Step 4: Implement evidential-floor validation**

For every source assessment, collect `required_preservations`. Every required preservation must be present in at least one of:

```text
anchors
provenance_refs
unresolved_refs
```

Otherwise fail closed with `CpsValidationError`.

The builder also requires every `source_assessments` ID to correspond to an assessment passed to the builder.

- [ ] **Step 5: Implement deterministic fingerprint**

Use:

```python
sha256_domain(
    b"MNEME-CPS-FACTORIZATION-0.1",
    canonical_json_bytes(proposal_without_proposal_id),
)
```

and deterministic proposal IDs using a separate `MNEME-CPS-FACTORIZATION-ID-0.1` domain.

- [ ] **Step 6: Add provenance and authority negative tests**

Reject:

```text
unknown source assessment ID
required evidence omitted
source_ref absent from provenance/anchor/unresolved coverage
authority=true
unknown field
```

- [ ] **Step 7: Run focused regression**

```bash
PYTHONPATH=src python -m pytest tests/test_cps_factorization.py tests/test_cps_rules.py -q
```

- [ ] **Step 8: Commit Task 3**

```bash
git add schemas/factorization-proposal-0.1.schema.json src/mneme/cps/factorization.py tests/test_cps_factorization.py
git commit -m "feat: add CPS factorization proposals"
```

---

### Task 4: RecomputationReference and EquivalenceContract

**Files:**
- Create: `schemas/recomputation-reference-0.1.schema.json`
- Create: `schemas/equivalence-contract-0.1.schema.json`
- Modify: `src/mneme/cps/models.py`
- Test: `tests/test_cps_models.py`

**Interfaces:**
- `RecomputationReference.from_dict(raw) -> RecomputationReference`.
- `EquivalenceContract.from_dict(raw) -> EquivalenceContract`.
- Both expose deterministic `to_dict()` and `fingerprint()`.

- [ ] **Step 1: Write failing recomputation tests**

```python
import pytest
from mneme.cps.models import RecomputationReference
from mneme.errors import CpsValidationError


def test_recompute_requires_freshness_and_failure_policy():
    raw = {
        "reference_version": "mneme.recomputation-reference/0.1",
        "reference_id": "rr-x",
        "source_kind": "web",
        "source_ref": "synthetic://source/current-version",
        "query_or_operation": "fetch-current-version",
        "freshness_requirement": "before-use",
        "previous_observation_ref": "record-version-1",
        "failure_policy": "FAIL_CLOSED",
        "authority": False,
    }
    assert RecomputationReference.from_dict(raw).to_dict()["freshness_requirement"] == "before-use"
```

- [ ] **Step 2: Write failing equivalence-contract tests**

```python
from mneme.cps.models import EquivalenceContract


def test_equivalence_contract_uses_observation_surfaces_not_token_equality():
    raw = {
        "contract_version": "mneme.equivalence-contract/0.1",
        "contract_id": "eq-x",
        "observation_surfaces": [
            {"kind": "DECISION_MUST_NOT_REVERSE", "subject_ref": "record-decision-1"},
            {"kind": "AUTHORITY_MUST_NOT_ESCALATE", "subject_ref": "record-authority-1"},
        ],
        "forbidden_equalities": ["TOKEN_EQUALITY", "TRACE_EQUALITY"],
        "authority": False,
    }
    contract = EquivalenceContract.from_dict(raw)
    assert "TOKEN_EQUALITY" in contract.to_dict()["forbidden_equalities"]
```

- [ ] **Step 3: Run and verify RED**

```bash
PYTHONPATH=src python -m pytest tests/test_cps_models.py -q
```

- [ ] **Step 4: Implement recomputation schema/model**

Required fields:

```text
reference_version
reference_id
source_kind
source_ref
query_or_operation
freshness_requirement
previous_observation_ref (nullable)
failure_policy
authority=false
```

`freshness_requirement` and `failure_policy` must be non-empty strings. The model does not execute the query.

- [ ] **Step 5: Implement equivalence-contract schema/model**

Allowed observation kinds for v0.1:

```text
ANCHOR_MUST_MATCH
DECISION_MUST_NOT_REVERSE
DEPENDENCY_MUST_HOLD
PROVENANCE_MUST_COVER
FRESH_STATE_REQUIRED
IDENTITY_SCOPE_MUST_MATCH
AUTHORITY_MUST_NOT_ESCALATE
```

`observation_surfaces` must be non-empty. `forbidden_equalities` is an explicit array restricted to:

```text
TOKEN_EQUALITY
TRACE_EQUALITY
```

- [ ] **Step 6: Add stale/missing/authority negative tests**

Reject a recomputation reference with missing freshness semantics, and reject either object with `authority=true` or an unknown observation kind.

- [ ] **Step 7: Run focused regression**

```bash
PYTHONPATH=src python -m pytest tests/test_cps_models.py tests/test_cps_factorization.py -q
```

- [ ] **Step 8: Commit Task 4**

```bash
git add schemas/recomputation-reference-0.1.schema.json schemas/equivalence-contract-0.1.schema.json src/mneme/cps/models.py tests/test_cps_models.py
git commit -m "feat: add CPS recomputation and equivalence contracts"
```

---

### Task 5: CognitiveSeedProposal and Completeness Validation

**Files:**
- Create: `schemas/cognitive-seed-proposal-0.1.schema.json`
- Create: `src/mneme/cps/seed.py`
- Test: `tests/test_cps_seed.py`

**Interfaces:**
- Consumes: `FactorizationProposal`, `RecomputationReference`, `EquivalenceContract`.
- Produces:
  - `CognitiveSeedProposal.from_dict(raw) -> CognitiveSeedProposal`.
  - `build_cognitive_seed_proposal(...) -> CognitiveSeedProposal`.
  - deterministic `fingerprint()`.

- [ ] **Step 1: Write failing seed-completeness test**

```python
import pytest

from mneme.cps.seed import build_cognitive_seed_proposal
from mneme.errors import CpsValidationError


def test_high_risk_seed_requires_anchor_and_equivalence_contract(generative_factorization):
    with pytest.raises(CpsValidationError):
        build_cognitive_seed_proposal(
            factorization=generative_factorization,
            anchors=[],
            structure=[{"relation": "depends_on", "source_ref": "r-a", "target_ref": "r-b"}],
            generators=[{"kind": "RECONSTRUCTION_RECIPE", "generator_ref": "synthetic://recipe/1"}],
            obligations=[{"kind": "ANCHOR_MUST_MATCH", "subject_ref": "r-a"}],
            provenance_refs=["r-a", "r-b"],
            recomputation_refs=[],
            unresolved_components=[],
            equivalence_contract=None,
        )
```

- [ ] **Step 2: Run and verify RED**

```bash
PYTHONPATH=src python -m pytest tests/test_cps_seed.py -q
```

- [ ] **Step 3: Define seed schema**

Required explicit fields:

```text
seed_version
seed_id
source_factorization
anchors
structure
generators
obligations
provenance_refs
recomputation_refs
unresolved_components
equivalence_contract
seed_fingerprint
authority=false
```

- [ ] **Step 4: Implement completeness rules**

Rules:

```text
all factorization anchors must appear in seed anchors
all factorization provenance_refs must remain covered
all factorization unresolved_refs remain explicit or are resolved by an anchor/provenance reference
all recompute_refs must resolve to supplied RecomputationReference IDs
GENERATIZE-sourced factorization requires at least one anchor
GENERATIZE-sourced factorization requires a non-empty EquivalenceContract
seed authority must be false
```

The builder does not execute reconstruction and does not replace source memory.

- [ ] **Step 5: Implement seed fingerprint**

Use canonical JSON excluding `seed_id` and `seed_fingerprint`, domain:

```text
MNEME-CPS-SEED-0.1
```

Then set `seed_fingerprint` to the resulting digest and derive deterministic `seed_id` with `MNEME-CPS-SEED-ID-0.1`.

- [ ] **Step 6: Add unresolved-reference and identity/authority negative tests**

Reject unknown recomputation refs, omitted mandatory anchors, missing equivalence contract for a generative source, or any attempt to encode an authority-grant field/value.

- [ ] **Step 7: Run focused regression**

```bash
PYTHONPATH=src python -m pytest tests/test_cps_seed.py tests/test_cps_factorization.py tests/test_cps_models.py -q
```

- [ ] **Step 8: Commit Task 5**

```bash
git add schemas/cognitive-seed-proposal-0.1.schema.json src/mneme/cps/seed.py tests/test_cps_seed.py
git commit -m "feat: add CPS cognitive seed proposals"
```

---

### Task 6: Read-Only CPS Adapter and C0–C13 Acceptance Gate

**Files:**
- Create: `src/mneme/cps/adapter.py`
- Create: `tests/test_cps_adapter.py`
- Create: `scripts/validate_cognitive_persistence_semantics.py`
- Create: `tests/test_cps_acceptance.py`

**Interfaces:**
- `CpsObservationAdapter.assess(records, contexts) -> tuple[PersistenceAssessment, ...]`.
- `CpsObservationAdapter.factorize(...) -> FactorizationProposal`.
- `CpsObservationAdapter.propose_seed(...) -> CognitiveSeedProposal`.
- Adapter exposes no `commit`, `delete`, `tombstone`, `rewrite`, `archive_move`, `update_store`, or `promote_seed` method.
- Acceptance runner emits canonical JSON receipt with `profile`, `status`, `cases`, `controls`, `source_commit`.

- [ ] **Step 1: Write failing API-surface test**

```python
from mneme.cps.adapter import CpsObservationAdapter


def test_cps_adapter_has_no_destructive_or_commit_api():
    forbidden = {
        "commit", "delete", "tombstone", "rewrite", "archive_move",
        "update_store", "replace_record", "commit_factorization", "promote_seed",
    }
    public = {name for name in dir(CpsObservationAdapter) if not name.startswith("_")}
    assert forbidden.isdisjoint(public)
```

- [ ] **Step 2: Write failing source-isolation test**

Create a `MemoryRecord`, deep-copy `record.to_dict()`, call assessment/factorization/seed paths, and require the source dictionary and record digest to remain unchanged.

- [ ] **Step 3: Run and verify RED**

```bash
PYTHONPATH=src python -m pytest tests/test_cps_adapter.py -q
```

- [ ] **Step 4: Implement read-only adapter**

The adapter composes existing CPS functions only. It accepts immutable `MemoryRecord` objects and explicit `AssessmentContext` values. It never accepts a writable `MemoryStore` and has no mutation callback.

- [ ] **Step 5: Implement deterministic acceptance runner**

Acceptance cases:

```text
C0 additive compatibility
C1 assessment isolation
C2 conservative UNKNOWN fallback
C3 evidential floor
C4 all six candidate semantics
C5 recompute freshness
C6 identity/authority non-escalation
C7 factorization provenance
C8 seed proposal completeness
C9 reconstruction isolation
C10 equivalence contract
C11 no de-materialization API
C12 deterministic replay
C13 negative evidence
```

At least one negative control must exist for every C0–C12 family.

- [ ] **Step 6: Define the acceptance control matrix explicitly**

Use these controls:

```text
C0-existing-record-digest-unchanged
C1-source-record-mutation-blocked
C2-conflicting-evidence-yields-unknown
C3-required-preservation-omission-rejected
C4-invalid-candidate-rejected
C5-recompute-without-freshness-rejected
C6-authority-true-rejected
C7-unknown-assessment-reference-rejected
C8-generative-seed-without-anchor-rejected
C9-source-memory-remains-addressable
C10-token-equality-not-used-as-equivalence
C11-forbidden-mutation-methods-absent
C12-mutated-input-changes-fingerprint
```

C13 passes only when all thirteen prior control families are present.

- [ ] **Step 7: Add acceptance subprocess test**

```python
import json
import subprocess
import sys


def test_cps_acceptance_gate(tmp_path):
    output = tmp_path / "cps.json"
    proc = subprocess.run(
        [sys.executable, "scripts/validate_cognitive_persistence_semantics.py", "--output", str(output)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["profile"] == "MNEME-CPS/0.1"
    assert receipt["status"] == "PASS"
    assert all(receipt["cases"][f"C{i}"] == "PASS" for i in range(14))
    assert receipt["controls"] >= 13
```

- [ ] **Step 8: Run full local verification**

```bash
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python scripts/validate_fresh_memory_core.py --output fresh-memory-core.json
PYTHONPATH=src python scripts/validate_memory_markdown_profile.py --output memory-markdown-profile.json
PYTHONPATH=src python scripts/validate_cognitive_persistence_semantics.py --output cps.json
python -m compileall -q src
```

- [ ] **Step 9: Inject a red control**

Temporarily mutate one CPS fixture assessment to `authority: true`, run the CPS acceptance runner, require non-zero exit and `status: FAIL`, restore the fixture, then rerun the full verification commands from Step 8 to PASS.

- [ ] **Step 10: Commit Task 6**

```bash
git add src/mneme/cps/adapter.py tests/test_cps_adapter.py scripts/validate_cognitive_persistence_semantics.py tests/test_cps_acceptance.py
git commit -m "test: close CPS observation-only acceptance"
```

---

### Task 7: Documentation, Exact-Remote CI, and 0.3.0a1 Candidate Closure

**Files:**
- Create: `.github/workflows/cognitive-persistence-semantics.yml`
- Modify: `README.md`
- Modify: `pyproject.toml`
- Modify: `src/mneme/__init__.py`

**Interfaces:**
- Candidate package version becomes `0.3.0a1`.
- CI runs the exact checked-out bytes on Python 3.11.

- [ ] **Step 1: Update README with CPS position**

Document the additive stack:

```text
MLF-RM/0.1  -> canonical memory
MNEME-MD/0.1 -> Markdown compatibility
MNEME-CPS/0.1 -> persistence assessment / factorization / seed proposals
```

Document the non-destructive boundary prominently:

```text
ASSESSMENT != AUTHORITY
RECONSTRUCTIBLE != DISPENSABLE
NO CPS/0.1 DELETION OR CANONICAL FACTORIZATION COMMIT
```

- [ ] **Step 2: Add exact-remote GitHub Actions workflow**

Use Ubuntu 24.04 and Python 3.11. Run:

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python scripts/validate_fresh_memory_core.py --output fresh-memory-core.json
python scripts/validate_memory_markdown_profile.py --output memory-markdown-profile.json
python scripts/validate_cognitive_persistence_semantics.py --output cps.json
python -m compileall -q src
```

Trigger on push and pull request changes under `src/**`, `schemas/**`, `fixtures/**`, `tests/**`, `scripts/**`, `pyproject.toml`, `README.md`, and the CPS workflow file.

- [ ] **Step 3: Bump package alpha version**

Set both:

```text
pyproject.toml -> version = "0.3.0a1"
src/mneme/__init__.py -> __version__ = "0.3.0a1"
```

Do not change MLF-RM or MNEME-MD profile-version strings.

- [ ] **Step 4: Run final local verification**

```bash
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python scripts/validate_fresh_memory_core.py --output fresh-memory-core.json
PYTHONPATH=src python scripts/validate_memory_markdown_profile.py --output memory-markdown-profile.json
PYTHONPATH=src python scripts/validate_cognitive_persistence_semantics.py --output cps.json
python -m compileall -q src
```

Expected: zero failures and all three acceptance receipts report `status: PASS`.

- [ ] **Step 5: Verify branch diff scope**

The implementation diff may contain CPS runtime/schema/tests/docs/version/workflow changes only. It must not modify the existing `schemas/memory-record-0.1.schema.json`, transaction schema, `MemoryStore.commit`, or MNEME-MD profile semantics.

- [ ] **Step 6: Commit Task 7**

```bash
git add .github/workflows/cognitive-persistence-semantics.yml README.md pyproject.toml src/mneme/__init__.py
git commit -m "release: prepare MNEME-CPS 0.1 candidate"
```

---

## Plan Self-Review

- C0 additive compatibility: Tasks 1, 6, and 7 explicitly regression-test the existing core and forbid `MemoryRecord` schema changes.
- C1 assessment isolation: Task 6 source-digest/source-dictionary control.
- C2 conservative fallback: Task 2 precedence and `UNKNOWN/BLOCKED` behavior.
- C3 evidential floor: Task 3 required-preservation coverage.
- C4 candidate semantics: Tasks 1 and 2 define and exercise all six exact values.
- C5 recompute freshness: Tasks 2 and 4 require explicit source/freshness semantics.
- C6 identity/authority non-escalation: all schemas require `authority=false`; Task 6 injects `authority=true` as a negative control.
- C7 factorization provenance: Task 3 validates source assessment and record coverage.
- C8 seed completeness: Task 5 requires anchors/provenance/recomputation/unresolved/equivalence fields explicitly.
- C9 reconstruction isolation: Task 5 packages proposals only; Task 6 proves source memory remains addressable and unmodified.
- C10 equivalence contract: Task 4 encodes observation surfaces and explicitly rejects token/trace equality as the criterion.
- C11 no de-materialization: Task 6 forbids destructive API names/behaviors; no task adds delete/tombstone/rewrite/archive movement.
- C12 deterministic replay: Tasks 1, 2, 3, 4, and 5 use canonical JSON/domain-separated fingerprints; Task 6 repeats identical inputs.
- C13 negative evidence: Task 6 requires a negative control for C0–C12 and an injected red-control run.
- The plan contains no reconstruction engine, SOACR integration, model-assisted classifier, MLF-RM/0.2 migration, or regenerative forgetting.
- `PersistenceAssessment`, `FactorizationProposal`, and `CognitiveSeedProposal` remain sidecar experiment artifacts with `authority=false`.
- No placeholder requirement remains; all runtime interfaces used by later tasks are introduced by an earlier task.
