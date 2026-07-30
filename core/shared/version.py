"""Single source of truth for the code version.

The excellence guide (§8.1) requires explicit version tracking in both the code
and every configuration file, starting at 1.00. The startup check refuses to run
when a config file was written for a different major version, because a silently
mismatched config is how two peers end up enforcing different physics.
"""

from __future__ import annotations

__all__ = ["VERSION", "MAJOR", "is_compatible"]

VERSION = "1.00"

MAJOR = VERSION.split(".")[0]


def is_compatible(config_version: str) -> bool:
    """Return True when *config_version* may be loaded by this code version.

    Compatibility is by major version: 1.00 code reads any 1.xx config. A change
    that alters the meaning of an existing key must bump the major version, so
    that an old config fails loudly instead of being misread.
    """
    return str(config_version).split(".")[0] == MAJOR
