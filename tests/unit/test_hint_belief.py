"""What a hint does to the posterior, scaled by trust (TODO 4.2.1.d).

Split from ``test_reliability.py`` when that file passed the 150-line rule —
and the seam is a real one. That file asks *"how honest has this opponent
been?"*; this one asks *"so what should we do with what they just said?"*

The rule underneath every test here: **the scent is a fact, the hint is an
argument.** Words may tilt the posterior. They may never dominate it, and they
may never eliminate a cell.
"""

from __future__ import annotations

import pytest

from core.domain.actions import Direction
from core.domain.belief import uniform
from core.domain.belief_hints import update_from_hint
from core.domain.board import Board
from core.domain.hint_parser import ParsedHint, parse
from core.domain.reliability import Reliability

BOARD = Board(grid_size=7)

def _northward_share(text: str, record: Reliability) -> float:
    """Fraction of the posterior sitting in the northern half after the tilt.

    **Measured as mass, not as the peak.** The first version of these tests
    asked where ``peak()`` landed, and from a uniform prior that is decided by
    tie-breaking rather than by evidence: tilting a flat distribution leaves the
    interior flat and only moves the edges. The peak read row 1 whichever way
    the hint pointed, so the test passed for the truthful case and failed for
    the liar — for the same wrong reason both times.
    """
    belief = update_from_hint(uniform(BOARD), parse(text), record.trust, BOARD)
    total = sum(belief.values())
    return sum(v for (row, _), v in belief.items() if row < 3) / total


def test_a_strangers_words_change_nothing() -> None:
    """Trust is 0, so the update is a deliberate no-op."""
    before = uniform(BOARD)
    after = update_from_hint(before, parse("I go north."), Reliability().trust, BOARD)
    assert after == before


def test_a_truthful_opponents_claim_moves_mass_toward_it() -> None:
    honest = Reliability(truths=20.0, lies=1.0)
    baseline = 3 / 7  # rows 0-2 of 7, before any tilt
    assert _northward_share("I am heading north.", honest) > baseline


def test_a_liars_claim_moves_mass_the_other_way() -> None:
    """**The DoD, and the reason this extension is worth the code.**

    Against an opponent whose record says 0.05, "I am going north" is evidence
    for *south*. A liar who is consistent has told us where they are.
    """
    liar = Reliability(truths=1.0, lies=20.0)
    honest = Reliability(truths=20.0, lies=1.0)
    baseline = 3 / 7
    assert _northward_share("I am heading north.", liar) < baseline
    assert _northward_share("I am heading north.", liar) < _northward_share(
        "I am heading north.", honest
    )


def test_an_unusable_hint_is_ignored_however_trusted_the_opponent() -> None:
    """Two gates, and both must open: understood *and* worth believing.

    Confusing them would let a clearly-worded lie count as strong evidence
    merely because the speaker is usually honest.
    """
    honest = Reliability(truths=20.0, lies=1.0)
    before = uniform(BOARD)
    for text in ("You will never catch me.", "North then west."):
        assert update_from_hint(before, parse(text), honest.trust, BOARD) == before


def test_words_alone_never_drive_a_cell_to_zero() -> None:
    """The scent is a fact; the hint is an argument. Arguments do not eliminate."""
    honest = Reliability(truths=50.0, lies=1.0)
    after = update_from_hint(uniform(BOARD), parse("I go north."), honest.trust, BOARD)
    assert all(value > 0.0 for value in after.values())
    assert abs(sum(after.values()) - 1.0) < 1e-9


def test_the_tilt_stays_bounded_even_at_total_trust() -> None:
    """A hint must never outweigh the scent field, which cannot lie."""
    after = update_from_hint(uniform(BOARD), ParsedHint(Direction.N, 1.0, "north"), 1.0, BOARD)
    assert max(after.values()) < 4 * (1 / 49)


def test_the_description_reports_the_sample_size() -> None:
    """"0.31 over 24 checked" is a claim; "0.31" alone might rest on one reading."""
    record = Reliability()
    for _ in range(24):
        record.record(truthful=False)
    assert "24 checked" in record.describe()
    assert "deceptive" in record.describe()


# --- the overwrite bug (caught on Windows, invisible on Linux) --------------


def _share_toward(direction: Direction, belief: dict) -> float:
    """Mass in the half-board *direction* points at."""
    total = sum(belief.values())
    if direction in (Direction.N, Direction.S):
        rows = range(0, 3) if direction is Direction.N else range(4, 7)
        return sum(v for (r, _), v in belief.items() if r in rows) / total
    cols = range(0, 3) if direction is Direction.W else range(4, 7)
    return sum(v for (_, c), v in belief.items() if c in cols) / total


@pytest.mark.parametrize("claimed", [Direction.N, Direction.S, Direction.E, Direction.W])
def test_the_tilt_works_in_all_four_directions(claimed: Direction) -> None:
    """**The regression test for a bug that only appeared in some directions.**

    Both writes in ``update_from_hint`` used to *assign* rather than accumulate.
    A cell would receive mass from its neighbour, then the loop would reach that
    cell and overwrite the contribution — so whether the tilt worked depended
    entirely on whether the iteration visited donors before recipients.

    Tilting north worked. Tilting south did **nothing**, silently returning a
    still-uniform posterior. The result was a filter that could read a truthful
    opponent but not a liar, which is the case this module exists for. It
    surfaced on Windows/3.12 and not on Linux/3.10, so a single-direction test
    would have shipped it.
    """
    honest = Reliability(truths=20.0, lies=1.0)
    hint = ParsedHint(claimed, 0.9, "…")
    after = update_from_hint(uniform(BOARD), hint, honest.trust, BOARD)
    assert _share_toward(claimed, after) > _share_toward(claimed, uniform(BOARD))


@pytest.mark.parametrize("claimed", [Direction.N, Direction.S, Direction.E, Direction.W])
def test_a_liar_is_inverted_in_all_four_directions(claimed: Direction) -> None:
    """The same bug from the other side: every claim must invert, not just north."""
    liar = Reliability(truths=1.0, lies=20.0)
    hint = ParsedHint(claimed, 0.9, "…")
    after = update_from_hint(uniform(BOARD), hint, liar.trust, BOARD)
    assert _share_toward(claimed, after) < _share_toward(claimed, uniform(BOARD))


def test_the_tilt_does_not_depend_on_iteration_order() -> None:
    """Order-independence, asserted directly rather than hoped for."""
    hint = ParsedHint(Direction.S, 0.9, "…")
    forward = uniform(BOARD)
    reversed_belief = dict(reversed(list(forward.items())))
    first = update_from_hint(forward, hint, 0.9, BOARD)
    second = update_from_hint(reversed_belief, hint, 0.9, BOARD)
    assert all(abs(first[c] - second[c]) < 1e-12 for c in first)


def test_edge_mass_is_kept_rather_than_drained() -> None:
    """A cell with nowhere to send mass keeps it.

    Draining it would bias the posterior away from the board edges — an opinion
    about geometry that no hint ever expressed.
    """
    hint = ParsedHint(Direction.N, 1.0, "…")
    after = update_from_hint(uniform(BOARD), hint, 1.0, BOARD)
    assert abs(sum(after.values()) - 1.0) < 1e-9
    assert all(value > 0.0 for value in after.values())


def test_the_decayed_score_is_recorded_but_never_read_by_the_belief() -> None:
    """**A one-shot betrayal is bounded by the tilt cap, not by the coefficient.**

    Measured: at *maximum* trust a single hint moves the northern-half mass from
    0.429 to 0.449 — two percentage points. Reputation is backward-looking and
    the decisive lie is the last thing that happens, so detecting it one turn
    later cannot help. The cap is what makes the attack survivable, and it is
    already in force.
    """
    record = Reliability()
    for step in range(12):
        record.record(True, step=step)
    before = update_from_hint(uniform(BOARD), parse("I go north."), record.trust, BOARD)
    record.record(False, step=12)
    after = update_from_hint(uniform(BOARD), parse("I go north."), record.trust, BOARD)
    assert before != after  # the plain coefficient did move
    assert max(after.values()) < 4 * (1 / 49)  # but the tilt stays capped
