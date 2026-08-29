# MNEME Claude Global Memory Transition v0.1 — Final Review Design Delta 002

**Status:** narrow superseding correction within the already approved inline
implementation. This delta changes only the publication-to-import sequencing
boundary. It does not authorize real Claude memory access, private Residence,
local activation, push, merge, release or deployment.

## 1. Superseded claim

Delta 001 introduced an issuer-bound `VerifiedClaudePublication` runtime
capability. Lares' re-review of exact HEAD
`4bf6efd2ede92d5496b94c192c009a3a59775d11` / tree
`c31f6e3ff5711c7fa659d3b8d6a6cecb11c1f92b` proved that this capability was
forgeable:

```text
import module-private issuer sentinel
→ object.__new__(VerifiedClaudePublication)
→ object.__setattr__(receipt, issuer)
→ wrap self-sealed attacker receipt
→ ClaudeManagedImport.apply(...)
→ user-memory mutation without publisher execution
```

The attack was independently reproduced against the exact reviewed HEAD. The
import receipt pinned an attacker-chosen publication receipt ID even though
`ClaudeProjectionPublisher.publish()` never ran.

The following Delta 001 design is therefore superseded:

```text
caller supplies VerifiedClaudePublication to ClaudeManagedImport.apply()
```

No replacement sentinel, `__all__`, private constructor or Python object
identity is treated as a security boundary.

## 2. Selected design: structural sequencing

The importer no longer accepts any caller-supplied publication capability or
publication receipt. Instead, the publication plan becomes part of the sealed
import plan, and the importer itself executes the exact publisher immediately
before import:

```text
VerifiedClaudeWriteContext
+ PreparedClaudePublication
+ user-memory preimage
→ ClaudeManagedImport.plan(...)
→ PreparedClaudeImport

ClaudeManagedImport.apply(prepared_import, verified_context)
  1. reverify committed context and both plans
  2. instantiate the exact ClaudeProjectionPublisher for the importer's runtime root
  3. call publisher.publish(prepared_publication, verified_context)
  4. retain returned ClaudePublicationReceipt as a local value
  5. lock and re-read the projection
  6. require current projection bytes == publication receipt == import plan
  7. mutate only the synthetic user-memory target
  8. return both durable receipts
```

There is no capability authenticity decision for a caller to satisfy or forge.
The only public `apply` path necessarily executes the real publisher method.

## 3. Corrected interfaces

The old interfaces are removed:

```text
ClaudeProjectionPublisher.publish(...) -> VerifiedClaudePublication
ClaudeManagedImport.plan(user_memory, projection_path, expected_digest)
ClaudeManagedImport.apply(plan, context, publication_capability)
```

The corrected interfaces are:

```text
ClaudeProjectionPublisher.publish(plan, context) -> ClaudePublicationReceipt

ClaudeManagedImport.plan(
    user_memory,
    prepared_publication,
    expected_user_memory_digest,
) -> PreparedClaudeImport

ClaudeManagedImport.apply(
    prepared_import,
    verified_context,
) -> ClaudePublishedImportResult
```

`ClaudePublishedImportResult` is a frozen result container with:

```text
publication_receipt: ClaudePublicationReceipt
import_receipt: ClaudeImportReceipt
```

It is evidence returned after both steps, never authority consumed before a
write.

## 4. Import-plan binding

The unreleased `ClaudeImportPlan 0.1` candidate resource is tightened in place
with:

```text
publication_plan_ref
publication_plan_digest
```

`PreparedClaudeImport` retains the exact `PreparedClaudePublication`, verifies
its immutable content, manifest, target and contract, and derives its
`projection` property from the publication target. The import plan can be made
before the projection exists; planning remains read-only.

At apply time:

- the publication plan must match the import plan ref/digest;
- the publisher validates the exact committed context and target preimage;
- a pre-existing hand-written projection is either validated by an idempotent
  publisher execution against its exact preimage or refused as stale;
- the returned receipt must match projection ref/digest, path, content bytes,
  readback digest, authorization, transaction and committed head;
- any projection change between publisher release and importer lock is refused
  by the existing reread checks.

The import receipt retains the publication receipt ref/digest and all existing
transaction/head bindings.

## 5. Threat boundary

This design guarantees sequencing through the supported public API. It does not
claim to sandbox arbitrary Python code capable of monkeypatching class methods,
calling underscore implementation helpers directly or replacing source code in
the running interpreter; that is arbitrary code execution, not a capability
validation problem.

The fix removes the exact public `apply` bypass demonstrated by the reviewer.
There is no importable issuer secret or caller-constructed authority token.

## 6. Required RED/GREEN controls

1. The exact `object.__new__` + imported sentinel attack is RED on the old HEAD.
2. The superseding module exports no `VerifiedClaudePublication` and no issuer
   sentinel.
3. `ClaudeManagedImport.apply` accepts only import plan + verified context;
   a third receipt/capability argument is rejected by the interface.
4. A hand-written projection created after a missing-target publication plan is
   refused as stale before user-memory mutation.
5. A pre-existing exact projection can succeed only when publisher planning
   bound that exact preimage and importer invokes publisher idempotently.
6. A spy around the real publisher proves exactly one publisher call per import
   apply.
7. Publication and import receipts retain exact ref/digest/head bindings.
8. Stale store, unrelated authorization, cross-transaction plan and changed
   projection populations remain refused.
9. Crash, path, mixed-EOL and concurrent-reader guarantees remain unchanged.
10. Full acceptance, runtime effect observer, clean wheel and installed schema
    gates remain green.

## 7. Retained limits

Real Claude user memory, private Residence, real global-memory adoption,
provider/MCP/Bridge access, network activity, local activation, push, merge,
release and deployment remain outside this fixwave and remain not run.
