# MNEME

**File-first, record-oriented canonical memory infrastructure for Residence-aware AI systems.**

> MEMORY.md != MEMORY
>
> Markdown is a projection. Canonical memory is a validated state of typed records, routes, provenance, and commits.

MNEME separates persistent AI memory from bounded model context and human-readable Markdown. Its first profile, **MLF-RM (Matrix Ledger Format — Residence Memory Profile)**, adapts the structural-first ideas of EveMissLab's 3M work to AI memory: preserve canonical structure first, then materialize human, model, graph, and runtime views as projections.

## Why MNEME

A monolithic Markdown memory file can simultaneously become:

- a canonical store;
- an index;
- a host bootstrap input;
- an LLM write target; and
- a human-readable document.

Those roles have different safety requirements. A host may load only a bounded prefix, an LLM generation may terminate before a rewrite is complete, and a syntactically valid Markdown document can still be semantically truncated. MNEME therefore moves canonical memory to bounded, independently validatable records and treats Markdown as a rebuildable projection.

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

## MLF-RM v0.1 direction

The initial file-first package is expected to contain typed memory records, relation/dependency graphs, routes, provenance events, projection metadata, checksums, and transaction receipts. A human-facing `MEMORY.md` may still be generated, but it is an output of the memory state rather than the memory state itself.

The design intentionally keeps the storage contract backend-neutral so a future dynamic database can implement the same record/route/transaction semantics without redefining MNEME.

## Safety model

A memory write is accepted only as a complete transaction. Incomplete or truncated model output must fail closed and produce no canonical commit. Projections are budgeted outputs and may be regenerated at different sizes without deleting canonical records.

## Status

**v0.1 architecture/design baseline.** No production Residence migration, real private-memory activation, autonomous background service, or production write authority is claimed.

Start with:

- [`docs/superpowers/specs/2026-08-27-mneme-v0.1-design.md`](docs/superpowers/specs/2026-08-27-mneme-v0.1-design.md)

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
- Current phase: architecture baseline
