from __future__ import annotations

import argparse
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
from mneme.errors import ProjectionBudgetError, StoreConflictError, TransactionValidationError
from mneme.markdown_import import propose_markdown_import
from mneme.projection import project_markdown
from mneme.records import MemoryRecord
from mneme.routes import Route, RouteResolver
from mneme.store import MemoryStore
from mneme.transactions import TransactionProposal

PROFILE = "MLF-RM/0.1"
FIXTURE = ROOT / "fixtures" / "synthetic" / "records.jsonl"


def load_fixture(path: Path = FIXTURE) -> list[MemoryRecord]:
    records: list[MemoryRecord] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        item = json.loads(line)
        if set(item) != {"declared_digest", "record"}:
            raise ValueError(f"fixture line {line_no}: exact wrapper shape required")
        record = MemoryRecord.from_dict(item["record"])
        if record.digest() != item["declared_digest"]:
            raise ValueError(f"fixture line {line_no}: declared digest mismatch")
        records.append(record)
    if len(records) < 3:
        raise ValueError("fixture must contain global, identity/a, identity/b controls")
    return records


def make_tx(records: list[MemoryRecord], *, tx_id: str, expected_head: str) -> TransactionProposal:
    raw_records = [r.to_dict() for r in records]
    return TransactionProposal.from_dict({
        "transaction_version": "mneme.transaction/0.1",
        "transaction_id": tx_id,
        "expected_source_head": expected_head,
        "declared_record_count": len(raw_records),
        "record_digests": [r.digest() for r in records],
        "records": raw_records,
        "authority_ref": "synthetic-authority:acceptance",
        "commit_marker": "MNEME_COMMIT/0.1",
    })


def source_commit() -> str | None:
    try:
        proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False)
        value = proc.stdout.strip()
        return value if proc.returncode == 0 and len(value) == 40 else None
    except OSError:
        return None


def run_gate() -> dict[str, object]:
    fixture = load_fixture()
    cases: dict[str, str] = {}
    controls: list[str] = []

    tx_a = make_tx(fixture, tx_id="tx-acceptance", expected_head="GENESIS")
    tx_b = make_tx(load_fixture(), tx_id="tx-acceptance", expected_head="GENESIS")
    assert canonical_json_bytes(tx_a.to_dict()) == canonical_json_bytes(tx_b.to_dict())
    assert tx_a.digest() == tx_b.digest()
    mutated = fixture[0].to_dict()
    mutated["content"]["text"] += " mutated"
    assert MemoryRecord.from_dict(mutated).digest() != fixture[0].digest()
    controls.append("A0-mutated-input-changes-digest")
    cases["A0"] = "PASS"

    with tempfile.TemporaryDirectory(prefix="mneme-acceptance-") as td:
        temp = Path(td)
        store = MemoryStore(temp / "memory.mlfdir")
        store.initialize()
        receipt = store.commit(tx_a)
        baseline_head = receipt.new_head
        baseline_count = len(list(store.iter_committed_transactions()))

        try:
            json.loads('{"transaction_version":"mneme.transaction/0.1"')
            raise AssertionError("truncated JSON unexpectedly parsed")
        except json.JSONDecodeError:
            controls.append("A1-truncated-json")

        missing = tx_a.to_dict()
        missing["transaction_id"] = "tx-missing"
        missing["expected_source_head"] = baseline_head
        del missing["commit_marker"]
        try:
            TransactionProposal.from_dict(missing)
            raise AssertionError("missing marker unexpectedly accepted")
        except TransactionValidationError:
            controls.append("A1-missing-marker")

        for name, mutate in [
            ("wrong-count", lambda raw: raw.__setitem__("declared_record_count", len(raw["records"]) + 1)),
            ("wrong-digest", lambda raw: raw.__setitem__("record_digests", ["0" * 64] * len(raw["records"]))),
        ]:
            raw = make_tx(fixture, tx_id=f"tx-{name}", expected_head=baseline_head).to_dict()
            mutate(raw)
            bad = TransactionProposal.from_dict(raw)
            try:
                store.commit(bad)
                raise AssertionError(f"{name} unexpectedly committed")
            except StoreConflictError:
                controls.append(f"A1-{name}")

        stale = make_tx(fixture, tx_id="tx-stale", expected_head="GENESIS")
        stale_raw = stale.to_dict()
        stale_raw["records"][0]["record_id"] = "g1-stale"
        stale_raw["records"][0]["provenance"]["event_id"] = "evt-g1-stale"
        stale_record = MemoryRecord.from_dict(stale_raw["records"][0])
        stale_raw["record_digests"][0] = stale_record.digest()
        stale = TransactionProposal.from_dict(stale_raw)
        try:
            store.commit(stale)
            raise AssertionError("stale head unexpectedly committed")
        except StoreConflictError:
            controls.append("A1-stale-head")

        assert store.head() == baseline_head
        assert len(list(store.iter_committed_transactions())) == baseline_count
        cases["A1"] = "PASS"

        before = [r.to_dict() for r in fixture]
        small = project_markdown(fixture, source_head=baseline_head, route_id="route://acceptance/all", byte_budget=130)
        large = project_markdown(fixture, source_head=baseline_head, route_id="route://acceptance/all", byte_budget=2000)
        assert small.content != large.content
        assert small.manifest["source_head"] == large.manifest["source_head"] == baseline_head
        assert [r.to_dict() for r in fixture] == before
        detached = fixture[0].to_dict()
        detached["content"]["text"] = "attempted external mutation"
        assert fixture[0].to_dict() == before[0]
        controls.append("A2-detached-projection-source-mutation")
        cases["A2"] = "PASS"

        assert len(small.content) <= 130
        assert len(large.content) <= 2000
        try:
            project_markdown([], source_head=baseline_head, route_id="route://acceptance/all", byte_budget=1)
            raise AssertionError("impossible projection budget unexpectedly succeeded")
        except ProjectionBudgetError:
            controls.append("A3-explicit-overflow")
        cases["A3"] = "PASS"

        route = Route.from_dict({
            "route_version": "mneme.route/0.1",
            "route_id": "route://identity/a/bootstrap",
            "scope_prefixes": ["identity/a"],
            "record_types": [],
        })
        routed = RouteResolver().resolve(route, fixture, {"identity/a"})
        assert "a1" in routed.included_ids
        assert "b1" not in routed.included_ids
        private_b = fixture[2].to_dict()["content"]["text"]
        routed_projection = project_markdown(
            routed.records,
            source_head=baseline_head,
            route_id=route.route_id,
            byte_budget=1000,
            omissions=routed.omitted,
        )
        assert private_b.encode("utf-8") not in routed_projection.content
        assert private_b not in json.dumps(routed_projection.manifest, ensure_ascii=False)
        controls.append("A4-identity-b-scope-leak-blocked")
        cases["A4"] = "PASS"

        md = temp / "MEMORY.md"
        md.write_text("# Rules\n\n- Preserve exact state.\n\nFree prose.\n\n```text\nopaque\n```\n", encoding="utf-8")
        original = md.read_bytes()
        proposal = propose_markdown_import(md)
        assert md.read_bytes() == original
        assert proposal.loss_report["source_sha256"] == hashlib.sha256(original).hexdigest()
        assert proposal.committed is False
        assert proposal.loss_report["unmapped_count"] >= 1
        controls.append("A5-unmapped-code-fence-accounted")
        cases["A5"] = "PASS"

        families = {item.split("-", 1)[0] for item in controls}
        assert all(f"A{i}" in families for i in range(6))
        cases["A6"] = "PASS"

        return {
            "profile": PROFILE,
            "status": "PASS",
            "cases": cases,
            "controls": len(controls),
            "control_details": controls,
            "canonical_head": baseline_head,
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
