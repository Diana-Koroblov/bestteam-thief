"""Unit tests for the secret scanner.

Every pattern must fire on a realistic key and stay silent on prose that merely
mentions secrets — a scanner that cries wolf gets disabled, which is worse than
having none.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from core.shared.secret_scanner import (
    SECRET_PATTERNS,
    scan_history,
    scan_staged,
    scan_text,
    scan_tracked,
)


def _git_repo(path: Path) -> None:
    """Initialise a throwaway repository with an identity, so commits succeed."""
    path.mkdir(parents=True, exist_ok=True)
    for args in (
        ["init", "-q", "-b", "main"],
        ["config", "user.email", "test@example.com"],
        ["config", "user.name", "Test"],
    ):
        subprocess.run(["git", *args], cwd=path, check=True, capture_output=True)


def _commit(path: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", message], cwd=path, check=True, capture_output=True)

REALISTIC = {
    "Groq API key": "GROQ_API_KEY = 'gsk_" + "a1B2c3D4e5F6g7H8i9J0" * 2 + "'",
    "Anthropic API key": "key = 'sk-ant-api03-" + "aB3dE6gH9jK2mN5pQ8sT1vW4" + "'",
    "OpenAI API key": "key = 'sk-" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6" + "'",
    "Google API key": "key = 'AIza" + "SyA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6" + "'",
    "Private key block": "-----BEGIN RSA PRIVATE KEY-----",
    "Google OAuth client secret": "secret = 'GOCSPX-" + "aB3dE6gH9jK2mN5pQ8sT" + "'",
}


@pytest.mark.parametrize("label", [label for label, _ in SECRET_PATTERNS])
def test_every_pattern_detects_a_realistic_key(label: str) -> None:
    """Each configured pattern fires on a plausible example of its key type."""
    findings = scan_text(REALISTIC[label])
    assert label in {finding.label for finding in findings}


@pytest.mark.parametrize(
    "prose",
    [
        "Zero matches for `gsk_`, `sk-ant`, `BEGIN PRIVATE KEY` in tracked files.",
        "Never commit a private key.",
        "The consent screen produces a client secret; keep it in .env.",
        "GROQ_API_KEY=gsk_replace_me",
        "ANTHROPIC_API_KEY=sk-ant-replace-me-optional",
    ],
)
def test_prose_and_placeholders_do_not_trigger(prose: str) -> None:
    """Documentation about secrets, and .env-example placeholders, are not secrets."""
    assert scan_text(prose) == []


def test_finding_reports_label_location_and_line() -> None:
    """A finding carries enough context to locate and fix the leak."""
    finding = scan_text(REALISTIC["Groq API key"], "config/game.toml")[0]
    assert finding.label == "Groq API key"
    assert finding.location == "config/game.toml:1"
    assert "gsk_" in str(finding)


def test_clean_text_yields_nothing() -> None:
    """The happy path returns an empty list."""
    assert scan_text("x = 1\ny = 2\n") == []


def test_scan_tracked_outside_a_git_repo_is_quiet(tmp_path: Path) -> None:
    """A non-repository yields no findings rather than an exception."""
    assert scan_tracked(tmp_path) == []


def test_scan_staged_outside_a_git_repo_is_quiet(tmp_path: Path) -> None:
    """Same tolerance for the staged-changes path."""
    assert scan_staged(tmp_path) == []


def test_multiple_secrets_on_separate_lines_are_all_reported() -> None:
    """The scan does not stop at the first hit."""
    text = REALISTIC["Groq API key"] + "\n" + REALISTIC["Private key block"]
    assert len(scan_text(text)) == 2


def test_scan_history_outside_a_git_repo_is_quiet(tmp_path: Path) -> None:
    assert scan_history(tmp_path) == []


def test_a_deleted_secret_survives_in_the_history(tmp_path: Path) -> None:
    """The reason 0.QG.3 demands a history scan and not just a tracked scan.

    Committing a key and deleting it in the next commit leaves the working tree
    clean. The key is still readable by anyone who clones the repository, so the
    tracked scan passing means nothing. (M#39, M#40)
    """
    repo = tmp_path / "repo"
    _git_repo(repo)
    leak = repo / "settings.py"
    leak.write_text(f'API_KEY = "{REALISTIC["Groq API key"]}"\n', encoding="utf-8")
    _commit(repo, "oops")
    leak.unlink()
    _commit(repo, "remove the key")

    assert scan_tracked(repo) == []  # the checkout looks innocent
    findings = scan_history(repo)
    assert len(findings) == 1
    assert findings[0].label == "Groq API key"
    assert "settings.py" in findings[0].location


def test_history_scan_ignores_the_scanners_own_fixtures(tmp_path: Path) -> None:
    """Otherwise every repository reports itself and the gate is useless."""
    repo = tmp_path / "repo"
    _git_repo(repo)
    exempt = repo / "tests" / "unit"
    exempt.mkdir(parents=True)
    (exempt / "test_secret_scanner.py").write_text(
        f'SAMPLE = "{REALISTIC["Groq API key"]}"\n', encoding="utf-8"
    )
    _commit(repo, "the scanner's own fixtures")

    assert scan_history(repo) == []


def test_a_real_key_in_env_example_is_still_reported(tmp_path: Path) -> None:
    """`.env-example` is deliberately not exempt.

    It is the likeliest place for someone to paste a real key "just to test".
    Its own placeholders are too short to match, so nothing is lost by scanning
    it and a whole class of leak is caught.
    """
    repo = tmp_path / "repo"
    _git_repo(repo)
    (repo / ".env-example").write_text(
        f'GROQ_API_KEY={REALISTIC["Groq API key"]}\n', encoding="utf-8"
    )
    _commit(repo, "example file with a real-looking key")

    assert len(scan_history(repo)) == 1


def test_a_clean_history_yields_nothing(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _git_repo(repo)
    (repo / "main.py").write_text("print('hello')\n", encoding="utf-8")
    _commit(repo, "clean")
    assert scan_history(repo) == []
