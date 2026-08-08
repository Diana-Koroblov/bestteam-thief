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

__all__ = ["BrainLoadError", "DEFAULTS", "CONFIG_KEYS", "load_brain", "brain_for"]


class BrainLoadError(Exception):
    """A configured strategy could not be loaded. Always raised at startup."""


# The built-in baselines, used when the config says nothing.
DEFAULTS: dict[str, str] = {
    "cop": "police.brain:PoliceBrain",
    "thief": "thief.brain:ThiefBrain",
}

# Where each role's strategy is named in `game.toml`. **One definition**, because
# until this existed the key had none: Appendix B.4 and `[strategy]` in our own
# config both call it `police_class`, and every caller asked for
# `strategy.cop_class` — a key no file contains. The lookup missed silently, the
# fallback returned the baseline, and a config that named a strategy was
# obeyed by nobody.
#
# Note the asymmetry, which is where the drift came from: the *role* is `cop`
# (`Role.COP.value`, and the key into DEFAULTS) while the *config key* says
# `police`, because Appendix B.4 spells it that way and the shared vocabulary
# wins over our own.
CONFIG_KEYS: dict[str, str] = {
    "cop": "strategy.police_class",
    "thief": "strategy.thief_class",
}


def load_brain(spec: str | None, role: str, config: object = None) -> BrainBase:
    """Return the brain named by *spec*, or the baseline for *role*.

    Args:
        spec: ``package.module:Class``. Empty or None selects the default.
        role: ``cop`` or ``thief``, used to pick the fallback.
        config: Passed to ``BrainBase.configure`` when supplied, so a strategy
            can read its own `[strategy]` keys — search depth, weights,
            thresholds. Optional because the fallback baselines need none, and a
            brain that could not be built without config would be unusable as
            the fallback for a config that failed to load.

    Returns:
        An instantiated brain, already configured.

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
        brain = brain_class(name=class_name)
        if config is not None:
            brain.configure(config)
    except Exception as error:  # noqa: BLE001 - re-raised as a startup failure
        raise BrainLoadError(f"{target!r} could not be constructed: {error}") from error
    return brain


def brain_for(role: str, config) -> BrainBase:
    """Return the brain *config* names for *role*, or the shipped baseline.

    Args:
        role: ``cop`` or ``thief`` — the role, not the configuration directory.

    The one place the `[strategy]` key is read. A caller that spelled it inline
    got no error for spelling it wrong: `Config.get` returns None for an absent
    path, `load_brain` reads None as "use the default", and the result is a peer
    playing a strategy nobody chose. See `CONFIG_KEYS`.
    """
    return load_brain(config.get(CONFIG_KEYS[role]), role, config)
