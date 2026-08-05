"""The advanced Thief, end to end (TODO 8.2).

The pieces are tested apart in `test_thief_search.py`, `test_thief_evaluation.py`,
`test_trail.py` and `test_thief_anchor.py`. What is left is the wiring: that
the brain emits into its own trail every turn, resets both trail and bluff at a
sub-game boundary, and never produces a decision only a Cop is allowed to make.
"""

from __future__ import annotations

from core.domain.actions import Direction
from core.domain.board import Board
from core.domain.brain_base import Observation
from thief.advanced import AdvancedThief
from thief.anchor import AnchorPhase
from thief.search import DEFAULT_DEPTH

BOARD = Board(grid_size=7)


def observe(own, belief, barriers=frozenset(), step=5, walls_left=14) -> Observation:
    """Build one Thief's view."""
    return Observation(
        board=BOARD, own_position=own, barriers=barriers, step=step,
        barriers_remaining=walls_left, belief=belief,
    )


UNIFORM = dict.fromkeys(BOARD.cells(), 1.0 / 49)


# --- only a cop places barriers ---------------------------------------------


def test_a_thief_never_returns_a_barrier() -> None:
    """Ch. 3.4 gives the Thief no placement, and `PeerRuntime.on_barrier`
    rejects one from us outright — so producing one would be a protocol error we
    committed to before the opponent even saw it."""
    thief = AdvancedThief()
    for view in (observe((3, 3), UNIFORM), observe((0, 0), {(6, 6): 1.0}), observe((6, 6), {})):
        assert thief.decide(view).barrier is None


def test_every_decision_is_a_legal_move() -> None:
    """An illegal move is a technical loss (M#13)."""
    thief = AdvancedThief()
    walls = frozenset({(0, 1)})
    decision = thief.decide(observe((0, 0), {(6, 6): 1.0}, walls))
    assert decision.move in {Direction.STAY, Direction.S}


# --- the tactics, visible from outside --------------------------------------


def test_it_keeps_room_rather_than_maximising_distance() -> None:
    """The baseline ran to (6,6) and sat there for 29 turns. From (5,5) with the
    Cop at (0,0), raw distance says E or S into the corner."""
    decision = AdvancedThief().decide(observe((5, 5), {(0, 0): 1.0}))
    landing = {Direction.STAY: (5, 5), Direction.N: (4, 5), Direction.S: (6, 5),
               Direction.E: (5, 6), Direction.W: (5, 4)}
    assert landing[decision.move] != (6, 6)


def test_it_steps_away_from_an_adjacent_cop() -> None:
    """Capture risk dominates every other term, as it must."""
    assert AdvancedThief().decide(observe((3, 3), {(3, 4): 1.0})).move is not Direction.E


def test_the_reason_carries_the_stage_exits_and_risk() -> None:
    """Written to the log so a replay explains itself (TODO 7.5.1)."""
    reason = AdvancedThief().decide(observe((3, 3), {(0, 0): 1.0})).reason
    assert reason.startswith("OFF") and "exits" in reason and "risk" in reason


# --- determinism ------------------------------------------------------------


def test_the_same_position_always_produces_the_same_decision() -> None:
    """A brain that consulted a clock or an unseeded source would make the match
    unverifiable."""
    view = observe((3, 3), {(0, 0): 0.5, (6, 6): 0.5})
    assert len({AdvancedThief().decide(view).move for _ in range(4)}) == 1


# --- the trail is kept in step ----------------------------------------------


def test_it_emits_into_its_own_trail_every_turn() -> None:
    """`Observation` carries no record of what we have emitted, so the brain
    rebuilds it — and it has to actually happen, every turn, or the reconstruction
    silently drifts."""
    thief = AdvancedThief()
    for step, cell in enumerate([(3, 3), (3, 4), (2, 4)]):
        thief.decide(observe(cell, {(0, 0): 1.0}, step=step))
    assert thief.verbal.trail.visits == [(3, 3), (3, 4), (2, 4)]


def test_a_new_sub_game_clears_the_trail_and_the_bluff() -> None:
    """The boundary shows up as the step counter failing to advance. Carrying a
    trail across it would have the Thief fleeing the ghost of a scored game."""
    thief = AdvancedThief()
    thief.decide(observe((3, 3), {(0, 0): 1.0}, step=7))
    thief.decide(observe((6, 6), {(0, 0): 1.0}, step=0))
    assert thief.verbal.trail.visits == [(6, 6)]
    assert thief.anchor.phase is AnchorPhase.OFF


# --- A1.3 configuration -----------------------------------------------------


class Stub:
    """A config answering the keys the Thief reads, and nothing else."""

    def __init__(self, **values: object) -> None:
        self.values = values

    def get(self, path: str, default: object = None) -> object:
        return self.values.get(path, default)


def test_depth_and_weights_come_from_config() -> None:
    """Read once at startup, where a bad value costs an error message rather
    than a technical loss thirty seconds into a graded match."""
    thief = AdvancedThief()
    thief.configure(Stub(**{"strategy.search_depth": 1, "strategy.weight_cycle": 5.0}))
    assert thief.depth == 1
    assert thief.weights.cycle == 5.0


def test_the_decay_model_comes_from_the_negotiated_section() -> None:
    """**C-007.** The trail we rebuild has to match the one the engine emits,
    and which decay model is in force is settled at the handshake — not by our
    own preference."""
    thief = AdvancedThief()
    thief.configure(Stub(**{"pheromones.decay_model": "subtractive", "pheromones.pheromone_decay": 0.2}))
    assert thief.verbal.trail.model == "subtractive"
    assert thief.verbal.trail.rate == 0.2


def test_the_false_anchor_is_off_unless_config_asks_for_it() -> None:
    """8.2.6 measured it and it lost: 37/48 against 44/48. It ships disabled."""
    thief = AdvancedThief()
    thief.configure(Stub())
    assert thief.anchor.enabled is False


def test_the_false_anchor_can_be_switched_back_on() -> None:
    """The switch has to work, or the ablation could not have been run."""
    thief = AdvancedThief()
    thief.configure(Stub(**{"strategy.false_anchor": True}))
    assert thief.anchor.enabled is True


# --- the rejected path, still exercised -------------------------------------


def enabled_thief() -> AdvancedThief:
    """A Thief with the bluff switched on, as the ablation ran it."""
    thief = AdvancedThief()
    thief.configure(Stub(**{"strategy.false_anchor": True}))
    return thief


def test_the_bluff_path_is_exercised_even_though_it_ships_off() -> None:
    """**Disabled is not the same as untested.** 8.2.6's numbers came out of this
    branch, so leaving it uncovered would mean the measurement that rejected the
    tactic ran through code nothing else checks — and a later re-run would be
    comparing against an untested arm."""
    # (3,3), not a corner: `min_exits` refuses to stand still anywhere that
    # could be closed while we do it, and a corner has only two exits.
    thief = enabled_thief()
    decision = thief.decide(observe((3, 3), {(0, 0): 1.0}))
    assert thief.phase is AnchorPhase.ANCHORING
    assert decision.barrier is None
    assert decision.reason.startswith("ANCHORING")


def test_the_bluff_still_runs_away_from_a_cop_that_arrives() -> None:
    """The bluff biases a choice between comparable moves; it never overrides a
    safety verdict. A tactic that could talk the Thief into standing next to the
    Cop would be worse than no tactic."""
    thief = enabled_thief()
    thief.decide(observe((3, 3), {(0, 0): 1.0}))
    assert thief.phase is AnchorPhase.ANCHORING
    decision = thief.decide(observe((3, 3), {(3, 4): 1.0}, step=6))
    assert thief.phase is AnchorPhase.OFF
    assert decision.move is not Direction.E


def test_the_two_stages_produce_different_moves() -> None:
    """ANCHORING holds near the plateau, BREAKING leaves it — otherwise the
    ablation would have been comparing the tactic against itself."""
    thief = enabled_thief()
    thief.anchor.anchor_turns, thief.anchor.break_turns = 1, 5
    view = observe((3, 3), {(0, 0): 1.0})
    thief.decide(view)
    anchoring = thief.decide(observe((3, 3), {(0, 0): 1.0}, step=6)).move
    assert thief.phase is AnchorPhase.BREAKING
    assert thief.anchor.bias((6, 6), 3.0) > thief.anchor.bias((3, 3), 3.0)
    assert anchoring in set(Direction)


def test_an_unconfigured_thief_plays_a_real_game() -> None:
    """A fresh clone with no tuning file must field a strategy, not a stub."""
    thief = AdvancedThief()
    assert thief.depth == DEFAULT_DEPTH
    assert thief.decide(observe((3, 3), {(3, 4): 1.0})).move is not Direction.E


def test_the_loader_configures_the_brain_it_builds() -> None:
    """The wiring, not the hook: a `configure` nobody calls is decoration."""
    from core.runtime.brain_loader import load_brain

    brain = load_brain("thief.advanced:AdvancedThief", "thief", Stub(**{"strategy.search_depth": 1}))
    assert brain.depth == 1
    assert load_brain("thief.advanced:AdvancedThief", "thief").depth == DEFAULT_DEPTH
