import json
import subprocess
import sys


def test_cps_acceptance_gate(tmp_path):
    output = tmp_path / "cps.json"
    proc = subprocess.run(
        [sys.executable, "scripts/validate_cognitive_persistence_semantics.py", "--output", str(output)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["profile"] == "MNEME-CPS/0.1"
    assert receipt["status"] == "PASS"
    assert all(receipt["cases"][f"C{i}"] == "PASS" for i in range(14))
    assert receipt["controls"] >= 13
