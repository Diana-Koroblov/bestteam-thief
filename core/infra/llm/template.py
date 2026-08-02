"""The template bank: a hint every turn, at zero tokens (TODO 4.3.2).

The book's own default, and ours (Appendix F). It matters far more than
"fallback" suggests:

* It is the **floor**. In template or ollama mode the whole 6-sub-game series
  costs nothing, and the contest reduces to movement-algorithm quality — which
  is where our belief filter and expectimax live.
* It is the **safety net**. Every provider error, timeout or killed Ollama
  lands here (ADR-003), so no verbal failure can ever forfeit a turn.
* It is **deterministic**. Two peers replaying the same log must produce the
  same text, so selection is by hash of the prompt, never by ``random``.

The bank speaks in landmarks and directions, never in numbers — the coordinate
scanner runs over template output too, and these lines are written to pass it.
"""

from __future__ import annotations

from hashlib import sha256

from core.infra.llm.base import TextProvider

__all__ = ["TemplateProvider", "BANK", "DIRECTIONS"]

DIRECTIONS: tuple[str, ...] = ("north", "south", "east", "west")

# Keyed by the direction the *brain* decided to convey. Whether that direction
# is the truth or a bluff was settled before this module was called (4.5.1) —
# the bank cannot tell, and must not be able to.
BANK: dict[str, tuple[str, ...]] = {
    "north": (
        "Heading up and north, and you are already too slow.",
        "The northern edge is calling me. Try to keep up.",
        "I drift north while you guess at shadows.",
    ),
    "south": (
        "Going south, low and quiet. You will not follow.",
        "The southern side suits me better today.",
        "South, and unhurried. Your move.",
    ),
    "east": (
        "Eastward now. The far side is friendlier.",
        "I lean east, where your trail runs thin.",
        "East it is. Catch me if the board allows.",
    ),
    "west": (
        "West, into the quiet corner. Good luck.",
        "Drifting west while you read the wrong scent.",
        "The western edge suits my plans nicely.",
    ),
    "": (
        "You are chasing a rumour, not an agent.",
        "Nothing you have read this turn was worth reading.",
        "I am somewhere you have not thought to look.",
    ),
}


class TemplateProvider(TextProvider):
    """Picks a line from the bank. No network, no model, no tokens."""

    name = "template"

    def generate(self, prompt: str, max_words: int) -> str:
        """Return a hint matching whichever direction *prompt* asks for.

        Selection is by SHA-256 of the prompt rather than ``random`` so that a
        replay reproduces the exact text. The prompt changes every turn (it
        carries the step number), so the bank still varies turn to turn without
        ever varying between two runs of the same game.
        """
        bank = BANK[_direction_in(prompt)]
        index = int(sha256(prompt.encode("utf-8")).hexdigest(), 16) % len(bank)
        return bank[index]


def _direction_in(prompt: str) -> str:
    """Return the compass word the prompt asks for, or "" for a generic taunt.

    A missing direction is not an error. Early turns, and turns where the belief
    is too flat to justify pointing anywhere, deliberately say nothing useful —
    and saying nothing useful is itself a legitimate move in the verbal game.
    """
    lowered = prompt.lower()
    for direction in DIRECTIONS:
        if direction in lowered:
            return direction
    return ""
