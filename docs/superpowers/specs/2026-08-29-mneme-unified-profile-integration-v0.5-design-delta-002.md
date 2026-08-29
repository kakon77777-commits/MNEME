# MNEME Unified Profile Integration v0.5 — Design Delta 002

Date: 2026-08-29

## Status and scope

This append-only delta narrows how the six final acceptance reports are bound
and reproduced. It does not change canonical memory, profile selection,
authority, projection content, private access, or activation behavior.

It responds to the independent review bound to:

- reviewed HEAD `84d7de8aadd948a8d3a8dd8b1ad1711bfebd985d`;
- reviewed tree `e760a83a8a40ad72c61a4b1f115ede8490bc410a`;
- review SHA256 `7107783A48504D6C8B166926B1FD24BDA62436B91C9206B0FB5604E857B66BA4`.

## Deterministic surfaces

The following reports remain exact byte/SHA256 gates when regenerated at the
pinned candidate commit:

1. Fresh Memory Core;
2. MNEME-MD 0.1;
3. EveMiss profile 0.2;
4. MNEME-CPS 0.1;
5. Private Residence Dry-Run 0.2.

Their maintained gate runs each real validation script in a disposable clone of
the pinned commit and compares fresh bytes and SHA256 with the acceptance
evidence. A digest over stored claims alone is not sufficient.

## Claude root sensitivity

Claude publication, import, and activation receipts bind the selected synthetic
root. Consequently the complete Claude report changes across roots even when
its behavior, cases, effects, and materialized content are equivalent.

The runtime report must declare:

```text
report_byte_reproducibility = NOT_CLAIMED_SYNTHETIC_ROOT_SENSITIVE
root_sensitive_fields =
  - artifact_runs[].activation_receipt_digest
  - artifact_runs[].import_receipt_digest
  - artifact_runs[].projection_receipt_digest
  - run_fingerprints[]
  - report_digest
```

The maintained gate runs the Claude validation twice from the same pinned code
with two distinct synthetic roots. Whole-report hashes must differ. After
replacing exactly the declared fields with one fixed sentinel, the canonical
payloads and their domain-separated semantic SHA256 must match.

The acceptance evidence may retain a whole-report hash only as a named local-run
observation. It must not use that hash as a cross-root reproducibility gate.

## Evidence and failure behavior

- Each deterministic report mismatch fails the maintained test.
- Any undeclared Claude field difference fails the semantic comparison.
- Equal whole-report Claude hashes across distinct roots fail the root-sensitivity
  control because that would mean the test did not exercise the intended branch.
- The acceptance evidence records the semantic digest, the named-run hash, and
  the whole-report byte-reproducibility nonclaim separately.

## Non-authority

This delta authorizes no provider call, private read, real activation, migration,
canonical write, publication, release, or deployment.
