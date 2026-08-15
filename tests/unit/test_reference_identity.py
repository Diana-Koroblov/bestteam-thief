"""The identity block we publish at every reference-protocol handshake.

An opponent files this against us and a grader reads it afterwards, so what it
omits matters as much as what it says.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.protocol.schemas import Role
from core.reference_identity import identity_of
from core.sdk.peer_sdk import PeerSDK
from tests.paths import PRESENT_ROLES, role_dir

ROLE = PRESENT_ROLES[0]


@pytest.fixture
def identity() -> dict:
    """The block a real peer of the published role would send."""
    role = Role.COP if role_dir(ROLE).name == "police" else Role.THIEF
    return identity_of(PeerSDK(role_dir(ROLE), role))


def test_it_declares_the_commit_that_is_being_played(identity: dict) -> None:
    """🐛 M#53, and the key was **absent** until 16/08 — never sent at all.

    The native path pins the commit through `step_zero`; this path had no field
    for it, so an opponent's artefacts recorded ``unknown`` against us across
    two match attempts and neither side could name the code that ran. An
    omission is worse than an admitted blank, because nobody notices it.
    """
    assert "github_commit" in identity, "M#53: the commit played must be declared"
    assert identity["github_commit"], "an empty commit is the same failure with a key"


def test_the_commit_is_read_from_git_rather_than_typed(identity: dict) -> None:
    """A literal would pin whichever commit somebody last pasted in."""
    import subprocess

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
        cwd=Path(__file__).resolve().parents[2], check=False,
    ).stdout.strip()
    if head:
        assert identity["github_commit"].startswith(head[:12])


def test_it_declares_the_model_that_will_actually_answer(identity: dict) -> None:
    """The wire and the filed papers must not disagree.

    They did: `.env` selected `ollama` while every written declaration said
    template/zero-tokens, and the opponent spotted the contradiction before we
    did. The value is read from the provider registry so it cannot drift from
    whichever provider a turn really calls.
    """
    assert identity["llm_model"], "a blank model tells an opponent nothing"


def test_the_counted_total_comes_from_the_league_log(identity: dict) -> None:
    """M#38 disqualifies the project for a wrong count, so it is never typed."""
    from core.shared.league_log import counted_matches

    assert identity["counted_games_played"] == counted_matches()


def test_both_repositories_are_named(identity: dict) -> None:
    """Ch. 9.4 wants four links in the closing JSON — two of them are ours."""
    assert identity["repos"]["cop"] and identity["repos"]["thief"]
