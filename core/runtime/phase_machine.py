"""The turn's state machine, as an explicit table (TODO 6.4.1, M#4, M#5).

**A hang is worse than a loss.** A peer that stalls waiting for a message that
will never arrive takes the opponent down with it, and the match ends with no
result for either side — which is the one outcome nobody can appeal. So every
failure path in this project terminates, and this is where that is enforced.

The table is written out rather than implied by ``if`` statements for a reason
the rulebook is blunt about (M#4): "which module changed the state" must have
exactly one answer. A transition scattered across five call sites has five
answers, and the one that fires at 2 a.m. during a graded match is the one
nobody reviewed.

Two rules give the machine its shape:

* **``TECHNICAL_LOSS`` is reachable from everywhere.** Any phase can fail —
  the network, the model, the opponent, our own code — and every one of those
  must have somewhere legal to go. A failure with no legal exit becomes a hang.
* **Terminal means terminal.** ``TECHNICAL_LOSS`` and ``COMPLETE`` have no
  outgoing edges at all, so a lost sub-game cannot quietly resume and start
  sending moves again after the result was recorded.
"""

from __future__ import annotations

from enum import Enum

__all__ = ["Phase", "IllegalTransitionError", "PhaseMachine", "TRANSITIONS"]


class Phase(str, Enum):
    """Where one turn currently stands.

    Inherits ``str`` so a phase serialises as ``"committing"`` rather than
    ``"Phase.COMMITTING"`` — these names go into the log the grader reads.
    """

    WAITING_FOR_OPPONENT = "waiting_for_opponent"
    COMPUTING_MOVE = "computing_move"
    COMMITTING = "committing"
    AWAITING_REVEAL = "awaiting_reveal"
    VERIFYING = "verifying"
    TECHNICAL_LOSS = "technical_loss"
    COMPLETE = "complete"


TERMINAL = frozenset({Phase.TECHNICAL_LOSS, Phase.COMPLETE})

# The happy path, and nothing else. Every non-terminal phase additionally gets
# an edge to TECHNICAL_LOSS, added below rather than written out seven times.
_FORWARD: dict[Phase, frozenset[Phase]] = {
    Phase.WAITING_FOR_OPPONENT: frozenset({Phase.COMPUTING_MOVE}),
    Phase.COMPUTING_MOVE: frozenset({Phase.COMMITTING}),
    Phase.COMMITTING: frozenset({Phase.AWAITING_REVEAL}),
    Phase.AWAITING_REVEAL: frozenset({Phase.VERIFYING}),
    # A verified turn either starts the next one or ends the sub-game.
    Phase.VERIFYING: frozenset({Phase.WAITING_FOR_OPPONENT, Phase.COMPLETE}),
}

TRANSITIONS: dict[Phase, frozenset[Phase]] = {
    **{phase: edges | {Phase.TECHNICAL_LOSS} for phase, edges in _FORWARD.items()},
    Phase.TECHNICAL_LOSS: frozenset(),
    Phase.COMPLETE: frozenset(),
}


class IllegalTransitionError(RuntimeError):
    """An attempted move the table does not allow.

    Raised rather than logged. An illegal transition means our own code has
    lost track of where it is, and continuing from that point would put
    unverifiable moves on the wire — far worse than crashing into a recorded
    technical loss.
    """


class PhaseMachine:
    """Tracks one turn's phase and refuses every transition not in the table.

    Attributes:
        phase: Where we are now.
        history: Every phase entered, in order, for the replay and the log.
    """

    def __init__(self, phase: Phase = Phase.WAITING_FOR_OPPONENT) -> None:
        self.phase = phase
        self.history: list[Phase] = [phase]

    @property
    def terminal(self) -> bool:
        """Whether the sub-game is over, either way."""
        return self.phase in TERMINAL

    @property
    def lost(self) -> bool:
        """Whether it ended in a technical loss specifically."""
        return self.phase is Phase.TECHNICAL_LOSS

    def can(self, target: Phase) -> bool:
        """Whether *target* is reachable from here. Asks; never changes state."""
        return target in TRANSITIONS[self.phase]

    def to(self, target: Phase) -> Phase:
        """Move to *target*, or raise.

        Args:
            target: The phase to enter.

        Raises:
            IllegalTransitionError: Naming both phases, because "illegal transition"
                alone cannot be debugged from a log after a match.
        """
        if not self.can(target):
            allowed = ", ".join(sorted(p.value for p in TRANSITIONS[self.phase])) or "nothing"
            raise IllegalTransitionError(
                f"cannot go from {self.phase.value} to {target.value}; "
                f"legal from here: {allowed}"
            )
        self.phase = target
        self.history.append(target)
        return target

    def fail(self, reason: str) -> Phase:
        """End the sub-game in a technical loss, from wherever we are.

        Always legal from a live phase, and deliberately a no-op when already
        terminal: a watchdog and a deadline tracker can both fire on the same
        stalled turn, and the second one must not raise while handling the
        first.
        """
        if self.terminal:
            return self.phase
        self.reason = reason
        return self.to(Phase.TECHNICAL_LOSS)
