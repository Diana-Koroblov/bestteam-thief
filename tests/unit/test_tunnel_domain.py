"""Which domain we publish on, and where that answer comes from (M#10).

Untested until now, and the two bugs that hid there both cost the same thing:
no public URL, therefore no league match, therefore no grade — and neither was
visible to any other test, because localhost play needs no tunnel at all.

The rule this file pins is that there is **one** resolver with a stated
precedence: what this machine was told, then the legacy name, then the shared
config, then nothing (which is legal — the agent assigns a random URL).
"""

from __future__ import annotations

import pytest

from core.infra.tunnel import DOMAIN_VAR, LEGACY_DOMAIN_VAR, reserved_domain

RESERVED = "denotatively-sciuroid-florine.ngrok-free.dev"
PLACEHOLDER = "your-domain.ngrok-free.dev"


class FakeConfig:
    """Only `get`, which is all `reserved_domain` asks of a config."""

    def __init__(self, domain: str = "") -> None:
        self.domain = domain

    def get(self, key: str, default: object = None) -> object:
        return self.domain if key == "network.public_domain" else default


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never read the developer's own .env: the answer would depend on it."""
    monkeypatch.delenv(DOMAIN_VAR, raising=False)
    monkeypatch.delenv(LEGACY_DOMAIN_VAR, raising=False)


def test_the_environment_beats_the_committed_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """🐛 **The committed value was a domain reserved on another account.**

    `--tunnel` could not start at all — `ERR_NGROK_320: This domain is reserved
    for another account` — so M#10 was unmet and no match could be played over
    the internet. A reserved domain is bound to one ngrok login, which makes it
    an account credential in everything but name, so it belongs beside the
    authtoken in `.env` and not in two public repositories.
    """
    monkeypatch.setenv(DOMAIN_VAR, RESERVED)
    assert reserved_domain(FakeConfig("someone-elses.ngrok-free.dev")) == RESERVED


def test_the_legacy_name_never_overrides_the_current_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """🐛 **The placeholder used to win, and it fails like a stolen domain.**

    There were two variables for one value. `P2P_PUBLIC_DOMAIN` was applied by
    `PeerSDK.tunnel` *after* this function had already answered, so it silently
    overrode it — and `.env-example` shipped it holding the literal text
    `your-domain.ngrok-free.dev`. Copying the example and filling in the domain
    the file tells you to fill in therefore left the placeholder in charge, and
    a placeholder domain cannot be bound any more than someone else's can.

    So the old name is still read — an existing `.env` must not stop working —
    but it is read **last**, because a value set on purpose beats one inherited
    from a template.
    """
    monkeypatch.setenv(DOMAIN_VAR, RESERVED)
    monkeypatch.setenv(LEGACY_DOMAIN_VAR, PLACEHOLDER)
    assert reserved_domain(FakeConfig()) == RESERVED


def test_the_legacy_name_still_works_on_its_own(monkeypatch: pytest.MonkeyPatch) -> None:
    """Renaming a variable must not silently unpublish a working machine."""
    monkeypatch.setenv(LEGACY_DOMAIN_VAR, RESERVED)
    assert reserved_domain(FakeConfig()) == RESERVED


def test_the_config_key_still_answers_when_nothing_is_set() -> None:
    """Kept as a fallback so an older setup is not broken by the move to .env."""
    assert reserved_domain(FakeConfig("from-config.ngrok-free.dev")) == (
        "from-config.ngrok-free.dev"
    )


def test_no_domain_anywhere_is_a_legitimate_answer() -> None:
    """**None means "let the agent choose", not "fail".**

    The public URL is read back from the agent rather than computed, so a peer
    with no reserved domain still plays; the URL simply changes on restart and
    has to be re-sent. Raising here would stop a fresh clone from playing at
    all, over a convenience.
    """
    assert reserved_domain(FakeConfig()) is None


@pytest.mark.parametrize("blank", ["", "   ", "\t"])
def test_whitespace_is_not_a_domain(blank: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """A key left empty in `.env` reads as a set-but-blank string, not as unset.

    Passed through, it becomes `ngrok http 8081 --url ''`, which the agent
    rejects — at the one moment there is no time to debug it.
    """
    monkeypatch.setenv(DOMAIN_VAR, blank)
    assert reserved_domain(FakeConfig()) is None


def test_the_sdk_does_not_resolve_the_domain_a_second_time() -> None:
    """The regression guard for the bug above, at the place that caused it.

    `PeerSDK.tunnel` once re-read the environment after `from_config` had
    resolved the domain, which is how a lower-precedence name came to win. One
    resolver means one precedence, so the SDK must not mention a domain
    variable at all.
    """
    from pathlib import Path

    source = Path("core/sdk/peer_sdk.py").read_text(encoding="utf-8")
    body = source.split("def tunnel")[1].split("\n    @")[0]
    assert "env.optional(" in body, "the authtoken is still resolved here"
    assert f'"{LEGACY_DOMAIN_VAR}"' not in body
    assert f'"{DOMAIN_VAR}"' not in body
