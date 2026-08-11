"""The Replay Viewer's model (TODO 7.5.1-7.5.3, T7.11, T7.12, M#20).

**One `TAMPERED` voids the match** — no appeal, no retrospective correction. So
the verdict has to be right about clean logs *and* specific about dirty ones,
and both are tested against genuinely sealed commitments rather than invented
digests.

The window itself is not tested: asserting on Tkinter geometry tests Tkinter.
What is tested is everything the window merely displays.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.crypto.commitment import seal
from core.report.artefacts import write
from core.report.match_log import build_log, build_step
from core.report.replay import (
    TAMPERED,
    VERIFIED_OK,
    ReplayError,
    ReplaySession,
    load_replay,
)


def sealed_log(count: int = 5) -> dict:
    """Return a genuinely sealed, clean log of *count* steps."""
    steps, nonces = [], {}
    for index in range(count):
        state = {"cop": [0, index], "thief": [3, 3], "step": index}
        locked = seal(state, "N", "truth")
        steps.append(
            build_step(index, locked.digest, state, locked.move, locked.intent, hint=f"h{index}")
        )
        nonces[str(index)] = locked.nonce
    return build_log("gid", 2, "cop", steps, nonces, outcome="survival")


# --- 7.5.2 / 7.5.3 the verdict ----------------------------------------------


def test_a_clean_log_reads_verified_ok() -> None:
    """**T7.11.** Green, and the required submission screenshot (7.25)."""
    session = ReplaySession(sealed_log())
    assert session.verdict == VERIFIED_OK
    assert session.result.passed
    assert "Verified OK" in session.describe()


def test_an_altered_move_reads_tampered_and_names_the_step() -> None:
    """**T7.12.** A verdict nobody can locate is one nobody can defend against."""
    payload = sealed_log()
    payload["steps"][3]["move"] = "S"

    session = ReplaySession(payload)
    assert session.verdict == TAMPERED
    assert session.result.failures[0][0] == 3
    assert not session.step_ok(3)
    assert session.step_ok(0)


def test_the_whole_log_is_audited_before_the_first_frame() -> None:
    """**Not lazily, as the cursor moves.**

    A viewer that verified only what somebody clicked through would show a
    green banner on a log whose forgery sits at step 30.
    """
    payload = sealed_log(40)
    payload["steps"][30]["nonce"] = "0" * 32

    session = ReplaySession(payload)
    assert session.cursor == 0, "nothing has been stepped through"
    assert session.verdict == TAMPERED


def test_a_step_verdict_is_recomputed_not_read_from_the_audit() -> None:
    """An ordering or duplication failure is about the log's *shape* and says
    nothing about whether that individual seal is genuine. Conflating them would
    point the viewer at the wrong row."""
    payload = sealed_log(3)
    payload["steps"][2]["step"] = 1  # duplicate number, but the seal is untouched

    session = ReplaySession(payload)
    assert not session.result.passed
    assert session.step_ok(2), "the seal itself still verifies"


# --- 7.5.1 stepping ---------------------------------------------------------


def test_the_cursor_walks_forward_and_back() -> None:
    session = ReplaySession(sealed_log(3))
    assert session.forward() == 1
    assert session.forward() == 2
    assert session.back() == 1
    assert session.current()["step"] == 1


def test_the_cursor_stops_at_both_ends() -> None:
    """Clamped rather than wrapped: a viewer that looped would make "is this the
    last step?" unanswerable from the screen."""
    session = ReplaySession(sealed_log(2))
    for _ in range(10):
        session.forward()
    assert session.cursor == 1
    for _ in range(10):
        session.back()
    assert session.cursor == 0


def test_an_empty_log_neither_crashes_nor_passes() -> None:
    """A log with no steps is a missing log, not a clean one."""
    session = ReplaySession(build_log("gid", 1, "cop", [], {}))
    assert session.current() is None
    assert session.total == 0
    assert session.verdict == TAMPERED
    assert session.forward() == 0


# --- loading ----------------------------------------------------------------


def test_it_loads_and_audits_a_log_off_disk(tmp_path: Path) -> None:
    target = write(sealed_log(), tmp_path, "log.json")
    assert load_replay(target).verdict == VERIFIED_OK


def test_a_non_ascii_hint_loads(tmp_path: Path) -> None:
    """Read as explicit UTF-8 bytes; a cp1252 console default would raise on a
    perfectly valid file (the rule from 6.5.2)."""
    payload = sealed_log(1)
    payload["steps"][0]["hint"] = "צפונה"
    target = write(payload, tmp_path, "log.json")
    assert load_replay(target).current()["hint"] == "צפונה"


def test_a_missing_file_says_so(tmp_path: Path) -> None:
    with pytest.raises(ReplayError, match="no log at"):
        load_replay(tmp_path / "absent.json")


def test_a_file_that_is_not_json_is_refused(tmp_path: Path) -> None:
    target = tmp_path / "log.json"
    target.write_text("this is not json", encoding="utf-8")
    with pytest.raises(ReplayError, match="not a readable JSON log"):
        load_replay(target)


def test_a_json_file_that_is_not_a_log_is_refused(tmp_path: Path) -> None:
    """A list parses as JSON and is still not a match log."""
    target = tmp_path / "log.json"
    target.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    with pytest.raises(ReplayError, match="not a match log"):
        load_replay(target)


def test_an_unverifiable_log_refuses_rather_than_showing_green(tmp_path: Path) -> None:
    """**A green banner over a file that could not be checked is the worst
    possible output** — worse than refusing to open it, because it looks like
    evidence."""
    payload = sealed_log(1)
    del payload["steps"][0]["claimed_digest"]
    target = write(payload, tmp_path, "log.json")
    with pytest.raises(ReplayError, match="not a replayable match log"):
        load_replay(target)


# --- the CLI entry point ----------------------------------------------------


def test_the_cli_verifies_a_log_without_a_display(tmp_path: Path, capsys) -> None:
    """**Headless on purpose.** One `TAMPERED` voids the match (7.24), which is
    not a verdict that should require a human to be looking at a window."""
    from core import __main__ as cli

    target = write(sealed_log(), tmp_path, "log.json")
    assert cli.main(["replay", str(target), "--headless"]) == 0
    assert "Verified OK" in capsys.readouterr().out


def test_the_cli_exit_code_carries_the_verdict(tmp_path: Path, capsys) -> None:
    """So a script or a CI job can act on it without parsing prose."""
    from core import __main__ as cli

    payload = sealed_log()
    payload["steps"][1]["intent"] = "lie"
    target = write(payload, tmp_path, "log.json")

    assert cli.main(["replay", str(target), "--headless"]) == 1
    assert "FAILED" in capsys.readouterr().out


def test_the_viewer_reaches_the_system_only_through_the_sdk(tmp_path: Path) -> None:
    """**7.5.4, X §4.1.** The facade the window actually imports."""
    from core.sdk.replay_sdk import VERIFIED_OK as SDK_OK
    from core.sdk.replay_sdk import load_replay as sdk_load

    target = write(sealed_log(), tmp_path, "log.json")
    assert sdk_load(target).verdict == SDK_OK


def walled_log() -> dict:
    """A clean log whose middle step seals a barrier (C-018).

    ⚠️ **`sealed_log` never places one, which is why the bug below survived.**
    A placement moves as `STAY` and carries `sealed_barrier_cell`; a helper that
    only ever walks the board exercises neither.
    """
    steps, nonces = [], {}
    for index in range(3):
        state = {"cop": [0, index], "thief": [3, 3], "step": index}
        wall = (5, 4) if index == 1 else None
        move = "STAY" if wall else "N"
        locked = seal(state, move, "truth", barrier_cell=wall)
        steps.append(
            build_step(
                index, locked.digest, state, locked.move, locked.intent,
                hint=f"h{index}", barrier_cell=wall, sealed_barrier=wall is not None,
            )
        )
        nonces[str(index)] = locked.nonce
    return build_log("gid", 2, "cop", steps, nonces, outcome="capture")


def test_a_sealed_barrier_step_is_not_marked_a_mismatch() -> None:
    """🐛 **The viewer contradicted its own banner on every walling turn.**

    `step_ok` re-hashed with `scent_digest` and without `sealed_barrier_cell`,
    so it rebuilt a payload the sealing peer never hashed. `verify_all` goes
    through `match_log.records`, which reads both — so the window showed a green
    `Verified OK` over a red `MISMATCH` on an honest log.

    That is the worst possible failure for this artefact: the screenshot of this
    window is a required submission deliverable (7.25) whose entire job is to
    prove integrity, and a placement moves as `STAY`, so the steps it accused
    were the Cop's most consequential ones.
    """
    session = ReplaySession(walled_log())
    assert session.verdict == VERIFIED_OK
    assert [session.step_ok(i) for i in range(session.total)] == [True, True, True]


def test_every_step_mark_agrees_with_the_whole_log_verdict() -> None:
    """**The general property, so the two paths cannot drift again.**

    They are deliberately separate computations — the banner audits shape as
    well as seals — but on a clean log they must not disagree about any step. A
    field added to one payload builder and not the other reappears here.
    """
    for payload in (sealed_log(), walled_log()):
        session = ReplaySession(payload)
        assert session.result.passed
        assert all(session.step_ok(i) for i in range(session.total))


def test_a_forged_barrier_cell_is_still_caught() -> None:
    """The fix must not become a blanket pass. Rewriting the walled cell after
    the fact is exactly the after-the-fact revision C-018 seals against."""
    payload = walled_log()
    payload["steps"][1]["sealed_barrier_cell"] = [0, 0]

    session = ReplaySession(payload)
    assert session.verdict == TAMPERED
    assert not session.step_ok(1)


def test_a_step_index_outside_the_log_is_not_ok() -> None:
    """The viewer clamps its cursor, but `step_ok` is public and must not raise
    for a caller that does not."""
    session = ReplaySession(sealed_log(2))
    assert not session.step_ok(-1)
    assert not session.step_ok(99)


def test_the_parsed_records_are_available_directly() -> None:
    """For anything that wants the audit input rather than the display."""
    session = ReplaySession(sealed_log(3))
    assert len(session.audit_records()) == 3
