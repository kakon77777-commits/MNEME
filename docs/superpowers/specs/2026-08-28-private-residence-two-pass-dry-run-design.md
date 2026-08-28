# MNEME Private Residence Two-Pass Dry-Run Analyzer — Design Specification

**Status:** Canonical design candidate  
**Date:** 2026-08-28  
**Repository:** `kakon77777-commits/MNEME`  
**Base:** `main@84b9b0ee94115902d7a9e6acfdc48372e60fd673`  
**Base package:** `mneme-memory==0.3.0a1`  
**Canonical memory profile:** `MLF-RM/0.1`  
**Markdown compatibility profile:** `MNEME-MD/0.1`  
**Cognitive persistence semantics:** `MNEME-CPS/0.1`  
**Dry-run report version:** `mneme.private-residence-dry-run/0.2`

---

## 1. Purpose

The Private Residence Two-Pass Dry-Run Analyzer is a read-only evidence subsystem for studying existing private Residence `MEMORY.md` files before any real migration, canonical factorization, or cognitive reconstruction is allowed.

The original 2026-08-27 dry-run design asked only:

> What existing Markdown maps safely into MNEME, what remains unresolved, and what bounded projections would be produced?

After MNEME-CPS/0.1, that question is incomplete. The analyzer must now ask two separate questions in two explicit passes:

```text
PASS 1 — Compatibility
What does this Markdown explicitly map to?

PASS 2 — Persistence
Given only the mapped memory candidates, how might each candidate need to persist?
```

The second pass is observational. It does not prove that cognition is reconstructible and does not authorize deletion, archive retirement, tombstoning, or canonical factorization.

```text
DRY RUN != MIGRATION
ANALYSIS != COMMIT
ASSESSMENT != AUTHORITY
FACTORIZE != DELETE
SEED != AUTHORITY
```

This design supersedes the unmerged 2026-08-27 single-pass dry-run candidate. It preserves its source-integrity, privacy, projection, route, loss-accounting, and no-write boundaries while adding CPS-aware persistence analysis.

---

## 2. Selected architecture

Three approaches were considered.

### A. Single pass with a CPS summary appended

Run the old compatibility analysis and add aggregate CPS counts afterward.

Rejected because it obscures whether persistence analysis is operating on explicitly mapped memory records or directly on source Markdown.

### B. Unified Markdown + persistence semantic parser

Merge MNEME-MD and CPS logic into one parser that reads source prose and emits persistence classifications.

Rejected because this would collapse two already-verified abstraction boundaries and reintroduce semantic guessing into the compatibility layer.

### C. Explicit two-pass evidence pipeline

```text
source Markdown
  -> MNEME-MD compatibility pass
  -> mapped MemoryRecord proposals
  -> explicit/deterministic CPS context resolution
  -> CPS persistence assessments
  -> factorization/seed readiness evidence
  -> optional caller-supplied explicit proposal intents
```

**Selected approach.**

The boundary is architectural, not cosmetic:

```text
PASS 2 MAY CONSUME PASS 1 MAPPED RECORDS
PASS 2 MUST NOT REPARSE RAW MARKDOWN FOR SEMANTIC MEANING
```

---

## 3. Position in the MNEME stack

```text
Private Residence MEMORY.md
        |
        v
+------------------------------------+
| PASS 1 — MNEME-MD Compatibility   |
+------------------------------------+
        |
        +--> source/profile binding
        +--> mapped MemoryRecord proposals
        +--> mapping receipt
        +--> explicit loss inventory
        +--> heading inventory
        +--> route inventory
        +--> bounded preview projections
        +--> profile-extension review candidates
        |
        v
mapped proposal boundary
        |
        v
+------------------------------------+
| PASS 2 — MNEME-CPS Persistence    |
+------------------------------------+
        |
        +--> explicit context provenance
        +--> PersistenceAssessment sidecars
        +--> candidate/disposition counts
        +--> evidential-floor inventory
        +--> factorization readiness
        +--> recomputation readiness
        +--> seed readiness
        +--> optional validated CPS proposals
        +--> unresolved persistence inventory
        |
        v
DryRunEvidenceBundle

NO MemoryStore.commit()
NO source rewrite
NO profile mutation
NO automatic factorization synthesis
NO reconstruction
NO deletion / tombstoning / archive movement
```

---

## 4. Hard invariants

The analyzer must enforce:

```text
SOURCE BYTES BEFORE == SOURCE BYTES AFTER
DRY RUN DOES NOT ACCEPT A WRITABLE MEMORY STORE
CANONICAL MEMORY IS NOT MUTATED
PASS 2 INPUT SUBSET == PASS 1 MAPPED RECORDS
RAW MARKDOWN TEXT != CPS CLASSIFICATION INPUT
ASSESSMENT CONTEXT != INFERRED FROM PROSE
PROFILE CANDIDATE != PROFILE UPDATE
PERSISTENCE CANDIDATE != RETENTION POLICY
FACTORIZE READINESS != FACTORIZATION GENERATION
FACTORIZE != DELETE
RECONSTRUCTIBLE != DISPENSABLE
DISCARD CANDIDATE != DELETE AUTHORITY
COGNITIVE SEED != CANONICAL EVIDENCE
DISPLAY LABEL != RESIDENT ID
PREVIEW PROJECTION != CANONICAL MEMORY
```

Any implementation convenience that violates one of these invariants is out of scope.

---

## 5. Inputs

A dry-run request contains:

```text
source_path
markdown_profile
privacy_mode
projection_budgets
optional expected_source_sha256
optional persistence_policy
optional exact_record_context_overrides
optional factorization_intents
optional seed_intents
optional sanitization_salt
optional canonical_head_snapshot (string only)
```

The analyzer does not accept `MemoryStore` as an input.

### 5.1 Source path

The caller supplies a local Markdown file path. The path is private operational metadata.

The source file is never copied into the evidence bundle by default.

### 5.2 Markdown profile

The caller supplies an already validated `MemoryMarkdownProfile`.

The analyzer never mutates the selected profile.

### 5.3 Projection budgets

One or more positive byte budgets may be supplied. Each bounded preview must bind the same PASS 1 proposal set.

### 5.4 Expected source digest

If supplied, it must match before parsing. A mismatch blocks the run.

### 5.5 Canonical head snapshot

A caller may provide a plain string representing the canonical head observed before the dry run. It is comparison metadata only.

The analyzer never receives a store object and therefore cannot commit or update that head.

---

## 6. PASS 1 — Compatibility analysis

PASS 1 reuses MNEME-MD/0.1 exactly:

```python
propose_profiled_markdown_import(source_path, markdown_profile)
```

It must not add a second Markdown semantic parser.

Outputs include:

- mapped `MemoryRecord` proposals;
- exact mapping receipt;
- loss entries and reason counts;
- unknown-heading observations;
- route hints copied from matched profile sections;
- bounded profile-aware projection previews;
- profile-extension review candidates.

No CPS classification occurs during PASS 1.

---

## 7. PASS 1 mapped-proposal boundary

Every PASS 2 record must be traceable to a PASS 1 mapping receipt entry.

For each mapped record the analyzer retains an internal metadata tuple:

```text
record_id
section_id
record_type
scope
route_hints
source_line_range
profile_id
profile_digest
```

This tuple is the only compatibility metadata available to deterministic persistence policy matching.

PASS 2 must not inspect source block text to decide persistence semantics.

---

## 8. PASS 2 — Persistence analysis

PASS 2 consumes mapped `MemoryRecord` objects plus explicitly resolved `AssessmentContext` values and delegates classification to MNEME-CPS/0.1:

```text
MemoryRecord + AssessmentContext
    -> CpsObservationAdapter.assess(...)
    -> PersistenceAssessment
```

The Dry-Run analyzer does not implement a second persistence classifier.

All six CPS/0.1 candidate dispositions remain valid:

```text
PRESERVE
STRUCTURALIZE
GENERATIZE
RECOMPUTE
DISCARD
UNKNOWN
```

`UNKNOWN` is a successful conservative result.

---

## 9. AssessmentContext resolution

The analyzer needs a scalable way to provide explicit CPS context without using source prose as a classifier.

Resolution has four possible sources, in precedence order:

```text
1. exact record override
2. deterministic metadata policy rule
3. policy conflict -> conflicting_evidence context
4. no match -> empty AssessmentContext -> UNKNOWN
```

Every produced assessment records context provenance:

```text
EXACT_RECORD_OVERRIDE
POLICY_RULE
POLICY_CONFLICT
DEFAULT_UNKNOWN
```

### 9.1 Exact record overrides

The caller may bind a serialized `AssessmentContext` to an exact PASS 1 `record_id`.

An override for an unknown or unmapped record ID is rejected.

### 9.2 Deterministic persistence policy

A reusable policy may match only exact structured metadata supplied by PASS 1.

Allowed selector fields in v0.1:

```text
section_id
record_type
route_hint
scope_kind
scope_subject
block_kind
```

All declared selector fields must match exactly.

A policy rule outputs a normalized complete `AssessmentContext` representation, including explicit false/null values for fields not asserted by the rule, so policy equality is byte-comparable.

### 9.3 Forbidden selectors

The v0.1 policy system must not inspect or match:

```text
content.text
raw paragraph text
raw list-item text
raw heading text
substrings
regular expressions over source content
edit distance
semantic similarity
embeddings
LLM output
```

This prevents the Dry-Run layer from becoming an implicit semantic migration model.

### 9.4 Policy conflicts

If multiple matching rules produce byte-identical normalized contexts, the result is accepted once and all matching rule IDs are recorded.

If multiple matching rules produce different contexts, the analyzer must not choose one by order. It produces a conflict context equivalent to:

```text
conflicting_evidence = true
```

CPS then yields `UNKNOWN / BLOCKED` for that record.

### 9.5 Policy digest

The report binds:

```text
policy_id
policy_version
policy_digest
rule_count
```

If no policy is supplied, a canonical `NO_POLICY` marker is used.

---

## 10. PersistenceAssessment inventory

For every PASS 1 mapped record, PASS 2 produces exactly one `PersistenceAssessment`.

The report aggregates:

- candidate counts;
- risk-class counts;
- review-state counts;
- required-preservation count;
- context-provenance counts;
- policy-conflict count;
- `UNKNOWN` count;
- evidence-sensitive record count.

The private evidence bundle may contain full CPS assessment objects.

The sanitized bundle must not expose source content and may replace record IDs with deterministic salted aliases.

---

## 11. Evidential floor in the dry run

The analyzer treats CPS `required_preservations` as an explicit floor.

It reports:

```text
required preservation refs
which records require preservation
which proposed factorization intents cover them
which remain unresolved
```

The analyzer does not decide that a preserved reference can be deleted merely because it is also present in a seed proposal.

```text
PRESERVED IN SEED != SAFE TO DELETE SOURCE
```

---

## 12. Factorization readiness

Dry-Run analysis must distinguish **readiness** from **actual factorization proposal construction**.

For each assessment, the analyzer emits a readiness state.

Recommended states:

```text
PRESERVE_ONLY
READY_FOR_STRUCTURAL_REVIEW
READY_FOR_GENERATIVE_REVIEW
READY_FOR_RECOMPUTE_REVIEW
DISCARD_REQUIRES_REVIEW
UNRESOLVED
```

These states are report semantics only. They do not modify the CPS candidate.

Suggested mapping:

```text
PRESERVE      -> PRESERVE_ONLY
STRUCTURALIZE -> READY_FOR_STRUCTURAL_REVIEW
GENERATIZE    -> READY_FOR_GENERATIVE_REVIEW
RECOMPUTE     -> READY_FOR_RECOMPUTE_REVIEW
DISCARD       -> DISCARD_REQUIRES_REVIEW
UNKNOWN       -> UNRESOLVED
```

No structure, generator, obligation, anchor, or provenance component is invented from source prose.

---

## 13. FactorizationIntent

The caller may optionally provide an explicit factorization intent when it wants the dry run to validate a concrete CPS factorization proposal.

An intent binds:

```text
intent_id
subject_record_ids
anchors
structure
generators
obligations
provenance_refs
recompute_refs
unresolved_refs
```

Every subject record must belong to PASS 1.

Every component must satisfy existing CPS component traceability rules.

The analyzer delegates construction to:

```python
CpsObservationAdapter.factorize(...)
```

If the CPS builder rejects the intent, the dry run records a rejected intent finding. It does not weaken CPS validation.

```text
FACTORIZE INTENT != FACTORIZATION AUTHORITY
```

---

## 14. Seed readiness and SeedIntent

A `CognitiveSeedProposal` is even more constrained.

The analyzer always reports seed readiness, but it builds an actual seed proposal only when the caller supplies an explicit `SeedIntent` referencing an accepted `FactorizationIntent` result.

A seed intent binds:

```text
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
```

The analyzer delegates to:

```python
CpsObservationAdapter.propose_seed(...)
```

The Dry-Run layer cannot synthesize a missing equivalence contract.

The Dry-Run layer cannot modify factorization structure/generators/obligations to make a seed pass.

---

## 15. Recompute readiness

A `RECOMPUTE` assessment indicates persistence semantics, not a completed external query contract.

The report distinguishes:

```text
RECOMPUTE_CANDIDATE
RECOMPUTATION_REFERENCE_SUPPLIED
RECOMPUTATION_REFERENCE_MISSING
```

No network call is performed.

No recomputation reference is synthesized from URLs or prose.

---

## 16. DryRunReport model

The top-level deterministic report contains at least:

```json
{
  "report_version": "mneme.private-residence-dry-run/0.2",
  "status": "PASS_WITH_FINDINGS",
  "source": {
    "sha256": "...",
    "byte_count": 0,
    "line_count": 0,
    "mutated": false
  },
  "markdown_profile": {
    "profile_id": "evemiss-residence/0.1",
    "profile_digest": "..."
  },
  "persistence_policy": {
    "policy_id": "NO_POLICY",
    "policy_digest": null,
    "rule_count": 0
  },
  "pass1": {
    "mapped_record_count": 0,
    "record_type_counts": {},
    "loss_count": 0,
    "unknown_heading_count": 0,
    "route_hint_counts": {}
  },
  "pass2": {
    "assessment_count": 0,
    "candidate_counts": {},
    "context_provenance_counts": {},
    "required_preservation_count": 0,
    "factorization_readiness_counts": {},
    "factorization_intent_count": 0,
    "factorization_proposal_count": 0,
    "seed_intent_count": 0,
    "seed_proposal_count": 0,
    "unknown_count": 0
  },
  "risk": {
    "compatibility": "LOW",
    "persistence": "MEDIUM",
    "overall": "MEDIUM",
    "reasons": []
  },
  "canonical_mutation": false,
  "destructive_actions": false
}
```

Allowed top-level statuses:

```text
PASS
PASS_WITH_FINDINGS
BLOCKED
```

`PASS` does not mean every cognition has been proven reconstructible. It means the requested analysis completed deterministically with no unresolved findings under the supplied explicit policies/intents.

---

## 17. Evidence bundle

Recommended private bundle shape:

```text
dry-run-report/
├── report.json
├── summary.md
├── pass1/
│   ├── mapping-receipt.json
│   ├── loss-inventory.json
│   ├── heading-inventory.json
│   ├── route-inventory.json
│   └── profile-candidates.json
├── pass2/
│   ├── persistence-assessments.jsonl
│   ├── context-resolution.jsonl
│   ├── evidential-floor.json
│   ├── factorization-readiness.jsonl
│   ├── factorization-intent-results.jsonl
│   ├── seed-readiness.jsonl
│   └── seed-intent-results.jsonl
├── projections/
│   ├── 20000.md
│   ├── 20000.manifest.json
│   └── ...
└── checksums.json
```

The original source file is not copied into the bundle by default.

---

## 18. Source integrity

The analyzer records source SHA-256 before and after analysis.

A valid run requires:

```text
source_sha_before == source_sha_after
```

If `expected_source_sha256` is supplied, it must also equal the before hash.

The implementation exposes no source rewrite API.

---

## 19. Canonical-store isolation

The analyzer accepts no writable `MemoryStore` object.

It exposes no methods named or behaving as:

```text
commit
write_memory
apply_migration
update_store
replace_record
tombstone
archive_move
commit_factorization
promote_seed
```

An optional canonical-head string may be echoed into comparison metadata but cannot be changed by construction.

---

## 20. Loss and heading inventory

The old dry-run loss-accounting behavior remains.

All MNEME-MD losses remain explicit, including:

```text
unknown_heading
unknown_section
no_active_section
unsupported_block_kind
block_kind_not_mapped
malformed_structure (if introduced by future scanner validation)
```

Every heading is counted, including unmatched headings with no body content.

No unknown heading becomes a profile alias automatically.

---

## 21. Profile-extension review candidates

Repeated unknown headings may produce deterministic review candidates.

A candidate may contain:

- opaque or private heading reference;
- occurrence count;
- line numbers;
- body-block kinds;
- unresolved-block contribution;
- suggested action `REVIEW_FOR_PROFILE_EXTENSION`.

It must contain:

```text
target_section = null
```

unless the caller separately supplies an explicit human-reviewed target outside this subsystem.

The analyzer never mutates `profiles/memory-markdown/*.json`.

---

## 22. Route inventory

Route hints come only from matched MNEME-MD section rules.

The report preserves:

```text
route_id
record_count
contributing_section_ids
```

PASS 2 policy may match exact route IDs, but route IDs do not grant authority.

---

## 23. Projection previews

Projection previews are still PASS 1 materialization evidence.

For each budget the analyzer calls `project_profiled_markdown()` over the same mapped proposal set.

A preview may use a synthetic source-head marker such as:

```text
dryrun:<source-prefix>:<profile-prefix>
```

This string is never interpreted as a canonical commit head.

Different budgets may alter preview inclusion but must not alter PASS 1 records or PASS 2 assessments.

---

## 24. Privacy modes

Two modes remain.

### 24.1 `private`

May contain source text, exact headings, exact local paths, exact mapped content, full record IDs, and local preview material.

### 24.2 `sanitized`

Must omit:

- local source path;
- source block text;
- mapped record content text;
- resident labels embedded in source content;
- generated projection bodies;
- exact unmatched heading text;
- full source digest when digest privacy is requested.

Sanitized mode may retain:

- counts;
- reason classes;
- structural line ranges if allowed;
- public profile ID/digest;
- candidate/disposition counts;
- risk levels;
- deterministic salted aliases for record/heading IDs.

Any salt affecting deterministic sanitized aliases must be caller supplied. Random salts do not enter canonical report content.

No automatic upload exists.

---

## 25. Risk model

Risk measures analysis uncertainty, not semantic truth.

The report contains separate `compatibility` and `persistence` risk plus `overall = max(...)` under the ordering:

```text
LOW < MEDIUM < HIGH < BLOCKED
```

### 25.1 Compatibility risk

`LOW` when source integrity is valid and there are no unknown/unsupported structural findings.

`MEDIUM` when unresolved compatibility findings exist but mapped content remains dominant.

`HIGH` when at least 25% of non-heading structural blocks are unresolved, repeated unknown headings dominate unresolved material, or mapped records exist but every requested preview fails to materialize successfully under its declared budget.

`BLOCKED` on source digest mismatch, source mutation, profile validation failure, UTF-8 decode failure, or deterministic rerun mismatch.

### 25.2 Persistence risk

`LOW` when every mapped record has a non-conflicting explicit context, no `UNKNOWN`, no rejected intent, and no `GENERATIZE`/`DISCARD` candidate requiring stronger review.

`MEDIUM` when some records default to `UNKNOWN`, structural/recompute readiness remains incomplete, or explicit review is still required but no destructive candidate was inferred automatically.

`HIGH` when:

- `UNKNOWN` is at least 25% of mapped records; or
- any `GENERATIZE` or `DISCARD` candidate exists; or
- a factorization/seed intent is rejected; or
- policy conflicts exist.

`BLOCKED` on invalid persistence policy schema, authority escalation in supplied CPS objects, cross-pass record reference violations, CPS deterministic replay mismatch, or source-integrity failure.

These thresholds are deterministic heuristics and must be reported as such.

---

## 26. Determinism

With identical:

```text
source bytes
markdown profile bytes
persistence policy bytes
exact record overrides
projection budgets
privacy mode
sanitization salt
factorization intents
seed intents
canonical-head snapshot
```

all deterministic evidence files and report fingerprints must reproduce identically.

Timestamps, temp paths, random IDs, random salts, and host-specific absolute paths are excluded from canonical evidence.

A double-run verification mode compares bundle/report fingerprints and blocks on mismatch.

---

## 27. Identity and authority safety

The analyzer preserves:

```text
DISPLAY LABEL != RESIDENT ID
MEMORY TEXT != IDENTITY AUTHORITY
ASSESSMENT != AUTHORIZATION
PROFILE RULE != AUTHORITY
ROUTE != AUTHORITY
SEED != AUTHORITY
```

It does not call SEDB-RAL or LIMEN in this milestone.

Identity-like content remains data unless an external identity-resolved layer is introduced later.

---

## 28. Failure model

The run becomes `BLOCKED` for:

- expected source digest mismatch;
- source mutation;
- UTF-8 decode failure;
- invalid MNEME-MD profile;
- invalid persistence policy;
- exact context override referencing an unmapped record;
- policy rule using a forbidden selector;
- cross-pass record reference not present in PASS 1;
- authority-bearing CPS object where `authority=false` is required;
- deterministic replay mismatch;
- evidence-bundle checksum mismatch during verification.

The run may complete `PASS_WITH_FINDINGS` for:

- explicit compatibility loss;
- default `UNKNOWN` assessments;
- policy conflicts translated to conservative `UNKNOWN`;
- incomplete readiness;
- rejected optional factorization/seed intents;
- high migration/persistence risk.

The analyzer must not convert these findings into hidden defaults.

---

## 29. Security

Source Markdown is treated as data.

The analyzer must not:

- execute fenced code;
- execute shell snippets;
- follow arbitrary URLs;
- interpret embedded source instructions as runtime instructions;
- load plugins named by source text;
- perform network calls from `RECOMPUTE` metadata;
- send private source to a model automatically.

Public repository fixtures remain synthetic.

---

## 30. Non-goals

This milestone does not implement:

- real canonical migration;
- `MemoryStore.commit()`;
- deletion or tombstoning;
- archive movement;
- regenerative forgetting;
- production cognitive reconstruction;
- semantic proof of reconstructibility;
- model/LLM persistence classification;
- vector retrieval;
- identity resolution;
- LIMEN authorization;
- SEDB-RAL integration;
- SOACR reconstruction orchestration;
- MLF-RM/0.2 evolution;
- automatic profile alias promotion;
- automatic factorization component synthesis;
- automatic equivalence-contract generation.

---

## 31. Proposed API boundary

A minimal public API may expose:

```python
class PrivateResidenceDryRunAnalyzer:
    def analyze(request: DryRunRequest) -> DryRunResult: ...
```

Supporting immutable objects may include:

```text
DryRunRequest
PersistencePolicy
PersistencePolicyRule
ContextResolution
FactorizationReadiness
FactorizationIntent
FactorizationIntentResult
SeedReadiness
SeedIntent
SeedIntentResult
DryRunReport
DryRunResult
```

The analyzer composes existing MNEME-MD and CPS APIs rather than duplicating them.

No mutation callback is accepted.

---

## 32. CLI direction

A future CLI may look like:

```bash
mneme dry-run-memory \
  --source /private/Residence/MEMORY.md \
  --profile profiles/memory-markdown/evemiss-residence-0.1.json \
  --persistence-policy /private/mneme/persistence-policy.json \
  --budget 20000 \
  --budget 64000 \
  --privacy private \
  --output /private/reports/mneme-dry-run
```

No `--commit`, `--delete`, `--apply`, or `--forget` flag exists.

---

## 33. Synthetic acceptance fixture

Public tests use a synthetic Residence-style Markdown file containing:

- known mapped headings;
- a repeated unknown heading;
- an unknown empty heading;
- unsupported fenced code;
- a `Named Identities` entry;
- Traditional-Chinese UTF-8 content;
- records spanning multiple route hints;
- records selected by exact persistence-policy metadata;
- at least one default-UNKNOWN record;
- enough records to exercise multiple projection budgets.

A synthetic persistence policy covers all six CPS candidate dispositions without inspecting source text.

Separate synthetic explicit intents exercise factorization and seed validation.

---

## 34. Acceptance criteria

### D0 — Source immutability

Source SHA-256 before and after analysis is identical.

### D1 — Zero canonical mutation by construction

The analyzer accepts no writable `MemoryStore` and exposes no canonical commit/update API.

### D2 — Two-pass isolation

Every PASS 2 subject record is present in the PASS 1 mapping receipt; raw unmapped Markdown never becomes a CPS subject.

### D3 — Profile-bound compatibility

Every mapped record binds the exact selected MNEME-MD profile ID/digest and source line range.

### D4 — Explicit compatibility loss

Unknown headings, unknown-section blocks, unsupported blocks, and block-kind mismatches remain explicit.

### D5 — Complete heading inventory

All headings are counted, including unmatched headings with no body.

### D6 — Route provenance

Every route hint is traceable to a matched MNEME-MD section rule; no route is inferred from prose.

### D7 — No prose-based persistence inference

Persistence-policy selectors cannot inspect content/raw heading text/regex/similarity/LLM output. Exact structured metadata only.

### D8 — Conservative context resolution

No rule match yields default `UNKNOWN`; conflicting rules yield conservative `UNKNOWN/BLOCKED`; exact record override takes explicit precedence.

### D9 — One assessment per mapped record

PASS 2 produces exactly one CPS `PersistenceAssessment` per mapped PASS 1 record, with context provenance recorded.

### D10 — Evidential-floor visibility

All CPS required preservations are reported; optional factorization intents cannot silently omit them.

### D11 — Factorization readiness isolation

The analyzer may label readiness but does not synthesize anchors, structure, generators, obligations, provenance, or recomputation references from source prose.

### D12 — Explicit factorization intent validation

A supplied factorization intent can produce a CPS `FactorizationProposal` only through existing CPS validation, including component traceability and evidential-floor checks.

### D13 — Seed proposal binding

A supplied seed intent can produce a CPS `CognitiveSeedProposal` only from an accepted factorization result and existing CPS validation; source factorization components cannot be silently replaced.

### D14 — Recompute isolation

`RECOMPUTE` analysis performs no network call and does not synthesize external-source/query contracts.

### D15 — Bounded projection isolation

Different projection budgets may alter preview materialization but never change the PASS 1 proposal set or PASS 2 assessments.

### D16 — Privacy-mode separation

Sanitized evidence excludes private path/text/projection content while preserving structural counts and deterministic policy/CPS evidence.

### D17 — Identity and authority non-escalation

No compatibility mapping, policy rule, assessment, factorization intent, seed intent, route, or report can mint resident identity or grant authority.

### D18 — Deterministic rerun

Identical inputs reproduce identical deterministic report/bundle fingerprints.

### D19 — No de-materialization

No public API performs delete, tombstone, source rewrite, archive move, canonical factorization commit, seed promotion, or regenerative forgetting.

### D20 — Negative evidence

Every D0-D19 family has at least one negative, conflicting, tampered, missing-evidence, cross-pass, privacy-leak, or authority-escalation control where applicable.

---

## 35. Initial implementation milestone

After design approval, the first implementation should remain a bounded observation subsystem:

```text
1. DryRunRequest / report schemas
2. deterministic PersistencePolicy loader/digest
3. two-pass coordinator
4. PASS 1 inventories and projections
5. PASS 2 context resolver
6. CPS assessment aggregation
7. factorization/seed readiness
8. optional explicit intent validation
9. private/sanitized evidence rendering
10. deterministic bundle manifest/fingerprint
11. D0-D20 synthetic acceptance runner
12. exact-remote CI
```

No real private Residence source is committed publicly.

---

## 36. Design closure

The revised Private Residence Dry-Run Analyzer establishes a stricter migration-research boundary:

> **Compatibility analysis determines what existing Markdown explicitly maps to. Persistence analysis then operates only on those mapped memory candidates using explicit deterministic context evidence. The analyzer may measure factorization and cognitive-seed readiness, but it must not invent missing cognitive structure from prose or convert readiness into deletion authority.**

The resulting progression is:

```text
existing MEMORY.md
    -> compatibility evidence
    -> persistence evidence
    -> factorization readiness
    -> optional explicit CPS proposals
    -> later reconstruction experiments
    -> only after separate evidence consider de-materialization
```

Therefore:

```text
MAP BEFORE ASSESS
ASSESS BEFORE FACTORIZE
FACTORIZE BEFORE RECONSTRUCT
PROVE RECONSTRUCTION BEFORE DE-MATERIALIZATION
PRESERVE EVIDENCE BEFORE OPTIMIZING MEMORY
```
