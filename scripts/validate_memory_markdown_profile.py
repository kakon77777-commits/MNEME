from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mneme.canonical import canonical_json_bytes
from mneme.errors import ProfileValidationError, ProjectionBudgetError
from mneme.markdown_compat import (
    compatibility_entries,
    project_profiled_markdown,
    propose_profiled_markdown_import,
)
from mneme.markdown_profile import MemoryMarkdownProfile, load_builtin_evemiss_profile
from mneme.records import MemoryRecord
from mneme.store import MemoryStore
from mneme.transactions import TransactionProposal

PROFILE = "MNEME-MD/0.1"


def source_commit() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        value = proc.stdout.strip()
        return value if proc.returncode == 0 and len(value) == 40 else None
    except OSError:
        return None


def _write(path: Path, text: str) -> bytes:
    path.write_text(text, encoding="utf-8", newline="\n")
    return path.read_bytes()


def _make_tx(records: list[MemoryRecord], *, tx_id: str, expected_head: str) -> TransactionProposal:
    return TransactionProposal.from_dict(
        {
            "transaction_version": "mneme.transaction/0.1",
            "transaction_id": tx_id,
            "expected_source_head": expected_head,
            "declared_record_count": len(records),
            "record_digests": [record.digest() for record in records],
            "records": [record.to_dict() for record in records],
            "authority_ref": "synthetic-authority:mneme-md-acceptance",
            "commit_marker": "MNEME_COMMIT/0.1",
        }
    )


def _synthetic_unicode_profile() -> MemoryMarkdownProfile:
    return MemoryMarkdownProfile.from_dict(
        {
            "profile_version": "mneme.memory-markdown-profile/0.1",
            "profile_id": "synthetic-zh/0.1",
            "title": "Synthetic Traditional Chinese Alias Profile",
            "sections": [
                {
                    "section_id": "rules",
                    "aliases": ["固定規則"],
                    "render_heading": "固定規則",
                    "scope": {"kind": "global", "subject": "core"},
                    "block_rules": {"unordered_list_item": "instruction"},
                    "route_hints": ["route://global/tier0"],
                }
            ],
        }
    )


def run_gate() -> dict[str, object]:
    profile = load_builtin_evemiss_profile()
    cases: dict[str, str] = {}
    controls: list[str] = []

    # M0: profile determinism and digest sensitivity.
    again = load_builtin_evemiss_profile()
    assert profile.digest() == again.digest()
    assert canonical_json_bytes(profile.to_dict()) == canonical_json_bytes(again.to_dict())
    changed = profile.to_dict()
    changed["title"] = changed["title"] + " changed"
    assert MemoryMarkdownProfile.from_dict(changed).digest() != profile.digest()
    controls.append("M0-profile-mutation-changes-digest")
    cases["M0"] = "PASS"

    # M1: normalized alias collisions fail closed.
    collision = profile.to_dict()
    collision["sections"][1]["aliases"].append(" standing   instructions ")
    try:
        MemoryMarkdownProfile.from_dict(collision)
        raise AssertionError("normalized alias collision unexpectedly accepted")
    except ProfileValidationError:
        controls.append("M1-normalized-alias-collision")
    cases["M1"] = "PASS"

    with tempfile.TemporaryDirectory(prefix="mneme-md-acceptance-") as td:
        temp = Path(td)

        # M2: exact mapping, unknown section is not guessed.
        exact_source = temp / "exact.md"
        _write(
            exact_source,
            "## Standing instructions\n"
            "- Keep exact state.\n\n"
            "## Unknown Section\n"
            "- Never guess this.\n",
        )
        exact = propose_profiled_markdown_import(exact_source, profile)
        assert len(exact.records) == 1
        assert exact.records[0]["content"]["text"] == "Keep exact state."
        assert all(record["content"]["text"] != "Never guess this." for record in exact.records)
        assert any(item["reason"] == "unknown_section" for item in exact.loss_report["loss"])
        controls.append("M2-unknown-section-not-guessed")
        cases["M2"] = "PASS"

        # M3: identity-like text remains a fact, never a resident identity.
        identities_source = temp / "identities.md"
        _write(
            identities_source,
            "## Named Identities\n"
            "- Synthetic-A -> synthetic path -> test label\n",
        )
        identities = propose_profiled_markdown_import(identities_source, profile)
        assert len(identities.records) == 1
        identity_record = identities.records[0]
        assert identity_record["record_type"] == "fact"
        assert identity_record["scope"] == {"kind": "global", "subject": "identity_registry"}
        assert identity_record["record_type"] != "identity"
        controls.append("M3-display-label-does-not-mint-identity")
        cases["M3"] = "PASS"

        # M4: source is byte-preserved and hash-bound.
        nondestructive_source = temp / "nondestructive.md"
        before = _write(nondestructive_source, "## Standing instructions\n- Preserve source bytes.\n")
        before_sha = hashlib.sha256(before).hexdigest()
        nondestructive = propose_profiled_markdown_import(nondestructive_source, profile)
        assert nondestructive_source.read_bytes() == before
        assert nondestructive.loss_report["source_sha256"] == before_sha
        changed_copy = before + b"\n"
        assert hashlib.sha256(changed_copy).hexdigest() != before_sha
        controls.append("M4-byte-mutation-changes-source-hash")
        cases["M4"] = "PASS"

        # M5: Unicode alias works only when declared explicitly.
        zh_profile = _synthetic_unicode_profile()
        zh_source = temp / "zh.md"
        _write(zh_source, "## 固定規則\n- 保留精確狀態。\n")
        zh = propose_profiled_markdown_import(zh_source, zh_profile)
        assert len(zh.records) == 1
        undeclared_source = temp / "zh-undeclared.md"
        _write(undeclared_source, "## 常駐規則\n- 不應被猜測。\n")
        undeclared = propose_profiled_markdown_import(undeclared_source, zh_profile)
        assert len(undeclared.records) == 0
        assert any(item["reason"] == "unknown_section" for item in undeclared.loss_report["loss"])
        controls.append("M5-undeclared-unicode-alias-not-guessed")
        cases["M5"] = "PASS"

        # M6: profile-aware projection is hard-budget and whole-record.
        budget_source = temp / "budget.md"
        _write(
            budget_source,
            "## Standing instructions\n"
            "- 第一條完整規則。\n"
            "- 第二條完整規則而且比較長。\n",
        )
        budget_import = propose_profiled_markdown_import(budget_source, profile)
        budget_records = [MemoryRecord.from_dict(raw) for raw in budget_import.records]
        full = project_profiled_markdown(
            budget_records,
            profile=profile,
            source_head="a" * 64,
            byte_budget=10_000,
        )
        second = "- 第二條完整規則而且比較長。\n".encode("utf-8")
        cut_budget = full.content.index(second) + len(second) - 1
        bounded = project_profiled_markdown(
            budget_records,
            profile=profile,
            source_head="a" * 64,
            byte_budget=cut_budget,
        )
        assert len(bounded.content) <= cut_budget
        bounded_text = bounded.content.decode("utf-8")
        assert "第一條完整規則。" in bounded_text
        assert "第二條完整規則而且比較長。" not in bounded_text
        assert any(item["reason"] == "budget_exceeded" for item in bounded.manifest["omitted"])
        try:
            project_profiled_markdown(
                budget_records,
                profile=profile,
                source_head="a" * 64,
                byte_budget=1,
            )
            raise AssertionError("impossible header budget unexpectedly succeeded")
        except ProjectionBudgetError:
            controls.append("M6-impossible-header-budget")
        cases["M6"] = "PASS"

        # M7: import -> store -> projection -> re-import compatibility closure.
        round_source = temp / "roundtrip.md"
        _write(
            round_source,
            "## Standing instructions\n"
            "- Keep exact state.\n"
            "- Reject silent truncation.\n\n"
            "## Verification lessons\n"
            "- Use negative controls.\n",
        )
        round_import = propose_profiled_markdown_import(round_source, profile)
        original_records = [MemoryRecord.from_dict(raw) for raw in round_import.records]
        store = MemoryStore(temp / "memory.mlfdir")
        store.initialize()
        receipt = store.commit(_make_tx(original_records, tx_id="tx-md-acceptance", expected_head="GENESIS"))
        projected = project_profiled_markdown(
            tuple(store.iter_committed_records()),
            profile=profile,
            source_head=receipt.new_head,
            byte_budget=10_000,
        )
        projected_path = temp / "projected.md"
        projected_path.write_bytes(projected.content)
        reimported = propose_profiled_markdown_import(projected_path, profile)
        reimported_records = [MemoryRecord.from_dict(raw) for raw in reimported.records]
        original_entries = compatibility_entries(original_records)
        reimported_entries = compatibility_entries(reimported_records)
        assert original_entries == reimported_entries

        tampered_text = projected.content.decode("utf-8").replace("Keep exact state.", "Changed state.", 1)
        tampered_path = temp / "tampered.md"
        _write(tampered_path, tampered_text)
        tampered_import = propose_profiled_markdown_import(tampered_path, profile)
        tampered_records = [MemoryRecord.from_dict(raw) for raw in tampered_import.records]
        assert compatibility_entries(tampered_records) != original_entries
        controls.append("M7-tampered-projection-changes-compatibility")
        cases["M7"] = "PASS"

        # M8: every prior family has a negative control.
        families = {item.split("-", 1)[0] for item in controls}
        assert all(f"M{i}" in families for i in range(8))
        cases["M8"] = "PASS"

        return {
            "profile": PROFILE,
            "status": "PASS",
            "cases": cases,
            "controls": len(controls),
            "control_details": controls,
            "canonical_head": receipt.new_head,
            "profile_id": profile.profile_id,
            "profile_digest": profile.digest(),
            "source_commit": source_commit(),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        receipt = run_gate()
        code = 0
    except Exception as exc:
        receipt = {
            "profile": PROFILE,
            "status": "FAIL",
            "cases": {},
            "controls": 0,
            "control_details": [],
            "canonical_head": "GENESIS",
            "profile_id": None,
            "profile_digest": None,
            "source_commit": source_commit(),
            "error": f"{type(exc).__name__}: {exc}",
        }
        code = 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json_bytes(receipt) + b"\n")
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
