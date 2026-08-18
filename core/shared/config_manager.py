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

__all__ = [
    "ConfigError",
    "ConfigVersionError",
    "ConfigRuleError",
    "Config",
    "load_config",
    "SCHEMA_VERSION",
]

# The **file format** published in Appendix B.3, which is a different thing from
# `version` below and has to be, because they answer different questions:
#
#   schema_version — "which layout is this file written in?" The opponent's
#       question. It is the book's field, with the book's value, and it is why
#       both are carried: a peer that builds to Appendix B.3 looks for this key
#       by name and would not recognise ours.
#   version        — "which code wrote it?" Ours. It gates `is_compatible` and
#       has nothing to do with the opponent, who is entirely free to run code at
#       any version of their own.
#
# Compatibility is by major version here too: a 2.x schema has moved a key we
# read, and guessing which one during a graded match is not a risk worth taking.
SCHEMA_VERSION = "1.2"


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

    @property
    def agreed_between(self) -> list[str]:
        """Return the parties named in the shared contract (Appendix B.3).

        A list of one is our unsigned **proposal**; a signed contract names both
        teams. `PreMatch.warnings` says so out loud before a match, because the
        failure mode is filing a config snapshot that never records who agreed
        to it — and a contract with one signature is the thing a dispute is
        least able to survive.
        """
        found = self.shared.get("agreed_between", [])
        return [str(name) for name in found] if isinstance(found, list) else []

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

    # Shared first, then private, and **absent is accepted** — exactly as
    # `schema_version` is accepted absent twenty lines below, and for the same
    # reason stated there: refusing over a missing label forfeits a fixture while
    # proving nothing.
    #
    # After imreeyal's counted checklist (item 9) the agreed contract is the
    # 9-key Appendix F shape, which carries no `version` at all — theirs never
    # did, and ours carrying it was the whole of our canonical digest mismatch
    # (17606f14 against their cca1243e) over content that differed in no rule.
    # A gate that refused an absent version would now refuse every
    # kit-conformant peer's contract, including the one we just agreed to.
    #
    # What is still refused is a **stated** incompatible version, which is a
    # claim rather than a silence — the same distinction `schema_version` draws.
    # Ours moved to the private file, so our own load still reads "1.00".
    declared = str(shared.get("version", private.get("version", "")))
    if declared and not version.is_compatible(declared):
        raise ConfigVersionError(
            f"{role_dir / 'game.json'} declares version {declared}, "
            f"which this code (version {version.VERSION}) cannot read"
        )

    # Absent is accepted: an opponent's file may predate Appendix B.3's field or
    # simply omit it, and refusing over a missing label would forfeit a fixture
    # while proving nothing. A *stated* incompatible layout is a different claim
    # and is refused.
    schema = str(shared.get("schema_version", SCHEMA_VERSION))
    if schema.split(".")[0] != SCHEMA_VERSION.split(".")[0]:
        raise ConfigVersionError(
            f"{role_dir / 'game.json'} declares schema_version {schema}, but this code "
            f"reads the Appendix B.3 layout {SCHEMA_VERSION}; a different major schema "
            "has moved a key we depend on"
        )

    merged = _deep_merge(private, shared)
    if enforce_rules:
        found = config_spec.violations(merged) + config_spec.invariant_violations(merged)
        if found:
            raise ConfigRuleError("configuration is not playable:\n  " + "\n  ".join(found))
    return Config(shared=shared, private=private, merged=merged)
