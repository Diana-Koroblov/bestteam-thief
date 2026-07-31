"""Unit tests for the scent engine (TODO 4.1).

The values are checked against the rulebook's figure directly. They are part of
the signed pre-match agreement (M#23), so "close enough" is not a category that
exists here — a peer whose table differs by 0.01 fails the digest comparison and
the match does not start.
"""

from __future__ import annotations

import pytest

from core.domain.board import Board
from core.domain.scent import EMISSION, decay, emit, merge, sample

BOARD = Board(grid_size=7)
CENTRE = (3, 3)

# The book's figure, Ch. 4, read row by row around the emitting cell.
BOOK_FIGURE = [
    [0.04, 0.14, 0.20, 0.14, 0.04],
    [0.14, 0.42, 0.62, 0.42, 0.14],
    [0.20, 0.62, 0.90, 0.62, 0.20],
    [0.14, 0.42, 0.62, 0.42, 0.14],
    [0.04, 0.14, 0.20, 0.14, 0.04],
]


def test_the_emission_reproduces_the_book_figure_exactly() -> None:
    """4.1.1. Every one of the 25 cells, not a spot check."""
    field = emit(CENTRE, BOARD)
    for d_row, row in enumerate(BOOK_FIGURE, start=-2):
        for d_col, expected in enumerate(row, start=-2):
            cell = (CENTRE[0] + d_row, CENTRE[1] + d_col)
            assert field[cell] == expected, cell


def test_the_centre_is_the_appendix_f_value() -> None:
    assert emit(CENTRE, BOARD)[CENTRE] == 0.90
    assert EMISSION[0] == 0.90


def test_the_field_is_symmetric() -> None:
    """A directional trail would leak which way the agent was facing."""
    field = emit(CENTRE, BOARD)
    for d_row in range(-2, 3):
        for d_col in range(-2, 3):
            here = field[(CENTRE[0] + d_row, CENTRE[1] + d_col)]
            assert here == field[(CENTRE[0] - d_row, CENTRE[1] + d_col)]
            assert here == field[(CENTRE[0] + d_row, CENTRE[1] - d_col)]


def test_intensity_falls_with_distance() -> None:
    assert list(EMISSION.values()) == sorted(EMISSION.values(), reverse=True)


def test_a_corner_emits_a_smaller_field() -> None:
    """Not clamped — a weak edge reading is itself evidence of an edge."""
    field = emit((0, 0), BOARD)
    assert len(field) == 9
    assert field[(0, 0)] == 0.90
    assert (-1, 0) not in field


def test_a_full_field_covers_twenty_five_cells() -> None:
    assert len(emit(CENTRE, BOARD)) == 25


# --- decay ------------------------------------------------------------------


def test_the_book_model_gives_the_worked_example() -> None:
    """4.1.2 and M#23: 0.9 decays to **0.81**, which is what we exchange."""
    assert round(decay({CENTRE: 0.90}, 0.10)[CENTRE], 10) == 0.81


def test_the_reference_model_gives_a_different_number() -> None:
    """C-007: the reference's subtractive decay gives 0.80, not 0.81.

    Catching this in the pre-match exchange also identifies which
    implementation the opponent built on.
    """
    assert round(decay({CENTRE: 0.90}, 0.10, "subtractive")[CENTRE], 10) == 0.80


def test_the_two_models_diverge_immediately() -> None:
    field = {CENTRE: 0.90}
    assert decay(field, 0.10) != decay(field, 0.10, "subtractive")


def test_decay_never_goes_negative() -> None:
    """4.1.4. A negative reading would put belief on cells never visited."""
    faded = decay({CENTRE: 0.04}, 0.10, "subtractive")
    assert CENTRE not in faded
    assert all(value > 0 for value in faded.values())


def test_a_deposit_crosses_half_peak_around_turn_seven() -> None:
    """Ch. 4's stated behaviour, under the book's multiplicative model."""
    value = 0.90
    turns = 0
    while value > 0.45:
        value = (1 - 0.10) * value
        turns += 1
    assert turns == 7


# --- merging and sampling ---------------------------------------------------


def test_merging_keeps_the_stronger_reading() -> None:
    """Maximum, not sum.

    A sum would let an agent that lingered on one cell reach an intensity no
    single deposit can produce, which reads as "several agents" — and there are
    only two on the board.
    """
    merged = merge({CENTRE: 0.42}, {CENTRE: 0.90})
    assert merged[CENTRE] == 0.90
    assert merge({CENTRE: 0.90}, {CENTRE: 0.42})[CENTRE] == 0.90


def test_merging_keeps_cells_from_both_fields() -> None:
    merged = merge({(1, 1): 0.2}, {(5, 5): 0.4})
    assert merged == {(1, 1): 0.2, (5, 5): 0.4}


def test_an_unvisited_cell_reads_zero() -> None:
    assert sample(emit(CENTRE, BOARD), (0, 0)) == 0.0


@pytest.mark.parametrize("cell,expected", [((3, 3), 0.90), ((3, 4), 0.62), ((1, 1), 0.04)])
def test_sampling_returns_the_deposited_value(cell, expected) -> None:
    assert sample(emit(CENTRE, BOARD), cell) == expected


def test_silence_is_not_absence() -> None:
    """Ch. 4's own phrasing, and the trap the belief filter must not fall into.

    A zero reading only says the opponent is not within two cells. Reading it
    as proof of absence would drive the posterior to a certainty it has not
    earned — and the thief can exploit exactly that.
    """
    field = emit((6, 6), BOARD)
    assert sample(field, (0, 0)) == 0.0
    assert sample(field, (6, 6)) == 0.90


# --- the M#23 signed model --------------------------------------------------


def test_the_worked_example_carries_the_number_not_just_a_label() -> None:
    """C-007 caught before the first move rather than in the audit.

    A label can be agreed while the arithmetic still differs. A number cannot.
    """
    from core.crypto.scent_model import scent_model_payload

    book = scent_model_payload(0.10, "multiplicative", 5)
    reference = scent_model_payload(0.10, "subtractive", 5)
    assert book["worked_example"]["after_one_turn"] == 0.81
    assert reference["worked_example"]["after_one_turn"] == 0.80


def test_the_two_models_produce_different_digests() -> None:
    """The whole point: a mismatch is detectable at the handshake."""
    from core.crypto.scent_model import scent_model_digest

    assert scent_model_digest(0.10, "multiplicative", 5) != scent_model_digest(
        0.10, "subtractive", 5
    )


def test_the_payload_carries_the_full_emission_table() -> None:
    from core.crypto.scent_model import scent_model_payload

    table = scent_model_payload(0.10, "multiplicative", 5)["emission_by_squared_distance"]
    assert table == {"0": 0.90, "1": 0.62, "2": 0.42, "4": 0.20, "5": 0.14, "8": 0.04}


def test_the_digest_is_stable_across_calls() -> None:
    """Two peers computing it independently must agree, so it cannot vary."""
    from core.crypto.scent_model import scent_model_digest

    assert len({scent_model_digest(0.10, "multiplicative", 5) for _ in range(10)}) == 1
