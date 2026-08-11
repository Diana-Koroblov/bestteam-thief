"""The token meter (TODO 6.3.4, M#54).

M#54 requires the closing report to state the tokens consumed. Before this the
figure was the literal `0` in `runtime/filing.py` — true on `template` and a
false declaration on any provider that calls a model, which is what both
machines' `.env` files select. These tests pin the two properties that make the
number defensible: it is what the provider reported, and a call we could not
account for is visible rather than free.
"""

from __future__ import annotations

import httpx
import pytest

from core.infra.llm.meter import TokenMeter, tokens_in
from core.infra.llm.remote import GroqProvider, OllamaProvider

USAGE = {"prompt_tokens": 40, "completion_tokens": 12, "total_tokens": 52}


def _response(payload: dict) -> httpx.Response:
    """Return a stub httpx response carrying *payload* as JSON."""
    return httpx.Response(200, json=payload, request=httpx.Request("POST", "http://x.invalid"))


def _completion(text: str = "You will not find me.", usage: dict | None = None) -> dict:
    """Return an OpenAI-shaped completion, optionally with a usage block."""
    body: dict = {"choices": [{"message": {"content": text}}]}
    if usage is not None:
        body["usage"] = usage
    return body


def _served(monkeypatch, payload: dict) -> None:
    """Make every provider POST return *payload* without touching the network."""
    monkeypatch.setattr(httpx.Client, "post", lambda self, *a, **k: _response(payload))


# --- reading a usage block --------------------------------------------------


def test_it_prefers_the_total_the_provider_computed() -> None:
    assert tokens_in(USAGE) == 52


def test_it_falls_back_to_the_two_halves() -> None:
    """A local Ollama build has been seen to omit `total_tokens`."""
    assert tokens_in({"prompt_tokens": 40, "completion_tokens": 12}) == 52


@pytest.mark.parametrize(
    "usage", [None, {}, "52 tokens", {"total_tokens": None}, {"total_tokens": "many"}]
)
def test_an_unreadable_usage_block_is_zero_not_an_exception(usage) -> None:
    """**Accounting may not raise.** A hint is sealed into the commit record
    every turn (Ch. 5.3.1), so an exception here would forfeit a turn over a
    reporting field."""
    assert tokens_in(usage) == 0


def test_a_negative_count_is_clamped() -> None:
    """No provider should send one; if one does, it must not reduce the series
    total and understate what we consumed."""
    assert tokens_in({"total_tokens": -500}) == 0


# --- the meter --------------------------------------------------------------


def test_it_accumulates_across_calls() -> None:
    meter = TokenMeter()
    meter.record(USAGE)
    meter.record(USAGE)
    assert (meter.total, meter.calls, meter.unmetered) == (104, 2, 0)


def test_an_unaccounted_call_is_counted_apart_from_a_free_one() -> None:
    """**Zero because nothing was spent and zero because nobody told us are
    different findings.** Collapsing them would let a provider that silently
    stopped reporting usage file a whole series as free."""
    meter = TokenMeter()
    meter.record(None)
    assert (meter.total, meter.calls, meter.unmetered) == (0, 1, 1)


def test_take_returns_the_window_since_the_last_take() -> None:
    """One `take` per sub-game, so the row is that sub-game's spend and the
    cumulative total stays readable beside it."""
    meter = TokenMeter()
    meter.record(USAGE)
    assert meter.take() == 52
    meter.record(USAGE)
    meter.record(USAGE)
    assert meter.take() == 104
    assert meter.take() == 0
    assert meter.total == 156


# --- the providers report into it -------------------------------------------


def test_groq_reports_what_it_spent(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    meter = TokenMeter()
    _served(monkeypatch, _completion(usage=USAGE))
    GroqProvider("llama-3.3-70b-versatile", meter=meter).generate("taunt", 15)
    assert meter.total == 52


def test_ollama_reports_what_it_spent(monkeypatch) -> None:
    """Counted even though the tokens are unbilled: M#54 asks what was consumed,
    and a local model consumes tokens. `[token estimate per series]` is the
    ceiling they are checked against."""
    meter = TokenMeter()
    _served(monkeypatch, _completion(usage=USAGE))
    OllamaProvider("llama3.1:8b", meter=meter).generate("taunt", 15)
    assert meter.total == 52


def test_a_provider_with_no_meter_still_answers(monkeypatch) -> None:
    """The meter is optional so a script or a test double runs unchanged."""
    _served(monkeypatch, _completion(usage=USAGE))
    assert OllamaProvider("llama3.1:8b").generate("taunt", 15)


def test_the_peer_hands_its_own_meter_to_the_provider(minimal_config, monkeypatch) -> None:
    """**The seam the whole fix hangs on.**

    The meter is owned by `LocalTruth`, reached by `SeriesRunner` through
    `PeerRuntime.meter`, and must be the same object the provider reports into.
    A writer built with a *different* meter would count faithfully into an object
    nobody reads, and the report would go back to declaring zero — which is the
    defect, restored, with tests passing.
    """
    from core.infra.llm.factory import build_writer
    from core.protocol.schemas import Role
    from core.runtime.orchestrator import Orchestrator
    from core.runtime.peer_runtime import PeerRuntime

    monkeypatch.setenv("P2P_LLM_PROVIDER", "ollama")
    peer = PeerRuntime(orchestrator=Orchestrator.from_config(minimal_config, Role.COP))
    writer = build_writer(minimal_config, peer.meter)

    assert writer.provider.meter is peer.meter
    assert peer.meter is peer.truth.meter


def test_the_template_bank_reports_no_call_at_all(minimal_config, monkeypatch) -> None:
    """Zero tokens **and** zero calls. The bank answers in process, so its
    honest contribution to the report is the absence of a call rather than a
    metered zero — which is what keeps `unmetered` meaningful."""
    from core.domain.intent import Intent
    from core.infra.llm.factory import build_writer

    monkeypatch.setenv("P2P_LLM_PROVIDER", "template")
    meter = TokenMeter()
    hint = build_writer(minimal_config, meter).write("north", Intent.TRUTH, step=1)

    assert hint.text
    assert (meter.total, meter.calls, meter.unmetered) == (0, 0, 0)


def test_a_failed_call_costs_nothing(monkeypatch) -> None:
    """No completion, no usage block, no entry — the call never reached a model
    in a way that could be billed, and inventing a figure for it would overstate
    consumption in a signed report."""
    from core.infra.llm.base import ProviderError

    meter = TokenMeter()
    monkeypatch.setattr(httpx.Client, "post", lambda self, *a, **k: _response({"error": "boom"}))
    with pytest.raises(ProviderError):
        OllamaProvider("llama3.1:8b", meter=meter).generate("taunt", 15)
    assert (meter.total, meter.calls) == (0, 0)
