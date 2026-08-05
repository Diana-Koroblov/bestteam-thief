"""What a Thief position is worth (TODO 8.2.1-8.2.4).

Each term is isolated by zeroing every other weight. `capture_risk` gets the most
tests because it is the mirror of the Cop's win condition — the single most
valuable line in this evaluation (A2.4), and the one whose failure looks like
ordinary play right up until the sub-game ends.
"""

from __future__ import annotations

from core.domain.board import Board
from thief.evaluation import ThiefWeights, capture_risk, evaluate, seal_pressure

BOARD = Board(grid_size=7)
_FIELDS = ("capture_risk", "seal_pressure", "room", "cycle", "scent", "distance")


def only(term: str) -> ThiefWeights:
    """Return weights with every term zeroed but *term*, at weight 1."""
    return ThiefWeights(**{name: (1.0 if name == term else 0.0) for name in _FIELDS})


# --- A2.4 the losing state --------------------------------------------------


def test_a_sealed_cell_is_total_risk() -> None:
    """M#47: no free neighbour is a capture, not a near-capture — and it holds
    wherever the Cop happens to be."""
    walls = frozenset({(0, 1), (1, 0)})
    assert capture_risk((0, 0), {(6, 6): 1.0}, walls, BOARD) == 1.0


def test_one_exit_with_the_cop_beside_it_is_the_losing_state() -> None:
    """**§2.2 read from the other side.** Exit count 1 and the Cop within
    placement range of that exit is exactly what the Cop is playing for."""
    walls = frozenset({(0, 1)})
    assert capture_risk((0, 0), {(1, 1): 1.0}, walls, BOARD) == 1.0


def test_one_exit_with_the_cop_standing_on_it_also_counts() -> None:
    """Ch. 3.4 lets the Cop wall its own cell, so a Cop *on* our last exit is as
    lethal as one beside it."""
    walls = frozenset({(0, 1)})
    assert capture_risk((0, 0), {(1, 0): 1.0}, walls, BOARD) == 1.0


def test_an_adjacent_cop_can_simply_step_onto_us() -> None:
    """The third way the sub-game ends, and the one a barrier-only reading of
    the rules would miss."""
    assert capture_risk((3, 3), {(3, 4): 1.0}, frozenset(), BOARD) == 1.0


def test_a_distant_cop_is_no_immediate_risk() -> None:
    """Four exits and nothing in reach. Confirms the test above is not vacuous."""
    assert capture_risk((3, 3), {(0, 0): 1.0}, frozenset(), BOARD) == 0.0


def test_risk_is_mass_not_a_verdict() -> None:
    """The Cop's position is a belief. A 30% chance of being caught next turn is
    a price to weigh, not a veto to obey."""
    belief = {(3, 4): 0.3, (0, 0): 0.7}
    assert capture_risk((3, 3), belief, frozenset(), BOARD) == 0.3


def test_the_risk_penalty_dominates_every_other_term() -> None:
    """Being caught is the sub-game lost, not a weak position."""
    weights = ThiefWeights()
    doomed = evaluate((3, 3), {(3, 4): 1.0}, frozenset(), BOARD, 14, weights)
    safe = evaluate((3, 3), {(0, 0): 1.0}, frozenset(), BOARD, 14, weights)
    assert doomed < safe - weights.capture_risk / 2


# --- A2.3 and A2.8 the cop's remaining quota --------------------------------


def test_a_spent_quota_means_no_seal_pressure() -> None:
    """A Cop with no walls left cannot close anything, however tight we are."""
    assert seal_pressure((0, 0), frozenset(), BOARD, 0) == 0.0


def test_a_wide_cell_is_safe_from_a_small_quota() -> None:
    """Four exits needs three walls; with two left it cannot be done."""
    assert seal_pressure((3, 3), frozenset(), BOARD, 2) == 0.0


def test_pressure_rises_as_the_quota_covers_the_gap() -> None:
    """**A2.8.** Fourteen walls and two walls are different games, and a fixed
    threshold would play both the same."""
    corner = seal_pressure((0, 0), frozenset(), BOARD, 14)
    middle = seal_pressure((3, 3), frozenset(), BOARD, 14)
    assert corner > middle > 0.0


def test_pressure_is_never_negative() -> None:
    """A huge quota against a wide open cell is safe, not *extra* safe — a
    negative would let the Thief bank credit for the Cop being over-supplied."""
    assert seal_pressure((3, 3), frozenset(), BOARD, 99) >= 0.0


# --- A2.1 and A2.7 room and cycles ------------------------------------------


def test_more_escape_room_scores_higher() -> None:
    """**A2.1.** Reachable cells several steps ahead, not immediate distance."""
    weights = only("room")
    open_board = evaluate((3, 3), {(0, 0): 1.0}, frozenset(), BOARD, 14, weights)
    boxed = evaluate((3, 3), {(0, 0): 1.0}, frozenset({(2, 3), (4, 3), (3, 2)}), BOARD, 14, weights)
    assert open_board > boxed


def test_a_region_with_a_cycle_scores_higher() -> None:
    """**A2.7, the direct counter to the Cop's §3.3.** A cycle is what lets one
    evader outlast one pursuer indefinitely."""
    weights = only("cycle")
    keep = {(r, c) for r in range(3) for c in range(3)} - {(1, 1)}
    ring = frozenset(cell for cell in BOARD.cells() if cell not in keep)
    assert evaluate((0, 0), {(6, 6): 1.0}, ring, BOARD, 14, weights) > evaluate(
        (0, 0), {(6, 6): 1.0}, ring | {(0, 1)}, BOARD, 14, weights
    )


def test_distance_still_counts_but_only_a_little() -> None:
    """Kept as the smallest term: a far cell with one exit is worse than a near
    cell with four, and raw distance is what sent the baseline into the corner."""
    weights = only("distance")
    assert evaluate((6, 6), {(0, 0): 1.0}, frozenset(), BOARD, 14, weights) > evaluate(
        (1, 1), {(0, 0): 1.0}, frozenset(), BOARD, 14, weights
    )


def test_room_beats_distance_at_the_shipped_weights() -> None:
    """The trade the baseline got wrong: it ran to (6,6) and sat there for 29
    turns, because the far corner maximises distance and is also the square a Cop
    seals with two barriers."""
    weights = ThiefWeights()
    corner = evaluate((6, 6), {(0, 0): 1.0}, frozenset(), BOARD, 14, weights)
    inside = evaluate((5, 5), {(0, 0): 1.0}, frozenset(), BOARD, 14, weights)
    assert inside > corner


# --- configuration ----------------------------------------------------------


def test_weights_come_from_config_when_it_offers_them() -> None:
    """Tuning must not need a code change; the defaults must not need a config."""

    class Stub:
        def get(self, path: str, default: object = None) -> object:
            return 7.0 if path == "strategy.weight_cycle" else default

    weights = ThiefWeights.from_config(Stub())
    assert weights.cycle == 7.0
    assert weights.capture_risk == ThiefWeights().capture_risk


def test_a_missing_config_still_produces_a_playable_thief() -> None:
    """A fresh clone with no tuning file must field a strategy, not a stub."""
    assert ThiefWeights.from_config(None) == ThiefWeights()
