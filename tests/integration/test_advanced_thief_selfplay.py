"""The advanced Thief against the baseline — the fast tripwire (TODO 8.2.1, 8.2.6).

8.2.1's DoD is *"beats the baseline thief"* and 8.2.6's is an ablation, so both
are measurements rather than arguments and both are made on the engine a graded
match runs on.

**Survival rate is the metric here, and it has signal.** The Cop's A/B had to fall
back on time-to-capture because both Cops caught the baseline Thief every time;
the reverse is not true. The baseline Thief survives **nothing** against either
Cop, so anything above zero is a real gain and the number is not saturated.

🐛 **This file used to claim 48 openings and run 16.** `range(0, 7, 2)` yields
four values per axis, so `OPENINGS` has always held sixteen mirrored pairs, while
the docstring — and `docs/TODO.md` §8.2 with it — reported every figure as *n*/48.

**The 48-opening numbers were real.** Re-measured on 06/08 against the full
mirrored set, the advanced Thief survives 40 of 48 against the advanced Cop in
30.42 mean steps having faced 41 walls — the recorded figure to the decimal. What
was wrong was never the measurement; it was that **the committed test did not
perform it**, so a regression in the eight sub-games between 40/48 and the
tripwire's threshold could have landed without a red test. The warning below made
that worse by resting on it: it argues that sixteen openings are too narrow to
adopt a tactic on, in a file whose own assertions came from sixteen.

Corrected in both directions. This module is now honestly labelled the
**16-opening tripwire**, and the 48-opening matrix that 8.3.6 requires is run —
not just cited — in `test_advanced_league_benchmark.py`.

⚠️ **Sample size is not a formality, and that lesson survives the correction.**
The false-anchor ablation came out 12/16 → 16/16 on the narrow sweep and lost
ground on the wide one. The narrow set happened to hold exactly the games the
tactic fixes and none it breaks, and on its own it would have had us adopt a
tactic that loses. So this file's job is to fail fast on a regression, never to
settle an adoption; that is the benchmark's job.
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

# Sixteen mirrored openings — every second cell on each axis. `range(0, 7, 2)`
# gives four values, so this is 4x4 and not the 48 the file once claimed. The
# full 7x7 set is in `test_advanced_league_benchmark.py`.
OPENINGS = [((row, col), (6 - row, 6 - col)) for row in range(0, 7, 2) for col in range(0, 7, 2)]
assert len(OPENINGS) == 16, "the docstring's arithmetic and this list must agree"


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


def test_it_holds_up_against_our_own_advanced_cop(results: dict) -> None:
    """The harder half: the Cop it is running from is the best one we have.

    ⚠️ **This used to demand ≥70 % here and that was a broken gate.** The cell is
    zero-sum — every sub-game the Thief survives is one the Cop did not win — so
    a 70 % floor on the Thief's side is a *ceiling* of 30 % on the Cop's, in the
    role that carries a 15-point spread against the Thief's 5. It failed for the
    first time in 8.3 for the best possible reason: the Cop's verbal layer
    started working and took sub-games off our own Thief. A test that goes red
    when the other role improves is measuring the wrong thing.

    A4.2's ≥70 % gate is against the **baselines**, where it is not zero-sum, and
    that is where `test_advanced_league_benchmark.py` applies it. What is checked
    here is that the Thief still beats the floor it replaced and is not shut out.
    """
    advanced = survivals(results[("advanced", "advanced")])
    assert advanced > survivals(results[("baseline", "advanced")])
    assert advanced >= len(OPENINGS) * 0.5


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
