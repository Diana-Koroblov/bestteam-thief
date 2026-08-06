"""The pheromone trail: a 5×5 deposit that decays each turn.

Both agents emit; each reads only the **opponent's** field (Ch. 4). That
asymmetry is the whole information channel — the scent is the one signal that
cannot lie, because the hint can (M#22) and the position is never shown.

**The emission table is hardcoded because the book publishes a table, not a
formula.** Ch. 4.3 defines the deposit only as *"determined by the radial
proximity of the cell to the agent's emission centre"* — 0.9 at the centre, 0
when far — and then prints 25 numbers in a figure. No equation is given. (The
*decay* rule is stated explicitly, and ``decay()`` implements it verbatim.)

So ``d²`` below is an **index**, not a model: it selects which published value
applies. A Gaussian ``0.9·exp(−0.377·d²)`` happens to reproduce all six values,
but that is our own reverse-engineering — run once to confirm the figure is
genuinely radial rather than arbitrary — and it is deliberately not used.
Shipping it would mean shipping a *reconstruction* of a spec the book never
wrote, and M#23 requires both peers to produce byte-identical numbers.

Values read from the rulebook's figure, Ch. 4, "5×5 scent emission field".
"""

from __future__ import annotations

from core.domain.board import Board, Position

__all__ = ["EMISSION", "RADIUS", "emit", "decay", "merge", "sample", "encode", "decode"]

# Intensity by **squared Euclidean distance** from the emitting cell.
# d² = 0, 1, 2, 4, 5, 8 — the only distances a 5×5 window can produce.
EMISSION: dict[int, float] = {0: 0.90, 1: 0.62, 2: 0.42, 4: 0.20, 5: 0.14, 8: 0.04}

# A 5×5 window reaches two cells in each direction.
RADIUS = 2


def emit(centre: Position, board: Board) -> dict[Position, float]:
    """Return the field an agent standing on *centre* deposits this turn.

    Cells outside the board are dropped rather than clamped: an agent in a
    corner simply leaves a smaller trail, which is itself information — a weak
    edge reading is evidence of an edge.
    """
    row, col = centre
    field: dict[Position, float] = {}
    for d_row in range(-RADIUS, RADIUS + 1):
        for d_col in range(-RADIUS, RADIUS + 1):
            cell = (row + d_row, col + d_col)
            if board.in_bounds(cell):
                field[cell] = EMISSION[d_row * d_row + d_col * d_col]
    return field


def decay(
    field: dict[Position, float],
    rate: float,
    model: str = "multiplicative",
) -> dict[Position, float]:
    """Return *field* one turn older.

    Args:
        field: The current intensities.
        rate: ``pheromone_decay``, fixed at 0.10 by Appendix F.
        model: ``multiplicative`` — the book's ``(1−ρ)·τ``, giving 0.9 → **0.81**.
            ``subtractive`` — the reference implementation's ``τ−ρ``, giving
            0.9 → **0.80**. Both are implemented because an opponent may have
            built on the reference and we must be able to play under whichever
            was signed (CONTRADICTIONS C-007).

    Truncated at zero: a negative intensity is not a meaningful reading, and
    letting one through would put mass on cells the opponent has never visited.
    """
    if model == "subtractive":
        aged = {cell: value - rate for cell, value in field.items()}
    else:
        aged = {cell: (1.0 - rate) * value for cell, value in field.items()}
    return {cell: value for cell, value in aged.items() if value > 0.0}


def merge(
    existing: dict[Position, float],
    fresh: dict[Position, float],
) -> dict[Position, float]:
    """Combine an aged field with this turn's deposit, keeping the stronger.

    Maximum rather than sum. A sum would let an agent that lingered on one cell
    accumulate an intensity no single deposit can produce, which would read as
    "several agents" rather than "one agent, twice" — and there are only two
    agents on the board.
    """
    combined = dict(existing)
    for cell, value in fresh.items():
        combined[cell] = max(combined.get(cell, 0.0), value)
    return combined


def encode(field: dict[Position, float]) -> tuple[tuple[int, int, float], ...]:
    """Return *field* as sorted ``(row, col, intensity)`` triples, for the wire.

    **A field has to leave this process to be worth anything** (C-005): there is
    no shared board, so each peer transmits what it emitted and the opponent
    merges it. JSON has no tuple keys, so a `dict[Position, float]` cannot cross
    as it stands.

    Triples rather than a ``"r,c"``-keyed object because the receiver then parses
    integers instead of splitting strings, and a malformed cell fails loudly at
    the boundary rather than becoming a plausible wrong coordinate.

    Sorted, because the field is hashed under C-008 and two peers must produce
    identical bytes from identical data. `canonical_json` sorts *keys*, and this
    is a list — so the ordering has to be settled here or not at all.
    """
    return tuple((row, column, field[(row, column)]) for row, column in sorted(field))


def decode(rows: object) -> dict[Position, float]:
    """Return the field encoded by :func:`encode`, or ``{}`` for nothing.

    Raises:
        ValueError: A row is not three values. Loud on purpose — a silently
            dropped cell is a hole in the one channel that cannot lie, and it
            would show up as a belief filter that mysteriously underperforms.

    Absent and empty both decode to ``{}``, which the filter treats as *silence,
    not absence* (Ch. 4): no reading is no evidence, and a peer whose trail has
    genuinely decayed to nothing is not making a claim about where it is not.
    """
    if not rows:
        return {}
    field: dict[Position, float] = {}
    for row in rows:  # type: ignore[union-attr]
        if len(row) != 3:
            raise ValueError(f"a scent cell needs [row, col, intensity], got {row!r}")
        line, column, intensity = row
        field[(int(line), int(column))] = float(intensity)
    return field


def sample(field: dict[Position, float], cell: Position) -> float:
    """Return the intensity at *cell*, or 0.0 where nothing was deposited.

    Zero means **silence, not absence** (Ch. 4): the opponent may simply be
    further away than the 5×5 window reaches. Treating it as proof of absence
    would drive the belief filter to certainty it has not earned.
    """
    return field.get(cell, 0.0)
