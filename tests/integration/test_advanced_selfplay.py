"""The advanced Cop against the baseline, in real sub-games (TODO 8.1.1).

8.1.1's DoD is *"beats the baseline cop"*, and that is a measurement rather than
an argument, so it is made here on the same engine a graded match runs on.

**Why sixteen openings and not a hundred games.** Both brains are deterministic
and the rules are deterministic, so a hundred sub-games from the shipped opening
would be one sub-game reported a hundred times — a batch size that looks like
evidence and is not. Varying the opening instead produces sixteen genuinely
different games, which is the honest way to get a distribution out of two
deterministic players. The seeded randomisation that would let a batch mean
something is TODO 8.3.1, and until it lands, sample size here is a lie.

**What this cannot show.** The baseline Thief is caught in every opening by both
Cops, so a *win rate* saturates at 1.0 and measures nothing. What separates them
is how long it takes, and that is what is asserted. A win-rate comparison worth
making needs the advanced Thief from 8.2 to lose to.

Measured 05/08, sixteen openings each::

    baseline  16/16 captures  mean 17.75 steps   0 barriers  0 separations
    advanced  16/16 captures  mean  9.00 steps  12 barriers  0 separations
"""

from __future__ import annotations

import pytest

from core.domain.board import Board
from core.domain.game_state import GameState
from core.domain.rules import Rules, Verdict
from core.runtime.selfplay import play_sub_game
from tests.paths import PRESENT_ROLES

pytestmark = pytest.mark.skipif(
    "police" not in PRESENT_ROLES or "thief" not in PRESENT_ROLES,
    reason="a published repository ships one role; self-play needs both (ADR-001)",
)

BOARD = Board(grid_size=7)
RULES = Rules(board=BOARD, survival_threshold=35)
QUOTA = 14

# Mirrored openings across the board, so neither brain is measured from one
# lucky corner. Sixteen distinct games, every one reproducible.
OPENINGS = [((row, col), (6 - row, 6 - col)) for row in range(0, 7, 2) for col in range(0, 7, 2)]


def play(cop_class) -> list:
    """Play every opening with *cop_class* against the baseline Thief."""
    from thief.brain import ThiefBrain

    return [
        play_sub_game(cop_class(), ThiefBrain(), RULES, QUOTA, GameState(cop=start, thief=flee))
        for start, flee in OPENINGS
    ]


@pytest.fixture(scope="module")
def results() -> dict:
    """Both Cops over the same sixteen openings."""
    from police.advanced import AdvancedCop
    from police.brain import PoliceBrain

    return {"baseline": play(PoliceBrain), "advanced": play(AdvancedCop)}


def mean_steps(games: list) -> float:
    """Average turns to a terminal state."""
    return sum(game.steps for game in games) / len(games)


def test_the_advanced_cop_captures_in_every_opening(results: dict) -> None:
    """It may not lose ground the baseline holds."""
    captures = sum(1 for game in results["advanced"] if game.outcome.verdict is Verdict.CAPTURE)
    assert captures == len(OPENINGS)


def test_it_captures_faster_than_the_baseline(results: dict) -> None:
    """The measurable edge. Steps are the scarce resource — a Thief that has not
    been caught by step 35 has won, so time to capture *is* the margin."""
    assert mean_steps(results["advanced"]) < mean_steps(results["baseline"])


def test_it_is_faster_in_the_large_and_not_by_one_lucky_opening(results: dict) -> None:
    """A mean can be carried by a single outlier. This is the distribution."""
    faster = sum(
        1
        for advanced, baseline in zip(results["advanced"], results["baseline"], strict=True)
        if advanced.steps <= baseline.steps
    )
    assert faster >= len(OPENINGS) * 0.7


def test_the_advanced_cop_never_walls_itself_away_from_the_thief(results: dict) -> None:
    """**TODO 3.5.4 and 8.QG.4: this must be 0.**

    Self-separation is not a weak result, it is a forfeited sub-game — barriers
    are permanent and the Thief simply waits out the clock. No other number on
    the table matters until this one is zero.
    """
    assert sum(game.cop_separations for game in results["advanced"]) == 0


def test_the_baseline_is_unchanged_and_still_a_floor(results: dict) -> None:
    """Every claim above is relative to the baseline, and a floor that has been
    edited to flatter the thing measured against it is not a floor."""
    assert all(game.barriers_placed == 0 for game in results["baseline"])
    assert mean_steps(results["baseline"]) > 0


def test_barriers_are_actually_spent_in_play(results: dict) -> None:
    """The placement path runs in real games, not only in unit tests.

    Worth asserting on its own. Before the capture-versus-stranding fix in
    `barrier_policy` this number was **zero** across all sixteen openings — the
    separation guard vetoed every wall that mattered, and the Cop still won, so
    nothing about the result looked wrong. A strategy whose most expensive
    subsystem never executes is a subsystem that will first execute in a graded
    match.
    """
    assert sum(game.barriers_placed for game in results["advanced"]) > 0


def test_the_quota_is_never_overspent(results: dict) -> None:
    """Appendix F allows 14. Walls are permanent, so an off-by-one here is not
    a warning, it is a board that cannot be un-built."""
    assert all(game.barriers_placed <= QUOTA for game in results["advanced"])
