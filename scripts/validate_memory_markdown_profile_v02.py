from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mneme.canonical import canonical_json_bytes
from mneme.markdown_compat import compatibility_entries, project_profiled_markdown, propose_profiled_markdown_import
from mneme.markdown_profile import MemoryMarkdownProfile, load_builtin_evemiss_profile, load_builtin_evemiss_profile_v02
from mneme.records import MemoryRecord

PROFILE = "MNEME-MD-EVEMISS/0.2"
FIXTURE = ROOT / "fixtures" / "synthetic" / "memory-markdown-real-dialect-v02.md"
V01_DIGEST = "0757299afd2d72d9cd0f3f3c7ff616f17836edff2b694afc0340d0eea055fdeb"


def source_commit() -> str | None:
    proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False)
    value = proc.stdout.strip()
    return value if proc.returncode == 0 and len(value) == 40 else None


def run_gate() -> dict[str, object]:
    cases: dict[str, str] = {}
    controls: list[str] = []

    v01 = load_builtin_evemiss_profile()
    v02 = load_builtin_evemiss_profile_v02()

    assert v01.digest() == V01_DIGEST
    controls.append("R0-v01-digest-frozen")
    cases["R0"] = "PASS"

    assert v02.profile_id == "evemiss-residence/0.2"
    assert v02.digest() == load_builtin_evemiss_profile_v02().digest()
    assert v02.digest() != v01.digest()
    mutated = v02.to_dict()
    mutated["title"] = str(mutated["title"]) + " mutated"
    assert MemoryMarkdownProfile.from_dict(mutated).digest() != v02.digest()
    controls.append("R1-v02-mutation-changes-digest")
    cases["R1"] = "PASS"

    proposal = propose_profiled_markdown_import(FIXTURE, v02)
    assert len(proposal.records) == 6
    loss = proposal.loss_report["loss"]
    assert len(loss) == 1
    assert loss[0]["reason"] == "block_kind_not_mapped"
    assert loss[0]["section_id"] == "named_identities"
    assert loss[0]["kind"] == "paragraph"
    controls.append("R2-mixed-registry-paragraph-remains-unmapped")
    cases["R2"] = "PASS"

    old = propose_profiled_markdown_import(FIXTURE, v01)
    old_reasons = [item["reason"] for item in old.loss_report["loss"]]
    assert old_reasons.count("unknown_heading") == 2
    controls.append("R3-v01-does-not-guess-v02-dialect")
    cases["R3"] = "PASS"

    tmp = ROOT / ".tmp-v02-unknown-heading.md"
    try:
        tmp.write_text("## Named Residents\n- Synthetic resident.\n", encoding="utf-8")
        unknown = propose_profiled_markdown_import(tmp, v02)
        assert len(unknown.records) == 0
        assert any(item["reason"] == "unknown_heading" for item in unknown.loss_report["loss"])
    finally:
        tmp.unlink(missing_ok=True)
    controls.append("R4-undeclared-synonym-not-guessed")
    cases["R4"] = "PASS"

    records = tuple(MemoryRecord.from_dict(raw) for raw in proposal.records)
    projection = project_profiled_markdown(records, profile=v02, source_head="synthetic-v02", byte_budget=64000)
    tmp = ROOT / ".tmp-v02-roundtrip.md"
    try:
        tmp.write_bytes(projection.content)
        again = propose_profiled_markdown_import(tmp, v02)
        again_records = tuple(MemoryRecord.from_dict(raw) for raw in again.records)
        assert compatibility_entries(records) == compatibility_entries(again_records)
    finally:
        tmp.unlink(missing_ok=True)
    controls.append("R5-roundtrip-compatibility-preserved")
    cases["R5"] = "PASS"

    return {
        "profile": PROFILE,
        "profile_id": v02.profile_id,
        "profile_digest": v02.digest(),
        "status": "PASS",
        "cases": cases,
        "controls": len(controls),
        "control_details": controls,
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
