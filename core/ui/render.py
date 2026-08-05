"""Plain-text rendering of a board. No dependencies, works over SSH.

Exists so milestone M1 can be *seen* rather than only asserted (TODO 1.QG.4).
The Tkinter GUI arrives in Phase 5; this is what makes the engine inspectable
until then, and it stays useful afterwards for debugging a failed match from a
log without launching a window.

Excluded from coverage (`pyproject.toml` omits `core/ui/*`) because asserting on
box-drawing characters tests the drawing, not the game.

**Takes plain numbers, not a `Board`.** It used to accept the engine object,
which meant `core/ui/` imported `core.domain` — a breach of X §4.1 and TODO
7.5.4 that survived because the boundary test only looked for
`core.runtime`, `core.protocol` and `core.infra`. A `Board` is duck-typed here
now: anything with `grid_size` and the two index bounds will do, so the module
depends on a shape rather than on a class.
"""

from __future__ import annotations

from typing import Any

__all__ = ["render", "legend"]

Position = tuple[int, int]

COP = "C"
THIEF = "T"
BOTH = "X"
BARRIER = "#"
EMPTY = "."


def _symbol(cell: Position, cop: Position, thief: Position, barriers: frozenset[Position]) -> str:
    """Return the single character for *cell*.

    Agents are drawn on top of barriers deliberately. A barrier under an agent
    should be impossible, so if one ever appears the rendering must not hide it
    — ``X`` on a cell that is also in *barriers* is a visible contradiction.
    """
    if cop == thief == cell:
        return BOTH
    if cell == cop:
        return COP
    if cell == thief:
        return THIEF
    return BARRIER if cell in barriers else EMPTY


def render(
    board: Any,
    cop: Position,
    thief: Position,
    barriers: frozenset[Position] = frozenset(),
) -> str:
    """Return the board as text, with row and column indices.

    Indices are drawn because every coordinate dispute in this project comes
    from disagreeing about which axis is which (CONTRADICTIONS C-010). A picture
    with labelled axes settles it in one glance.
    """
    span = range(board.origin_index, board.last_index + 1)
    header = "    " + " ".join(f"{col}" for col in span)
    lines = [header, "   +" + "-" * (2 * board.grid_size - 1) + "+"]
    for row in span:
        cells = " ".join(_symbol((row, col), cop, thief, barriers) for col in span)
        lines.append(f"{row:2d} |{cells}|")
    lines.append("   +" + "-" * (2 * board.grid_size - 1) + "+")
    return "\n".join(lines)


def legend() -> str:
    """Return a one-line key for the symbols used by ``render``."""
    return f"{COP}=cop  {THIEF}=thief  {BARRIER}=barrier  {EMPTY}=free  {BOTH}=capture"
