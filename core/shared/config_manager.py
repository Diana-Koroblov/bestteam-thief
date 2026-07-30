"""Loading, merging and fingerprinting a peer's configuration.

A peer holds two files. ``game.json`` is the **shared** contract: after the
handshake it must be byte-identical on both machines, and its digest is what the
two peers exchange to prove it (M#11). ``game.toml`` is **private**: the local
ngrok domain, the LLM provider, UI preferences — things the opponent neither
sees nor agrees to.

They are merged with the shared file on top. That direction is deliberate: a
private preference can fill a gap, but it can never quietly override a value
both teams agreed on. The reverse ordering would let a local edit change the
physics of a match while the digest still matched, which is the whole class of
failure this project scores 0 for.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.crypto.canonical import digest
from core.shared import config_spec, version

if sys.version_info >= (3, 11):  # pragma: no cover - depends on the interpreter
    import tomllib
else:  # pragma: no cover - depends on the interpreter
    import tomli as tomllib

__all__ = ["ConfigError", "ConfigVersionError", "ConfigRuleError", "Config", "load_config"]


class ConfigError(Exception):
    """A configuration file is missing, unreadable or malformed."""


class ConfigVersionError(ConfigError):
    """A configuration file was written for an incompatible code version."""


class ConfigRuleError(ConfigError):
    """A configuration file breaches Appendix F."""


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Return *base* updated by *overlay*, recursing into nested dicts.

    Scalars and lists are replaced wholesale; only mappings are merged. Merging
    lists would silently blend two move sets into a third that neither peer
    agreed to play with.
    """
    merged = dict(base)
    for key, value in overlay.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(current, value)
        else:
            merged[key] = value
    return merged


@dataclass(frozen=True)
class Config:
    """A loaded configuration.

    Attributes:
        shared: The negotiated contract, exactly as parsed from ``game.json``.
        private: Local-only settings from ``game.toml``.
        merged: ``private`` with ``shared`` layered on top; what the game reads.
    """

    shared: dict
    private: dict
    merged: dict

    def get(self, path: str, default: Any = None) -> Any:
        """Return the merged value at a dotted *path*, e.g. ``scoring.tie_score``."""
        return config_spec.dotted_get(self.merged, path, default)

    def require(self, path: str) -> Any:
        """Return the merged value at *path*, raising ``ConfigError`` if absent."""
        value = config_spec.dotted_get(self.merged, path, None)
        if value is None:
            raise ConfigError(f"required configuration key is missing: {path}")
        return value

    def shared_digest(self) -> str:
        """Return the SHA-256 of the shared contract, for the M#11 exchange.

        Only ``shared`` is hashed. Including private settings would make two
        correctly-agreed peers disagree, because their ngrok domains differ.
        """
        return digest(self.shared)


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ConfigError(f"missing shared configuration: {path}") from error
    except json.JSONDecodeError as error:
        raise ConfigError(f"{path} is not valid JSON: {error}") from error


def _read_toml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{path} is not valid TOML: {error}") from error


def load_config(role_dir: Path, *, enforce_rules: bool = True) -> Config:
    """Load, merge and validate the configuration in *role_dir*.

    Args:
        role_dir: Directory holding ``game.json`` and optionally ``game.toml``.
        enforce_rules: When True, refuse to return a config that breaches
            Appendix F. Set False only to inspect an opponent's proposal so the
            violations can be quoted back at them.

    Raises:
        ConfigError: The files are missing or malformed.
        ConfigVersionError: ``game.json`` declares an incompatible version.
        ConfigRuleError: The merged config breaches Appendix F.
    """
    role_dir = Path(role_dir)
    shared = _read_json(role_dir / "game.json")
    private = _read_toml(role_dir / "game.toml")

    declared = str(shared.get("version", ""))
    if not version.is_compatible(declared):
        raise ConfigVersionError(
            f"{role_dir / 'game.json'} declares version {declared or '<none>'}, "
            f"which this code (version {version.VERSION}) cannot read"
        )

    merged = _deep_merge(private, shared)
    if enforce_rules:
        found = config_spec.violations(merged) + config_spec.invariant_violations(merged)
        if found:
            raise ConfigRuleError("configuration is not playable:\n  " + "\n  ".join(found))
    return Config(shared=shared, private=private, merged=merged)
