"""Single entry point for environment configuration.

Every module that needs a credential goes through here. Nothing reads
``os.environ`` directly, and nothing calls ``load_dotenv`` on its own.

**Why this exists.** If modules read ambient environment variables, the system
works wherever the shell happens to have them set and fails silently everywhere
else — a different terminal, the other team member's machine, CI. That failure
would surface during a league match, and an unsent report scores 0 for *both*
teams (M#35). Loading the file explicitly, in one place, makes behaviour
identical everywhere.

This is also why we decline VS Code's ``python.terminal.useEnvFile`` prompt:
terminal injection would mask exactly this class of bug during development.

Values are never logged. Use :func:`redact` when a variable must appear in
diagnostic output.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["EnvError", "load_env", "require", "optional", "role_scoped", "redact", "is_loaded"]

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_loaded = False


class EnvError(RuntimeError):
    """A required environment variable is missing or empty."""


def load_env(root: Path | None = None, *, force: bool = False) -> bool:
    """Load ``.env`` from *root* exactly once.

    Idempotent: repeated calls are cheap no-ops, so any module may call it at
    import time without worrying about ordering.

    Args:
        root: Directory containing ``.env``. Defaults to the project root.
        force: Reload even if already loaded. Used by tests.

    Returns:
        True if a ``.env`` file was found and read.
    """
    global _loaded
    if _loaded and not force:
        return True

    env_path = (root or _PROJECT_ROOT) / ".env"
    if not env_path.exists():
        return False

    try:
        from dotenv import load_dotenv
    except ImportError as error:  # pragma: no cover - dependency is declared
        raise EnvError(
            "python-dotenv is not installed. Run: uv sync --all-extras --dev"
        ) from error

    load_dotenv(env_path, override=force)
    _loaded = True
    return True


def is_loaded() -> bool:
    """Return True once :func:`load_env` has successfully read a file."""
    return _loaded


def require(name: str, setup_step: str = "") -> str:
    """Return the value of *name*, or raise with an actionable message.

    Args:
        name: Environment variable name.
        setup_step: Section of ``docs/SETUP.md`` that configures it.

    Raises:
        EnvError: The variable is missing or empty.
    """
    load_env()
    value = os.environ.get(name, "").strip()
    if not value:
        hint = f" See docs/SETUP.md {setup_step}." if setup_step else ""
        raise EnvError(
            f"{name} is not set. Copy .env-example to .env and fill it in.{hint}"
        )
    return value


def optional(name: str, default: str | None = None) -> str | None:
    """Return the value of *name*, or *default* when it is unset or empty."""
    load_env()
    value = os.environ.get(name, "").strip()
    return value or default


def role_scoped(name: str, role: str) -> str | None:
    """Return ``{name}_{ROLE}`` if set, else the plain *name* (or None).

    Lets our cop and thief processes, sharing one ``.env`` from one working
    tree (docs/MATCHDAY.md), each get their own tunnel domain and authtoken —
    a single-role setup that only ever sets the plain name keeps working
    unchanged, since the suffixed lookup simply never finds anything.
    """
    return optional(f"{name}_{role.upper()}") or optional(name)


def redact(value: str | None, keep: int = 4) -> str:
    """Return a safely printable form of a secret.

    Shows the first *keep* characters and the length, never the whole value —
    enough to confirm the right key is loaded, useless to anyone reading a log.
    """
    if not value:
        return "<unset>"
    if len(value) <= keep:
        return "*" * len(value)
    return f"{value[:keep]}...({len(value)} chars)"
