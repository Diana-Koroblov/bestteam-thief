"""The one-time OAuth consent, which nothing performed (SETUP 0.2.1, M#32).

`gmail_sender.build_transport` refuses to send without a token at
`GMAIL_TOKEN_PATH`, and its error names the consent flow — but no consent flow
existed. `InstalledAppFlow` appeared nowhere in the project, `SETUP.md` stops at
downloading `credentials.json`, and `setup_checks.check_token` reassured anyone
who looked that a missing token is *"normal before the first send; the consent
flow creates it."* Nothing did. This is that step.

**Send-only, and the scope list says so once.** Consent grants exactly what
`SEND_SCOPE` names (M#30). Asking for `gmail.compose` or `gmail.modify` here
would hand this token read access to the whole mailbox, and the grant is what
the user actually approves on the consent screen — a narrower scope in the code
that sends would not take it back.

**The token is a credential and never goes inside a repository.** It carries a
refresh token, which is a durable key to sending mail as us; committed once it
is in the history forever (M#39, M#40). The guard below refuses rather than
warns, because the moment to catch it is before the file is written.
"""

from __future__ import annotations

from pathlib import Path

from core.infra.gmail_sender import SEND_SCOPE, GmailError

__all__ = ["SCOPES", "REPOS", "refuse_unsafe_token_path", "run_consent"]

# Exactly one scope, deliberately. See the module docstring.
SCOPES = [SEND_SCOPE]

# The repository directory names a secret must never land in. Checked by name
# rather than by asking git, so this works from an unpacked copy too.
REPOS = ("bestteam-cop", "bestteam-thief", "p2p-chase")


def refuse_unsafe_token_path(token_path: Path, repo_parent: Path) -> Path:
    """Return *token_path*, or refuse if it would sit inside a repository.

    Args:
        token_path: Where the refresh token is about to be written.
        repo_parent: The directory the repositories live in.

    Raises:
        GmailError: The path resolves inside a repository, or names no file.
            Refused rather than warned: a warning at this point is printed to a
            console that scrolls, and the next `git add -A` in `ship.py` stages
            the token. `scan_secrets.py` looks for API-key shapes and would not
            necessarily catch an OAuth JSON blob.
    """
    # `Path("")` normalises to `Path(".")`, so an unset variable arrives here
    # looking like the working directory rather than like nothing — and the
    # working directory during a setup walkthrough is usually the repository.
    if not str(token_path).strip() or token_path == Path("."):
        raise GmailError("GMAIL_TOKEN_PATH is empty; set it in .env (SETUP 0.2.1.f)")
    resolved = token_path.resolve()
    for repo in REPOS:
        root = (repo_parent / repo).resolve()
        # `==` as well as `in parents`: a directory is not among its own
        # parents, so a path that resolves *to* the repository root would
        # otherwise pass the check it most obviously fails.
        if resolved == root or root in resolved.parents:
            raise GmailError(
                f"GMAIL_TOKEN_PATH points inside {repo}. The token holds a refresh "
                "token — a durable key to sending mail as you — and a secret committed "
                "once lives in the git history forever (M#39, M#40). Put it somewhere "
                r"like C:\Users\<you>\.p2p-secrets\token.json."
            )
    return token_path


def run_consent(  # pragma: no cover - opens a browser and talks to Google
    credentials_path: Path, token_path: Path, port: int = 0
) -> Path:
    """Run the browser consent flow once and save the token. Returns its path.

    Args:
        port: Loopback port for the redirect. 0 lets the OS choose a free one,
            which matters because a Desktop-app client accepts any loopback
            port and a fixed one collides with whatever else is running.

    Raises:
        GmailError: The libraries are missing or `credentials.json` is absent.
            Both name the SETUP step, because the person reading this is part
            way through a console walkthrough and needs the line number, not a
            Google traceback.

    The token is written with `Path.write_text` rather than handed to the
    library's own writer so the parent directory is created first: the
    documented location is a folder outside the repository that may not exist
    yet, and a flow that completes and then fails to save makes the user do the
    browser dance twice.
    """
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as error:
        raise GmailError(
            "Gmail libraries missing: run `uv sync --all-extras --dev`"
        ) from error

    if not credentials_path.exists():
        raise GmailError(
            f"no credentials at {credentials_path}. Download the Desktop-app client "
            "JSON and set GMAIL_CREDENTIALS_PATH (SETUP 0.2.1.e-f)."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    credentials = flow.run_local_server(port=port, prompt="consent")
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(credentials.to_json(), encoding="utf-8")
    return token_path
