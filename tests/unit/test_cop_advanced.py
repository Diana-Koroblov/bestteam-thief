"""The advanced Cop, end to end (TODO 8.1).

The pieces are tested apart in `test_cop_search.py`, `test_barrier_policy.py`
and `test_cop_phases.py`. What is left, and what this file is for, is the part
only the assembled brain can get wrong: choosing **between** a wall and a step,
which are alternatives on the same turn rather than a sequence.
"""

from __future__ import annotations

from core.domain.actions import Direction
from core.domain.board import Board
from core.domain.brain_base import Observation
from police.advanced import AdvancedCop
from police.phases import Phase
from police.search import DEFAULT_DEPTH

BOARD = Board(grid_size=7)


def observe(own, belief, barriers=frozenset(), step=5, remaining=14) -> Observation:
    """Build one Cop's view."""
    return Observation(
        board=BOARD, own_position=own, barriers=barriers, step=step,
        barriers_remaining=remaining, belief=belief,
    )


UNIFORM = dict.fromkeys(BOARD.cells(), 1.0 / 49)

# (0,0)'s only remaining exit is (1,0), and the Cop stands beside that exit
# rather than on the Thief. Chosen deliberately: from a cell adjacent to the
# Thief the Cop could simply step onto it, and a wall would only be *tied* with
# a move. Here the wall is the sole capture available, so preferring it is a
# real decision rather than a coin toss.
ENDGAME = observe((1, 1), {(0, 0): 1.0}, frozenset({(0, 1)}))


# --- the choice between a wall and a step -----------------------------------


def test_a_decision_never_moves_and_places_at_once() -> None:
    """Ch. 3.4 forbids it and `Decision` raises on it, so this asserts the brain
    never constructs one — across a spread of positions, not one."""
    cop = AdvancedCop()
    for view in (observe((3, 3), UNIFORM), ENDGAME, observe((0, 0), {(6, 6): 1.0})):
        decision = cop.decide(view)
        assert decision.barrier is None or decision.move is Direction.STAY


def test_the_endgame_wall_is_taken_over_any_step() -> None:
    """Sealing the Thief's last exit wins outright (M#47), and here no move can.

    🐛 **This is the test that caught the separation guard refusing the winning
    move.** A wall on the last exit strands the Thief by construction, so the
    guard fired on the one placement that ends the sub-game in our favour. It
    now judges stranding on the mass that *survives* the placement — mass that
    has been captured cannot be stranded.
    """
    decision = AdvancedCop().decide(ENDGAME)
    assert decision.barrier == (1, 0)
    assert decision.move is Direction.STAY


def test_no_wall_is_built_while_the_belief_is_diffuse() -> None:
    """**8.1.12.** The phase machine holds us in HERD and the placement filter
    refuses independently; either alone would do, and permanence earns both."""
    cop = AdvancedCop()
    decision = cop.decide(observe((3, 3), UNIFORM))
    assert decision.barrier is None
    assert cop.phase is Phase.HERD


def test_a_spent_quota_still_produces_a_move() -> None:
    """A Cop out of walls is not a Cop out of options."""
    decision = AdvancedCop().decide(observe((1, 0), {(0, 0): 1.0}, remaining=0))
    assert decision.barrier is None


def test_the_reason_carries_the_phase_into_the_log() -> None:
    """So a replay can explain a turn the Cop spent walking past a wall it could
    have built (TODO 7.5.1)."""
    assert AdvancedCop().decide(observe((3, 3), UNIFORM)).reason.startswith("HERD")
    assert AdvancedCop().decide(ENDGAME).reason.startswith("SEAL")


# --- determinism ------------------------------------------------------------


def test_the_same_position_always_produces_the_same_decision() -> None:
    """Two peers replay one log and must reach the same result. A brain that
    consulted a clock or an unseeded random source would make the match
    unverifiable (`BrainBase._pick_move`)."""
    view = observe((3, 3), {(0, 0): 0.5, (6, 6): 0.5})
    decisions = [AdvancedCop().decide(view) for _ in range(4)]
    assert len({(d.move, d.barrier) for d in decisions}) == 1


def test_pick_move_works_without_the_barrier_machinery() -> None:
    """Present so the movement half can be exercised alone, and so a caller that
    only wants a move is not forced through placement logic."""
    decision = AdvancedCop()._pick_move(observe((3, 3), {(3, 4): 1.0}))
    assert decision.move is Direction.E
    assert decision.barrier is None


# --- the opponent profile ---------------------------------------------------


def test_the_profile_grows_as_the_sub_game_runs() -> None:
    """Recording is free, so it happens every turn (TODO 8.3.2)."""
    cop = AdvancedCop()
    for step in range(4):
        cop.decide(observe((3, 3), {(0, step): 1.0}, step=step))
    assert cop.verbal.profile.visits == 4
    assert cop.verbal.profile.transitions == 3


def test_a_new_sub_game_restarts_the_trajectory() -> None:
    """A cell "revisited" across two different sub-games says nothing about
    whether this opponent circles. The boundary shows up as the step counter
    failing to advance."""
    cop = AdvancedCop()
    cop.decide(observe((3, 3), {(0, 0): 1.0}, step=7))
    cop.decide(observe((3, 3), {(6, 6): 1.0}, step=0))
    # The trait counters are **banked** across the boundary (8.3.3); what
    # restarts is the trajectory, so the second sub-game's first peak cannot be
    # scored as a transition from a cell in a game that is over.
    assert cop.verbal.profile.visits == 2
    assert cop.verbal.profile.transitions == 0


def test_the_series_boundary_banks_the_profile_and_drops_the_trail() -> None:
    """`BrainBase.restart_sub_game`, called by the runner between sub-games.

    The two halves of what a brain remembers cross the line differently: what
    this opponent is *like* is the reason for playing them six times, and where
    everyone *was* is a scent trail from a game that is over. Rebuilding the
    brain would throw away both.
    """
    cop = AdvancedCop()
    for step in range(3):
        cop.decide(observe((3, 3), {(0, step): 1.0}, step=step))
    banked = cop.verbal.profile.visits

    cop.restart_sub_game(2)
    assert cop.verbal.profile.visits == banked, "the reputation must survive the boundary"
    assert cop.verbal.trail.emitted == {}, "the trail must not"
    assert cop.verbal.peak is None


# --- A1.3 configuration -----------------------------------------------------


def test_depth_comes_from_config() -> None:
    """**A1.3.** Read once at startup, where a bad value costs an error message
    rather than a technical loss thirty seconds into a graded match."""

    class Stub:
        def get(self, path: str, default: object = None) -> object:
            return 2 if path == "strategy.search_depth" else default

    cop = AdvancedCop()
    cop.configure(Stub())
    assert cop.depth == 2


def test_an_unconfigured_cop_plays_a_real_game() -> None:
    """A fresh clone with no tuning file must field a strategy, not a stub."""
    cop = AdvancedCop()
    assert cop.depth == DEFAULT_DEPTH
    assert cop.decide(observe((3, 3), {(3, 4): 1.0})).move is Direction.E


def test_the_loader_configures_the_brain_it_builds() -> None:
    """The wiring, not the hook: a `configure` nobody calls is decoration."""
    from core.runtime.brain_loader import load_brain

    class Stub:
        def get(self, path: str, default: object = None) -> object:
            return 1 if path == "strategy.search_depth" else default

    brain = load_brain("police.advanced:AdvancedCop", "cop", Stub())
    assert brain.depth == 1
    assert load_brain("police.advanced:AdvancedCop", "cop").depth == DEFAULT_DEPTH
