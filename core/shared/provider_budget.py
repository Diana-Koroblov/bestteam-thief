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

from core.shared import env

__all__ = ["BudgetError", "DAEMON_PROVIDERS", "METERED_PROVIDERS", "MIN_INTERVAL_WHEN_METERED",
           "ProviderUnreachableError", "verify_budget", "verify_reachable"]

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

    🐛 **Through `env.optional`, never `os.environ` directly.** This read the
    ambient environment, which is empty of `.env` until somebody calls
    `env.load_env()` — so at CLI startup it answered ``template`` on a machine
    whose `.env` said ``ollama``, and every check built on it passed without
    examining anything. Exactly the fault `core/infra/tunnel.py` documents
    having fixed in `reserved_domain`, in a module whose own docstring warns
    that asking the same question two ways is how a check comes to pass while
    the thing it checks is misconfigured. It cost two match windows on 15/08.
    """
    name = env.optional("P2P_LLM_PROVIDER") or config.get("trash_talk.provider", "template")
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


# Providers that are a **local daemon** rather than a library call: selecting one
# whose daemon is down does not fail, it stalls.
DAEMON_PROVIDERS = frozenset({"ollama"})

# What one unreachable call costs, from `[llm] timeout_sec`, when nothing answers.
DEFAULT_STALL_SEC = 8.0


class ProviderUnreachableError(RuntimeError):
    """The selected provider is a daemon and the daemon is not answering."""


def verify_reachable(config, probe=None) -> None:
    """Raise if the selected provider is a daemon that is not running.

    **Why this is fatal rather than a warning.** An unreachable Ollama does not
    error: every turn waits out `[llm] timeout_sec` and then writes the template
    hint anyway, so the match plays on, produces byte-identical hints to
    `template`, and pays the timeout for nothing. At the shipped 8 s and a hint
    every turn that is up to **280 s of dead time per 35-step sub-game** — enough
    to time out an opponent who is behaving perfectly, which is exactly how it
    presented against imreeyal on 15/08: two windows lost to what looked like a
    protocol fault and was a daemon nobody had started.

    Silent, self-healing and expensive is the worst combination a default can
    have, so it is refused at startup where a human can still fix it. The two
    fixes are both one line, and which is right depends on the match: a counted
    league game wants the model running (the verbal layer is graded); a friendly
    is perfectly playable at `template`, which spends zero tokens and stalls for
    nothing.

    Args:
        config: A loaded configuration.
        probe: Injected for tests — ``(base_url) -> bool``. Defaults to a short
            HTTP GET against the daemon's own tag listing.
    """
    provider = selected_provider(config)
    if provider not in DAEMON_PROVIDERS:
        return

    base = env.optional("OLLAMA_BASE_URL") or "http://localhost:11434"
    if (probe or _reachable)(base):
        return

    stall = float(config.get("llm.timeout_sec", DEFAULT_STALL_SEC) or DEFAULT_STALL_SEC)
    steps = int(config.get("movement_and_barriers.max_moves", 35) or 35)
    raise ProviderUnreachableError(
        f"P2P_LLM_PROVIDER is {provider!r} but nothing is answering at {base}. "
        f"This does NOT fail at run time - every turn would wait out "
        f"[llm] timeout_sec ({stall:g}s) and then write the template hint anyway, "
        f"up to {stall * steps:.0f}s of dead time per {steps}-step sub-game. "
        f"Either start it ('ollama serve' in its own terminal, then 'ollama pull "
        f"<model>') for a counted match where the verbal layer is graded, or set "
        f"P2P_LLM_PROVIDER=template in .env for a friendly - zero tokens, no stall. "
        f"See docs/SETUP.md 0.2.3 and docs/MATCHDAY.md."
    )


def _reachable(base_url: str) -> bool:  # pragma: no cover - needs a live daemon
    """Return whether the daemon answers its tag listing inside 3 seconds."""
    try:
        import httpx

        return httpx.get(f"{base_url}/api/tags", timeout=3.0).status_code == 200
    except Exception:  # noqa: BLE001 - any failure means "not reachable"
        return False
