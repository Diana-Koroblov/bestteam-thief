"""Unit tests for core/compat/league_row.py's live-session -> league-row translation.

Found live against the league conformance kit's sparring peer: a plain timeout
(no audit ever received) was being written as `tampered: true`, the same
verdict as a genuinely mismatched record — a forgery accusation over a peer
that simply never answered.
"""

from __future__ import annotations

from core.compat.league_row import row_from_session
from core.domain.scoring import ScoreTable
from core.protocol.schemas import Role

TABLE = ScoreTable(
    capture_cop=20, capture_thief=5, survival_cop=5, survival_thief=10,
    tie_score=2, technical_loss=0,
)


class _State:
    def __init__(self, step: int) -> None:
        self.step = step


class _Session:
    def __init__(self, role: Role, winner: str, step: int = 20) -> None:
        self.role = role
        self.winner = winner
        self.state = _State(step)


class _SDK:
    team_name = "bestteam"
    scoring = TABLE


def test_a_clean_capture_is_scored_and_marks_the_winner_group() -> None:
    session = _Session(Role.COP, winner="cop")
    row = row_from_session(
        sdk=_SDK(), session=session, number=1, raw_result="capture",
        verdict={"passed": True, "received": True}, started="t0", ended="t1",
        their_group="imreeyal", their_commit="b" * 40, our_commit="a" * 40,
    )
    assert row["result"] == "capture"
    assert row["winner_group"] == "bestteam"
    assert row["score"] == {"bestteam": 20, "imreeyal": 5}
    assert row["audit"] == {"log_verified": True, "tampered": False}


def test_our_thief_survival_credits_the_thief_score_to_our_group() -> None:
    session = _Session(Role.THIEF, winner="thief")
    row = row_from_session(
        sdk=_SDK(), session=session, number=2, raw_result="survival",
        verdict={"passed": True, "received": True}, started="t0", ended="t1",
        their_group="imreeyal", their_commit="b" * 40, our_commit="a" * 40,
    )
    assert row["roles"] == {"bestteam": "thief", "imreeyal": "police"}
    assert row["score"] == {"bestteam": 10, "imreeyal": 5}
    assert row["winner_group"] == "bestteam"


def test_a_win_credited_to_the_other_role_names_the_opponent_group() -> None:
    """We are cop; the thief (them) survived — they win, not us."""
    session = _Session(Role.COP, winner="thief")
    row = row_from_session(
        sdk=_SDK(), session=session, number=1, raw_result="survival",
        verdict={"passed": True, "received": True}, started="t0", ended="t1",
        their_group="imreeyal", their_commit="b" * 40, our_commit="a" * 40,
    )
    assert row["winner_group"] == "imreeyal"
    assert row["score"] == {"bestteam": 5, "imreeyal": 10}


def test_a_plain_timeout_is_a_technical_loss_scored_zero_zero_and_not_tampered() -> None:
    """No audit ever arrived — a technical loss (Ch. 3.5), never a forgery claim."""
    session = _Session(Role.COP, winner="cop")
    row = row_from_session(
        sdk=_SDK(), session=session, number=3, raw_result="timeout (no reply)",
        verdict={"passed": False, "received": False, "failed_steps": []},
        started="t0", ended="t1", their_group="imreeyal", their_commit="", our_commit="a" * 40,
    )
    assert row["result"] == "technical_loss"
    assert row["winner_group"] == ""
    assert row["score"] == {"bestteam": 0, "imreeyal": 0}
    assert row["audit"] == {"log_verified": False, "tampered": False}


def test_a_received_but_failed_audit_is_reported_as_genuinely_tampered() -> None:
    """An audit that DID arrive and DID fail is the real forgery signal —
    distinct from a timeout, and must still read that way."""
    session = _Session(Role.COP, winner="cop")
    row = row_from_session(
        sdk=_SDK(), session=session, number=1, raw_result="capture",
        verdict={"passed": False, "received": True, "failed_steps": [5]},
        started="t0", ended="t1", their_group="imreeyal", their_commit="b" * 40, our_commit="a" * 40,
    )
    assert row["audit"] == {"log_verified": False, "tampered": True}


def test_an_unknown_opponent_group_falls_back_to_a_labelled_placeholder() -> None:
    """No sub-game ever agreed with a real peer, so nothing is safe to
    attribute to a real name — used only for the row's own group keys."""
    session = _Session(Role.COP, winner="cop")
    row = row_from_session(
        sdk=_SDK(), session=session, number=1, raw_result="capture",
        verdict={"passed": True, "received": True}, started="t0", ended="t1",
        their_group="", their_commit="", our_commit="a" * 40,
    )
    assert "opponent" in row["roles"]
    assert row["winner_group"] == "bestteam"


def test_the_row_files_the_commit_it_was_given_and_never_reads_one_itself() -> None:
    """M#53. The declared head and the filed head must be the same value.

    This used to call `commit_hash(Path.cwd())` while the declaration read
    `REPO_ROOT`, so a process launched from the wrong directory declared the
    published head and filed a tree with no remote against itself. The row now
    takes the declared value, and taking it is the whole guarantee.
    """
    session = _Session(Role.COP, winner="cop")
    row = row_from_session(
        sdk=_SDK(), session=session, number=1, raw_result="capture",
        verdict={"passed": True, "received": True}, started="t0", ended="t1",
        their_group="imreeyal", their_commit="b" * 40, our_commit="c" * 40,
    )
    assert row["github_commit"] == {"bestteam": "c" * 40, "imreeyal": "b" * 40}


def test_a_dirty_declared_head_is_filed_dirty_rather_than_quietly_cleaned() -> None:
    """The suffix was stripped here, so the row claimed a clean commit over a
    tree the declaration had just told the opponent was dirty — our own two
    artefacts contradicting each other about which code ran."""
    session = _Session(Role.THIEF, winner="thief")
    row = row_from_session(
        sdk=_SDK(), session=session, number=3, raw_result="survival",
        verdict={"passed": True, "received": True}, started="t0", ended="t1",
        their_group="imreeyal", their_commit="b" * 40, our_commit="c" * 40 + "-dirty",
    )
    assert row["github_commit"]["bestteam"] == "c" * 40 + "-dirty"
