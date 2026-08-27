# MNEME-MD/0.1 Compatibility Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a versioned, deterministic Markdown compatibility layer that maps only explicitly declared `MEMORY.md` sections into MLF-RM records, loss-accounts everything else, and supports bounded standardized projection plus compatibility round-trip verification.

**Architecture:** Keep the existing Fresh Memory Core unchanged. `markdown_profile.py` validates and digests compatibility profiles; `markdown_compat.py` performs profile-aware import, section-membership relations, loss/mapping receipts, projection, and compatibility-entry comparison. Built-in profile data lives as JSON, and acceptance runs only synthetic public fixtures.

**Tech Stack:** Python 3.11+, standard library (`dataclasses`, `hashlib`, `json`, `pathlib`, `re`, `unicodedata`), existing `jsonschema>=4.23`, `pytest>=8.0`.

**Spec:** `docs/superpowers/specs/2026-08-27-memory-markdown-compatibility-profile-design.md`

## Global Constraints

- Base canonical format remains `MLF-RM/0.1`; MNEME-MD is a compatibility profile, not a replacement format.
- No fuzzy, embedding, or LLM section classification.
- Heading comparison is NFC + whitespace collapse + casefold only; punctuation is preserved.
- Unknown sections and unsupported blocks are explicit loss, never guessed mappings.
- `Named Identities` maps to `fact` under `global/identity_registry`; it never mints resident identity.
- Real private Residence source content, paths, resident lists, and source digests are not committed publicly.
- Import is proposal-only and non-destructive.
- Projection is hard-budget and whole-record; no byte slicing.
- Existing Fresh Memory Core tests remain green.

---

## Planned Files

```text
schemas/memory-markdown-profile-0.1.schema.json
profiles/memory-markdown/evemiss-residence-0.1.json
src/mneme/markdown_profile.py
src/mneme/markdown_compat.py
tests/test_markdown_profile.py
tests/test_markdown_compat.py
fixtures/synthetic/compat-memory.md
scripts/validate_memory_markdown_profile.py
tests/test_markdown_profile_acceptance.py
.github/workflows/memory-markdown-profile.yml
README.md
```

---

### Task 1: Profile Model, Digest, and Alias Collision Gate

**Files:**
- Create: `schemas/memory-markdown-profile-0.1.schema.json`
- Create: `src/mneme/markdown_profile.py`
- Modify: `src/mneme/errors.py`
- Test: `tests/test_markdown_profile.py`

**Interfaces:**
- `normalize_heading(text: str) -> str`
- `MemoryMarkdownProfile.from_dict(raw: dict[str, object]) -> MemoryMarkdownProfile`
- `MemoryMarkdownProfile.digest() -> str`
- `MemoryMarkdownProfile.match_heading(text: str) -> SectionRule | None`
- `ProfileValidationError(MnemeError, ValueError)`

- [ ] **Step 1: Write failing profile tests**

```python
from mneme.markdown_profile import MemoryMarkdownProfile, normalize_heading
from mneme.errors import ProfileValidationError
import pytest


def base_profile():
    return {
        "profile_version": "mneme.memory-markdown-profile/0.1",
        "profile_id": "synthetic/0.1",
        "title": "Synthetic",
        "sections": [{
            "section_id": "rules",
            "aliases": ["Standing Instructions"],
            "render_heading": "Standing Instructions",
            "scope": {"kind": "global", "subject": "core"},
            "block_rules": {"unordered_list_item": "instruction"},
            "route_hints": ["route://global/tier0"]
        }]
    }


def test_heading_normalization_is_nfc_whitespace_casefold_only():
    assert normalize_heading("  Standing   Instructions  ") == "standing instructions"
    assert normalize_heading("Standing-Instructions") != normalize_heading("Standing Instructions")


def test_profile_digest_is_stable():
    a = MemoryMarkdownProfile.from_dict(base_profile())
    b = MemoryMarkdownProfile.from_dict(dict(reversed(list(base_profile().items()))))
    assert a.digest() == b.digest()


def test_normalized_alias_collision_is_rejected():
    raw = base_profile()
    raw["sections"].append({**raw["sections"][0], "section_id": "other", "aliases": [" standing   instructions "]})
    with pytest.raises(ProfileValidationError):
        MemoryMarkdownProfile.from_dict(raw)
```

- [ ] **Step 2: Run and verify RED**

```bash
PYTHONPATH=src python -m pytest tests/test_markdown_profile.py -q
```

Expected: import failure because `mneme.markdown_profile` does not exist.

- [ ] **Step 3: Implement minimal profile loader**

Use `jsonschema` with `additionalProperties: false`. Allowed scope kinds equal the MLF-RM set. Allowed record types equal the current `MemoryRecord` vocabulary. Allowed block-rule keys in v0.1 are exactly `unordered_list_item` and `paragraph`. Route hints must start `route://`.

Profile digest:

```python
sha256_domain(b"MNEME-MD-PROFILE-0.1", canonical_json_bytes(profile.to_dict()))
```

Alias table is built at load time and rejects duplicate normalized aliases across all sections.

- [ ] **Step 4: Add negative tests for bad route, record type, duplicate section ID, empty render heading**

Each must raise `ProfileValidationError`.

- [ ] **Step 5: Run focused regression**

```bash
PYTHONPATH=src python -m pytest tests/test_markdown_profile.py tests/test_records.py tests/test_canonical.py -q
```

- [ ] **Step 6: Commit Task 1**

```bash
git add schemas/memory-markdown-profile-0.1.schema.json src/mneme/markdown_profile.py src/mneme/errors.py tests/test_markdown_profile.py
git commit -m "feat: add versioned memory Markdown profiles"
```

---

### Task 2: Built-in EveMiss Residence Profile and Unicode Alias Capability

**Files:**
- Create: `profiles/memory-markdown/evemiss-residence-0.1.json`
- Modify: `tests/test_markdown_profile.py`

**Interfaces:**
- `load_profile(path: Path) -> MemoryMarkdownProfile`
- `load_builtin_evemiss_profile() -> MemoryMarkdownProfile`

- [ ] **Step 1: Add failing built-in mapping test**

Verify exact observed mappings:

```text
Standing instructions -> instruction / global/core
Verification lessons -> lesson / global/verification
Who / how we work -> instruction / global/collaboration
Named Identities -> fact / global/identity_registry
This machine -> fact / global/machine
```

- [ ] **Step 2: Add explicit Unicode alias test**

Create an in-memory synthetic profile with alias `固定規則`; assert `## 固定規則` can match only because the profile declares it. Also assert an undeclared Chinese synonym does not match.

- [ ] **Step 3: Implement built-in JSON and loader helpers**

The built-in profile must not add unobserved Chinese aliases.

- [ ] **Step 4: Run focused tests**

```bash
PYTHONPATH=src python -m pytest tests/test_markdown_profile.py -q
```

- [ ] **Step 5: Commit Task 2**

```bash
git add profiles/memory-markdown/evemiss-residence-0.1.json src/mneme/markdown_profile.py tests/test_markdown_profile.py
git commit -m "feat: add EveMiss Residence Markdown profile"
```

---

### Task 3: Profile-Aware Import, Deterministic IDs, and Explicit Loss

**Files:**
- Create: `src/mneme/markdown_compat.py`
- Create: `fixtures/synthetic/compat-memory.md`
- Test: `tests/test_markdown_compat.py`

**Interfaces:**
- `ProfiledImportProposal(records, loss_report, mapping_receipt, committed=False)`
- `propose_profiled_markdown_import(path: Path, profile: MemoryMarkdownProfile) -> ProfiledImportProposal`
- `compatibility_entries(records) -> tuple[tuple[str, str, str, str, str], ...]`

- [ ] **Step 1: Write failing exact-mapping test**

Synthetic source:

```markdown
# MEMORY

## Standing instructions
- Keep exact state.

## Named Identities
- Synthetic-A -> synthetic path -> test label

## Unknown Section
- Never guess this.

## Verification lessons
- Validators need negative controls.

```text
opaque
```
```

Assert:

- 3 mapped records;
- record types are `instruction`, `fact`, `lesson`;
- identity-registry item is a `fact`, not `identity`;
- unknown-section list item does not map;
- code fence is loss-accounted;
- source bytes unchanged.

- [ ] **Step 2: Run and verify RED**

```bash
PYTHONPATH=src python -m pytest tests/test_markdown_compat.py -q
```

- [ ] **Step 3: Implement structural scanner and profiled importer**

Do not change the legacy `propose_markdown_import()` behavior. The new scanner tracks heading, unordered list item, paragraph, code fence, and table blocks with exact line ranges.

Mapped records include relation:

```json
{"relation_type":"mneme-md.section/0.1","target":"<section_id>"}
```

Deterministic record ID domain is `MNEME-MD-RECORD-ID-0.1` over canonical JSON containing profile digest, source SHA, section ID, block kind, line range, and exact content text.

`source_ref` uses only profile ID, source SHA, and line range; it does not include local file paths.

- [ ] **Step 4: Add loss-reason and deterministic-ID controls**

Assert reasons include `unknown_section`, `unsupported_block_kind`, `block_kind_not_mapped`, and `no_active_section` where appropriate. Re-importing byte-identical source with same profile yields identical record IDs.

- [ ] **Step 5: Run profiled import + legacy importer regression**

```bash
PYTHONPATH=src python -m pytest tests/test_markdown_compat.py tests/test_markdown_import.py -q
```

- [ ] **Step 6: Commit Task 3**

```bash
git add src/mneme/markdown_compat.py fixtures/synthetic/compat-memory.md tests/test_markdown_compat.py
git commit -m "feat: add fail-closed profiled Markdown import"
```

---

### Task 4: Profile-Aware Bounded Projection and Compatibility Entries

**Files:**
- Modify: `src/mneme/markdown_compat.py`
- Modify: `tests/test_markdown_compat.py`

**Interfaces:**
- `ProfiledProjectionResult(content: bytes, manifest: dict[str, object])`
- `project_profiled_markdown(records, *, profile, source_head: str, byte_budget: int) -> ProfiledProjectionResult`
- `compatibility_entries(records) -> tuple[tuple[str, str, str, str, str], ...]`

- [ ] **Step 1: Write failing standardized-projection tests**

Assert output groups records as:

```markdown
# MEMORY

## Standing Instructions
- ...
```

and manifest binds `profile_id`, `profile_digest`, `source_head`, `byte_budget`, `included_ids`, `omitted`, `content_sha256`, `byte_count`.

- [ ] **Step 2: Add hard-budget/multibyte tests**

Use Traditional-Chinese content and a budget one byte below the next whole record block. Assert valid UTF-8 and whole-record inclusion/omission only.

- [ ] **Step 3: Implement projection**

Group records by `mneme-md.section/0.1`. Unknown/missing section relations are omitted with explicit reasons. Emit a section heading only when at least one full record in that section fits. If `# MEMORY\n` cannot fit, raise `ProjectionBudgetError`.

- [ ] **Step 4: Implement compatibility entry extraction**

Each mapped record yields:

```text
(section_id, record_type, scope.kind, scope.subject, content.text)
```

Order is input order.

- [ ] **Step 5: Run focused regressions**

```bash
PYTHONPATH=src python -m pytest tests/test_markdown_compat.py tests/test_projection.py -q
```

- [ ] **Step 6: Commit Task 4**

```bash
git add src/mneme/markdown_compat.py tests/test_markdown_compat.py
git commit -m "feat: add profile-aware bounded Markdown projection"
```

---

### Task 5: Import → Store → Projection → Re-import Round-Trip

**Files:**
- Modify: `tests/test_markdown_compat.py`
- Create: `scripts/validate_memory_markdown_profile.py`
- Test: `tests/test_markdown_profile_acceptance.py`

**Interfaces:**
- Acceptance script emits canonical JSON receipt with `profile`, `status`, `cases`, `controls`, `canonical_head`, `profile_digest`, and `source_commit`.

- [ ] **Step 1: Write failing end-to-end round-trip test**

Pipeline:

```text
synthetic MEMORY.md
-> profiled proposal
-> TransactionProposal
-> MemoryStore
-> profile-aware projection
-> re-import projection
-> compatibility_entries equality
```

Assert canonical IDs may differ, but compatibility entries are identical for all included records.

- [ ] **Step 2: Implement deterministic acceptance runner**

Cases:

```text
M0 profile determinism
M1 alias collision rejection
M2 exact mapping / no guessing
M3 identity non-inference
M4 source non-destruction
M5 Unicode explicit alias support
M6 hard-budget profile projection
M7 compatibility round trip
M8 negative evidence
```

At least one negative control per M0-M7 family.

- [ ] **Step 3: Add acceptance test**

Run the script as a subprocess and require exit `0`, `status: PASS`, M0-M8 all PASS, and at least 8 controls.

- [ ] **Step 4: Run full local verification**

```bash
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python scripts/validate_memory_markdown_profile.py --output memory-markdown-profile.json
python -m compileall -q src
```

- [ ] **Step 5: Corrupt built-in profile alias and verify acceptance turns red**

Temporarily introduce a normalized alias collision, run acceptance, require non-zero/FAIL, restore, rerun full verification to PASS.

- [ ] **Step 6: Commit Task 5**

```bash
git add scripts/validate_memory_markdown_profile.py tests/test_markdown_profile_acceptance.py tests/test_markdown_compat.py
git commit -m "test: close MNEME-MD compatibility acceptance"
```

---

### Task 6: Documentation, CI, and Release Candidate Closure

**Files:**
- Modify: `README.md`
- Create: `.github/workflows/memory-markdown-profile.yml`
- Modify: `src/mneme/__init__.py`

**Interfaces:**
- Package version becomes `0.2.0a1`.
- CI runs exact branch bytes on Python 3.11.

- [ ] **Step 1: Update README**

Document:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts/validate_fresh_memory_core.py --output fresh-memory-core.json
python scripts/validate_memory_markdown_profile.py --output memory-markdown-profile.json
```

Explain the built-in profile boundary and that unknown aliases remain loss-accounted.

- [ ] **Step 2: Add exact-remote GitHub Actions workflow**

Workflow runs install, full pytest, both acceptance scripts, and `compileall` on push/PR affecting runtime/profile/schema/tests/scripts/workflow files.

- [ ] **Step 3: Bump alpha package version**

```python
__version__ = "0.2.0a1"
```

and keep `pyproject.toml` package version synchronized.

- [ ] **Step 4: Run final local verification**

```bash
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python scripts/validate_fresh_memory_core.py --output fresh-memory-core.json
PYTHONPATH=src python scripts/validate_memory_markdown_profile.py --output memory-markdown-profile.json
python -m compileall -q src
```

- [ ] **Step 5: Commit Task 6**

```bash
git add README.md .github/workflows/memory-markdown-profile.yml src/mneme/__init__.py pyproject.toml
git commit -m "release: prepare MNEME-MD 0.1 candidate"
```

---

## Plan Self-Review

- Profile validation/digest/collision: Task 1.
- Built-in observed headings + Unicode capability: Task 2.
- Exact mapping, section relations, deterministic IDs, loss report: Task 3.
- Hard-budget standardized projection + compatibility entries: Task 4.
- Full import/store/project/re-import compatibility proof and negative controls: Task 5.
- Documentation/version/exact-remote CI: Task 6.
- Identity non-inference is tested explicitly in Tasks 3 and 5.
- Legacy importer remains unchanged and regression-tested.
- No fuzzy/LLM mapping, real Residence migration, or private source publication enters scope.

Execute Tasks 1–6 strictly in order with TDD. Do not start dynamic DB integration, live LIMEN integration, or automatic migration of real private Residence files in this plan.
