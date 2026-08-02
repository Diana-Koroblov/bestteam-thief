"""The hint writer (TODO 4.3.1-4.3.9, 4.5.1, 4.6.3).

One guarantee holds every test here together: **a legal hint always comes back.**
A hint is sealed into the commit record with the Intent flag every single turn
(Ch. 5.3.1), so a turn without one breaks commit-reveal outright. There is no
error path — only degradation.

No test touches a live API (X §6.1).
"""

from __future__ import annotations

import pytest

from core.infra.llm.base import ProviderError, TextProvider
from core.infra.llm.template import BANK, TemplateProvider
from core.infra.llm.writer import HintWriter, build_prompt
from core.protocol.schemas import Intent

FORBIDDEN = ("capture", "barriers", "scent", "game_count")


class Broken(TextProvider):
    """A provider that always fails — Ollama killed mid-match (ADR-003)."""

    name = "broken"

    def generate(self, prompt: str, max_words: int) -> str:
        raise ProviderError("connection refused")


class Leaky(TextProvider):
    """A model that ignores its instructions and emits a coordinate."""

    name = "leaky"

    def generate(self, prompt: str, max_words: int) -> str:
        return "I am at (3,4), come and find me."


class Rambling(TextProvider):
    name = "rambling"

    def generate(self, prompt: str, max_words: int) -> str:
        return " ".join(f"word{n}" for n in range(40))


class Liar(TextProvider):
    name = "liar"

    def generate(self, prompt: str, max_words: int) -> str:
        return "I caught you already, give up."


class Exploding(TextProvider):
    """A provider that raises something nobody predicted.

    Not hypothetical. `httpx` raised `ImportError` while *constructing* its
    client — before any request — and sailed straight through a tidy
    `(HTTPError, KeyError, IndexError, ValueError)` clause, crashing the demo.
    """

    name = "exploding"

    def generate(self, prompt: str, max_words: int) -> str:
        raise ImportError("SOCKS proxy support is not installed")


# --- the guarantee ----------------------------------------------------------


def test_a_working_provider_is_used() -> None:
    hint = HintWriter(TemplateProvider()).write("north", Intent.TRUTH, 1)
    assert hint.provider == "template"
    assert hint.text in BANK["north"]


def test_a_dead_provider_degrades_instead_of_failing() -> None:
    """**ADR-003.** Killing Ollama mid-match costs quality, never the match.

    A raised exception here would forfeit the turn on the watchdog, which is a
    technical loss worth 0. A duller sentence costs nothing.
    """
    hint = HintWriter(Broken()).write("west", Intent.TRUTH, 3)
    assert hint.text
    assert hint.provider == "template"
    assert any("connection refused" in r for r in hint.rejected)


def test_a_leaked_coordinate_never_leaves_the_process() -> None:
    """M#27, enforced on model output rather than trusted to the prompt."""
    hint = HintWriter(Leaky()).write("east", Intent.LIE, 4)
    assert "(3,4)" not in hint.text
    assert hint.provider == "template"
    assert any("coordinate" in r for r in hint.rejected)


def test_an_over_long_generation_is_brought_under_the_cap() -> None:
    hint = HintWriter(Rambling(), max_words=15).write("south", Intent.TRUTH, 5)
    assert len(hint.text.split()) <= 15


def test_an_audited_claim_never_leaves_the_process() -> None:
    """Worth 0 to *both* teams, so it is caught before it is sealed."""
    hint = HintWriter(Liar(), forbidden=FORBIDDEN).write("north", Intent.LIE, 6)
    assert "caught" not in hint.text.lower()
    assert any("fabricates" in r for r in hint.rejected)


def test_every_provider_failure_still_produces_a_legal_hint() -> None:
    """The guarantee, stated once over every failure mode we can name."""
    for provider in (Broken(), Leaky(), Rambling(), Liar(), Exploding()):
        hint = HintWriter(provider, forbidden=FORBIDDEN).write("north", Intent.TRUTH, 7)
        assert hint.text and len(hint.text.split()) <= 15


def test_an_unforeseen_exception_type_still_degrades() -> None:
    """**The bug that a narrower `except` clause actually let through.**

    A listed-exceptions tuple is a bet that we can enumerate every way a
    third-party HTTP stack, a proxy layer and a remote JSON API can fail. We
    lost that bet on the first real run. The forfeit for losing it in a graded
    match is the whole match, and the fallback is identical either way — so the
    provider now catches everything.
    """
    hint = HintWriter(Exploding()).write("north", Intent.TRUTH, 8)
    assert hint.text
    assert hint.provider == "template"


def test_a_real_provider_wraps_arbitrary_failures() -> None:
    """The same guarantee at the provider boundary, not just the writer's."""
    from core.infra.llm.base import ProviderError
    from core.infra.llm.remote import GroqProvider

    provider = GroqProvider("nonexistent-model", timeout=0.001)
    with pytest.raises(ProviderError):
        provider.generate("hello", 15)


# --- who decides to lie -----------------------------------------------------


def test_the_intent_is_carried_through_untouched() -> None:
    """**4.5.1: the brain decides, the model is told** (Ch. 5).

    Letting an LLM choose whether to lie would put the most strategic call in
    the game inside the one component we cannot test, replay or hold to a
    policy — and it is sealed into the hash, so it must be reproducible.
    """
    assert HintWriter().write("north", Intent.LIE, 1).intent is Intent.LIE
    assert HintWriter().write("north", Intent.TRUTH, 1).intent is Intent.TRUTH


def test_the_prompt_never_reveals_a_position() -> None:
    """A prompt carrying coordinates would eventually see them echoed back."""
    from core.infra.llm.safety import leaks_coordinates

    for step in range(1, 40):
        assert not leaks_coordinates(build_prompt("north", Intent.TRUTH, step))


def test_the_prompt_does_not_announce_that_it_is_a_lie() -> None:
    """The word "lie" in a prompt invites a model to hedge, apologise or confess."""
    prompt = build_prompt("east", Intent.LIE, 2).lower()
    assert "lie" not in prompt and "deceiv" not in prompt


# --- determinism ------------------------------------------------------------


def test_the_same_turn_produces_the_same_text() -> None:
    """Both peers replay the same log, so nothing here may vary between runs."""
    texts = {HintWriter().write("north", Intent.TRUTH, 9).text for _ in range(10)}
    assert len(texts) == 1


def test_different_turns_produce_different_text() -> None:
    """Determinism must not collapse into repeating one sentence all series."""
    texts = {HintWriter().write("north", Intent.TRUTH, step).text for step in range(1, 12)}
    assert len(texts) > 1


def test_an_empty_direction_gives_away_nothing() -> None:
    """Saying nothing useful is a legitimate move when the belief is flat."""
    hint = HintWriter().write("", Intent.TRUTH, 2)
    assert hint.text in BANK[""]
    assert hint.provider == "template"


# --- 4.3.9: free language, structurally ------------------------------------


def test_the_hint_channel_carries_no_position_field() -> None:
    """**M#26, enforced against the schema rather than against good intentions.**

    The rulebook requires the verbal channel to be *free natural language*. The
    temptation under pressure is to add one small structured field — a hint
    direction enum, a distance integer — and each would quietly convert the
    inference problem into a position protocol, forfeiting the grade that
    rewards reading ambiguous text.

    Written as an **allowlist** rather than a type check, because the first
    version of this test looked for numeric fields and flagged `step` — a turn
    counter, not a position. A heuristic that cries wolf gets deleted. An
    allowlist instead fails on *any* new field, forcing whoever adds one to
    justify it here.

    `barrier_cell` is a coordinate and is allowed: a barrier is a public,
    audited board fact declared on the move channel, not a hint. The hint itself
    stays a bare `str`, with no structure to fill in.
    """
    from dataclasses import fields

    from core.protocol.schemas import Reveal

    allowed = {"step", "role", "move", "hint", "intent", "barrier_cell"}
    present = {f.name for f in fields(Reveal)}
    assert present == allowed, f"Reveal changed shape: {present ^ allowed}"

    hint_field = next(f for f in fields(Reveal) if f.name == "hint")
    assert hint_field.type in ("str", str), "the hint must stay free text"


def test_the_empty_instruction_does_not_name_the_directions_it_forbids() -> None:
    """**A prompt that defeats its own reader.**

    The template provider picks its bank by scanning the prompt for a compass
    word. An earlier instruction read "Do NOT mention north, south, east or
    west" — so the provider matched on the word "north" inside the very clause
    forbidding it, and produced a northward taunt when asked to reveal nothing.
    """
    from core.infra.llm.safety import COMPASS

    prompt = build_prompt("", Intent.TRUTH, 3).lower()
    assert not [point for point in COMPASS if point in prompt]


def test_landmarks_are_forbidden_when_no_map_area_was_negotiated() -> None:
    """**A leak that passes every other rule, seen in real Groq output.**

    Turn 1 said "heading north towards the old warehouse" — truthful, legal.
    Turn 3 was instructed to reveal nothing and said "near the old warehouse".
    No compass word, so the direction check passes. But an opponent who paired
    "warehouse" with "north" on turn 1 reads turn 3 as north regardless.

    The model had quietly built a **private codebook** out of its own flavour
    text, turning our deliberately-empty hint into a directional one. Landmarks
    are only safe when both peers negotiated a shared `map_area` (4.3.10); with
    none, they are an unaudited side channel.
    """
    assert "no place names" in build_prompt("north", Intent.TRUTH, 1).lower()
    assert "landmark" in build_prompt("", Intent.TRUTH, 3).lower()


def test_a_negotiated_map_area_re_enables_landmarks() -> None:
    """With a shared frame of reference they become legitimate flavour again."""
    prompt = build_prompt("north", Intent.TRUTH, 1, map_area="New York")
    assert "New York" in prompt and "no place names" not in prompt.lower()


def test_a_hint_always_carries_the_direction_the_brain_chose() -> None:
    """Across every direction and many turns, not one lucky sample.

    This is the property that makes the verbal channel worth having at all: if
    our hints carry no direction, our truths inform nobody and our bluffs
    deceive nobody.
    """
    from core.infra.llm.safety import conveys

    writer = HintWriter(forbidden=FORBIDDEN)
    for direction in ("north", "south", "east", "west"):
        for step in range(1, 15):
            assert conveys(writer.write(direction, Intent.TRUTH, step).text, direction)


def test_an_empty_direction_never_leaks_one() -> None:
    from core.infra.llm.safety import conveys

    writer = HintWriter(forbidden=FORBIDDEN)
    for step in range(1, 15):
        assert conveys(writer.write("", Intent.TRUTH, step).text, "")
