"""The one interface every text provider implements (TODO 4.3.1).

Appendix F Table 21 names four provider modes and states that the choice is
**private to each peer** — it is not negotiated and the opponent never learns
it. That is why this is an interface rather than a setting: Diana's machine
runs `groq`, Itay's runs `ollama` for graded matches, and a fresh clone runs
`template` offline. All three must be interchangeable at the call site.

One method, because a provider's only job is turning a prompt into a sentence.
Everything that makes a hint *legal* — the word cap, the coordinate scanner,
the fabrication ban — lives in ``safety.py`` and is applied by the caller to
every provider alike. A provider cannot opt out of the rules by being clever.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

__all__ = ["TextProvider", "ProviderError"]


class ProviderError(RuntimeError):
    """A provider could not produce text.

    Always recoverable by design: the caller degrades to the template bank
    (ADR-003). A dull sentence costs nothing, a raised exception costs the match.
    """


class TextProvider(ABC):
    """Turns a prompt into one short sentence.

    Attributes:
        name: Short identifier, written to the log so a replay records which
            provider actually spoke on each turn — including the turns where a
            timeout silently demoted us to the template bank.
    """

    name: str = "base"

    @abstractmethod
    def generate(self, prompt: str, max_words: int) -> str:
        """Return a hint of at most *max_words* words.

        Args:
            prompt: The instruction, already carrying the brain's chosen
                ``Intent``. A provider is never asked to decide whether to lie
                — see 4.5.1 and Ch. 5.
            max_words: Appendix F's negotiated cap.

        Raises:
            ProviderError: On any failure. The caller handles it; the provider
                does not retry, because the fallback is faster than a retry and
                the watchdog does not care why we were slow.
        """
