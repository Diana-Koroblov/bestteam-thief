"""The hardware probe behind the Step-0 declaration (TODO 6.3.1, M#24, FR-6.7).

The declaration is signed and feeds the computational-fairness weighting, so a
wrong value here is a false statement in the one artefact whose whole purpose is
to be believed without a referee.

Every test below is written against a fault the previous probe actually shipped,
found by reading a filed declaration from a real match:

    "gpu": "NVIDIA-SMI has failed because you do not have suffient permissions."
    "ram_gb": "unknown"
    "cpu_cores": 16          # the machine has 8

`nvidia-smi` was present as a leftover in `system32`, so the `shutil.which`
guard passed; the command then failed and its **error text became the GPU
name**, because nothing checked the return code.
"""

from __future__ import annotations

import subprocess

import pytest

from core.shared import hardware
from core.shared.hardware import UNKNOWN, Machine, probe


def _result(stdout: str, returncode: int = 0) -> subprocess.CompletedProcess:
    """A finished subprocess with the given output and status."""
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


# --- the return-code check --------------------------------------------------


def test_a_failed_command_contributes_nothing(monkeypatch) -> None:
    """🐛 **The bug, isolated.** A tool that fails still writes to stdout, and
    treating that text as an answer is how a permissions error became a GPU."""
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: _result("NVIDIA-SMI has failed because ...", 9)
    )
    assert hardware._run(["anything"]) == ""


def test_a_succeeding_command_is_read_normally(monkeypatch) -> None:
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _result("output", 0))
    assert hardware._run(["anything"]) == "output"


@pytest.mark.parametrize("boom", [OSError("no such binary"), subprocess.SubprocessError()])
def test_a_missing_or_broken_binary_is_not_an_exception(monkeypatch, boom) -> None:
    """**Degrade, never fail.** Refusing to play over an unreadable field would
    turn a reporting gap into a forfeit."""

    def explode(*_args, **_kwargs):
        raise boom

    monkeypatch.setattr(subprocess, "run", explode)
    assert hardware._run(["anything"]) == ""


# --- the GPU label ----------------------------------------------------------


def test_every_real_adapter_is_declared() -> None:
    """A discrete card beside an integrated one is a different competitor from
    the integrated one alone, and that difference is what the declaration is
    for."""
    label = hardware._gpu_label(["AMD Radeon RX 9070 XT", "AMD Radeon(TM) Graphics"])
    assert label == "AMD Radeon RX 9070 XT; AMD Radeon(TM) Graphics"


def test_a_fallback_driver_is_not_a_gpu() -> None:
    """Declaring the Microsoft basic adapter would understate a machine as badly
    as the NVIDIA string overstated it."""
    assert hardware._gpu_label(["Microsoft Basic Display Adapter"]) == "none"


def test_no_adapters_reads_none() -> None:
    assert hardware._gpu_label([]) == "none"


def test_duplicate_adapters_are_listed_once() -> None:
    assert hardware._gpu_label(["Radeon", "Radeon"]) == "Radeon"


# --- coercion ---------------------------------------------------------------


@pytest.mark.parametrize("value", [None, "", "  ", "sixteen", 0, -4])
def test_an_unreadable_count_is_unknown_not_a_guess(value) -> None:
    assert hardware._count(value) == UNKNOWN


def test_a_readable_count_is_an_int() -> None:
    assert hardware._count("8") == 8
    assert hardware._count(16) == 16


def test_bytes_become_gigabytes() -> None:
    assert hardware._gigabytes(33460293632) == 31.2


@pytest.mark.parametrize("value", [None, "", "lots"])
def test_unreadable_memory_is_unknown(value) -> None:
    assert hardware._gigabytes(value) == UNKNOWN


def test_whitespace_in_a_model_name_is_collapsed() -> None:
    """CIM pads some processor names; the declaration is compared byte for byte
    against the digest that sealed it."""
    assert hardware._text("  AMD   Ryzen 7  9700X  ") == "AMD Ryzen 7 9700X"


# --- the assembled machine --------------------------------------------------


def test_a_totally_silent_platform_still_produces_a_machine(monkeypatch) -> None:
    """Every field unknown, nothing raised — the match starts anyway."""
    monkeypatch.setattr(hardware, "_run", lambda *a, **k: "")
    monkeypatch.setattr(hardware.platform, "system", lambda: "Windows")
    built = probe()
    assert built.gpu == "none"
    assert built.cpu_model == UNKNOWN
    assert built.ram_gb == UNKNOWN


def test_windows_reads_cores_and_threads_apart(monkeypatch) -> None:
    """🐛 `os.cpu_count()` reports **logical** processors, and the field is
    called `cpu_cores`. A Ryzen 7 9700X was declared as a 16-core machine; it
    has 8. Under a weighting that rewards doing well on modest hardware,
    overstating the machine is the direction that costs us."""
    monkeypatch.setattr(hardware.platform, "system", lambda: "Windows")
    monkeypatch.setattr(
        hardware,
        "_run",
        lambda *a, **k: (
            '{"model":"AMD Ryzen 7 9700X 8-Core Processor","cores":8,"threads":16,'
            '"mhz":3800,"gpus":["AMD Radeon RX 9070 XT"],"ram":33460293632}'
        ),
    )
    built = probe()
    assert (built.cpu_cores, built.cpu_threads) == (8, 16)
    assert built.cpu_mhz == 3800
    assert built.ram_gb == 31.2
    assert built.gpu == "AMD Radeon RX 9070 XT"


def test_a_single_adapter_arrives_as_a_scalar(monkeypatch) -> None:
    """PowerShell's ConvertTo-Json collapses a one-element array, so both shapes
    reach the parser and neither may be assumed."""
    monkeypatch.setattr(hardware.platform, "system", lambda: "Windows")
    monkeypatch.setattr(hardware, "_run", lambda *a, **k: '{"gpus":"Radeon RX 9070 XT"}')
    assert probe().gpu == "Radeon RX 9070 XT"


def test_unparseable_probe_output_is_not_fatal(monkeypatch) -> None:
    monkeypatch.setattr(hardware.platform, "system", lambda: "Windows")
    monkeypatch.setattr(hardware, "_run", lambda *a, **k: "not json at all")
    assert isinstance(probe(), Machine)
