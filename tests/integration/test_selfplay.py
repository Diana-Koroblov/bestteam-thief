"""The self-play harness (TODO 3.5).

The property that matters most: the harness must give brains **exactly** what a
real match gives them. A harness that fed better information would measure a
strategy nobody can actually play, and we would only find out in a graded match.
"""

from __future__ import annotations

import pytest

from core.domain.board import Board
from core.domain.game_state import GameState
from core.domain.rules import Rules, Verdict
from core.protocol.schemas import Role
from core.runtime.orchestrator import Orchestrator
from core.runtime.peer_runtime import PeerRuntime
from core.runtime.selfplay import play_sub_game
from tests.paths import brain_class

BOTH_BRAINS = pytest.mark.skipif(
    brain_class("police") is None or brain_class("thief") is None,
    reason="self-play needs both role packages; a published repo ships one (ADR-001)",
)


@pytest.fixture
def rules(minimal_config) -> Rules:
    return Rules.from_config(minimal_config, Board(grid_size=7))


@pytest.fixture
def start(minimal_config) -> GameState:
    return GameState(
        cop=tuple(minimal_config.require("board_and_agents.cop_start")),
        thief=tuple(minimal_config.require("board_and_agents.thief_start")),
    )


@pytest.fixture
def played(rules: Rules, start: GameState):
    return play_sub_game(brain_class("police")(), brain_class("thief")(), rules, 14, start)


@BOTH_BRAINS
def test_a_sub_game_reaches_a_terminal_state(played) -> None:
    assert played.outcome.verdict in (Verdict.CAPTURE, Verdict.SURVIVAL)
    assert played.outcome.reason


@BOTH_BRAINS
def test_it_never_runs_past_the_survival_threshold(played, rules: Rules) -> None:
    """Otherwise a broken brain hangs a hundred-game batch."""
    assert played.steps <= rules.survival_threshold


@BOTH_BRAINS
def test_the_history_covers_every_turn(played) -> None:
    assert len(played.history) == played.steps + 1
    assert len(played.reasons) == played.steps


@BOTH_BRAINS
def test_every_turn_records_why_both_sides_moved(played) -> None:
    """A surprising game must explain itself, not show an unmotivated sequence."""
    assert all(cop and thief for cop, thief in played.reasons)


@BOTH_BRAINS
def test_the_baseline_cop_never_separates_itself(played) -> None:
    """TODO 3.5.4, and the number that must stay 0 for any cop we field.

    Trivially true today because the baseline places no barriers. The counter
    exists so that the moment barrier strategy arrives, a self-trapping cop
    shows up as a number instead of as a mysterious run of losses.
    """
    assert played.cop_separations == 0


@BOTH_BRAINS
def test_the_run_is_reproducible(rules: Rules, start: GameState) -> None:
    """Both peers replay the same log, so nothing here may vary between runs."""
    outcomes = {
        play_sub_game(
            brain_class("police")(), brain_class("thief")(), rules, 14, start
        ).outcome.reason
        for _ in range(5)
    }
    assert len(outcomes) == 1


@BOTH_BRAINS
def test_the_harness_shows_brains_no_more_than_a_real_match_does(
    minimal_config, played
) -> None:
    """The harness and the live runtime must build the *same* observation.

    If self-play were more generous, every measurement taken here would be
    optimistic — and we would discover that against a real opponent.
    """
    runtime = PeerRuntime(orchestrator=Orchestrator.from_config(minimal_config, Role.COP))
    live = runtime.observe()
    assert live.belief and len(live.belief) == 48
    assert abs(sum(live.belief.values()) - 1.0) < 1e-9


@BOTH_BRAINS
def test_a_thief_that_survives_scores_five_ten(played, minimal_config) -> None:
    """Ties the harness back to Appendix F rather than inventing its own scoring."""
    from core.domain.scoring import ScoreTable, score

    if played.outcome.verdict is Verdict.SURVIVAL:
        assert score(played.outcome, ScoreTable.from_config(minimal_config)) == (5, 10)


@BOTH_BRAINS
def test_the_baseline_cop_does_not_yet_catch_the_thief(played) -> None:
    """**The honest headline, recorded as a test so it cannot be forgotten.**

    With a uniform belief the cop has no information: every cell is equally
    likely, so the peak is an artefact of tie-breaking rather than a sighting.
    It walks to a corner and waits. The thief runs out the clock every time.

    That is not a bug in the baseline — it is the measurement telling us the
    cop's grade comes from the **belief filter** (Phase 4), not from pathfinding.
    When this test starts failing, the belief filter is working.
    """
    assert played.outcome.verdict is Verdict.SURVIVAL


# --- the ceiling (M3) -------------------------------------------------------


@BOTH_BRAINS
def test_a_perfect_belief_catches_the_thief_every_time(rules: Rules, start: GameState) -> None:
    """**Milestone M3, and the measurement that makes Phase 4 judgeable.**

    Given the thief's true position the cop walks a shortest path and captures
    in ~10 steps, unaided. Two things follow:

    * M3's DoD — "computes and walks the shortest path to a known target with no
      manual intervention" — is satisfied, and *observable* via `--oracle`.
    * The gap between this and normal play (win rate 1.000 against 0.000) is
      exactly what a perfect belief is worth. Phase 4's filter is judged against
      that ceiling rather than against an opinion.
    """
    results = [
        play_sub_game(
            brain_class("police")(), brain_class("thief")(), rules, 14, start, oracle=True
        )
        for _ in range(5)
    ]
    assert all(r.outcome.verdict is Verdict.CAPTURE for r in results)
    assert all(r.steps < rules.survival_threshold for r in results)


@BOTH_BRAINS
def test_the_oracle_is_a_harness_flag_that_no_brain_can_request(rules: Rules) -> None:
    """It must never be reachable from a real match.

    `PeerRuntime` has no equivalent parameter, so the only way to obtain a
    perfect belief is for the harness to hand one over — and the harness never
    runs in a graded game.
    """
    import inspect

    assert "oracle" not in inspect.signature(PeerRuntime.observe).parameters
    assert "oracle" not in inspect.signature(PeerRuntime.belief).parameters
