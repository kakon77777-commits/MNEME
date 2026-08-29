# MNEME 0.5.0a1 Unified Profile Integration — Design Specification

**Date:** 2026-08-29
**Status:** design candidate for Neo.K and Lares review
**Canonical integration base:** GitHub `main@c21546a263920e0f80701696e1857c203917d701`
**Accepted Claude input:** `feat/claude-global-memory-transition-v0.1@89bb1509f2bb96c4067d12c15094adacc2512b67`
**Target package candidate:** `mneme-memory==0.5.0a1`

## 1. Decision

MNEME v0.2, v0.3 and v0.4 are not competing memory engines and are not a
linear sequence of canonical data formats. They are additive package-delivery
stages containing distinct profiles and sidecars over one unchanged canonical
core.

The unified candidate SHALL absorb them into the existing architecture as
separate typed capabilities:

```text
MLF-RM/0.1                              canonical memory core
├─ MNEME-MD/0.1                         Markdown compatibility engine
│  ├─ evemiss-residence/0.1             frozen baseline dialect
│  └─ evemiss-residence/0.2             explicit additive observed dialect
├─ MNEME-CPS/0.1                        read-only persistence sidecar
├─ MNEME-PRIVATE-RESIDENCE-DRY-RUN/0.2  read-only pre-migration analyzer
├─ Claude Global Memory Transition/0.1  bounded consumer adapter
└─ SOACR adapter                        read-only planning/materialization seam
```

No profile creates a second writable canonical store. `MemoryRecord`,
`TransactionProposal`, `MemoryStore` and MLF-RM exact-head history remain the
canonical memory truth.

## 2. Why the target is 0.5.0a1

The current remote main and the accepted Claude branch independently advanced
from the same v0.3 base:

```text
84b9b0ee94115902d7a9e6acfdc48372e60fd673  MNEME-CPS/0.1 merged baseline
├─ c21546a263920e0f80701696e1857c203917d701  remote main
│  ├─ Private Residence Dry-Run/0.2
│  └─ evemiss-residence/0.2
│     package 0.4.0a2
└─ 89bb1509f2bb96c4067d12c15094adacc2512b67  accepted Claude branch
   ├─ installed schema-resource hardening
   ├─ writer/record-ID hardening
   ├─ Claude global adapter/publisher/importer
   └─ runtime-audited acceptance
      package 0.4.0a1
```

Reusing `0.4.0a1` or `0.4.0a2` for the combined tree would conceal a material
new capability set and create ambiguous wheel provenance. The combined
candidate therefore advances to `0.5.0a1`. This version number describes the
package assembly only; it does not rename any stable profile contract.

## 3. Source authority and provenance

### 3.1 Canonical source

The runtime source of truth is the Git repository and GitHub main line, not the
ZIP archive directory.

The directory:

```text
D:\我的研究\學術討論\論文\真終極\真本體論12\MNEME
```

is a research, closure and reproducibility archive. Its bundles are immutable
source evidence and SHALL NOT be imported as a second live checkout or runtime
store.

### 3.2 Frozen archive evidence

The design uses these archives only as corroborating evidence:

```text
MNEME_v0.2_MNEME-MD_Compatibility_Profile_2026-08-27.zip
SHA256 5EB6A836BF9611031275C5F42CEBE7A9B201710F62637A247E906681295A0300

MNEME_v0.3_CPS_0.1_Closure_2026-08-28.zip
SHA256 BA32A63447449EEA6716788BE724C1069967712047F127D1192EFA7AEDC62CA2

MNEME_v0.4_Private_Residence_Two_Pass_Dry_Run_Closure_2026-08-28.zip
SHA256 833DC699EBDC44781763CAD2810FBA615023CC5B8CAFA2CE4A4B26F2EBAE49D9
```

The archive explicitly named `PRIVATE` is not an integration input and SHALL
not be read, copied, hashed into public evidence or used by synthetic tests.

### 3.3 Claude review evidence

The Claude transition input is accepted only at this exact pair:

```text
HEAD  89bb1509f2bb96c4067d12c15094adacc2512b67
tree  0fcac15cbccdde61013b8dfa6938ed19ca161ef8
```

Lares final acceptance:

```text
D:\Ai\work together\EveMissLab-PMW-Fabric\runtime\task-handoffs\2026-08-29_claude-lares_to_01a037c2_mneme-claude-global-final-fixwave-002-review.md
bytes   4388
SHA256  50E7C5E999DE8BEAF80FF7B45856750CD9B398E28FC01F2BE279BB4185EADCCF
verdict ACCEPT / blocking 0 / nonblocking 0
```

The accepted candidate is synthetic-only. Acceptance is not local-activation,
merge, release or deployment authority.

## 4. Ownership boundaries

| Owner | Canonical responsibility | Explicit exclusions |
|---|---|---|
| SEDB-RAL / LIMEN | resident/task identity, status, authority and private capability evidence | memory body, retrieval strategy, working context |
| MNEME MLF-RM | canonical typed memory records, provenance, transactions, exact-head store, deterministic projections | identity resolution, context-window selection |
| MNEME-MD | explicit Markdown-dialect mapping, proposals, loss reports and compatibility projection | semantic guessing, identity minting, direct commit authority |
| MNEME-CPS | persistence assessments and factorization/recomputation/seed proposals | deletion, reconstruction proof, canonical mutation |
| Dry-Run/0.2 | two-pass read-only migration/factorization evidence | writable store, migration, delete/tombstone, seed/profile promotion |
| Claude adapter | bounded global projection and byte-preserving managed import | canonical memory ownership, Claude-originated writeback |
| SOACR | MemoryNeed, strategy selection, scope/result admission and Working Context materialization | second canonical memory store, identity registry |
| PMW Fabric | optional digest-bound transport evidence | authority, currentness, adoption or private memory custody |

These boundaries are cumulative. Package integration does not transfer
ownership between layers.

## 5. Canonical core remains MLF-RM/0.1

The integrated candidate SHALL NOT evolve the `MemoryRecord` schema, transaction
envelope or exact-head semantics merely to combine package branches.

The following accepted hardening from the Claude branch SHALL be retained:

- installed-wheel schema resources through `mneme.schemas`;
- one canonical schema body per `$id`;
- no root-level duplicate schema directory;
- single-writer store serialization;
- global `record_id` uniqueness;
- deterministic commit/readback behavior;
- exact schema bytes in source and installed wheel.

The remote-main dry-run code currently reads several root-level schema paths.
During integration, its four additional schemas SHALL move into the same
installed resource package and every dry-run validator SHALL call the shared
schema loader. The integration SHALL NOT reintroduce filesystem fallback or
vendored copies.

The expected union is 21 installed schema resources:

```text
10 MLF-RM / MNEME-MD / MNEME-CPS resources
+ 4 Dry-Run/0.2 resources
+ 7 Claude transition resources
= 21 canonical installed schema resources
```

The four dry-run additions are:

```text
factorization-intent-0.1.schema.json
persistence-policy-0.1.schema.json
private-residence-dry-run-report-0.2.schema.json
seed-intent-0.1.schema.json
```

## 6. Markdown profile composition

`MNEME-MD/0.1` is the compatibility engine. `evemiss-residence/0.1` and
`evemiss-residence/0.2` are explicit data profiles consumed by that engine.

Rules:

1. v0.1 remains byte/digest frozen.
2. v0.2 remains additive and separately identified.
3. The caller selects the exact profile ID; profile choice is never inferred
   from source prose, fuzzy heading similarity, embeddings or an LLM.
4. Unknown headings and unsupported blocks remain explicit loss.
5. The v0.2 mixed identity-registry paragraph remains unmapped.
6. A Markdown display label or identity section remains a memory fact and does
   not mint RAL/LIMEN identity.
7. Profile mapping returns proposals and receipts, not write authority.

The v0.2 profile may be used for a later authorized private read-only dry run.
It SHALL NOT trigger automatic migration merely because its dialect matches.

## 7. CPS remains an observation-only sidecar

MNEME-CPS/0.1 is available on demand after canonical or proposed records are
selected. It is not part of every recall or Working Context hot path.

The integrated package retains:

```text
ASSESSMENT != AUTHORITY
RECONSTRUCTIBLE != DISPENSABLE
FACTORIZE != DELETE
SEED != AUTHORITY
UNKNOWN -> PRESERVE / REVIEW BY DEFAULT
```

CPS outputs remain sidecar evidence. `PRESERVE`, `STRUCTURALIZE`, `GENERATIZE`,
`RECOMPUTE`, `DISCARD` and `UNKNOWN` are candidate dispositions, not canonical
state transitions.

No CPS result alone may:

- delete or tombstone a `MemoryRecord`;
- advance the MNEME head;
- promote a factorization or seed;
- claim reconstruction or behavioral equivalence;
- grant SOACR admission or RAL authority.

## 8. Dry-Run/0.2 remains pre-adoption evidence

The Private Residence two-pass analyzer is integrated as an optional,
read-only subsystem:

```text
PASS 1  explicit MNEME-MD profile mapping
        → mapped proposals + heading/loss/route evidence

PASS 2  mapped records only + explicit structured AssessmentContext
        → CPS assessments + readiness + optional caller intents

OUTPUT  private or sanitized evidence bundle
```

It SHALL retain all current negative capabilities:

```text
canonical_mutation = false
destructive_actions = false
no writable MemoryStore input
no migration
no deletion / tombstone / archive move
no reconstruction
no regenerative forgetting
no automatic factorization or seed generation
```

Persistence-policy selectors may inspect only closed structured metadata. They
must not inspect raw source prose, `content.text`, regex matches, embeddings,
similarity scores or LLM output.

Integration tests use synthetic fixtures only. A later real private dry run
requires a fresh task-local identity/private-capability decision and Neo.K's
explicit authorization. Its private evidence stays within the private custody
boundary; only schema-validated sanitized evidence may leave.

## 9. Claude consumer composition

The accepted Claude transition is integrated as a consumer of canonical global
records, not as another persistence layer.

```text
MLF-RM committed global records
→ exact global route
→ <= 16000-byte whole-record projection
→ exact publication plan
→ internally enforced publisher
→ byte-preserving managed block in Claude user memory
→ digest-bound receipts
```

The integration SHALL retain:

- exact committed transaction and manual-authorization binding;
- publisher execution structurally inside import apply;
- no caller-supplied publication capability;
- stale-target and path/reparse/hardlink controls;
- runtime-audited private/production/network/provider/MCP/Bridge/external-CLI
  effect evidence;
- `real_claude_user_memory = NOT_TOUCHED` in the code-candidate gate;
- `CGM-023/024/026/027 = NOT_RUN_LOCAL_ACTIVATION_REQUIRED`.

Claude's `CLAUDE.md` remains a generated consumer surface. Claude output cannot
commit, correct, delete or promote canonical MNEME memory.

## 10. SOACR and context-memory seam

The unified package does not replace SOACR. The seam is:

```text
RAL/LIMEN verified identity + capability
→ SOACR MemoryScopeRequest / MemoryScopeDecision
→ MNEME read-only route/projection adapter
→ SOACR result admission and ContextPlan
→ Working Context
→ ContextMaterializationReceipt
```

MNEME returns records, projections and digest-bound evidence. SOACR decides
whether and how those results enter bounded Working Context. Neither a
Markdown mapping, CPS assessment, dry-run report nor Claude publication receipt
is by itself a scope/admission decision.

Correction/currentness follows source ownership:

```text
MNEME/domain owner correction or tombstone
→ source head advances
→ SOACR ContextInvalidationObservation
→ derived context invalidation / A2 repair
```

Transport evidence never promotes source currentness.

## 11. Git integration topology

Implementation SHALL start from exact remote main `c21546a...`, not from the
stale local `main@84b9b0e...` and not from a ZIP extraction.

The accepted Claude branch is a pinned integration input. Its changes are
replayed/cherry-picked by semantic slice onto the new base; the integration
must not use an unreviewed wholesale conflict choice.

Conflict adjudication order:

1. preserve remote-main Dry-Run/0.2 and `evemiss-residence/0.2` semantics;
2. preserve accepted Claude public interfaces and final review fixes;
3. retain Claude-branch schema packaging, writer-lock and record-ID hardening;
4. migrate dry-run validators to installed resources rather than restoring root
   schemas;
5. set package and `mneme.__version__` to `0.5.0a1` only after the combined
   source tree is coherent;
6. update README/workflows as a combined view, not by taking either side whole.

The design branch/worktree is:

```text
branch    feat/mneme-unified-profile-integration-v0.5
worktree  D:\Ai\work together\MNEME\.worktrees\unified-profile-integration-v0.5
base      c21546a263920e0f80701696e1857c203917d701
tree      5ad5725ca685df334110b257e4004d9274e35674
baseline  191 passed / 0 failed
```

No push, PR or merge is authorized by this design.

## 12. Runtime selection model

The unified package exposes capabilities, not one monolithic mode switch.

| Use case | Enabled layers |
|---|---|
| Ordinary canonical recall | MLF-RM + read-only route/projection |
| Legacy Markdown import proposal | MLF-RM + explicit MNEME-MD profile |
| Persistence research | selected records + CPS sidecar |
| Pre-migration assessment | explicit MD profile + Dry-Run/0.2 + optional intents |
| Claude global projection | committed global route + Claude consumer adapter |
| SOACR Working Context | SOACR decision/admission + MNEME read seam |

CPS and Dry-Run are not automatically enabled on every retrieval. Profile
selection and private-source access are explicit inputs.

## 13. Data and upgrade compatibility

The integration performs no automatic data migration.

- Existing MLF-RM/0.1 stores remain readable under unchanged core contracts.
- Existing v0.1 Markdown profile digests remain frozen.
- v0.2 is a new selectable profile, not an in-place mutation of v0.1.
- CPS and Dry-Run evidence remain noncanonical sidecars.
- Existing Claude synthetic receipts remain evidence for their exact source
  tree; they are not replayed as receipts for the integrated tree.
- The integrated candidate produces new package/build/schema and acceptance
  digests.

Any future evolution of `MemoryRecord`, transaction or store format requires a
separate migration design and versioned schema family.

## 14. Acceptance gates

### 14.1 Frozen input gates

- remote main exact base/tree verified;
- Claude exact head/tree and final Lares acceptance verified;
- research archive hashes recorded but archives remain non-runtime evidence;
- both source worktrees clean before integration.

### 14.2 Core and schema gates

- all prior MLF-RM A0-A6 controls pass;
- all 21 schema resources are installed-wheel assets;
- source and wheel schema names/bytes/digests match exactly;
- no root-level or vendored duplicate schema bodies;
- writer lock, exact-head and global record-ID controls pass.

### 14.3 Profile gates

- MNEME-MD M0-M8 pass;
- `evemiss-residence/0.1` digest remains frozen;
- v0.2 R0-R5 pass;
- v0.1 does not guess v0.2 dialect;
- mixed identity-registry paragraph remains explicit loss;
- no profile or Markdown prose mints identity.

### 14.4 CPS and Dry-Run gates

- CPS C0-C13 and all controls pass;
- Dry-Run D0-D20 and all controls pass;
- analyzer accepts no writable `MemoryStore`;
- canonical bytes/head remain unchanged;
- raw Markdown never enters CPS classification;
- deterministic private/sanitized bundles reproduce;
- sanitized output rejects nested private fields and contains no private body,
  source path or raw source digest.

### 14.5 Claude gates

- all accepted Claude unit and adversarial populations pass;
- original publication-capability forgery remains impossible;
- runtime observer catches real UDP, subprocess and outside-root writes;
- same-root acceptance reports are byte/digest deterministic;
- actual user-memory and local activation cases remain NOT_RUN.

### 14.6 Combined package gates

- full combined suite passes on Windows and Ubuntu;
- all six acceptance families run in CI:
  - Fresh Memory Core;
  - MNEME-MD/0.1;
  - EveMiss profile v0.2;
  - MNEME-CPS/0.1;
  - Dry-Run/0.2;
  - Claude Global Transition/0.1;
- clean `git archive` wheel builds without network during build;
- installed imports and all CLIs/adapters execute from a clean target;
- package metadata is exactly `0.5.0a1`;
- worktree is clean and external repositories/private sources are unchanged.

CI SHALL report the six named acceptance surfaces individually rather than
collapsing them into one generic PASS.

## 15. Real-use sequencing after code acceptance

The first real-use design is separate from this integration:

```text
fresh task-local RAL/LIMEN binding
→ explicit private read capability
→ select exact MNEME-MD profile
→ read-only Dry-Run/0.2
→ private review + sanitized evidence
→ explicit Neo.K adoption decision
→ separately approved MLF-RM transaction
→ canonical commit/readback
→ separately approved Claude local activation
→ /memory readback or explicit unmeasured state
```

No synthetic, CI, archive or reviewer result substitutes for those live facts.

## 16. Explicit non-goals

This integration does not implement:

- real private-memory migration;
- automatic profile selection;
- autonomous writeback;
- deletion, tombstoning or regenerative forgetting;
- factorization/seed promotion;
- reconstruction or equivalence proof;
- resident identity creation;
- PMW live federation;
- provider execution;
- production deployment;
- merge, release or publication.

## 17. Success definition

The design succeeds when one `0.5.0a1` source tree contains the upstream
Dry-Run/v0.2 profile line and the accepted Claude consumer line while
preserving one canonical MLF-RM store, strict ownership boundaries, installed
schema resources and every prior negative control.

Success is a reviewed synthetic code candidate. It is not permission to open a
private Residence, migrate memory, mutate real Claude user memory or deploy.
