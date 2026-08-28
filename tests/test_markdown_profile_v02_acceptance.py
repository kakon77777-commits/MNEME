from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_memory_markdown_profile_v02_acceptance(tmp_path):
    proc = subprocess.run(
        [sys.executable, "scripts/validate_memory_markdown_profile_v02.py", "--output", str(tmp_path / "receipt.json")],
        cwd=ROOT,
        check=False,
    )
    assert proc.returncode == 0
