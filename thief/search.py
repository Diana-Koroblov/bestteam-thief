"""Expectimax for the evader (TODO 8.2.1; PRD advanced §4.1).

The mirror of `police/search.py` — max nodes over our moves, chance nodes over
the posterior about the Cop — with the sign flipped and one structural
difference that is worth stating plainly.

Why the scent cost sits at the root and not inside the tree
-----------------------------------------------------------
A2.5 says to treat our own emission as a cost, and the obvious place to put it is
in the evaluation, charged at every node. **That would be false precision.** What
a trail actually costs us is the sharpness it gives the *Cop's* filter, and this
search does not model the Cop's filter at all — its chance nodes propagate *our*
belief about the Cop by diffusion, which is a different object entirely. Charging
a trail cost at depth 3 would price an effect the tree has no machinery to
represent.

So the trail is charged once, against the cell we would actually step onto this
turn, where it is a plain comparison between real alternatives: this cell is
somewhere I have circled ten times, that one is quiet. Honest and shallow beats
dishonest and deep.

Depth is smaller than the Cop's for a reason too. The Cop is hunting and needs to
see a capture coming; we are running, and the thing that kills an evader is the
one-move blunder into a sealable cell, which depth 2 already sees.
"""

from __future__ import annotations

from core.domain.actions import Direction
from core.domain.belief import mask, predict
from core.domain.board import Board, Position
from core.domain.brain_base import Observation
from thief.evaluation import CAPTURED, ThiefWeights, evaluate
from thief.trail import TrailTracker

__all__ = ["best_move", "expectimax", "options", "value_of", "DEFAULT_DEPTH"]

DEFAULT_DEPTH = 2


def options(
    thief: Position, barriers: frozenset[Position], board: Board
) -> list[tuple[Direction, Position]]:
    """Return every ``(direction, destination)`` the Thief may legally take.

    STAY first and always available, so a boxed-in Thief still has a decision to
    return rather than raising inside a search — and so an unbroken tie resolves
    identically on both machines replaying one log.
    """
    moves = [(Direction.STAY, thief)]
    moves.extend(
        (direction, cell)
        for direction, cell in board.neighbours(thief)
        if board.is_passable(cell, barriers)
    )
    return moves


def value_of(
    destination: Position,
    belief: dict[Position, float],
    barriers: frozenset[Position],
    board: Board,
    depth: int,
    weights: ThiefWeights,
    walls_left: int,
) -> float:
    """Return the expected value of stepping onto *destination*.

    The chance node the Cop's version has, read from the other side: with
    probability ``belief[destination]`` we have walked straight into the Cop and
    the sub-game is over. Otherwise the posterior conditioned on *not* having
    been caught is the masked, renormalised belief — free information a search
    that skipped it would throw away, and it matters most in exactly the tight
    positions where it is cheapest to be wrong.
    """
    caught = belief.get(destination, 0.0)
    survivors = mask(belief, barriers, destination)
    if not survivors:
        return CAPTURED
    ahead = expectimax(
        destination,
        predict(survivors, board, barriers),
        barriers,
        board,
        depth - 1,
        weights,
        walls_left,
    )
    return caught * CAPTURED + (1.0 - caught) * ahead


def expectimax(
    thief: Position,
    belief: dict[Position, float],
    barriers: frozenset[Position],
    board: Board,
    depth: int,
    weights: ThiefWeights,
    walls_left: int,
) -> float:
    """Return the value of a position to the Thief, searching *depth* plies.

    Barriers are constant through the search. We cannot place them and cannot
    know where the Cop will, so branching over hypothetical walls would be
    searching a board nobody has built — `seal_pressure` prices that threat
    statically instead, from the quota the Cop must declare.
    """
    if depth <= 0 or not belief:
        return evaluate(thief, belief, barriers, board, walls_left, weights)
    return max(
        value_of(destination, belief, barriers, board, depth, weights, walls_left)
        for _, destination in options(thief, barriers, board)
    )


def best_move(
    observation: Observation,
    weights: ThiefWeights,
    trail: TrailTracker,
    depth: int = DEFAULT_DEPTH,
) -> tuple[Direction, float]:
    """Return the Thief's best action and its value.

    The trail cost is applied here and nowhere deeper, for the reason in the
    module docstring. Ties break on the fixed ordering from `options` rather
    than on whichever float compared larger, so two peers replaying one log
    reach the same move.
    """
    scored = []
    for index, (direction, destination) in enumerate(
        options(observation.own_position, observation.barriers, observation.board)
    ):
        value = value_of(
            destination,
            observation.belief,
            observation.barriers,
            observation.board,
            depth,
            weights,
            observation.barriers_remaining,
        )
        value -= weights.scent * trail.cost_at(destination, observation.board)
        scored.append((value, index, direction))

    value, _, direction = max(scored, key=lambda entry: (entry[0], -entry[1]))
    return direction, value
