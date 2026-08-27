import json
import subprocess
import sys


def test_fresh_memory_core_acceptance_gate(tmp_path):
    output = tmp_path / "receipt.json"
    proc = subprocess.run(
        [sys.executable, "scripts/validate_fresh_memory_core.py", "--output", str(output)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["profile"] == "MLF-RM/0.1"
    assert receipt["status"] == "PASS"
    assert set(receipt["cases"]) >= {"A0", "A1", "A2", "A3", "A4", "A5", "A6"}
    assert all(receipt["cases"][case] == "PASS" for case in ["A0", "A1", "A2", "A3", "A4", "A5", "A6"])
    assert receipt["controls"] >= 6
    assert len(receipt["canonical_head"]) == 64
