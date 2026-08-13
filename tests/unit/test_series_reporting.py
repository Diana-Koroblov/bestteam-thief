"""Reporting a finished series without being asked (TODO 7.3.4, 9.3.3, M#35).

`[email] send_on_series_end = true` described a hook nothing called: the sender,
the transport and the Gatekeeper wiring were all built and tested, and the
report went out when a human remembered. M#35 voids the match and scores 0 for
*both* teams when either side fails to report, so "remembered" is not a
mechanism.

Every branch is covered here because every branch except one leaves a report
unsent, and the failure mode of this module is a match that was won and scored
zero on the paperwork.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.runtime.reporting import send_series_report

GAME_ID = "2026-08-12_bestteam-vs-them_abc12345"


class FakeMailer:
    """A `GmailSender` shaped stand-in that records what it was asked to send."""

    def __init__(self, enabled: bool = True, on_series_end: bool = True, fails: str = "") -> None:
        self.enabled = enabled
        self.on_series_end = on_series_end
        self.fails = fails
        self.recipient = "lecturer@example.com"
        self.sent: list[Path] = []

    def send_result(self, path: Path, subject: str = "") -> None:
        """Record the send, or fail the way the live API would."""
        if self.fails:
            raise RuntimeError(self.fails)
        self.sent.append(path)


def result_file(directory: Path, played: int) -> Path:
    """Write a result artefact holding *played* sub-game rows."""
    path = directory / f"result_{GAME_ID}.json"
    rows = [{"sub_game": n, "our_points": 20, "their_points": 5} for n in range(1, played + 1)]
    path.write_text(json.dumps({"game_id": GAME_ID, "sub_games": rows}), encoding="utf-8")
    return path


def test_a_completed_series_reports_itself(tmp_path: Path) -> None:
    """The whole point: nobody types a command and the report still goes out."""
    mailer = FakeMailer()
    path = result_file(tmp_path, 6)
    message = send_series_report(lambda: mailer, path, 6, counted=True)

    assert mailer.sent == [path]
    assert "sent to lecturer@example.com" in message


def test_the_first_half_of_a_split_holds_its_report_back(tmp_path: Path) -> None:
    """**Mailing three sub-games would create the pair M#35 voids matches over.**

    A 3-3 split is two processes in sequence. If the first to finish reported,
    the grader would hold two messages under one `game_id`, the earlier one
    disagreeing with the later — a contradictory pair produced by the code
    written to satisfy the rule against them.
    """
    mailer = FakeMailer()
    message = send_series_report(lambda: mailer, result_file(tmp_path, 3), 6)

    assert mailer.sent == []
    assert "held back" in message and "3 of 6" in message


def test_holding_back_still_prints_the_manual_command(tmp_path: Path) -> None:
    """The series may never complete — an opponent can drop at sub-game four —
    and the match still has to be reported."""
    message = send_series_report(lambda: FakeMailer(), result_file(tmp_path, 4), 6)
    assert "scripts/send_report.py" in message


def test_a_failed_send_is_loud_and_not_fatal(tmp_path: Path) -> None:
    """The match is over; raising would lose nothing and bury the one line the
    human still has to act on."""
    mailer = FakeMailer(fails="invalid_grant: the token was revoked")
    message = send_series_report(lambda: mailer, result_file(tmp_path, 6), 6, counted=True)

    assert "NOT SENT" in message
    assert "invalid_grant" in message
    assert "scripts/send_report.py" in message


def test_a_reporter_that_cannot_be_built_is_reported_as_unsent(tmp_path: Path) -> None:
    """No stored token is the likeliest failure of all, and it happens where the
    mailer is constructed rather than where it sends."""

    def broken():
        raise RuntimeError("no Gmail token. Run the one-time consent flow first")

    message = send_series_report(broken, result_file(tmp_path, 6), 6, counted=True)
    assert "NOT SENT" in message and "consent flow" in message


def test_switching_reporting_off_says_so_rather_than_sending(tmp_path: Path) -> None:
    """`[email] send_on_series_end = false` is a real choice, and a silent one
    would be indistinguishable from a broken send."""
    mailer = FakeMailer(on_series_end=False)
    message = send_series_report(lambda: mailer, result_file(tmp_path, 6), 6, counted=True)

    assert mailer.sent == []
    assert "NOT SENT" in message and "send_on_series_end" in message


def test_disabled_email_does_not_reach_the_mailer(tmp_path: Path) -> None:
    """`[email] enabled = false` is the development setting, checked separately
    so a disabled peer never constructs a message at all."""
    mailer = FakeMailer(enabled=False)
    send_series_report(lambda: mailer, result_file(tmp_path, 6), 6, counted=True)
    assert mailer.sent == []


def test_the_manual_command_names_the_role_that_ran(tmp_path: Path) -> None:
    """A published repository ships one role, so a command naming the other one
    is a command that cannot run where it is printed."""
    message = send_series_report(lambda: FakeMailer(), result_file(tmp_path, 2), 6, "thief")
    assert "--role thief" in message


def test_an_absent_result_is_held_back_rather_than_crashing(tmp_path: Path) -> None:
    """A series that filed nothing has nothing to send, and must still exit."""
    message = send_series_report(lambda: FakeMailer(), tmp_path / "missing.json", 6)
    assert "held back" in message and "0 of 6" in message


@pytest.mark.parametrize(
    ("played", "mailer"),
    [(6, FakeMailer()), (3, FakeMailer()), (6, FakeMailer(fails="the tunnel went down"))],
    ids=["sent", "held-back", "failed"],
)
def test_every_message_is_ascii(tmp_path: Path, played: int, mailer: FakeMailer) -> None:
    """Printed to a Windows console, which is cp1252: an em dash in one of these
    strings is a `UnicodeEncodeError` at the end of a match instead of a report."""
    message = send_series_report(lambda: mailer, result_file(tmp_path, played), 6, counted=True)
    message.encode("ascii")


# --- the rehearsal guard ----------------------------------------------------


def test_a_rehearsal_files_its_report_but_never_sends_it(tmp_path: Path) -> None:
    """🐛 **A self-match used to mail the lecturer a fake league report.**

    Any six-row result triggered a send, and a 3-3 self-match produces two of
    them — one per team process. Nothing distinguished a rehearsal from a
    counted match.
    """
    mailer = FakeMailer()
    message = send_series_report(lambda: mailer, result_file(tmp_path, 6), 6)

    assert mailer.sent == []
    assert "NOT SENT" in message and "rehearsal" in message


def test_the_rehearsal_message_still_shows_how_to_send_by_hand(tmp_path: Path) -> None:
    """**Which is why the default may be silence.** Forgetting `--counted` on
    match day costs one command; an unsendable fake report costs the grader's
    trust. The asymmetry is what decides the direction of the default."""
    message = send_series_report(lambda: FakeMailer(), result_file(tmp_path, 6), 6, role="thief")
    assert "send_report.py" in message and "--role thief" in message


def test_an_incomplete_rehearsal_is_still_reported_as_held_back(tmp_path: Path) -> None:
    """Completeness is checked first. Calling three of six sub-games a rehearsal
    would hide that the other role process has three left to file (M#35)."""
    message = send_series_report(lambda: FakeMailer(), result_file(tmp_path, 3), 6)
    assert "held back" in message and "3 of 6" in message
