"""The self-play harness (TODO 3.5).

The property that matters most: the harness must give brains **exactly** what a
real match gives them. A harness that fed better information would measure a
strategy nobody can actually play, and we would only find out in a graded match.
"""

from __future__ import annotations

import pytest

from core.domain.board import Board
from core.domain.filter import BeliefFilter
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

    🐛 **This test is named for a property it did not check, and the property
    was false for the whole of Phase 8.** It asserted that the live belief was
    non-empty, summed to 1.0, and that our own position was not the thief's —
    all true of the uniform placeholder the live runtime returned at the time,
    and all true of any posterior whatsoever. Meanwhile the harness was handing
    both brains the opponent's *current-turn* scent deposit, which commit-reveal
    cannot deliver: a field revealed at turn k is first readable at turn k+1.

    So it now compares the two paths on the thing that differs — the evidence
    available at decision time — instead of on invariants neither could break.
    """
    runtime = PeerRuntime(orchestrator=Orchestrator.from_config(minimal_config, Role.COP))
    live = runtime.observe()

    # Both paths run the same filter, on a field that is one turn old in each.
    assert live.belief
    assert abs(sum(live.belief.values()) - 1.0) < 1e-9

    # Turn 0: nothing has been revealed yet, so the live path has no reading. A
    # harness that had already folded in the opponent's opening deposit would be
    # strictly sharper than this, which is the discrepancy that went unnoticed.
    assert runtime.latest_opponent_scent() == {}

    # **The parity check itself.** The live belief must be exactly what the
    # shared filter produces from the same inputs — not merely similar, and not
    # merely a distribution. Run the reference filter alongside and compare.
    # Note the prior is *not* uniform even with no evidence: `predict` spreads
    # mass over legal destinations, and cells beside a wall or an edge have
    # fewer, so an equality check is the only honest one here.
    state = runtime.orchestrator.state
    reference = BeliefFilter(board=runtime.orchestrator.board)
    reference.deposit(runtime.orchestrator.own_position)
    expected = reference.observe({}, state.barriers, runtime.orchestrator.own_position)
    assert live.belief == expected

    # The live path masks what the harness masks: a wall and our own cell hold
    # exactly zero, never a small number that merely looks like zero.
    assert live.own_position not in live.belief
    assert all(cell not in live.belief for cell in runtime.orchestrator.state.barriers)


@BOTH_BRAINS
def test_a_thief_that_survives_scores_five_ten(played, minimal_config) -> None:
    """Ties the harness back to Appendix F rather than inventing its own scoring."""
    from core.domain.scoring import ScoreTable, score

    if played.outcome.verdict is Verdict.SURVIVAL:
        assert score(played.outcome, ScoreTable.from_config(minimal_config)) == (5, 10)


@BOTH_BRAINS
def test_the_belief_filter_is_what_makes_the_cop_work(played, rules: Rules) -> None:
    """**This test used to assert the opposite, and that was the point.**

    Until the belief filter existed it read
    ``test_the_baseline_cop_does_not_yet_catch_the_thief`` and asserted
    SURVIVAL: with a uniform posterior the cop had no information, the "peak"
    was an artefact of tie-breaking, and the thief ran out the clock 20 games
    out of 20.

    It was written to fail the moment the filter started working, so that the
    improvement would announce itself instead of being assumed. It now does.

    Measured baseline against baseline, re-measured 06/08 over **48 openings**
    once the harness stopped handing the filter a turn of scent the wire cannot
    deliver::

    ==================  ==============  ==========
    cop belief          captures / 48   mean steps
    ==================  ==============  ==========
    uniform (none)            0            35.00
    Bayesian filter          27            19.62
    oracle (perfect)         48            10.25
    ==================  ==============  ==========

    ⚠️ **The middle row used to read 1.000 and it was an artefact.** The old
    figure came from one opening, and from a harness that let the filter read
    the opponent's *current-turn* deposit — evidence commit-reveal cannot
    deliver, since our move is sealed before their reveal arrives. With the
    field held back one turn, the baseline Cop's filter recovers roughly **half**
    the distance from blind to omniscient rather than all of it. That is the
    honest number, and it is what the advanced Cop of Phase 8 was built to
    close: it still captures 48/48.

    The claim the test defends is unchanged and now rests on a real sample: a
    uniform belief captures **nothing**, so every capture here is the filter's.

    Asserted as the *ordering* of the three rows rather than as any one figure.
    A single opening is one sample and a fixed capture count is a number that
    goes stale the next time a weight moves; "blind < filtered < perfect" is the
    claim, and it is the thing that would actually be false if the filter broke.
    """
    openings = [((0, 0), (6, 6)), ((0, 6), (6, 0)), ((2, 2), (4, 4)), ((1, 5), (5, 1))]

    def captures(oracle: bool) -> int:
        return sum(
            play_sub_game(
                brain_class("police")(), brain_class("thief")(), rules, 14,
                GameState(cop=cop, thief=thief), oracle,
            ).outcome.verdict is Verdict.CAPTURE
            for cop, thief in openings
        )

    filtered, perfect = captures(oracle=False), captures(oracle=True)
    assert perfect == len(openings), "a known target must always be caught"
    assert 0 < filtered <= perfect, "the filter must be worth something, and less than perfect"


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
