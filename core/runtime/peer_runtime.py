"""What this peer does when a message arrives. Implements ``PeerHandler``.

The receiving half: the state machine that decides whether an incoming message
is *allowed* right now.

That ordering check is the point. Under commit-reveal a peer that accepted a
reveal before the matching commit would let an opponent see our move and then
choose theirs — the single failure the whole protocol exists to prevent. So
every handler validates its position in the sequence before doing anything, and
refuses out of order with a message we can quote.

**What this peer *knows* lives next door**, in `local_truth.py`: the scent it
emits, the posterior it maintains, the observation a brain is handed and the
reveal that carries a decision back out. Two jobs, and only one of them is about
what an opponent is permitted to do to us. The methods below that touch belief,
scent or hints are one-line delegations, kept here so callers still have one
object to talk to.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.domain.board import Position
from core.domain.brain_base import BrainBase, Decision, Observation
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
from core.runtime.local_truth import LocalTruth
from core.runtime.orchestrator import Orchestrator
from core.runtime.prematch import PreMatch

__all__ = ["PeerRuntime"]


@dataclass
class PeerRuntime:
    """Receives the opponent's messages and keeps the record the audit reads.

    Attributes:
        orchestrator: Owns the state; the only thing allowed to change it.
        agreed: True once the handshake matched. Nothing else is accepted first.
        commits: Opponent digest per step, kept until the final reveal proves it.
        barriers: Every barrier the opponent declared, for the log (M#15).
        truth: What we emit, believe and say. Built against the same
            orchestrator, because two views of one game that could disagree are
            worse than one view that is wrong.
        prematch: What we declare about ourselves, and the agreement we reached.
    """

    orchestrator: Orchestrator
    brain: BrainBase | None = None
    agreed: bool = False
    commits: dict[int, str] = field(default_factory=dict)
    barriers: list[BarrierDeclaration] = field(default_factory=list)
    opponent_nonces: dict[str, str] = field(default_factory=dict)
    truth: LocalTruth = None  # type: ignore[assignment]
    prematch: PreMatch = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        """Attach both halves to the same orchestrator we were given."""
        if self.truth is None:
            self.truth = LocalTruth(orchestrator=self.orchestrator)
        if self.prematch is None:
            self.prematch = PreMatch(orchestrator=self.orchestrator)

    @property
    def reveals(self) -> dict[int, Reveal]:
        """Opponent move per step, with the scent field that came with it.

        Owned by `LocalTruth`, because reading these is what that file is for
        and recording them is one line here. Exposed as a property so callers
        and the audit see one record rather than two that can disagree.
        """
        return self.truth.reveals

    def observe(self) -> Observation:
        """Build what the brain is allowed to see. See `LocalTruth.observe`."""
        return self.truth.observe()

    def belief(self) -> dict[Position, float]:
        """Return the posterior over where the opponent is (4.2.1)."""
        return self.truth.belief()

    def latest_opponent_scent(self) -> dict[Position, float]:
        """Return the newest field the opponent transmitted, or ``{}``."""
        return self.truth.latest_opponent_scent()

    def reveal_for(self, decision: Decision, step: int | None = None) -> Reveal:
        """Turn this turn's decision into the reveal that carries it (4.5.1)."""
        return self.truth.reveal_for(decision, self.own_role, step)

    def scent_digest(self) -> str | None:
        """Return the digest of the field we transmit, or None (C-008)."""
        return self.truth.scent_digest()

    def sealed_barrier(self, decision: Decision) -> Position | None:
        """Return the barrier cell to seal into this commitment, or None (C-018)."""
        return self.truth.sealed_barrier(decision)

    def start_sub_game(self, sub_game: int = 1) -> None:
        """Clear everything belonging to the sub-game just finished (TODO 9.5).

        **Everything keyed by step number, without exception.** A commit, a
        reveal or a nonce surviving the boundary is indexed by a step the next
        sub-game will reach again, so `on_commit` would refuse step 0 as already
        committed — and the peer would take a technical loss on the opening move
        of a sub-game it had not yet played.

        The brain is told rather than replaced: what the opponent is like banks
        across the six sub-games and where everyone was does not. See
        `BrainBase.restart_sub_game`.

        The Step-0 declaration is **not** rebuilt here. It is signed per
        sub-game (M#24) and re-signing it means re-handshaking, which is the
        caller's business and not a side effect of clearing a board.
        """
        self.orchestrator.restart(sub_game)
        self.truth.reset()
        self.commits.clear()
        self.barriers.clear()
        self.opponent_nonces.clear()
        if self.brain is not None:
            self.brain.restart_sub_game(sub_game)

    def decide(self) -> Decision:
        """Ask the brain for this turn's decision.

        Ch. 6 places this **between decoding the incoming hint and packing the
        outgoing commit** — the hints are already recorded by ``on_reveal``, and
        the caller seals whatever comes back. Keeping the brain on that seam is
        what stops a strategy from ever seeing the opponent's sealed move.

        Raises:
            RuntimeError: No brain was loaded. Better than silently standing
                still for 35 turns and losing on the clock.
        """
        if self.brain is None:
            raise RuntimeError("no brain loaded; the peer cannot choose a move")
        return self.brain.decide(self.observe())

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
        """Settle the handshake and answer with our own proposal (TODO 9.1).

        A refusal does **not** start a match that cannot be audited: the two
        peers would be enforcing different physics, and the end-of-game audit
        would report forgery against two honest teams (M#11).

        **The reply is our proposal, never an echo of theirs.** This used to
        return the opponent's `game_count`, `role_split` and `readings` back at
        them, which made the exchange incapable of detecting the disagreements
        it exists to detect: agreement was guaranteed because we simply repeated
        whatever arrived. What we send now is what we independently believe, and
        `prematch` sources every value from git, the league log and the config
        rather than from the message being answered.

        Warnings — the readings they never signed, a dirty tree on either side —
        are recorded on `prematch.agreement` and do not block. See
        `negotiation.settle` for why silence warns and contradiction refuses.
        """
        locked = self.prematch.settle(message)
        self.agreed = locked.agreed
        if not self.agreed:
            raise ProtocolError(f"{locked.result} - " + "; ".join(locked.reasons))
        return self.prematch.proposal()

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
