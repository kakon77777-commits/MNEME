# MNEME Claude Global Memory Transition v0.1 — Final Review Design Delta 001

**Status:** approved implementation scope carried forward from the already
approved Claude global-memory design and inline execution. This delta records
the minimum architecture correction required by the final Lares review; it
does not authorize local activation, real Claude memory access, push, merge,
release or deployment.

## 1. Superseding evidence

This delta supplements, and where stated supersedes,
`2026-08-28-claude-global-memory-transition-v0.1-design.md`.

The reviewed candidate was:

- HEAD `2d0ba32295429c54a764917a3fe3cfe6db60e7a2`
- tree `7fa887ec1394830f297b54a51b9a7312054fb926`
- Lares review file
  `2026-08-29_claude-lares_to_01a037c2_mneme-claude-global-final-review.md`
- review SHA-256
  `A97958C1EDA00DF52EF6EA40BB08E764D50ED3AE038E6AD7BAF9A4BC3B3A25B9`
- verdict `REVISE`, blocking `2`, nonblocking `1`

Both blocking counterexamples were independently reproduced against the exact
reviewed HEAD:

1. a direct publisher accepted an active authorization unrelated to the
   projection transaction, and a direct importer accepted hand-written
   projection bytes without publication evidence;
2. a real loopback UDP send, real subprocess and real file write outside the
   acceptance root occurred while the acceptance report still returned
   `PASS` with all three relevant counters equal to zero.

## 2. Frozen boundaries

The following remain unchanged:

- canonical memory stays provider-neutral and global-only;
- Claude remains a read-only consumer;
- only synthetic paths and records may be exercised in this code candidate;
- real Claude user memory, private Residence and real global records remain
  unopened and unmodified;
- no provider, MCP, Bridge or external network operation is needed by the
  positive path;
- local activation remains a later, separately approved gate;
- no push, merge, release, deployment or publication is implied.

## 3. Primitive authority must be self-defending

The old interfaces are superseded:

```text
ClaudeProjectionPublisher.publish(plan, authorization)
ClaudeManagedImport.apply(plan, authorization)
```

They relied on the orchestrator to have checked the relationship between the
authorization and the committed transaction. Public primitives therefore lost
that guarantee when called directly.

The corrected runtime chain is:

```text
TransactionProposal
+ CommitReceipt read back from the exact MemoryStore
+ LocalManualWriteAuthorization
→ VerifiedClaudeWriteContext

PreparedClaudePublication
+ VerifiedClaudeWriteContext
→ ClaudeProjectionPublisher.publish(...)
→ VerifiedClaudePublication (runtime capability)
  └─ ClaudePublicationReceipt (durable digest evidence)

PreparedClaudeImport
+ VerifiedClaudeWriteContext
+ VerifiedClaudePublication
→ ClaudeManagedImport.apply(...)
→ ClaudeImportReceipt
```

### 3.1 VerifiedClaudeWriteContext

`VerifiedClaudeWriteContext` is a frozen runtime capability, not a fifth
portable contract family. It contains the exact store, transaction, commit
receipt and manual authorization and verifies all of the following every time a
primitive consumes it:

- transaction validates at the authorization's expected source head;
- transaction ref and digest equal the authorization pair;
- transaction `authority_ref` equals the authorization ID;
- every transaction scope is covered by the authorization;
- commit receipt transaction digest and previous/new heads match the
  transaction and deterministic head transition;
- the store's current head equals the commit receipt new head;
- the store's reachable committed transaction bytes equal the supplied
  transaction;
- the projection manifest source head equals the committed new head;
- included and required record IDs belong to that transaction.

Missing, stale, substituted or unrelated evidence fails before publisher or
importer mutation.

### 3.2 VerifiedClaudePublication

`ClaudeProjectionPublisher.publish()` returns a
`VerifiedClaudePublication`. It contains the durable publication receipt and an
issuer-bound runtime capability created only after target readback succeeds.
The importer accepts this capability, not a caller-created receipt.

Before import mutation, it must prove:

- it was issued by the publisher path;
- its receipt verifies;
- authorization, transaction and committed-head fields equal the current
  `VerifiedClaudeWriteContext`;
- projection ref/digest, target ref, content bytes and readback digest equal the
  exact import plan and current projection bytes.

A hand-written projection, a self-sealed receipt, a receipt from another
transaction or a valid publication capability for another projection is
refused before the user-memory target is opened for writing.

### 3.3 Durable receipt additions

The unreleased `0.1` receipt resources are tightened in place. Publication and
import receipts add exact transaction ref/digest and committed-head evidence.
Import receipts additionally pin the publication receipt ref/digest. This is a
candidate correction, not a new schema family or a second store.

## 4. Acceptance effect evidence must be observed

The old implementation inferred positive logical writes from receipt steps and
left forbidden counters at dataclass defaults. `injected_effect` then directly
changed the counter it was intended to test. Those defaults are not effect
evidence and are superseded.

### 4.1 Runtime observer

The acceptance runner installs one process-local, scoped observer only while
the two synthetic runs execute:

- CPython audit events observe file content opens, file mutations, socket
  operations and subprocess/external-CLI launches;
- a scoped call profiler observes entry into known provider, MCP and
  EveMissLab/Herdr Bridge module namespaces;
- the observer is inactive outside the acceptance context and serializes
  concurrent acceptance runs;
- report evidence contains normalized categories/counts and a digest, never a
  host absolute path, command body, memory body or credential;
- private markers are classified before the synthetic-root allowlist;
- any content read/write outside the exact synthetic root and closed read-only
  resource allowlist is classified as production;
- exact schema resources, the acceptance fixture and the closed AST-scan source
  set are allowed read-only; writes to them remain production writes.

The observer does not claim kernel-wide or cross-process tracing. It proves the
effects initiated by the exercised Python process through the monitored APIs.
A subprocess launch is itself a forbidden observed effect; the child does not
need to be trusted or inspected.

### 4.2 Honest counters and probes

Forbidden counters are populated exclusively from observed events. Test probes
must invoke the corresponding monitored API; they may not replace a dataclass
field. Independent adversarial tests also wrap the real `_execute_run` path and
perform a loopback UDP send, a local subprocess launch and a disposable file
write outside the acceptance root. Each must produce `FAIL` from observation.

The existing `synthetic_writes` value remains a receipt-verified logical-step
count, not an OS write-operation count. The report names its evidence mode so
the two meanings cannot be confused.

Provider, MCP and Bridge positives remain zero only when both the runtime
module-call observer and the existing static source boundary are clean. Generic
network and external-CLI observations remain separate and cannot be promoted
from those domain labels.

## 5. Build prerequisite correction

`pip wheel --no-deps --no-build-isolation` intentionally consumes the current
environment. Therefore the developer extra must install its required build
tools explicitly:

```text
pytest>=8.0
setuptools>=68
wheel
```

The candidate does not claim byte-identical wheels across unspecified build
tool versions. A wheel SHA is an exact observation of one named build; package
name/version, source tree and installed schema bytes are the portable checks.

## 6. Required controls

Release-blocking RED/GREEN controls are:

1. unrelated transaction authorization cannot publish;
2. stale/noncurrent commit context cannot publish or import;
3. raw authorization cannot enter either primitive;
4. hand-written projection without `VerifiedClaudePublication` cannot import;
5. self-sealed or cross-projection publication evidence cannot import;
6. exact context → publish capability → import succeeds and receipts retain all
   atomic ref/digest bindings;
7. real loopback socket, subprocess and outside-root file operations are
   observed and turn the report `FAIL`;
8. private/production read/write and provider/MCP/Bridge probes are observed by
   their actual monitor paths, not counter replacement;
9. the clean positive run remains deterministic and contains no absolute path
   or memory body;
10. a fresh developer environment obtains setuptools and wheel from the
    declared dev extra before the offline no-build-isolation wheel step.

All prior focused, full, installed-wheel, schema-byte, compile and clean-state
gates remain required.
