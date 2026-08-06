"""Every message that crosses the wire, as a frozen value.

There is no referee, so the wire format *is* the rulebook between two peers.
Each message therefore carries its own `step` and `role`: a payload that cannot
say which turn it belongs to cannot be audited afterwards, and the end-of-match
log audit is the only thing standing between us and an unprovable dispute.

**The one asymmetry worth understanding.** ``Commit`` carries a digest and
nothing else. ``Reveal`` carries the move, the hint and the intent flag — but
**not the nonce** (M#18). The nonce is released only in ``FinalReveal``, at the
end of the match. So an opponent cannot verify our commitment mid-game; they
verify the whole log at the end. That is deliberate: releasing the nonce per
turn would let an opponent confirm each guess about our strategy while the game
is still running.

Every message serialises through ``core.crypto.canonical``, so two peers hash
identical bytes or the mismatch is provable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, ClassVar

from core.domain.intent import Intent

__all__ = ["Role", "Intent", "MessageKind", "Message", "Commit", "Ack", "Reveal",
           "FinalReveal", "CaptureClaim", "CaptureResponse", "BarrierDeclaration", "Negotiation"]


class Role(str, Enum):
    """Which side a peer plays. One process, one role, for the whole sub-game."""

    COP = "cop"
    THIEF = "thief"


class MessageKind(str, Enum):
    """The tag every payload carries, so a receiver never guesses."""

    COMMIT = "commit"
    ACK = "ack"
    REVEAL = "reveal"
    FINAL_REVEAL = "final_reveal"
    CAPTURE_CLAIM = "capture_claim"
    CAPTURE_RESPONSE = "capture_response"
    BARRIER_DECLARATION = "barrier_declaration"
    NEGOTIATION = "negotiation"


@dataclass(frozen=True)
class Message:
    """Fields shared by everything on the wire.

    ``KIND`` is a class variable rather than a field: it identifies the type and
    is never something a caller chooses, so making it settable would allow a
    Commit that calls itself a Reveal. It is added to the payload on the way
    out, so the wire still carries an explicit tag and a receiver never has to
    infer the type from its shape.

    Attributes:
        step: The turn this belongs to, 0-based. Replaying a message from an
            earlier step is the cheapest attack there is, and the step number is
            what makes it detectable.
        role: Who sent it.
    """

    step: int
    role: Role

    KIND: ClassVar[MessageKind]

    def payload(self) -> dict[str, Any]:
        """Return a JSON-ready dict, for hashing and for the wire.

        Tuples become lists because JSON has no tuple, and a peer that received
        one and re-serialised it would otherwise produce different bytes from
        the peer that sent it.
        """
        return {**_jsonable(asdict(self)), "kind": self.KIND.value}


def _jsonable(value: Any) -> Any:
    """Convert dataclass output into something JSON round-trips unchanged."""
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    return value


@dataclass(frozen=True)
class Commit(Message):
    """A sealed move. Reveals nothing (Ch. 5.3.1).

    Attributes:
        digest: ``SHA256(state ‖ move ‖ intent ‖ nonce)`` over canonical JSON.
    """

    digest: str = ""
    KIND: ClassVar[MessageKind] = MessageKind.COMMIT


@dataclass(frozen=True)
class Ack(Message):
    """Confirms the opponent's commitment is stored and we are locked too."""

    acknowledged_digest: str = ""
    KIND: ClassVar[MessageKind] = MessageKind.ACK


@dataclass(frozen=True)
class Reveal(Message):
    """The move, its hint and our scent field — **without** the nonce (M#18).

    Attributes:
        move: One of the five legal actions.
        hint: The verbal message, capped at ``world.hint_max_words``.
        intent: Whether *hint* is truthful. Sealed in the commit, so it cannot
            be revised now.
        barrier_cell: Set when this turn placed a barrier. Declaring it here is
            mandatory and must be exact (M#15, M#16).
        scent: The field we emitted this turn, as sorted ``(row, col, intensity)``
            triples from `scent.encode`.

    **The scent field rides on the reveal, and there is nowhere else it could
    go.** There is no shared board, so a peer learns the opponent's field only
    because the opponent sends it (C-005). The commit carries a digest and
    nothing else, so the field travels here — which fixes the timing for the
    whole game: a field revealed at turn *k* is first usable when deciding turn
    *k+1*, because turn *k*'s own move was committed before it arrived. That is
    not a limitation to work around, it *is* commit-reveal.

    Under C-008 the commit may additionally seal a digest of this field, so a
    peer cannot transmit one field and hash another. That is opt-in and
    negotiated: sealing unilaterally would fail every digest the opponent
    recomputes.
    """

    move: str = ""
    hint: str = ""
    intent: Intent = Intent.TRUTH
    barrier_cell: tuple[int, int] | None = None
    scent: tuple[tuple[int, int, float], ...] = ()
    KIND: ClassVar[MessageKind] = MessageKind.REVEAL


@dataclass(frozen=True)
class FinalReveal(Message):
    """Every nonce, released once, at the end of the match.

    Attributes:
        nonces: Step number to nonce, for every step played. A missing entry
            makes that step unverifiable, which the audit treats as forgery.
    """

    nonces: dict[str, str] = field(default_factory=dict)
    KIND: ClassVar[MessageKind] = MessageKind.FINAL_REVEAL


@dataclass(frozen=True)
class CaptureClaim(Message):
    """The Cop asserts a capture and names the cell it happened on."""

    cell: tuple[int, int] = (0, 0)
    rule: str = ""
    KIND: ClassVar[MessageKind] = MessageKind.CAPTURE_CLAIM


@dataclass(frozen=True)
class CaptureResponse(Message):
    """The Thief's answer, which M#21 obliges to be truthful.

    A false denial is discovered at the log audit without exception, and the
    sanction is total disqualification — so this is never a judgement call.
    """

    accepted: bool = False
    reason: str = ""
    KIND: ClassVar[MessageKind] = MessageKind.CAPTURE_RESPONSE


@dataclass(frozen=True)
class BarrierDeclaration(Message):
    """An open declaration of a placement, with its exact cell (M#15)."""

    cell: tuple[int, int] = (0, 0)
    remaining: int = 0
    KIND: ClassVar[MessageKind] = MessageKind.BARRIER_DECLARATION


@dataclass(frozen=True)
class Negotiation(Message):
    """The pre-match handshake (M#37, M#11, M#23).

    Attributes:
        config_digest: SHA-256 of the shared config. A mismatch refuses the
            match rather than starting one that cannot be audited.
        scent_model_digest: Seals the decay formula, not just its rate — the
            book gives 0.81 after one turn, the reference gives 0.80 (C-007).
        game_count: Counted matches already played, declared honestly (M#37).
        role_split: Which sub-games each side plays. Not in Appendix F at all
            (C-011), so silence here means two teams assuming different things.
        readings: The C-006 and C-010 mechanism choices, by name.
        step_zero: The signed declaration, carrying ``github_commit`` (M#24,
            M#53). It travels **inside** the handshake rather than as a message
            of its own because the two are one decision: a peer that agreed the
            physics but pinned no commit can still swap agents between
            sub-games, and there would be no moment left at which to notice.

    **Every field but ``config_digest`` decodes to empty when the opponent
    omitted it**, and that is load-bearing. Our extensions are not in the book,
    so a peer that never built them must be distinguishable from one that
    disagrees — the first is warned about, the second refuses the match. A
    decoder default of ``"3-3"`` would have made an opponent who said nothing
    indistinguishable from one who agreed, which is the C-011 failure exactly.
    """

    config_digest: str = ""
    scent_model_digest: str = ""
    game_count: int = 0
    role_split: str = "3-3"
    readings: dict[str, str] = field(default_factory=dict)
    step_zero: dict[str, Any] = field(default_factory=dict)
    KIND: ClassVar[MessageKind] = MessageKind.NEGOTIATION
