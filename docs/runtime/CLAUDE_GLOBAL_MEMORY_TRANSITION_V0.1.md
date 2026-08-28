# Claude Global Memory Transition v0.1

## Candidate status

This document describes the public, synthetic-only `mneme.claude-global/0.1`
code candidate. It does not authorize or perform local activation.

```text
real_claude_user_memory = NOT_TOUCHED
private_residence = NOT_READ
claude_memory_readback = NOT_RUN
production_wave_run = NOT_APPLICABLE
```

MNEME remains the canonical source for provider-neutral global records. Claude
Code is a read-only consumer of one generated Markdown projection. The Claude
user-memory entrypoint is not a second canonical store and model or relay output
is never write authority.

## Implemented synthetic flow

The installed command is:

```text
mneme-claude-global verify
mneme-claude-global plan --root <new-synthetic-root>
mneme-claude-global apply-synthetic --root <new-synthetic-root>
mneme-claude-global status --root <synthetic-root>
```

`apply-synthetic` derives every path beneath the one new disposable root. It
does not accept real runtime or Claude user-memory overrides. The operation
order is:

```text
validated transaction + request + manual authority
→ canonical commit
→ global-only whole-record projection (maximum 16000 UTF-8 bytes)
→ atomic projection publication
→ byte-preserving exact MNEME managed import
→ digest-bound synthetic activation receipt
```

The managed block is the only generated region. Existing bytes outside that
block, including BOM state, mixed line endings and unrelated managed blocks,
remain byte-identical.

## Fail-closed boundaries

- identity, project, task and private scopes are not admitted;
- private, reparse, junction, symlink, hardlink, alternate-stream, network and
  escaping paths refuse before target content access;
- two writers cannot both succeed against one pre-image;
- Windows atomic replacement contention produces one typed refusal and no
  automatic retry;
- stale store, projection or user-memory pre-images produce no success receipt;
- real-target overrides are readable policy refusals with exit code `2`;
- provider, network, MCP, Bridge and external-command effects are zero in the
  positive acceptance population.

## Acceptance ownership

The synthetic runner executes CGM-001 through CGM-022, CGM-025 and CGM-028
twice against one deterministic synthetic path. It compares the canonical store
head, projection SHA-256, manifest digest and publication/import/activation
receipt digests. Every forbidden injected effect turns the report red.

These cases remain intentionally unexecuted by the code candidate:

```text
CGM-023  manual Claude /memory observation
CGM-024  explicit unmeasured /memory state on the target host
CGM-026  empirical real 16000-byte import visibility
CGM-027  pre-activation session restart or explicit reload observation
```

Their status is `NOT_RUN_LOCAL_ACTIVATION_REQUIRED`, never inferred from a
synthetic result.

## Later local activation gate

Real use requires a **separate local activation plan** reviewed after the code
candidate is accepted. That plan must bind all of the following before any real
write:

1. exact approved local runtime and consumer paths, represented only in local
   evidence;
2. the first provider-neutral global transaction and its exact digest;
3. Neo.K's manual authorization bound to that transaction and source head;
4. canonical commit receipt and readback head;
5. projection target pre-image, result digest and readback;
6. Claude user-memory pre-image, byte-preservation proof and import receipt;
7. empirical maximum-size import result on the target host;
8. manual `/memory` visibility or an explicit unmeasured result;
9. restart or explicit reload evidence for sessions started before activation.

The later gate must not copy private memory bodies, credentials, native session
history or resident bindings into public evidence. Failure never authorizes a
blind retry, guessed repair, canonical-history rollback or provider call.
