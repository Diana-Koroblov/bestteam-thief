"""Where is the opponent? A full posterior over the board, not a guess.

A point estimate throws away the thing that matters. "Probably (5,5)" and
"(5,5) at 0.9" and "(5,5) at 0.11, and everywhere else nearly as likely" lead to
completely different play, and only a distribution can tell them apart. The Cop
needs that difference to know whether to commit to a chase or keep its options.

Two steps per turn, the standard recursive filter:

* **predict** — the opponent moved since we last looked, so mass spreads to the
  cells it could have reached. This *increases* uncertainty and must happen
  first; updating on new evidence against a stale prior is how a filter becomes
  confidently wrong.
* **update** — weight each cell by how well it explains the scent we received,
  then renormalise.

The one trap, and Ch. 4 names it: **silence is not absence.** A zero reading
says only "not within two cells". Treating it as proof would drive the posterior
to a certainty it has not earned — and a thief who works that out can walk us
into it deliberately.
"""

from __future__ import annotations

from core.domain.board import Board, Position
from core.domain.scent import EMISSION, RADIUS

__all__ = ["uniform", "predict", "update_from_scent", "mask", "normalise", "entropy", "peak"]

# How much a cell's likelihood is reduced when the scent says nothing about it.
# Not zero: a silent cell is merely unsupported, never disproved (Ch. 4).
SILENT_LIKELIHOOD = 0.05


def uniform(board: Board, barriers: frozenset[Position] = frozenset()) -> dict[Position, float]:
    """Return an even posterior over every passable cell (4.2.1.a)."""
    cells = [cell for cell in board.cells() if cell not in barriers]
    return dict.fromkeys(cells, 1.0 / len(cells)) if cells else {}


def normalise(belief: dict[Position, float]) -> dict[Position, float]:
    """Return *belief* summing to 1.0, or uniform over its keys if it summed to 0.

    A posterior that summed to zero means every hypothesis was ruled out, which
    on this board is always an error rather than a fact — the opponent is
    somewhere. Falling back to uniform loses information; asserting would crash
    a live match. Losing information is the cheaper failure.
    """
    total = sum(belief.values())
    if total <= 0.0:
        return dict.fromkeys(belief, 1.0 / len(belief)) if belief else {}
    return {cell: value / total for cell, value in belief.items()}


def predict(
    belief: dict[Position, float],
    board: Board,
    barriers: frozenset[Position] = frozenset(),
) -> dict[Position, float]:
    """Spread mass to every cell the opponent could have moved to (4.2.1.b).

    The motion model is the rulebook's own move set: stay, or one orthogonal
    step. Mass is divided evenly among the legal destinations because we have no
    reason yet to think the opponent prefers one — a bias here would be us
    inventing evidence.
    """
    spread: dict[Position, float] = {}
    for cell, mass in belief.items():
        if mass <= 0.0:
            continue
        destinations = [cell] + [
            neighbour
            for _, neighbour in board.neighbours(cell)
            if board.is_passable(neighbour, barriers)
        ]
        share = mass / len(destinations)
        for destination in destinations:
            spread[destination] = spread.get(destination, 0.0) + share
    return normalise(spread)


def _likelihood(reading: float, candidate: Position, source: Position) -> float:
    """Return how well *candidate* explains a scent *reading* at *source*.

    If the opponent stood on *candidate*, the deposit at *source* would be the
    published value for that separation. The closer the reading is to it, the
    better the explanation.
    """
    d_row, d_col = source[0] - candidate[0], source[1] - candidate[1]
    squared = d_row * d_row + d_col * d_col
    if max(abs(d_row), abs(d_col)) > RADIUS:
        # Out of emission range: this candidate predicts silence here.
        return 1.0 - min(reading, 1.0)
    return max(0.0, 1.0 - abs(EMISSION[squared] - reading))


def update_from_scent(
    belief: dict[Position, float],
    field: dict[Position, float],
    board: Board,
) -> dict[Position, float]:
    """Reweight *belief* by how well each cell explains the opponent's field (4.2.1.c).

    Args:
        belief: The predicted prior.
        field: The scent the opponent transmitted this turn.
        board: Geometry.

    An empty field leaves the belief untouched. That is the "silence is not
    absence" rule at the top level: no reading is no evidence, and a filter that
    sharpened on nothing would be manufacturing confidence.
    """
    if not field:
        return dict(belief)

    updated: dict[Position, float] = {}
    for candidate, prior in belief.items():
        weight = 1.0
        for source, reading in field.items():
            weight *= max(_likelihood(reading, candidate, source), SILENT_LIKELIHOOD)
        updated[candidate] = prior * weight
    return normalise(updated)


def mask(
    belief: dict[Position, float],
    barriers: frozenset[Position],
    own_position: Position | None = None,
) -> dict[Position, float]:
    """Drop impossible cells and renormalise (4.2.1.e).

    Barriers hold exactly zero — the opponent cannot be inside a wall — and so
    does our own cell, because if it were there the game would already be over.
    """
    blocked = set(barriers) | ({own_position} if own_position else set())
    return normalise({c: v for c, v in belief.items() if c not in blocked})


def peak(belief: dict[Position, float]) -> Position | None:
    """Return the most likely cell, breaking ties on coordinates for replay."""
    return max(sorted(belief), key=lambda cell: belief[cell]) if belief else None


def entropy(belief: dict[Position, float]) -> float:
    """Return the Shannon entropy in bits — how much we still do not know.

    0 means certainty; log2(49) ≈ 5.6 is a uniform 7×7. The Cop uses it to
    decide whether to commit to a chase or keep gathering, and it is the honest
    way to report *"the filter is working"* without cherry-picking a game.
    """
    from math import log2

    return -sum(v * log2(v) for v in belief.values() if v > 0.0)
