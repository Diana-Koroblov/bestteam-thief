"""Repository paths that survive the role split.

The working tree holds both roles, but each *published* repository holds exactly
one: ``bestteam-cop`` ships ``config/police/`` and ``bestteam-thief`` ships
``config/thief/``, and each forbids the other (ADR-001, M#2). So a test that
names a role directory literally passes here and fails in CI on at least one of
the two repositories — at import time, which takes the whole suite down rather
than one test.

Everything below therefore derives from what is actually present. Tests
parametrise over ``PRESENT_ROLES`` and skip cross-role comparisons when only one
role is available.
"""

from __future__ import annotations

import json
from pathlib import Path

__all__ = [
    "REPO_ROOT",
    "CONFIG_ROOT",
    "ALL_ROLES",
    "PRESENT_ROLES",
    "role_dir",
    "shared_config",
    "brain_class",
    "needs_brain",
]

REPO_ROOT = Path(__file__).resolve().parents[1]

CONFIG_ROOT = REPO_ROOT / "config"

ALL_ROLES: tuple[str, ...] = ("police", "thief")

PRESENT_ROLES: tuple[str, ...] = tuple(
    role for role in ALL_ROLES if (CONFIG_ROOT / role / "game.json").is_file()
)

if not PRESENT_ROLES:  # pragma: no cover - a broken checkout, not a code path
    raise RuntimeError(
        f"no role configuration found under {CONFIG_ROOT}. Every repository must ship "
        "at least one of config/police/game.json or config/thief/game.json."
    )


def role_dir(role: str) -> Path:
    """Return the configuration directory for *role*."""
    return CONFIG_ROOT / role


def shared_config(role: str | None = None) -> dict:
    """Return the parsed shared contract for *role*, or for any present role.

    The shared file is byte-identical across roles by construction, so when the
    caller does not care which one it gets, the first present role is fine.
    """
    return json.loads((role_dir(role or PRESENT_ROLES[0]) / "game.json").read_text("utf-8"))


# The role package each role's brain lives in.
_BRAIN_MODULES = {"police": ("police.brain", "PoliceBrain"), "thief": ("thief.brain", "ThiefBrain")}


def brain_class(role: str):
    """Return the brain class for *role*, or None when that role is not shipped.

    A published repository holds one role package, so importing the other at
    module level takes the whole suite down at collection — the same failure
    the split-repository gate caught for `config/` paths. Tests ask for a class
    and skip when it is absent.
    """
    module_name, class_name = _BRAIN_MODULES[role]
    try:
        module = __import__(module_name, fromlist=[class_name])
    except ImportError:
        return None
    return getattr(module, class_name, None)


def needs_brain(role: str):
    """Return a skip marker for tests that require *role*'s brain."""
    import pytest

    return pytest.mark.skipif(
        brain_class(role) is None,
        reason=f"the {role!r} package is not published to this repository (ADR-001)",
    )
