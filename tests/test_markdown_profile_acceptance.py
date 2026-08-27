import json
import subprocess
import sys


def test_memory_markdown_profile_acceptance_gate(tmp_path):
    output = tmp_path / "receipt.json"
    proc = subprocess.run(
        [sys.executable, "scripts/validate_memory_markdown_profile.py", "--output", str(output)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["profile"] == "MNEME-MD/0.1"
    assert receipt["status"] == "PASS"
    assert all(receipt["cases"][f"M{i}"] == "PASS" for i in range(9))
    assert receipt["controls"] >= 8
    assert len(receipt["profile_digest"]) == 64
