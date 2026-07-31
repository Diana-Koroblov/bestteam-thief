"""Load the strategy named in config, and fail **now** rather than mid-match.

`[strategy] police_class` / `thief_class` in ``package.module:Class`` form. An
empty setting falls back to the built-in baseline, so a fresh clone plays.

The important property is *when* a bad value is discovered. A typo resolved
lazily on the first turn would surface thirty seconds into a real match, and a
peer that crashes mid-turn takes a technical loss worth 0 to **both** teams. So
the class is imported and instantiated during startup, where the only cost of
being wrong is an error message.

This lives in the runtime because it is a join: it reads config and builds a
domain object. Neither of those subsystems may reach the other (M#3).
"""

from __future__ import annotations

from importlib import import_module

from core.domain.brain_base import BrainBase

__all__ = ["BrainLoadError", "DEFAULTS", "load_brain"]


class BrainLoadError(Exception):
    """A configured strategy could not be loaded. Always raised at startup."""


# The built-in baselines, used when the config says nothing.
DEFAULTS: dict[str, str] = {
    "cop": "police.brain:PoliceBrain",
    "thief": "thief.brain:ThiefBrain",
}


def load_brain(spec: str | None, role: str) -> BrainBase:
    """Return the brain named by *spec*, or the baseline for *role*.

    Args:
        spec: ``package.module:Class``. Empty or None selects the default.
        role: ``cop`` or ``thief``, used to pick the fallback.

    Returns:
        An instantiated brain.

    Raises:
        BrainLoadError: The spec is malformed, the module or class is missing,
            the class is not a ``BrainBase``, or it cannot be constructed. Every
            message names the spec, because the person reading it is looking at
            a config file and needs to know which line is wrong.
    """
    target = (spec or "").strip() or DEFAULTS.get(role)
    if not target:
        raise BrainLoadError(f"no brain configured and no default for role {role!r}")

    if ":" not in target:
        raise BrainLoadError(
            f"{target!r} is not a valid strategy path; expected 'package.module:Class'"
        )

    module_name, _, class_name = target.partition(":")
    try:
        module = import_module(module_name)
    except ImportError as error:
        raise BrainLoadError(f"cannot import {module_name!r} for {target!r}: {error}") from error

    brain_class = getattr(module, class_name, None)
    if brain_class is None:
        raise BrainLoadError(f"{module_name!r} has no class named {class_name!r}")
    if not (isinstance(brain_class, type) and issubclass(brain_class, BrainBase)):
        raise BrainLoadError(f"{target!r} is not a BrainBase subclass")

    try:
        return brain_class(name=class_name)
    except Exception as error:  # noqa: BLE001 - re-raised as a startup failure
        raise BrainLoadError(f"{target!r} could not be constructed: {error}") from error
