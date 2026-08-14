"""The six sub-games of a series against one opponent (TODO 9.5, C-011).

`match_driver.py` plays one sub-game. This plays the series: the role plan, the
boundary between sub-games, the audit after each, and the points.

**The role plan is ours alone.** `[number of sub-games]` is fixed at 6 and no
appendix says who plays Cop in which of them, so we state 3-3 in the handshake
and refuse a match that answers differently (C-011, N17). But "3-3" is symmetric
— both peers send the identical string and it settles nothing about who starts
as Cop. What settles that is `Negotiation.role`, declared per sub-game and
checked to be the opposite of ours. So the plan below is built from the role this
process actually holds, and the handshake is what stops the two peers building
mirror-image plans.

**One process, one role — including here.** A published repository ships one
brain (ADR-001, M#1, M#2), so a 3-3 split is two processes in sequence: the Cop
repository plays its three sub-games and the Thief repository plays the other
three, each filing its own artefacts into the same directory. `plan` is
therefore a list of the sub-games *this* process plays, not always all six.

**Nothing here builds a peer.** `build` is supplied, exactly as `MatchDriver`
takes a runtime and a client rather than constructing them. A driver over a live
ngrok URL and a driver over the in-process transport differ in every way except
the one this file cares about, which is that a sub-game can be played.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from core.domain.rules import Outcome, Rules, Verdict
from core.domain.scoring import ScoreTable, level_series, score
from core.protocol.schemas import Role
from core.runtime.match_closing import exchange_and_audit
from core.runtime.match_driver import MatchDriver

__all__ = ["SubGameReport", "SeriesReport", "SeriesRunner", "roles_for", "OTHER"]

# The role the opponent holds while we hold ours. There are exactly two.
OTHER = {Role.COP: Role.THIEF, Role.THIEF: Role.COP}


def roles_for(split: str, first: Role, count: int) -> list[Role]:
    """Return the role for each sub-game of the series, in order.

    Args:
        split: The negotiated plan, ``"3-3"`` — the block lengths, in order.
            More than two blocks alternate the same way, so ``"1-1-1-1-1-1"``
            is a legal way to say "swap every sub-game".
        first: The role held in the **first** block. Ours, from this process's
            own configuration; see the module docstring for why the split string
            cannot supply it.
        count: `[number of sub-games]`, fixed at 6 by Appendix F Table 18.

    Raises:
        ValueError: The split is malformed, or its blocks do not add up to
            *count*. Loud rather than truncated: a plan covering five sub-games
            of a six-sub-game series would play a whole match before anyone
            noticed the missing one, and by then the opponent has filed a report
            that disagrees with ours.
    """
    blocks = split.split("-")
    if not all(block.isdigit() for block in blocks) or len(blocks) < 2:
        raise ValueError(f"role split {split!r} is not blocks of digits, e.g. '3-3' (C-011)")

    roles: list[Role] = []
    current = first
    for block in blocks:
        roles.extend([current] * int(block))
        current = OTHER[current]
    if len(roles) != count:
        raise ValueError(
            f"role split {split!r} covers {len(roles)} sub-games but the series is "
            f"{count} (Appendix F Table 18)"
        )
    return roles


@dataclass(frozen=True)
class SubGameReport:
    """One finished sub-game, priced and audited.

    Attributes:
        role: The side **we** played, which is what turns a Cop/Thief score into
            our score and theirs.
        outcome: The verdict and the rule that fired.
        audit: The re-hash of *their* log, or None when the closing exchange
            never completed. None and "failed" are different findings and are
            kept apart: one is an accusation, the other is a missing document.
        llm_tokens: Model tokens this sub-game cost us (M#54, which wants the
            sub-game figure as well as the series). Per sub-game rather than per
            series because the series is summed from the **merged** rows, and
            under a 3-3 split neither process meters the other's half.
    """

    sub_game: int
    role: Role
    outcome: Outcome
    steps: int
    audit: Any = None
    llm_tokens: int = 0

    def points(self, table: ScoreTable) -> tuple[int, int]:
        """Return ``(ours, theirs)`` for this sub-game."""
        cop, thief = score(self.outcome, table)
        return (cop, thief) if self.role is Role.COP else (thief, cop)

    def row(self, table: ScoreTable) -> dict[str, Any]:
        """Return the entry `build_result` files for this sub-game (7.2.4)."""
        cop, thief = score(self.outcome, table)
        ours, theirs = self.points(table)
        return {
            "sub_game": self.sub_game,
            "role": self.role.value,
            "verdict": self.outcome.verdict.value,
            "reason": self.outcome.reason,
            "steps": self.steps,
            "cop_points": cop,
            "thief_points": thief,
            "our_points": ours,
            "their_points": theirs,
            "opponent_log_audit": _audit_word(self.audit),
            "llm_tokens": self.llm_tokens,
        }


def _audit_word(audit: Any) -> str:
    """Describe an audit in one word a grader can scan a column of."""
    if audit is None:
        return "not_run"
    return "passed" if audit.passed else "FAILED"


def _tokens_spent(driver: MatchDriver) -> int:
    """Return the model tokens the sub-game just played cost us (M#54).

    Read through `getattr` because a test double standing in for the runtime is
    a legitimate driver and has no meter. A missing meter reports 0, which is
    the same answer the `template` provider gives and is true of every double we
    ship: none of them calls a model.
    """
    meter = getattr(getattr(driver, "runtime", None), "meter", None)
    return meter.take() if meter is not None else 0


@dataclass(frozen=True)
class SeriesReport:
    """Everything the series produced, and what the meeting is worth.

    Attributes:
        our_points: Summed across the sub-games, attributed by *team*.
        verdict: `TIE` when the totals are level and at least one sub-game was
            really played, `TECHNICAL_LOSS` when level with none played (C-013),
            and None when the points decided it. None rather than a winner
            enum: a series is scored, not won, and inventing a verdict for the
            decided case would put a claim in the report that the totals beside
            it already make.
        league_points: What each side collects under the tie rule, or None when
            the totals stand as they are.
    """

    sub_games: tuple[SubGameReport, ...]
    our_points: int
    their_points: int
    verdict: Verdict | None
    league_points: int | None

    def rows(self, table: ScoreTable) -> list[dict[str, Any]]:
        """Return every sub-game entry, oldest first."""
        return [report.row(table) for report in self.sub_games]

    def summary(self) -> dict[str, Any]:
        """Return the block naming what the meeting is worth in the league.

        Filed **beside** the arithmetic rather than replacing it: `totals` in
        the result file is the sum of the sub-games, and this is what the tie
        rule makes of it. A level 45-45 series pays 2-2, and a report showing
        only one of those two numbers invites the reader to think the other was
        a mistake.
        """
        return {
            "verdict": self.verdict.value if self.verdict else "decided_on_points",
            "our_points": self.our_points,
            "their_points": self.their_points,
            "our_league_points": (
                self.league_points if self.league_points is not None else self.our_points
            ),
            "their_league_points": (
                self.league_points if self.league_points is not None else self.their_points
            ),
        }

    @property
    def forged(self) -> list[int]:
        """Sub-games whose opponent log failed its re-hash (Ch. 5.4, M#19).

        Reported, never acted on. A failed audit is a total technical loss for
        the forger, but that verdict is awarded by a league with two reports in
        front of it — not by the accusing peer, scoring its own match from its
        own re-hash. What we owe is the evidence, filed.
        """
        return [
            report.sub_game
            for report in self.sub_games
            if report.audit is not None and not report.audit.passed
        ]


@dataclass
class SeriesRunner:
    """Plays this process's share of a series and prices the result.

    Attributes:
        build: ``(sub_game, role) -> MatchDriver``, called once per sub-game.
        plan: The ``(sub_game, role)`` pairs this process plays, in order.
        table: The negotiated scoring values.
        filing: A `MatchFiling`, or None to play without writing artefacts.
            Optional because a warm-up should not file a log that looks
            like a league match.
        reports: Filled as the series proceeds, so a series interrupted halfway
            still has everything it managed to play.
        settle: Seconds to wait between sub-games, so an opponent still closing
            the last one is listening before our first commit of the next
            arrives. Defaults to 0 because in-process play has no such window
            and every test would otherwise pay it; the live CLI sets it.
    """

    build: Callable[[int, Role], MatchDriver]
    plan: list[tuple[int, Role]]
    table: ScoreTable
    filing: Any = None
    reopen: Callable[[int], None] | None = None
    reports: list[SubGameReport] = field(default_factory=list)
    settle: float = 0.0

    async def run(self) -> SeriesReport:
        """Play every sub-game in the plan and return the priced series.

        The pause between sub-games is the **other half** of the boundary fix.
        Holding their early messages protects us from losing theirs; it cannot
        stop an opponent losing *ours*, and a peer still finishing its own
        closing exchange is not yet listening for our opening commit. Waiting
        costs seconds; the alternative cost sub-games 2 and 3 on 13/08.
        """
        for index, (sub_game, role) in enumerate(self.plan):
            if index and self.settle > 0:
                await asyncio.sleep(self.settle)
            self.reports.append(await self.play(sub_game, role))
        return self.finish()

    async def play(self, sub_game: int, role: Role) -> SubGameReport:
        """Play one sub-game, close it, file it, and price it.

        The artefacts are written **here**, not after the loop. A series that
        crashes in sub-game four must still leave the first three logs on disk:
        they are the evidence for sub-games that really happened, and holding
        them in memory until the end makes the record as fragile as the process.
        """
        driver = self.build(sub_game, role)
        await driver.play_sub_game()
        # The board is finished, so from here anything the opponent sends
        # belongs to the *next* sub-game — they close at their own pace, not
        # ours. Held from this moment and promoted by the reset below, rather
        # than arriving into an inbox that is about to be cleared.
        begin = getattr(getattr(driver, "runtime", None), "begin_closing", None)
        if begin is not None:
            begin()
        audit = await self._close(driver)
        # Reopen the board for the next sub-game **now**, before the artefacts
        # are written. Filing reads the driver and never the runtime, so this is
        # safe here — and it is not safe later: an opponent whose own closing
        # exchange finished a moment before ours sends its first commit of the
        # next sub-game while we are still writing two files to disk, and a
        # reset that happens afterwards clears the commit we just received. The
        # peer then rejects their reveal as unsealed and takes a technical loss
        # on a sub-game neither side played wrong.
        if self.reopen is not None:
            self.reopen(sub_game + 1)
        report = SubGameReport(
            sub_game=sub_game,
            role=role,
            # `play_sub_game` never returns without setting one, but a driver
            # that somehow did would otherwise crash the series at scoring —
            # after the sub-game was played and before its log was written.
            outcome=driver.outcome or Rules.technical_loss("the sub-game reached no verdict"),
            steps=len(driver.records),
            audit=audit,
            llm_tokens=_tokens_spent(driver),
        )
        if self.filing is not None:
            self.filing.sub_game(report, driver)
        return report

    async def _close(self, driver: MatchDriver) -> Any:
        """Exchange nonces and audit their log, or return None if we cannot.

        Every failure here is swallowed on purpose. The sub-game is already
        over and its verdict already recorded; an opponent who drops the
        connection at the closing exchange has left us unable to *verify* their
        log, which is a finding to file rather than an exception that loses the
        five sub-games after it.
        """
        try:
            return await exchange_and_audit(driver)
        except Exception:  # noqa: BLE001 - see the docstring; nothing here may abort a series
            return None

    def finish(self) -> SeriesReport:
        """Price the sub-games played so far into a series result."""
        pairs = [report.points(self.table) for report in self.reports]
        ours = sum(pair[0] for pair in pairs)
        theirs = sum(pair[1] for pair in pairs)
        outcomes = [report.outcome for report in self.reports]

        verdict: Verdict | None = None
        league: int | None = None
        if ours == theirs:
            league, verdict = level_series(outcomes, self.table)
        report = SeriesReport(tuple(self.reports), ours, theirs, verdict, league)
        if self.filing is not None:
            self.filing.result(report, self.table)
        return report
