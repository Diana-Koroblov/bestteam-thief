"""League reporting (TODO 7.3, T7.7, T7.8, M#30-M#35, M#51).

**No test contacts the live Gmail API** (PRD 7 §5). It does not need to: every
rule this module exists to enforce lives in the message it builds, and that is a
pure function whose output a test can decode byte for byte.

M#35 is why this matters more than its size suggests. If either side fails to
report, or the two reports disagree, the match is void and *both* teams score 0.
"""

from __future__ import annotations

import base64
import email
import json
from pathlib import Path

import pytest

from core.infra.gmail_sender import (
    BODY_TEXT,
    SEND_SCOPE,
    GmailError,
    GmailSender,
    build_message,
)
from core.shared.gatekeeper import Gatekeeper
from core.shared.rate_limits import RateLimits

LECTURER = "rmisegal+uoh26finalgame@gmail.com"
US = "bestteam@example.com"
REPORT = {"game_id": "2026-08-12_a-vs-b_abc", "totals": {"ours": 30, "theirs": 10}}


class StubConfig:
    """Answers the `[email]` keys and nothing else."""

    def __init__(self, **values: object) -> None:
        self.values = values

    def get(self, path: str, default: object = None) -> object:
        return self.values.get(path.replace(".", "_"), default)


def report_file(directory: Path) -> Path:
    """Write a result artefact and return its path."""
    target = directory / "result_2026-08-12_a-vs-b_abc.json"
    target.write_bytes(json.dumps(REPORT, ensure_ascii=False).encode("utf-8"))
    return target


def decoded(body: dict) -> email.message.Message:
    """Return the RFC-822 message Gmail would receive."""
    return email.message_from_bytes(base64.urlsafe_b64decode(body["raw"]))


def gatekeeper() -> Gatekeeper:
    """A real Gatekeeper on the shipped budget, with a clock that never sleeps."""
    limits = RateLimits(
        requests_per_minute=30,
        burst_capacity=5,
        concurrent_requests=2,
        retry_backoff_sec=5,
        max_retries=3,
        queue_depth=100,
        daily_send_quota=50,
        dos_window_sec=10,
        dos_max_calls_in_window=20,
    )
    return Gatekeeper(limits=limits, sleep=lambda _: None)


def build(directory: Path, **overrides):
    """Return `(sender, sent)` where *sent* collects the transport's payloads."""
    sent: list[dict] = []
    values = {"email_sender": US, "email_recipient": LECTURER, "email_enabled": True}
    sender = GmailSender.from_config(StubConfig(**{**values, **overrides}), gatekeeper(), sent.append)
    return sender, sent, report_file(directory)


# --- 7.3.2 attachment only --------------------------------------------------


def test_the_report_travels_as_a_json_attachment(tmp_path: Path) -> None:
    """**T7.7, M#34.** A free-text report is rejected outright."""
    sender, sent, path = build(tmp_path)
    sender.send_result(path)

    parts = list(decoded(sent[0]).walk())
    attachments = [p for p in parts if p.get_filename()]
    assert len(attachments) == 1
    assert attachments[0].get_filename() == path.name
    assert attachments[0].get_content_type() == "application/json"
    assert json.loads(attachments[0].get_payload(decode=True).decode("utf-8")) == REPORT


def test_the_body_carries_no_report_data(tmp_path: Path) -> None:
    """**M#33.** A grader parsing the attachment must not find a second, possibly
    disagreeing, copy in the prose."""
    sender, sent, path = build(tmp_path)
    sender.send_result(path)

    body = next(p for p in decoded(sent[0]).walk() if p.get_content_type() == "text/plain")
    text = body.get_payload(decode=True).decode("utf-8")
    assert text.strip() == BODY_TEXT.strip()
    for leaked in ("game_id", "totals", "2026-08-12_a-vs-b_abc", "30"):
        assert leaked not in text


def test_a_non_ascii_report_survives_the_attachment(tmp_path: Path) -> None:
    """Read as bytes, never decoded through the local console codec.

    Decoding would put the report through cp1252 on Diana's machine and mangle
    a Hebrew team name on the way to the grader.
    """
    path = tmp_path / "result.json"
    path.write_bytes(json.dumps({"team": "Ωμέγα"}, ensure_ascii=False).encode("utf-8"))
    body = build_message(US, LECTURER, "subject", path)

    attachment = next(p for p in decoded(body).walk() if p.get_filename())
    assert json.loads(attachment.get_payload(decode=True).decode("utf-8"))["team"] == "Ωμέγα"


# --- 7.3.3 recipient from config --------------------------------------------


def test_the_recipient_comes_from_config(tmp_path: Path) -> None:
    """**T7.8, M#51.** Not a literal, so the suite cannot mail the lecturer."""
    sender, sent, path = build(tmp_path, email_recipient="somebody.else@example.com")
    sender.send_result(path)
    assert decoded(sent[0])["To"] == "somebody.else@example.com"


def test_no_address_is_ever_guessed(tmp_path: Path) -> None:
    """A default recipient is a hardcoded lecturer address by another name."""
    for missing in ("email_sender", "email_recipient"):
        values = {"email_sender": US, "email_recipient": LECTURER}
        values[missing] = ""
        with pytest.raises(GmailError, match="not set"):
            GmailSender.from_config(StubConfig(**values), gatekeeper(), lambda _: None)


def test_the_lecturer_address_is_not_written_into_the_source() -> None:
    """The one address that must never be a literal, checked literally."""
    source = Path(__file__).resolve().parents[2] / "core" / "infra" / "gmail_sender.py"
    assert "rmisegal" not in source.read_text(encoding="utf-8")


# --- 7.3.1 through the Gatekeeper -------------------------------------------


def test_every_send_goes_through_the_gates(tmp_path: Path) -> None:
    """**7.15.** Automated reporting hands a live account to code that may loop.

    A direct API call here would walk around the three gates that stand between
    a bug and a suspended account.
    """
    sender, sent, path = build(tmp_path)
    sender.send_result(path)

    assert len(sent) == 1
    assert sender.gatekeeper.logger.records[-1].target == "gmail.send"
    assert sender.gatekeeper.status().quota_remaining == 49


def test_a_locked_pipe_stops_the_send(tmp_path: Path) -> None:
    """The gates are load-bearing, not decorative: if the detector has locked,
    nothing reaches the transport."""
    from core.shared.gatekeeper import GatekeeperLockedError

    sender, sent, path = build(tmp_path)
    sender.gatekeeper.detector.locked = True
    sender.gatekeeper.detector.reason = "locked in a prior loop"
    with pytest.raises(GatekeeperLockedError):
        sender.send_result(path)
    assert sent == []


def test_the_scope_is_send_only() -> None:
    """**M#30.** `gmail.compose` and `gmail.modify` would also grant read access,
    so a leaked token would expose the mailbox rather than only the ability to
    send as us."""
    assert SEND_SCOPE.endswith("/auth/gmail.send")
    assert "modify" not in SEND_SCOPE and "compose" not in SEND_SCOPE


# --- 7.3.4 our own report only ----------------------------------------------


def test_there_is_no_way_to_send_on_the_opponents_behalf(tmp_path: Path) -> None:
    """**M#35.** Each team files independently.

    Checked structurally rather than by intent: `send_result` takes a path and a
    subject, and no parameter anywhere names whose report it is. A peer that
    "helpfully" filed for both would produce the disagreeing pair the rule voids
    matches over.
    """
    import inspect

    parameters = set(inspect.signature(GmailSender.send_result).parameters)
    assert parameters == {"self", "result_path", "subject"}
    assert "sender" not in parameters, "the From address is ours, never a caller's choice"


def test_a_missing_report_fails_before_the_api(tmp_path: Path) -> None:
    """Better here than as a stack trace from the API after the match."""
    sender, _, _ = build(tmp_path)
    with pytest.raises(GmailError, match="does not exist"):
        sender.send_result(tmp_path / "never_written.json")


def test_disabled_email_skips_rather_than_fails(tmp_path: Path) -> None:
    """A development run must not be a failed run."""
    sender, sent, path = build(tmp_path, email_enabled=False)
    assert sender.send_result(path) is None
    assert sent == []


# --- the SDK wiring ---------------------------------------------------------


@pytest.mark.parametrize("role", ["police", "thief"])
def test_the_sdk_builds_a_mailer_from_the_shipped_config(role: str, tmp_path: Path) -> None:
    """The path a real series-end report will take, on the real config.

    The transport is injected so no OAuth token is needed: everything up to the
    network is exercised, and the network is the one part a test must not touch.
    """
    from core.protocol.schemas import Role
    from core.sdk.peer_sdk import PeerSDK
    from tests.paths import PRESENT_ROLES, role_dir

    if role not in PRESENT_ROLES:
        pytest.skip(f"{role} is not published to this repository (ADR-001)")

    sent: list[dict] = []
    sdk = PeerSDK(role_dir(role), Role.COP if role == "police" else Role.THIEF)
    mailer = sdk.mailer(transport=sent.append)

    assert mailer.recipient == LECTURER, "the shipped config must point at the lecturer (M#51)"
    mailer.send_result(report_file(tmp_path))
    assert decoded(sent[0])["To"] == LECTURER


def test_the_mailer_shares_the_peers_one_gatekeeper() -> None:
    """**One instance per process.** A mailer with its own Gatekeeper would
    start with a full bucket and an empty DOS window, which is the loop the
    detector exists to catch, made undetectable."""
    from core.protocol.schemas import Role
    from core.sdk.peer_sdk import PeerSDK
    from tests.paths import PRESENT_ROLES, role_dir

    # Whichever role this repository ships — hardcoding COP loaded the police
    # brain in the thief repo, which is the split-repository failure ADR-001
    # exists to prevent (caught by `scripts/check_split_repos.py`).
    role = PRESENT_ROLES[0]
    sdk = PeerSDK(role_dir(role), Role.COP if role == "police" else Role.THIEF)
    assert sdk.mailer(transport=lambda _: None).gatekeeper is sdk.gatekeeper
