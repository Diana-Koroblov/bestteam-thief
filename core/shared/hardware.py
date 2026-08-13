"""Reading what this machine actually is (TODO 6.3.1, M#24, FR-6.7).

Split from `system_info.py`, which now only assembles the declaration. The seam
is platform detail versus the shape of the signed payload: probing is a pile of
OS-specific commands that differ per machine, and the payload is a contract with
whoever reads the report months later.

🐛 **Why this exists at all.** The previous probe declared, on an AMD machine
with a Radeon RX 9070 XT and 31.2 GB of RAM:

    "gpu": "NVIDIA-SMI has failed because you do not have suffient permissions."
    "ram_gb": "unknown"
    "cpu_cores": 16          # a Ryzen 7 9700X has 8

Three separate faults. `nvidia-smi` is present on this machine as a leftover in
`system32`, so the `shutil.which` guard passed; the command then failed and its
**error text was returned as the GPU name**, because nothing checked the return
code. `wmic` no longer ships on Windows 11, so RAM silently degraded to
`"unknown"`. And `os.cpu_count()` reports *logical* processors under a field
named `cpu_cores`.

That output went into a **signed** Step-0 payload that feeds the computational-
fairness weighting. A declaration naming a GPU this machine does not have is not
a cosmetic bug — it is a false statement in the one artefact whose purpose is to
be believed without a referee (M#24).

**Everything still degrades rather than fails.** An unreadable field reports
`"unknown"` and the match proceeds; refusing to play over a missing CPU
frequency would turn a reporting gap into a forfeit. What is no longer permitted
is reporting a *wrong* value confidently.

No third-party dependency, as before: `psutil` would answer all of this in one
call and is one more thing to install correctly under deadline.
"""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
from dataclasses import dataclass

__all__ = ["Machine", "probe", "UNKNOWN"]

UNKNOWN = "unknown"

# Adapters that describe a fallback driver rather than a real card. Declaring
# one as *the* GPU would understate a machine as badly as the NVIDIA string
# overstated it.
_NOT_A_GPU = ("microsoft basic display", "remote display", "meta virtual")

# One CIM round trip for every field. `wmic` is gone from Windows 11; CIM is its
# supported replacement and is present on every Windows the project targets.
_PS_PROBE = (
    "$ErrorActionPreference='SilentlyContinue';"
    "$c=Get-CimInstance Win32_Processor|Select-Object -First 1;"
    "$v=@(Get-CimInstance Win32_VideoController|ForEach-Object{$_.Name});"
    "$s=Get-CimInstance Win32_ComputerSystem;"
    "@{model=$c.Name;cores=$c.NumberOfCores;threads=$c.NumberOfLogicalProcessors;"
    "mhz=$c.MaxClockSpeed;gpus=$v;ram=$s.TotalPhysicalMemory}|ConvertTo-Json -Compress"
)


@dataclass(frozen=True)
class Machine:
    """What we declare about this computer. Any field may be ``"unknown"``."""

    cpu_model: str = UNKNOWN
    cpu_cores: int | str = UNKNOWN
    cpu_threads: int | str = UNKNOWN
    cpu_mhz: int | str = UNKNOWN
    ram_gb: float | str = UNKNOWN
    gpu: str = UNKNOWN


def probe() -> Machine:
    """Return this machine's specification, by whatever route the OS allows."""
    if platform.system() == "Windows":
        return _windows()
    return _posix()


def _run(command: list[str], timeout: float = 15.0) -> str:
    """Run *command* and return stdout, or ``""`` on any failure.

    **The return code is checked**, unlike the probe this replaces. A tool that
    fails still writes to stdout, and treating that text as an answer is exactly
    how an NVIDIA permissions error became a declared GPU.
    """
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout if done.returncode == 0 else ""


def _windows() -> Machine:
    """Probe via CIM, in a single PowerShell call."""
    raw = _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS_PROBE])
    try:
        facts = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        facts = {}
    if not isinstance(facts, dict):
        facts = {}

    gpus = facts.get("gpus")
    # ConvertTo-Json collapses a one-element array to a scalar, so both shapes
    # arrive here and neither may be assumed.
    names = gpus if isinstance(gpus, list) else ([gpus] if gpus else [])
    return Machine(
        cpu_model=_text(facts.get("model")),
        cpu_cores=_count(facts.get("cores")),
        cpu_threads=_count(facts.get("threads")) or (os.cpu_count() or UNKNOWN),
        cpu_mhz=_count(facts.get("mhz")),
        ram_gb=_gigabytes(facts.get("ram")),
        gpu=_gpu_label(names),
    )


def _posix() -> Machine:
    """Probe via `/proc`, `sysconf` and `lspci`."""
    info = _cpuinfo()
    cores = _count(info.get("cpu cores")) or UNKNOWN
    return Machine(
        cpu_model=_text(info.get("model name")),
        # A container or a VM reports no `cpu cores` line at all; the logical
        # count is then the only honest answer available.
        cpu_cores=cores if cores != UNKNOWN else (os.cpu_count() or UNKNOWN),
        cpu_threads=os.cpu_count() or UNKNOWN,
        cpu_mhz=_count(str(info.get("cpu MHz", "")).split(".")[0]),
        ram_gb=_sysconf_gb(),
        gpu=_gpu_label(_lspci_names()),
    )


def _cpuinfo() -> dict[str, str]:
    """Return the first processor block of `/proc/cpuinfo` as a mapping."""
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return {}
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            fields.setdefault(key.strip(), value.strip())
    return fields


def _sysconf_gb() -> float | str:
    """Physical RAM in GB from `sysconf`, or ``"unknown"``."""
    try:
        return round(os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 1024**3, 1)
    except (AttributeError, ValueError, OSError):
        return UNKNOWN


def _lspci_names() -> list[str]:
    """Return VGA/3D controller descriptions from `lspci`, if it is installed."""
    return [
        line.split(":", 2)[-1].strip()
        for line in _run(["lspci"], timeout=5).splitlines()
        if re.search(r"VGA compatible controller|3D controller", line)
    ]


def _gpu_label(names: list) -> str:
    """Return the adapters worth declaring, or ``"none"``.

    **Every real adapter is listed, not just the first.** A machine with a
    discrete card beside an integrated one is a different competitor from a
    machine with only the integrated one, and the fairness weighting is the
    whole point of declaring hardware at all.
    """
    real = [
        str(name).strip()
        for name in names
        if str(name).strip() and not any(dull in str(name).lower() for dull in _NOT_A_GPU)
    ]
    return "; ".join(dict.fromkeys(real)) if real else "none"


def _text(value: object) -> str:
    """Collapse a probe result to a clean string, or ``"unknown"``."""
    text = str(value).strip() if value is not None else ""
    return " ".join(text.split()) or UNKNOWN


def _count(value: object) -> int | str:
    """Coerce a probe result to a positive int, or ``"unknown"``."""
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return UNKNOWN
    return number if number > 0 else UNKNOWN


def _gigabytes(value: object) -> float | str:
    """Convert a byte count to GB, or ``"unknown"``."""
    try:
        return round(int(str(value).strip()) / 1024**3, 1)
    except (TypeError, ValueError):
        return UNKNOWN
