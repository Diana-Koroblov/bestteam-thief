"""Builds the provider named in config, honouring the private override.

The selection lives in `[trash_talk] provider`, but the committed value is
always `template` — the book's default, and the only one that works on a fresh
clone with no network. Each machine overrides it through the environment
(`P2P_LLM_PROVIDER`), never by editing the file, because `game.toml` is
exchanged with the opponent during negotiation and the provider choice is
explicitly private (Appendix F Table 21).

An unknown or unavailable provider name resolves to `template` rather than
raising. Starting a graded match is worth more than running the provider we
preferred.
"""

from __future__ import annotations

import os

from core.infra.llm.base import TextProvider
from core.infra.llm.meter import TokenMeter
from core.infra.llm.remote import GroqProvider, OllamaProvider
from core.infra.llm.template import TemplateProvider
from core.infra.llm.writer import HintWriter

__all__ = ["build_provider", "build_writer", "model_name", "PROVIDERS"]

PROVIDERS = ("template", "ollama", "groq")


def build_provider(config, meter: TokenMeter | None = None) -> TextProvider:
    """Return the provider this machine should use.

    The environment wins over the file, and an unrecognised name degrades to
    the template bank instead of raising (ADR-003).

    Args:
        meter: Where model calls report their token cost (M#54). Optional, and
            **only the model-backed providers take it**: the template bank calls
            nothing, so its honest contribution is the absence of a call rather
            than a zero.
    """
    name = os.environ.get("P2P_LLM_PROVIDER") or config.get("trash_talk.provider", "template")
    name = str(name).strip().lower()
    timeout = float(config.get("llm.timeout_sec", 8))
    tokens = int(config.get("llm.max_output_tokens", 200))

    if name == "ollama":
        model = str(config.get("llm.ollama_model", "llama3.1:8b"))
        return OllamaProvider(model, timeout, tokens, meter)
    if name == "groq":
        model = str(config.get("llm.groq_model", "llama-3.3-70b-versatile"))
        return GroqProvider(model, timeout, tokens, meter)
    return TemplateProvider()


def model_name(config) -> str:
    """Return the model this machine will actually run (M#24, TODO 9.1.4).

    Resolved through `build_provider`, so the **environment override is
    honoured**. A Step-0 declaration that read `llm.ollama_model` directly would
    name Ollama on a machine whose `.env` selected groq or template, and Appendix
    F Table 21 makes the model — not the provider — the thing we declare. A
    declaration naming a model we never called is a false one.

    Template mode has no model, so it names itself: "template" is the honest
    answer to "which model produced these hints" when none did.
    """
    provider = build_provider(config)
    return str(getattr(provider, "model", "") or provider.name)


def build_writer(config, meter: TokenMeter | None = None) -> HintWriter:
    """Return a `HintWriter` wired to Appendix F's caps and fabrication bans."""
    return HintWriter(
        provider=build_provider(config, meter),
        max_words=int(config.get("trash_talk.max_words", 15)),
        forbidden=tuple(config.get("trash_talk.never_fabricate", ())),
        allow_fallback=bool(config.get("llm.allow_template_fallback", True)),
    )
