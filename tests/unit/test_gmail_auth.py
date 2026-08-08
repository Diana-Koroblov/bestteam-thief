"""The one-time consent, and the guard on where its token lands (SETUP 0.2.1).

The browser flow itself cannot be tested — it opens a window and talks to
Google, which is exactly why it is one function at the edge. What *is* testable
is the part that decides whether a refresh token is about to be written
somewhere it must never go, and that is the part with a permanent consequence.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.gmail_auth import REPOS, SCOPES, refuse_unsafe_token_path
from core.infra.gmail_sender import SEND_SCOPE, GmailError


def test_consent_asks_for_send_only(tmp_path) -> None:
    """**M#30.** The grant is what the user approves, and it cannot be narrowed later.

    A token minted under `gmail.modify` can read the mailbox no matter how
    carefully the sending code is written, so the scope list has to be right
    here rather than at the call site.
    """
    assert SCOPES == [SEND_SCOPE]
    assert "gmail.send" in SEND_SCOPE


@pytest.mark.parametrize("repo", REPOS)
def test_a_token_inside_a_repository_is_refused(tmp_path, repo: str) -> None:
    """**M#39, M#40.** Refused, not warned — the write is the irreversible act.

    A warning here is printed to a console that scrolls, and the next
    `git add -A` inside `ship.py` stages the token. `scan_secrets.py` hunts for
    API-key shapes and would not reliably recognise an OAuth JSON blob, so this
    is the check that stands between a refresh token and a permanent place in
    two public git histories.
    """
    inside = tmp_path / repo / "config" / "token.json"
    inside.parent.mkdir(parents=True)
    with pytest.raises(GmailError, match=f"inside {repo}"):
        refuse_unsafe_token_path(inside, tmp_path)


def test_a_token_outside_every_repository_is_allowed(tmp_path) -> None:
    """The documented location: a secrets folder beside the repos, not in one."""
    outside = tmp_path / ".p2p-secrets" / "token.json"
    assert refuse_unsafe_token_path(outside, tmp_path) == outside


def test_a_sibling_directory_is_not_mistaken_for_a_repository(tmp_path) -> None:
    """`p2p-chase-secrets` starts with a repository name and is not one.

    A substring test would refuse the obvious place someone puts this, and an
    error that fires on a correct setup teaches people to work around the check.
    """
    sibling = tmp_path / "p2p-chase-secrets" / "token.json"
    assert refuse_unsafe_token_path(sibling, tmp_path) == sibling


@pytest.mark.parametrize("value", ["", ".", "   "])
def test_an_unset_path_is_refused_by_name(tmp_path, value: str) -> None:
    """🐛 `Path("")` normalises to `Path(".")`, which is not empty and is not safe.

    An unset `.env` key therefore arrived looking like the working directory —
    which during a setup walkthrough is the repository itself, the one place the
    token must never go.
    """
    with pytest.raises(GmailError, match="GMAIL_TOKEN_PATH is empty"):
        refuse_unsafe_token_path(Path(value), tmp_path)


def test_the_repository_root_itself_is_refused(tmp_path) -> None:
    """🐛 A directory is not among its own parents.

    `Path(...).parents` walks *upwards*, so a token path resolving exactly to
    the repository root passed a check written only as `root in parents` — the
    most obvious failure slipping through the guard against it.
    """
    (tmp_path / "p2p-chase").mkdir()
    with pytest.raises(GmailError, match="inside p2p-chase"):
        refuse_unsafe_token_path(tmp_path / "p2p-chase", tmp_path)
