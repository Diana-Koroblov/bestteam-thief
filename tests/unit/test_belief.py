"""Unit tests for the belief filter (TODO 4.2).

Two properties do the work. The posterior must stay a **distribution** — every
update renormalises, blocked cells hold exactly zero — and it must never become
more confident than the evidence allows. The second is the one a clever thief
attacks.
"""

from __future__ import annotations

from math import log2

from core.domain.belief import (
    entropy,
    mask,
    normalise,
    peak,
    predict,
    uniform,
    update_from_scent,
)
from core.domain.board import Board
from core.domain.scent import emit

BOARD = Board(grid_size=7)


def test_it_starts_uniform_over_the_whole_board() -> None:
    """4.2.1.a: 1/49 everywhere, knowing nothing."""
    belief = uniform(BOARD)
    assert len(belief) == 49
    assert all(abs(v - 1 / 49) < 1e-12 for v in belief.values())
    assert abs(entropy(belief) - log2(49)) < 1e-9


def test_every_step_leaves_a_distribution() -> None:
    """4.2.1: sums to 1.0 after every update, or the numbers mean nothing."""
    belief = uniform(BOARD)
    for _ in range(3):
        belief = predict(belief, BOARD)
        belief = update_from_scent(belief, emit((5, 5), BOARD), BOARD)
        belief = mask(belief, frozenset({(1, 1)}), (0, 0))
        assert abs(sum(belief.values()) - 1.0) < 1e-9


# --- prediction -------------------------------------------------------------


def test_prediction_spreads_mass_to_reachable_cells_only() -> None:
    """4.2.1.b: the motion model is the rulebook's move set, nothing wider."""
    spread = predict({(3, 3): 1.0}, BOARD)
    assert set(spread) == {(3, 3), (2, 3), (4, 3), (3, 2), (3, 4)}
    assert all(abs(v - 0.2) < 1e-12 for v in spread.values())


def test_prediction_respects_barriers() -> None:
    spread = predict({(3, 3): 1.0}, BOARD, frozenset({(2, 3), (3, 4)}))
    assert (2, 3) not in spread and (3, 4) not in spread


def test_prediction_increases_uncertainty() -> None:
    """The opponent moved since we last looked, so we must know *less*."""
    certain = {(3, 3): 1.0}
    assert entropy(predict(certain, BOARD)) > entropy(certain)


def test_a_cornered_prediction_has_fewer_destinations() -> None:
    assert set(predict({(0, 0): 1.0}, BOARD)) == {(0, 0), (1, 0), (0, 1)}


# --- update -----------------------------------------------------------------


def test_a_scent_reading_finds_the_source() -> None:
    """4.2.1.c. One observation is enough to locate a stationary opponent."""
    belief = update_from_scent(uniform(BOARD), emit((5, 5), BOARD), BOARD)
    assert peak(belief) == (5, 5)
    assert belief[(5, 5)] > 0.5


def test_the_update_collapses_entropy() -> None:
    """5.61 bits of ignorance down to under 1 bit, from a single reading."""
    before = uniform(BOARD)
    after = update_from_scent(before, emit((5, 5), BOARD), BOARD)
    assert entropy(before) > 5.5
    assert entropy(after) < 1.0


def test_an_empty_field_changes_nothing() -> None:
    """**Silence is not absence** (Ch. 4).

    No reading is no evidence. A filter that sharpened on an empty field would
    be manufacturing confidence out of nothing — and a thief who noticed could
    walk us into it on purpose.
    """
    before = uniform(BOARD)
    assert update_from_scent(before, {}, BOARD) == before


def test_a_silent_cell_is_never_ruled_out_entirely() -> None:
    """A zero reading means "not within two cells", not "not on the board"."""
    belief = update_from_scent(uniform(BOARD), emit((0, 0), BOARD), BOARD)
    assert belief[(6, 6)] > 0.0
    assert peak(belief) == (0, 0)


def test_two_readings_of_a_mover_track_it() -> None:
    """The filter must follow a moving target, not lock onto its first sighting."""
    belief = update_from_scent(uniform(BOARD), emit((1, 1), BOARD), BOARD)
    belief = predict(belief, BOARD)
    belief = update_from_scent(belief, emit((1, 2), BOARD), BOARD)
    assert peak(belief) == (1, 2)


# --- masking and helpers ----------------------------------------------------


def test_barriers_hold_exactly_zero() -> None:
    """4.2.1.e: the opponent cannot be inside a wall."""
    masked = mask(uniform(BOARD), frozenset({(2, 2), (4, 4)}), None)
    assert (2, 2) not in masked and (4, 4) not in masked
    assert abs(sum(masked.values()) - 1.0) < 1e-9


def test_our_own_cell_is_excluded() -> None:
    """If the opponent were here the sub-game would already be over."""
    assert (0, 0) not in mask(uniform(BOARD), frozenset(), (0, 0))


def test_the_peak_breaks_ties_on_coordinates() -> None:
    """Two peers replaying the same log must reach the same cell."""
    assert peak({(3, 3): 0.5, (1, 1): 0.5}) == (1, 1)
    assert peak({}) is None


def test_a_collapsed_posterior_falls_back_to_uniform_rather_than_crashing() -> None:
    """Every hypothesis ruled out is always an error, never a fact.

    The opponent *is* somewhere. Losing information is a cheaper failure than
    crashing a live match, which would be a technical loss worth 0 to both.
    """
    recovered = normalise({(0, 0): 0.0, (1, 1): 0.0})
    assert abs(sum(recovered.values()) - 1.0) < 1e-9


def test_entropy_reports_certainty_as_zero() -> None:
    assert entropy({(3, 3): 1.0}) == 0.0
    assert entropy({}) == 0.0
