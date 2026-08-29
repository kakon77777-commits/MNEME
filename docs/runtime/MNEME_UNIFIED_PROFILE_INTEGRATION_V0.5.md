# MNEME Unified Profile Integration v0.5

## Candidate status

This runbook describes the public, synthetic-only `mneme-memory==0.5.0a1`
candidate. It does not authorize real activation, private-memory access,
migration, release, deployment, or publication.

```text
real_private_residence = NOT_READ
real_memory_markdown = NOT_READ
real_claude_user_memory = NOT_TOUCHED
claude_memory_readback = NOT_RUN
production_activation = NOT_AUTHORIZED
```

## One canonical owner, explicit consumers

MLF-RM/0.1 remains the single writable canonical `MemoryStore`. The other
surfaces have separate, non-promoting responsibilities:

| Surface | Responsibility | Not authority for |
|---|---|---|
| MNEME-MD/0.1 | Explicit Markdown compatibility proposals | Canonical commit or identity |
| EveMiss profile 0.2 | Explicit opt-in dialect mapping | Automatic detection or migration |
| MNEME-CPS/0.1 | Persistence assessment and proposals | Deletion, forgetting, or reconstruction proof |
| Dry-Run/0.2 | Two-pass read-only evidence | Private read or writeback |
| Claude Global Transition/0.1 | Bounded generated global projection | A second store or provider continuity |
| SOACR adapter | Authorized read/materialization seam | Identity, scope admission, or write authority |

The built-in EveMiss profile IDs are selected exactly by the caller. There is
no content-based `auto` mode and no implicit upgrade from
`evemiss-residence/0.1` to `evemiss-residence/0.2`. CPS and Dry-Run are explicit
sidecar calls and do not run during ordinary SOACR recall or Claude projection.

## Installed candidate verification

Install the development dependencies, build one wheel, and install that exact
wheel without resolving a second dependency graph:

```text
python -m pip install -e ".[dev]"
python -m pip wheel . --no-deps --no-build-isolation --wheel-dir <wheelhouse>
python -m pip install --no-deps --force-reinstall <wheel>
mneme-claude-global verify
```

The wheel must report package name `mneme-memory`, version `0.5.0a1`, one
installed schema resource set containing exactly 21 `*.schema.json` files, and
the committed unified schema digest manifest. A local wheel hash identifies
that build only; it is not a cross-toolchain reproducibility claim.

## Six acceptance surfaces

Run each acceptance surface separately so one success cannot hide another
surface's failure:

```text
python -B scripts/validate_fresh_memory_core.py --output <fresh-output>
python -B scripts/validate_memory_markdown_profile.py --output <md-v01-output>
python -B scripts/validate_memory_markdown_profile_v02.py --output <profile-v02-output>
python -B scripts/validate_cognitive_persistence_semantics.py --output <cps-output>
python -B scripts/validate_private_residence_two_pass_dry_run.py --output <dry-run-output>
python -B scripts/validate_claude_global_memory.py --root <new-synthetic-root> --output <claude-output>
```

All inputs are repository fixtures or a new disposable synthetic root. The
positive Claude acceptance population observes zero private, production,
network, provider, MCP, Bridge, and external-command effects.

## Later gates not satisfied here

The candidate does not resolve resident identity or grant private access. A
future real operation requires fresh RAL/LIMEN identity and authority evidence,
an explicit private capability where applicable, exact current-state pins,
manual approval, effect receipts, and post-operation readback. Synthetic
acceptance, a task label, a transport receipt, or a provider session never
substitutes for those gates.

No real host path, resident identifier, private digest, memory body, credential,
or provider token belongs in this public runbook or its evidence.
