"""The advanced Thief against the baseline, in real sub-games (TODO 8.2.1, 8.2.6).

8.2.1's DoD is *"beats the baseline thief"* and 8.2.6's is an ablation, so both
are measurements rather than arguments and both are made on the engine a graded
match runs on.

**Survival rate is the metric here, and it has signal.** The Cop's A/B had to fall
back on time-to-capture because both Cops caught the baseline Thief every time;
the reverse is not true. The baseline Thief survives **0 of 48** openings against
either Cop, so anything above zero is a real gain and the number is not saturated.

Measured 05/08 over 48 openings, `survival_threshold = 35`, **after** the C-006b
barrier-timing fix::

                        baseline thief      advanced thief
    baseline cop        0/48, 14.67 steps   46/48, 34.38 steps
    advanced cop        0/48,  8.17 steps   40/48, 30.42 steps

⚠️ **Sample size is not a formality here.** The false-anchor ablation came out
12/16 → 16/16 on a 16-opening sweep and **40/48 → 37/48** on the full 48. The
narrow set happened to hold exactly the games the tactic fixes and none it breaks,
and it would have had us adopt a tactic that loses ground. The suite runs the
16-opening version as a fast regression tripwire; the 48-opening numbers above are
the evidence, and they are what `docs/TODO.md` records.

The bottom-right cell moved from 44/48 to 40/48 when the barrier-timing defect
was fixed — four sub-games the Cop had earned and the engine was dropping. Every
number here post-dates that fix.
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

OPENINGS = [((row, col), (6 - row, 6 - col)) for row in range(0, 7, 2) for col in range(0, 7, 2)]


def play(thief_class, cop_class) -> list:
    """Play every opening with *thief_class* against *cop_class*."""
    return [
        play_sub_game(cop_class(), thief_class(), RULES, QUOTA, GameState(cop=start, thief=flee))
        for start, flee in OPENINGS
    ]


def survivals(games: list) -> int:
    """How many sub-games the Thief lasted out."""
    return sum(1 for game in games if game.outcome.verdict is Verdict.SURVIVAL)


@pytest.fixture(scope="module")
def results() -> dict:
    """Both Thieves against both Cops over the same openings."""
    from police.advanced import AdvancedCop
    from police.brain import PoliceBrain
    from thief.advanced import AdvancedThief
    from thief.brain import ThiefBrain

    return {
        (thief, cop): play(thief_class, cop_class)
        for thief, thief_class in (("baseline", ThiefBrain), ("advanced", AdvancedThief))
        for cop, cop_class in (("baseline", PoliceBrain), ("advanced", AdvancedCop))
    }


def test_the_baseline_thief_survives_nothing(results: dict) -> None:
    """The floor, and the reason survival rate is the honest metric: it starts
    at zero, so it cannot saturate the way the Cop's win rate did."""
    assert survivals(results[("baseline", "baseline")]) == 0
    assert survivals(results[("baseline", "advanced")]) == 0


def test_it_beats_the_baseline_against_the_baseline_cop(results: dict) -> None:
    """8.2.1's DoD, stated plainly."""
    assert survivals(results[("advanced", "baseline")]) > survivals(
        results[("baseline", "baseline")]
    )


def test_it_survives_our_own_advanced_cop_most_of_the_time(results: dict) -> None:
    """The harder half, and the one that matters for the league: the Cop it is
    running from is the best one we have."""
    assert survivals(results[("advanced", "advanced")]) >= len(OPENINGS) * 0.7


def test_a_better_cop_is_still_a_harder_cop(results: dict) -> None:
    """A sanity check on both brains at once. If the advanced Cop were not
    harder to escape than the baseline, one of the two A/Bs would be measuring
    something other than what it claims."""
    advanced = results[("advanced", "advanced")]
    baseline = results[("advanced", "baseline")]
    assert sum(g.steps for g in advanced) <= sum(g.steps for g in baseline)


def test_the_baseline_thief_is_unchanged_and_still_a_floor(results: dict) -> None:
    """Every claim above is relative to it, and a floor edited to flatter the
    thing measured against it is not a floor."""
    assert all(game.steps > 0 for game in results[("baseline", "baseline")])


def test_the_false_anchor_is_shipped_off(results: dict) -> None:
    """**8.2.6's verdict, pinned.** Adopted only if it wins — it did not, so the
    default must stay False and a later edit has to argue with the ablation."""
    from thief.advanced import AdvancedThief

    assert AdvancedThief().anchor.enabled is False
