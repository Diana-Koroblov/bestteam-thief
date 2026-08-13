"""What this machine is, declared at Step-0 (TODO 6.3.1, M#24, FR-6.7).

The rulebook requires each peer to declare its hardware before the first move,
and the reason is fairness rather than curiosity: a match between a laptop and a
GPU workstation is a different contest, and the declaration is what lets the
grader see which one happened. FR-6.7 names the fields — OS, CPU cores and
frequency, RAM, GPU.

This module assembles the declaration; `core/shared/hardware.py` does the
probing, and its docstring records the three faults that made the old output
wrong on the machine that plays our matches.

**Cores and threads are declared separately, and that is the point.** A field
called `cpu_cores` holding the logical processor count reports a Ryzen 7 9700X
as a 16-core machine. It has 8. Under a weighting that rewards doing well on
modest hardware, overstating the machine is the direction that costs us — and
either number alone loses information a reader needs, so both are declared.

**Everything degrades rather than fails.** An unknown field reports `"unknown"`
and the game proceeds. What is not permitted is a confident wrong answer.
"""

from __future__ import annotations

import platform
from functools import lru_cache

from core.shared.hardware import UNKNOWN, Machine, probe

__all__ = ["describe", "gpu_name", "total_ram_gb", "cpu_summary"]


@lru_cache(maxsize=1)
def _machine() -> Machine:
    """Probe once per process.

    Cached for the reason `step_zero.commit_hash` is: this shells out to CIM,
    Step-0 is built per sub-game, and — more importantly — what we declare must
    be the *same bytes* all series. A function that re-probes is a function that
    can answer differently after the digest was signed.
    """
    return probe()


def total_ram_gb() -> float | str:
    """Physical RAM in GB, or ``"unknown"``."""
    return _machine().ram_gb


def gpu_name() -> str:
    """The GPU model(s), or ``"none"`` when there is not one we can see.

    **"none" is a real answer, not a failure.** A machine with no discrete card
    plays anyway; the declaration records that difference rather than treating
    it as an error. An *error message* is not a real answer, which is what the
    return-code check in `hardware._run` now enforces.
    """
    return _machine().gpu


def cpu_summary() -> str:
    """One line naming the processor, for the setup check and the scoreboard."""
    cpu = _machine()
    speed = f" @ {cpu.cpu_mhz} MHz" if cpu.cpu_mhz != UNKNOWN else ""
    return f"{cpu.cpu_model} ({cpu.cpu_cores}C/{cpu.cpu_threads}T){speed}"


def describe() -> dict[str, object]:
    """Return this machine's declaration.

    Sorted, JSON-safe primitives only: this dictionary goes inside a signed
    payload, so anything that serialises differently on two machines would break
    the digest comparison.
    """
    cpu = _machine()
    return {
        "os": f"{platform.system()} {platform.release()}".strip() or UNKNOWN,
        "python": platform.python_version(),
        "machine": platform.machine() or UNKNOWN,
        "cpu_model": cpu.cpu_model,
        "cpu_cores": cpu.cpu_cores,
        "cpu_threads": cpu.cpu_threads,
        "cpu_mhz": cpu.cpu_mhz,
        "ram_gb": cpu.ram_gb,
        "gpu": cpu.gpu,
    }
