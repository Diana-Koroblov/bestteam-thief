"""Game identifiers and the filenames derived from them (TODO 7.2.5).

Every artefact a match produces is named from one shared ``game_id``, so files
from two different matches can never collide — including in the grader's inbox,
where reports from ten teams land side by side.

**The id is agreed, not generated locally.** Two peers each rolling their own
would produce two ids for one match, and the pair of reports would look like two
separate games that each side won. So it is derived from values both peers
already agree on at Step-0: the two team names and the match date, sorted.

That derivation has a useful property nobody has to remember — it is
**symmetric**. Whichever peer computes it first, both get the same answer,
because the team names are sorted before hashing rather than taken in the order
the local peer happens to hold them.
"""

from __future__ import annotations

import re
from hashlib import sha256

__all__ = ["game_id", "artefact_name", "SAFE_PATTERN"]

# Filenames end up in an email attachment and on two operating systems, so the
# character set is deliberately narrow.
SAFE_PATTERN = re.compile(r"[^A-Za-z0-9_.-]")


def game_id(team_a: str, team_b: str, date: str) -> str:
    """Return the shared identifier for one match.

    Args:
        team_a: One team name.
        team_b: The other. **Order does not matter** — see below.
        date: ``YYYY-MM-DD`` of the match.

    Both peers compute this independently and must agree, so the names are
    sorted first. Taking them in local order would give the Cop and the Thief
    different ids for the same match, and the two reports would read as two
    separate games.
    """
    first, second = sorted([team_a.strip().lower(), team_b.strip().lower()])
    # Hashed from the ORIGINAL names, before sanitising. Two team names written
    # entirely in a non-Latin script both sanitise to nothing, so hashing the
    # sanitised form would give two different matches the same id — exactly the
    # collision this function exists to prevent.
    fingerprint = sha256(f"{first}|{second}|{date}".encode()).hexdigest()[:8]
    return _safe(f"{date}_{_label(first)}-vs-{_label(second)}_{fingerprint}")


def _label(name: str) -> str:
    """Return a filename-safe label for one team, never empty.

    A team name written entirely in a non-Latin script sanitises to an empty
    string, which would produce ``2026-08-12_-vs-_9733af2a`` — unique, thanks to
    the fingerprint, and unreadable. Falling back to a short hash of the name
    keeps the two sides distinguishable at a glance in a directory listing.
    """
    cleaned = _safe(name)
    return cleaned or f"team{sha256(name.encode()).hexdigest()[:6]}"


def artefact_name(kind: str, identifier: str, sub_game: int | None = None) -> str:
    """Return the filename for one artefact.

    Args:
        kind: ``declaration``, ``config``, ``log`` or ``result``.
        identifier: The shared ``game_id``.
        sub_game: 1-6 for per-sub-game artefacts; None for whole-match ones.

    The sub-game number is zero-padded so a directory listing sorts correctly.
    ``g10`` before ``g2`` is the kind of thing nobody notices until they are
    reading twelve files at midnight looking for the one that failed.
    """
    suffix = f"_g{sub_game:02d}" if sub_game is not None else ""
    return _safe(f"{kind}_{identifier}{suffix}.json")


def _safe(name: str) -> str:
    """Replace anything outside the safe set, and collapse repeats.

    Team names are chosen by students and may contain spaces, punctuation or
    non-Latin characters. All of those are legal in a team name and none of them
    belong in a filename that has to survive an email attachment and two
    filesystems.
    """
    return re.sub(r"_{2,}", "_", SAFE_PATTERN.sub("_", name)).strip("_")
