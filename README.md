# MNEME

**File-first, record-oriented canonical memory infrastructure for Residence-aware AI systems.**

> MEMORY.md != MEMORY
>
> Markdown is a projection. Canonical memory is a validated state of typed records, routes, provenance, and commits.

MNEME separates persistent AI memory from bounded model context and human-readable Markdown. Its canonical memory profile is **MLF-RM/0.1**. The next compatibility layer, **MNEME-MD/0.1**, migrates explicitly declared `MEMORY.md` conventions without allowing Markdown layout or model guesses to become canonical truth.

## System position

```text
SEDB-RAL
  residency / identity evidence
        |
        v
LIMEN
  identity resolution / authorization
        |
        v
AI Residence
  private custody boundary
        |
        v
MNEME
  canonical memory records / routes / provenance / transactions
        |
        v
SOACR
  MemoryNeed / reconstruction / continuation
        |
        v
Working Context
```

## Core invariants

```text
IDENTITY != MEMORY
MEMORY != CONTEXT
MEMORY != MARKDOWN
CANONICAL STATE != PROJECTION
READ AUTHORITY != WRITE AUTHORITY
PROPOSAL != COMMIT
PARTIAL OUTPUT != VALID TRANSACTION
MODEL CONTEXT BUDGET != MEMORY CAPACITY
COMPATIBILITY PROFILE != CANONICAL MEMORY FORMAT
```

## Fresh Memory Core — MLF-RM/0.1

The Fresh Memory Core provides deterministic canonical UTF-8 JSON, typed `MemoryRecord` validation, complete transaction envelopes, an immutable exact-head file-first store, scoped routes, hard-budget whole-record projections, a conservative legacy Markdown importer, and a read-only SOACR-facing adapter.

Its A0-A6 gate includes corrupted/truncation/stale-head/scope-leak controls. It is synthetic/local evidence and grants no production Residence write authority.

## Memory Markdown Compatibility — MNEME-MD/0.1

MNEME-MD adds a versioned compatibility profile above MLF-RM. A Markdown heading has mapping meaning only when the selected profile declares an exact alias.

```text
existing MEMORY.md
→ exact profile match
→ typed MemoryRecord proposals
→ section-membership relation + mapping receipt
→ explicit loss report
→ MNEME transaction/store
→ profile-aware bounded MEMORY.md projection
```

### No semantic guessing

Heading matching uses NFC normalization, whitespace collapse, and Unicode casefold only. Punctuation is preserved. There is no fuzzy matching, embedding classification, synonym guessing, or LLM classification.

Unknown sections and unsupported blocks remain explicit loss rather than being silently converted.

### Built-in EveMiss Residence profiles

`evemiss-residence/0.1` remains frozen as the original compatibility baseline. `evemiss-residence/0.2` is an additive real-dialect profile derived from a private read-only dry run; no private source text or digest is stored in this repository. The v0.1 baseline contains:

| Section | Record | Scope |
|---|---|---|
| `Standing instructions` | `instruction` | `global/core` |
| `Verification lessons` | `lesson` | `global/verification` |
| `Who / how we work` | `instruction` | `global/collaboration` |
| `Named Identities` | `fact` | `global/identity_registry` |
| `This machine` | `fact` | `global/machine` |

`Named Identities` intentionally remains a fact registry. A display label in Markdown never mints or resolves a resident identity.

The v0.2 profile adds only observed dialect structure: `Memory Index` as a `global/core` paragraph instruction and the exact alias `Named Identities (Tier 1 Residences)`. The mixed introductory paragraph under the identity registry remains intentionally unmapped because it combines registry description with a hard rule; v0.2 does not guess a single record type for it.

The profile format supports arbitrary Unicode aliases, including Traditional Chinese, but a particular real-world alias is built in only when there is evidence that it is actually used with that meaning.

### Round-trip compatibility

Profile-aware projection renders a standardized bounded `MEMORY.md` view. Re-import compatibility compares ordered tuples:

```text
(section_id, record_type, scope.kind, scope.subject, content.text)
```

This proves compatibility semantics without pretending source-dependent canonical record IDs must be byte-identical after projection/re-import.


## Cognitive Persistence Semantics — MNEME-CPS/0.1

MNEME-CPS is an additive, observation-only semantic layer above canonical memory and Markdown compatibility. It asks how a cognition-related memory candidate might need to persist without rewriting `MemoryRecord`, mutating `MemoryStore`, or claiming that reconstructibility has already been proven.

```text
MLF-RM/0.1   -> canonical memory
MNEME-MD/0.1 -> Markdown compatibility
MNEME-CPS/0.1 -> persistence assessment / factorization / cognitive-seed proposals
```

CPS/0.1 defines six non-authoritative candidate dispositions:

```text
PRESERVE
STRUCTURALIZE
GENERATIZE
RECOMPUTE
DISCARD
UNKNOWN
```

The destructive boundary is explicit:

```text
ASSESSMENT != AUTHORITY
RECONSTRUCTIBLE != DISPENSABLE
FACTORIZE != DELETE
SEED != AUTHORITY
UNKNOWN -> PRESERVE / REVIEW BY DEFAULT
NO CPS/0.1 DELETION OR CANONICAL FACTORIZATION COMMIT
```

`PersistenceAssessment`, `FactorizationProposal`, and `CognitiveSeedProposal` are sidecar experiment artifacts. CPS/0.1 performs no reconstruction, no regenerative forgetting, no archive retirement, and no MLF-RM schema evolution.

## Private Residence Two-Pass Dry Run — 0.2

The Dry-Run/0.2 analyzer composes the existing compatibility and persistence layers without merging their semantics:

```text
MLF-RM/0.1      -> canonical memory
MNEME-MD/0.1    -> Markdown compatibility
MNEME-CPS/0.1   -> cognitive persistence semantics
Dry-Run/0.2     -> private two-pass migration/factorization evidence
```

PASS 1 maps only through MNEME-MD. PASS 2 receives only PASS 1 mapped records and exact structured metadata; persistence-policy selectors cannot inspect source prose, `content.text`, regexes, embeddings, similarity, or LLM output. Readiness is evidence only and never synthesizes factorization components. Actual factorization/seed proposals require explicit caller intents and existing CPS validation.

Dry-Run/0.2 accepts no writable `MemoryStore` and exposes no deletion, migration, reconstruction, tombstoning, archive movement, seed promotion, profile promotion, or regenerative-forgetting path. Public fixtures remain synthetic; sanitized evidence removes private path/text/source-digest/projection-body material.

## Explicit profile composition

MNEME keeps one writable canonical `MemoryStore`. Markdown profiles, CPS,
Dry-Run, Claude projection/import, and the SOACR adapter are explicit consumers
or sidecars; none becomes a second canonical store.

Built-in EveMiss profile selection is exact and caller-driven:

```python
from mneme import load_builtin_evemiss_profile_by_id

profile = load_builtin_evemiss_profile_by_id("evemiss-residence/0.2")
```

Only `evemiss-residence/0.1` and `evemiss-residence/0.2` are accepted. There is
no `auto` mode, content-based profile detection, fuzzy dialect selection, or
implicit v0.1-to-v0.2 upgrade. The v0.1 bytes and semantic digest remain frozen;
v0.2 is an explicit opt-in.

CPS and Dry-Run run only through their existing explicit APIs. Ordinary SOACR
recall and Claude global projection do not import or invoke either sidecar, and
public profile selection grants no private read, write, migration, identity, or
activation authority.

## Verification

Python 3.11+:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts/validate_fresh_memory_core.py --output fresh-memory-core.json
python scripts/validate_memory_markdown_profile.py --output memory-markdown-profile.json
python scripts/validate_memory_markdown_profile_v02.py --output memory-markdown-profile-v02.json
python scripts/validate_cognitive_persistence_semantics.py --output cps.json
python scripts/validate_private_residence_two_pass_dry_run.py --output private-residence-dry-run.json
python scripts/validate_claude_global_memory.py --root new-synthetic-root --output claude-global.json
python -m compileall -q src
```

A successful MNEME-MD gate reports `profile: MNEME-MD/0.1`, M0-M8 all `PASS`, an exact built-in profile digest, a canonical head for the synthetic round-trip, and negative-control evidence.

## Safety boundary

The public repository uses synthetic Markdown only. Real private Residence `MEMORY.md` files, local private paths, resident lists, and private source digests are not committed.

Current work does not implement live LIMEN authorization, real Residence migration, a dynamic database backend, vector routing, federation, or autonomous background writeback.

## Design and plans

- `docs/superpowers/specs/2026-08-27-mneme-v0.1-design.md`
- `docs/superpowers/plans/2026-08-27-fresh-memory-core.md`
- `docs/superpowers/specs/2026-08-27-memory-markdown-compatibility-profile-design.md`
- `docs/superpowers/plans/2026-08-27-memory-markdown-compatibility-profile.md`
- `docs/papers/2026-08-27-cognitive-reconstruction-theory-v0.1.md`
- `docs/superpowers/specs/2026-08-28-cognitive-persistence-semantics-design.md`
- `docs/superpowers/plans/2026-08-28-cognitive-persistence-semantics.md`
- `docs/superpowers/specs/2026-08-28-private-residence-two-pass-dry-run-design.md`
- `docs/superpowers/plans/2026-08-28-private-residence-two-pass-dry-run.md`
- `docs/superpowers/specs/2026-08-29-mneme-unified-profile-integration-v0.5-design.md`
- `docs/superpowers/plans/2026-08-29-mneme-unified-profile-integration-v0.5.md`
- `docs/runtime/MNEME_UNIFIED_PROFILE_INTEGRATION_V0.5.md`

## Repository identity

- Repository: `kakon77777-commits/MNEME`
- Package: `mneme-memory`
- Candidate package version: `0.5.0a1`
- Canonical memory profile: `MLF-RM/0.1`
- Markdown compatibility profiles: `MNEME-MD/0.1` + EveMiss `evemiss-residence/0.2`
- Cognitive persistence semantics: `MNEME-CPS/0.1`
- Private Residence dry-run: `MNEME-PRIVATE-RESIDENCE-DRY-RUN/0.2`
