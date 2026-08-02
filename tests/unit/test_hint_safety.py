"""The outbound guard rails (TODO 4.3.7, 4.3.8, 4.6.4).

These run on **our own** text before it is sealed into the commit. A rule caught
here costs one regeneration; the same rule caught in the audit costs the series.
So the scanner is deliberately over-eager, and these tests pin that down.
"""

from __future__ import annotations

import pytest

from core.infra.llm.safety import cap_words, conveys, leaks_coordinates, violations

# Every way a model has actually been seen to smuggle a position into "free" text.
LEAKY = [
    "I am at (3,4) and you cannot reach me.",
    "Try row 5, if you have the time.",
    "Heading for cell 12 while you wander.",
    "Look at 3,4 and weep.",
    "I sit in column 2, untouchable.",
    "Somewhere around 6-6, good luck.",
    "You will find me at 2 5 eventually.",
    "My position 7 is safer than yours.",
]

CLEAN = [
    "Heading north along the wall while you guess.",
    "I drift west, and your trail runs cold.",
    "You are chasing a rumour, not an agent.",
    "Two steps ahead and getting further away.",
]


@pytest.mark.parametrize("text", LEAKY)
def test_it_catches_every_way_a_coordinate_can_leak(text: str) -> None:
    """M#27. Free natural language is the requirement, not a preference.

    A hint carrying ``(3,4)`` turns the verbal game into a structured position
    protocol — which forfeits exactly the part of the grade that rewards
    inference from ambiguous text.
    """
    assert leaks_coordinates(text), text


@pytest.mark.parametrize("text", CLEAN)
def test_it_leaves_ordinary_taunts_alone(text: str) -> None:
    """Over-eager is fine; useless is not. Directional language must survive."""
    assert not leaks_coordinates(text), text


def test_the_word_cap_truncates_at_a_word_boundary() -> None:
    """4.3.7. A negotiated value, so a long hint is a violation, not a style bug."""
    capped = cap_words(" ".join(f"word{n}" for n in range(30)), 15)
    assert len(capped.split()) == 15
    assert capped.endswith(".")


def test_a_short_hint_is_returned_untouched() -> None:
    assert cap_words("Heading north, and you are late.", 15) == "Heading north, and you are late."


def test_an_over_long_hint_is_reported() -> None:
    assert any("word cap" in v for v in violations("a " * 40, 15))


def test_an_empty_hint_is_reported() -> None:
    """A turn without a hint would break commit-reveal, not merely look odd."""
    assert violations("   ", 15)


# --- the fabrication ban ----------------------------------------------------

FORBIDDEN = ("capture", "barriers", "scent", "game_count")


@pytest.mark.parametrize(
    "text",
    [
        "I caught you two turns ago, admit it.",
        "I have placed walls on every route you have.",
        "My scent reads you clearly, three cells away.",
        "I have won this series already.",
    ],
)
def test_audited_claims_are_rejected_even_though_we_are_allowed_to_lie(text: str) -> None:
    """**The one place the rulebook overrules our own deception policy.**

    Bluffing about direction is the game. Capture claims, barrier placements,
    scent fields and game counts are *audited*, and a lie about any of them
    scores 0 **for both teams** — so it cannot be a strategic choice.
    """
    assert any("fabricates" in v for v in violations(text, 15, FORBIDDEN))


def test_a_directional_bluff_is_still_allowed() -> None:
    """Deception is a first-class move; only the audited categories are barred."""
    assert violations("I am running north, far from you.", 15, FORBIDDEN) == []


# --- does the hint do its job at all? ---------------------------------------


@pytest.mark.parametrize(
    "text,direction",
    [
        ("I drift north while you guess at shadows.", "north"),
        ("The northern edge is calling me. Keep up.", "north"),
        ("Heading westward, and you are far too slow.", "west"),
        ("Southbound and gone before you look.", "south"),
    ],
)
def test_a_hint_carrying_its_direction_passes(text: str, direction: str) -> None:
    """Stems count. "northern" and "southbound" carry a direction to any reader.

    The first version of this check demanded an exact word match and was wrong
    **in both directions at once**: it rejected "the northern edge" as saying
    nothing about north, while letting that same phrase through as a supposedly
    direction-free hint.
    """
    assert conveys(text, direction)


@pytest.mark.parametrize(
    "text",
    [
        "You'll never catch me, I'm heading towards the mountains.",
        "Headed towards the river, you'll never catch me that way.",
        "Good luck finding me before the clock runs out.",
    ],
)
def test_an_evocative_hint_that_carries_no_direction_is_rejected(text: str) -> None:
    """**Real Groq output, and the reason this check exists.**

    Asked for *north* it wrote "the mountains"; asked for *west*, "the river".
    Both read well and both are useless: there is no shared map, so the parser
    on the other side cannot turn a river into a direction. A hint like this
    informs nobody when truthful and deceives nobody when a lie — a turn of the
    verbal game spent saying nothing.
    """
    assert not conveys(text, "north")


def test_a_deliberately_empty_hint_must_leak_no_direction() -> None:
    """Saying nothing is a real move, so it has to actually say nothing.

    Groq was told to give away nothing and replied "head towards the river" —
    which is why the empty case is checked rather than assumed.
    """
    assert conveys("You are chasing a rumour, not an agent.", "")
    assert not conveys("The northern edge is calling me.", "")


def test_the_wrong_direction_is_reported() -> None:
    """A bluff must convey the direction we *chose*, not merely some direction."""
    assert any("north" in v for v in violations("I go south, quietly.", 15, direction="north"))
