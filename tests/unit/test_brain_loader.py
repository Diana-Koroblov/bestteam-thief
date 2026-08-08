"""Choosing which strategy a peer fields (TODO 3.4).

Split from `test_brains.py`, which tests what the baselines *do*. This tests
which brain gets to do it — a different subject, and the one where a mistake is
silent: every failure mode here ends in a peer that plays perfectly well, just
not with the strategy anybody chose.

Hence the emphasis on *when* a bad value is found. A typo resolved on the first
turn of a graded match is a technical loss worth 0 to both teams; the same typo
found at startup costs an error message.
"""

from __future__ import annotations

import pytest

from core.runtime.brain_loader import CONFIG_KEYS, DEFAULTS, BrainLoadError, brain_for, load_brain
from tests.paths import brain_class, needs_brain

PoliceBrain = brain_class("police")
cop_only = needs_brain("police")


class Config:
    """A config answering exactly the strategy keys it is given, and nothing else.

    A real `Config` returns None for an absent path, which is what made the
    misspelled key invisible — so the stub reproduces that rather than raising.
    """

    def __init__(self, **named: str) -> None:
        self.named = named

    def get(self, path: str, default=None):
        return self.named.get(path, default)


@pytest.mark.parametrize("role,package", [("cop", "police"), ("thief", "thief")])
def test_an_empty_setting_falls_back_to_the_baseline(role: str, package: str) -> None:
    """A fresh clone must play without editing config."""
    expected = brain_class(package)
    if expected is None:
        pytest.skip(f"the {package!r} package is not published to this repository")
    assert isinstance(load_brain("", role), expected)
    assert isinstance(load_brain(None, role), expected)


@cop_only
def test_an_explicit_path_is_honoured() -> None:
    assert isinstance(load_brain("police.brain:PoliceBrain", "cop"), PoliceBrain)


def test_the_defaults_cover_both_roles() -> None:
    assert set(DEFAULTS) == {"cop", "thief"}


def test_the_configured_strategy_key_is_the_one_the_config_file_uses() -> None:
    """🐛 **The key nobody read.**

    Appendix B.4 and our own `[strategy]` section both spell it `police_class`;
    every caller asked for `strategy.cop_class`, which no file contains. Nothing
    failed: `Config.get` answers None for an absent path and `load_brain` reads
    None as "use the baseline", so a config naming a strategy was obeyed by
    nobody and a graded match would have fielded the shipped baseline.
    """
    assert CONFIG_KEYS == {"cop": "strategy.police_class", "thief": "strategy.thief_class"}


@cop_only
def test_a_configured_strategy_is_actually_fielded() -> None:
    """The lookup and the key have to agree, which is what silently failed."""
    named = Config(**{"strategy.police_class": "police.advanced:AdvancedCop"})
    assert type(brain_for("cop", named)).__name__ == "AdvancedCop"
    assert isinstance(brain_for("cop", Config()), PoliceBrain)


@pytest.mark.parametrize(
    "spec,message",
    [
        ("police.brain.PoliceBrain", "not a valid strategy path"),
        ("nope.missing:Brain", "cannot import"),
        ("police.brain:NoSuchBrain", "has no class named"),
        ("core.domain.board:Board", "not a BrainBase subclass"),
    ],
)
@cop_only
def test_a_bad_path_fails_at_startup_not_mid_match(spec: str, message: str) -> None:
    """A typo found on turn one is a technical loss worth 0 to both teams."""
    with pytest.raises(BrainLoadError, match=message):
        load_brain(spec, "cop")


def test_an_unknown_role_with_no_spec_is_refused() -> None:
    with pytest.raises(BrainLoadError, match="no default for role"):
        load_brain("", "referee")
