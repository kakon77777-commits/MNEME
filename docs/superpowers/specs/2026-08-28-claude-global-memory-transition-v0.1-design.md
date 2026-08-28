# MNEME Claude Global Memory Transition v0.1 Design

> **Status:** Neo.K approved the architectural direction; implementation has
> not started
>
> **Date:** 2026-08-28
>
> **Canonical base:** `84b9b0ee94115902d7a9e6acfdc48372e60fd673`
>
> **Scope:** Provider-neutral global memory with Claude Code as the first
> bounded-projection consumer

## 1. Goal

Provide Claude Code with a bounded global-memory projection that cannot be
silently truncated into canonical truth, while preserving MNEME as the sole
owner of this new global-memory slice.

The transition solves one immediate problem:

```text
large or growing global instructions
-> host loads only a prefix
-> omitted rule is indistinguishable from absent rule
```

The replacement flow is:

```text
human-approved provider-neutral records
-> MNEME MLF-RM/0.1 canonical transaction
-> route://global/tier0
-> 16,000-byte whole-record projection
-> Claude Code user-memory import
```

The global Claude file remains a consumer entrypoint. It is not the canonical
memory store and never becomes a model-controlled write surface.

## 2. Ownership and exclusions

### 2.1 Canonical ownership

- **MNEME** owns canonical global memory records, transaction history, route
  resolution and projection manifests for this slice.
- **Claude Code** consumes one generated Markdown projection through its user
  memory import mechanism.
- **SEDB-RAL/LIMEN** retain identity, resident, representation and authority
  ownership. MNEME does not infer or mint identity.
- **AI Residence** remains the private custody boundary. This profile does not
  open or migrate a private Residence.
- **SOACR** remains the future MemoryNeed/reconstruction orchestrator. It is not
  required for the first Claude bootstrap projection.

### 2.2 No second domain truth

MNEME records may retain digest-bound references to external domain facts, but
must not copy an external owner's mutable canonical bytes and then claim the
copy is independently current.

```text
domain fact ref + source digest + currentness obligation
!= duplicated writable domain store
```

### 2.3 Explicit exclusions

This profile does not implement:

- identity-specific `identity/{id}` routes;
- private memory reads or writes;
- Claude-to-MNEME automatic writeback;
- MCP, network, provider or Bridge calls;
- live LIMEN authorization;
- Codex global-memory activation;
- CPS factorization, reconstruction, deletion or regenerative forgetting;
- background refresh services;
- push, merge, release, deployment or publication authority.

## 3. Why a managed import

Claude Code supports a user memory file at `~/.claude/CLAUDE.md` and supports
absolute-path imports using `@path`. The transition uses that native import
surface instead of overwriting the whole user memory file.

The two alternatives are rejected:

1. **Direct replacement of `CLAUDE.md`** would mix hand-authored provider
   instructions with generated canonical-memory projection bytes.
2. **A live MCP query service** would introduce provider execution, service
   lifecycle, identity and authority before the bounded file-first path is
   proven.

The managed-import design preserves the existing user file byte-for-byte
outside one closed block and permits the generated projection to be replaced
independently.

## 4. Runtime placement

No machine-specific absolute path is committed to Git. A local activation
plan supplies three explicit absolute paths:

```text
runtime_root
canonical_store_root = {runtime_root}/shared-global/memory.mlfdir
claude_projection    = {runtime_root}/claude/MNEME_GLOBAL.md
claude_user_memory   = %USERPROFILE%/.claude/CLAUDE.md
```

For Neo.K's current Windows host, the intended runtime root is outside the Git
checkout under the local MNEME project umbrella. That exact path belongs in
local activation evidence, not this public specification.

Runtime paths must be caller-supplied and prevalidated. The implementation may
not search the D drive, scan home directories, fall back to `%TEMP%`, or infer a
private Residence path.

## 5. Provider-neutral global record profile

The first live slice accepts only active records in these exact scopes:

```text
global/core
global/collaboration
global/verification
global/machine
```

Records may use the existing MLF-RM/0.1 record types:

```text
instruction
fact
lesson
```

The profile refuses:

- `identity/*`, `project/*`, `task/*`, `method/*` and relation-only private
  scopes;
- resident IDs, task IDs or display labels presented as identity evidence;
- provider credentials, tokens, private paths or conversation bodies;
- a record whose semantics apply only to Claude but are represented as a
  provider-neutral invariant.

Claude-specific invocation instructions, such as which local skill Claude
should call, remain hand-authored in `CLAUDE.md`. Provider-neutral invariants,
such as relay/authority separation or verification rules, may be MNEME global
records.

## 6. Claude projection contract

### 6.1 Request

`mneme.claude-global-projection-request/0.1` is a closed object:

```text
request_id
expected_source_head
route_id = route://global/tier0
allowed_scope_paths[1..4]
required_record_ids[]
byte_budget = 16000
target_kind = claude_code_user_memory_import
projection_ref
not_claimed
request_digest
```

`allowed_scope_paths` must be a nonempty subset of the four scopes in section
5. It never contains an identity scope. `required_record_ids` is explicit and
unique.

### 6.2 Result and manifest

`mneme.claude-global-projection/0.1` returns:

```text
projection_ref
source_head
route_id
byte_budget
content_bytes
content_sha256
included_record_ids
omitted[{record_id, reason}]
required_record_ids
generator_version
projection_digest
```

The persisted manifest uses the same fields except that content is represented
by exact bytes, byte count and digest rather than duplicated inline text.

### 6.3 Budget rules

- The hard maximum is exactly 16,000 UTF-8 bytes.
- Records are included whole; no record body is byte-sliced.
- A required record omitted for any reason makes the projection ineligible for
  publication.
- Header and provenance metadata count against the budget.
- Omitted optional records remain canonical and are listed with reasons.
- A smaller request budget is allowed; a larger one is schema-invalid.

Projection success proves only bounded materialization from one MNEME head. It
does not prove Claude loaded, understood or followed the projection.

## 7. Managed Claude import block

The only automated change to the Claude user memory file is this closed block:

```text
<!-- BEGIN MNEME GLOBAL PROJECTION v0.1 -->
@{absolute-claude-projection-path}
<!-- END MNEME GLOBAL PROJECTION v0.1 -->
```

Rules:

- exactly zero or one block may exist;
- the import line is not inside a Markdown code fence;
- the path is absolute, local, points to the verified projection and contains
  no newline or control character;
- content before and after the block is preserved byte-for-byte;
- duplicate, nested, malformed or partially present markers refuse mutation;
- first insertion and every replacement bind the exact pre-image digest;
- replacement is atomic and followed by byte-for-byte readback;
- a create-new local evidence receipt records before/after digests, projection
  digest and operation outcome;
- the receipt does not copy the user's full `CLAUDE.md` content.

An existing generated projection remains unchanged when the user memory file
gate refuses. The tool never tries to repair ambiguous Markdown by guessing.

## 8. Core hardening required before adoption

The Claude profile may not be activated on the existing v0.1 store behavior
until these three measured gaps are closed.

### 8.1 Installed schema resources

The current wheel omits the JSON Schemas and installed imports fail. All MNEME
schemas must have one canonical package-resource location and load through
`importlib.resources` in source, editable and installed-wheel modes.

No vendored second schema body is allowed. Source and installed resource
bytes/digests must match.

### 8.2 Single-writer store lock

`MemoryStore.commit()` must hold one cross-process writer lock across:

```text
current HEAD read
-> transaction validation
-> immutable transaction publication
-> receipt publication
-> final HEAD compare-and-swap/write
-> post-write readback
```

Concurrent writers against one expected head must produce exactly one
successful commit. The loser returns a typed conflict and cannot report a
different successful head. Orphan evidence remains noncanonical and is
reported; it is never silently promoted.

The first implementation uses a local OS file lock with Windows and POSIX
adapters. It does not add a database or network lock service.

### 8.3 Global record-ID uniqueness

Before publication, the store rebuilds the current reachable record-ID index.
Any proposed `record_id` already present in canonical history is rejected,
whether the proposed content is equal or different. Updates use a new record
ID plus an explicit supersession/correction relation in a later profile.

Duplicate IDs inside one transaction are also rejected before publication.

## 9. Write authority and proposal boundary

MLF-RM/0.1 currently validates that `authority_ref` is nonempty; it does not
prove the authority. Therefore the first real global transaction is gated by a
separate local activation artifact:

```text
mneme.local-manual-write-authorization/0.1
principal_ref
transaction_ref + transaction_digest
expected_source_head
allowed_scope_paths
status
source_user_item_ref + source_user_item_digest
authorization_digest
```

The implementation validates this artifact only in the local activation path.
Synthetic core tests use synthetic authority. A model response, relay, remembered
approval or Claude edit is never principal authority.

Claude-originated suggestions may be saved as noncanonical proposal evidence
only under a future separately approved flow. They are not part of this first
slice.

## 10. Publication state machine

The first activation follows this sequence:

```text
verified MNEME source/install
-> explicit runtime paths verified
-> human-reviewed global transaction prepared
-> exact transaction digest approved
-> single-writer canonical commit
-> route resolution against exact new head
-> bounded projection generated
-> projection and manifest staged
-> target pre-image/digest revalidated
-> projection atomically published and read back
-> CLAUDE.md pre-image/digest revalidated
-> managed import block atomically inserted and read back
-> local activation receipt
-> Claude /memory readback (separate manual observation)
```

Code-candidate testing stops before the real transaction, runtime directory or
Claude user-memory mutation. Those are a separate local activation gate after
the implementation candidate is accepted.

## 11. Fail-closed behavior

| Condition | Required result |
|---|---|
| Store missing/corrupt/unreachable head | no projection publication |
| Writer lock busy | typed refusal; no retry loop |
| Stale expected head | no transaction publication |
| Duplicate record ID | no transaction publication |
| Invalid/unverified write authority | no transaction publication |
| Route includes non-global scope | projection refused |
| Required record omitted | projection refused |
| Projection exceeds 16,000 bytes | projection refused |
| Projection manifest/content mismatch | no target replacement |
| Projection target changed since plan | stale-target refusal |
| Claude file changed since plan | stale-target refusal |
| Managed block malformed/duplicated | no Claude file mutation |
| Atomic replace/readback mismatch | failure receipt; do not claim activation |
| Claude `/memory` unavailable | activation state remains `readback_unmeasured` |

No failure triggers automatic deletion, rollback of canonical history, private
search, provider call or blind retry.

## 12. Components and interfaces

### 12.1 Package resources

```text
mneme.schemas.read_schema(name) -> bytes
mneme.schemas.schema_digest(name) -> str
```

### 12.2 Store hardening

```text
MemoryStore.commit(tx, *, writer_lock, write_authorization=None)
MemoryStore.validate_record_id_population(tx)
```

The local manual authorization is required only by the activation wrapper, not
by existing synthetic acceptance fixtures.

### 12.3 Claude read adapter

```text
ClaudeGlobalProjectionRequest
ClaudeGlobalProjectionResult
ClaudeGlobalMemoryAdapter.materialize(request) -> result
```

The adapter reads only committed records, resolves the closed global route and
calls the whole-record projection engine. It has no write method.

### 12.4 Local publisher

```text
ClaudeProjectionPublisher.plan(...)
ClaudeProjectionPublisher.publish(plan) -> publication_receipt
ClaudeManagedImport.plan(...)
ClaudeManagedImport.apply(plan) -> import_receipt
```

Planning is read-only. Apply methods require exact plan/pre-image equality and
explicit local activation authority.

## 13. Acceptance matrix

| ID | Population | Required result |
|---|---|---|
| CGM-001 | Same store/head/request | byte-identical projection and manifest |
| CGM-002 | Global core/collaboration records | included by declared route |
| CGM-003 | Identity/project/task record | excluded and reported |
| CGM-004 | Required record cannot fit | projection refused |
| CGM-005 | Optional record cannot fit | omitted whole; source retained |
| CGM-006 | 16,000-byte boundary | output at or below exact maximum |
| CGM-007 | 16,001-byte request | schema refusal |
| CGM-008 | Installed wheel import | all schemas load with exact source hashes |
| CGM-009 | Two concurrent writers at same head | exactly one success |
| CGM-010 | Duplicate ID in one transaction | no publication |
| CGM-011 | Existing canonical record ID reused | no publication |
| CGM-012 | Missing/manual authority mismatch | no real activation write |
| CGM-013 | Fresh empty managed block state | one block inserted |
| CGM-014 | Existing exact block and same projection | idempotent no-op |
| CGM-015 | Duplicate/partial/nested markers | no file mutation |
| CGM-016 | Bytes outside managed block | byte-identical preservation |
| CGM-017 | Claude pre-image changes after plan | stale-target refusal |
| CGM-018 | Projection pre-image changes after plan | stale-target refusal |
| CGM-019 | Injected crash before atomic replace | old target retained |
| CGM-020 | Injected crash after replace before receipt | readback/recovery required |
| CGM-021 | Projection tries private path or provider call | hard refusal; zero effect |
| CGM-022 | Claude suggestion presented as commit authority | refused |
| CGM-023 | Manual `/memory` confirms import | observed readback receipt |
| CGM-024 | `/memory` not run | `readback_unmeasured`, never promoted |

Each negative control has an executed positive counterpart proving the named
gate is live.

## 14. Evidence and privacy

The public code candidate records:

- exact source commit/tree and dirty state;
- schema bytes/digests from source and installed wheel;
- focused/full tests and injected controls;
- synthetic store/projection/import receipts;
- no-network/no-private/no-provider effect counters;
- deterministic repeated-run digests.

The local activation evidence records only refs, digests, byte counts, paths
needed for local recovery, and outcome states. It does not commit:

- the user's full Claude memory bytes;
- private Residence content;
- provider tokens or credentials;
- native session/task history;
- real resident bindings.

## 15. Codex boundary

Codex is not activated as a consumer in this profile. Codex long-running task
continuation may use compaction, task-local memory and durable handoffs, while
MNEME later becomes a provider-neutral source when a measured cross-task/global
need exists.

The absence of a current Codex consumer does not permit Claude-specific facts
to become provider-neutral canonical records.

## 16. Success definition

The code candidate succeeds when all CGM-001 through CGM-022 synthetic cases
pass, installed-wheel resources work, the concurrent-writer and duplicate-ID
counterexamples are closed, and no real/global file is touched.

Local activation succeeds only when:

```text
exact approved transaction committed once
-> provider-neutral global projection <= 16000 bytes
-> projection manifest and content read back exactly
-> existing Claude memory preserved outside one managed import block
-> Claude /memory observes the import, or status remains explicitly unmeasured
```

No status in this profile claims resident identity, private memory access,
provider continuity, autonomous write authority or cognitive reconstruction.
