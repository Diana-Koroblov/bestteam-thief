"""Budget loading, the token-budget startup check, and naming discipline.

Covers TODO 7.1.4 and 7.1.6 plus PRD 7 req. 7.6. These are the parts of the
Gatekeeper that are policy rather than mechanism: what the limits are allowed
to be, what pairing of provider and interval is allowed to start, and what
things are allowed to be called.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from core.shared.provider_budget import (
    METERED_PROVIDERS,
    MIN_INTERVAL_WHEN_METERED,
    BudgetError,
    verify_budget,
)
from core.shared.rate_limits import RateLimitsError, load_rate_limits
from tests.paths import PRESENT_ROLES, REPO_ROOT, role_dir

SHIPPED = json.loads((role_dir(PRESENT_ROLES[0]) / "rate_limits.json").read_text("utf-8"))


@pytest.fixture(autouse=True)
def _no_ambient_provider(monkeypatch) -> None:
    """Clear `P2P_LLM_PROVIDER` so these tests read the config they were given.

    **Found by the suite, not in isolation.** `env.load_env()` copies the real
    `.env` into `os.environ` the first time anything touches it, and the
    provider check deliberately lets the environment win over the file. So
    whether this file saw a provider at all depended on test order: alone it
    passed, after any test that loads `.env` it silently asserted nothing.

    That is the same ambient-environment failure `core/shared/env.py` exists to
    prevent, arriving through the test suite instead of through a module.
    """
    monkeypatch.delenv("P2P_LLM_PROVIDER", raising=False)


class StubConfig:
    """A config that answers only what the check under test asks it."""

    def __init__(self, **values: object) -> None:
        self.values = values

    def get(self, path: str, default: object = None) -> object:
        return self.values.get(path.replace(".", "_"), default)


def write_limits(directory: Path, **overrides: object) -> Path:
    """Write a budget file into *directory*, starting from the shipped one."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "rate_limits.json").write_text(
        json.dumps({**SHIPPED, **overrides}), encoding="utf-8"
    )
    return directory


# --- loading the budget (req. 7.6) -------------------------------------------


@pytest.mark.parametrize("role", PRESENT_ROLES)
def test_the_shipped_budget_is_complete_and_playable(role: str) -> None:
    assert load_rate_limits(role_dir(role)).violations() == []


def test_a_missing_file_names_the_path(tmp_path: Path) -> None:
    with pytest.raises(RateLimitsError, match="missing Gatekeeper budget"):
        load_rate_limits(tmp_path)


def test_malformed_json_is_reported_as_such(tmp_path: Path) -> None:
    (tmp_path / "rate_limits.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(RateLimitsError, match="not valid JSON"):
        load_rate_limits(tmp_path)


def test_a_missing_limit_is_named_rather_than_defaulted(tmp_path: Path) -> None:
    """**No limit has a default in code.** A number nobody can inspect is a
    number nobody agreed to, which is the whole point of req. 7.6."""
    incomplete = {key: value for key, value in SHIPPED.items() if key != "daily_send_quota"}
    (tmp_path / "rate_limits.json").write_text(json.dumps(incomplete), encoding="utf-8")
    with pytest.raises(RateLimitsError, match="daily_send_quota"):
        load_rate_limits(tmp_path)


def test_a_retry_budget_that_outlives_the_response_window_is_refused(tmp_path: Path) -> None:
    """3 x 5 s fits inside 30 s; a fourth retry would not.

    The last retry would still be waiting when the opponent has already
    recorded us as gone, which converts a recoverable blip into a technical
    loss for both sides.
    """
    write_limits(tmp_path, max_retries=6, retry_backoff_sec=5)
    with pytest.raises(RateLimitsError, match="does not fit inside"):
        load_rate_limits(tmp_path)


def test_an_unplayable_budget_can_still_be_inspected(tmp_path: Path) -> None:
    """So the problem can be quoted back rather than merely refused."""
    write_limits(tmp_path, max_retries=6)
    limits = load_rate_limits(tmp_path, enforce=False)
    assert len(limits.violations()) == 1


def test_a_budget_that_permits_no_call_at_all_is_refused(tmp_path: Path) -> None:
    """Zero is arithmetically legal and operationally a permanent outage.

    The bucket needs one whole token per request, so `burst_capacity = 0` never
    admits anything; `concurrent_requests = 0` blocks in the queue forever.
    Both are silent — no error, just a peer that never reports.
    """
    write_limits(tmp_path, burst_capacity=0, concurrent_requests=0)
    limits = load_rate_limits(tmp_path, enforce=False)
    assert len(limits.violations()) == 2
    with pytest.raises(RateLimitsError, match="no call at all"):
        load_rate_limits(tmp_path)


# --- the startup check (7.1.6) -----------------------------------------------


def test_a_zero_token_provider_may_run_every_turn() -> None:
    """`template` and `ollama` spend nothing, so 1 is correct and buys the
    richest verbal game — in a project where deception is graded."""
    for provider in ("template", "ollama"):
        verify_budget(StubConfig(trash_talk_provider=provider, trash_talk_every_n_steps=1))


def test_a_metered_provider_every_turn_is_refused() -> None:
    """~210 model calls instead of ~70, roughly 52k tokens on a paid tier."""
    with pytest.raises(BudgetError) as caught:
        verify_budget(StubConfig(trash_talk_provider="groq", trash_talk_every_n_steps=1))

    message = str(caught.value)
    assert "every_n_steps" in message and "P2P_LLM_PROVIDER" in message, (
        "the message must name BOTH keys: they live in different files on "
        "different machines, and naming one leaves the reader hunting the other"
    )


def test_a_metered_provider_at_the_safe_interval_starts() -> None:
    verify_budget(
        StubConfig(
            trash_talk_provider="groq", trash_talk_every_n_steps=MIN_INTERVAL_WHEN_METERED
        )
    )


def test_the_environment_wins_over_the_file(monkeypatch) -> None:
    """Asking the question a different way than `build_provider` does is how a
    check comes to pass while the thing it checks is misconfigured."""
    config = StubConfig(trash_talk_provider="template", trash_talk_every_n_steps=1)
    monkeypatch.setenv("P2P_LLM_PROVIDER", "groq")
    with pytest.raises(BudgetError):
        verify_budget(config)


def test_every_metered_provider_is_covered() -> None:
    assert {"groq", "claude_api", "claude_cli"} == METERED_PROVIDERS
    for provider in METERED_PROVIDERS:
        with pytest.raises(BudgetError):
            verify_budget(StubConfig(trash_talk_provider=provider, trash_talk_every_n_steps=1))


@pytest.mark.parametrize("role", PRESENT_ROLES)
def test_the_shipped_pairing_starts(role: str, monkeypatch) -> None:
    from core.shared.config_manager import load_config

    monkeypatch.delenv("P2P_LLM_PROVIDER", raising=False)
    verify_budget(load_config(role_dir(role)))


# --- naming discipline (7.1.4) -----------------------------------------------

# Every module on the outbound path. "Token" means three unrelated things in
# this project and these are where two of them meet.
GATE_MODULES = (
    "gatekeeper",
    "rate_limiter",
    "rate_limits",
    "dos_detector",
    "queue_manager",
    "call_logger",
)


def bound_names(path: Path) -> set[str]:
    """Return every identifier the module binds: fields, arguments, targets."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.arg):
            found.add(node.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            found.add(node.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            found.add(node.target.id)
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
            found.add(node.attr)
    return found


def test_the_three_meanings_of_token_never_share_an_identifier() -> None:
    """**PRD 7 §3.1.** Rate-limiter tokens, LLM tokens and OAuth tokens.

    The book calls this out explicitly, which suggests it has caused confusion
    before. A bare `tokens` on the outbound path is exactly the ambiguity: the
    reader cannot tell whether draining it costs money or merely time.
    `oauth_token` is reserved for the Gmail sender in 7.3.
    """
    for module in GATE_MODULES:
        path = REPO_ROOT / "core" / "shared" / f"{module}.py"
        ambiguous = bound_names(path) & {"token", "tokens"}
        assert not ambiguous, f"{module}.py binds {ambiguous}; say which kind of token"


def test_the_distinct_names_are_actually_used() -> None:
    """A discipline nothing follows is a comment, not a discipline."""
    limiter = (REPO_ROOT / "core" / "shared" / "rate_limiter.py").read_text("utf-8")
    logger = (REPO_ROOT / "core" / "shared" / "call_logger.py").read_text("utf-8")
    assert "rate_tokens" in limiter
    assert "llm_tokens" in logger
