"""The guard rails every hint passes through, whoever wrote it.

**This module is the reason the verbal channel cannot lose us the match.** Three
independent rules, applied to template output and model output alike:

* **The word cap** (Appendix F, ``max_words = 15``). A negotiated limit, so an
  over-long hint is a protocol violation, not a style problem.
* **The coordinate scanner** (M#27). The book requires *free natural language*;
  a hint that leaks ``(3,4)`` turns the verbal game into a structured position
  protocol and forfeits the part of the grade that rewards inference.
* **The fabrication ban** (Appendix F ``never_fabricate``). Capture claims,
  barrier placements, scent fields and game counts are **audited**. A lie about
  any of them scores 0 *for both teams* — so this is the one place where our own
  deception policy is overruled by the rulebook.

The scanner runs **outbound**, on our own text, before it is sealed into the
commit. Catching it here means regenerating a sentence; catching it in the audit
means losing the series.
"""

from __future__ import annotations

import re

__all__ = [
    "COORD_PATTERNS",
    "FORBIDDEN_CLAIMS",
    "COMPASS",
    "leaks_coordinates",
    "cap_words",
    "conveys",
    "violations",
]

# The only vocabulary both peers are guaranteed to share. A model left to itself
# reaches for "the mountains" or "the river" — evocative, and useless: there is
# no map, so the opponent's parser cannot turn a river into a direction.
COMPASS: tuple[str, ...] = ("north", "south", "east", "west")

# Ported from HW6's `_COORD_RE` and widened. Each pattern is a way a model has
# actually been observed to smuggle a position into "free" text.
COORD_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"[(\[]\s*\d+\s*[,;]\s*\d+\s*[)\]]"),  # (3,4)  [3; 4]
    re.compile(r"\b\d+\s*[,;]\s*\d+\b"),  # 3,4  bare
    re.compile(r"\b(?:row|col|column|rank|file)\s*\.?\s*#?\s*\d+", re.I),  # row 3
    re.compile(r"\b(?:cell|square|tile|position|coord\w*)\s*\.?\s*#?\s*\d+", re.I),
    re.compile(r"\b\d+\s*[-–/]\s*\d+\b"),  # 3-4  3/4
    re.compile(r"\bat\s+\d+\s+\d+\b", re.I),  # at 3 4
)

# Appendix F `never_fabricate`, as language rather than as config keys. A hint
# may bluff about direction all it likes; it may not claim any of these.
FORBIDDEN_CLAIMS: dict[str, tuple[str, ...]] = {
    "capture": ("i caught", "i have caught", "you are caught", "i captured", "got you"),
    "barriers": ("i walled", "i have placed", "i sealed you", "i blocked every"),
    "scent": ("my scent reads", "your trail shows", "the field says"),
    "game_count": ("i have won", "we are ahead", "the series stands"),
}


def leaks_coordinates(text: str) -> bool:
    """Return True if *text* contains anything readable as a board coordinate.

    Deliberately over-eager. A false positive costs one regeneration; a false
    negative costs the free-language requirement the grade rewards (M#26).
    """
    return any(pattern.search(text) for pattern in COORD_PATTERNS)


def cap_words(text: str, limit: int) -> str:
    """Truncate *text* to *limit* words at a word boundary.

    Truncation is the fallback, not the plan — the model is asked for brevity
    first. But an over-long hint is a violation of a *negotiated* value, so it
    can never be allowed to leave the process merely because a model ignored
    its instructions.
    """
    words = text.split()
    if len(words) <= limit:
        return text.strip()
    return " ".join(words[:limit]).rstrip(",;:-") + "."


def conveys(text: str, direction: str) -> bool:
    """Return whether *text* actually carries the direction it was asked to.

    **The hint's entire job.** A taunt that mentions no direction informs nobody
    when truthful and deceives nobody when a lie — it is a turn of the verbal
    game spent saying nothing, and the parser on the other side has nothing to
    read. Landmarks do not count: with no shared map, "the river" is noise.

    An empty *direction* inverts the test. When the brain decided to give
    nothing away, a compass word leaking into the text is the failure.

    Matching is on the **stem**, not the exact word. The first version required
    an exact match and was wrong in both directions at once: it rejected
    "the northern edge" as saying nothing about north, while letting that same
    phrase through as a supposedly direction-free hint. "northward", "westerly"
    and "southbound" all carry a direction to any reader, so they must count.
    """
    lowered = text.lower()
    found = {point for point in COMPASS if re.search(rf"\b{point}\w*", lowered)}
    return not found if not direction else direction.lower() in found


def violations(
    text: str, max_words: int, forbidden: tuple[str, ...] = (), direction: str | None = None
) -> list[str]:
    """Return every rule *text* breaks, empty if it is safe to send.

    Args:
        text: The candidate hint.
        max_words: Appendix F's ``max_words``.
        forbidden: Which ``never_fabricate`` categories are in force.
        direction: The compass word the brain asked for, ``""`` for a
            deliberately empty hint, or None to skip the check entirely.

    Returns a list rather than raising: the caller regenerates and wants to tell
    the model everything that was wrong, not just the first thing.
    """
    found: list[str] = []
    if not text.strip():
        found.append("empty hint")
    if len(text.split()) > max_words:
        found.append(f"over the {max_words}-word cap")
    if leaks_coordinates(text):
        found.append("leaks a board coordinate (M#27)")

    if direction is not None and not conveys(text, direction):
        found.append(
            f"says nothing about '{direction}'" if direction else "leaks a direction"
        )

    lowered = text.lower()
    for category in forbidden:
        for phrase in FORBIDDEN_CLAIMS.get(category, ()):
            if phrase in lowered:
                found.append(f"fabricates a '{category}' claim, which is audited")
                break
    return found
