"""Applying one turn's two decisions to the board (TODO 9.4.1).

Extracted from `runtime/selfplay.py`, which had been the only thing that knew
how a turn resolves. That was tolerable while self-play was the only thing
playing; it stops being tolerable the moment a live match resolves turns too,
because two copies of this logic is two sets of physics — and the peer that
tuned its strategy against one would meet the other in a graded match.

It lives in `domain` rather than `runtime` because it is the rules, not the
plumbing: it reads the board, the barriers and the negotiated terminal
conditions, and it knows nothing about messages, transports or opponents.

**One deliberate difference between the two callers**, and it is the whole
reason `strict` exists. In self-play an illegal proposal holds position: one bad
decision must not abort a hundred-game batch, and the reason string still
records what was attempted. In a live match an opponent's illegal move is a
technical loss in our favour, and silently converting it to STAY would hand back
a point the rules already gave us (M#13, M#14).
"""

from __future__ import annotations

from dataclasses import dataclass

from core.domain.barriers import BarrierManager, Placement, PlacementOutcome
from core.domain.board import Board, Position
from core.domain.brain_base import Decision
from core.domain.connectivity import exit_count
from core.domain.game_state import GameState
from core.domain.movement import resolve_move
from core.domain.rules import Outcome, Rules, Verdict

__all__ = ["TurnResult", "IllegalMoveError", "resolve_turn", "destination"]


class IllegalMoveError(ValueError):
    """A decision proposed a move the board does not permit.

    Raised only under ``strict``. The message names the side, because the
    remedy differs entirely: ours is a bug to fix, theirs is a technical loss to
    claim, and a peer that cannot tell them apart will do the wrong one.
    """


@dataclass(frozen=True)
class TurnResult:
    """What one turn produced.

    Attributes:
        state: The board after both decisions applied simultaneously.
        placed: The Cop's placement, when it asked for one — including a refused
            one, which still carries the cell it named.
        outcome: The verdict, when this turn ended the sub-game.
    """

    state: GameState
    placed: Placement | None
    outcome: Outcome | None


def destination(
    decision: Decision,
    position: Position,
    state: GameState,
    board: Board,
    *,
    strict: bool = False,
    side: str = "agent",
) -> Position:
    """Return where *decision* lands, or where it holds.

    Raises:
        IllegalMoveError: The move is not legal and *strict* is set.
    """
    try:
        return resolve_move(position, decision.move, state.barriers, board)
    except ValueError as error:
        if strict:
            raise IllegalMoveError(f"{side} proposed an illegal move: {error}") from error
        return position


def resolve_turn(
    state: GameState,
    cop: Decision,
    thief: Decision,
    barriers: BarrierManager,
    rules: Rules,
    *,
    strict: bool = False,
) -> TurnResult:
    """Apply both decisions to *state* and return the turn's result.

    Args:
        barriers: Mutated when the Cop places — it owns the quota, and a copy
            would let the same wall be spent twice.
        strict: Raise on an illegal move instead of holding position. Set by a
            live match, unset by the measurement harness.

    The **Thief's destination is resolved first**, against the barriers as they
    stood when both sides committed, and then handed to the placement so capture
    is judged on where the Thief actually ends up (C-006b). The other order let a
    Thief walk into the wall being built and stand inside it.
    """
    thief_to = destination(thief, state.thief, state, board=rules.board, strict=strict, side="thief")
    placed = _place(cop, barriers, state, thief_to)
    cop_to = (
        state.cop
        if placed
        else destination(cop, state.cop, state, board=rules.board, strict=strict, side="cop")
    )
    after = state.advanced(
        cop=cop_to,
        thief=thief_to,
        barriers=state.barriers | ({placed.cell} if placed and placed.succeeded else set()),
        barriers_placed=state.barriers_placed + (1 if placed and placed.succeeded else 0),
    )
    return TurnResult(state=after, placed=placed, outcome=_verdict(state, after, rules, placed))


def _place(
    decision: Decision, barriers: BarrierManager, state: GameState, thief_to: Position
) -> Placement | None:
    """Apply a barrier placement if the Cop asked for one.

    Args:
        thief_to: Where the Thief ends this turn, **not** where it started.
            `capture.resolution = "after_moves"` evaluates positions once both
            actions apply, so this is the cell M#46 is judged against — a wall on
            a vacated cell misses, and a wall on the cell the Thief steps onto
            captures. Both halves follow from the same value.
    """
    if decision.barrier is None:
        return None
    return barriers.place(decision.barrier, state.cop, thief_pos=thief_to)


def _verdict(
    before: GameState, after: GameState, rules: Rules, placed: Placement | None
) -> Outcome | None:
    """Return the verdict for this turn, if any."""
    if placed is not None and placed.outcome is PlacementOutcome.CAPTURE:
        return Outcome(Verdict.CAPTURE, f"barrier at {placed.cell} captured the thief")
    if exit_count(after.thief, after.barriers, rules.board) == 0 and not rules.stay_counts_as_move:
        return Outcome(Verdict.CAPTURE, f"thief sealed in at {after.thief} (M#47)")
    return rules.turn_verdict(before, after)
