# MNEME Unified Profile Integration v0.5 — Design Delta 003

Date: 2026-08-29

## Status and supersession

This append-only delta supersedes only Design Delta 002's statement that the
Private Residence Dry-Run report is exact-byte reproducible across checkout
roots. The Claude root-sensitivity contract and all canonical-memory,
authority, privacy, and activation boundaries remain unchanged.

It responds to the independent review bound to:

- reviewed HEAD `84d7de8aadd948a8d3a8dd8b1ad1711bfebd985d`;
- reviewed tree `e760a83a8a40ad72c61a4b1f115ede8490bc410a`;
- review SHA256 `7107783A48504D6C8B166926B1FD24BDA62436B91C9206B0FB5604E857B66BA4`.

## Reproduced root cause

The Dry-Run analyzer's private evidence bundle intentionally records the source
path in its private report. `bundle_fingerprint` covers that bundle. Two clones
of the same commit at different checkout paths therefore produce different
bundle fingerprints and different whole-report SHA256 values, while status,
cases, controls, report fingerprint, source commit, and every other field remain
identical.

Two process runs within one checkout remain byte-identical. Two different
checkout roots are semantically equivalent after replacing only
`bundle_fingerprint` with one fixed sentinel.

## Revised deterministic set

The exact byte/SHA256 gates are:

1. Fresh Memory Core;
2. MNEME-MD 0.1;
3. EveMiss profile 0.2;
4. MNEME-CPS 0.1.

Private Residence Dry-Run final evidence declares:

```text
byte_reproducibility = NOT_CLAIMED_CHECKOUT_ROOT_SENSITIVE
root_sensitive_fields =
  - bundle_fingerprint
```

Its maintained gate runs the real script from two disposable clones of the
pinned candidate. Whole-report hashes must differ, normalized canonical
payloads must be equal, and their domain-separated semantic SHA256 must match
the final evidence.

## Six-surface maintained gate

One maintained test clones the exact `candidate.verified_head` recorded in the
acceptance evidence and executes all six real validation scripts. It performs:

- exact bytes and SHA256 for the four deterministic reports;
- dual-checkout semantic equivalence for Private Residence Dry-Run;
- dual-synthetic-root semantic equivalence for Claude Global Transition.

This test re-derives the claims. It does not treat the acceptance file's own
digest as proof that the enclosed report hashes are true.

## Non-authority

This delta authorizes no private read, provider call, real activation,
migration, canonical write, publication, release, or deployment.
