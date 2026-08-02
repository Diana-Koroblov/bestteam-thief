"""State persistence, so a killed process leaves evidence (TODO 6.4.4).

The watchdog calls this before shutting down, and that ordering is the whole
point: **losing a sub-game is survivable; losing the evidence is not.** The
end-of-match audit is what proves we played honestly, and it can only run over a
log that reached the disk.

Three properties, each protecting against a way a crash-time write goes wrong:

* **Atomic.** Write to a temporary file, then ``os.replace``, which is atomic on
  both Windows and POSIX. A process dying mid-write would otherwise leave a
  half-written JSON file — and a truncated snapshot is worse than none, because
  it looks recoverable right up until it is parsed.
* **UTF-8, explicitly.** Team names and hints may be Hebrew, and a Windows
  console defaults to cp1252. We already lost an afternoon to that in 6.5.2.
* **Never raises.** This runs *during* a failure. An exception here would
  replace a recorded technical loss with an unhandled traceback, and lose the
  original reason along with it.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

__all__ = ["save", "load", "SNAPSHOT_NAME"]

SNAPSHOT_NAME = "snapshot.json"


def save(state: dict[str, Any], directory: Path, name: str = SNAPSHOT_NAME) -> Path | None:
    """Write *state* atomically. Returns the path, or None if it could not.

    Args:
        state: Anything JSON-serialisable — the phase history, the step log,
            the reason we are shutting down.
        directory: Where to write. Created if missing.
        name: Filename, so a test or a second sub-game can use its own.

    Returns None rather than raising on failure. The caller is already handling
    a technical loss; a disk error must not become the thing that crashes the
    shutdown path and destroys the reason we were shutting down.
    """
    try:
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / name
        temporary = directory / f"{name}.tmp"

        # `ensure_ascii=False` keeps Hebrew readable in the file; the explicit
        # UTF-8 encoding is what makes that safe on Windows.
        temporary.write_text(
            json.dumps(state, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(temporary, target)
        return target
    except (OSError, TypeError, ValueError):
        return None


def load(directory: Path, name: str = SNAPSHOT_NAME) -> dict[str, Any] | None:
    """Read a snapshot back, or None if there is not a usable one.

    A missing file and a corrupt file both return None on purpose. The caller's
    response is identical — start fresh — and a corrupt snapshot is exactly what
    a crash during an *older*, non-atomic write would have left behind.
    """
    try:
        loaded = json.loads((directory / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return loaded if isinstance(loaded, dict) else None
