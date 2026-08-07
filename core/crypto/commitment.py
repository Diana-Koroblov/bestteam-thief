"""Sealing a move before the opponent chooses theirs.

``H = SHA256(State ‖ Move ‖ Intent ‖ Nonce)`` (Ch. 5.3.1). The commitment is
sent alone; the contents follow later, and the nonce later still. Three
properties fall out, and all three matter:

* **No time travel.** The state is inside the hash, so a commitment made for
  step 4 cannot be replayed at step 9.
* **No revision.** A single changed bit changes the digest completely, so a move
  cannot be adjusted after seeing the opponent's.
* **No dictionary attack.** There are only five moves; without a nonce an
  opponent could hash all five and read our commitment instantly. The nonce is
  what makes the space unguessable.

The nonce is withheld until ``FinalReveal`` (M#18), so verification happens at
the end-of-match audit rather than turn by turn.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Any

from core.crypto.canonical import digest

__all__ = ["NONCE_BYTES", "new_nonce", "commitment_payload", "seal", "verify", "Sealed"]

# 16 bytes = 128 bits. The move space is five, so the nonce is doing all of the
# work here; anything shorter would narrow a search that must stay infeasible.
NONCE_BYTES = 16


def new_nonce() -> str:
    """Return a fresh cryptographically random nonce, hex-encoded.

    ``secrets`` rather than ``random``: the latter is seeded predictably and an
    opponent who guessed the seed could reproduce every nonce in the match.
    """
    return secrets.token_hex(NONCE_BYTES)


def commitment_payload(
    state: Any,
    move: str,
    intent: str,
    nonce: str,
    scent_digest: str | None = None,
    barrier_cell: Any = None,
) -> dict[str, Any]:
    """Return the exact structure both peers hash.

    Kept as one named function so the field set can never drift between the
    peer that seals and the peer that verifies. Adding a field here changes
    every digest in the project, which is why it is a single place.

    Args:
        scent_digest: Hash of the field we emitted this turn (C-008), or None.
        barrier_cell: The cell this turn walls (C-018, M#15/M#16), or None. A
            placement moves as ``STAY``, so without this the *only* thing
            distinguishing "the cop stood still" from "the cop walled (2,3)" is
            an unsealed declaration — which is precisely the after-the-fact
            revision commit-reveal exists to prevent.

    **When either optional field is None the key is omitted entirely, not set to
    null, and this is a correctness requirement rather than tidiness.** The
    opponent recomputes our digests during the end-of-match audit using *their*
    payload builder. If we added a ``"scent_digest": null`` key that they do not,
    every digest we ever sent would fail their verification and we would look
    like forgers — the sanction for which is a total technical loss.

    So both sealed fields are opt-in and only ever included once both peers have
    agreed to them at negotiation (N13c, N20). Sealing unilaterally would be
    worse than not sealing at all.

    *barrier_cell* is normalised to a list because JSON has no tuple: a peer that
    read our log back would hash ``[2, 3]`` where we hashed ``(2, 3)``. Canonical
    serialisation renders both identically today, and relying on that would make
    every digest in the match depend on an implementation detail of `json`.
    """
    payload: dict[str, Any] = {"state": state, "move": move, "intent": intent, "nonce": nonce}
    if scent_digest is not None:
        payload["scent_digest"] = scent_digest
    if barrier_cell is not None:
        payload["barrier_cell"] = list(barrier_cell)
    return payload


@dataclass(frozen=True)
class Sealed:
    """A commitment together with the secrets needed to open it later.

    Attributes:
        digest: What goes on the wire this turn.
        nonce: Held back until the final reveal (M#18).
        move: Held back until the reveal step.
        intent: Held back until the reveal step.
    """

    digest: str
    nonce: str
    move: str
    intent: str


def seal(
    state: Any,
    move: str,
    intent: str,
    nonce: str | None = None,
    scent_digest: str | None = None,
    barrier_cell: Any = None,
) -> Sealed:
    """Commit to *move* against *state*, generating a nonce unless one is given.

    Args:
        state: The board snapshot this move was decided against.
        move: One of the five legal actions.
        intent: ``truth`` or ``lie`` — the flag covering the accompanying hint.
        nonce: Supplied only by tests that need a deterministic digest. Leave it
            unset in play, so the nonce is always fresh: reusing one across two
            steps lets an opponent link them.
        scent_digest: C-008. The reference transmits the scent field but leaves
            it **outside** the hash, so a peer can fabricate a field and pass
            the audit. Passing it here closes that hole — but only when the
            opponent has agreed to the same payload shape.
        barrier_cell: C-018. The cell walled this turn, when one was, and only
            when the opponent agreed to seal it. `LocalTruth.sealed_barrier`
            applies both conditions; callers should not decide it themselves.

    Returns:
        A ``Sealed`` holding the digest to send and the secrets to keep.
    """
    nonce = nonce or new_nonce()
    return Sealed(
        digest=digest(commitment_payload(state, move, intent, nonce, scent_digest, barrier_cell)),
        nonce=nonce,
        move=move,
        intent=intent,
    )


def verify(
    claimed: str,
    state: Any,
    move: str,
    intent: str,
    nonce: str,
    scent_digest: str | None = None,
    barrier_cell: Any = None,
) -> bool:
    """Return True when the revealed values actually produce *claimed*.

    Run over the opponent's whole log at the end of the match. A mismatch is
    proof of tampering — there is no statistical doubt with SHA-256 — and the
    sanction is a total technical loss for the team that forged it.

    Compared with ``secrets.compare_digest`` rather than ``==``. Being honest
    about why: a timing attack is **not** a realistic threat here — the audit
    runs offline, at the end, over a log the opponent already holds, so there is
    no secret for a timing difference to leak. But constant-time comparison of
    digests is simply what the primitive is for, it costs nothing measurable,
    and reaching for ``==`` on a hash is the habit that eventually gets used
    somewhere it does matter.
    """
    computed = digest(
        commitment_payload(state, move, intent, nonce, scent_digest, barrier_cell)
    )
    return secrets.compare_digest(computed, claimed)
