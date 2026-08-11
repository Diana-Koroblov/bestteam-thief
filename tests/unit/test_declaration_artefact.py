"""The pre-game declaration, actually filed (TODO 7.2.1, M#24, M#54).

`declaration_<game_id>.json` is one of the four artefacts Ch. 9.3.3 names, and
`MatchFiling.declaration` had exactly three callers — all of them in this test
suite. A real match filed a config snapshot, six logs and a result, and no
declaration at all: the one artefact whose job is to fix, signed, everything
that does not change during the match.

These tests are written against that failure. They go through `live.declare` and
`MatchFiling`, the path match day takes, rather than checking the builder on
arguments handed to it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.crypto.canonical import digest
from core.domain.rules import Outcome, Verdict
from core.protocol.schemas import Negotiation, Role
from core.report.artefacts import build_declaration
from core.report.identifiers import artefact_name
from core.runtime.filing import MatchFiling
from core.runtime.live import declare
from core.runtime.series import SeriesRunner, SubGameReport

GAME_ID = "2026-08-12_bestteam-vs-them_abc12345"
CAPTURE = Outcome(Verdict.CAPTURE, "cop and thief share cell (3, 3)")

THEIR_STEP_ZERO = {
    "team_name": "them",
    "members": ["Their One", "Their Two"],
    "role": "thief",
    "github_commit": "f" * 40,
    "hardware": {"cpu": "theirs"},
}

DECLARED: dict[str, Any] = {
    "teams": {"bestteam": ["Itay Malich", "Diana Koroblov"]},
    "mcp_urls": {"ours": "https://ours.ngrok.dev/mcp"},
    "llm_model": "llama3.1:8b",
    "token_cap": 200_000,
}


class StubConfig:
    """A config whose shared half is a constant, for filing artefacts."""

    shared: dict = {"grid_size": 7}

    def shared_digest(self) -> str:
        return digest(self.shared)

    def get(self, key: str, default=None):
        return {"network_and_league.token_budget_per_series": 200_000}.get(key, default)


class StubStepZero:
    """Our sealed Step-0, as `PreMatch.step_zero` returns it."""

    payload = {"team_name": "bestteam", "members": ["Itay Malich"], "llm_model": "llama3.1:8b"}
    digest = "a" * 64


class StubRuntime:
    """The two attributes `declare` reads, and nothing else."""

    class prematch:  # noqa: N801 - a namespace, not a class used as one
        @staticmethod
        def step_zero() -> StubStepZero:
            return StubStepZero()

    class orchestrator:  # noqa: N801 - as above
        config = StubConfig()


def handshake(step_zero: dict) -> Negotiation:
    """The opponent's settled handshake, carrying *step_zero*."""
    return Negotiation(step=0, role=Role.THIEF, step_zero=step_zero)


def filed(directory: Path) -> dict:
    """Return the declaration on disk."""
    path = directory / artefact_name("declaration", GAME_ID)
    return json.loads(path.read_text(encoding="utf-8"))


def filing_at(directory: Path) -> MatchFiling:
    """A filing for this match, as a fresh role process would build one."""
    return MatchFiling(game_id=GAME_ID, directory=directory, config=StubConfig())


# --- the defect: it was never written ---------------------------------------


def test_a_match_files_a_declaration(tmp_path: Path) -> None:
    """**The bug.** Nothing outside the test suite called the builder, so a real
    match left three of the four mandatory artefacts (Ch. 9.3.3, F.10)."""
    declare(filing_at(tmp_path), StubRuntime(), ("https://ours.dev/mcp", "https://them.dev/mcp"), None)
    assert (tmp_path / artefact_name("declaration", GAME_ID)).is_file()


def test_it_records_both_teams_and_their_members(tmp_path: Path) -> None:
    """Ch. 9.3.3 wants *"the identity of both groups and their members"*, and the
    Step-0 exchange is the only channel that carries the opponent's."""
    theirs = handshake(THEIR_STEP_ZERO)
    declare(filing_at(tmp_path), StubRuntime(), ("ours", "theirs"), theirs)

    teams = filed(tmp_path)["teams"]
    assert teams["bestteam"] == ["Itay Malich"]
    assert teams["them"] == ["Their One", "Their Two"]


def test_an_opponent_who_sends_no_roster_is_empty_not_invented(tmp_path: Path) -> None:
    """**A missing field prompts a question; a wrong one does not.**

    `members` is our own extension, so a peer that never built it must be
    readable as silent rather than refused — and must not be filled in with a
    plausible guess in a signed artefact.
    """
    theirs = handshake({"team_name": "them"})
    declare(filing_at(tmp_path), StubRuntime(), ("ours", "theirs"), theirs)
    assert filed(tmp_path)["teams"]["them"] == []


def test_a_handshake_that_never_settled_records_an_opponent_placeholder(tmp_path: Path) -> None:
    """A refused match still files what it can. `None` is the shape a refusal
    reaches `_series` in, and an absent opponent half is a visible finding."""
    declare(filing_at(tmp_path), StubRuntime(), ("ours", ""), None)
    payload = filed(tmp_path)
    assert payload["teams"]["opponent"] == []
    assert payload["step_zero"]["theirs"] == {"payload": {}, "sha256": ""}


# --- the signed hardware declaration (M#24) ---------------------------------


def test_both_step_zero_payloads_are_filed_with_their_digests(tmp_path: Path) -> None:
    """**This is what makes the hardware declaration a signed one.**

    A machine specification restated in a report proves nothing; one filed beside
    the digest the opponent already holds cannot be rewritten afterwards without
    contradicting a value they can produce.
    """
    theirs = handshake(THEIR_STEP_ZERO)
    declare(filing_at(tmp_path), StubRuntime(), ("ours", "theirs"), theirs)

    sealed = filed(tmp_path)["step_zero"]
    assert sealed["ours"]["sha256"] == StubStepZero.digest
    assert sealed["theirs"]["payload"]["hardware"] == {"cpu": "theirs"}


def test_their_digest_is_recomputed_over_what_they_sent(tmp_path: Path) -> None:
    """Not quoted from them. A digest a peer supplies for its own declaration
    proves nothing; this one is the value their bytes actually hash to, and it
    is ours to stand behind in a dispute."""
    theirs = handshake(THEIR_STEP_ZERO)
    declare(filing_at(tmp_path), StubRuntime(), ("ours", "theirs"), theirs)
    assert filed(tmp_path)["step_zero"]["theirs"]["sha256"] == digest(THEIR_STEP_ZERO)


def test_it_records_the_address_the_match_actually_ran_over(tmp_path: Path) -> None:
    """Read back from the tunnel agent rather than computed from config, so a
    peer that failed to publish is distinguishable from one that did."""
    declare(filing_at(tmp_path), StubRuntime(), ("https://ours.dev/mcp", "https://them.dev/mcp"), None)
    assert filed(tmp_path)["mcp_urls"] == {
        "ours": "https://ours.dev/mcp",
        "theirs": "https://them.dev/mcp",
    }


# --- the match window -------------------------------------------------------


def test_it_is_written_before_the_first_move_with_no_end_time(tmp_path: Path) -> None:
    """An interrupted series must leave the declaration it was played under, and
    an empty `ended_utc` is exactly what an unfinished match should show."""
    filing_at(tmp_path).declaration(**DECLARED)
    payload = filed(tmp_path)
    assert payload["started_utc"]
    assert payload["ended_utc"] == ""


def test_filing_the_result_closes_the_declaration(tmp_path: Path, score_table) -> None:
    """Stamped where the series is known to be over, not by the CLI: an end time
    that depends on the caller remembering is absent from exactly the matches
    that ended badly."""
    filing = filing_at(tmp_path)
    filing.declaration(**DECLARED)
    reports = [SubGameReport(sub_game=1, role=Role.COP, outcome=CAPTURE, steps=35)]
    SeriesRunner(build=None, plan=[], table=score_table, filing=filing, reports=reports).finish()

    assert filed(tmp_path)["ended_utc"]


def test_the_second_process_keeps_the_first_start_time(tmp_path: Path) -> None:
    """**The same two-process problem the result file has.**

    A 3-3 split is two processes in sequence and both write this file. Taking the
    later one's clock would file a match window beginning after three sub-games
    had already been played.
    """
    filing_at(tmp_path).declaration(**DECLARED)
    opened = filed(tmp_path)["started_utc"]

    second = filing_at(tmp_path)
    second.declaration(**DECLARED)
    second.close_declaration()

    assert filed(tmp_path)["started_utc"] == opened


def test_closing_a_match_that_declared_nothing_files_nothing(tmp_path: Path) -> None:
    """A rehearsal run without `--out`, or a harness that never declared. Writing
    one at the end would produce the one artefact whose whole purpose is to have
    existed *before* the first move."""
    assert filing_at(tmp_path).close_declaration() is None
    assert not (tmp_path / artefact_name("declaration", GAME_ID)).exists()


def test_opening_and_closing_it_counts_as_one_artefact(tmp_path: Path) -> None:
    """The scoreboard prints `len(written)` as a file count, and the declaration
    is written twice. Nine files over a directory holding eight is a small
    untruth beside seven numbers a reader is being asked to trust."""
    filing = filing_at(tmp_path)
    filing.declaration(**DECLARED)
    filing.close_declaration()
    assert filing.written == [filing.declaration_path]


def test_the_closed_declaration_restates_what_was_declared(tmp_path: Path) -> None:
    """Verbatim, from what was kept. A second caller re-assembling it could file
    a declaration that disagrees with the one the opponent was handed."""
    filing = filing_at(tmp_path)
    filing.declaration(**DECLARED)
    before = filed(tmp_path)
    filing.close_declaration()
    after = filed(tmp_path)

    assert {key: after[key] for key in DECLARED} == {key: before[key] for key in DECLARED}


# --- the builder ------------------------------------------------------------


def test_the_declaration_carries_every_field_chapter_nine_names() -> None:
    """Groups and members, the four repository links, the MCP addresses, the
    hardware, the model, the token ceiling, and the start and end times."""
    payload = build_declaration(GAME_ID, {"bestteam": ["Itay"]}, {}, {}, "template", 200_000)
    for key in ("teams", "repositories", "mcp_urls", "hardware", "llm_model", "token_cap"):
        assert key in payload
    assert set(payload) >= {"started_utc", "ended_utc", "step_zero"}
