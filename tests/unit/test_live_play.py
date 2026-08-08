"""The wiring that turns a shipped brain into a peer at a live match (TODO 9.2).

Two things are worth testing without a network, and they are the two that were
wrong when the command was first run against a real opponent:

* which sub-games *this* repository plays, given a negotiated split, and
* that the board is reopened exactly once per sub-game.

The second is not a style point. `start_sub_game` clears every inbox keyed by
step number; run it a second time after the opponent has committed and their
commit is gone, their reveal is refused as unsealed, and a sub-game neither side
played wrong is scored a technical loss. That bug survived the in-process suite
— where nothing can arrive between two synchronous calls — and appeared on the
first two-process run.
"""

from __future__ import annotations

import pytest

from core.cli_play import plan_for
from core.protocol.schemas import Role
from core.runtime.live import reopen


class _Runtime:
    """A runtime that only counts resets. `start_sub_game` is what matters here."""

    def __init__(self) -> None:
        self.opened: list[int] = []

    def start_sub_game(self, sub_game: int = 1) -> None:
        self.opened.append(sub_game)


class TestPlanFor:
    """Which of the six sub-games this process is responsible for."""

    def test_cop_repository_opens_the_series(self) -> None:
        """Holding Cop in the first block means sub-games 1-3."""
        plan = plan_for("3-3", Role.COP, 6, Role.COP)
        assert [number for number, _ in plan] == [1, 2, 3]
        assert {role for _, role in plan} == {Role.COP}

    def test_thief_repository_plays_the_other_half(self) -> None:
        """The same negotiated term hands our Thief process sub-games 4-6.

        Both of our processes are given the identical ``first``; the filter is
        what stops them both trying to open the series.
        """
        assert [n for n, _ in plan_for("3-3", Role.COP, 6, Role.THIEF)] == [4, 5, 6]

    def test_the_opponent_mirrors_us(self) -> None:
        """Their Thief meets our Cop, because they were told they open as Thief.

        The C-011 failure this guards: two teams that each derive ``first`` from
        the role they happen to hold build mirror-image plans and meet
        Cop-on-Cop in sub-game one.
        """
        ours = plan_for("3-3", Role.COP, 6, Role.COP)
        theirs = plan_for("3-3", Role.THIEF, 6, Role.THIEF)
        assert [n for n, _ in ours] == [n for n, _ in theirs]

    def test_alternating_split(self) -> None:
        """More than two blocks alternate; ``1-1-1-1-1-1`` swaps every sub-game."""
        assert [n for n, _ in plan_for("1-1-1-1-1-1", Role.COP, 6, Role.COP)] == [1, 3, 5]

    def test_a_split_that_does_not_cover_the_series_is_refused(self) -> None:
        """Loud, because a plan missing a sub-game is found only after it is played."""
        with pytest.raises(ValueError, match="covers 4 sub-games"):
            plan_for("2-2", Role.COP, 6, Role.COP)


class TestReopen:
    """The reset that must happen once, and must not happen twice."""

    def test_reopens_each_sub_game_once(self) -> None:
        """A second call for the same sub-game does nothing at all."""
        runtime = _Runtime()
        prepare = reopen(runtime, set())
        prepare(1)
        prepare(1)
        assert runtime.opened == [1]

    def test_the_state_is_shared_between_callers(self) -> None:
        """Preparing before the server starts must suppress the build-time reset.

        Two callers hold their own closure over one `prepared` set: the command
        prepares the opening board before anything can be received, and
        `driver_factory` would otherwise clear it again at the moment the
        opponent's first commit has already landed.
        """
        runtime, prepared = _Runtime(), set()
        reopen(runtime, prepared)(1)
        reopen(runtime, prepared)(1)
        assert runtime.opened == [1]

    def test_later_sub_games_still_reopen(self) -> None:
        """Idempotence is per sub-game, not a one-shot latch."""
        runtime = _Runtime()
        prepare = reopen(runtime, set())
        for sub_game in (1, 1, 2, 2, 3):
            prepare(sub_game)
        assert runtime.opened == [1, 2, 3]
