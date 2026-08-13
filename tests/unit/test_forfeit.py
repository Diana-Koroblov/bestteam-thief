"""Filing a match the handshake never settled (TODO 9.5, M#35).

Split from `test_declaration_artefact.py` when that file reached its 150
lines. The seam is real rather than arbitrary: that file is about the shape
of the pre-game declaration, and this one is about what a peer owes the
opponent when it cannot play at all.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.domain.rules import Outcome, Verdict
from core.protocol.schemas import Role
from core.report.identifiers import artefact_name
from core.runtime.live import forfeit
from core.runtime.series import SeriesRunner, SubGameReport
from tests.unit.test_declaration_artefact import DECLARED, GAME_ID, filing_at

CAPTURE = Outcome(Verdict.CAPTURE, "cop and thief share cell (3, 3)")

# --- a match that never started (M#35) --------------------------------------


def test_a_refused_handshake_files_its_sub_games_as_technical_losses(
    tmp_path: Path, score_table
) -> None:
    """🐛 **Observed in a real localhost match.**

    Our peer's outbound handshake failed while its *inbound* server had already
    agreed, so the opponent played its half against a peer that had given up. It
    scored three technical losses and filed a six-row report; we filed three,
    because the process exited before a filing was ever built.

    Two teams, one match, two reports disagreeing about how many sub-games
    happened — a contradictory pair, 0 for **both** under M#35. A technical loss
    is already 0-0, so filing them costs nothing and buys a report that agrees
    with theirs.
    """

    filing = filing_at(tmp_path)
    filing.declaration(**DECLARED)
    forfeit(filing, [(1, Role.COP), (2, Role.COP), (3, Role.COP)], score_table, "no handshake")

    filed = json.loads(filing.result_path.read_text(encoding="utf-8"))
    assert [row["sub_game"] for row in filed["sub_games"]] == [1, 2, 3]
    assert {row["verdict"] for row in filed["sub_games"]} == {Verdict.TECHNICAL_LOSS.value}
    assert filed["totals"] == {"ours": 0, "theirs": 0, "sub_games_played": 3}


def test_a_forfeited_half_still_merges_with_a_played_half(
    tmp_path: Path, score_table
) -> None:
    """**The property that actually matters.** One role process forfeits, the
    other plays; the filed report must still cover all six sub-games, because
    that is the number the opponent's report will show."""

    forfeit(filing_at(tmp_path), [(1, Role.COP), (2, Role.COP), (3, Role.COP)],
            score_table, "no handshake")
    played = [
        SubGameReport(sub_game=n, role=Role.THIEF, outcome=CAPTURE, steps=35) for n in (4, 5, 6)
    ]
    SeriesRunner(
        build=None, plan=[], table=score_table, filing=filing_at(tmp_path), reports=played
    ).finish()

    filed = json.loads((tmp_path / artefact_name("result", GAME_ID)).read_text(encoding="utf-8"))
    assert filed["totals"]["sub_games_played"] == 6
    assert [row["sub_game"] for row in filed["sub_games"]] == [1, 2, 3, 4, 5, 6]


def test_a_forfeit_reason_is_recorded_so_it_can_be_quoted(
    tmp_path: Path, score_table
) -> None:
    """With no referee, "your peer never completed its handshake" is the entire
    remedy available to either side."""

    filing = filing_at(tmp_path)
    forfeit(filing, [(1, Role.COP)], score_table, "handshake not agreed: REFUSED_BY_OPPONENT")
    filed = json.loads(filing.result_path.read_text(encoding="utf-8"))
    assert "REFUSED_BY_OPPONENT" in filed["sub_games"][0]["reason"]


