"""Commit, acknowledge, reveal, final reveal (TODO 6.2, M#17-M#22).

The protocol that makes simultaneous movement possible over a network where one
peer must physically send first. Four phases, and each exists to close a
specific way of cheating:

1. **Commit** — the hash alone. No move, no hint, no intent. Whoever sends
   first reveals nothing, so going first costs nothing.
2. **Acknowledge** — both sides confirm they hold the other's hash. Only now is
   revealing safe: an early reveal would hand the opponent our move while they
   were still free to choose theirs.
3. **Reveal** — move, hint and intent, **without the nonce** (M#18). The
   opponent can act on the move but cannot yet verify it, which is deliberate:
   verification is a whole-log operation at the end, not a per-turn negotiation.
4. **Final reveal** — every nonce at once, in the terminal state. Now the audit
   (6.1.4) can re-hash the entire match.

**The nonce is the hinge.** Releasing it per turn would let a peer verify each
move immediately, which sounds better and is worse: a peer that verified turn 4
and disliked the result could abandon the match before turn 5 and argue about it
afterwards. Withholding until the end means the only moment to walk away is
after every move is already sealed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

__all__ = ["Stage", "ProtocolError", "TurnExchange"]


class Stage(str, Enum):
    """How far one turn's exchange has got."""

    AWAITING_COMMITS = "awaiting_commits"
    AWAITING_ACKS = "awaiting_acks"
    AWAITING_REVEALS = "awaiting_reveals"
    SETTLED = "settled"


class ProtocolError(RuntimeError):
    """The opponent, or we, did something the protocol forbids.

    Raised rather than tolerated. Every one of these is either a bug on our side
    or an attempt to gain information out of order on theirs, and continuing
    would mean playing a game whose guarantees no longer hold.
    """


@dataclass
class TurnExchange:
    """One turn's four-phase exchange, tracked from both sides.

    Attributes:
        step: Which turn this is.
        commits: ``{"us": digest, "them": digest}`` as they arrive.
        acks: Who has confirmed holding the other's commit.
        reveals: ``{"us": payload, "them": payload}`` — never a nonce.
        stage: Where the exchange has got to.
    """

    step: int
    commits: dict[str, str] = field(default_factory=dict)
    acks: set[str] = field(default_factory=set)
    reveals: dict[str, dict] = field(default_factory=dict)
    stage: Stage = Stage.AWAITING_COMMITS

    # --- phase 1 ------------------------------------------------------------

    def commit(self, side: str, digest: str) -> Stage:
        """Record a commitment hash. Nothing else may travel yet.

        Raises:
            ProtocolError: On a second commit from the same side — that is an
                attempt to change a move after seeing something, which is the
                exact behaviour the hash exists to prevent.
        """
        if side in self.commits:
            raise ProtocolError(f"{side} already committed at step {self.step}")
        if self.stage is not Stage.AWAITING_COMMITS:
            raise ProtocolError(f"commit arrived during {self.stage.value}")

        self.commits[side] = digest
        if len(self.commits) == 2:
            self.stage = Stage.AWAITING_ACKS
        return self.stage

    # --- phase 2 ------------------------------------------------------------

    def acknowledge(self, side: str) -> Stage:
        """Confirm this side holds the opponent's commitment.

        The ack is what makes revealing safe. Without it the peer who sends
        first cannot know the other is locked in, and revealing to an opponent
        still free to choose would hand them the game.
        """
        if self.stage is Stage.AWAITING_COMMITS:
            raise ProtocolError(f"{side} acked before both commits arrived")
        if self.stage is not Stage.AWAITING_ACKS:
            raise ProtocolError(f"ack arrived during {self.stage.value}")

        self.acks.add(side)
        if len(self.acks) == 2:
            self.stage = Stage.AWAITING_REVEALS
        return self.stage

    # --- phase 3 ------------------------------------------------------------

    def reveal(self, side: str, payload: dict) -> Stage:
        """Disclose move, hint and intent — **never the nonce** (M#18).

        Raises:
            ProtocolError: If a nonce is present, or if revealing early. The
                nonce check guards our own code as much as theirs: leaking it
                per turn would quietly dismantle the end-of-match audit while
                every test still passed.
        """
        if self.stage is not Stage.AWAITING_REVEALS:
            raise ProtocolError(f"{side} revealed during {self.stage.value}")
        if "nonce" in payload:
            raise ProtocolError(
                f"{side} included a nonce in a step reveal; nonces are withheld "
                "until the final reveal (M#18)"
            )

        self.reveals[side] = payload
        if len(self.reveals) == 2:
            self.stage = Stage.SETTLED
        return self.stage

    # --- state --------------------------------------------------------------

    @property
    def settled(self) -> bool:
        """Whether both sides have revealed and the turn can be applied."""
        return self.stage is Stage.SETTLED

    def waiting_for(self) -> str:
        """What is outstanding, in words, for the log and the watchdog."""
        missing = {
            Stage.AWAITING_COMMITS: {"us", "them"} - set(self.commits),
            Stage.AWAITING_ACKS: {"us", "them"} - self.acks,
            Stage.AWAITING_REVEALS: {"us", "them"} - set(self.reveals),
            Stage.SETTLED: set(),
        }[self.stage]
        return f"{self.stage.value}: {', '.join(sorted(missing)) or 'nobody'}"
