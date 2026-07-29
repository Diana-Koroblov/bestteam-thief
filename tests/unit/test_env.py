"""Unit tests for the environment loader.

The important guarantees: a missing variable produces an actionable error rather
than a confusing `None` deep in a call stack, and secrets never appear in full
in any diagnostic string.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.shared import env as env_module
from core.shared.env import EnvError, load_env, optional, redact, require


@pytest.fixture(autouse=True)
def _reset_loader(monkeypatch):
    """Each test starts with a clean loader and a clean environment."""
    monkeypatch.setattr(env_module, "_loaded", False)
    monkeypatch.delenv("P2P_TEST_KEY", raising=False)


def test_load_env_reports_false_when_no_file(tmp_path: Path) -> None:
    """A missing .env is not an error here - the checks report it instead."""
    assert load_env(tmp_path) is False


def test_load_env_reads_the_file(tmp_path: Path, monkeypatch) -> None:
    """Values in .env become available through the accessors."""
    (tmp_path / ".env").write_text("P2P_TEST_KEY=hello\n", encoding="utf-8")
    assert load_env(tmp_path, force=True) is True
    assert optional("P2P_TEST_KEY") == "hello"


def test_load_env_is_idempotent(tmp_path: Path) -> None:
    """Repeated calls are safe, so modules may call it at import time."""
    (tmp_path / ".env").write_text("P2P_TEST_KEY=1\n", encoding="utf-8")
    assert load_env(tmp_path, force=True) is True
    assert load_env(tmp_path) is True


def test_require_returns_the_value(monkeypatch) -> None:
    """The happy path."""
    monkeypatch.setenv("P2P_TEST_KEY", "value")
    assert require("P2P_TEST_KEY") == "value"


def test_require_raises_on_missing_variable() -> None:
    """A missing credential fails loudly, not as a None three frames later."""
    with pytest.raises(EnvError) as excinfo:
        require("P2P_TEST_KEY")
    assert "P2P_TEST_KEY" in str(excinfo.value)
    assert ".env" in str(excinfo.value)


def test_require_raises_on_empty_variable(monkeypatch) -> None:
    """An empty value is as useless as an absent one."""
    monkeypatch.setenv("P2P_TEST_KEY", "   ")
    with pytest.raises(EnvError):
        require("P2P_TEST_KEY")


def test_require_names_the_setup_step() -> None:
    """The error points at the documentation section that fixes it."""
    with pytest.raises(EnvError) as excinfo:
        require("P2P_TEST_KEY", setup_step="0.2.2")
    assert "0.2.2" in str(excinfo.value)


def test_require_strips_surrounding_whitespace(monkeypatch) -> None:
    """A trailing newline pasted from a console must not corrupt a key."""
    monkeypatch.setenv("P2P_TEST_KEY", "  gsk_abc  ")
    assert require("P2P_TEST_KEY") == "gsk_abc"


def test_optional_returns_the_default_when_unset() -> None:
    """Optional settings have sensible fallbacks."""
    assert optional("P2P_TEST_KEY", "fallback") == "fallback"


def test_optional_returns_none_by_default() -> None:
    """No default means None, not an empty string."""
    assert optional("P2P_TEST_KEY") is None


def test_redact_hides_all_but_a_short_prefix() -> None:
    """Enough to confirm the right key is loaded, useless to a log reader."""
    secret = "gsk_" + "a1B2c3D4e5F6g7H8i9J0" * 2
    shown = redact(secret)
    assert shown.startswith("gsk_")
    assert secret not in shown
    assert str(len(secret)) in shown


def test_redact_handles_unset_values() -> None:
    """Diagnostics must not crash on a missing variable."""
    assert redact(None) == "<unset>"
    assert redact("") == "<unset>"


def test_redact_fully_masks_a_short_value() -> None:
    """A value shorter than the prefix reveals nothing at all."""
    assert redact("abc") == "***"
