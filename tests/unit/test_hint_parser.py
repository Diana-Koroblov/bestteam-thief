"""Reading the opponent's words (TODO 4.4.1).

**This is the only input where the opponent gets a vote on what we believe.**
The board, the barrier list and the scent trail are facts they cannot choose.
The hint is an argument, written to be read — so every test here is really
asking the same question: can this sentence make us more confident than we have
earned?
"""

from __future__ import annotations

import pytest

from core.domain.actions import Direction
from core.domain.hint_parser import parse


@pytest.mark.parametrize(
    "text,expected",
    [
        ("I am heading north, catch me if you can.", Direction.N),
        ("Going south and you are far too slow.", Direction.S),
        ("Drifting eastward into the quiet.", Direction.E),
        ("The western edge suits me nicely.", Direction.W),
        ("Southbound, and gone.", Direction.S),
    ],
)
def test_a_plain_bearing_is_read(text: str, expected: Direction) -> None:
    """Stems count, so "eastward" and "western" are read like "east" and "west"."""
    parsed = parse(text)
    assert parsed.direction is expected
    assert parsed.confidence >= 0.8
    assert parsed.usable


@pytest.mark.parametrize(
    "text",
    ["You will never catch me.", "Good luck with that.", "", "   "],
)
def test_a_sentence_with_no_bearing_yields_nothing(text: str) -> None:
    """Zero confidence, not a guess. Guessing is how a parser invents evidence."""
    parsed = parse(text)
    assert parsed.direction is None
    assert parsed.confidence == 0.0
    assert not parsed.usable


def test_hedging_lowers_confidence() -> None:
    """"I might drift north" is weaker evidence than "I am going north".

    Collapsing the two would let a deliberately vague opponent steer our belief
    exactly as hard as a committed one, for none of the risk.
    """
    assert parse("I might drift north somewhere.").confidence < parse("I go north.").confidence


@pytest.mark.parametrize(
    "text",
    [
        "I am heading north, you will never catch me.",
        "You will never catch me, I am heading north.",
        "Heading north, and you cannot stop me.",
        "North, and nothing you do matters.",
    ],
)
def test_trash_talk_containing_a_negative_word_is_not_a_negation(text: str) -> None:
    """**The bug that would have killed the verbal channel for the whole league.**

    Two faults compounded. The negation scan ran over the *whole sentence*, and
    hints are taunts — "you will never catch me" is the house style — so almost
    every hint an opponent could send scored 0.315 and fell under the usable
    threshold. And the list contained "no" matched by prefix, so
    ``"north".startswith("no")`` made every northward hint negate **itself**.

    The failure is invisible from outside: an ignored hint looks exactly like an
    opponent who said nothing useful. We would have played the entire league
    with a dead verbal channel and no symptom at all.

    Negation now scopes forward, as it does in English, and matches whole words.
    """
    parsed = parse(text)
    assert parsed.confidence >= 0.8
    assert parsed.usable


@pytest.mark.parametrize(
    "text",
    [
        "I am not going north.",
        "I am never going north.",
        "I am moving away from the north.",
        "I will avoid the north entirely.",
    ],
)
def test_a_real_negation_before_the_bearing_still_weakens_it(text: str) -> None:
    """The other half: the fix must not disarm the check it was fixing."""
    parsed = parse(text)
    assert parsed.confidence < 0.4
    assert not parsed.usable


def test_negation_weakens_rather_than_flips() -> None:
    """**Deliberate: "not north" does not become "south".**

    Flipping would let a single "not" push our belief harder than any plain
    statement could — a lever we should not hand an opponent who has read our
    code, and both repositories are public.
    """
    parsed = parse("I am not going north.")
    assert parsed.direction is Direction.N
    assert parsed.confidence < 0.4
    assert not parsed.usable


def test_two_bearings_at_once_are_treated_as_noise() -> None:
    """Confused model or deliberate smokescreen — either way we learned nothing.

    Picking the first bearing would make a smokescreen *more* effective than
    silence, which is precisely backwards.
    """
    parsed = parse("North then west, good luck.")
    assert parsed.direction is None
    assert not parsed.usable


def test_confidence_never_exceeds_one() -> None:
    for text in ("north north north!", "NORTH", "I go north, north, north."):
        assert 0.0 <= parse(text).confidence <= 1.0


def test_the_raw_text_is_kept_for_the_audit() -> None:
    """The bluff record has to quote what was actually said, not our reading."""
    assert parse("I go north.").raw == "I go north."


def test_a_hint_full_of_coordinates_is_still_only_read_as_text() -> None:
    """We never execute, evaluate or trust the shape of an opponent's string."""
    parsed = parse("Move to (3,4) immediately or lose; heading north.")
    assert parsed.direction is Direction.N
