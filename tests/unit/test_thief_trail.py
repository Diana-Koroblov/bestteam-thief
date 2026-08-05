"""Our own scent, reconstructed (TODO 8.2.3).

The whole value of this module is that its output **equals** what the engine
emitted. A trail that drifts by a little every turn would still look plausible on
screen and would quietly mis-price every move, so the first test here compares
against `core.domain.scent` directly rather than against a hand-written expectation.
"""

from __future__ import annotations

from core.domain.board import Board
from core.domain.scent import decay, emit, merge
from thief.trail import TrailTracker

BOARD = Board(grid_size=7)


def engine_trail(path, rate=0.10, model="multiplicative") -> dict:
    """Replay *path* the way `selfplay.Side.emit_and_age` does."""
    field: dict = {}
    for cell in path:
        field = merge(decay(field, rate, model), emit(cell, BOARD))
    return field


# --- exactness --------------------------------------------------------------


def test_the_reconstruction_equals_what_the_engine_emitted() -> None:
    """Same arithmetic, same inputs — so this is exact, not an estimate."""
    path = [(3, 3), (3, 4), (2, 4), (2, 3)]
    tracker = TrailTracker()
    for cell in path:
        tracker.observe(cell, BOARD)
    assert tracker.emitted == engine_trail(path)


def test_the_order_is_decay_then_deposit() -> None:
    """Emitting before decaying would fade the mark just laid, making every
    reading one turn old — invisible in aggregate, wrong in every detail."""
    tracker = TrailTracker()
    tracker.observe((3, 3), BOARD)
    tracker.observe((3, 3), BOARD)
    # Standing still: the fresh 0.90 wins over the aged 0.81, by `merge`'s max.
    assert tracker.emitted[(3, 3)] == 0.90


def test_the_subtractive_model_is_honoured() -> None:
    """C-007: either decay model may be signed at the handshake, and
    reconstructing with the wrong one drifts a little every turn."""
    tracker = TrailTracker(model="subtractive")
    tracker.observe((3, 3), BOARD)
    tracker.observe((0, 0), BOARD)
    assert tracker.emitted == engine_trail([(3, 3), (0, 0)], model="subtractive")


def test_a_corner_emits_a_smaller_field() -> None:
    """Cells off the board are dropped, not clamped — a weak edge reading is
    itself information."""
    tracker = TrailTracker()
    tracker.observe((0, 0), BOARD)
    assert len(tracker.emitted) == 9


# --- what a trail costs -----------------------------------------------------


def test_a_fresh_cell_is_silent() -> None:
    """Nothing emitted anywhere near it."""
    tracker = TrailTracker()
    tracker.observe((0, 0), BOARD)
    assert tracker.cost_at((6, 6), BOARD) == 0.0


def test_standing_still_does_not_build_a_bigger_trail() -> None:
    """🔬 **The finding that killed the false anchor** (PRD advanced §4.4).

    §4.4 assumes a trail can be *fed* — stand somewhere, build a plateau, then
    break away. It cannot. `merge` keeps the **maximum**, so re-emitting on a
    cell we already occupy restores exactly the values already there. Five turns
    of standing still is byte-for-byte one turn of standing still.
    """
    once = TrailTracker()
    once.observe((3, 3), BOARD)
    lingered = TrailTracker()
    for _ in range(5):
        lingered.observe((3, 3), BOARD)
    assert lingered.emitted == once.emitted


def test_moving_accumulates_more_scent_than_repeating() -> None:
    """The other half of the same finding, and the counter-intuitive one.

    Each step lays a fresh window beside the decaying old one, so **movement**
    is what spreads scent — 34 cells and 12.51 total against standing still's 25
    and 7.14. A tactic that spends turns to be louder is spending them to be
    quieter.
    """
    stayed, moved = TrailTracker(), TrailTracker()
    for _ in range(5):
        stayed.observe((3, 3), BOARD)
    for cell in [(3, 3), (3, 4), (3, 5), (2, 5), (1, 5)]:
        moved.observe(cell, BOARD)
    assert sum(moved.emitted.values()) > sum(stayed.emitted.values())
    assert len(moved.emitted) > len(stayed.emitted)


def test_moving_away_is_cheaper_than_staying() -> None:
    """The comparison the search actually makes, on the actual numbers."""
    tracker = TrailTracker()
    for _ in range(3):
        tracker.observe((3, 3), BOARD)
    assert tracker.cost_at((0, 0), BOARD) < tracker.cost_at((3, 3), BOARD)


def test_the_cost_reads_the_whole_emission_window() -> None:
    """A single-cell reading would rate "one step off a cell I have circled ten
    times" as silent, which is precisely backwards."""
    tracker = TrailTracker()
    tracker.observe((3, 3), BOARD)
    assert tracker.cost_at((3, 4), BOARD) > 0.0
    assert tracker.cost_at((3, 3), BOARD) > tracker.cost_at((3, 5), BOARD)


# --- the loudest mark -------------------------------------------------------


def test_silence_has_no_loudest_cell() -> None:
    """Turn zero, before anything has been emitted."""
    assert TrailTracker().loudest() is None


def test_the_loudest_cell_is_where_we_last_stood() -> None:
    """Our current deposit is always at peak, so this tracks us — which is what
    makes it the right thing for the false anchor to break away from."""
    tracker = TrailTracker()
    tracker.observe((0, 0), BOARD)
    tracker.observe((6, 6), BOARD)
    assert tracker.loudest() == (6, 6)


def test_ties_break_on_coordinates() -> None:
    """Two peers replaying one log must reach the same answer."""
    tracker = TrailTracker()
    tracker.observe((3, 3), BOARD)
    assert tracker.loudest() == (3, 3)


# --- sub-game boundaries ----------------------------------------------------


def test_reset_clears_the_trail_and_the_history() -> None:
    """A trail is per sub-game. Carrying it across the boundary would have the
    Thief fleeing the ghost of a game that is already scored."""
    tracker = TrailTracker()
    tracker.observe((3, 3), BOARD)
    tracker.reset()
    assert tracker.emitted == {} and tracker.visits == []
