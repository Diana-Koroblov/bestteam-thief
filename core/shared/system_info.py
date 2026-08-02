"""What this machine is, declared at Step-0 (TODO 6.3.1, M#24).

The rulebook requires each peer to declare its hardware before the first move,
and the reason is fairness rather than curiosity: a match between a laptop and a
GPU workstation is a different contest, and the declaration is what lets the
grader see which one happened.

**Everything here degrades rather than fails.** A missing GPU, an unreadable
`/proc`, a Windows API that answers differently than expected — none of those
should stop a match starting. An unknown field reports `"unknown"` and the game
proceeds; refusing to play because we could not read a CPU frequency would turn
a cosmetic gap into a forfeit.

No third-party dependency. `psutil` would report more, but it is one more thing
to install correctly on two machines under deadline, and the fields the rulebook
asks for are all reachable from the standard library.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess

__all__ = ["describe", "gpu_name", "total_ram_gb"]

UNKNOWN = "unknown"


def total_ram_gb() -> float | str:
    """Physical RAM in GB, or ``"unknown"``.

    Tries the POSIX `sysconf` pair first, then Windows' `wmic`. Both are absent
    often enough that the fallback is the expected path, not an edge case.
    """
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return round(pages * page_size / 1024**3, 1)
    except (AttributeError, ValueError, OSError):
        pass

    try:
        output = subprocess.run(
            ["wmic", "computersystem", "get", "TotalPhysicalMemory"],
            capture_output=True, text=True, timeout=5, check=False,
        ).stdout
        digits = "".join(c for c in output if c.isdigit())
        return round(int(digits) / 1024**3, 1) if digits else UNKNOWN
    except (OSError, ValueError):
        return UNKNOWN


def gpu_name() -> str:
    """The GPU model, or ``"none"`` when there is not one we can see.

    **"none" is a real answer, not a failure.** Diana's machine has no GPU and
    plays anyway; the declaration is meant to record that difference, not to
    treat it as an error.
    """
    if shutil.which("nvidia-smi") is None:
        return "none"
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5, check=False,
        )
        first = result.stdout.strip().splitlines()
        return first[0].strip() if first else "none"
    except (OSError, subprocess.SubprocessError):
        return "none"


def describe() -> dict[str, object]:
    """Return this machine's declaration.

    Sorted, JSON-safe primitives only: this dictionary goes inside a signed
    payload, so anything that serialises differently on two machines would break
    the digest comparison.
    """
    return {
        "os": f"{platform.system()} {platform.release()}".strip() or UNKNOWN,
        "python": platform.python_version(),
        "machine": platform.machine() or UNKNOWN,
        "cpu_cores": os.cpu_count() or UNKNOWN,
        "ram_gb": total_ram_gb(),
        "gpu": gpu_name(),
    }
