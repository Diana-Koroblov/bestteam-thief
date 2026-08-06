"""The belief filter, shared by the harness and the wire (TODO 4.1.6, 4.2.1).

`test_belief.py` covers the maths — predict, update, mask — one step at a time.
What is left is the thing that only exists once they are joined: **a turn**, and
the rule that a peer may only ever act on evidence a turn old.

This file is the guard for the defect it was written after. `BeliefFilter` did
not exist; the harness had a private copy and the live runtime had none, so the
two could not be compared and in fact disagreed for the whole of Phase 8. Every
test here is written to fail if they diverge again.
"""

from __future__ import annotations

from core.domain.belief import entropy, mask, peak, predict, uniform
from core.domain.board import Board
from core.domain.filter import BeliefFilter
from core.domain.scent import emit

BOARD = Board(grid_size=7)
NO_WALLS: frozenset = frozenset()


def filter_at(rate: float = 0.10, model: str = "multiplicative") -> BeliefFilter:
    """A fresh filter on the standard board."""
    return BeliefFilter(board=BOARD, rate=rate, model=model)


# --- what it starts with ----------------------------------------------------


def test_it_starts_uniform_over_the_whole_board() -> None:
    """Honest ignorance (4.2.1.a). log2(49) is ~5.61 bits."""
    assert filter_at().belief == uniform(BOARD)
    assert abs(entropy(filter_at().belief) - 5.61) < 0.01


def test_it_starts_with_no_trail_at_all() -> None:
    """Nothing has been emitted, so there is nothing to transmit."""
    assert filter_at().trail == {}


# --- what it emits ----------------------------------------------------------


def test_a_deposit_is_the_field_we_transmit() -> None:
    """C-005: the returned field is what goes on the wire, current turn
    included, because that is what the reference sends and most opponents will
    therefore expect."""
    side = filter_at()
    assert side.deposit((3, 3)) == emit((3, 3), BOARD)
    assert side.trail == emit((3, 3), BOARD)


def test_the_trail_decays_under_the_negotiated_model() -> None:
    """C-007: either model may have been signed, and reconstructing with the
    wrong one drifts a little every turn."""
    book, reference = filter_at(model="multiplicative"), filter_at(model="subtractive")
    book.deposit((0, 6))
    reference.deposit((0, 6))
    book.deposit((6, 0))
    reference.deposit((6, 0))
    assert abs(book.trail[(0, 6)] - 0.81) < 1e-9
    assert abs(reference.trail[(0, 6)] - 0.80) < 1e-9


# --- what it believes -------------------------------------------------------


def test_a_reading_moves_the_posterior_onto_the_source() -> None:
    """The filter's whole job: turn a smear of intensities into a cell."""
    side = filter_at()
    side.observe(emit((5, 5), BOARD), NO_WALLS, (0, 0))
    assert peak(side.belief) == (5, 5)
    assert entropy(side.belief) < 2.0


def test_silence_is_not_absence() -> None:
    """Ch. 4's own phrase: an empty field is *no evidence*, and a filter that
    sharpened on nothing would manufacture confidence a thief could walk us into.

    Asserted as an equality against predict-then-mask rather than as "entropy
    must not fall", which is what this test first claimed and is **false**:
    masking removes our own cell, and a distribution over 48 cells carries less
    entropy than one over 49 however little was learned. That is legitimate
    information — the opponent is not standing where we are — so the honest
    claim is narrower. The *update* step must contribute nothing at all.
    """
    side = filter_at()
    expected = mask(predict(uniform(BOARD), BOARD, NO_WALLS), NO_WALLS, (0, 0))
    assert side.observe({}, NO_WALLS, (0, 0)) == expected


def test_prediction_runs_before_the_update() -> None:
    """Order is the difference between a filter and a confidently wrong one: the
    opponent moved since we last looked, so the prior must widen before new
    evidence narrows it.

    Asserted through a consequence — after a sighting, the cells one step from
    the source hold mass. A filter that updated first and predicted afterwards
    would smear the sharpened posterior instead, leaving the source no more
    likely than its neighbours.
    """
    side = filter_at()
    side.observe(emit((3, 3), BOARD), NO_WALLS, (0, 0))
    assert side.belief[(3, 3)] > side.belief[(3, 4)] > 0.0


def test_walls_and_our_own_cell_hold_exactly_zero() -> None:
    """4.2.1.e. Not a small number that looks like zero — absent."""
    side = filter_at()
    side.observe(emit((3, 3), BOARD), frozenset({(2, 2)}), (0, 0))
    assert (2, 2) not in side.belief
    assert (0, 0) not in side.belief
    assert abs(sum(side.belief.values()) - 1.0) < 1e-9


# --- the sub-game boundary --------------------------------------------------


def test_a_reset_returns_it_to_honest_ignorance() -> None:
    """A posterior carried across the boundary would describe a board the rules
    have just rebuilt, and a trail would have us chasing a finished game."""
    side = filter_at()
    side.deposit((3, 3))
    side.observe(emit((5, 5), BOARD), NO_WALLS, (0, 0))
    side.reset()
    assert side.trail == {}
    assert side.belief == uniform(BOARD)


# --- one filter, two callers ------------------------------------------------


def test_two_filters_do_not_share_state() -> None:
    """Held per peer, because in a real match neither side can see the other's.
    Sharing one object between two agents would silently make the harness
    measure a game nobody is playing."""
    first, second = filter_at(), filter_at()
    first.deposit((0, 0))
    assert second.trail == {}
    assert first.trail != second.trail
