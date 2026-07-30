"""Terminal conditions: when a sub-game ends and who won.

Four ways a sub-game ends (Ch. 3.5):

* the Cop occupies the Thief's cell and claims the capture;
* the Cop's barrier lands on the Thief's cell (M#46);
* the Thief is sealed in — every orthogonal neighbour blocked (M#47);
* the Thief survives ``survival_threshold`` valid steps.

Plus a fifth that is not a game outcome at all: a crash, a missed deadline or a
cryptographic forgery. The book is blunt about how that scores — *"ההפסד הטכני
מאפס את שני הצדדים כאחד, ובכך מתמרץ את שניהם לשמור על תקינות פרוטוקולרית ולא
לנצח בפסק זמן"*. **Both** sides get 0. There is no way to profit from an
opponent's failure, so inducing one is never worth engineering.

Three of these readings are not stated by the rulebook and are config flags
negotiated per match (CONTRADICTIONS C-006). They are implemented, not merely
defaulted: an opponent may sign the opposite reading and we then play under it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.domain.board import Board
from core.domain.game_state import GameState
from core.domain.movement import is_immobilised

__all__ = ["Verdict", "Outcome", "Rules"]


class Verdict(str, Enum):
    """How a sub-game or a series ended."""

    CAPTURE = "CAPTURE"
    SURVIVAL = "SURVIVAL"
    TECHNICAL_LOSS = "TECHNICAL_LOSS"
    TIE = "TIE"


@dataclass(frozen=True)
class Outcome:
    """A verdict together with the reason it fired.

    The reason is not decoration. When we claim a capture the opponent may
    dispute it, and the log audit resolves the dispute — so the record has to
    say *which* rule ended the game, not merely that one did.
    """

    verdict: Verdict
    reason: str


@dataclass(frozen=True)
class Rules:
    """The terminal conditions, resolved once from the negotiated config.

    Built once per sub-game rather than parsed per call: an expectimax search
    evaluates this thousands of times per turn, and re-reading config in the hot
    loop would be both slow and a chance for the two peers to drift.

    Attributes:
        board: Supplies bounds for the sealed-in test.
        survival_threshold: Valid steps the Thief must survive to win.
        resolution: ``after_moves`` (default) evaluates capture once both
            actions have applied, so a barrier dropped on a cell the Thief has
            just left does **not** capture. ``before_moves`` evaluates against
            the pre-move snapshot. (C-006a)
        stay_counts_as_move: When False (default), M#47 is decided by
            **adjacency** — all four orthogonal neighbours blocked. When True,
            STAY counts as an available move, which makes M#47 unreachable,
            because STAY is legal from every cell. (C-006b)
        swap_is_capture: When True (default), the two agents exchanging cells in
            one turn counts as a capture rather than passing through each
            other. (C-006c)
    """

    board: Board
    survival_threshold: int
    resolution: str = "after_moves"
    stay_counts_as_move: bool = False
    swap_is_capture: bool = True

    @classmethod
    def from_config(cls, config, board: Board) -> Rules:
        """Build the rules from a loaded ``Config``. No literals, all negotiated."""
        return cls(
            board=board,
            survival_threshold=config.require("movement_and_barriers.survival_threshold"),
            resolution=config.require("capture.resolution"),
            stay_counts_as_move=config.require("capture.stay_counts_as_move"),
            swap_is_capture=config.require("capture.swap_is_capture"),
        )

    def sealed_in(self, state: GameState) -> bool:
        """Return True when the Thief is immobilised under the agreed reading."""
        if self.stay_counts_as_move:
            return False
        return is_immobilised(state.thief, state.barriers, self.board)

    def verdict(self, state: GameState) -> Outcome | None:
        """Return the outcome of *state*, or None if the sub-game continues.

        Capture conditions are checked before survival: a Thief captured on the
        very step that reaches the threshold has been captured, not survived.
        """
        if state.agents_share_a_cell:
            return Outcome(Verdict.CAPTURE, f"cop and thief share cell {state.cop}")
        if self.sealed_in(state):
            return Outcome(Verdict.CAPTURE, f"thief sealed in at {state.thief} (M#47)")
        if state.step >= self.survival_threshold:
            return Outcome(
                Verdict.SURVIVAL,
                f"thief survived {state.step} of {self.survival_threshold} steps",
            )
        return None

    def turn_verdict(self, before: GameState, after: GameState) -> Outcome | None:
        """Return the outcome of the transition *before* → *after*.

        Args:
            before: The state both agents committed against.
            after: The state once both actions have applied.

        The swap is checked first because it is invisible in either snapshot
        alone — each agent simply appears to have moved, and only the pair of
        states reveals that they passed through one another.
        """
        if self.swap_is_capture and before.cop == after.thief and before.thief == after.cop:
            return Outcome(Verdict.CAPTURE, f"cop and thief swapped {before.cop}<->{before.thief}")
        return self.verdict(after if self.resolution == "after_moves" else before)

    @staticmethod
    def technical_loss(reason: str) -> Outcome:
        """Return the outcome for a crash, timeout or forgery. Scores 0-0."""
        return Outcome(Verdict.TECHNICAL_LOSS, reason)
