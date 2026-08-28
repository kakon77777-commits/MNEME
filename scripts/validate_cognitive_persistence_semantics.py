from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mneme.canonical import canonical_json_bytes
from mneme.cps.adapter import CpsObservationAdapter
from mneme.cps.factorization import (
    FactorizationProposal,
    build_factorization_proposal,
    validate_factorization_sources,
)
from mneme.cps.models import (
    EquivalenceContract,
    PersistenceAssessment,
    RecomputationReference,
)
from mneme.cps.rules import AssessmentContext, assess_record
from mneme.cps.seed import build_cognitive_seed_proposal
from mneme.errors import CpsValidationError
from mneme.records import MemoryRecord

PROFILE = "MNEME-CPS/0.1"


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


def _load_records() -> dict[str, MemoryRecord]:
    records: dict[str, MemoryRecord] = {}
    path = ROOT / "fixtures" / "synthetic" / "cps-records.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = MemoryRecord.from_dict(json.loads(line))
        records[str(record.to_dict()["record_id"])] = record
    return records


def _eq_contract() -> EquivalenceContract:
    return EquivalenceContract.from_dict({
        "contract_version": "mneme.equivalence-contract/0.1",
        "contract_id": "eq-cps-acceptance",
        "observation_surfaces": [
            {"kind": "ANCHOR_MUST_MATCH", "subject_ref": "cps-generative"},
            {"kind": "AUTHORITY_MUST_NOT_ESCALATE", "subject_ref": "cps-decision"},
        ],
        "forbidden_equalities": ["TOKEN_EQUALITY", "TRACE_EQUALITY"],
        "authority": False,
    })


def _recompute_ref() -> RecomputationReference:
    return RecomputationReference.from_dict({
        "reference_version": "mneme.recomputation-reference/0.1",
        "reference_id": "rr-cps-current",
        "source_kind": "synthetic",
        "source_ref": "synthetic://world/current",
        "query_or_operation": "read-current-state",
        "freshness_requirement": "before-use",
        "previous_observation_ref": "cps-current",
        "failure_policy": "FAIL_CLOSED",
        "authority": False,
    })


def _expect_cps_error(fn, label: str, controls: list[str]) -> None:
    try:
        fn()
    except CpsValidationError:
        controls.append(label)
        return
    raise AssertionError(f"negative control did not fail closed: {label}")


def run_gate() -> dict[str, object]:
    cases: dict[str, str] = {}
    controls: list[str] = []
    records = _load_records()
    adapter = CpsObservationAdapter()

    # Load one explicit fixture assessment so an external corruption can make the gate red.
    control_assessment_raw = json.loads(
        (ROOT / "fixtures" / "synthetic" / "cps-control-assessment.json").read_text(encoding="utf-8")
    )
    fixture_assessment = PersistenceAssessment.from_dict(control_assessment_raw)

    # C0 — additive compatibility.
    decision = records["cps-decision"]
    decision_before = decision.to_dict()
    decision_digest = decision.digest()
    assert MemoryRecord.from_dict(decision_before).digest() == decision_digest
    assert fixture_assessment.to_dict()["authority"] is False
    controls.append("C0-existing-record-digest-unchanged")
    cases["C0"] = "PASS"

    # C1 — source objects remain isolated even when returned dictionaries are mutated.
    assessed = adapter.assess([decision], [AssessmentContext(explicit_decision=True)])[0]
    mutated_view = decision.to_dict()
    mutated_view["content"]["text"] = "mutated outside record"
    assert decision.to_dict() == decision_before
    assert decision.digest() == decision_digest
    controls.append("C1-source-record-mutation-blocked")
    cases["C1"] = "PASS"

    # C2 — conflicting evidence falls back to UNKNOWN/BLOCKED.
    unknown = assess_record(
        records["cps-ephemeral"],
        AssessmentContext(conflicting_evidence=True, ephemeral_working_state=True),
    )
    assert unknown.to_dict()["candidate"] == "UNKNOWN"
    assert unknown.to_dict()["risk"] == "BLOCKED"
    controls.append("C2-conflicting-evidence-yields-unknown")
    cases["C2"] = "PASS"

    # Build canonical examples of all six candidates for C4 and later cases.
    preserve = assessed
    structural = assess_record(
        records["cps-structure"],
        AssessmentContext(structural_dependency=True),
    )
    generative = assess_record(
        records["cps-generative"],
        AssessmentContext(
            derivable_explanation=True,
            reconstruction_recipe_ref="synthetic://recipe/cps",
            obligation_set_ref="synthetic://obligation/cps",
        ),
    )
    recompute = assess_record(
        records["cps-current"],
        AssessmentContext(
            historical_observation=True,
            freshness_required=True,
            external_source_ref="synthetic://world/current",
            previous_observation_ref="cps-current",
        ),
    )
    discard = assess_record(
        records["cps-ephemeral"],
        AssessmentContext(ephemeral_working_state=True),
    )
    plain_unknown = assess_record(records["cps-ephemeral"], AssessmentContext())

    # C3 — evidential floor cannot be silently omitted.
    _expect_cps_error(
        lambda: build_factorization_proposal(
            assessments=[preserve],
            source_refs=["cps-decision"],
            anchors=[],
            structure=[],
            generators=[],
            obligations=[],
            provenance_refs=[],
            recompute_refs=[],
            unresolved_refs=[],
        ),
        "C3-required-preservation-omission-rejected",
        controls,
    )
    cases["C3"] = "PASS"

    # C4 — all six semantics are machine-readable and invalid candidates fail closed.
    candidates = {
        preserve.to_dict()["candidate"],
        structural.to_dict()["candidate"],
        generative.to_dict()["candidate"],
        recompute.to_dict()["candidate"],
        discard.to_dict()["candidate"],
        plain_unknown.to_dict()["candidate"],
    }
    assert candidates == {"PRESERVE", "STRUCTURALIZE", "GENERATIZE", "RECOMPUTE", "DISCARD", "UNKNOWN"}
    invalid_candidate = fixture_assessment.to_dict()
    invalid_candidate["candidate"] = "DELETE"
    _expect_cps_error(
        lambda: PersistenceAssessment.from_dict(invalid_candidate),
        "C4-invalid-candidate-rejected",
        controls,
    )
    cases["C4"] = "PASS"

    # C5 — recompute needs explicit freshness semantics and preserves previous observation ref.
    rr = _recompute_ref()
    assert recompute.to_dict()["candidate"] == "RECOMPUTE"
    assert "cps-current" in recompute.to_dict()["required_preservations"]
    invalid_rr = rr.to_dict()
    invalid_rr["freshness_requirement"] = ""
    _expect_cps_error(
        lambda: RecomputationReference.from_dict(invalid_rr),
        "C5-recompute-without-freshness-rejected",
        controls,
    )
    cases["C5"] = "PASS"

    # C6 — CPS cannot grant authority.
    invalid_auth = fixture_assessment.to_dict()
    invalid_auth["authority"] = True
    _expect_cps_error(
        lambda: PersistenceAssessment.from_dict(invalid_auth),
        "C6-authority-true-rejected",
        controls,
    )
    cases["C6"] = "PASS"

    # C7 — factorization provenance and assessment references are bound.
    factorization = adapter.factorize(
        assessments=[generative],
        source_refs=["cps-generative"],
        anchors=["cps-generative"],
        structure=[{"relation": "depends_on", "source_ref": "cps-generative", "target_ref": "cps-decision"}],
        generators=[{"kind": "RECONSTRUCTION_RECIPE", "generator_ref": "synthetic://recipe/cps", "source_ref": "cps-generative"}],
        obligations=[{"kind": "ANCHOR_MUST_MATCH", "subject_ref": "cps-generative", "source_ref": "cps-generative"}],
        provenance_refs=["cps-generative"],
        recompute_refs=["rr-cps-current"],
        unresolved_refs=[],
    )
    assert factorization.to_dict()["source_refs"] == ["cps-generative"]
    tampered_factorization = factorization.to_dict()
    tampered_factorization["source_assessments"] = ["pa-unknown"]
    tampered_model = FactorizationProposal.from_dict(tampered_factorization)
    _expect_cps_error(
        lambda: validate_factorization_sources(tampered_model, [generative]),
        "C7-unknown-assessment-reference-rejected",
        controls,
    )
    _expect_cps_error(
        lambda: build_factorization_proposal(
            assessments=[generative],
            source_refs=["cps-generative"],
            anchors=["cps-generative"],
            structure=[{"relation": "depends_on", "target_ref": "cps-decision"}],
            generators=[],
            obligations=[],
            provenance_refs=["cps-generative"],
            recompute_refs=[],
            unresolved_refs=[],
        ),
        "C7-untraceable-factorized-component-rejected",
        controls,
    )
    cases["C7"] = "PASS"

    # C8 — generative seed must preserve anchor/equivalence completeness.
    eq = _eq_contract()
    seed = adapter.propose_seed(
        factorization=factorization,
        anchors=["cps-generative"],
        structure=factorization.to_dict()["structure"],
        generators=factorization.to_dict()["generators"],
        obligations=factorization.to_dict()["obligations"],
        provenance_refs=["cps-generative"],
        recomputation_refs=[rr],
        unresolved_components=[],
        equivalence_contract=eq,
    )
    _expect_cps_error(
        lambda: build_cognitive_seed_proposal(
            factorization=factorization,
            anchors=[],
            structure=factorization.to_dict()["structure"],
            generators=factorization.to_dict()["generators"],
            obligations=factorization.to_dict()["obligations"],
            provenance_refs=["cps-generative"],
            recomputation_refs=[rr],
            unresolved_components=[],
            equivalence_contract=eq,
        ),
        "C8-generative-seed-without-anchor-rejected",
        controls,
    )
    _expect_cps_error(
        lambda: build_cognitive_seed_proposal(
            factorization=factorization,
            anchors=["cps-generative"],
            structure=factorization.to_dict()["structure"],
            generators=[],
            obligations=factorization.to_dict()["obligations"],
            provenance_refs=["cps-generative"],
            recomputation_refs=[rr],
            unresolved_components=[],
            equivalence_contract=eq,
        ),
        "C8-factorization-generator-replacement-rejected",
        controls,
    )
    cases["C8"] = "PASS"

    # C9 — seed remains a sidecar; source memory is still addressable and byte-identical.
    assert records["cps-generative"].to_dict()["record_id"] == "cps-generative"
    assert records["cps-generative"].digest() == MemoryRecord.from_dict(records["cps-generative"].to_dict()).digest()
    assert seed.to_dict()["source_factorization"] == factorization.to_dict()["proposal_id"]
    controls.append("C9-source-memory-remains-addressable")
    cases["C9"] = "PASS"

    # C10 — equivalence is expressed through observation surfaces; token equality is forbidden, not a criterion.
    assert "TOKEN_EQUALITY" in eq.to_dict()["forbidden_equalities"]
    invalid_eq = eq.to_dict()
    invalid_eq["observation_surfaces"][0]["kind"] = "TOKEN_EQUALITY"
    _expect_cps_error(
        lambda: EquivalenceContract.from_dict(invalid_eq),
        "C10-token-equality-not-used-as-equivalence",
        controls,
    )
    cases["C10"] = "PASS"

    # C11 — no destructive/de-materialization surface exists.
    forbidden = {
        "commit", "delete", "tombstone", "rewrite", "archive_move", "update_store",
        "replace_record", "commit_factorization", "promote_seed",
    }
    public = {name for name in dir(CpsObservationAdapter) if not name.startswith("_")}
    assert forbidden.isdisjoint(public)
    controls.append("C11-forbidden-mutation-methods-absent")
    cases["C11"] = "PASS"

    # C12 — deterministic replay, and semantic input mutation changes fingerprint.
    replay = assess_record(records["cps-structure"], AssessmentContext(structural_dependency=True))
    assert replay.to_dict() == structural.to_dict()
    mutated = structural.to_dict()
    mutated["risk"] = "HIGH"
    mutated["assessment_id"] = "pa-mutated"
    mutated_model = PersistenceAssessment.from_dict(mutated)
    assert mutated_model.fingerprint() != structural.fingerprint()
    controls.append("C12-mutated-input-changes-fingerprint")
    cases["C12"] = "PASS"

    # C13 — every prior family contributes a negative control.
    families = {item.split("-", 1)[0] for item in controls}
    assert all(f"C{i}" in families for i in range(13))
    cases["C13"] = "PASS"

    return {
        "profile": PROFILE,
        "status": "PASS",
        "cases": cases,
        "controls": len(controls),
        "control_details": controls,
        "assessment_fingerprint": structural.fingerprint(),
        "factorization_fingerprint": factorization.fingerprint(),
        "seed_fingerprint": seed.fingerprint(),
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
