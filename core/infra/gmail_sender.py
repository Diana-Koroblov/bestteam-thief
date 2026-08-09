"""League reporting over the Gmail API (TODO 7.3, M#30-M#35, M#51).

**M#35 is the harshest rule in the book.** If either side fails to report, or
the two reports disagree, the match is void and *both* teams score 0. Winning on
the board is worth nothing if the report does not arrive. That single fact
shapes everything here.

Four consequences, each a requirement rather than a preference:

* **Send-only scope** (M#30). The token this code holds cannot read a mailbox,
  cannot delete, cannot list. If it leaked, the worst it buys an attacker is the
  ability to send mail as us — bad, but not a readable inbox.
* **Attachment, never body text** (M#33, M#34). A free-text report is rejected
  outright. The body carries a human sentence and no report data at all, so a
  grader's parser reads the JSON or fails loudly rather than half-parsing prose.
* **Recipient from config** (M#51). Never a literal, so the test suite cannot
  mail the lecturer and a changed address is a config edit.
* **Everything through the Gatekeeper** (7.15). Automated reporting hands a live
  account to code that might loop. The three gates are what stand between a bug
  and a suspended account, and a direct API call here would walk around them.

**We send our own report and only our own** (M#35, 7.3.4). There is no parameter
for whose result to send and no code path that takes the opponent's: each team
files independently, and a peer that "helpfully" filed for both would produce
the disagreeing pair the rule voids matches over.

The transport is injected. No test contacts the live API (PRD 7 §5), and the
message construction — which is where every one of the rules above is actually
enforced — is a pure function that tests can read byte for byte.
"""

from __future__ import annotations

import base64
from collections.abc import Callable
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Any

__all__ = [
    "GmailSender",
    "GmailError",
    "SEND_SCOPE",
    "build_message",
    "build_transport",
    "BODY_TEXT",
]

# Send-only. Deliberately not `gmail.compose` or `gmail.modify`, both of which
# would also grant read access to the mailbox (M#30).
SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"

# The entire body. It says where to look and carries **no report data** — no
# scores, no game id, no team names. A grader parsing the attachment must never
# find a second, possibly disagreeing, copy in the prose (M#33, M#34).
BODY_TEXT = (
    "Automated league report. The result is attached as JSON.\n"
    "This message body deliberately contains no match data.\n"
)


class GmailError(RuntimeError):
    """The report could not be built or sent."""


def build_message(sender: str, recipient: str, subject: str, attachment: Path) -> dict[str, Any]:
    """Return the Gmail API body for one report, attachment included.

    Pure, so every rule it enforces is checkable without a network: that the
    JSON travels as an attachment, that the body carries no match data, and
    that the recipient is whatever was passed rather than a literal.

    Args:
        attachment: The `result_<game_id>.json` to send. Read as **bytes** and
            attached as `application/json`, not decoded and pasted: decoding
            would put the report through the local console codec, which is
            cp1252 on Diana's machine and would mangle a Hebrew team name.

    Raises:
        GmailError: The attachment is missing. Better here than at the API,
            where the failure would arrive as a stack trace after the match.
    """
    if not attachment.is_file():
        raise GmailError(f"no report to send: {attachment} does not exist")

    message = EmailMessage()
    message["To"] = recipient
    message["From"] = sender
    message["Subject"] = subject
    message.set_content(BODY_TEXT)
    message.add_attachment(
        attachment.read_bytes(),
        maintype="application",
        subtype="json",
        filename=attachment.name,
    )
    # Gmail wants base64url of the whole RFC-822 message.
    return {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")}


def build_transport() -> Callable[[dict[str, Any]], Any]:  # pragma: no cover - real OAuth
    """Return a callable that posts a built message to the Gmail API.

    Everything above this line is testable without a network; this is the part
    that is not, which is why it is one function at the edge rather than logic
    threaded through the sender.

    **No human step at send time** (M#32). The consent flow runs once, by hand,
    and leaves a refresh token at `GMAIL_TOKEN_PATH`; every later send refreshes
    silently. That one-time consent is SETUP 0.2.1, and 0.2.1.d — publishing the
    app — is what stops the refresh token expiring after seven days and breaking
    league reporting mid-project.

    Raises:
        GmailError: No stored token, or the libraries are absent. Named with the
            SETUP step, because the alternative is a Google traceback arriving
            at the moment a report is due.
    """
    from core.shared import env

    token_path = env.optional("GMAIL_TOKEN_PATH")
    if not token_path or not Path(token_path).exists():
        raise GmailError(
            "no Gmail token. Run the one-time consent flow first (docs/SETUP.md 0.2.1) "
            "and set GMAIL_TOKEN_PATH in .env. Reporting is automated only *after* "
            "consent has been given once."
        )

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError as error:
        raise GmailError("Gmail libraries missing: run `uv sync --all-extras --dev`") from error

    credentials = Credentials.from_authorized_user_file(token_path, [SEND_SCOPE])
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    service = build("gmail", "v1", credentials=credentials, cache_discovery=False)

    def send(body: dict[str, Any]) -> Any:
        """Post one message as the authenticated user."""
        return service.users().messages().send(userId="me", body=body).execute()

    return send


@dataclass
class GmailSender:
    """Sends this team's report, through the Gatekeeper, as an attachment.

    Attributes:
        sender: Our address, from `[email] sender`.
        recipient: The lecturer's address, from `[email] recipient` (M#51).
        gatekeeper: The only route out. Every send goes through `execute()`.
        transport: Called with the Gmail API body. Injected so no test reaches
            the live API and so the OAuth client is built only when a real send
            happens.
        enabled: `[email] enabled`. False skips the send and says so, rather
            than failing — a development run must not be a failed run.
        on_series_end: `[email] send_on_series_end`. Whether a finished series
            files its own report without anyone typing a command. Read here
            because here is where `[email]` is read; acted on by
            `core.runtime.reporting`, which is what knows a series has ended.
    """

    sender: str
    recipient: str
    gatekeeper: Any
    transport: Callable[[dict[str, Any]], Any]
    enabled: bool = True
    on_series_end: bool = True

    @classmethod
    def from_config(cls, config: Any, gatekeeper: Any, transport: Callable[..., Any]) -> GmailSender:
        """Build from `[email]`, refusing to guess any address.

        Raises:
            GmailError: Either address is missing. A default recipient would be
                a hardcoded lecturer address by another name (M#51), and a
                default sender would file our report under someone else's name.
        """
        sender = str(config.get("email.sender", "")).strip()
        recipient = str(config.get("email.recipient", "")).strip()
        missing = [
            name for name, value in (("sender", sender), ("recipient", recipient)) if not value
        ]
        if missing:
            raise GmailError(
                f"[email] {' and '.join(missing)} not set in config/<role>/game.toml. "
                "Neither has a default: guessing the recipient would be a hardcoded "
                "address (M#51), and guessing the sender would file our report as "
                "somebody else."
            )
        return cls(
            sender=sender,
            recipient=recipient,
            gatekeeper=gatekeeper,
            transport=transport,
            enabled=bool(config.get("email.enabled", True)),
            on_series_end=bool(config.get("email.send_on_series_end", True)),
        )

    def send_result(self, result_path: Path, subject: str = "") -> Any:
        """Send **our** report and return whatever the transport returned.

        Args:
            result_path: The `result_<game_id>.json` we produced. There is no
                parameter for whose report this is, on purpose: each team files
                its own (M#35, 7.3.4).
            subject: Defaults to the filename, which already carries the shared
                `game_id` — so the grader can pair two teams' mails without
                opening either.
        """
        if not self.enabled:
            return None
        body = build_message(
            self.sender, self.recipient, subject or result_path.stem, result_path
        )
        return self.gatekeeper.execute(self.transport, body, target="gmail.send")
