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

### Built-in EveMiss Residence profile

The initial built-in profile contains only section names already observed in prior memory-design evidence:

| Section | Record | Scope |
|---|---|---|
| `Standing instructions` | `instruction` | `global/core` |
| `Verification lessons` | `lesson` | `global/verification` |
| `Who / how we work` | `instruction` | `global/collaboration` |
| `Named Identities` | `fact` | `global/identity_registry` |
| `This machine` | `fact` | `global/machine` |

`Named Identities` intentionally remains a fact registry. A display label in Markdown never mints or resolves a resident identity.

The profile format supports arbitrary Unicode aliases, including Traditional Chinese, but a particular real-world alias is built in only when there is evidence that it is actually used with that meaning.

### Round-trip compatibility

Profile-aware projection renders a standardized bounded `MEMORY.md` view. Re-import compatibility compares ordered tuples:

```text
(section_id, record_type, scope.kind, scope.subject, content.text)
```

This proves compatibility semantics without pretending source-dependent canonical record IDs must be byte-identical after projection/re-import.

## Verification

Python 3.11+:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts/validate_fresh_memory_core.py --output fresh-memory-core.json
python scripts/validate_memory_markdown_profile.py --output memory-markdown-profile.json
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

## Repository identity

- Repository: `kakon77777-commits/MNEME`
- Package: `mneme-memory`
- Candidate package version: `0.2.0a1`
- Canonical memory profile: `MLF-RM/0.1`
- Markdown compatibility profile: `MNEME-MD/0.1`
