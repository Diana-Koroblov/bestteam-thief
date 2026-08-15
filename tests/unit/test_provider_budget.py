"""The two startup refusals about `P2P_LLM_PROVIDER`.

Both exist because the same misconfiguration is invisible at run time: a metered
provider quietly overspends, and an unreachable daemon quietly stalls. Neither
fails, so neither is noticed until the bill or the match arrives.
"""

from __future__ import annotations

import pytest

from core.shared.config_manager import Config
from core.shared.provider_budget import (
    BudgetError,
    ProviderUnreachableError,
    selected_provider,
    verify_budget,
    verify_reachable,
)


def _config(**private: object) -> Config:
    """A config carrying only the private keys these checks read.

    `merged` is what `get` reads, so it has to carry the same values — these
    checks live entirely in the private half (`game.toml`), which is why
    `shared` stays empty.
    """
    return Config(shared={}, private=dict(private), merged=dict(private))


# --- which provider are we actually using ------------------------------------


def test_the_environment_beats_the_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """`.env` is the per-machine override; `game.toml` is the committed default."""
    monkeypatch.setenv("P2P_LLM_PROVIDER", "ollama")
    assert selected_provider(_config(trash_talk={"provider": "template"})) == "ollama"


def test_the_provider_is_read_through_env_not_os_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    """🐛 The regression that cost two match windows on 15/08.

    `selected_provider` read `os.environ` directly, which holds nothing from
    `.env` until `env.load_env()` has run. At CLI startup it therefore answered
    ``template`` on a machine whose `.env` said ``ollama``, so both checks below
    passed without examining the thing they exist to examine. Reading through
    `core.shared.env` — the one module allowed to answer this question — is what
    makes them fire at all.
    """
    from core.shared import provider_budget

    asked: list[str] = []

    def only_in_dotenv(name: str, default: object = None) -> object:
        """Stand in for a `.env` that `os.environ` has never been told about."""
        asked.append(name)
        return "ollama" if name == "P2P_LLM_PROVIDER" else default

    monkeypatch.delenv("P2P_LLM_PROVIDER", raising=False)
    monkeypatch.setattr(provider_budget.env, "optional", only_in_dotenv)

    # Reading `os.environ` would miss this entirely and fall back to the file.
    assert selected_provider(_config(trash_talk={"provider": "template"})) == "ollama"
    assert "P2P_LLM_PROVIDER" in asked


# --- metered providers -------------------------------------------------------


def test_a_metered_provider_at_every_turn_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("P2P_LLM_PROVIDER", "claude_api")
    with pytest.raises(BudgetError, match="every_n_steps"):
        verify_budget(_config(trash_talk={"every_n_steps": 1}))


def test_a_free_provider_at_every_turn_is_fine(monkeypatch: pytest.MonkeyPatch) -> None:
    """`template` and `ollama` spend zero tokens, so 1 buys the richest talk."""
    monkeypatch.setenv("P2P_LLM_PROVIDER", "template")
    verify_budget(_config(trash_talk={"every_n_steps": 1}))


# --- daemon providers --------------------------------------------------------


def test_an_unreachable_daemon_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """It does not fail at run time — it stalls every turn and hides itself."""
    monkeypatch.setenv("P2P_LLM_PROVIDER", "ollama")
    with pytest.raises(ProviderUnreachableError) as raised:
        verify_reachable(_config(llm={"timeout_sec": 8}), probe=lambda _url: False)

    message = str(raised.value)
    assert "ollama" in message
    # Both one-line fixes named: which is right depends on the match, and a
    # message naming only one sends a human hunting for the other.
    assert "ollama serve" in message and "P2P_LLM_PROVIDER=template" in message
    assert "280s" in message, "the cost must be quantified, not merely asserted"


def test_a_reachable_daemon_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("P2P_LLM_PROVIDER", "ollama")
    verify_reachable(_config(), probe=lambda _url: True)


def test_a_non_daemon_provider_is_never_probed(monkeypatch: pytest.MonkeyPatch) -> None:
    """`template` calls nothing, so there is no daemon to be down."""
    monkeypatch.setenv("P2P_LLM_PROVIDER", "template")

    def explode(_url: str) -> bool:
        raise AssertionError("template must not be probed")

    verify_reachable(_config(), probe=explode)
