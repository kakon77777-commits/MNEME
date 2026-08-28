# MNEME-CPS/0.1 — Cognitive Persistence Semantics Design

**Status:** Canonical design candidate  
**Date:** 2026-08-28  
**Repository:** `kakon77777-commits/MNEME`  
**Base runtime:** MNEME `main` after MNEME-MD/0.1  
**Canonical memory profile:** `MLF-RM/0.1`  
**Markdown compatibility profile:** `MNEME-MD/0.1`  
**New semantic layer:** `MNEME-CPS/0.1` — Cognitive Persistence Semantics

---

## 1. Purpose

MNEME-CPS defines an additive semantic-analysis layer for deciding **how a cognition-related memory candidate might need to persist**, without changing existing canonical memory records, granting deletion authority, or claiming that reconstructibility has already been proven.

Existing MNEME establishes:

```text
MEMORY.md != MEMORY
MEMORY != CONTEXT
CANONICAL STATE != PROJECTION
```

The cognitive reconstruction theory adds:

```text
MEMORY != COGNITION
```

MNEME-CPS turns that theoretical distinction into a conservative engineering contract.

The core question becomes:

> Given existing canonical memory and cognition-related material, should a future system preserve it exactly, represent its structure, retain a generative reconstruction basis, recompute fresh state when needed, retire it from active memory, or keep the disposition unresolved?

CPS/0.1 answers only at the **assessment and proposal** level.

```text
ASSESSMENT != AUTHORITY
PROPOSAL != COMMIT
RECONSTRUCTIBLE != DISPENSABLE
```

---

## 2. Why CPS is additive rather than a schema rewrite

Three integration approaches were considered.

### A. Add persistence fields directly to `MemoryRecord`

Example:

```json
{
  "persistence": "reconstructible"
}
```

Rejected for CPS/0.1 because the reconstructibility model has not yet been validated strongly enough to become part of the canonical MLF-RM record schema.

### B. Add new canonical record types

Examples:

```text
anchor
generator
obligation
recomputable
```

Rejected for CPS/0.1 because these categories may later prove to be orthogonal roles, relations, or profiles rather than mutually exclusive record types.

### C. Add a sidecar semantic-analysis layer

```text
MemoryRecord / canonical evidence
        ↓
PersistenceAssessment
        ↓
FactorizationProposal
        ↓
CognitiveSeedProposal
        ↓
future reconstruction experiment
```

**Selected approach.**

Existing MLF-RM/0.1 and MNEME-MD/0.1 remain valid and unchanged.

---

## 3. Architectural position

```text
                     AI Residence
                          |
                          v
                    MNEME Core
                  MLF-RM/0.1
          canonical records / transactions
                          |
              +-----------+-----------+
              |                       |
              v                       v
        MNEME-MD/0.1             existing routes /
      Markdown compatibility       projections
              |
              v
     canonical/proposed records
              |
              v
        MNEME-CPS/0.1
 Cognitive Persistence Semantics
              |
     +--------+---------+
     |                  |
     v                  v
PersistenceAssessment  FactorizationProposal
                            |
                            v
                    CognitiveSeedProposal
                            |
                            v
                 future reconstruction bench
                            |
                            v
                           SOACR
                 reconstruction/orchestration
```

CPS does not replace the memory core, Markdown compatibility, SOACR, SEDB-RAL, LIMEN, or AI Residence.

---

## 4. Core invariants

MNEME-CPS/0.1 adopts the following hard invariants:

```text
MEMORY != COGNITION
ASSESSMENT != AUTHORITY
RECONSTRUCTIBLE != DISPENSABLE
FACTORIZE != DELETE
DISCARD CANDIDATE != DELETE AUTHORITY
GENERATED EQUIVALENCE != EVIDENCE EQUALITY
COGNITIVE SEED != CANONICAL EVIDENCE
SEED != AUTHORITY
ARCHIVE != ACTIVE MEMORY
RECOMPUTABLE != STALE-CACHE-REUSABLE
UNKNOWN -> PRESERVE/REVIEW BY DEFAULT
PROPOSAL != COMMIT
```

No CPS object may weaken existing identity, scope, provenance, transaction, or authority boundaries.

---

## 5. Persistence candidate vocabulary

CPS/0.1 defines six candidate dispositions:

```text
PRESERVE
STRUCTURALIZE
GENERATIZE
RECOMPUTE
DISCARD
UNKNOWN
```

These are **candidate persistence semantics**, not mutation commands.

### 5.1 `PRESERVE`

The subject contains exact evidence, decisions, observations, provenance-bearing facts, or other material for which generated equivalence cannot replace the original.

`PRESERVE` means the exact evidence must remain addressable. It does **not** mean the content must appear in every model context.

### 5.2 `STRUCTURALIZE`

The subject appears to contain a relationship, topology, dependency, state structure, classification, or constraint graph whose long-form explanation may be representable by a smaller structural substrate.

The original evidence remains available during CPS/0.1 experiments.

### 5.3 `GENERATIZE`

The subject appears to be constrained-reconstructible cognition for which a future cognitive seed may preserve anchors, structure, generators, obligations, and provenance instead of keeping every surface explanation active.

This is the highest-risk non-destructive candidate in CPS/0.1.

```text
GENERATIZE != SAFE_TO_DELETE
```

### 5.4 `RECOMPUTE`

The future value should normally be obtained from a fresh source, query, computation, or external world observation.

Examples include current package versions, live service state, current prices, current repository HEADs, or other freshness-sensitive values.

Historical observations may still be preserved as evidence.

### 5.5 `DISCARD`

The subject appears to be ephemeral working cognition with no demonstrated long-term evidence, replay, decision, provenance, or reconstruction value.

In CPS/0.1 this means only:

```text
candidate for active-memory retirement
```

It does not authorize archive deletion, record tombstoning, or source destruction.

### 5.6 `UNKNOWN`

Evidence is insufficient or conflicting.

`UNKNOWN` is a first-class successful result, not a parser failure.

Default safety policy:

```text
UNKNOWN -> PRESERVE / REVIEW
```

---

## 6. The evidential floor

A factorization proposal must identify an **evidential floor**: exact canonical items or source references that may not be substituted by generated cognition.

Examples:

- explicit user decisions;
- original experiment outputs;
- commit hashes;
- identity or authority evidence;
- timestamps of important events;
- exact external observations when historical truth matters;
- source documents required to support a derived structure.

The evidential floor is expressed through references rather than duplicated content where possible.

```text
FACTORIZE(C) MAY REDUCE ACTIVE MATERIALIZATION
FACTORIZE(C) MUST NOT ERASE THE EVIDENTIAL FLOOR
```

---

## 7. `PersistenceAssessment`

The primary CPS/0.1 object is a sidecar assessment.

Recommended form:

```json
{
  "assessment_version": "mneme.persistence-assessment/0.1",
  "assessment_id": "pa-...",
  "subject_refs": ["record-..."],
  "candidate": "GENERATIZE",
  "basis": {
    "method": "structural_rule",
    "deterministic": true,
    "reason_codes": ["DERIVABLE_EXPLANATION"],
    "evidence_refs": ["record-..."]
  },
  "required_preservations": ["record-..."],
  "risk": "HIGH",
  "review_state": "UNREVIEWED",
  "authority": false
}
```

### 7.1 Required fields

An assessment must bind:

- exact assessment version;
- assessment ID;
- one or more subject references;
- exactly one candidate disposition;
- assessment method;
- determinism declaration;
- machine-readable reason codes;
- evidence/basis references;
- required preservations;
- risk class;
- review state;
- `authority: false`.

### 7.2 Assessment IDs

For deterministic assessments, the assessment ID is content-addressed over canonical assessment inputs excluding the ID itself.

Non-deterministic model-proposed assessments may use a generated ID, but must declare:

```text
deterministic = false
```

and may never be used as sole evidence for de-materialization.

---

## 8. Assessment methods

CPS distinguishes **what the candidate says** from **how it was produced**.

Initial methods:

```text
EXPLICIT_RULE
STRUCTURAL_RULE
MODEL_PROPOSAL
HUMAN_REVIEW
```

### 8.1 `EXPLICIT_RULE`

A direct deterministic rule applies.

Example:

```text
commit hash with provenance -> PRESERVE candidate
```

### 8.2 `STRUCTURAL_RULE`

A deterministic relation/topology/freshness rule applies.

Example:

```text
current external version + refresh source -> RECOMPUTE candidate
```

### 8.3 `MODEL_PROPOSAL`

A model proposes an interpretation from content.

Allowed only as non-authoritative evidence.

A model proposal must not silently become a canonical persistence decision.

### 8.4 `HUMAN_REVIEW`

A human explicitly records a review decision for experiment planning.

Even human review in CPS/0.1 does not automatically grant canonical delete authority; destructive retention policy remains outside this profile.

---

## 9. Reason-code discipline

Free-form rationale may accompany an assessment, but machine behavior must rely on declared reason codes.

Initial candidate reason families include:

```text
EVIDENTIAL_SOURCE
EXPLICIT_DECISION
IDENTITY_OR_AUTHORITY_EVIDENCE
HISTORICAL_OBSERVATION
STRUCTURAL_DEPENDENCY
STRUCTURAL_STATE
DERIVABLE_EXPLANATION
RECONSTRUCTION_RECIPE_AVAILABLE
OBLIGATION_SET_AVAILABLE
FRESHNESS_REQUIRED
EXTERNAL_SOURCE_AVAILABLE
EPHEMERAL_WORKING_STATE
SUPERSEDED_MATERIALIZATION
INSUFFICIENT_EVIDENCE
CONFLICTING_EVIDENCE
```

The vocabulary may evolve independently of MLF-RM record types.

---

## 10. Risk classes

CPS/0.1 assessments expose a conservative risk class:

```text
LOW
MEDIUM
HIGH
BLOCKED
```

Risk means **risk of acting on the persistence interpretation**, not probability that the content is true.

Suggested defaults:

- `PRESERVE`: LOW action risk because it retains evidence.
- `STRUCTURALIZE`: MEDIUM until structural equivalence is tested.
- `GENERATIZE`: HIGH until reconstruction equivalence is repeatedly demonstrated.
- `RECOMPUTE`: MEDIUM unless freshness source and historical evidence policy are explicit.
- `DISCARD`: HIGH in CPS/0.1 because retirement can hide useful cognition.
- `UNKNOWN`: BLOCKED for destructive action.

---

## 11. Review states

Assessment review states are:

```text
UNREVIEWED
ACCEPTED_FOR_EXPERIMENT
REJECTED
SUPERSEDED
```

`ACCEPTED_FOR_EXPERIMENT` permits only non-destructive experiments such as factorization and parallel reconstruction.

It does not authorize deletion.

---

## 12. `FactorizationProposal`

A `FactorizationProposal` describes how a subject could be represented as a cognitive substrate **without mutating the source memory**.

Conceptual form:

```json
{
  "proposal_version": "mneme.factorization-proposal/0.1",
  "proposal_id": "fp-...",
  "source_assessments": ["pa-..."],
  "source_refs": ["record-..."],
  "anchors": ["record-..."],
  "structure": [],
  "generators": [],
  "obligations": [],
  "provenance_refs": [],
  "recompute_refs": [],
  "unresolved_refs": [],
  "authority": false
}
```

A factorization proposal is an experiment artifact.

```text
FACTORIZATION PROPOSAL != CANONICAL REWRITE
```

---

## 13. Cognitive seed decomposition

CPS uses the theoretical decomposition:

\[
K=(A,S,G,O,P)
\]

where:

- `A` — Anchors;
- `S` — Structure;
- `G` — Generators;
- `O` — Obligations / Invariants;
- `P` — Provenance.

For engineering purposes, recomputation references are tracked separately as `R`, because a source to query later is not equivalent to persistent cognition.

Thus an experimental seed proposal can be represented as:

\[
K'=(A,S,G,O,P,R)
\]

This does not redefine the paper's theoretical seed; `R` is an operational extension.

---

## 14. Anchors

Anchors are references to exact evidence or exact canonical propositions whose semantic identity must survive reconstruction.

Examples:

- accepted decision IDs;
- exact constraints;
- source artifact hashes;
- experiment receipts;
- immutable external observations;
- authority boundaries.

A seed proposal with no declared anchor set cannot be used to claim successful cognitive equivalence for high-risk cognition.

---

## 15. Structure

Structure entries express relationships that should survive surface de-materialization.

Examples:

```text
depends_on
causes
constrains
supersedes
part_of
requires_validation_of
rejected_by
```

CPS/0.1 does not require these relations to become new canonical MLF-RM relation vocabulary immediately.

They may first exist in factorization proposals.

---

## 16. Generators

A generator is a proposal for how cognition can be regenerated.

Initial generator classes may include:

```text
DERIVATION_RULE
RECONSTRUCTION_RECIPE
EXPLANATION_SCHEMA
STATE_RESTORE_RECIPE
QUERY_PLAN
```

A generator must declare its required inputs and obligations.

Generator success is never inferred merely because model output is fluent.

---

## 17. Obligations

Obligations define what a reconstructed cognition must preserve or refresh.

Examples:

```text
ANCHOR_MUST_MATCH
DECISION_MUST_NOT_REVERSE
DEPENDENCY_MUST_HOLD
PROVENANCE_MUST_COVER
FRESH_STATE_REQUIRED
IDENTITY_SCOPE_MUST_MATCH
AUTHORITY_MUST_NOT_ESCALATE
```

Obligations form the future reconstruction verification contract.

---

## 18. Provenance

Every assessment, factorization proposal, and seed proposal must remain traceable to:

- source MemoryRecord IDs;
- source transaction/head when applicable;
- source document fingerprint when imported;
- assessment method;
- generating tool/model version when non-deterministic analysis is involved;
- human review event when applicable.

Generated cognition must never replace provenance-bearing evidence.

---

## 19. Recomputation references

A recomputation reference specifies how fresh world state should be obtained later.

Conceptual fields:

```text
source_kind
source_ref
query_or_operation
freshness_requirement
previous_observation_ref
failure_policy
```

A recomputation reference does not imply that previous observations should be destroyed.

Historical observations may remain evidential memory while future use requires fresh recomputation.

---

## 20. `CognitiveSeedProposal`

A `CognitiveSeedProposal` packages a factorization proposal for parallel reconstruction experiments.

It binds:

- source factorization proposal;
- exact anchors;
- structural relations;
- generator references;
- obligation set;
- provenance coverage;
- recomputation requirements;
- unresolved components;
- seed fingerprint;
- `authority: false`.

```text
COGNITIVE SEED PROPOSAL != CANONICAL COGNITIVE SEED
```

CPS/0.1 intentionally does not define a final canonical seed storage format.

That decision is deferred until reconstruction experiments provide evidence.

---

## 21. Reconstructibility is a property to be demonstrated

CPS does not assume that a `GENERATIZE` candidate is actually reconstructible.

A future reconstruction experiment must test:

\[
\hat C = R(K,X,W)
\]

and validate:

\[
V(\hat C,K,X,W)
\]

before any stronger persistence conclusion can be drawn.

Therefore:

```text
GENERATIZE CANDIDATE
        ↓
FACTORIZE
        ↓
PARALLEL RECONSTRUCTION
        ↓
VERIFY
        ↓
REPEAT
        ↓
ONLY THEN DISCUSS DE-MATERIALIZATION
```

---

## 22. Cognitive equivalence contract

CPS records an equivalence contract for future experiments.

A contract identifies observation queries or invariants `Q` such that:

\[
C \sim_Q \hat C
\]

may be evaluated.

Equivalence does not require:

- token equality;
- sentence equality;
- reasoning trace equality;
- identical model internals.

It does require the declared observation surfaces to remain valid.

Examples:

- same accepted decision;
- same write-authority owner;
- same hard invariants;
- same dependency relation;
- same identity boundary;
- same freshness obligations;
- same evidence references for evidential claims.

---

## 23. No de-materialization in CPS/0.1

CPS/0.1 stops before active-memory retirement or regenerative forgetting.

It may produce:

```text
candidate = DISCARD
candidate = GENERATIZE
```

but no API or schema in this milestone may perform:

```text
delete
archive_move
tombstone
rewrite_source
replace_record
commit_factorization
auto_promote_seed
```

Regenerative Forgetting is an experimental future phase, not CPS/0.1 behavior.

---

## 24. Archive versus active memory

CPS distinguishes conceptual roles:

```text
Archive
Canonical Memory
Cognitive Substrate
Reconstructed Cognition
Working Context
```

CPS/0.1 does not require a physical archive implementation.

The distinction exists to prevent the false conclusion:

```text
not active in working memory
=
deleted from history
```

---

## 25. Interaction with MLF-RM/0.1

MLF-RM/0.1 remains the canonical memory profile.

CPS objects refer to MLF-RM records; they do not add mandatory fields to them.

```text
MLF-RM record
    |
    +--> zero or more CPS assessments
```

A future MLF-RM/0.2 may incorporate persistence semantics only after experimental evidence demonstrates stable requirements.

---

## 26. Interaction with MNEME-MD/0.1

MNEME-MD answers:

> What does this Markdown structure explicitly map to?

CPS answers a different question:

> Given the resulting memory candidate, how might it need to persist?

The combined analysis flow becomes:

```text
Markdown / existing memory
        ↓
MNEME-MD Compatibility Analysis
        ↓
MemoryRecord proposals / canonical records
        ↓
MNEME-CPS Persistence Analysis
        ↓
PersistenceAssessment
        ↓
FactorizationProposal
        ↓
CognitiveSeedProposal
```

No CPS assessment changes MNEME-MD mapping semantics.

---

## 27. Interaction with the Private Residence Dry-Run Migrator

The existing Dry-Run design should be revised after CPS is approved.

Instead of a single migration-analysis pass, it should use two explicit passes:

```text
PASS 1 — Compatibility
MEMORY.md
→ explicit MNEME-MD mapping
→ loss / heading / route evidence

PASS 2 — Persistence
mapped/proposed memory
→ CPS assessment
→ factorization candidates
→ cognitive seed candidates
→ unresolved candidates
```

The Dry-Run subsystem remains read-only and non-authoritative.

---

## 28. Interaction with SOACR

CPS does not implement reconstruction orchestration.

A future SOACR integration may consume accepted experimental seed proposals and perform:

```text
CognitiveNeed
→ seed selection
→ evidence retrieval
→ recomputation
→ reconstruction
→ verification
→ context materialization
```

SOACR may not infer write authority or identity from CPS classifications.

---

## 29. Identity and authority safety

Persistence analysis is not identity analysis.

CPS must preserve existing rules:

```text
DISPLAY LABEL != RESIDENT ID
MEMORY TEXT != IDENTITY AUTHORITY
ASSESSMENT != AUTHORIZATION
SEED != AUTHORITY
```

Identity-like content can be marked as evidence-sensitive, but CPS does not resolve resident identity.

---

## 30. Conservative classification policy

CPS/0.1 uses the following safety ordering for unresolved cases:

```text
PRESERVE / UNKNOWN
before
STRUCTURALIZE / RECOMPUTE
before
GENERATIZE / DISCARD
```

This is not a total semantic ranking. It is a **destructive-risk ordering**.

When evidence is insufficient, the system must not choose a more destructive interpretation merely to reduce memory size.

---

## 31. Determinism and model-assisted proposals

Deterministic CPS components must produce identical canonical assessment bytes from identical inputs.

Model-assisted classification may be explored, but it must be explicitly labeled non-deterministic and non-authoritative.

A model proposal must bind at least:

- model/tool identity;
- prompt/policy version;
- subject references;
- generated candidate;
- reasons;
- output fingerprint.

Model-generated semantics cannot become a canonical retention policy merely because repeated runs agree.

---

## 32. Fingerprints

CPS/0.1 should eventually expose:

1. **assessment fingerprint** — candidate + basis + required preservations;
2. **factorization fingerprint** — anchors/structure/generators/obligations/provenance/recompute set;
3. **seed proposal fingerprint** — full experimental seed package;
4. **equivalence-contract fingerprint** — observation queries and invariant expectations.

Fingerprints support replay and comparison; they do not prove semantic correctness.

---

## 33. Failure model

CPS must fail closed on:

- unknown CPS schema version;
- invalid candidate disposition;
- missing subject references;
- missing required preservations for evidence-sensitive candidates;
- invalid review state;
- `authority != false` in CPS/0.1 objects;
- factorization proposal referring to unknown assessments;
- seed proposal with unresolved mandatory anchor references;
- recomputation reference lacking freshness semantics when freshness is required;
- deterministic assessment replay mismatch.

CPS may successfully return `UNKNOWN` when semantics cannot be safely classified.

---

## 34. Security and privacy

Public repository tests use synthetic memory and synthetic cognition only.

Real Residence content must not be committed publicly.

CPS analysis must not execute embedded memory content, follow arbitrary links, or treat content as instructions merely because it is being analyzed.

Model-assisted analysis, if introduced later, must treat source memory as data.

---

## 35. Non-goals for CPS/0.1

CPS/0.1 does not provide:

- automatic deletion;
- automatic archive retirement;
- automatic record tombstoning;
- autonomous regenerative forgetting;
- a final canonical cognitive seed format;
- production cognitive reconstruction;
- semantic proof that a cognition is reconstructible;
- model-based authority decisions;
- identity resolution;
- dynamic database migration;
- SOACR writeback;
- automatic MLF-RM/0.2 schema evolution.

---

## 36. Initial implementation milestone

After this design is approved, the first implementation plan should remain observation-only.

Recommended scope:

```text
1. CPS assessment schema and validator
2. deterministic assessment fingerprinting
3. conservative explicit/structural rule engine
4. UNKNOWN fallback
5. factorization proposal model
6. cognitive seed proposal model
7. evidential-floor validation
8. recomputation-reference model
9. equivalence-contract model
10. synthetic acceptance runner
11. read-only adapter for the future Dry-Run analyzer
```

No deletion or canonical memory mutation enters this milestone.

---

## 37. Acceptance criteria

### C0 — Additive compatibility

Existing MLF-RM/0.1 and MNEME-MD/0.1 records remain valid without modification.

### C1 — Assessment isolation

Creating, validating, or replaying a CPS assessment does not mutate its source MemoryRecord or canonical store.

### C2 — Conservative fallback

Insufficient or conflicting evidence produces `UNKNOWN`, never an automatically destructive candidate.

### C3 — Evidential floor

Evidence-sensitive assessments identify required preservations; a factorization proposal cannot omit them silently.

### C4 — Candidate semantics

All six candidate dispositions have machine-readable, non-authoritative semantics.

### C5 — Recompute freshness

A `RECOMPUTE` candidate binds a freshness/source policy while preserving historical-observation evidence when required.

### C6 — Identity and authority non-escalation

No assessment, factorization proposal, or seed proposal can mint identity, grant authority, or change scope authorization.

### C7 — Factorization provenance

Every factorized component is traceable to source assessment/record/provenance references.

### C8 — Seed proposal completeness

A seed proposal declares anchors, structure, generators, obligations, provenance, recomputation requirements, and unresolved components explicitly.

### C9 — Reconstruction isolation

CPS objects may be used for parallel reconstruction experiments but do not replace source memory or evidence.

### C10 — Equivalence contract

Cognitive equivalence is represented through declared observation surfaces/invariants rather than token or trace equality.

### C11 — No de-materialization

No CPS/0.1 public API performs deletion, tombstoning, source rewrite, archive movement, or canonical factorization commit.

### C12 — Deterministic replay

Deterministic assessments and proposal fingerprints reproduce identically from identical inputs.

### C13 — Negative evidence

Every positive acceptance family has at least one invalid, conflicting, missing-evidence, stale, or authority-escalating negative counterpart.

---

## 38. Experimental progression after CPS/0.1

CPS establishes only the semantics needed to run experiments safely.

The intended progression is:

```text
Phase A — Persistence Assessment
Phase B — Factorization Proposal
Phase C — Cognitive Seed Proposal
Phase D — Parallel Reconstruction
Phase E — Equivalence / Obligation Bench
Phase F — Long-Horizon Replay
Phase G — only then consider MLF-RM/0.2
Phase H — only after further evidence consider Regenerative Forgetting
```

The order is intentional.

```text
PROVE RECONSTRUCTION BEFORE DE-MATERIALIZATION
PRESERVE EVIDENCE BEFORE OPTIMIZING MEMORY
```

---

## 39. Design closure

MNEME-CPS/0.1 establishes the following architectural refinement:

> **MNEME canonical memory is not required to preserve every previously materialized cognition in the same surface form. However, before any cognition can be de-materialized, the system must first distinguish irreducible evidence from structural, generative, recomputable, ephemeral, and unresolved material; preserve an evidential floor; construct non-authoritative factorization/seed proposals; and demonstrate reconstruction equivalence under explicit obligations.**

The immediate engineering consequence is conservative:

```text
Do not rewrite MLF-RM/0.1.
Do not delete memory.
Do not promote model guesses to retention policy.
Add a sidecar persistence-semantics layer first.
Measure before evolving the canonical schema.
```

This allows MNEME to evolve from a safe canonical memory layer toward a possible **Canonical Cognitive Substrate** without invalidating the already verified memory, transaction, projection, and Markdown-compatibility foundation.
