"""The verbal half of a turn, wired together (TODO 8.3.2-8.3.5).

`test_bluff.py` and `test_opponent_profile.py` cover the parts. What is left is
the thing neither of them can see: whether the parts are joined **in the order
the protocol delivers in**. A hint for turn *k* is read at turn *k+1*, so the
peak we held when they spoke and the peak we hold now bracket exactly the move
their claim described. Get that wrong and honest opponents are scored as liars
at random — with no symptom, because a wrong coefficient looks exactly like a
right one until it costs a sub-game.
"""

from __future__ import annotations

from core.domain.actions import Direction
from core.domain.bluff import BluffPolicy, BluffSettings
from core.domain.board import Board
from core.domain.brain_base import Observation
from core.domain.verbal import VerbalLayer

BOARD = Board(grid_size=7)


def observe(peak, hints=(), step=0, own=(0, 0), remaining=14, belief=None) -> Observation:
    """A view whose belief peaks on *peak*, point-mass unless *belief* says otherwise."""
    return Observation(
        board=BOARD,
        own_position=own,
        step=step,
        barriers_remaining=remaining,
        belief={peak: 1.0} if belief is None else belief,
        hints=hints,
    )


def spread(peak) -> dict:
    """A posterior with somewhere for a tilt to go.

    A one-cell belief cannot be tilted at all — `update_from_hint` only moves
    mass to cells the posterior already contains, because off-board mass has
    nowhere to go — so a test for the tilt built on a point mass would pass
    against a filter that did nothing.
    """
    column = {(row, 3): 0.1 for row in range(7)}
    column[peak] = 0.4
    return column


# --- reading what they said -------------------------------------------------


def test_a_hint_is_read_exactly_once_however_often_it_is_offered() -> None:
    """`Observation.hints` is cumulative, so a layer that re-read the tuple each
    turn would score one claim as evidence over and over and manufacture a
    reputation out of a single sentence."""
    layer = VerbalLayer()
    said = ("I drift north while you guess at shadows.",)
    layer.observe(observe((3, 3), step=0))
    layer.observe(observe((2, 3), said, step=1))
    layer.observe(observe((1, 3), said, step=2))
    assert layer.profile.reliability.checked == 1


def test_a_truthful_opponent_earns_a_rising_coefficient() -> None:
    """The peaks bracketing their move are what the claim is checked against."""
    layer = VerbalLayer()
    north = "The northern edge is calling me. Try to keep up."
    layer.observe(observe((6, 3), step=0))
    for index, row in enumerate((5, 4, 3, 2), start=1):
        layer.observe(observe((row, 3), (north,) * index, step=index))
    assert layer.profile.reliability.coefficient > 0.5
    assert layer.profile.reliability.checked == 4


def test_an_opponent_moving_against_their_claim_is_caught() -> None:
    """The scent is a fact and the hint is an argument — this is the check that
    makes the difference operational."""
    layer = VerbalLayer()
    north = "The northern edge is calling me. Try to keep up."
    layer.observe(observe((0, 3), step=0))
    for index, row in enumerate((1, 2, 3, 4), start=1):
        layer.observe(observe((row, 3), (north,) * index, step=index))
    assert layer.profile.reliability.coefficient < 0.5


def test_an_unread_backlog_is_discarded_rather_than_misdated() -> None:
    """A hint describes the move that just happened. Scoring three of them
    against one pair of peaks would file honest opponents as liars at random,
    and discarding evidence we cannot place is the cheaper error."""
    layer = VerbalLayer()
    layer.observe(observe((3, 3), step=0))
    backlog = ("Going south, low and quiet. You will not follow.",) * 3
    layer.observe(observe((2, 3), backlog, step=1))
    assert layer.profile.reliability.checked == 1
    assert layer.heard == 3


def test_a_trusted_claim_actually_moves_the_posterior() -> None:
    """Otherwise the whole inbound path is decoration: the parser reads, the
    coefficient rises, and nothing downstream changes."""
    layer = VerbalLayer()
    north = "The northern edge is calling me. Try to keep up."
    layer.observe(observe((6, 3), step=0))
    for index, row in enumerate((5, 4, 3), start=1):
        layer.observe(observe((row, 3), (north,) * index, step=index))

    before = spread((2, 3))
    after = layer.observe(observe((2, 3), (north,) * 4, step=4, belief=before))
    # North decreases the row index (C-010), so a believed claim moves mass up
    # the column and takes it off the cell it came from.
    assert after[(1, 3)] > before[(1, 3)]
    assert after[(2, 3)] < before[(2, 3)]


def test_a_stranger_gets_no_vote_at_all() -> None:
    """Turn one against someone we have never played: trust is 0 and the tilt
    is a deliberate no-op."""
    layer = VerbalLayer()
    north = ("I drift north while you guess at shadows.",)
    layer.observe(observe((3, 3), step=0))
    assert layer.observe(observe((2, 3), north, step=1)) == {(2, 3): 1.0}


# --- measuring whether they listen ------------------------------------------


def test_our_own_claim_is_correlated_against_their_next_move() -> None:
    """8.3.5's input. The claim we made last turn is what this turn's peak
    movement is scored against — not this turn's claim, which they cannot
    possibly have heard yet."""
    layer = VerbalLayer()
    layer.observe(observe((3, 3), step=0))
    layer.speak(Direction.N, observe((3, 3), step=0))
    layer.observe(observe((2, 3), step=1))
    assert layer.profile.aligned + layer.profile.opposed + layer.profile.neutral == 1


def test_saying_nothing_leaves_the_responsiveness_trait_untouched() -> None:
    """There is no correlation to measure against a claim we never made."""
    layer = VerbalLayer(bluff=BluffPolicy(settings=BluffSettings(enabled=False)))
    for step, row in enumerate((3, 2, 1, 0)):
        layer.observe(observe((row, 3), step=step))
        layer.speak(Direction.N, observe((row, 3), step=step))
    assert layer.profile.hint_responsiveness is None


# --- the sub-game boundary --------------------------------------------------


def test_a_restart_keeps_the_reputation_and_drops_the_board_state() -> None:
    """A3.5's two scopes. Six sub-games are the sample the traits rest on, while
    a trail carried across a boundary would have us fleeing a scored game."""
    layer = VerbalLayer()
    north = "The northern edge is calling me. Try to keep up."
    layer.observe(observe((6, 3), step=0))
    layer.observe(observe((5, 3), (north,), step=1))
    checked = layer.profile.reliability.checked

    layer.restart(1)
    assert layer.profile.reliability.checked == checked
    assert layer.trail.visits == []
    assert layer.claimed is None and layer.peak is None


def test_the_hint_index_is_not_reset_by_a_restart() -> None:
    """**A deliberate asymmetry.** `Observation.hints` is cumulative across the
    peer connection, not per sub-game, so an index reset would re-read every
    hint of the previous game as fresh evidence the moment a new one started."""
    layer = VerbalLayer()
    layer.observe(observe((3, 3), ("Eastward now. The far side is friendlier.",), step=0))
    layer.restart(1)
    assert layer.heard == 1


# --- the public traits ------------------------------------------------------


def test_the_opponents_declared_quota_is_recorded_every_turn() -> None:
    """Public under M#15, so counting it is arithmetic rather than inference —
    and it is the trait the Thief acts on."""
    layer = VerbalLayer()
    for step, remaining in enumerate((14, 13, 12, 12, 11, 10, 9)):
        layer.observe(observe((3, 3), step=step, remaining=remaining))
    assert layer.profile.barrier_rate == 5 / 6
