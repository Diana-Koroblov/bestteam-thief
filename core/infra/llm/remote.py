"""The two model-backed providers: Ollama and Groq (TODO 4.3.3, 4.3.4).

Both speak the OpenAI chat-completions shape, so they differ only in URL, auth
and model name. Kept in one module because that is the whole difference — two
near-identical files would invite them to drift apart.

**This module is the only place either service is called.** No SDK import, no
API key and no base URL appears anywhere else in the codebase (4.3.4), which is
what makes "which provider are we running?" a one-line answer during a match
and keeps the key off every other import path.

Keys come from the environment, never from ``game.toml``: the config file is
committed and exchanged with the opponent during negotiation.
"""

from __future__ import annotations

import os

import httpx

from core.infra.llm.base import ProviderError, TextProvider
from core.infra.llm.meter import TokenMeter

__all__ = ["OllamaProvider", "GroqProvider"]

SYSTEM = (
    "You are an agent in a pursuit game taunting your opponent. "
    "Reply with ONE sentence of at most {max_words} words. "
    "Never write numbers, coordinates, row/column references or grid positions. "
    "Speak only in directions and landmarks."
)


class _ChatProvider(TextProvider):
    """Shared request/parse logic for any OpenAI-compatible chat endpoint."""

    def __init__(
        self,
        model: str,
        timeout: float = 8.0,
        max_tokens: int = 200,
        meter: TokenMeter | None = None,
    ) -> None:
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        # Optional so a provider built in a test or a script still runs; the
        # match wiring always supplies the peer's one meter (M#54).
        self.meter = meter

    def _url(self) -> str:
        raise NotImplementedError

    def _headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    def generate(self, prompt: str, max_words: int) -> str:
        """POST the prompt and return the sentence, or raise ``ProviderError``.

        Every failure mode is collapsed into one exception type on purpose. The
        caller's response is identical whatever went wrong — fall back to the
        template bank — and a turn spent distinguishing a 429 from a DNS failure
        is a turn spent approaching the 30-second response limit.
        """
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM.format(max_words=max_words)},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self.max_tokens,
            "temperature": 0.8,
            "stream": False,
        }
        payload: dict = {}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self._url(), json=body, headers=self._headers())
                response.raise_for_status()
                payload = response.json()
                content = payload["choices"][0]["message"]["content"]
        except Exception as error:  # noqa: BLE001 - deliberate, see below
            # **Catching bare Exception is the correct call here, not laziness.**
            # This started as a tidy `(httpx.HTTPError, KeyError, IndexError,
            # ValueError)` tuple, and an ImportError raised while *constructing*
            # the client — before any request — sailed straight through it and
            # crashed the process. On a listed-exceptions basis we would be
            # betting that we can enumerate every way a third-party HTTP stack,
            # a proxy layer and a remote JSON API can fail. We cannot, and the
            # forfeit for being wrong is the whole match.
            #
            # The caller's response is identical whatever happened: fall back to
            # the template bank. So the only thing a narrower clause buys is the
            # chance to miss one.
            raise ProviderError(f"{self.name}: {type(error).__name__}: {error}") from error

        # **Outside the try, deliberately.** A call that produced a sentence has
        # already cost tokens, so it is counted even if the sentence is then
        # rejected as empty — and an accounting surprise must never be raised as
        # a ProviderError, which would discard a hint the model did produce.
        if self.meter is not None:
            self.meter.record(payload.get("usage"))
        if not content or not content.strip():
            raise ProviderError(f"{self.name}: empty completion")
        return content.strip().strip('"')


class OllamaProvider(_ChatProvider):
    """Local model on ``localhost:11434``. Unmetered, so ``every_n_steps`` is 1.

    Itay's machine runs this for graded matches: zero tokens, no rate limit and
    no dependency on a service being up during a match we cannot replay.
    """

    name = "ollama"

    def _url(self) -> str:
        base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        return f"{base}/v1/chat/completions"


class GroqProvider(_ChatProvider):
    """Hosted model, our own fifth provider (ADR-003).

    Diana's machine runs this in development because it has no GPU. It is
    **metered**, which is the one condition under which ``every_n_steps`` must
    rise from 1 to 3 — see the note in ``game.toml``.
    """

    name = "groq"

    def _url(self) -> str:
        return "https://api.groq.com/openai/v1/chat/completions"

    def _headers(self) -> dict[str, str]:
        key = os.environ.get("GROQ_API_KEY", "")
        if not key:
            raise ProviderError("groq: GROQ_API_KEY is not set")
        return {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
