"""Run the one-time Gmail consent, and optionally prove the send path works.

    uv run python scripts/gmail_consent.py
    uv run python scripts/gmail_consent.py --test-to you@gmail.com

The first form opens a browser once and saves a refresh token; every later send
is silent (M#32). The second sends one real message through the **whole** live
path — Gatekeeper, message builder, Gmail API — so the first time that code
carries a real report is not the first time it runs.

`--test-to` takes an address and has no default, deliberately. The configured
recipient is the lecturer (M#51), and a self-test that defaults to the real
recipient is a self-test that mails him a fake report the first time somebody
runs it to see what it does.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.infra.gmail_auth import refuse_unsafe_token_path, run_consent  # noqa: E402
from core.infra.gmail_sender import GmailError, GmailSender, build_transport  # noqa: E402
from core.shared.config_manager import load_config  # noqa: E402
from core.shared.env import load_env, optional  # noqa: E402


def _paths() -> tuple[Path, Path]:
    """Return (credentials, token) from .env, refusing an unsafe token location."""
    credentials = optional("GMAIL_CREDENTIALS_PATH")
    token = optional("GMAIL_TOKEN_PATH")
    if not credentials:
        raise GmailError("GMAIL_CREDENTIALS_PATH not set in .env (SETUP 0.2.1.f)")
    if not token:
        raise GmailError("GMAIL_TOKEN_PATH not set in .env (SETUP 0.2.1.f)")
    return Path(credentials), refuse_unsafe_token_path(Path(token), ROOT.parent)


def consent(force: bool) -> Path:
    """Ensure a token exists, running the browser flow if needed."""
    credentials, token = _paths()
    if token.exists() and not force:
        print(f"[ OK ]  token already present at {token}")
        print("        re-run with --force to replace it (a revoked grant needs this)")
        return token
    print(f"[ .. ]  opening the consent screen; approve for {credentials.name}")
    print("        an 'unverified app' warning is expected -> Advanced -> Go to ... (unsafe)")
    saved = run_consent(credentials, token)
    print(f"[ OK ]  token saved to {saved}")
    return saved


def send_test(address: str, role: str) -> None:
    """Send one real message to *address*, through the live path.

    The attachment is a throwaway JSON written beside the token rather than a
    real `result_<game_id>.json`, so a rehearsal can never put a file into the
    league record that looks like a match report.
    """
    from core.shared.gatekeeper import Gatekeeper  # local: only a real send needs it
    from core.shared.rate_limits import load_rate_limits

    role_dir = ROOT / "config" / role
    config = load_config(role_dir)
    _, token = _paths()
    probe = token.parent / "gmail_selftest.json"
    probe.write_text(
        json.dumps({"self_test": True, "note": "not a match report"}, indent=2), encoding="utf-8"
    )

    sender = GmailSender.from_config(
        config,
        gatekeeper=Gatekeeper(limits=load_rate_limits(role_dir)),
        transport=build_transport(),
    )
    sender.recipient = address  # never the configured lecturer address (M#51)
    sender.send_result(probe, subject="p2p-chase Gmail self-test")
    print(f"[ OK ]  test message sent to {address}; check the inbox and the Sent folder")


def main(argv: list[str] | None = None) -> int:
    """Run consent, then the optional self-test. Returns a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Replace an existing token.")
    parser.add_argument(
        "--test-to", metavar="ADDRESS", help="Send one real test message to this address."
    )
    parser.add_argument(
        "--role", default="police", choices=["police", "thief"], help="Which config to read."
    )
    args = parser.parse_args(argv)

    load_env(ROOT)
    try:
        consent(args.force)
        if args.test_to:
            send_test(args.test_to, args.role)
    except GmailError as error:
        print(f"[FAIL]  {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
