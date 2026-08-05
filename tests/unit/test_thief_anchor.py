"""The false anchor's gate and state machine (TODO 8.2.5).

The tactic ships **disabled** — 8.2.6 measured it and it lost. These tests are
still worth their space: they are what makes the ablation trustworthy. An
`enabled=False` that quietly perturbed a decision, or a `bias` that leaked when
the tactic was off, would have made the measurement compare two things that
differ in more than one place.
"""

from __future__ import annotations

from core.domain.board import Board
from core.domain.brain_base import Observation
from thief.anchor import AnchorPhase, FalseAnchor

BOARD = Board(grid_size=7)


def observe(own=(3, 3), cop=(0, 0)) -> Observation:
    """A view with the believed Cop at *cop*."""
    return Observation(board=BOARD, own_position=own, belief={cop: 1.0}, barriers_remaining=14)


def running() -> FalseAnchor:
    """An enabled anchor mid-ANCHORING, for the cancellation tests."""
    anchor = FalseAnchor(enabled=True)
    anchor.update(observe(), risk=0.0, exits=4)
    return anchor


# --- the tactic is off by default -------------------------------------------


def test_it_does_nothing_unless_switched_on() -> None:
    """8.2.6 rejected it, so `false_anchor` defaults to False and the state
    machine must genuinely never leave OFF."""
    anchor = FalseAnchor()
    for _ in range(10):
        assert anchor.update(observe(), risk=0.0, exits=4) is AnchorPhase.OFF


def test_a_disabled_anchor_contributes_no_bias() -> None:
    """**The property the ablation rests on.** If a disabled tactic could shift
    a score by even a little, the with/without comparison would be measuring two
    differences instead of one."""
    anchor = FalseAnchor()
    anchor.update(observe(), risk=0.0, exits=4)
    assert all(anchor.bias(cell, 3.0) == 0.0 for cell in ((0, 0), (3, 3), (6, 6)))


# --- A2.10 payoff must exceed cost ------------------------------------------


def test_a_nearby_cop_offers_no_head_start_worth_buying() -> None:
    """Payoff is bounded by how far the Cop must travel: against a Cop three
    steps away there is no five-turn head start to win, however confused it is."""
    anchor = FalseAnchor(enabled=True)
    close = observe(own=(3, 3), cop=(3, 0))
    assert anchor.payoff(close) == 3
    assert anchor.update(close, risk=0.0, exits=4) is AnchorPhase.OFF


def test_a_distant_cop_makes_the_bluff_worth_its_turns() -> None:
    """Six steps away, capped at `break_turns`, against three turns of cost."""
    anchor = FalseAnchor(enabled=True)
    assert anchor.update(observe(own=(6, 6), cop=(0, 0)), risk=0.0, exits=4) is AnchorPhase.ANCHORING


def test_no_belief_means_no_payoff_estimate() -> None:
    """Turn one. Bluffing against an unknown position is guessing, not tactics."""
    blind = Observation(board=BOARD, own_position=(3, 3), barriers_remaining=14)
    assert FalseAnchor(enabled=True).payoff(blind) == 0


# --- standing still is only safe when nothing can reach us ------------------


def test_danger_prevents_the_bluff_from_starting() -> None:
    """Standing still is the loudest thing a Thief can do; doing it under threat
    is indefensible."""
    anchor = FalseAnchor(enabled=True)
    assert anchor.update(observe(), risk=0.5, exits=4) is AnchorPhase.OFF


def test_a_tight_cell_prevents_the_bluff_from_starting() -> None:
    """Standing in a pocket to run a bluff is how a Thief loses a game it had
    already won."""
    anchor = FalseAnchor(enabled=True)
    assert anchor.update(observe(), risk=0.0, exits=2) is AnchorPhase.OFF


def test_a_denormal_risk_still_opens_the_gate() -> None:
    """🐛 **The regression that made the tactic un-measurable.**

    The gate was `risk <= 0.0`, and `belief.normalise` leaves unreachable cells
    holding denormals around 1e-18 — so on a board where nothing could possibly
    reach us the comparison was still false and the anchor never once fired.
    Both ablation arms came back byte-identical, which reads exactly like "the
    tactic does nothing" rather than "the tactic never ran".
    """
    anchor = FalseAnchor(enabled=True)
    assert anchor.update(observe(own=(6, 6)), risk=3e-18, exits=4) is AnchorPhase.ANCHORING


# --- the two stages ---------------------------------------------------------


def test_it_anchors_then_breaks_then_stops() -> None:
    """The full cycle, one turn at a time."""
    # `break_turns` also caps the payoff, so it must exceed `anchor_turns` for
    # the A2.10 gate to open at all — the tactic refuses to buy a head start
    # shorter than the turns it costs.
    anchor = FalseAnchor(enabled=True, anchor_turns=2, break_turns=3)
    view = observe(own=(6, 6), cop=(0, 0))
    phases = [anchor.update(view, risk=0.0, exits=4) for _ in range(7)]
    assert phases == [
        AnchorPhase.ANCHORING, AnchorPhase.ANCHORING,
        AnchorPhase.BREAKING, AnchorPhase.BREAKING, AnchorPhase.BREAKING,
        AnchorPhase.OFF, AnchorPhase.ANCHORING,
    ]


def test_the_plateau_is_built_where_the_bluff_started() -> None:
    """That cell is what BREAKING runs away from."""
    anchor = FalseAnchor(enabled=True)
    anchor.update(observe(own=(6, 6), cop=(0, 0)), risk=0.0, exits=4)
    assert anchor.cell == (6, 6)


def test_danger_cancels_a_bluff_already_under_way() -> None:
    """**A3.2.** A tactic that ran to completion regardless would be a scripted
    sequence, and a scripted Thief is a readable one."""
    anchor = running()
    assert anchor.update(observe(), risk=0.9, exits=4) is AnchorPhase.OFF
    assert anchor.cell is None


def test_switching_the_tactic_off_mid_bluff_stops_it() -> None:
    """So the ablation cannot be contaminated by a run already in flight."""
    anchor = running()
    anchor.enabled = False
    assert anchor.update(observe(), risk=0.0, exits=4) is AnchorPhase.OFF


def test_reset_clears_the_state_machine() -> None:
    """A sub-game boundary must not resume a bluff on a board that is gone."""
    anchor = running()
    anchor.reset()
    assert anchor.phase is AnchorPhase.OFF and anchor.remaining == 0


# --- the bias, and its sign -------------------------------------------------


def test_anchoring_pulls_toward_the_plateau_and_breaking_pushes_away() -> None:
    """The tactic in one line: build the mass, then leave it decisively."""
    anchor = FalseAnchor(enabled=True, anchor_turns=1, break_turns=3)
    view = observe(own=(6, 6), cop=(0, 0))
    anchor.update(view, risk=0.0, exits=4)
    near, far = anchor.bias((6, 6), 3.0), anchor.bias((0, 0), 3.0)
    assert near > far

    anchor.update(view, risk=0.0, exits=4)
    assert anchor.phase is AnchorPhase.BREAKING
    assert anchor.bias((0, 0), 3.0) > anchor.bias((6, 6), 3.0)
