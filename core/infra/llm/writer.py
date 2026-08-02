"""Turns a brain's chosen intent into a legal hint (TODO 4.3.5-4.3.9, 4.5.1).

This is the layer that makes the verbal channel safe to plug into commit-reveal.
It guarantees exactly one thing, and everything else is arranged around it:

    **A hint always comes back, and it is always legal.**

A hint goes out every single turn, because it is sealed into the commit record
together with the Intent flag (Ch. 5.3.1) — a turn without one would break
commit-reveal outright. So there is no error path here. Provider down, model
slow, model ignored its instructions, model leaked a coordinate: each ends at
the template bank rather than at an exception.

**The brain decides truth or lie, never the model** (4.5.1, Ch. 5). The model
receives the decision as an instruction. Letting an LLM choose would put the
most strategic call in the game in the hands of the one component we cannot
test, replay or hold to a policy.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.domain.intent import Intent
from core.infra.llm.base import TextProvider
from core.infra.llm.safety import cap_words, violations
from core.infra.llm.template import TemplateProvider

__all__ = ["HintWriter", "WrittenHint", "build_prompt"]

MAX_ATTEMPTS = 2


@dataclass(frozen=True)
class WrittenHint:
    """The hint and the audit trail of how it was produced.

    Attributes:
        text: What we send. Always non-empty and always legal.
        intent: What the brain decided. Recorded because the reveal must show
            it, and because our own honesty rate is worth measuring.
        provider: Who actually wrote it — ``template`` here after a fallback
            even when the config selected ``groq``, which is the only way to
            notice a provider that has been quietly failing all series.
        rejected: Rules broken by discarded drafts. Empty on a clean first pass.
    """

    text: str
    intent: Intent
    provider: str
    rejected: tuple[str, ...] = ()


def build_prompt(direction: str, intent: Intent, step: int, map_area: str = "") -> str:
    """Compose the instruction sent to whichever provider is active.

    Args:
        direction: The compass word to convey — already resolved to a truth or
            a bluff by the brain.
        intent: Recorded and revealed later; the model is told the *content*,
            not asked to choose it.
        step: Included so the template bank's hash varies turn to turn.
        map_area: Optional landmark flavour, Appendix F (4.3.10).

    The prompt never contains our own position, the opponent's believed
    position, or any number that could be read as a coordinate. A prompt that
    carried them would eventually see them echoed back into the hint.
    """
    # **Landmarks are forbidden unless a shared map_area was negotiated.**
    # Left to itself the model invents them, and they are worse than useless —
    # they are a leak. Observed live: turn 1 said "heading north towards the old
    # warehouse" truthfully, and turn 3, instructed to reveal nothing, said
    # "near the old warehouse". Nothing in that sentence names a direction, so
    # every rule passes; but an opponent who paired "warehouse" with "north" on
    # turn 1 reads turn 3 as north anyway. The model had built a private
    # codebook out of its own flavour text, and we would be leaking through a
    # channel we neither chose nor audit.
    flavour = (
        f" Reference real landmarks in {map_area}."
        if map_area
        else " Use no place names or landmarks of any kind."
    )
    # The negative instruction deliberately does **not** spell out the compass
    # points. An earlier version read "Do NOT mention north, south, east or
    # west", and the template provider — which picks its bank by scanning the
    # prompt for a direction — matched on the word "north" inside the very
    # instruction forbidding it, and answered with a northward taunt.
    aim = (
        f"You MUST use the word '{direction}' to say you are moving {direction}"
        if direction
        else "Reveal nothing whatsoever about which way you are going"
    )
    return (
        f"Turn {step}. Taunt your opponent in one sentence. {aim}."
        f"{flavour} No numbers, no coordinates."
    )


class HintWriter:
    """Produces a legal hint every turn, degrading rather than failing."""

    def __init__(
        self,
        provider: TextProvider | None = None,
        max_words: int = 15,
        forbidden: tuple[str, ...] = (),
        allow_fallback: bool = True,
    ) -> None:
        self.provider = provider or TemplateProvider()
        self.fallback = TemplateProvider()
        self.max_words = max_words
        self.forbidden = forbidden
        self.allow_fallback = allow_fallback

    def write(self, direction: str, intent: Intent, step: int, map_area: str = "") -> WrittenHint:
        """Return a hint that has passed every rule in ``safety.py``."""
        prompt = build_prompt(direction, intent, step, map_area)
        rejected: list[str] = []

        for _ in range(MAX_ATTEMPTS):
            try:
                draft = self.provider.generate(prompt, self.max_words)
            except Exception as error:  # noqa: BLE001 - the guarantee, see module docstring
                # Providers are *supposed* to raise only ProviderError, and the
                # ones we ship do. This clause is for the one that does not:
                # a third-party stack raising from a constructor, a provider
                # written later, a typo in a subclass. Trusting the contract
                # here would make the guarantee depend on every future
                # implementer remembering it.
                rejected.append(f"{type(error).__name__}: {error}")
                break

            draft = cap_words(draft, self.max_words)
            broken = violations(draft, self.max_words, self.forbidden, direction)
            if not broken:
                return WrittenHint(draft, intent, self.provider.name, tuple(rejected))
            rejected.extend(broken)

        return self._fall_back(prompt, intent, rejected, direction)

    def _fall_back(
        self, prompt: str, intent: Intent, rejected: list[str], direction: str = ""
    ) -> WrittenHint:
        """Return a bank line, which is written to be legal by construction.

        If even this failed we would rather send a blunt fixed sentence than
        raise: an exception here forfeits the turn on the watchdog, and a dull
        taunt costs nothing at all.
        """
        if not self.allow_fallback and self.provider.name != "template":
            rejected.append("fallback disabled by config")
        text = cap_words(self.fallback.generate(prompt, self.max_words), self.max_words)
        if violations(text, self.max_words, self.forbidden, direction):
            text = "You are chasing a rumour, not an agent."
        return WrittenHint(text, intent, self.fallback.name, tuple(rejected))
