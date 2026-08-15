"""Verifying the opponent's agreement against the one we sent.

Split from `session.py` under the 150-line ceiling (ADR-005), the same
coordination/mechanics split as `turns.py`: the session owns *when* the
agreement is collected, this module owns *what makes it acceptable*.

The argument is the full agreement MESSAGE, not the bare terms. That is not
pedantry: the pairing fields (`sub_game_number`, `role`, the three locked-model
hashes) live beside the terms, not inside them, so a guard handed only the
terms sees our own side as permanently omitted and — because omission must
never refuse — silently never fires. That was a live bug: our role-collision
guard passed everything, and only the opponent's side of the same check ever
caught a real collision.
"""

from __future__ import annotations

from typing import Any

from core.compat import sealing
from core.compat.wire import terms_diff

__all__ = ["HandshakeError", "verify_agreement", "pairing_warnings"]


class HandshakeError(RuntimeError):
    """The agreement did not settle, so no move may be sent."""


def verify_agreement(ours: dict[str, Any], theirs: dict[str, Any]) -> list[str]:
    """Refuse unless they signed the very same terms we did; return log-only notes.

    Args:
        ours: The agreement message WE sent (`ReferenceSession.agreement_message`).
        theirs: The agreement message that arrived in our inbox.

    A refusal is the correct outcome: two peers enforcing different physics
    produce an audit that reports forgery against two honest teams (M#11).
    """
    differences = terms_diff(dict(ours.get("terms") or {}), dict(theirs.get("terms") or {}))
    if differences:
        raise HandshakeError("the agreed terms differ:\n  " + "\n  ".join(differences))
    if not sealing.verify(
        theirs["terms"], str(theirs.get("nonce", "")), str(theirs.get("signature", ""))
    ):
        raise HandshakeError("their signature does not cover the terms they sent")
    return pairing_warnings(ours, theirs)


def pairing_warnings(ours: dict[str, Any], theirs: dict[str, Any]) -> list[str]:
    """Refuse a mismatch that makes the sub-game unplayable; log the declared ones.

    Two peers that disagree here complete a perfect handshake and then sit
    waiting on different games, or both open as the same role — a deadlock
    discovered only once both timeouts fire (imreeyal §3.8). Omission on either
    side is silence, not disagreement, and must never refuse: the same rule the
    league conformance kit's own ``ref_pairing_decision`` applies.

    Of the locked-model hashes, a wire-shape or info-mode differ is an
    unplayable match and refuses; a scent-model differ is LOGGED — imreeyal's
    own check does the same, and under the 3.12 fallback a declared divergence
    is the agreement working, not breaking.
    """
    our_sg, their_sg = ours.get("sub_game_number"), theirs.get("sub_game_number")
    if isinstance(our_sg, int) and isinstance(their_sg, int) and our_sg != their_sg:
        raise HandshakeError(f"sub-game mismatch: we open {our_sg}, they open {their_sg}")
    our_role, their_role = ours.get("role"), theirs.get("role")
    if isinstance(our_role, str) and isinstance(their_role, str) and our_role == their_role:
        raise HandshakeError(f"role collision: both sides declare {our_role!r}")
    warnings: list[str] = []
    for key, refuses in (("wire_shape_sha256", True), ("info_mode_sha256", True),
                         ("scent_model_sha256", False)):
        mine, sent = ours.get(key), theirs.get(key)
        if not (isinstance(mine, str) and isinstance(sent, str) and mine and sent and mine != sent):
            continue
        note = f"{key} differs: ours={mine[:12]} theirs={sent[:12]}"
        if refuses:
            raise HandshakeError(note)
        warnings.append(f"logged, not refused (declared divergence): {note}")
    return warnings
