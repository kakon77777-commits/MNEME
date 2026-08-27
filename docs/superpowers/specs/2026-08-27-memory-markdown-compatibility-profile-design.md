# MNEME-MD/0.1 — Memory Markdown Compatibility Profile Design

**Status:** Canonical design candidate  
**Date:** 2026-08-27  
**Repository:** `kakon77777-commits/MNEME`  
**Base runtime:** MNEME Fresh Memory Core / MLF-RM/0.1  
**Compatibility profile:** `MNEME-MD/0.1`

## 1. Purpose

MNEME-MD defines a versioned, fail-closed compatibility layer for migrating existing `MEMORY.md`-style documents into MNEME without treating Markdown layout, remembered prose, model style, or heuristic interpretation as canonical truth.

The Fresh Memory Core already establishes:

```text
MEMORY.md != MEMORY
```

This profile solves the next problem:

> Existing AI memory ecosystems already contain useful Markdown conventions. How can those conventions be migrated into typed MNEME records without semantic guessing, silent loss, or identity confusion?

MNEME-MD answers with explicit profiles.

```text
Markdown syntax
!=
semantic mapping
```

A heading gains canonical mapping meaning only when an exact versioned profile declares that mapping.

## 2. Scope

MNEME-MD/0.1 provides:

- a JSON profile format for declaring exact Markdown section aliases;
- deterministic heading normalization and collision rejection;
- explicit block-kind-to-record-type mappings;
- explicit scope mappings;
- explicit section-membership relations for later projection;
- conservative import with line-level loss accounting;
- profile-aware bounded Markdown projection;
- compatibility comparison after re-import;
- one built-in EveMiss Residence profile based only on section names already observed in the existing memory design evidence.

MNEME-MD/0.1 does **not** provide:

- fuzzy heading matching;
- embedding-based section classification;
- LLM semantic classification;
- autonomous identity resolution;
- automatic parsing of names into resident IDs;
- arbitrary Markdown semantic reconstruction;
- tables/code-fence semantic extraction;
- migration of real private Residence data by default;
- write authority.

## 3. Relationship to MNEME

```text
Existing MEMORY.md
        |
        v
MNEME-MD profile loader
        |
        v
profile-aware importer
        |
        +--> typed MemoryRecord proposals
        +--> section membership relations
        +--> route hints
        +--> explicit loss report
        |
        v
MNEME TransactionProposal
        |
        v
MemoryStore
        |
        v
profile-aware bounded projection
        |
        v
MEMORY.md-compatible view
```

MNEME-MD does not alter the MLF-RM canonical record or transaction semantics. It is a compatibility/migration profile layered above them.

```text
COMPATIBILITY PROFILE != CANONICAL MEMORY FORMAT
```

## 4. Profile identity

Every profile document has an exact version and profile ID.

```json
{
  "profile_version": "mneme.memory-markdown-profile/0.1",
  "profile_id": "evemiss-residence/0.1",
  "title": "EveMiss Residence MEMORY.md Profile",
  "sections": []
}
```

The canonical profile digest is:

```text
sha256_domain(
  b"MNEME-MD-PROFILE-0.1",
  canonical_json_bytes(profile)
)
```

Every profiled import receipt and projection manifest binds the exact profile ID and digest.

Changing aliases, block rules, scopes, or render headings therefore changes the profile digest.

## 5. Heading normalization

Profile alias comparison is deterministic and intentionally conservative.

Normalization:

1. require a Unicode string;
2. normalize to NFC;
3. strip leading/trailing whitespace;
4. collapse runs of Unicode whitespace to one ASCII space;
5. apply Unicode `casefold()`;
6. do **not** remove punctuation;
7. do **not** perform fuzzy, edit-distance, embedding, synonym, or model matching.

Examples:

```text
"Standing Instructions" -> "standing instructions"
"  Standing   Instructions  " -> "standing instructions"
"Standing-Instructions" != "Standing Instructions"
```

Profile loading must reject two sections whose aliases normalize to the same string.

## 6. Section rule model

Each section rule declares:

- `section_id` — stable machine name;
- `aliases` — exact accepted headings after normalization;
- `render_heading` — canonical heading used by standardized projection;
- `scope` — exact `{kind, subject}` for generated records;
- `block_rules` — allowed Markdown block kinds and resulting record types;
- `route_hints` — optional route IDs emitted as compatibility metadata.

Example:

```json
{
  "section_id": "standing_instructions",
  "aliases": ["Standing Instructions", "Rules"],
  "render_heading": "Standing Instructions",
  "scope": {"kind": "global", "subject": "core"},
  "block_rules": {
    "unordered_list_item": "instruction"
  },
  "route_hints": ["route://global/tier0"]
}
```

No record is created from a block kind that is not explicitly declared in the matched section rule.

## 7. Built-in EveMiss Residence profile

The initial built-in profile is based only on section names already present in the prior memory design evidence:

| Observed section | Section ID | Record mapping | Scope |
|---|---|---|---|
| `Standing instructions` | `standing_instructions` | unordered list -> `instruction` | `global/core` |
| `Verification lessons` | `verification_lessons` | unordered list -> `lesson` | `global/verification` |
| `Who / how we work` | `who_how_we_work` | unordered list -> `instruction` | `global/collaboration` |
| `Named Identities` | `named_identities` | unordered list -> `fact` | `global/identity_registry` |
| `This machine` | `this_machine` | unordered list / paragraph -> `fact` | `global/machine` |

`Named Identities` deliberately maps to `fact`, not `identity`, because MNEME-MD must not mint or resolve resident identity from prose.

The built-in profile does not claim that these are the only possible Residence headings. Additional English, Traditional-Chinese, provider-specific, or agent-specific aliases require explicit profile evolution or a separate profile document.

## 8. Unicode and non-English aliases

The profile format supports arbitrary Unicode aliases. A profile may explicitly declare Traditional-Chinese headings such as a synthetic test alias:

```json
{
  "aliases": ["固定規則"]
}
```

Support for Unicode aliases is a format capability. Shipping a particular real-world alias as built-in canonical behavior requires evidence that the alias is actually used with that meaning.

## 9. Parser block model

MNEME-MD/0.1 recognizes these structural block classes:

- ATX heading (`#` through `######`);
- unordered list item beginning with `- `;
- paragraph block;
- fenced code block;
- table-like block.

Only `unordered_list_item` and `paragraph` are eligible for mapping in v0.1 profile rules.

Code fences and tables are always explicitly loss-accounted in v0.1 unless a future profile version adds a safe mapping.

## 10. Import algorithm

The importer operates as follows:

```text
source bytes
-> SHA-256 source binding
-> structural Markdown blocks with line ranges
-> exact heading normalization
-> profile section match
-> exact block rule lookup
-> MemoryRecord proposal
-> section-membership relation
-> route hints / mapping receipt
-> loss report
```

Unknown sections do not inherit the previous known section mapping. Their content remains unknown until a subsequent heading matches a declared profile section.

The source file is never modified.

## 11. Record construction

A mapped Markdown block produces a normal `MemoryRecord` under `mneme.memory-record/0.1`.

Example:

```json
{
  "record_version": "mneme.memory-record/0.1",
  "record_id": "md-...",
  "record_type": "instruction",
  "scope": {"kind": "global", "subject": "core"},
  "content": {"text": "Use exact-head validation."},
  "relations": [
    {
      "relation_type": "mneme-md.section/0.1",
      "target": "standing_instructions"
    }
  ],
  "provenance": {
    "event_id": "import-...",
    "source_ref": "mneme-md:evemiss-residence/0.1:<source-sha>:L12-L12"
  },
  "status": "active"
}
```

The section relation is a declared MNEME-MD extension relation. It does not redefine resident identity or authority.

## 12. Deterministic record IDs

Profiled-import record IDs are deterministic over:

- profile digest;
- source SHA-256;
- section ID;
- block kind;
- start/end line;
- exact UTF-8 content text.

Domain:

```text
MNEME-MD-RECORD-ID-0.1
```

Re-running the importer over byte-identical source and the same profile produces the same proposal IDs.

## 13. Loss report

A profiled import result must include at least:

- source SHA-256;
- profile ID;
- profile digest;
- total structural block count;
- mapped count;
- unknown-section block count;
- unsupported-block count;
- unmapped/uncertain entries with exact line ranges and machine reason;
- generated record IDs;
- route hints;
- `committed: false`.

Machine reasons include:

```text
no_active_section
unknown_section
unsupported_block_kind
block_kind_not_mapped
malformed_structure
```

A successful importer execution may still report loss. `status: PASS` means all loss is explicit, not that every source block was semantically migrated.

## 14. Mapping receipt

The importer emits a rebuildable compatibility mapping receipt separate from canonical transaction authority.

For each generated record:

- record ID;
- source line range;
- section ID;
- block kind;
- record type;
- scope;
- route hints.

The receipt allows audit and round-trip comparison but grants no canonical write authority.

## 15. Profile-aware projection

A standardized compatibility projection groups records by the `mneme-md.section/0.1` relation.

It emits:

```text
# MEMORY

## <render_heading>
- <whole record content>
```

Rules:

- records are never byte-sliced;
- a section heading is emitted only if at least one record from that section is included;
- records not mapped by the selected profile are omitted with reason `profile_unmapped`;
- unknown section relation targets are omitted with reason `unknown_section_relation`;
- projection is bound to source canonical head, profile ID/digest, included IDs, omissions, exact byte count, and content SHA-256;
- if even the fixed header cannot fit, projection fails explicitly.

## 16. Round-trip compatibility

Canonical record IDs are allowed to differ after re-import of a generated projection because source SHA and line ranges differ.

MNEME-MD therefore defines a compatibility entry tuple:

```text
(
  section_id,
  record_type,
  scope.kind,
  scope.subject,
  content.text
)
```

A projection/re-import round trip is compatible when the ordered compatibility entry sequence is identical.

This is a compatibility test only:

```text
COMPATIBILITY EQUALITY != CANONICAL BYTE EQUALITY
```

## 17. Scope and identity safety

MNEME-MD never derives identity scope from a person/agent name inside prose.

A profile section may declare `global/identity_registry`, but a record such as:

```text
- Aletheia -> path -> description
```

remains a fact string unless an external identity-aware layer separately resolves it.

```text
DISPLAY LABEL != RESIDENT ID
MEMORY TEXT != IDENTITY AUTHORITY
```

Identity-specific Markdown migration requires the caller to supply an already-resolved identity scope through a future or explicit profile context. v0.1 built-in mappings do not infer it.

## 18. Failure model

MNEME-MD fails closed on:

- unknown profile version;
- duplicate normalized aliases;
- duplicate section IDs;
- invalid record type in block rule;
- invalid scope kind/subject;
- invalid render heading;
- invalid route hint format;
- source decode failure;
- malformed profile JSON;
- projection impossible within hard budget.

It does not fail merely because a Markdown source contains unknown content; unknown content is loss-accounted instead.

## 19. Security and privacy

Public repository tests use synthetic Markdown only.

Real private Residence `MEMORY.md` files, local paths, resident lists, and private source digests are not committed to the public repository.

Profile parsing executes no embedded Markdown code and follows no links.

## 20. Initial implementation milestone

The first implementation milestone contains:

1. profile schema and loader;
2. deterministic alias normalization/collision gate;
3. built-in EveMiss Residence profile;
4. profile-aware Markdown importer;
5. deterministic record IDs and section relations;
6. explicit loss/mapping receipts;
7. profile-aware bounded projection;
8. compatibility-entry round-trip comparison;
9. synthetic Unicode alias tests;
10. exact-remote GitHub Actions acceptance gate.

## 21. Acceptance criteria

### M0 — Profile determinism

Byte-identical profile JSON produces the same profile digest and alias table.

### M1 — Alias collision rejection

Duplicate normalized aliases across sections are rejected.

### M2 — Exact mapping / no guessing

Known heading + supported block maps; unknown heading or unsupported block does not map and is explicitly loss-accounted.

### M3 — Identity non-inference

`Named Identities` entries remain facts under `global/identity_registry`; no resident ID is minted.

### M4 — Source non-destruction

Import leaves source bytes unchanged and binds source SHA-256.

### M5 — Unicode profile support

A synthetic Traditional-Chinese alias declared explicitly in a profile maps deterministically.

### M6 — Profile-aware budget projection

Projection remains within declared byte budget, contains only complete record blocks, and binds exact profile/source head metadata.

### M7 — Compatibility round trip

Import -> canonical records -> standardized profile projection -> re-import yields an identical ordered compatibility-entry sequence for all included records.

### M8 — Negative evidence

Every M0-M7 positive family has a corrupted, unknown, unauthorized, or unsupported counterpart that turns the relevant control red.

## 22. Design closure

MNEME-MD/0.1 establishes:

> Existing Markdown memory conventions are compatibility inputs, not canonical semantics. Their meaning enters MNEME only through an explicit versioned profile; anything not declared remains explicit loss rather than guessed memory.

This preserves the human convenience of `MEMORY.md` while keeping canonical memory deterministic, auditable, scope-safe, and independent of host Markdown limits.
