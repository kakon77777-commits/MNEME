# MNEME v0.1 — Markdown → Canonical Memory → Bounded Markdown Experiment

**Date:** 2026-08-27  
**Status:** PASS  
**Profile:** `MLF-RM/0.1`

## Purpose

This experiment checks the concrete failure mode that motivated MNEME: a Markdown memory source can exceed a host bootstrap/context budget, while canonical memory must remain complete and independently addressable.

The experiment asks whether MNEME can preserve the entire imported memory state while materializing a smaller `MEMORY.md` projection from the same canonical head.

## Inputs

Two inputs were used.

1. **Private real-world Traditional-Chinese Markdown structure sample** — 9,715 bytes. The source itself is intentionally not committed to this public repository.
2. **Synthetic oversize `MEMORY.md`-like stress sample** — 57,066 bytes, containing 320 bounded instruction items under a recognized `Standing Instructions` section.

The private sample is used only to test non-destructive parsing and explicit loss accounting. The synthetic sample exercises the observed 24.4 KB-class host boundary without publishing private Residence content.

## Real-world structure result

```text
source bytes      9,715
mapped records    0
uncertain blocks  53
unmapped blocks   10
source mutated    no
```

The `0 mapped` result is intentional evidence of a conservative v0.1 importer, not evidence that the source is empty. The current importer recognizes only a bounded Markdown dialect and refuses to infer identity, authority, dates, relations, or memory role from arbitrary prose or unrecognized section names.

This result exposes the next migration problem: a future Memory Markdown compatibility profile needs explicit, versioned section aliases and mapping rules rather than broader semantic guessing.

## Oversize stress result

```text
source bytes                 57,066
imported records             320
canonical committed records  320
canonical head               ea843b2948015255a5d98e99d6c5a10ca294855540d5cd238309f5f7eef0ed1d
```

All 320 imported records were committed before projection.

## Projection comparison

| Projection | Hard budget | Actual bytes | Included records | Omitted records | Canonical head |
|---|---:|---:|---:|---:|---|
| bounded `MEMORY.md` | 20,000 | 19,853 | 91 | 229 | same |
| large comparison view | 200,000 | 70,000 | 320 | 0 | same |

Both views bind to the same canonical head. The bounded view changes only materialization; it does not delete the other 229 records.

The experiment therefore demonstrates the intended separation:

$$
|M_t| \not\le B_t
$$

while a materialized view obeys:

$$
|P(M_t)| \le B_t
$$

## Verified properties

- Oversize Markdown can be compiled into bounded typed records.
- The source Markdown remains byte-identical after import.
- Canonical state keeps all 320 records even when the projected view contains only 91.
- Two projections with different budgets bind to the same canonical head.
- Projection uses whole record blocks; it does not byte-slice UTF-8 or return partial memory records.
- The test exercises a source substantially larger than the 24,986-byte reference boundary.

## Non-claims and exposed gaps

This experiment does **not** claim arbitrary Markdown semantic migration. In particular, v0.1 does not yet prove:

- recognition of the existing Residence `MEMORY.md` dialect;
- Traditional-Chinese section aliases;
- nested sub-index semantics;
- migration of identity registries or relationship sections;
- exact re-import equivalence of a generated Markdown projection;
- production Residence activation.

Those are compatibility-profile and migration-policy problems, not reasons to return Markdown to canonical-source status.

## Conclusion

The first practical round-trip supports the core MNEME architecture:

> `MEMORY.md` can remain a useful bounded interface while persistent memory lives in a larger canonical record state.

The next design step should define an explicit Memory Markdown compatibility profile for existing Residence memory files without weakening fail-closed import semantics.
