"""Counting the language-model tokens a series actually spent (TODO 6.3.4, M#54).

M#54 requires the closing report to state the tokens consumed in the sub-game and
in the series. Until this existed the number was the literal `0` in
`runtime/filing.py` — honest on the `template` provider, which calls no model at
all, and a **false declaration** the moment `.env` selects `groq` or `ollama`, as
both machines' documented setups do. A false declaration is the one class of
mistake the rulebook punishes hardest (M#38), and the way it happens to an honest
team is a placeholder nobody revisited.

Three decisions shape this:

**It counts what the provider reports, never an estimate.** Both endpoints we
call speak the OpenAI shape and return a `usage` block. A locally-computed guess
from word counts would be a number we could not defend against the opponent's
copy of the same conversation, and a defensible zero beats an indefensible
figure.

**A call whose usage we could not read is counted separately, not as zero.**
`unmetered` is the difference between "no tokens were spent" and "tokens were
spent and nobody told us how many". Collapsing the two would let a provider that
silently stopped reporting usage file a series as free.

**Nothing here can break a turn.** `record` never raises: a hint is sealed into
the commit record every turn (Ch. 5.3.1), and losing a sub-game to the accounting
would cost more than the accounting is worth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = ["TokenMeter", "tokens_in"]


def tokens_in(usage: Any) -> int:
    """Return the token count in a provider's ``usage`` block, or 0.

    Prefers ``total_tokens`` and falls back to the two halves, because Groq
    sends all three and a local Ollama build has been seen to send only the
    halves. Anything unreadable — absent, null, a string, a nested shape we do
    not recognise — is 0 rather than an exception; the caller records it as
    unmetered and the report says so.
    """
    if not isinstance(usage, dict):
        return 0
    for key in ("total_tokens", "totalTokens"):
        counted = _as_int(usage.get(key))
        if counted:
            return counted
    return _as_int(usage.get("prompt_tokens")) + _as_int(usage.get("completion_tokens"))


def _as_int(value: Any) -> int:
    """Coerce a reported figure to a non-negative int, or 0 if it is not one."""
    try:
        counted = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, counted)


@dataclass
class TokenMeter:
    """Cumulative model-token spend for one process, read per sub-game.

    Attributes:
        total: Every token this process has been told it spent. Cumulative and
            never reset, so it stays comparable with the running scoreboard.
        calls: How many times a model was actually asked for a sentence. Zero on
            `template`, which answers from a bank in process.
        unmetered: Calls that returned no readable usage. A non-zero value here
            beside a small `total` is the shape of a provider we stopped being
            able to account for.
    """

    total: int = 0
    calls: int = 0
    unmetered: int = 0
    _taken: int = 0

    def record(self, usage: Any) -> int:
        """Count one completed model call and return what it cost.

        Called after the response has been parsed, never inside the provider's
        own try block: a surprise in the accounting must not be reported to the
        caller as a provider failure, because that failure path discards a hint
        the model successfully produced.
        """
        counted = tokens_in(usage)
        self.calls += 1
        if counted:
            self.total += counted
        else:
            self.unmetered += 1
        return counted

    def take(self) -> int:
        """Return what has been spent since the last call, for one sub-game row.

        The series total is **not** this figure summed here. Under a 3-3 split
        two processes each meter their own half, so the series is summed from the
        merged per-sub-game rows in `core/report/merge.py` — the same place, and
        for the same reason, that the points are.
        """
        window = self.total - self._taken
        self._taken = self.total
        return window
