"""Scoring one sub-game and aggregating a series. Zero numeric literals.

Appendix F Table 17 fixes all five values, and M#48 requires them to come from
config rather than the source. That is not pedantry: Appendix F permits raising
minimums by agreement, so a hardcoded table would need a code change per match —
and a code change per match is how the two peers end up scoring differently.

The asymmetry is the engine of the whole game. Capture pays the Cop 20 but the
Thief only 5; survival pays the Thief 10 but the Cop only 5. So neither side's
optimal play is the mirror of the other's, and the Cop must force a result
because a stalemate is a Thief win.

A technical loss pays **0 to both sides** (Ch. 3.5) — *"a technical loss zeroes
both sides alike"* — which removes any incentive to win by making the opponent time
out. Worth knowing before designing anything that stresses an opponent's clock.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.domain.rules import Outcome, Verdict

__all__ = ["ScoreTable", "SeriesResult", "score", "aggregate"]


@dataclass(frozen=True)
class ScoreTable:
    """The five Appendix F scoring values, read from the negotiated config."""

    capture_cop: int
    capture_thief: int
    survival_cop: int
    survival_thief: int
    tie_score: int
    technical_loss: int

    @classmethod
    def from_config(cls, config) -> ScoreTable:
        """Build the table from a loaded ``Config``."""
        return cls(
            capture_cop=config.require("scoring.capture_cop"),
            capture_thief=config.require("scoring.capture_thief"),
            survival_cop=config.require("scoring.survival_cop"),
            survival_thief=config.require("scoring.survival_thief"),
            tie_score=config.require("scoring.tie_score"),
            technical_loss=config.require("scoring.technical_loss"),
        )


def score(outcome: Outcome, table: ScoreTable) -> tuple[int, int]:
    """Return ``(cop_points, thief_points)`` for a single sub-game.

    Args:
        outcome: The verdict from ``Rules``.
        table: The negotiated scoring values.

    Raises:
        ValueError: The verdict has no sub-game score. ``TIE`` is one of these —
            it is decided across a whole series, never for one sub-game, and
            silently returning something for it would hide the mistake.
    """
    if outcome.verdict is Verdict.CAPTURE:
        return table.capture_cop, table.capture_thief
    if outcome.verdict is Verdict.SURVIVAL:
        return table.survival_cop, table.survival_thief
    if outcome.verdict is Verdict.TECHNICAL_LOSS:
        return table.technical_loss, table.technical_loss
    raise ValueError(
        f"{outcome.verdict.value} is not a sub-game verdict; a tie is decided "
        "across the whole series, by aggregate()"
    )


@dataclass(frozen=True)
class SeriesResult:
    """The result of a full series against one opponent.

    Attributes:
        cop_points: Our cumulative points across every sub-game.
        thief_points: The opponent's cumulative points.
        verdict: ``TIE`` when the two totals are equal, otherwise the verdict
            of the side that finished ahead.
        sub_games: How many sub-games were aggregated.
    """

    cop_points: int
    thief_points: int
    verdict: Verdict
    sub_games: int


def aggregate(outcomes: list[Outcome], table: ScoreTable) -> SeriesResult:
    """Sum a series and decide the tie.

    Appendix F: a series is ``num_games`` sub-games (fixed at 6), and equal
    cumulative totals award ``tie_score`` to **both** sides rather than to
    neither. The tie is evaluated on the cumulative total, not on sub-games won,
    so three captures and three survivals is 75-45, not a draw.

    One reading the rulebook leaves open (CONTRADICTIONS C-013): a series in
    which **every** sub-game ended in a technical loss also has equal totals, at
    0-0. Paying the tie bonus there would hand two teams points for a series
    neither managed to play, and would reward crashing over competing — which
    directly contradicts *"a technical loss zeroes both sides alike"* (Ch. 3.5). We pay the
    bonus only when at least one sub-game produced a real result.
    """
    cop = sum(score(outcome, table)[0] for outcome in outcomes)
    thief = sum(score(outcome, table)[1] for outcome in outcomes)
    played = [o for o in outcomes if o.verdict is not Verdict.TECHNICAL_LOSS]

    if cop != thief:
        ahead = Verdict.CAPTURE if cop > thief else Verdict.SURVIVAL
        return SeriesResult(cop, thief, ahead, len(outcomes))
    if not played:
        loss = table.technical_loss
        return SeriesResult(loss, loss, Verdict.TECHNICAL_LOSS, len(outcomes))
    return SeriesResult(table.tie_score, table.tie_score, Verdict.TIE, len(outcomes))
