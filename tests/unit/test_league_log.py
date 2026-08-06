"""Reading the counted-match total off the log (TODO 9.1.3, M#37, M#38).

M#38 disqualifies the **entire project** for one wrong declaration, and the way
that happens to an honest team is not fraud — it is a number that was true last
week. So the tests below are mostly about the ways a document can quietly lie:
rows that are bookings rather than matches, a summary line that drifted from its
own table, and a warm-up section sitting two headings away from the real one.
"""

from __future__ import annotations

import pytest

from core.shared.league_log import (
    DEFAULT_PATH,
    LeagueLogError,
    counted_matches,
    parse,
    read,
)

HEADER = "| # | Date | Opponent team | Our role | Our score |"
RULE = "|---|---|---|---|---|"


def log(rows: str, declared: int = 0, extra: str = "") -> str:
    """A minimal document in the shipped file's shape."""
    return "\n".join(
        (
            "# League Log",
            "",
            "## Counted matches",
            "",
            HEADER,
            RULE,
            rows,
            "",
            f"**Counted matches so far: {declared}** <- declared to every opponent (M#37)",
            extra,
        )
    )


# --- counting ---------------------------------------------------------------


def test_a_blank_template_row_is_not_a_played_match() -> None:
    """The shipped log ships eight of them, and a peer that counted them would
    declare eight matches it never played — an over-declaration that costs the
    diversity reward and reads, to a grader holding the true count, as a lie."""
    assert parse(log("| 1 | | | | |\n| 2 | | | | |")).counted == 0


def test_a_row_naming_an_opponent_counts() -> None:
    assert parse(log("| 1 | 2026-08-09 | redteam | cop | 20 |", declared=1)).counted == 1


def test_the_column_is_found_by_name_not_by_position() -> None:
    """Someone will add or reorder a column before the deadline.

    The row is built so the two parsers disagree: the opponent's name sits where
    a *name*-based reader looks and the cell a *position*-based reader would take
    is empty. A positional parser counts 0 here, which is an under-declaration,
    which is the disqualifying direction (M#38).
    """
    text = log("| 1 | redteam | |", declared=1).replace(HEADER, "| # | Opponent team | Date |")
    assert parse(text).opponents == ("redteam",)


# --- the ways the document can contradict itself ----------------------------


def test_a_summary_that_disagrees_with_its_table_is_refused(tmp_path) -> None:
    """**The realistic failure.** A row gets added and the total below it does
    not. Guessing which half is true is the one thing that must not happen here:
    guessing high costs points, guessing low disqualifies the project (M#38)."""
    path = tmp_path / "drifted.md"
    path.write_text(log("| 1 | 2026-08-09 | redteam | cop | 20 |", declared=0), encoding="utf-8")
    with pytest.raises(LeagueLogError, match="counts 1 filled row"):
        counted_matches(path)


def test_a_document_with_no_summary_line_is_refused(tmp_path) -> None:
    """That line is what a human quotes to an opponent. Inferring it from the
    table would mean the number we say and the number we file could differ."""
    path = tmp_path / "nosummary.md"
    path.write_text("# League Log\n\n## Counted matches\n\n" + HEADER, encoding="utf-8")
    with pytest.raises(LeagueLogError, match="Counted matches so far"):
        read(path)


def test_a_missing_section_is_refused_rather_than_counted_as_zero(tmp_path) -> None:
    """Zero is a *legitimate* declaration right now, so a parser that fell back
    to it would be indistinguishable from one that worked — until the day it
    mattered."""
    path = tmp_path / "empty.md"
    path.write_text("# League Log\n\n**Counted matches so far: 3**", encoding="utf-8")
    with pytest.raises(LeagueLogError, match="heading"):
        read(path)


def test_an_unreadable_file_is_refused(tmp_path) -> None:
    with pytest.raises(LeagueLogError, match="cannot read"):
        read(tmp_path / "absent.md")


# --- the sections that must never be counted --------------------------------


def test_warm_ups_are_not_counted() -> None:
    """M#52 makes warm-ups uncounted and recommends them. A parser that took the
    first table it found would count them and disqualify us for the courtesy."""
    text = log(
        "| 1 | | | | |",
        extra="\n## Warm-up matches\n\n| Date | Opponent | Purpose |\n|---|---|---|\n"
        "| 2026-08-08 | redteam | shake out the protocol |",
    )
    assert parse(text).counted == 0


def test_a_booked_fixture_is_not_a_played_match() -> None:
    """The scheduling table has an `Opponent team` column too, and it lists teams
    we have *contacted*. Counting it would declare four matches on the day we
    booked four — the single most expensive off-by-one in the project."""
    text = log(
        "| 1 | | | | |",
        extra="\n## Scheduling pipeline\n\n| Opponent team | Contact | Status |\n|---|---|---|\n"
        "| redteam | a@b.c | agreed |\n| bluoteam | d@e.f | contacted |",
    )
    assert parse(text).counted == 0


# --- warnings ---------------------------------------------------------------


def test_playing_one_opponent_twice_is_reported() -> None:
    """M#52 allows one counted match per opponent. Reported rather than raised:
    it is a fact about the log, and a peer mid-handshake is the wrong place to
    crash over it."""
    rows = "| 1 | d | redteam | cop | 20 |\n| 2 | d | RedTeam | thief | 10 |"
    record = parse(log(rows, declared=2))
    assert any("redteam" in warning for warning in record.warnings())


def test_being_short_of_the_minimum_is_reported() -> None:
    """M#31: fewer than two counted matches is no grade at all, so the number is
    worth seeing every single time it is declared."""
    assert any("M#31" in warning for warning in parse(log("| 1 | | | | |")).warnings())


def test_exceeding_the_maximum_is_reported() -> None:
    rows = "\n".join(f"| {n} | d | team{n} | cop | 5 |" for n in range(1, 12))
    assert any("maximum" in warning for warning in parse(log(rows, declared=11)).warnings())


def test_a_healthy_log_reports_nothing_but_the_minimum() -> None:
    """A warning list that is never empty is a warning list nobody reads."""
    rows = "| 1 | d | redteam | cop | 20 |\n| 2 | d | blueteam | thief | 10 |"
    assert parse(log(rows, declared=2)).warnings() == []


# --- the shipped document ---------------------------------------------------


def test_the_shipped_log_is_readable_and_declares_what_it_counts() -> None:
    """The only test here that fails when the *real* document drifts, which is
    the document a grader reads and an opponent is quoted.

    `counted_matches` raises on a disagreement, so calling it is the assertion;
    comparing the two halves afterwards is what says so out loud.
    """
    record = read(DEFAULT_PATH)
    assert counted_matches(DEFAULT_PATH) == record.counted == record.declared
