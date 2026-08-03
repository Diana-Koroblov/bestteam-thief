"""Refusing a configuration that would quietly burn the token budget (TODO 7.1.6).

`[trash_talk] every_n_steps` governs how often the **model** runs, not how often
a hint is sent — a hint goes out every turn regardless, written by the template
bank on the turns the model is skipped, because the sealed commit covers the
hint and a turn without one would break commit-reveal (Ch. 5.3.1).

So the safe interval depends entirely on whether the provider costs anything:

* `template` and `ollama` spend **zero** tokens. `template` calls no model at
  all and `ollama` is local, unmetered and rate-limit free. At those, 1 is
  correct and buys the richest verbal game — in a project where the deception
  layer is graded.
* `groq`, `claude_api` and `claude_cli` are **metered**. At 1 a six-sub-game
  series makes 210 model calls instead of ~70 — roughly 52 k tokens on a paid
  tier, enough to brush the five-hour message window of every subscription.

**Why this is a check and not a comment.** The two halves live in different
files on different machines: the interval is committed in `game.toml`, the
provider is set per machine in `.env` (`P2P_LLM_PROVIDER`). Nothing stops them
drifting apart on someone else's laptop, and the drift is invisible until the
bill or the rate limit arrives mid-series. A comment cannot catch that; a
startup refusal naming both keys can.

Deliberately called from the CLI rather than from `PeerSDK.__init__`: this must
stop a human about to play a match, not fail the test suite on the one machine
whose `.env` happens to select a metered provider.
"""

from __future__ import annotations

import os

__all__ = ["BudgetError", "METERED_PROVIDERS", "MIN_INTERVAL_WHEN_METERED", "verify_budget"]

# The providers that cost money or rate-limit quota per call.
METERED_PROVIDERS = frozenset({"groq", "claude_api", "claude_cli"})

# See the module docstring for the arithmetic behind this number.
MIN_INTERVAL_WHEN_METERED = 3


class BudgetError(RuntimeError):
    """A metered provider is paired with an interval that would overspend."""


def selected_provider(config) -> str:
    """Return the provider this machine will actually use.

    The environment wins over the file, exactly as
    :func:`core.infra.llm.factory.build_provider` resolves it — asking the same
    question two different ways is how a check comes to pass while the thing it
    checks is misconfigured.
    """
    name = os.environ.get("P2P_LLM_PROVIDER") or config.get("trash_talk.provider", "template")
    return str(name).strip().lower()


def verify_budget(config) -> None:
    """Raise if a metered provider is paired with too short an interval.

    Args:
        config: A loaded :class:`~core.shared.config_manager.Config`.

    Raises:
        BudgetError: Naming **both** keys and both current values. Naming only
            one leaves whoever reads it hunting for the other half, and the
            other half is on a different machine.
    """
    provider = selected_provider(config)
    if provider not in METERED_PROVIDERS:
        return

    interval = int(config.get("trash_talk.every_n_steps", 1))
    if interval >= MIN_INTERVAL_WHEN_METERED:
        return

    raise BudgetError(
        f"provider {provider!r} is metered but [trash_talk] every_n_steps is {interval}. "
        f"A 6-sub-game series would make ~210 model calls instead of ~70 (~52k tokens). "
        f"Either raise every_n_steps to {MIN_INTERVAL_WHEN_METERED} in config/<role>/game.toml, "
        f"or set P2P_LLM_PROVIDER to 'template' or 'ollama' in .env - both spend zero tokens. "
        f"See docs/REFERENCE_PERFORMANCE_NOTES.md section 2."
    )
