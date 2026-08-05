"""What the Cop thinks a position is worth (TODO 8.1.2, 8.1.3, 8.1.8).

Each term is tested **in isolation**, by zeroing every other weight. An
evaluation is a sum, and a sum tested only as a whole hides sign errors: a
separation penalty entered with the wrong sign still produces plausible play
right up until the turn it walls the Cop away from the Thief and loses the
sub-game outright.
"""

from __future__ import annotations

from core.domain.board import Board
from police.evaluation import CopWeights, endgame_mass, evaluate, separation_mass

BOARD = Board(grid_size=7)

# A pocket: the 2x2 corner, sealed off from the rest of the board.
POCKET_WALLS = frozenset({(0, 2), (1, 2), (2, 0), (2, 1), (2, 2)})
IN_POCKET = {(0, 0): 1.0}


def only(term: str) -> CopWeights:
    """Return weights with every term zeroed but *term*, at weight 1."""
    return CopWeights(**{field: (1.0 if field == term else 0.0) for field in _FIELDS})


_FIELDS = ("separation", "shared_region", "proximity", "endgame", "cycle", "reach", "diagonal")


# --- 8.1.2 connectivity, not mobility --------------------------------------


def test_mass_we_cannot_reach_is_counted() -> None:
    """**A1.5.** The number that must stay at zero."""
    assert separation_mass((3, 3), IN_POCKET, POCKET_WALLS, BOARD) == 1.0
    assert separation_mass((0, 1), IN_POCKET, POCKET_WALLS, BOARD) == 0.0


def test_sealing_yourself_in_with_the_thief_scores_better_than_staying_out() -> None:
    """**The corrected guard, §3.2.** The same walls and the same belief; only
    the cop's side of them differs. An evaluation that penalised confinement
    would prefer the losing board, and it would look reasonable doing it."""
    weights = CopWeights()
    inside = evaluate((0, 1), IN_POCKET, POCKET_WALLS, BOARD, weights)
    outside = evaluate((3, 3), IN_POCKET, POCKET_WALLS, BOARD, weights)
    assert inside > outside


def test_the_separation_penalty_is_large_enough_to_override_everything_else() -> None:
    """A stranded thief is not a bad position, it is a lost sub-game. No
    arrangement of the other terms may outvote it."""
    weights = CopWeights()
    stranded = evaluate((3, 3), IN_POCKET, POCKET_WALLS, BOARD, weights)
    assert stranded < -weights.separation / 2


# --- 8.1.3 shrink the *shared* component ------------------------------------


def test_a_smaller_shared_region_scores_higher() -> None:
    """`−β·|component containing both|`, so smaller is better (A1.6)."""
    weights = only("shared_region")
    open_board = evaluate((0, 1), IN_POCKET, frozenset(), BOARD, weights)
    confined = evaluate((0, 1), IN_POCKET, POCKET_WALLS, BOARD, weights)
    assert confined > open_board


def test_shrinking_a_region_the_thief_is_not_in_earns_nothing() -> None:
    """The term is weighted by mass inside, so walling an empty corner scores
    zero — otherwise the Cop would spend its quota tidying the far side of the
    board while the Thief ran free."""
    weights = only("shared_region")
    elsewhere = {(6, 6): 1.0}
    assert evaluate((0, 1), elsewhere, POCKET_WALLS, BOARD, weights) == 0.0


# --- 8.1.8 the win condition, targeted explicitly ---------------------------


def test_one_wall_from_capture_with_the_cop_at_the_gap() -> None:
    """**§2.2.** Exit count 1 and we are standing next to it."""
    walls = frozenset({(0, 1)})
    assert endgame_mass((1, 1), {(0, 0): 1.0}, walls, BOARD) == 1.0


def test_standing_on_the_last_exit_also_counts() -> None:
    """Ch. 3.4 lets the Cop wall its **own** cell, so this is the strongest
    position on the board — and an adjacency-only test would score it zero."""
    walls = frozenset({(0, 1)})
    assert endgame_mass((1, 0), {(0, 0): 1.0}, walls, BOARD) == 1.0


def test_a_thief_with_two_exits_is_not_the_win_condition() -> None:
    """Two exits needs two walls, and the second gifts a free step to walk out
    through the first (§2.2)."""
    assert endgame_mass((1, 1), {(0, 0): 1.0}, frozenset(), BOARD) == 0.0


def test_the_last_exit_is_worthless_if_we_are_nowhere_near_it() -> None:
    """Exit count alone is not the condition; the standing-next-to-it half is
    what makes it a *plan* rather than an observation."""
    walls = frozenset({(0, 1)})
    assert endgame_mass((6, 6), {(0, 0): 1.0}, walls, BOARD) == 0.0


def test_an_already_sealed_cell_counts_in_full() -> None:
    """M#47: no free neighbour is a capture, not a near-capture."""
    walls = frozenset({(0, 1), (1, 0)})
    assert endgame_mass((6, 6), {(0, 0): 1.0}, walls, BOARD) == 1.0


def test_partial_belief_contributes_partially() -> None:
    """The Cop plays a distribution, not a position. Half the mass one wall from
    capture is worth half the reward."""
    walls = frozenset({(0, 1)})
    assert endgame_mass((1, 1), {(0, 0): 0.5, (6, 6): 0.5}, walls, BOARD) == 0.5


# --- the remaining terms ----------------------------------------------------


def test_closer_is_better() -> None:
    """Path distance, mass-weighted."""
    weights = only("proximity")
    near = evaluate((0, 1), IN_POCKET, frozenset(), BOARD, weights)
    far = evaluate((6, 6), IN_POCKET, frozenset(), BOARD, weights)
    assert near > far


def test_unreachable_mass_is_charged_rather_than_skipped() -> None:
    """Otherwise the proximity term would *improve* when the Cop walled the
    Thief away, which is the exact inversion the separation penalty exists to
    prevent — and two terms disagreeing is worse than one."""
    weights = only("proximity")
    assert evaluate((3, 3), IN_POCKET, POCKET_WALLS, BOARD, weights) <= -float(BOARD.grid_size * 2)


def test_a_region_the_thief_can_circle_is_penalised() -> None:
    """**§2.1.** A cyclic region is one a single pursuer cannot clear, however
    small it is."""
    weights = only("cycle")
    keep = {(r, c) for r in range(3) for c in range(3)} - {(1, 1)}
    ring = frozenset(cell for cell in BOARD.cells() if cell not in keep)
    assert evaluate((0, 1), IN_POCKET, ring, BOARD, weights) < 0.0
    assert evaluate((0, 1), IN_POCKET, ring | {(0, 1)}, BOARD, weights) == 0.0


# --- configuration ----------------------------------------------------------


def test_weights_come_from_config_when_it_offers_them() -> None:
    """Tuning must not require a code change; the defaults must not require a
    config."""

    class Stub:
        def get(self, path: str, default: object = None) -> object:
            return 9.0 if path == "strategy.weight_endgame" else default

    weights = CopWeights.from_config(Stub())
    assert weights.endgame == 9.0
    assert weights.separation == CopWeights().separation


def test_a_missing_config_still_produces_a_playable_cop() -> None:
    """A fresh clone with no tuning file must field a real strategy."""
    assert CopWeights.from_config(None) == CopWeights()
