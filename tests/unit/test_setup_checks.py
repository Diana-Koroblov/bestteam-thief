"""Unit tests for the setup verification checks.

The credentials check carries the most weight: storing `credentials.json` inside
a repository is a project-failing mistake (M#39), so that path is tested
explicitly rather than trusted.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.shared.setup_checks import (
    FAIL,
    OK,
    WARN,
    check_credentials,
    check_env_file,
    check_groq_key,
    check_ngrok,
    check_token,
)

_DESKTOP_CLIENT = {"installed": {"client_id": "x.apps.googleusercontent.com"}}


def _write_credentials(path: Path, payload: dict) -> Path:
    """Write a credentials JSON file and return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_env_file_missing_fails(tmp_path: Path) -> None:
    """No .env means nothing else can be configured."""
    assert check_env_file(tmp_path).status == FAIL


def test_env_file_present_passes(tmp_path: Path) -> None:
    """The happy path."""
    (tmp_path / ".env").write_text("X=1\n", encoding="utf-8")
    assert check_env_file(tmp_path).status == OK


@pytest.mark.parametrize("value", ["", None])
def test_missing_groq_key_warns_rather_than_fails(value: str | None) -> None:
    """Itay's machine uses Ollama and legitimately has no Groq key."""
    assert check_groq_key(value).status == WARN


def test_malformed_groq_key_fails() -> None:
    """A key that is present but wrong is worse than one that is absent."""
    assert check_groq_key("not-a-real-key").status == FAIL


def test_valid_groq_key_passes_and_is_not_echoed_in_full() -> None:
    """The report must not print the whole secret to the terminal."""
    key = "gsk_" + "a1B2c3D4e5F6g7H8i9J0" * 2
    result = check_groq_key(key)
    assert result.status == OK
    assert key not in result.detail


def test_credentials_inside_a_repository_fails(tmp_path: Path) -> None:
    """Storing the file in a repo risks committing it permanently. (M#39)"""
    repo_parent = tmp_path
    path = _write_credentials(repo_parent / "bestteam-cop" / "credentials.json", _DESKTOP_CLIENT)
    result = check_credentials(str(path), repo_parent)
    assert result.status == FAIL
    assert "INSIDE" in result.detail


def test_credentials_outside_every_repository_passes(tmp_path: Path) -> None:
    """The recommended location is a sibling secrets folder."""
    path = _write_credentials(tmp_path / ".p2p-secrets" / "credentials.json", _DESKTOP_CLIENT)
    assert check_credentials(str(path), tmp_path).status == OK


def test_credentials_of_the_wrong_client_type_fails(tmp_path: Path) -> None:
    """A Web client has no 'installed' key and will not drive the desktop flow."""
    path = _write_credentials(tmp_path / "credentials.json", {"web": {"client_id": "x"}})
    result = check_credentials(str(path), tmp_path)
    assert result.status == FAIL
    assert "Desktop" in result.fix


def test_credentials_not_json_fails(tmp_path: Path) -> None:
    """A truncated download is caught rather than crashing the report."""
    path = tmp_path / "credentials.json"
    path.write_text("{ broken", encoding="utf-8")
    assert check_credentials(str(path), tmp_path).status == FAIL


def test_credentials_path_unset_fails(tmp_path: Path) -> None:
    """Gmail reporting is mandatory, so an unset path is a failure. (M#32)"""
    assert check_credentials(None, tmp_path).status == FAIL


def test_missing_token_only_warns(tmp_path: Path) -> None:
    """No token before the first consent flow is expected, not broken."""
    assert check_token(str(tmp_path / "token.json")).status == WARN


def test_existing_token_passes(tmp_path: Path) -> None:
    """A saved token means consent has been granted at least once."""
    token = tmp_path / "token.json"
    token.write_text("{}", encoding="utf-8")
    assert check_token(str(token)).status == OK


def test_ngrok_missing_binary_fails(monkeypatch) -> None:
    """Public exposure is mandatory for league play. (M#10)"""
    monkeypatch.setattr("core.shared.setup_checks.shutil.which", lambda _: None)
    assert check_ngrok("token").status == FAIL


def test_ngrok_without_authtoken_warns(monkeypatch) -> None:
    """Installed but unconfigured is workable by hand, so warn rather than fail."""
    monkeypatch.setattr("core.shared.setup_checks.shutil.which", lambda _: "/usr/bin/ngrok")
    assert check_ngrok(None).status == WARN


def test_ngrok_fully_configured_passes(monkeypatch) -> None:
    """The happy path."""
    monkeypatch.setattr("core.shared.setup_checks.shutil.which", lambda _: "/usr/bin/ngrok")
    assert check_ngrok("token").status == OK
