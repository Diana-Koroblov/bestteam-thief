"""Immutable project constants.

Only values that are structurally fixed by the rulebook or the excellence guide
live here. Anything a match may negotiate belongs in ``config/<role>/game.json``;
anything private to one peer belongs in ``config/<role>/game.toml``.

Rule of thumb (excellence guide §7.2): if a reviewer could plausibly want to
change it without changing the rules, it is configuration, not a constant.
"""

from __future__ import annotations

__all__ = [
    "MAX_FILE_LOC",
    "SOURCE_ROOTS",
    "EXCLUDED_DIR_NAMES",
]

# Excellence guide §3.2: no source file may exceed 150 lines of code.
# Blank lines and comment lines do not count. See core/shared/loc_counter.py
# for the exact counting rules and the documented docstring interpretation.
MAX_FILE_LOC = 150

# Directories walked by the file-size guard.
SOURCE_ROOTS = ("core", "police", "thief", "tests", "scripts")

# Never walked, regardless of location.
EXCLUDED_DIR_NAMES = frozenset(
    {
        "__pycache__",
        ".venv",
        "venv",
        ".git",
        ".ruff_cache",
        ".pytest_cache",
        "build",
        "dist",
    }
)
