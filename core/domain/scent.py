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

__all__ = [
    "EMISSION", "RINGS", "RADIUS", "intensity", "emit", "decay", "merge",
    "sample", "encode", "decode",
]

# Intensity by **squared Euclidean distance** from the emitting cell.
# d² = 0, 1, 2, 4, 5, 8 — the only distances a 5×5 window can produce.
# The book's figure, Ch. 4, and the shape the MULTIPLICATIVE model emits.
EMISSION: dict[int, float] = {0: 0.90, 1: 0.62, 2: 0.42, 4: 0.20, 5: 0.14, 8: 0.04}

# Intensity by **Chebyshev ring** — the shape the registered SUBTRACTIVE model
# emits (kit doc 81ebee59…): three flat rings, 0.9 / 0.6 / 0.3.
#
# 🐛 **The emission kernel is part of the model, not a constant beside it.**
# Until 16/08 there was only `EMISSION`, applied whichever model was signed, so
# a match negotiated onto subtractive emitted the book's Euclidean kernel and
# then decayed it subtractively — a hybrid belonging to no declared document.
# imreeyal's physics check refused 105 of 105 frames and reconstructed it from
# our step-1 values exactly: {0.8, 0.52, 0.32, 0.1, 0.04} on 21 cells is this
# EMISSION minus 0.1 with the four sub-zero corners dropped. We declared
# 81ebee59 and emitted something else, which is the declared-and-differ case we
# had ourselves called the worst kind — it plays fine, and then two teams'
# records disagree about physics in front of a grader.
RINGS: tuple[float, ...] = (0.90, 0.60, 0.30)

# The clamp `merge` applies after summing: the centre intensity, so no amount of
# accumulated history can exceed a single fresh deposit. `RINGS[0]` rather than a
# second literal — one number, one place, and a config that moved the centre
# would otherwise leave the ceiling behind.
CEILING: float = RINGS[0]

# A 5×5 window reaches two cells in each direction.
RADIUS = 2


def intensity(d_row: int, d_col: int, model: str = "multiplicative") -> float:
    """Return the deposit *(d_row, d_col)* away from the emitting cell.

    The two models disagree about geometry, not merely about decay:
    ``multiplicative`` falls off with squared Euclidean distance (the book's
    figure), ``subtractive`` with the Chebyshev ring (the registered doc). A
    peer that gets this wrong still plays a legal game and still produces
    verifiable commits, which is precisely why it survives undetected until an
    opponent checks the physics.
    """
    if model == "subtractive":
        return RINGS[max(abs(d_row), abs(d_col))]
    return EMISSION[d_row * d_row + d_col * d_col]


def emit(
    centre: Position, board: Board, model: str = "multiplicative"
) -> dict[Position, float]:
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
                field[cell] = intensity(d_row, d_col, model)
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
    ceiling: float = CEILING,
) -> dict[Position, float]:
    """Combine an aged field with this turn's deposit: **sum, then clamp**.

    ``min(ceiling, aged + fresh)`` — the construction `multiplicative_book_v1`
    pins, and the one yanell11 run:

        value = max(0.0, survive * tau.get(cell, 0.0) + fresh)
        if ceiling is not None:
            value = min(ceiling, value)

    **This was `max` until 17/08, and it was our divergence to fix.** The
    argument for it was not silly — a sum lets an agent that lingers accumulate
    an intensity no single deposit produces, which reads as "several agents"
    rather than "one agent, twice". The clamp is what answers that: capped at the
    centre intensity, no history can exceed one fresh deposit, so the objection
    disappears and the sum stays faithful to the document.

    What settled it is that both peers now declare
    ``934c220d…`` — the registry hash *for that document*. A hash naming a model
    neither side runs exactly is worth less than the same hash naming one both
    do, and we had offered to match theirs if they preferred it. They did.

    Identical to `max` for a single emission and wherever two fields do not
    overlap; different where they do — which on a 7x7 with an agent re-emitting
    near itself is most turns near the trail head, not a corner case.
    """
    combined = dict(existing)
    for cell, value in fresh.items():
        combined[cell] = min(ceiling, combined.get(cell, 0.0) + value)
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
