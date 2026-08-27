# MNEME Private Residence Dry-Run Migrator — Design Specification

**Status:** Canonical design candidate  
**Date:** 2026-08-27  
**Repository:** `kakon77777-commits/MNEME`  
**Base:** `main@ca9dbe73c04a57f90de4bdb863bd0664f3ab6320`  
**Base package:** `mneme-memory==0.2.0a1`  
**Canonical memory profile:** `MLF-RM/0.1`  
**Markdown compatibility profile:** `MNEME-MD/0.1`

## 1. Purpose

The Private Residence Dry-Run Migrator is a read-only analysis layer for evaluating existing private Residence `MEMORY.md` files against MNEME before any real migration is allowed.

It answers a narrower question than a migration engine:

> Given an existing private `MEMORY.md` and an explicitly selected MNEME-MD profile, what would map safely, what would remain unresolved, what routes would be suggested, and what bounded projections would be produced — without mutating the source file or canonical memory?

The subsystem is intentionally evidence-only.

```text
DRY RUN != MIGRATION
ANALYSIS != COMMIT
REPORT != AUTHORITY
```

## 2. Core design choice

Three approaches were considered.

### A. Direct converter

Parse the source and immediately build or write canonical records.

Rejected for this phase because incomplete compatibility profiles can silently turn unknown conventions into wrong canonical memory.

### B. LLM-assisted semantic analyzer

Ask a model to classify unknown headings, paragraphs, aliases, or identity-like strings.

Rejected for this phase because it reintroduces non-deterministic semantic guessing into a layer whose purpose is to establish migration evidence.

### C. Evidence-only dry-run migrator

Run deterministic MNEME-MD mappings, produce proposals and analysis reports, but expose no canonical write path.

**Selected approach.**

## 3. Position in the architecture

```text
Private Residence MEMORY.md
        |
        v
Private Residence Dry-Run Migrator
        |
        +--> source fingerprint
        +--> selected profile fingerprint
        +--> profiled MemoryRecord proposals
        +--> mapping receipt
        +--> explicit loss inventory
        +--> unknown-heading inventory
        +--> route-hint inventory
        +--> bounded preview projections
        +--> migration-risk assessment
        +--> profile-promotion candidates
        |
        v
Evidence bundle only

NO MemoryStore.commit()
NO source rewrite
NO profile mutation
```

The existing MNEME runtime remains unchanged.

## 4. Hard invariants

```text
SOURCE BYTES BEFORE == SOURCE BYTES AFTER
CANONICAL HEAD BEFORE == CANONICAL HEAD AFTER
DRY-RUN RESULT != TransactionProposal AUTHORITY
PROFILE CANDIDATE != PROFILE UPDATE
UNKNOWN HEADING != AUTO-ALIAS
DISPLAY LABEL != RESIDENT ID
LOSS REPORT != DATA LOSS
PREVIEW PROJECTION != CANONICAL MEMORY
```

The implementation must make these invariants testable.

## 5. Inputs

A dry-run request contains:

```text
source_path
profile
optional source_label
projection_budgets
optional expected_source_sha256
```

### 5.1 Source path

The caller supplies a local Markdown path.

The path itself is private operational metadata and must not be copied into public reports by default.

### 5.2 Profile

The caller supplies an already loaded `MemoryMarkdownProfile` or a path to a profile document.

The dry-run migrator does not modify that profile.

### 5.3 Projection budgets

One or more byte budgets may be supplied for preview materialization, for example:

```text
20_000
24_000
64_000
```

Each preview binds the same proposed semantic record set and profile digest.

### 5.4 Expected source digest

If supplied, the source SHA-256 must match before analysis begins.

A mismatch fails closed.

## 6. Outputs

The primary output is a `DryRunReport` and a directory-style evidence bundle.

Recommended bundle shape:

```text
dry-run-report/
├── report.json
├── summary.md
├── mapping-receipt.json
├── loss-inventory.json
├── heading-inventory.json
├── route-inventory.json
├── profile-candidates.json
├── projections/
│   ├── 20000.md
│   ├── 20000.manifest.json
│   ├── 24000.md
│   ├── 24000.manifest.json
│   └── ...
└── checksums.json
```

The bundle is analysis evidence, not canonical memory.

## 7. DryRunReport model

A report contains at least:

```json
{
  "report_version": "mneme.private-residence-dry-run/0.1",
  "status": "PASS_WITH_LOSS",
  "source": {
    "sha256": "...",
    "byte_count": 0,
    "line_count": 0,
    "mutated": false
  },
  "profile": {
    "profile_id": "evemiss-residence/0.1",
    "profile_digest": "..."
  },
  "mapping": {
    "mapped_record_count": 0,
    "record_type_counts": {},
    "scope_counts": {}
  },
  "loss": {
    "loss_count": 0,
    "reason_counts": {},
    "unknown_heading_count": 0
  },
  "routes": {
    "route_hint_counts": {}
  },
  "projections": [],
  "profile_candidates": [],
  "risk": {
    "level": "LOW",
    "reasons": []
  },
  "canonical_mutation": false
}
```

`status: PASS` means the dry-run completed deterministically; it does not mean the source is fully understood.

Allowed statuses in v0.1:

```text
PASS
PASS_WITH_LOSS
FAIL
```

## 8. Source safety

The source file is read exactly once for canonical source binding and may be read again only for verification.

The migrator records:

- source SHA-256 before analysis;
- source byte count;
- source line count;
- source SHA-256 after analysis.

The run is valid only when:

```text
source_sha_before == source_sha_after
```

No API in this subsystem accepts replacement Markdown content for the original source path.

## 9. Canonical-store safety

The dry-run migrator must not require a writable `MemoryStore`.

If the caller supplies a store only for comparison, the subsystem may read its current `HEAD`, but the implementation must not expose or call:

```text
MemoryStore.commit
MemoryStore._atomic_write_head
```

The canonical head before and after a dry run must be equal.

A minimal v0.1 implementation may omit store input entirely and set:

```text
canonical_mutation = false
```

by construction.

## 10. Mapping behavior

The dry-run migrator reuses `propose_profiled_markdown_import()` from MNEME-MD/0.1.

It does not add a second semantic parser.

```text
DryRun Migrator
    uses
MNEME-MD profiled importer
    uses
explicit profile rules
```

No new heading inference is permitted here.

## 11. Mapping summary

The report summarizes mapped proposals by:

- record type;
- exact `{scope.kind, scope.subject}`;
- section ID;
- route hint;
- source line range.

The report may include record IDs and source line ranges.

It must not expose private source text in public-safe summaries unless the caller explicitly requests a private-detail mode.

## 12. Privacy modes

The first design defines two report detail levels.

### 12.1 `private`

For local user inspection.

May include:

- source block text;
- exact headings;
- record content;
- local-only migration preview.

### 12.2 `sanitized`

For issue reports, public GitHub evidence, or external review.

Must omit:

- local source path;
- source block text;
- resident names or labels embedded in content;
- full source digest when policy requires digest privacy;
- generated projection content.

Sanitized mode retains counts, reason classes, line ranges if allowed, profile ID/digest, and synthetic-safe structural metrics.

The default API mode for real Residence files is `private` locally, but no automatic public upload exists.

## 13. Loss inventory

All MNEME-MD loss entries are preserved.

The migrator aggregates them by reason:

```text
unknown_heading
unknown_section
no_active_section
unsupported_block_kind
block_kind_not_mapped
malformed_structure
```

The report additionally records:

- total loss entries;
- affected source line count;
- loss ratio by structural block count;
- unknown heading frequency;
- unknown heading body-block count.

No unknown content is silently dropped from the report.

## 14. Heading inventory

The heading inventory is the main instrument for discovering real-world Markdown dialects.

Each encountered heading produces an observation entry:

```json
{
  "normalized_heading": "current state",
  "matched": false,
  "matched_section_id": null,
  "occurrences": 3,
  "line_numbers": [12, 88, 140]
}
```

For privacy-preserving sanitized reports, an unmatched heading may be replaced by a salted or run-local digest while preserving occurrence counts.

## 15. Profile-promotion candidates

The dry-run migrator may identify **candidates for human review**.

A candidate is not an alias update.

```text
PROFILE CANDIDATE != PROFILE RULE
```

Candidate evidence may include:

- unmatched normalized heading;
- occurrence count;
- structural block kinds under it;
- nearby matched section transitions;
- percentage of total unresolved blocks;
- whether the same heading repeats consistently.

The subsystem must not assign a canonical target section automatically.

Example:

```json
{
  "candidate_id": "candidate-...",
  "heading": "Current",
  "occurrences": 5,
  "block_kinds": {"unordered_list_item": 12},
  "suggested_action": "REVIEW_FOR_PROFILE_EXTENSION",
  "target_section": null
}
```

## 16. Route inventory

Route hints are copied only from the selected profile's matched section rules.

The migrator reports:

- route ID;
- number of proposed records associated with the route;
- section IDs contributing to the route.

No new route is synthesized from prose.

## 17. Projection previews

For each requested budget, the dry-run migrator calls `project_profiled_markdown()` over proposed records.

Each preview is bound to a synthetic dry-run source head, not a canonical store head.

Recommended source-head namespace:

```text
dryrun:<source-sha-prefix>:<profile-digest-prefix>
```

If the current projection API requires a plain string only, this value remains metadata and must never be interpreted as a canonical commit head.

A preview proves materialization behavior only.

## 18. Projection comparison

The report compares preview budgets using:

- included record count;
- omitted record count;
- byte count;
- section coverage;
- same compatibility-entry source set;
- budget-exceeded omissions.

This makes host-limit planning explicit.

Example:

```text
20 KB preview: 91 included / 229 omitted
64 KB preview: 300 included / 20 omitted
```

The canonical proposal set remains unchanged across budgets.

## 19. Migration risk model

The dry-run migrator produces a deterministic heuristic risk level.

This risk level measures **migration uncertainty**, not semantic correctness.

Initial levels:

```text
LOW
MEDIUM
HIGH
BLOCKED
```

Suggested v0.1 rules:

### LOW

- zero unknown headings;
- zero unsupported blocks;
- all structural blocks mapped or intentionally ignored by an explicit rule;
- projection preview succeeds for at least one requested budget.

### MEDIUM

- unresolved content exists but mapped content remains dominant;
- no source-integrity failure;
- no profile validation failure.

### HIGH

- unresolved blocks are at least 25% of non-heading structural blocks; or
- repeated unknown headings account for meaningful unresolved content; or
- no requested bounded projection can include required core sections.

### BLOCKED

- source digest mismatch;
- source mutation detected;
- profile validation failure;
- UTF-8 decode failure;
- deterministic rerun mismatch.

Risk rules must be documented and tested; they are not model judgments.

## 20. Determinism

With identical:

- source bytes;
- selected profile bytes;
- projection budgets;
- privacy mode;

then all deterministic report fields must be identical.

Run-local timestamps, temp paths, and random salts are forbidden from canonical report content unless explicitly separated as non-deterministic envelope metadata.

A sanitized heading digest, if used, must derive from a caller-supplied salt so determinism remains controllable.

## 21. Rerun verification

The migrator supports a double-run verification mode:

```text
run A
run B
compare deterministic report fingerprints
```

A mismatch produces `BLOCKED`.

This is required before any future real migration workflow can use a dry-run result as evidence.

## 22. Evidence bundle fingerprint

The bundle manifest records SHA-256 for every generated evidence file.

A bundle fingerprint is derived from canonical JSON containing ordered file paths and hashes.

The original private source file itself is not copied into the bundle by default.

## 23. No identity escalation

The dry-run migrator preserves the current MNEME-MD rule:

```text
Named Identities -> fact/global/identity_registry
```

It does not call SEDB-RAL or LIMEN to resolve display labels in v0.1.

Future identity-aware migration must be a separate layer with already-resolved identity evidence.

## 24. No alias escalation

Repeated unknown headings may become review candidates, but the migrator must never update:

```text
profiles/memory-markdown/*.json
```

A profile change requires a separate explicit design/review/commit cycle.

## 25. No canonical commit path

The public class/API for v0.1 must not contain methods named or behaving as:

```text
commit
write_memory
apply_migration
update_store
promote_profile
```

The result contains proposals only.

## 26. CLI direction

A future CLI may look like:

```bash
mneme dry-run-memory \
  --source /private/Residence/MEMORY.md \
  --profile profiles/memory-markdown/evemiss-residence-0.1.json \
  --budget 20000 \
  --budget 64000 \
  --output /private/reports/mneme-dry-run
```

The CLI must refuse to overwrite the input source path.

No `--commit` flag exists in this milestone.

## 27. Synthetic acceptance fixture

The public repository uses a synthetic Residence-style Markdown fixture containing:

- known headings;
- one repeated unknown heading;
- one unknown empty heading;
- unsupported code fence;
- a `Named Identities` entry;
- Chinese UTF-8 content;
- enough records to exercise bounded projection differences.

No real private Residence source is committed.

## 28. Acceptance criteria

### D0 — Source immutability

Source SHA-256 before and after the run is identical.

### D1 — Zero canonical mutation

The dry-run API exposes no canonical commit path; when an optional read-only store snapshot is supplied, `HEAD` remains unchanged.

### D2 — Profile-bound mapping

Every mapped record is produced by the selected MNEME-MD profile and binds its exact profile digest.

### D3 — Explicit loss preservation

Unknown headings, unknown-section content, unsupported blocks, and block-kind mismatches remain explicit in the dry-run evidence.

### D4 — Heading inventory

All headings are counted; unmatched headings appear in the inventory, including headings with no body content.

### D5 — Identity non-escalation

Identity-like Markdown remains fact data; the dry run mints no resident identity.

### D6 — Candidate-only profile discovery

Repeated unmatched headings can produce review candidates, but no target section or alias update is applied automatically.

### D7 — Route provenance

Every route hint in the report is traceable to a matched profile section; no route is inferred from prose.

### D8 — Bounded preview isolation

Different projection budgets may change previews, but they bind the same proposal set and do not mutate proposals.

### D9 — Deterministic rerun

Two identical dry runs produce identical deterministic report fingerprints.

### D10 — Privacy-mode separation

Sanitized output excludes private text/path fields while preserving structural evidence.

### D11 — Negative evidence

Every D0-D10 positive family has at least one injected failure/control that turns the relevant acceptance result red or blocked.

## 29. Initial implementation boundary

The first implementation milestone contains only:

1. dry-run request/result types;
2. deterministic report compiler;
3. heading/loss/route aggregation;
4. profile-promotion candidate evidence;
5. bounded projection previews;
6. deterministic risk classifier;
7. private vs sanitized report rendering;
8. evidence-bundle checksums/fingerprint;
9. synthetic acceptance fixture and D0-D11 gate;
10. CLI read-only dry-run command if the core is stable enough.

Deferred:

- real Residence canonical migration;
- automatic profile updates;
- LLM classification of unknown content;
- LIMEN identity resolution;
- SEDB-RAL identity binding;
- dynamic database writes;
- SOACR writeback;
- background migration service.

## 30. Design closure

The Private Residence Dry-Run Migrator establishes the evidence boundary between **compatibility analysis** and **real migration**.

> A private Residence memory file may be inspected, fingerprinted, mapped, loss-accounted, routed, and previewed before migration — but none of those observations becomes canonical memory or profile authority merely because the dry run succeeded.

The milestone is successful when MNEME can safely answer:

```text
What would migrate?
What would not migrate?
Why?
Under which explicit profile rule?
How large would each bounded preview be?
Which repeated unknown conventions deserve human review?
```

without changing the source or canonical memory.