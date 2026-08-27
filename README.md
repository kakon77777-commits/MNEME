# MNEME

**File-first, record-oriented canonical memory infrastructure for Residence-aware AI systems.**

> MEMORY.md != MEMORY
>
> Markdown is a projection. Canonical memory is a validated state of typed records, routes, provenance, and commits.

MNEME separates persistent AI memory from bounded model context and human-readable Markdown. Its first profile, **MLF-RM (Matrix Ledger Format — Residence Memory Profile)**, adapts the structural-first ideas of EveMissLab's 3M work to AI memory: preserve canonical structure first, then materialize human, model, graph, and runtime views as projections.

## Why MNEME

A monolithic Markdown memory file can simultaneously become a canonical store, index, host bootstrap input, LLM write target, and human-readable document. Those roles have different safety requirements. A host may load only a bounded prefix, an LLM generation may terminate before a rewrite is complete, and a syntactically valid Markdown document can still be semantically truncated.

MNEME therefore moves canonical memory to bounded, independently validatable records and treats Markdown as a rebuildable projection.

## System position

```text
SEDB-RAL
  canonical residency / identity evidence
        |
        v
LIMEN
  host observation / identity resolution / authorization
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
  MemoryNeed / provider routing / reconstruction / continuation
        |
        v
Working Context
```

MNEME does not replace SEDB-RAL, LIMEN, AI Residence, SOACR, SEDB, MLF, or MMLC. It defines the canonical memory layer and the contracts that let those systems interoperate without collapsing identity, authority, memory, and context into one object.

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
STORAGE BACKEND != MEMORY SEMANTICS
```

## Fresh Memory Core v0.1

The current implementation candidate provides:

- deterministic canonical UTF-8 JSON bytes and domain-separated hashes;
- typed `MemoryRecord` validation for MLF-RM/0.1;
- complete transaction envelopes with exact commit marker, count, digest, and expected-head checks;
- file-first immutable committed transactions plus exact causal `HEAD` and receipts;
- idempotent current-head replay and stale-head rejection;
- auditable global/identity/project route filtering with explicit omission reasons;
- whole-record hard-budget Markdown/model projections with exact content hashes;
- non-destructive Markdown import proposals with explicit uncertain/unmapped loss accounting;
- a read-only SOACR-facing materialization adapter;
- an A0-A6 synthetic acceptance gate with injected negative controls.

A human-facing `MEMORY.md` may still be generated, but it is an output of canonical memory rather than canonical memory itself.

## Verification

Python 3.11+:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts/validate_fresh_memory_core.py --output fresh-memory-core.json
```

The acceptance runner is local, deterministic, synthetic, and network-free. A valid result reports `profile: MLF-RM/0.1`, `status: PASS`, A0-A6 all `PASS`, a canonical head, and the injected control count.

This evidence is **not** production Residence activation and grants **no production Residence write authority**. Real Residence migration, live LIMEN authorization, dynamic-database backends, vector routing, federation, and full SOACR writeback remain outside v0.1 Fresh Memory Core.

## Design and plan

- [`docs/superpowers/specs/2026-08-27-mneme-v0.1-design.md`](docs/superpowers/specs/2026-08-27-mneme-v0.1-design.md)
- [`docs/superpowers/plans/2026-08-27-fresh-memory-core.md`](docs/superpowers/plans/2026-08-27-fresh-memory-core.md)

## Related repositories

- SEDB-RAL — residency and attestation ledger
- LIMEN — identity mediation and access boundary
- SOACR — self-orienting context-memory runtime
- MLF — Matrix Ledger Format
- MMLC — Multidirectional Matrix Ledger Computation Runtime

## Repository identity

- Repository: `kakon77777-commits/MNEME`
- Project name: **MNEME**
- Initial profile: **MLF-RM v0.1**
- Current phase: **Fresh Memory Core implementation candidate**
