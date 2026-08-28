from __future__ import annotations

import sys
from pathlib import Path


def _run() -> int:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    from mneme.claude_cli import main

    return main()


if __name__ == "__main__":
    raise SystemExit(_run())
