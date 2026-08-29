# MNEME Unified Profile Integration v0.5 — Design Delta 001

Date: 2026-08-29

## Status and scope

This append-only delta narrows the interpretation of runtime effect evidence in
the accepted unified integration design. It does not change canonical memory,
authority, routing, projection, private access, or activation behavior.

It responds to the independent final review bound to:

- reviewed HEAD `d3add0862e89059781685e627805b42f640e1b3b`;
- reviewed tree `7a9d3c7196cb3689bcb6ec76205335e3cfb9b25c`;
- review SHA256 `148BE8DE5EAE9206A43D400830C57DC3AE26BA5E66AF6B5CB0C2D4E1113D51BA`.

## Observed limitation

`ClaudeRuntimeEffectObserver` uses CPython audit events and profile hooks. Those
mechanisms observe the maintained Python API controls, including ordinary file,
socket, subprocess, provider, MCP, and Bridge entrypoints. They are not an
operating-system containment boundary. Native FFI can execute below CPython's
audited API surface without incrementing the observer counters.

## Frozen decision

The v0.5 candidate does not add a platform-specific sandbox. Its machine-readable
effect contract is instead narrowed to:

```text
effect_observation_scope = cpython_audited_api_surface
effect_observation_not_claimed =
  - native_ffi_containment
  - os_level_sandbox
```

A zero effect counter means zero events observed within that exact scope. It
must not be cited as proof that arbitrary native code, FFI, kernel calls, child
processes outside CPython instrumentation, or a hostile extension module were
contained.

## Required propagation

The scope and not-claimed values must appear in the Claude acceptance report,
the unified acceptance evidence, and the public runtime runbook. Report digests
cover these values. Removing or changing them without a reviewed successor
must fail maintained tests.

## Reproducible static gate

Ruff is a declared development dependency and the combined CI checks exactly
the Python files changed from the pinned remote-main input commit. This avoids
silently claiming an unverifiable out-of-band gate while also avoiding an
unrelated mass rewrite of legacy source outside this integration's diff.

## Non-authority

This delta authorizes no private read, native execution, provider call, real
activation, migration, publication, release, deployment, or canonical write.
