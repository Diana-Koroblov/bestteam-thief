"""Watching a match without endangering it (TODO 7.4.1, M#8, M#35).

`--gui` was a flag on the `peer` subcommand and a dead end there: it opened the
window and returned without playing. So the belief-map capture Ch. 9.4 calls an
absolute requirement could only ever be taken at step 0 — a uniform prior, every
cell at peak intensity, a flat wash of red that shows a working renderer and
nothing at all about belief.

Wiring it into a live match puts a window next to a graded series, and these
tests are about the ways that could go wrong rather than about pixels. No test
here opens a real window; `LiveGui` is replaced, because a suite that needed a
display could not run in CI.
"""

from __future__ import annotations

import argparse
import threading

import pytest

from core import cli_gui


class FakeSdk:
    """Only what the host is allowed to touch."""

    def __init__(self) -> None:
        self.role = type("Role", (), {"value": "cop"})()
        self.ui_cell_pixels = 64
        self.asked = 0

    def gui_state(self, locked: bool = False) -> str:
        self.asked += 1
        return "frame"


def _args() -> argparse.Namespace:
    return argparse.Namespace(opponent="https://them.ngrok-free.dev/mcp", gui=True)


@pytest.fixture
def window(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Replace the window with a record of how it was built and when it closed."""
    seen: dict = {}

    class FakeGui:
        def __init__(self, provider, cell_pixels=64, title="", keep_open=None) -> None:
            seen.update(provider=provider, cell_pixels=cell_pixels,
                        title=title, keep_open=keep_open)

        def run(self) -> None:
            seen["frames"] = 0
            while seen["keep_open"]():
                seen["frames"] += 1

    monkeypatch.setattr("core.ui.live_gui.LiveGui", FakeGui)
    return seen


def test_the_match_result_is_what_the_command_returns(
    monkeypatch: pytest.MonkeyPatch, window: dict
) -> None:
    """`--gui` changes what is on screen and nothing about what the command means.

    A script that reads the exit code must not have to know whether a human was
    watching — a refused handshake is exit 1 either way.
    """
    async def refused(*args: object) -> int:
        return 1

    monkeypatch.setattr("core.cli_play._run", refused)
    assert cli_gui.play_with_window(FakeSdk(), None, _args(), [], set()) == 1


def test_the_window_closes_itself_when_the_match_ends(
    monkeypatch: pytest.MonkeyPatch, window: dict
) -> None:
    """Otherwise a finished match leaves a dead board waiting on a human.

    `keep_open` is the worker's own liveness, so the last frame drawn is the
    position the series actually ended in.
    """
    async def played(*args: object) -> int:
        return 0

    monkeypatch.setattr("core.cli_play._run", played)
    assert cli_gui.play_with_window(FakeSdk(), None, _args(), [], set()) == 0
    assert window["frames"] > 0, "the window never drew anything"
    assert not window["keep_open"](), "it should stop asking once the match is over"


def test_closing_the_window_does_not_forfeit_the_match(
    monkeypatch: pytest.MonkeyPatch, window: dict
) -> None:
    """**The trap this must never be.**

    A display whose close button abandons a series mid-sub-game leaves the
    opponent playing against a peer that has quit — three technical losses, a
    report that contradicts theirs, and 0 for both teams under M#35. So the
    worker is not a daemon and is joined after the window goes.
    """
    started = threading.Event()
    finished = threading.Event()

    async def slow(*args: object) -> int:
        started.set()
        finished.wait(5.0)
        return 0

    class ClosesImmediately:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def run(self) -> None:
            started.wait(5.0)  # the human shuts the window mid-match
            finished.set()

    monkeypatch.setattr("core.cli_play._run", slow)
    monkeypatch.setattr("core.ui.live_gui.LiveGui", ClosesImmediately)

    assert cli_gui.play_with_window(FakeSdk(), None, _args(), [], set()) == 0
    assert finished.is_set()


def test_a_display_that_cannot_open_never_stops_the_match(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Tkinter is absent on a headless box, and the match is the deliverable.

    Losing a booked fixture because a window would not open would be the wrong
    trade by a wide margin.
    """
    async def played(*args: object) -> int:
        return 0

    class Refuses:
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise RuntimeError("no display name and no $DISPLAY environment variable")

    monkeypatch.setattr("core.cli_play._run", played)
    monkeypatch.setattr("core.ui.live_gui.LiveGui", Refuses)

    assert cli_gui.play_with_window(FakeSdk(), None, _args(), [], set()) == 0
    assert "could not open" in capsys.readouterr().out


def test_the_window_is_handed_local_truth_and_never_the_board(window: dict) -> None:
    """**M#9 is disqualification, so the wiring is asserted, not trusted.**

    `gui_state` is built from an `Observation` and has no field for the
    opponent's position; `board_view` carries both true positions and exists for
    self-play. The host must reach for the first by name.
    """
    monkey_sdk = FakeSdk()

    async def played(*args: object) -> int:
        return 0

    with pytest.MonkeyPatch().context() as patch:
        patch.setattr("core.cli_play._run", played)
        cli_gui.play_with_window(monkey_sdk, None, _args(), [], set())

    assert window["provider"] == monkey_sdk.gui_state
    assert not hasattr(window["provider"], "board_view")
