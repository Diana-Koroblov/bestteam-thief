"""The opening turn emits once, not twice (imreeyal, 17/08).

The defect these pin survived two complete live series against a peer running a
physics checker, because it is invisible from inside: our own belief never reads
our own trail, every frame after the first is correct, and no test asserted what
the *first* one looked like to somebody replaying it from an empty board.

So these assert on the wire frame's **values**, which is the only place the
extra emission shows. A second deposit one decay apart puts a second-generation
intensity on the wire — at rho=0.1 subtractive, 0.9 -> 0.8 -> 0.7 — and 0.7 is
unexplainable in a game one step old.
"""

from __future__ import annotations

import pytest

from core.domain.board import Board
from core.domain.filter import BeliefFilter
from core.domain.scent import decay, decode, emit, encode

RATE = 0.1
BOARD = Board(7)


def _wire_frame(deposits: list[tuple[int, int]], model: str) -> dict:
    """Return the frame `send_turn` would transmit after *deposits*, rounded."""
    trail = BeliefFilter(board=BOARD, rate=RATE, model=model)
    for cell in deposits:
        trail.deposit(cell)
    # `core/compat/turns.send_turn` decays the outgoing copy once (imreeyal §3.13).
    field = decay(decode(encode(trail.trail)), RATE, model)
    return {cell: round(value, 3) for cell, value in field.items()}


def _one_emission(cell: tuple[int, int], model: str) -> dict:
    """What a peer replaying from an empty board can account for: emit, then decay.

    Derived rather than written out as literals, because the two models do not
    share a kernel — `subtractive` lays three rings and `multiplicative` a
    six-valued radial fall, and a hardcoded set for one silently becomes a
    wrong assertion for the other.
    """
    return {
        cell_: round(value, 3)
        for cell_, value in decay(emit(cell, BOARD, model), RATE, model).items()
    }


@pytest.mark.parametrize("model", ["subtractive", "multiplicative"])
@pytest.mark.parametrize(
    ("role", "spawn", "moved"),
    [("cop", (0, 0), (1, 0)), ("thief", (3, 3), (4, 3))],
)
def test_the_opening_frame_carries_exactly_one_emission(
    model: str, role: str, spawn: tuple[int, int], moved: tuple[int, int]
) -> None:
    """Both roles, both models: nothing older than this game's single move.

    Parametrised over the role because the live diagnosis named the Cop only —
    its spawn at the (0,0) corner clips most of the kernel off-board, so it
    showed 12 cells and one stray value where the Thief's centre spawn showed 30
    and three. The Thief was never clean; it was never *checked*, because it
    opens the sub-game and an opening frame has no predecessor to replay from.
    """
    assert _wire_frame([moved], model) == _one_emission(moved, model)


@pytest.mark.parametrize("model", ["subtractive", "multiplicative"])
@pytest.mark.parametrize(
    ("spawn", "moved"), [((0, 0), (1, 0)), ((3, 3), (4, 3))]
)
def test_a_spawn_deposit_would_be_visible_to_the_opponent(
    model: str, spawn: tuple[int, int], moved: tuple[int, int]
) -> None:
    """The guard's own premise: this is detectable, so it must not regress.

    Reintroducing the pre-move deposit puts a second-generation intensity on the
    wire — one the opponent cannot reach by replaying a single emission — which
    is exactly how imreeyal's checker reported us. Asserted rather than assumed,
    so this file cannot pass by testing nothing.
    """
    doubled = _wire_frame([spawn, moved], model)
    assert doubled != _one_emission(moved, model)
    stray = set(doubled.values()) - set(_one_emission(moved, model).values())
    assert stray, "a doubled deposit must be visible in the transmitted values"
