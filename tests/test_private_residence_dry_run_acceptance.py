import subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_private_residence_dry_run_acceptance(tmp_path):
    proc=subprocess.run([sys.executable,'scripts/validate_private_residence_two_pass_dry_run.py','--output',str(tmp_path/'receipt.json')],cwd=ROOT,check=False)
    assert proc.returncode==0


def test_public_acceptance_fixture_contains_traditional_chinese_utf8():
    fixture = ROOT / "fixtures" / "synthetic" / "private-residence-two-pass-memory.md"
    raw = fixture.read_bytes()
    text = raw.decode("utf-8")
    assert "合成測試" in text
    assert text.encode("utf-8") == raw
