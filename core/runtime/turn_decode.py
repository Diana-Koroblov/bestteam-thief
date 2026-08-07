"""Turning an opponent's reveal back into a decision the rules can apply.

Two small functions, kept out of `match_driver.py` because both are about the
*shape* of what crosses the wire and neither is about driving a turn.

`sealed_state` is the more delicate of the two. It defines the bytes both peers
hash for every step of every sub-game, so it has exactly one definition here for
the same reason `commitment_payload` has one: two spellings of the same state
produce two digests, and the audit would report forgery against two honest
teams.
"""

from __future__ import annotations

from typing import Any

from core.domain.actions import Direction
from core.domain.brain_base import Decision
from core.domain.game_state import GameState
from core.domain.turn import IllegalMoveError

__all__ = ["sealed_state", "decision_of"]


def sealed_state(state: GameState) -> dict[str, Any]:
    """Return the state snapshot a commitment is sealed against (Ch. 5.3.1).

    Lists, not tuples: the audit re-hashes this after a JSON round trip, where a
    tuple has become a list. Sealing one shape and verifying another is a
    self-inflicted forgery verdict.

    The step is included because `audit._step_inside` reads it to catch a
    commitment relabelled for a different turn — a genuine seal replayed under a
    new number verifies against itself and ascends correctly, so the step has to
    be *inside* the hash for the replay to be detectable at all.
    """
    return {"cop": list(state.cop), "thief": list(state.thief), "step": state.step}


def decision_of(reveal: Any) -> Decision:
    """Return the opponent's revealed turn as something the board can apply.

    **Movement only, deliberately.** `Decision` also carries a claimed bearing
    and a truth flag, and neither is reconstructed here. The flag was sealed in
    *their* commitment and is preserved where it belongs — on the stored
    `Reveal`, and in the log the audit reads. Copying it into this object would
    force us to invent a `claim` to satisfy the LIE invariant, and inventing a
    bearing an opponent never sent is precisely the kind of fabricated detail a
    dispute turns on.

    Raises:
        IllegalMoveError: The move is not one of the five legal actions. Raised
            rather than returned so it lands on the driver's technical-loss path
            with everything else the opponent can get wrong (M#13, M#14).
    """
    try:
        move = Direction(reveal.move)
    except ValueError as error:
        raise IllegalMoveError(
            f"opponent revealed {reveal.move!r}, which is not one of the five legal actions"
        ) from error
    return Decision(
        move=move,
        barrier=tuple(reveal.barrier_cell) if reveal.barrier_cell else None,
        reason="revealed by the opponent",
    )
