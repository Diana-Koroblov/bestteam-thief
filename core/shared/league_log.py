"""The counted-match declaration, read from the log rather than typed (9.1.3).

M#37 makes us declare how many counted matches we have already played, and M#38
disqualifies **the entire project** for declaring it wrongly. PRD_negotiation N8
says the declared count must match ``docs/LEAGUE_LOG.md``.

So nothing here takes a number from a human. The handshake reads the log, and the
log is the same table a grader reads. A false declaration then requires editing
the evidence, which is a different act from mistyping a digit — and mistyping a
digit is how an honest team gets disqualified.

**The doc states its own total in prose as well as in rows, and this file refuses
when the two disagree.** That line is what a human quotes to an opponent; the
rows are what a grader counts. A log whose summary has drifted from its table is
not a source of truth for either, and the drift is silent: a row added without
updating the total looks exactly like a correct log.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

__all__ = ["LeagueLogError", "LeagueRecord", "DEFAULT_PATH", "parse", "read", "counted_matches"]

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "docs" / "LEAGUE_LOG.md"

# The heading whose table holds counted matches. Warm-ups live under a different
# one and must never be counted (M#52), so the section is located by name rather
# than by taking the first table in the file.
COUNTED_SECTION = "## Counted matches"
OPPONENT_COLUMN = "Opponent team"

_DECLARED = re.compile(r"\*\*Counted matches so far:\s*(\d+)\*\*")

# Appendix F and M#31. Reported as warnings rather than raised: playing an
# eleventh match is a rule breach, but discovering it here should stop a human,
# not crash a peer that is mid-handshake.
MIN_TO_PASS = 2
MAX_PER_TEAM = 10


class LeagueLogError(ValueError):
    """The log cannot be read, or contradicts itself.

    Raised rather than defaulted. A handshake that quietly declared 0 because it
    could not find the table would be making exactly the claim M#38 punishes.
    """


@dataclass(frozen=True)
class LeagueRecord:
    """What the log says, split into the parts that must agree.

    Attributes:
        counted: Rows naming an opponent.
        declared: The total the document states in prose.
        opponents: Team names, in table order, for the M#52 duplicate check.
    """

    counted: int
    declared: int
    opponents: tuple[str, ...]

    def warnings(self) -> list[str]:
        """Everything a human should see before declaring this count.

        Returned, never raised. Whether to play an eleventh match is a decision
        for the people involved; refusing to hand back the number would only
        mean the count gets typed by hand instead.
        """
        found: list[str] = []
        seen = [name.lower() for name in self.opponents]
        repeats = sorted({name for name in seen if seen.count(name) > 1})
        if repeats:
            found.append(
                f"opponent(s) {', '.join(repeats)} appear more than once; only one "
                "counted match per opponent is permitted (M#52)"
            )
        if self.counted > MAX_PER_TEAM:
            found.append(f"{self.counted} counted matches exceeds the maximum of {MAX_PER_TEAM} (F)")
        if self.counted < MIN_TO_PASS:
            found.append(
                f"{self.counted} counted match(es) so far; {MIN_TO_PASS} are required "
                "for any grade at all (M#31)"
            )
        return found


def _section(text: str) -> list[str]:
    """Return the lines under the counted-matches heading, up to the next one."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip().startswith(COUNTED_SECTION):
            rest = lines[index + 1 :]
            end = next(
                (n for n, item in enumerate(rest) if item.strip().startswith("## ")), len(rest)
            )
            return rest[:end]
    raise LeagueLogError(f"no {COUNTED_SECTION!r} heading found; the log cannot be counted")


def _cells(row: str) -> list[str]:
    """Split one markdown table row into its trimmed cells."""
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def _opponents(lines: list[str]) -> tuple[str, ...]:
    """Return the opponent named by every filled row of the section's table."""
    rows = [line for line in lines if line.strip().startswith("|")]
    if len(rows) < 2:
        raise LeagueLogError("the counted-matches section holds no table")
    header = _cells(rows[0])
    if OPPONENT_COLUMN not in header:
        raise LeagueLogError(
            f"the counted-matches table has no {OPPONENT_COLUMN!r} column; "
            f"found {', '.join(header)}"
        )
    column = header.index(OPPONENT_COLUMN)
    # rows[1] is the |---|---| separator. Everything after it is data, and a row
    # with an empty opponent cell is a blank template row, not a played match.
    named = (_cells(row) for row in rows[2:])
    return tuple(cell[column] for cell in named if column < len(cell) and cell[column])


def parse(text: str) -> LeagueRecord:
    """Return what *text* declares, without judging whether it is consistent."""
    match = _DECLARED.search(text)
    if match is None:
        raise LeagueLogError(
            "the log does not state 'Counted matches so far: N'; that line is what "
            "is quoted to an opponent and it cannot be inferred from the table"
        )
    opponents = _opponents(_section(text))
    return LeagueRecord(counted=len(opponents), declared=int(match.group(1)), opponents=opponents)


@lru_cache(maxsize=4)
def read(path: Path = DEFAULT_PATH) -> LeagueRecord:
    """Return the record in *path*.

    Cached like ``step_zero.commit_hash`` and for the same reason: the number we
    declare must be the same one all series. Re-reading mid-match could answer
    differently from the value we signed at the handshake.
    """
    try:
        return parse(Path(path).read_text(encoding="utf-8"))
    except OSError as error:
        raise LeagueLogError(f"cannot read the league log at {path}: {error}") from error


def counted_matches(path: Path = DEFAULT_PATH) -> int:
    """Return the count to declare (M#37), or raise if the log contradicts itself."""
    record = read(path)
    if record.counted != record.declared:
        raise LeagueLogError(
            f"{path} counts {record.counted} filled row(s) but declares {record.declared}. "
            "Refusing to guess which is true: an over-declaration costs diversity points "
            "and an under-declaration disqualifies the project (M#38)."
        )
    return record.counted
