# MNEME Private Residence Two-Pass Dry-Run Analyzer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a read-only Private Residence dry-run analyzer that runs MNEME-MD compatibility first, then MNEME-CPS persistence analysis only over mapped records, producing deterministic private/sanitized evidence without canonical mutation, prose-based persistence inference, reconstruction, or de-materialization.

**Architecture:** The subsystem is an additive `mneme.dry_run` package. PASS 1 composes the existing MNEME-MD/0.1 importer/projection and a public structural scanner wrapper; PASS 2 resolves explicit deterministic `AssessmentContext` values from exact structured metadata and delegates every persistence/factorization/seed decision to existing MNEME-CPS/0.1 APIs. The coordinator owns source integrity, risk/status aggregation, privacy rendering, evidence-bundle checksums, and deterministic replay; it never accepts a writable `MemoryStore`.

**Tech Stack:** Python 3.11+, stdlib `dataclasses`, `hashlib`, `json`, `pathlib`, existing `jsonschema>=4.23`, `pytest`, existing MNEME canonical JSON/digest helpers, MNEME-MD/0.1, MNEME-CPS/0.1.

**Spec:** `docs/superpowers/specs/2026-08-28-private-residence-two-pass-dry-run-design.md`

## Global Constraints

- Base semantic stack remains `MLF-RM/0.1 + MNEME-MD/0.1 + MNEME-CPS/0.1`; do not evolve `MemoryRecord`, `MemoryStore`, MLF-RM transactions, or existing Markdown mapping semantics.
- Dry-run report version is exactly `mneme.private-residence-dry-run/0.2`.
- Package candidate becomes `mneme-memory==0.4.0a1` only after all implementation tasks and acceptance gates pass.
- The analyzer MUST NOT accept a writable `MemoryStore`.
- PASS 2 subjects MUST be a subset of PASS 1 mapped records.
- PASS 2 MUST NOT inspect `content.text`, raw paragraph/list text, raw heading text, regex over source text, edit distance, semantic similarity, embeddings, or LLM output to resolve persistence semantics.
- Exact structured policy selectors are limited to: `section_id`, `record_type`, `route_hint`, `scope_kind`, `scope_subject`, `block_kind`.
- Context resolution precedence is: exact record override -> deterministic policy match -> policy conflict -> default empty `AssessmentContext`.
- Conflicting matching rules MUST NOT be resolved by rule order; non-identical contexts produce `AssessmentContext(conflicting_evidence=True)`.
- Every PASS 1 mapped record MUST receive exactly one CPS `PersistenceAssessment`.
- `UNKNOWN` is a valid conservative assessment and is never auto-promoted.
- `FACTORIZE READINESS != FACTORIZATION GENERATION`.
- Actual `FactorizationProposal` / `CognitiveSeedProposal` construction occurs only from explicit caller intents and existing CPS builders.
- `RECOMPUTE` analysis performs no network calls and creates no external-source/query contract from prose.
- Private/sanitized evidence are separate renderings of one deterministic internal result.
- Sanitized evidence MUST omit local source path, source text, mapped content text, projection bodies, exact unmatched heading text, and full source digest.
- Any alias salt used by sanitized evidence MUST be caller supplied; no random salts/timestamps/temp paths enter canonical evidence.
- Risk order is exactly `LOW < MEDIUM < HIGH < BLOCKED`.
- No public API may perform or expose delete, tombstone, source rewrite, archive move, canonical factorization commit, seed promotion, profile promotion, or regenerative forgetting.
- Public fixtures MUST be synthetic; no real Residence source/path/digest/content may enter GitHub.
- CLI implementation is out of scope for this plan; the spec's CLI remains future direction.
- Every task uses TDD: establish RED for the intended reason before production code, then GREEN, then focused regression.
- Before merge, run exact feature-head push CI and PR merge-ref CI; after merge, run exact `main` post-merge CI.

---

## Planned File Structure

Create:

```text
src/mneme/dry_run/
├── __init__.py          # public observation-only exports
├── models.py            # immutable request/metadata/readiness/result value objects
├── policy.py            # persistence-policy validation/digest/context resolution
├── compatibility.py     # PASS 1 inventories, profile candidates, previews
├── persistence.py       # PASS 2 assessments/readiness/evidential floor
├── intents.py           # explicit FactorizationIntent / SeedIntent bridges
├── report.py            # deterministic risk/status/report/private/sanitized rendering
├── bundle.py            # deterministic evidence files/checksums/fingerprint/writer
└── analyzer.py          # source-integrity + two-pass orchestration + replay verification

schemas/
├── persistence-policy-0.1.schema.json
├── factorization-intent-0.1.schema.json
├── seed-intent-0.1.schema.json
└── private-residence-dry-run-report-0.2.schema.json

tests/
├── test_dry_run_policy.py
├── test_dry_run_compatibility.py
├── test_dry_run_persistence.py
├── test_dry_run_intents.py
├── test_dry_run_report.py
├── test_dry_run_bundle.py
├── test_dry_run_analyzer.py
└── test_private_residence_dry_run_acceptance.py

fixtures/synthetic/
├── private-residence-two-pass-memory.md
├── private-residence-persistence-policy.json
└── private-residence-intent-template.json

scripts/
└── validate_private_residence_two_pass_dry_run.py

.github/workflows/
└── private-residence-two-pass-dry-run.yml
```

Modify only where needed:

```text
src/mneme/markdown_compat.py    # add public structural scanner wrapper; do not change importer semantics
src/mneme/errors.py             # add DryRunValidationError
src/mneme/__init__.py           # candidate version only in final release task
pyproject.toml                  # candidate version only in final release task
README.md                       # document two-pass observation boundary
```

---

### Task 1: Common Dry-Run Models and Deterministic Persistence Policy Resolver

**Files:**
- Create: `src/mneme/dry_run/__init__.py`
- Create: `src/mneme/dry_run/models.py`
- Create: `src/mneme/dry_run/policy.py`
- Create: `schemas/persistence-policy-0.1.schema.json`
- Modify: `src/mneme/errors.py`
- Test: `tests/test_dry_run_policy.py`

**Interfaces:**
- Consumes: `mneme.cps.rules.AssessmentContext`, `mneme.canonical.canonical_json_bytes`, `mneme.canonical.sha256_domain`.
- Produces:
  - `MappedRecordMetadata(record_id, section_id, record_type, scope_kind, scope_subject, block_kind, route_hints, start_line, end_line, profile_id, profile_digest)`
  - `PersistencePolicy.from_dict(raw) -> PersistencePolicy`
  - `PersistencePolicy.digest() -> str`
  - `ContextResolution(record_id, provenance, rule_ids, context)`
  - `resolve_contexts(metadata, policy=None, exact_overrides=None) -> tuple[ContextResolution, ...]`
  - `DryRunValidationError`

- [ ] **Step 1: Add RED tests for the policy selector allowlist and authority-free schema**

```python
def test_policy_rejects_content_selector():
    raw = {
        "policy_version": "mneme.persistence-policy/0.1",
        "policy_id": "synthetic/0.1",
        "rules": [{
            "rule_id": "bad",
            "selector": {"content.text": "delete me"},
            "context": empty_context_dict(),
        }],
    }
    with pytest.raises(DryRunValidationError):
        PersistencePolicy.from_dict(raw)


def test_policy_rejects_unknown_context_field():
    raw = valid_policy_dict()
    raw["rules"][0]["context"]["grant_authority"] = True
    with pytest.raises(DryRunValidationError):
        PersistencePolicy.from_dict(raw)
```

The schema must use `additionalProperties: false` for the policy, each rule, selector, and serialized context. The serialized context requires exactly the current CPS/0.1 `AssessmentContext` fields:

```text
explicit_decision
identity_or_authority_evidence
historical_observation
structural_dependency
structural_state
derivable_explanation
reconstruction_recipe_ref
obligation_set_ref
freshness_required
external_source_ref
previous_observation_ref
ephemeral_working_state
superseded_materialization
conflicting_evidence
```

- [ ] **Step 2: Run the tests and verify RED**

```bash
python -m pytest -q tests/test_dry_run_policy.py
```

Expected: collection/import failure because `mneme.dry_run.policy` does not exist.

- [ ] **Step 3: Implement immutable common metadata and policy validation**

```python
@dataclass(frozen=True)
class MappedRecordMetadata:
    record_id: str
    section_id: str
    record_type: str
    scope_kind: str
    scope_subject: str
    block_kind: str
    route_hints: tuple[str, ...]
    start_line: int
    end_line: int
    profile_id: str
    profile_digest: str
```

Add `DryRunValidationError(MnemeError, ValueError)`.

`PersistencePolicy.digest()` must be:

```python
sha256_domain(
    b"MNEME-DRYRUN-POLICY-0.1",
    canonical_json_bytes(self.to_dict()),
)
```

No policy is represented in reports by:

```python
{"policy_id": "NO_POLICY", "policy_digest": None, "rule_count": 0}
```

- [ ] **Step 4: Add RED tests for exact structured selector matching**

```python
def test_selector_matches_only_declared_metadata_fields():
    metadata = mapped_metadata(
        section_id="verification_lessons",
        record_type="lesson",
        scope_kind="global",
        scope_subject="verification",
        block_kind="unordered_list_item",
        route_hints=("route://method/verification",),
    )
    policy = PersistencePolicy.from_dict(policy_with_rule(
        selector={
            "section_id": "verification_lessons",
            "route_hint": "route://method/verification",
        },
        context=context_dict(
            derivable_explanation=True,
            reconstruction_recipe_ref="recipe://v1",
            obligation_set_ref="obligation://v1",
        ),
    ))
    resolution = resolve_contexts([metadata], policy=policy)[0]
    assert resolution.provenance == "POLICY_RULE"
    assert resolution.context.derivable_explanation is True
```

Route matching is exact membership in `metadata.route_hints`; every other selector is exact scalar equality. No substring/regex/case-folding behavior exists.

- [ ] **Step 5: Add RED tests for precedence, default context, and conflict**

```python
def test_exact_override_precedes_policy():
    metadata = mapped_metadata(record_id="r1", section_id="standing_instructions")
    policy = PersistencePolicy.from_dict(policy_with_rule(
        selector={"section_id": "standing_instructions"},
        context=context_dict(structural_state=True),
    ))
    override = {"r1": context_dict(explicit_decision=True)}
    resolution = resolve_contexts([metadata], policy=policy, exact_overrides=override)[0]
    assert resolution.provenance == "EXACT_RECORD_OVERRIDE"
    assert resolution.context.explicit_decision is True
    assert resolution.context.structural_state is False


def test_no_match_returns_empty_context():
    resolution = resolve_contexts([mapped_metadata(record_id="r1")])[0]
    assert resolution.provenance == "DEFAULT_UNKNOWN"
    assert resolution.context == AssessmentContext()


def test_nonidentical_matching_rules_become_conflict():
    policy = PersistencePolicy.from_dict(policy_with_two_conflicting_rules())
    resolution = resolve_contexts([mapped_metadata(record_id="r1")], policy=policy)[0]
    assert resolution.provenance == "POLICY_CONFLICT"
    assert resolution.context == AssessmentContext(conflicting_evidence=True)
```

Identical contexts from multiple rules are accepted once, with all matching `rule_ids` recorded in stable lexical rule-ID order.

- [ ] **Step 6: Add RED tests for cross-pass override rejection and deterministic replay**

```python
def test_override_for_unmapped_record_is_rejected():
    with pytest.raises(DryRunValidationError):
        resolve_contexts(
            [mapped_metadata(record_id="mapped")],
            exact_overrides={"not-mapped": context_dict(explicit_decision=True)},
        )


def test_policy_digest_and_resolution_are_deterministic():
    a = PersistencePolicy.from_dict(valid_policy_dict())
    b = PersistencePolicy.from_dict(valid_policy_dict())
    assert a.digest() == b.digest()
    assert resolve_contexts(METADATA, policy=a) == resolve_contexts(METADATA, policy=b)
```

- [ ] **Step 7: Implement minimal resolver and run focused GREEN**

Implement `context_from_dict()` using an explicit field map to `AssessmentContext`; do not use unvalidated `**raw` input.

```bash
python -m pytest -q tests/test_dry_run_policy.py
```

Expected: all Task 1 tests PASS.

- [ ] **Step 8: Run current historical regression**

```bash
python -m pytest -q
python scripts/validate_fresh_memory_core.py --output /tmp/fresh.json
python scripts/validate_memory_markdown_profile.py --output /tmp/md.json
python scripts/validate_cognitive_persistence_semantics.py --output /tmp/cps.json
```

Expected: all pre-existing tests and all three pre-existing acceptance gates PASS.

- [ ] **Step 9: Commit Task 1**

```bash
git add src/mneme/dry_run src/mneme/errors.py schemas/persistence-policy-0.1.schema.json tests/test_dry_run_policy.py
git commit -m "feat: add dry-run persistence policy resolver"
```

---

### Task 2: PASS 1 Compatibility Evidence, Heading/Route Inventories, and Bounded Previews

**Files:**
- Modify: `src/mneme/markdown_compat.py`
- Create: `src/mneme/dry_run/compatibility.py`
- Test: `tests/test_dry_run_compatibility.py`

**Interfaces:**
- Consumes `propose_profiled_markdown_import()`, `project_profiled_markdown()`, and `MemoryMarkdownProfile`.
- Produces:
  - `scan_markdown_blocks(text) -> tuple[MarkdownBlock, ...]` public wrapper over the existing scanner implementation.
  - `CompatibilityPassResult`
  - `run_compatibility_pass(source_path, profile, projection_budgets) -> CompatibilityPassResult`
  - exact `MappedRecordMetadata` entries for PASS 2.

- [ ] **Step 1: Add RED regression proving a public scanner wrapper returns exactly the existing structural scan**

```python
def test_public_scanner_matches_importer_block_structure():
    text = "# Standing Instructions\n- A\n\n# Unknown\n```\nnoop\n```\n"
    blocks = scan_markdown_blocks(text)
    assert [(b.kind, b.start_line, b.end_line) for b in blocks] == [
        ("heading", 1, 1),
        ("unordered_list_item", 2, 2),
        ("heading", 4, 4),
        ("code_fence", 5, 7),
    ]
```

Implementation:

```python
def scan_markdown_blocks(text: str) -> tuple[MarkdownBlock, ...]:
    return tuple(_scan_markdown(text))
```

Do not change `_scan_markdown()`, record-ID derivation, importer loss semantics, or projection rendering.

- [ ] **Step 2: Run scanner RED, implement wrapper, then GREEN**

```bash
python -m pytest -q tests/test_dry_run_compatibility.py::test_public_scanner_matches_importer_block_structure
```

- [ ] **Step 3: Add RED tests for PASS 1 mapped metadata binding**

```python
def test_pass1_metadata_is_bound_to_mapping_receipt(tmp_path, profile):
    path = write_memory(tmp_path, "# Standing Instructions\n- Keep exact evidence.\n")
    result = run_compatibility_pass(path, profile, projection_budgets=(20000,))
    assert len(result.records) == 1
    meta = result.metadata[0]
    mapping = result.mapping_receipt["mappings"][0]
    assert meta.record_id == mapping["record_id"]
    assert meta.section_id == mapping["section_id"]
    assert meta.block_kind == mapping["block_kind"]
    assert (meta.start_line, meta.end_line) == (mapping["start_line"], mapping["end_line"])
    assert meta.profile_digest == profile.digest()
```

Every importer record becomes a `MemoryRecord`; metadata comes only from mapping receipt/profile, never from `content.text`.

- [ ] **Step 4: Add RED tests for complete heading inventory including empty unknown heading**

```python
def test_heading_inventory_includes_empty_unknown_heading(tmp_path, profile):
    path = write_memory(
        tmp_path,
        "# Standing Instructions\n- A\n\n# Strange Future Section\n\n# Verification Lessons\n- B\n",
    )
    result = run_compatibility_pass(path, profile, projection_budgets=(20000,))
    item = next(x for x in result.heading_inventory if x.matched is False)
    assert item.line_numbers == (4,)
    assert item.occurrences == 1
    assert item.body_block_count == 0
```

Heading matching uses only `profile.match_heading()`.

- [ ] **Step 5: Add RED tests for explicit loss and deterministic profile-extension candidates**

```python
def test_repeated_unknown_heading_becomes_review_candidate_only(tmp_path, profile):
    path = write_memory(tmp_path, "# Mystery\n- one\n\n# Mystery\n- two\n")
    result = run_compatibility_pass(path, profile, projection_budgets=(20000,))
    assert result.loss_reason_counts["unknown_heading"] == 2
    candidate = result.profile_candidates[0]
    assert candidate.suggested_action == "REVIEW_FOR_PROFILE_EXTENSION"
    assert candidate.target_section is None
    assert candidate.occurrences == 2
```

Candidate generation never mutates the profile.

- [ ] **Step 6: Add RED route provenance test**

```python
def test_route_inventory_comes_only_from_mapping_receipt(tmp_path, profile):
    path = write_memory(tmp_path, "# Verification Lessons\n- Verify first.\n")
    result = run_compatibility_pass(path, profile, projection_budgets=(20000,))
    assert {
        route.route_id for route in result.route_inventory
    } == set(result.mapping_receipt["mappings"][0]["route_hints"])
```

- [ ] **Step 7: Add RED test for multiple bounded previews over unchanged proposal set**

```python
def test_projection_budgets_change_preview_not_records(tmp_path, profile):
    path = write_many_known_records(tmp_path, count=120)
    result = run_compatibility_pass(path, profile, projection_budgets=(2000, 20000))
    before_ids = tuple(r.to_dict()["record_id"] for r in result.records)
    assert result.previews[0].manifest["included_ids"] != result.previews[1].manifest["included_ids"]
    assert tuple(r.to_dict()["record_id"] for r in result.records) == before_ids
```

Projection source head:

```python
f"dryrun:{source_sha256[:16]}:{profile.digest()[:16]}"
```

- [ ] **Step 8: Implement PASS 1 and run focused GREEN**

```bash
python -m pytest -q tests/test_dry_run_compatibility.py
```

- [ ] **Step 9: Prove importer semantics remain unchanged**

```bash
python -m pytest -q tests/test_markdown_compat.py tests/test_markdown_profile_acceptance.py
python scripts/validate_memory_markdown_profile.py --output /tmp/md-after-pass1.json
```

Expected: MNEME-MD/0.1 still PASS with existing canonical profile digest unchanged.

- [ ] **Step 10: Commit Task 2**

```bash
git add src/mneme/markdown_compat.py src/mneme/dry_run/compatibility.py tests/test_dry_run_compatibility.py
git commit -m "feat: add dry-run compatibility evidence pass"
```

---

### Task 3: PASS 2 CPS Assessment, Evidential Floor, and Readiness

**Files:**
- Create: `src/mneme/dry_run/persistence.py`
- Test: `tests/test_dry_run_persistence.py`

**Interfaces:**
- Consumes PASS 1 records/metadata, `resolve_contexts()`, `CpsObservationAdapter.assess()`.
- Produces:
  - `FactorizationReadiness(record_id, state, assessment_id)`
  - `RecomputeReadiness(record_id, state)`
  - `PersistencePassResult`
  - `run_persistence_pass(records, metadata, policy=None, exact_overrides=None)`.

- [ ] **Step 1: Add RED test enforcing PASS 2 mapped-set equality**

```python
def test_pass2_requires_metadata_for_every_and_only_mapped_record():
    records = (memory_record("r1"), memory_record("r2"))
    metadata = (mapped_metadata(record_id="r1"),)
    with pytest.raises(DryRunValidationError):
        run_persistence_pass(records, metadata)
```

Production rejects duplicates and requires exact record-ID set equality.

- [ ] **Step 2: Add RED one-assessment-per-record test**

```python
def test_pass2_produces_exactly_one_assessment_per_record():
    result = run_persistence_pass(RECORDS, METADATA, policy=POLICY)
    assert len(result.assessments) == len(RECORDS)
    assert {a.to_dict()["subject_refs"][0] for a in result.assessments} == {
        r.to_dict()["record_id"] for r in RECORDS
    }
```

Classification is exactly one call to `CpsObservationAdapter().assess(...)`; no classifier is duplicated in `persistence.py`.

- [ ] **Step 3: Add RED conservative UNKNOWN/conflict tests**

```python
def test_default_resolution_becomes_unknown():
    result = run_persistence_pass((record("r1"),), (metadata("r1"),))
    assert result.assessments[0].to_dict()["candidate"] == "UNKNOWN"
    assert result.resolutions[0].provenance == "DEFAULT_UNKNOWN"


def test_policy_conflict_becomes_unknown_blocked():
    result = run_persistence_pass((record("r1"),), (metadata("r1"),), policy=CONFLICT_POLICY)
    raw = result.assessments[0].to_dict()
    assert raw["candidate"] == "UNKNOWN"
    assert raw["risk"] == "BLOCKED"
```

- [ ] **Step 4: Implement and test exact readiness mapping**

```python
_READINESS = {
    "PRESERVE": "PRESERVE_ONLY",
    "STRUCTURALIZE": "READY_FOR_STRUCTURAL_REVIEW",
    "GENERATIZE": "READY_FOR_GENERATIVE_REVIEW",
    "RECOMPUTE": "READY_FOR_RECOMPUTE_REVIEW",
    "DISCARD": "DISCARD_REQUIRES_REVIEW",
    "UNKNOWN": "UNRESOLVED",
}
```

- [ ] **Step 5: Add RED test proving readiness invents no cognitive components**

```python
def test_readiness_contains_no_generated_cognitive_components():
    item = readiness_for(assessment_with_candidate("GENERATIZE"))
    raw = item.to_dict()
    for forbidden in ("anchors", "structure", "generators", "obligations", "provenance_refs", "recompute_refs"):
        assert forbidden not in raw
```

- [ ] **Step 6: Add evidential-floor aggregation test**

```python
def test_required_preservations_are_visible():
    result = run_persistence_pass(
        (record("r1"),),
        (metadata("r1"),),
        exact_overrides={"r1": context_dict(explicit_decision=True)},
    )
    assert result.evidential_floor == {
        "r1": (result.assessments[0].to_dict()["assessment_id"],)
    }
```

- [ ] **Step 7: Add recompute-isolation test**

```python
def test_recompute_candidate_reports_readiness_without_network():
    result = run_persistence_pass(
        (record("r1"),),
        (metadata("r1"),),
        exact_overrides={"r1": context_dict(
            historical_observation=True,
            freshness_required=True,
            external_source_ref="synthetic://current",
            previous_observation_ref="r1",
        )},
    )
    assert result.recompute_readiness[0].state == "RECOMPUTE_CANDIDATE"
```

`persistence.py` imports no HTTP/network library and performs no query.

- [ ] **Step 8: Implement PASS 2 and run focused GREEN**

```bash
python -m pytest -q tests/test_dry_run_persistence.py
```

- [ ] **Step 9: Run CPS regression**

```bash
python -m pytest -q tests/test_cps_models.py tests/test_cps_rules.py tests/test_cps_factorization.py tests/test_cps_seed.py tests/test_cps_adapter.py
python scripts/validate_cognitive_persistence_semantics.py --output /tmp/cps-after-pass2.json
```

- [ ] **Step 10: Commit Task 3**

```bash
git add src/mneme/dry_run/persistence.py tests/test_dry_run_persistence.py
git commit -m "feat: add dry-run CPS persistence pass"
```

---

### Task 4: Explicit FactorizationIntent and SeedIntent Validation Bridges

**Files:**
- Create: `src/mneme/dry_run/intents.py`
- Create: `schemas/factorization-intent-0.1.schema.json`
- Create: `schemas/seed-intent-0.1.schema.json`
- Test: `tests/test_dry_run_intents.py`

**Interfaces:**
- Consumes PASS 1 IDs, PASS 2 assessments, `CpsObservationAdapter.factorize()`, `CpsObservationAdapter.propose_seed()`, `RecomputationReference`, `EquivalenceContract`.
- Produces `FactorizationIntent`, `SeedIntent`, their result types, and `evaluate_factorization_intents()` / `evaluate_seed_intents()`.

- [ ] **Step 1: Add RED schema tests for non-authoritative exact intent shape**

`FactorizationIntent` requires:

```text
intent_version = mneme.factorization-intent/0.1
intent_id
subject_record_ids
anchors
structure
generators
obligations
provenance_refs
recompute_refs
unresolved_refs
authority = false
```

`SeedIntent` requires:

```text
intent_version = mneme.seed-intent/0.1
seed_intent_id
factorization_intent_id
anchors
structure
generators
obligations
provenance_refs
recomputation_references
unresolved_components
equivalence_contract
authority = false
```

Reject unknown fields and `authority:true`.

- [ ] **Step 2: Run schema RED then implement immutable validators**

```bash
python -m pytest -q tests/test_dry_run_intents.py -k "shape or authority"
```

- [ ] **Step 3: Add RED cross-pass subject test**

```python
def test_factorization_intent_rejects_unmapped_subject():
    intent = FactorizationIntent.from_dict(
        factorization_intent_dict(subject_record_ids=["not-mapped"])
    )
    result = evaluate_factorization_intents(
        [intent],
        pass1_record_ids={"mapped"},
        assessments_by_record={"mapped": ASSESSMENT},
    )[0]
    assert result.status == "REJECTED"
    assert result.error_code == "CROSS_PASS_SUBJECT"
```

Rejected optional intents are findings, not hidden defaults.

- [ ] **Step 4: Add RED evidential-floor delegation test**

```python
def test_factorization_intent_cannot_omit_required_preservation():
    intent = FactorizationIntent.from_dict(
        factorization_intent_dict(
            subject_record_ids=["decision"],
            anchors=[], provenance_refs=[], unresolved_refs=[],
        )
    )
    result = evaluate_factorization_intents(
        [intent],
        pass1_record_ids={"decision"},
        assessments_by_record={"decision": preserve_assessment("decision")},
    )[0]
    assert result.status == "REJECTED"
    assert result.error_code == "CPS_REJECTED"
```

Do not duplicate CPS validation; normalize `CpsValidationError` from `CpsObservationAdapter.factorize()`.

- [ ] **Step 5: Add RED component-traceability test**

```python
def test_untraceable_factorization_component_is_rejected():
    intent = FactorizationIntent.from_dict(
        factorization_intent_dict(
            subject_record_ids=["r1"],
            anchors=["r1"], provenance_refs=["r1"],
            structure=[{"relation": "depends_on", "target_ref": "r2"}],
        )
    )
    assert evaluate_factorization_intents(...)[0].error_code == "CPS_REJECTED"
```

- [ ] **Step 6: Add accepted factorization binding test**

```python
def test_valid_intent_returns_cps_factorization_proposal():
    result = evaluate_factorization_intents(...VALID...)[0]
    assert result.status == "ACCEPTED"
    assert result.proposal.to_dict()["authority"] is False
    assert set(result.proposal.to_dict()["source_refs"]) == {"r1"}
```

- [ ] **Step 7: Add seed unknown-factorization test**

```python
def test_seed_intent_requires_accepted_factorization():
    result = evaluate_seed_intents(
        [seed_intent("seed1", factorization_intent_id="missing")],
        accepted_factorizations={},
    )[0]
    assert result.status == "REJECTED"
    assert result.error_code == "UNKNOWN_FACTORIZATION_INTENT"
```

- [ ] **Step 8: Add seed exact-binding regression**

```python
def test_seed_intent_cannot_replace_factorization_generators():
    intent = SeedIntent.from_dict(seed_intent_dict(
        factorization_intent_id="fp-intent",
        generators=[],
    ))
    result = evaluate_seed_intents(
        [intent],
        accepted_factorizations={"fp-intent": ACCEPTED_FACTORIZATION},
    )[0]
    assert result.status == "REJECTED"
    assert result.error_code == "CPS_REJECTED"
```

- [ ] **Step 9: Add recomputation/equivalence validation tests**

Deserialize only through:

```python
RecomputationReference.from_dict(item)
EquivalenceContract.from_dict(raw["equivalence_contract"])
```

Invalid freshness or `authority:true` becomes `CPS_REJECTED`; no network operation occurs.

- [ ] **Step 10: Implement bridges and run focused GREEN**

```bash
python -m pytest -q tests/test_dry_run_intents.py
```

- [ ] **Step 11: Run CPS regression again**

```bash
python scripts/validate_cognitive_persistence_semantics.py --output /tmp/cps-after-intents.json
```

- [ ] **Step 12: Commit Task 4**

```bash
git add src/mneme/dry_run/intents.py schemas/factorization-intent-0.1.schema.json schemas/seed-intent-0.1.schema.json tests/test_dry_run_intents.py
git commit -m "feat: validate explicit dry-run CPS intents"
```

---

### Task 5: Deterministic Risk, Status, Report Schema, and Privacy Rendering

**Files:**
- Create: `src/mneme/dry_run/report.py`
- Create: `schemas/private-residence-dry-run-report-0.2.schema.json`
- Test: `tests/test_dry_run_report.py`

**Interfaces:**
- Produces `compatibility_risk()`, `persistence_risk()`, `build_report()`, `render_private_report()`, `render_sanitized_report()`, `report_fingerprint()`.

- [ ] **Step 1: Add exact compatibility-risk threshold tests**

```python
@pytest.mark.parametrize(
    ("unresolved", "total", "expected"),
    [(0, 20, "LOW"), (1, 20, "MEDIUM"), (5, 20, "HIGH")],
)
def test_compatibility_risk_ratio(unresolved, total, expected):
    pass1 = compatibility_result(nonheading_blocks=total, unresolved_nonheading=unresolved)
    assert compatibility_risk(pass1) == expected
```

Additional HIGH tests: repeated unknown-heading candidate contributes at least half of unresolved non-heading blocks; mapped records exist and every requested preview failed. BLOCKED is supplied by coordinator for integrity/profile/determinism failures.

- [ ] **Step 2: Add exact persistence-risk tests**

```python
def test_persistence_low_requires_no_unknown_conflict_review_or_high_risk_candidate():
    assert persistence_risk(pass2_all_preserve()) == "LOW"


def test_persistence_high_for_generatize_discard_rejected_intent_or_conflict():
    assert persistence_risk(pass2_with_candidate("GENERATIZE")) == "HIGH"
    assert persistence_risk(pass2_with_candidate("DISCARD")) == "HIGH"
    assert persistence_risk(pass2_with_policy_conflict()) == "HIGH"
    assert persistence_risk(pass2_clean(), factorization_results=[rejected_intent()]) == "HIGH"


def test_persistence_high_when_unknown_ratio_reaches_quarter():
    assert persistence_risk(pass2_with_unknown_ratio(1, 4)) == "HIGH"
```

MEDIUM covers UNKNOWN below 25%, incomplete structural/recompute readiness, or explicit review still required without HIGH conditions.

- [ ] **Step 3: Define/test overall risk ordering**

```python
_RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "BLOCKED": 3}

def max_risk(a: str, b: str) -> str:
    return max((a, b), key=_RISK_ORDER.__getitem__)
```

- [ ] **Step 4: Add RED report-schema tests**

Require:
- exact report version;
- status in `PASS`, `PASS_WITH_FINDINGS`, `BLOCKED`;
- source/profile/policy/pass1/pass2/risk sections;
- `canonical_mutation == false`;
- `destructive_actions == false`;
- no unknown top-level fields.

Status:
- BLOCKED iff coordinator supplies blocking reasons;
- PASS iff both risks LOW and no loss/UNKNOWN/conflict/rejected intent/incomplete readiness/privacy/checksum finding;
- otherwise PASS_WITH_FINDINGS.

- [ ] **Step 5: Add RED sanitized privacy-leak test**

```python
def test_sanitized_report_excludes_private_material():
    private = build_private_report_with_secret(
        source_path="/private/Residence/MEMORY.md",
        source_sha="a" * 64,
        heading="Secret Person",
        content="private fact",
        projection="# MEMORY\nprivate fact",
    )
    sanitized = render_sanitized_report(private, salt="caller-supplied-test-salt")
    encoded = canonical_json_bytes(sanitized)
    for secret in (
        b"/private/Residence/MEMORY.md", b"Secret Person", b"private fact",
        ("a" * 64).encode(), b"# MEMORY",
    ):
        assert secret not in encoded
```

- [ ] **Step 6: Implement deterministic aliasing and test salt sensitivity**

```python
def sanitized_alias(kind: str, value: str, salt: str) -> str:
    digest = sha256_domain(
        b"MNEME-DRYRUN-SANITIZED-ALIAS-0.2",
        canonical_json_bytes({"kind": kind, "value": value, "salt": salt}),
    )
    return f"{kind}-{digest[:24]}"
```

Identical input/salt must match; different salt must differ; no random module.

- [ ] **Step 7: Add report fingerprint tests**

```python
sha256_domain(
    b"MNEME-DRYRUN-REPORT-0.2",
    canonical_json_bytes(report_dict),
)
```

No timestamp/temp path/random value enters report.

- [ ] **Step 8: Implement report/risk/privacy and run focused GREEN**

```bash
python -m pytest -q tests/test_dry_run_report.py
```

- [ ] **Step 9: Commit Task 5**

```bash
git add src/mneme/dry_run/report.py schemas/private-residence-dry-run-report-0.2.schema.json tests/test_dry_run_report.py
git commit -m "feat: add deterministic dry-run reporting"
```

---

### Task 6: Evidence Bundle and Two-Pass Coordinator

**Files:**
- Create: `src/mneme/dry_run/bundle.py`
- Create: `src/mneme/dry_run/analyzer.py`
- Test: `tests/test_dry_run_bundle.py`
- Test: `tests/test_dry_run_analyzer.py`
- Modify: `src/mneme/dry_run/__init__.py`

**Interfaces:**
- Produces `DryRunRequest`, `DryRunResult`, `PrivateResidenceDryRunAnalyzer.analyze()`, `PrivateResidenceDryRunAnalyzer.verify_deterministic()`, `build_evidence_files()`, `bundle_manifest()`, `bundle_fingerprint()`, `write_evidence_bundle()`.

- [ ] **Step 1: Define `DryRunRequest` and add RED validation tests**

```python
@dataclass(frozen=True)
class DryRunRequest:
    source_path: Path
    markdown_profile: MemoryMarkdownProfile
    privacy_mode: str
    projection_budgets: tuple[int, ...]
    expected_source_sha256: str | None = None
    persistence_policy: PersistencePolicy | None = None
    exact_record_context_overrides: Mapping[str, dict[str, object]] | None = None
    factorization_intents: tuple[FactorizationIntent, ...] = ()
    seed_intents: tuple[SeedIntent, ...] = ()
    sanitization_salt: str | None = None
    canonical_head_snapshot: str | None = None
```

Validation: privacy exactly private/sanitized; positive budgets; sanitized requires caller salt; source is a file; no store/callback/write field.

- [ ] **Step 2: Add RED expected-source-digest fail-before-PASS-1 test**

```python
def test_expected_digest_mismatch_blocks_before_pass1(monkeypatch, request):
    called = False
    def forbidden(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("PASS 1 must not run")
    monkeypatch.setattr(analyzer_module, "run_compatibility_pass", forbidden)
    bad = replace(request, expected_source_sha256="0" * 64)
    result = PrivateResidenceDryRunAnalyzer().analyze(bad)
    assert result.report.status == "BLOCKED"
    assert "SOURCE_DIGEST_MISMATCH" in result.report.blocking_reasons
    assert called is False
```

Coordinator reads source bytes and validates UTF-8 before PASS 1.

- [ ] **Step 3: Add RED source-mutation detection test**

Inject PASS 1 wrapper that modifies source after evidence; expect `BLOCKED` + `SOURCE_MUTATED` after final digest read.

- [ ] **Step 4: Add RED PASS-1 source binding cross-check**

If importer-reported source digest differs from initial source digest, block with `PASS1_SOURCE_BINDING_MISMATCH`.

- [ ] **Step 5: Add RED end-to-end two-pass isolation test**

```python
def test_analyzer_pass2_subjects_equal_pass1_mapped_ids(request):
    result = PrivateResidenceDryRunAnalyzer().analyze(request)
    mapped = {m.record_id for m in result.pass1.metadata}
    assessed = {a.to_dict()["subject_refs"][0] for a in result.pass2.assessments}
    assert assessed == mapped
```

- [ ] **Step 6: Add RED no-destructive-API test**

```python
def test_analyzer_public_api_has_no_mutation_surface():
    forbidden = {
        "commit", "delete", "tombstone", "rewrite", "archive_move",
        "write_memory", "apply_migration", "update_store", "replace_record",
        "commit_factorization", "promote_seed", "promote_profile", "forget",
    }
    public = {name for name in dir(PrivateResidenceDryRunAnalyzer) if not name.startswith("_")}
    assert forbidden.isdisjoint(public)
```

Also inspect `analyze` signature for no store/writer/callback/mutation argument.

- [ ] **Step 7: Implement deterministic evidence files**

Private file map includes:

```text
report.json
summary.md
pass1/mapping-receipt.json
pass1/loss-inventory.json
pass1/heading-inventory.json
pass1/route-inventory.json
pass1/profile-candidates.json
pass2/persistence-assessments.jsonl
pass2/context-resolution.jsonl
pass2/evidential-floor.json
pass2/factorization-readiness.jsonl
pass2/factorization-intent-results.jsonl
pass2/seed-readiness.jsonl
pass2/seed-intent-results.jsonl
projections/<budget>.md
projections/<budget>.manifest.json
```

Sanitized evidence omits projection bodies/private path/text fields. JSON/JSONL use canonical UTF-8 plus trailing newline.

- [ ] **Step 8: Add RED bundle-manifest/checksum tamper test**

Manifest:

```json
{
  "manifest_version": "mneme.private-residence-dry-run-bundle/0.2",
  "files": [{"path": "...", "sha256": "...", "byte_count": 123}]
}
```

Paths sorted lexically. Fingerprint:

```python
sha256_domain(
    b"MNEME-DRYRUN-BUNDLE-0.2",
    canonical_json_bytes(manifest),
)
```

Mutating any evidence byte must fail verification/change fingerprint.

- [ ] **Step 9: Add writer safety test**

`write_evidence_bundle()` never copies source, refuses destination equal to source, and fails closed on an existing file with different bytes rather than silently overwrite.

- [ ] **Step 10: Add deterministic double-run test**

```python
def test_verify_deterministic_repeats_same_bundle_fingerprint(request):
    result = PrivateResidenceDryRunAnalyzer().verify_deterministic(request)
    assert result.deterministic_verified is True
```

Injected nondeterminism on second run -> `BLOCKED` + `DETERMINISTIC_REPLAY_MISMATCH`.

- [ ] **Step 11: Implement coordinator/bundle and run focused GREEN**

```bash
python -m pytest -q tests/test_dry_run_bundle.py tests/test_dry_run_analyzer.py
```

- [ ] **Step 12: Run full historical + new regression**

```bash
python -m pytest -q
python scripts/validate_fresh_memory_core.py --output /tmp/fresh-task6.json
python scripts/validate_memory_markdown_profile.py --output /tmp/md-task6.json
python scripts/validate_cognitive_persistence_semantics.py --output /tmp/cps-task6.json
python -m compileall -q src
```

- [ ] **Step 13: Commit Task 6**

```bash
git add src/mneme/dry_run tests/test_dry_run_bundle.py tests/test_dry_run_analyzer.py
git commit -m "feat: add private Residence two-pass dry-run analyzer"
```

---

### Task 7: Synthetic D0-D20 Acceptance Gate and Red Controls

**Files:**
- Create: `fixtures/synthetic/private-residence-two-pass-memory.md`
- Create: `fixtures/synthetic/private-residence-persistence-policy.json`
- Create: `fixtures/synthetic/private-residence-intent-template.json`
- Create: `scripts/validate_private_residence_two_pass_dry_run.py`
- Create: `tests/test_private_residence_dry_run_acceptance.py`

**Interfaces:**
- Produces deterministic receipt with `profile = "MNEME-PRIVATE-RESIDENCE-DRY-RUN/0.2"`, D0-D20 cases, control details, report/bundle fingerprints, source commit, status.

- [ ] **Step 1: Create synthetic Markdown fixture**

Include known headings `Standing Instructions`, `Verification Lessons`, `Who / how we work`, `Named Identities`, `This machine`; repeated unknown heading with body; empty unknown heading; fenced code; Traditional-Chinese UTF-8; multiple route hints; enough known records for two preview budgets. Use no real names/paths/Residence facts.

- [ ] **Step 2: Create metadata-only synthetic persistence policy covering six CPS outcomes**

```text
Standing Instructions + unordered_list_item -> explicit_decision -> PRESERVE
Who / how we work -> structural_state -> STRUCTURALIZE
Verification Lessons -> derivable_explanation + recipe/obligation refs -> GENERATIZE
This machine + paragraph -> freshness_required + synthetic external source -> RECOMPUTE
This machine + unordered_list_item -> ephemeral_working_state -> DISCARD
Named Identities -> empty AssessmentContext -> UNKNOWN
```

No source-text selector.

- [ ] **Step 3: Implement D0-D20 positive cases exactly**

```text
D0  source immutability
D1  no writable store / no mutation API
D2  pass2 subject set == pass1 mapped set
D3  profile ID/digest + line-range binding
D4  explicit compatibility loss
D5  all headings including empty unknown heading
D6  route provenance
D7  selector allowlist / no prose inference
D8  default UNKNOWN + conflict UNKNOWN + exact override precedence
D9  one assessment per mapped record
D10 evidential floor visible
D11 readiness only; no invented components
D12 explicit factorization intent through CPS
D13 seed intent through accepted factorization + CPS binding
D14 no network/recompute execution
D15 budgets change previews, not records/assessments
D16 sanitized privacy separation
D17 identity/authority non-escalation
D18 deterministic rerun
D19 no de-materialization surface
D20 negative evidence coverage
```

- [ ] **Step 4: Add required negative controls**

At minimum:

```text
D0-source-mutation-detected
D1-store-or-mutation-surface-absent
D2-cross-pass-subject-rejected
D3-profile-binding-mutation-detected
D4-unknown-loss-not-silenced
D5-empty-unknown-heading-accounted
D6-prose-route-not-created
D7-forbidden-content-selector-rejected
D8-policy-conflict-yields-unknown
D8-unmapped-exact-override-rejected
D9-assessment-count-mismatch-rejected
D10-required-preservation-omission-rejected
D11-readiness-has-no-generated-components
D12-untraceable-factorization-component-rejected
D13-factorization-generator-replacement-rejected
D14-recompute-performs-no-network-call
D15-preview-budget-does-not-change-assessments
D16-private-text-absent-from-sanitized-evidence
D17-authority-true-intent-rejected
D18-deterministic-input-mutation-changes-fingerprint
D19-forbidden-dematerialization-methods-absent
```

D20 asserts every `D0` through `D19` family is represented.

- [ ] **Step 5: Prove the gate can turn red**

Temporarily mutate one synthetic intent/policy `authority:false` to `true`; acceptance must exit non-zero with `status: FAIL`. Restore and rerun to PASS. Do not commit the mutated fixture.

- [ ] **Step 6: Run acceptance focused**

```bash
python scripts/validate_private_residence_two_pass_dry_run.py --output /tmp/dry-run.json
```

Expected: D0-D20 PASS and required controls present.

- [ ] **Step 7: Add pytest wrapper**

```python
def test_private_residence_dry_run_acceptance(tmp_path):
    proc = subprocess.run(
        [sys.executable, "scripts/validate_private_residence_two_pass_dry_run.py",
         "--output", str(tmp_path / "receipt.json")],
        cwd=ROOT,
        check=False,
    )
    assert proc.returncode == 0
```

- [ ] **Step 8: Run complete local gate**

```bash
python -m pytest -q
python scripts/validate_fresh_memory_core.py --output /tmp/fresh-final-local.json
python scripts/validate_memory_markdown_profile.py --output /tmp/md-final-local.json
python scripts/validate_cognitive_persistence_semantics.py --output /tmp/cps-final-local.json
python scripts/validate_private_residence_two_pass_dry_run.py --output /tmp/dry-final-local.json
python -m compileall -q src
```

- [ ] **Step 9: Commit Task 7**

```bash
git add fixtures/synthetic/private-residence-two-pass-memory.md fixtures/synthetic/private-residence-persistence-policy.json fixtures/synthetic/private-residence-intent-template.json scripts/validate_private_residence_two_pass_dry_run.py tests/test_private_residence_dry_run_acceptance.py
git commit -m "test: add two-pass dry-run acceptance gate"
```

---

### Task 8: README, Candidate Version, Exact-Remote CI, Review, and Merge Closure

**Files:**
- Create: `.github/workflows/private-residence-two-pass-dry-run.yml`
- Modify: `README.md`
- Modify: `pyproject.toml`
- Modify: `src/mneme/__init__.py`
- Review: all changed files against spec and this plan.

**Interfaces:**
- Candidate package: `mneme-memory==0.4.0a1`.
- CI runs all historical and new gates.

- [ ] **Step 1: Add workflow**

Trigger on push/PR changes under `src/**`, `schemas/**`, `fixtures/**`, `tests/**`, `scripts/**`, `pyproject.toml`, `README.md`, and this workflow. Use Ubuntu 24.04 / Python 3.11.

Steps:

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python scripts/validate_fresh_memory_core.py --output fresh-memory-core.json
python scripts/validate_memory_markdown_profile.py --output memory-markdown-profile.json
python scripts/validate_cognitive_persistence_semantics.py --output cps.json
python scripts/validate_private_residence_two_pass_dry_run.py --output private-residence-dry-run.json
python -m compileall -q src
```

- [ ] **Step 2: Update README with explicit stack/boundary**

```text
MLF-RM/0.1      canonical memory
MNEME-MD/0.1    Markdown compatibility
MNEME-CPS/0.1   cognitive persistence semantics
Dry-Run/0.2     two-pass private migration/factorization evidence
```

Document that PASS 2 receives mapped records rather than raw Markdown semantics, policy selectors are exact structured metadata only, readiness does not synthesize factorization, and no deletion/migration/reconstruction exists.

- [ ] **Step 3: Bump package candidate only now**

Change `pyproject.toml` and `src/mneme/__init__.py` from `0.3.0a1` to `0.4.0a1`.

- [ ] **Step 4: Run fresh local verification after metadata/version changes**

```bash
python -m pytest -q
python scripts/validate_fresh_memory_core.py --output /tmp/fresh-release.json
python scripts/validate_memory_markdown_profile.py --output /tmp/md-release.json
python scripts/validate_cognitive_persistence_semantics.py --output /tmp/cps-release.json
python scripts/validate_private_residence_two_pass_dry_run.py --output /tmp/dry-release.json
python -m compileall -q src
```

Record actual test/control counts from output; do not predict them in docs beforehand.

- [ ] **Step 5: Perform scope audit against protected historical semantics**

Verify no semantic changes to memory-record schema, transaction schemas, `src/mneme/store.py`, MNEME-MD profile JSON, or existing CPS schema/runtime unless a narrowly tested review repair requires one. Unexpected change stops closure.

- [ ] **Step 6: Commit release/CI metadata**

```bash
git add .github/workflows/private-residence-two-pass-dry-run.yml README.md pyproject.toml src/mneme/__init__.py
git commit -m "ci: validate private Residence two-pass dry run"
```

- [ ] **Step 7: Push exact feature head and require exact-head CI**

Record feature-head SHA; verify Actions checked out that exact SHA and full pytest + Fresh + MNEME-MD + CPS + Dry-Run + compileall all succeed. Acceptance receipts that expose `source_commit` must bind the exact feature head. Do not use prior local runs as merge evidence.

- [ ] **Step 8: Open PR and perform diff review before merge**

Review at minimum:
- `policy.py`: no text/prose selectors, no rule-order conflict resolution;
- `compatibility.py`: no second semantic parser;
- `persistence.py`: no second CPS classifier, one assessment/record;
- `intents.py`: actual proposals delegate to CPS;
- `analyzer.py`: no writable store/callback/mutation surface;
- `report.py` / `bundle.py`: sanitized output leaks no private path/text/digest/projection body;
- public API: no delete/tombstone/rewrite/archive/promote/forget methods.

Any Critical/Important finding stops merge; add RED regression, repair, rerun full local and exact-remote gates.

- [ ] **Step 9: Require PR merge-ref CI**

Verify GitHub's merge ref against current `main` passes the same complete workflow; record merge-ref SHA separately.

- [ ] **Step 10: Squash merge with expected head**

Suggested title:

```text
feat: add Private Residence two-pass dry-run analyzer
```

- [ ] **Step 11: Require exact post-merge `main` verification**

Confirm exact new main checkout, full pytest PASS, Fresh A0-A6 PASS, MNEME-MD M0-M8 PASS, CPS C0-C13 PASS, Dry-Run D0-D20 PASS, compileall success. Only then mark subsystem closed.

- [ ] **Step 12: Build a public-safe closure bundle**

Include source snapshot, synthetic fixtures only, spec + plan, final local receipts, `STATUS.md`, `MANIFEST.sha256.json`. Exclude real Residence source/path/labels/digest/private report/projection content.

---

## Plan Self-Review Checklist

1. **Spec coverage:** D0-D20 map to Tasks 1-8:
   - D0/D1/D18/D19: Task 6 + Task 7
   - D2-D6/D15: Task 2 + Task 6 + Task 7
   - D7-D9: Task 1 + Task 3 + Task 7
   - D10-D14/D17: Task 3 + Task 4 + Task 7
   - D16: Task 5 + Task 6 + Task 7
   - D20: Task 7
2. **No prose inference:** only Task 1 selectors exist and use exact structured metadata.
3. **No automatic factorization synthesis:** Task 3 emits readiness only; Task 4 requires explicit intents.
4. **CPS remains authoritative validator for proposals:** Task 4 delegates to existing `CpsObservationAdapter`.
5. **No canonical write path:** none of the new interfaces accept `MemoryStore`.
6. **Privacy:** sanitized output is tested byte-wise against known secrets.
7. **Determinism:** policy/report/bundle use domain-separated canonical JSON hashes; no random/timestamp/temp path enters canonical evidence.
8. **Type consistency:** `MappedRecordMetadata`, `ContextResolution`, intent/result names, and report version are consistent across tasks.
9. **No placeholders:** no TBD/TODO or unspecified implementation gaps remain.
10. **YAGNI:** no CLI, LLM classifier, reconstruction engine, MLF-RM/0.2, deletion, or forgetting enters this milestone.
