"""What this peer does when a message arrives. Implements ``PeerHandler``.

The turn loop itself lands in Phase 3, once there is a strategy to ask for a
move. What exists here is the receiving half: the state machine that decides
whether an incoming message is *allowed* right now.

That ordering check is the point. Under commit-reveal a peer that accepted a
reveal before the matching commit would let an opponent see our move and then
choose theirs — the single failure the whole protocol exists to prevent. So
every handler validates its position in the sequence before doing anything, and
refuses out of order with a message we can quote.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.protocol.schemas import (
    Ack,
    BarrierDeclaration,
    CaptureClaim,
    CaptureResponse,
    Commit,
    FinalReveal,
    Negotiation,
    Reveal,
    Role,
)
from core.protocol.tools import ProtocolError
from core.runtime.orchestrator import Orchestrator

__all__ = ["PeerRuntime"]


@dataclass
class PeerRuntime:
    """Receives the opponent's messages and keeps the record the audit reads.

    Attributes:
        orchestrator: Owns the state; the only thing allowed to change it.
        agreed: True once the handshake matched. Nothing else is accepted first.
        commits: Opponent digest per step, kept until the final reveal proves it.
        reveals: Opponent move per step, checked against the digest at the end.
        barriers: Every barrier the opponent declared, for the log (M#15).
    """

    orchestrator: Orchestrator
    agreed: bool = False
    commits: dict[int, str] = field(default_factory=dict)
    reveals: dict[int, Reveal] = field(default_factory=dict)
    barriers: list[BarrierDeclaration] = field(default_factory=list)
    opponent_nonces: dict[str, str] = field(default_factory=dict)

    @property
    def own_role(self) -> Role:
        """Return the role this process plays."""
        return self.orchestrator.role

    def _require_agreed(self, what: str) -> None:
        """Refuse anything that arrives before the handshake succeeded."""
        if not self.agreed:
            raise ProtocolError(f"{what} arrived before the configuration was agreed (M#11)")

    def _require_opponent(self, role: Role, what: str) -> None:
        """Refuse a message claiming to be from us.

        A peer that accepted its own role could be fed its own commitments back
        and would happily record them as the opponent's.
        """
        if role is self.own_role:
            raise ProtocolError(f"{what} claims role {role.value}, which is our own")

    def on_negotiate(self, message: Negotiation) -> Negotiation:
        """Compare digests and answer with ours.

        A mismatch does **not** start a match that cannot be audited: the two
        peers would be enforcing different physics, and the end-of-game audit
        would report forgery against two honest teams (M#11).
        """
        ours = self.orchestrator.config.shared_digest()
        self.agreed = message.config_digest == ours
        if not self.agreed:
            raise ProtocolError(
                f"config digest mismatch: opponent {message.config_digest[:16]}..., "
                f"ours {ours[:16]}... - refusing the match rather than playing "
                "two different rulebooks (M#11)"
            )
        return Negotiation(
            step=0,
            role=self.own_role,
            config_digest=ours,
            game_count=message.game_count,
            role_split=message.role_split,
            readings=message.readings,
        )

    def on_commit(self, message: Commit) -> Ack:
        """Store the opponent's sealed move and confirm we are locked too."""
        self._require_agreed("a commit")
        self._require_opponent(message.role, "a commit")
        if message.step in self.commits:
            raise ProtocolError(f"step {message.step} was already committed; no second attempt")
        self.commits[message.step] = message.digest
        return Ack(step=message.step, role=self.own_role, acknowledged_digest=message.digest)

    def on_reveal(self, message: Reveal) -> None:
        """Record the revealed move — only after its commitment arrived.

        Accepting a reveal with no commit behind it is the whole attack: the
        opponent sees our move, then chooses theirs.
        """
        self._require_agreed("a reveal")
        self._require_opponent(message.role, "a reveal")
        if message.step not in self.commits:
            raise ProtocolError(
                f"reveal for step {message.step} has no matching commit; "
                "a move must be sealed before it is shown (Ch. 5.3.1)"
            )
        if message.step in self.reveals:
            raise ProtocolError(f"step {message.step} was already revealed; no second version")
        self.reveals[message.step] = message

    def on_barrier(self, message: BarrierDeclaration) -> None:
        """Record a declared placement. Only the Cop may place one."""
        self._require_agreed("a barrier declaration")
        self._require_opponent(message.role, "a barrier declaration")
        if message.role is not Role.COP:
            raise ProtocolError("only the cop may place barriers (Ch. 3.4)")
        self.barriers.append(message)

    def on_capture_claim(self, message: CaptureClaim) -> CaptureResponse:
        """Answer a capture claim truthfully (M#21).

        The answer comes from the rules engine, not from what is convenient. A
        false denial is caught by the log audit without exception, and the
        sanction is total disqualification — so this is never a judgement call.
        """
        self._require_agreed("a capture claim")
        outcome = self.orchestrator.rules.verdict(self.orchestrator.state)
        accepted = outcome is not None
        return CaptureResponse(
            step=message.step,
            role=self.own_role,
            accepted=accepted,
            reason=outcome.reason if outcome else "no terminal condition holds in our state",
        )

    def on_final_reveal(self, message: FinalReveal) -> None:
        """Store every nonce, once, for the end-of-match audit (M#18)."""
        self._require_agreed("a final reveal")
        if self.opponent_nonces:
            raise ProtocolError("the final reveal was already received; it happens once")
        missing = sorted(set(map(str, self.commits)) - set(message.nonces))
        if missing:
            raise ProtocolError(
                f"final reveal is missing nonces for step(s) {', '.join(missing)}; "
                "an unverifiable step is treated as forgery"
            )
        self.opponent_nonces = dict(message.nonces)
