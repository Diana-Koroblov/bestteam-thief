"""Run whole sub-games in one process. No network, no LLM, no tokens.

Strategy is the grade, and you cannot tune what you cannot measure. Everything
from here on is A/B'd against the baselines rather than trusted, and this is
what makes that cheap enough to do on every change: a hundred sub-games in
seconds, for nothing.

**This is not a referee.** It uses the same `core.domain` rules both peers
enforce independently in a real match. If it disagreed with them the measurement
would be meaningless, so it has no rules of its own — it drives the two brains
and applies the engine.

Both agents move **simultaneously**, as commit-reveal requires: neither
decision sees the other. Deciding sequentially would let the second brain react
to the first and quietly inflate whichever role moved last.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.domain.barriers import BarrierManager, PlacementOutcome
from core.domain.board import Board, Position
from core.domain.brain_base import BrainBase, Decision, Observation
from core.domain.connectivity import are_connected, exit_count
from core.domain.game_state import GameState
from core.domain.movement import resolve_move
from core.domain.rules import Outcome, Rules, Verdict

__all__ = ["SubGameResult", "play_sub_game"]


@dataclass
class SubGameResult:
    """What one sub-game produced, and enough detail to explain why.

    Attributes:
        outcome: The verdict and the rule that ended it.
        steps: Turns played.
        barriers_placed: Walls the Cop actually spent.
        cop_separations: Turns on which the Cop could **not** reach the Thief.
            The self-inflicted loss from ``connectivity.py``. **Must be 0** for
            any cop we would field (TODO 3.5.4).
        history: Every state, for rendering and for the replay.
        reasons: Each turn's ``(cop_reason, thief_reason)``, so a surprising
            game explains itself instead of being a sequence of moves.
    """

    outcome: Outcome
    steps: int = 0
    barriers_placed: int = 0
    cop_separations: int = 0
    history: list[GameState] = field(default_factory=list)
    reasons: list[tuple[str, str]] = field(default_factory=list)


def _uniform_belief(board: Board, barriers: frozenset[Position], own: Position) -> dict:
    """Return the same uniform posterior the live runtime supplies.

    Deliberately identical to ``PeerRuntime.belief()``. A harness that fed
    brains better information than a real match provides would measure a
    strategy nobody can actually play.
    """
    cells = [c for c in board.cells() if c not in barriers and c != own]
    return dict.fromkeys(cells, 1.0 / len(cells)) if cells else {}


def _observe(state: GameState, board: Board, own: Position, remaining: int) -> Observation:
    """Build one side's view. Never contains the opponent's true position."""
    return Observation(
        board=board,
        own_position=own,
        barriers=state.barriers,
        step=state.step,
        barriers_remaining=remaining,
        belief=_uniform_belief(board, state.barriers, own),
    )


def _apply(decision: Decision, position: Position, state: GameState, board: Board) -> Position:
    """Return where an agent ends up, holding position on an illegal move.

    A brain that proposes an illegal move would forfeit in a real match. Here
    it holds instead, so one bad decision does not abort a hundred-game batch —
    and the reason string still records what it tried.
    """
    try:
        return resolve_move(position, decision.move, state.barriers, board)
    except ValueError:
        return position


def play_sub_game(
    cop: BrainBase,
    thief: BrainBase,
    rules: Rules,
    quota: int,
    start: GameState,
) -> SubGameResult:
    """Play one sub-game to a terminal state and return what happened.

    Args:
        cop: The Cop's brain.
        thief: The Thief's brain.
        rules: Terminal conditions, built from the negotiated config.
        quota: ``max_barriers``.
        start: The opening position.
    """
    board = rules.board
    barriers = BarrierManager(max_barriers=quota, board=board)
    state = start
    result = SubGameResult(outcome=Outcome(Verdict.SURVIVAL, "not started"))
    result.history.append(state)

    while True:
        if not are_connected(state.cop, state.thief, state.barriers, board):
            result.cop_separations += 1

        cop_move = cop.decide(_observe(state, board, state.cop, barriers.remaining))
        thief_move = thief.decide(_observe(state, board, state.thief, 0))
        result.reasons.append((cop_move.reason, thief_move.reason))

        before = state
        placed = _place(cop_move, barriers, state)
        state = _advance(state, cop_move, thief_move, board, placed)
        result.history.append(state)

        outcome = _resolve(before, state, rules, placed, barriers)
        if outcome is not None:
            result.outcome = outcome
            break

    result.steps = state.step
    result.barriers_placed = barriers.placed_count
    return result


def _place(decision: Decision, barriers: BarrierManager, state: GameState):
    """Apply a barrier placement if the Cop asked for one."""
    if decision.barrier is None:
        return None
    return barriers.place(decision.barrier, state.cop, thief_pos=state.thief)


def _advance(state, cop_move, thief_move, board, placed) -> GameState:
    """Return the next state with both moves applied simultaneously."""
    cop_to = state.cop if placed else _apply(cop_move, state.cop, state, board)
    thief_to = _apply(thief_move, state.thief, state, board)
    return state.advanced(
        cop=cop_to,
        thief=thief_to,
        barriers=state.barriers | ({placed.cell} if placed and placed.succeeded else set()),
        barriers_placed=state.barriers_placed + (1 if placed and placed.succeeded else 0),
    )


def _resolve(before, after, rules, placed, barriers) -> Outcome | None:
    """Return the verdict for this turn, if any."""
    if placed is not None and placed.outcome is PlacementOutcome.CAPTURE:
        return Outcome(Verdict.CAPTURE, f"barrier at {placed.cell} captured the thief")
    if exit_count(after.thief, after.barriers, rules.board) == 0 and not rules.stay_counts_as_move:
        return Outcome(Verdict.CAPTURE, f"thief sealed in at {after.thief} (M#47)")
    return rules.turn_verdict(before, after)
