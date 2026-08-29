from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _run() -> int:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    from mneme.canonical import canonical_json_bytes
    from mneme.claude_acceptance import validate_claude_global_memory

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--inject-effect")
    arguments = parser.parse_args()
    report = validate_claude_global_memory(
        Path(arguments.root),
        injected_effect=arguments.inject_effect,
    )
    payload = report.to_dict()
    encoded = canonical_json_bytes(payload) + b"\n"
    Path(arguments.output).write_bytes(encoded)
    sys.stdout.write(encoded.decode("utf-8"))
    return 0 if report.status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(_run())
