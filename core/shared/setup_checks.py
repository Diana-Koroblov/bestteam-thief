"""Verify the external-service setup described in docs/SETUP.md.

Each check returns a :class:`CheckResult` rather than raising, so one missing
service does not hide the state of the others — the point is a single readable
summary of what is and is not ready.

`FAIL` blocks progress. `WARN` is something that will bite later but not today,
such as Ollama being offline on a machine that only ever runs the template
provider.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from core.shared.env import redact

__all__ = ["Status", "CheckResult", "check_env_file", "check_groq_key", "check_credentials",
           "check_ollama", "check_ngrok", "run_all"]

OK = "OK"
WARN = "WARN"
FAIL = "FAIL"
Status = str


@dataclass(frozen=True)
class CheckResult:
    """Outcome of one setup check.

    Attributes:
        name: What was checked.
        status: ``OK``, ``WARN`` or ``FAIL``.
        detail: What was found.
        fix: Which step of docs/SETUP.md resolves it.
    """

    name: str
    status: Status
    detail: str
    fix: str = ""


def check_env_file(root: Path) -> CheckResult:
    """The .env file must exist and must never be committed."""
    env = root / ".env"
    if not env.exists():
        return CheckResult(".env file", FAIL, "not found",
                           "Copy .env-example to .env and fill it in.")
    return CheckResult(".env file", OK, str(env))


def check_groq_key(value: str | None) -> CheckResult:
    """The Groq key must be present and shaped like a real key."""
    if not value:
        return CheckResult("Groq API key", WARN, "GROQ_API_KEY not set",
                           "SETUP 0.2.2 - only needed on the machine that uses the groq provider.")
    if not value.startswith("gsk_") or len(value) < 24:
        return CheckResult("Groq API key", FAIL, "does not look like a Groq key",
                           "SETUP 0.2.2 - a real key starts with 'gsk_'.")
    return CheckResult("Groq API key", OK, redact(value, keep=8))


def check_credentials(path_value: str | None, repo_parent: Path) -> CheckResult:
    """Gmail credentials must exist, be a Desktop client, and sit outside the repos."""
    if not path_value:
        return CheckResult("Gmail credentials", FAIL, "GMAIL_CREDENTIALS_PATH not set",
                           "SETUP 0.2.1.f")
    path = Path(path_value)
    if not path.exists():
        return CheckResult("Gmail credentials", FAIL, f"no file at {path}", "SETUP 0.2.1.e-f")

    resolved = path.resolve()
    for repo in ("bestteam-cop", "bestteam-thief", "p2p-chase"):
        if (repo_parent / repo).resolve() in resolved.parents:
            return CheckResult(
                "Gmail credentials", FAIL, f"stored INSIDE {repo}",
                "SETUP 0.2.1.f - move it outside every repository. (M#39)")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return CheckResult("Gmail credentials", FAIL, "not valid JSON", "SETUP 0.2.1.e")

    if "installed" not in data:
        return CheckResult("Gmail credentials", FAIL, "not a Desktop app client",
                           "SETUP 0.2.1.e - application type must be 'Desktop app'.")
    return CheckResult("Gmail credentials", OK, f"Desktop client at {path}")


def check_token(path_value: str | None) -> CheckResult:
    """A saved token means the consent flow has been completed at least once."""
    if not path_value:
        return CheckResult("Gmail token", WARN, "GMAIL_TOKEN_PATH not set", "SETUP 0.2.1.f")
    if not Path(path_value).exists():
        return CheckResult("Gmail token", WARN, "no token yet",
                           "Normal before the first send; the consent flow creates it.")
    return CheckResult("Gmail token", OK, str(path_value))


def check_ollama(base_url: str | None) -> CheckResult:
    """Ollama is optional per machine but required on the one hosting graded matches."""
    url = base_url or "http://localhost:11434"
    try:
        import httpx

        response = httpx.get(f"{url}/api/tags", timeout=3.0)
        models = [m["name"] for m in response.json().get("models", [])]
    except Exception:  # noqa: BLE001 - any failure means "not reachable"
        return CheckResult("Ollama", WARN, f"not reachable at {url}",
                           "SETUP 0.2.3 - required on the machine hosting graded matches.")
    if not models:
        return CheckResult("Ollama", WARN, "running but no models pulled",
                           "SETUP 0.2.3 - run: ollama pull llama3.2:3b")
    return CheckResult("Ollama", OK, ", ".join(models))


def check_ngrok(authtoken: str | None) -> CheckResult:
    """The tunnel binary and its authtoken are both needed from Phase 5 on."""
    if shutil.which("ngrok") is None:
        return CheckResult("ngrok", FAIL, "binary not on PATH",
                           "SETUP 0.2.4 - winget install ngrok.ngrok")
    if not authtoken:
        return CheckResult("ngrok", WARN, "installed, NGROK_AUTHTOKEN not in .env",
                           "SETUP 0.2.4 - needed to start the tunnel programmatically.")
    return CheckResult("ngrok", OK, "installed and configured")


def run_all(root: Path) -> list[CheckResult]:
    """Run every check and return the results in report order."""
    return [
        check_env_file(root),
        check_credentials(os.getenv("GMAIL_CREDENTIALS_PATH"), root.parent),
        check_token(os.getenv("GMAIL_TOKEN_PATH")),
        check_groq_key(os.getenv("GROQ_API_KEY")),
        check_ollama(os.getenv("OLLAMA_BASE_URL")),
        check_ngrok(os.getenv("NGROK_AUTHTOKEN")),
    ]
