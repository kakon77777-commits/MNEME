from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def create_windows_junction(link: Path, target: Path) -> None:
    if os.name != "nt":
        raise RuntimeError("Windows junction helper called on a non-Windows host")
    executable = shutil.which("powershell") or shutil.which("pwsh")
    if executable is None:
        raise RuntimeError("PowerShell is required for the Windows junction control")
    environment = os.environ.copy()
    environment["MNEME_JUNCTION_LINK"] = str(link)
    environment["MNEME_JUNCTION_TARGET"] = str(target)
    command = (
        "$ErrorActionPreference='Stop'; "
        "New-Item -ItemType Junction "
        "-Path $env:MNEME_JUNCTION_LINK "
        "-Target $env:MNEME_JUNCTION_TARGET | Out-Null"
    )
    result = subprocess.run(
        [executable, "-NoProfile", "-NonInteractive", "-Command", command],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert link.exists()
