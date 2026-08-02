"""Game identifiers and artefact filenames (TODO 7.2.5).

One shared `game_id` names every artefact a match produces, so reports from ten
teams cannot collide in the grader's inbox — and so the Cop's report and the
Thief's report are recognisably about the *same* match.
"""

from __future__ import annotations

from core.report.identifiers import artefact_name, game_id

DATE = "2026-08-12"


def test_both_peers_compute_the_same_id() -> None:
    """**The property the whole scheme rests on.**

    Each peer holds the team names in its own order. Taking them as given would
    produce two ids for one match, and the pair of reports would read as two
    separate games that each side won. Sorting first makes the derivation
    symmetric without anyone having to remember to do it.
    """
    assert game_id("bestteam", "otherteam", DATE) == game_id("otherteam", "bestteam", DATE)


def test_case_and_whitespace_do_not_split_a_match_in_two() -> None:
    """One peer typing "BestTeam " must not disagree with "bestteam"."""
    assert game_id("  BestTeam ", "otherteam", DATE) == game_id("bestteam", "OtherTeam", DATE)


def test_different_matches_get_different_ids() -> None:
    assert game_id("a", "b", DATE) != game_id("a", "c", DATE)
    assert game_id("a", "b", DATE) != game_id("a", "b", "2026-08-13")


def test_a_non_latin_team_name_stays_distinguishable() -> None:
    """**Two non-Latin names both sanitise to nothing.**

    Hashing the *sanitised* form would give them the same id — precisely the
    collision this function exists to prevent. The fingerprint is taken from the
    original names, and each side gets a short readable stand-in.
    """
    one = game_id("Ωμέγα", "Δέλτα", DATE)
    two = game_id("Ωμέγα", "Σίγμα", DATE)
    assert one != two
    assert "-vs-" in one
    assert not one.endswith("-vs-")


def test_the_filename_is_safe_on_both_operating_systems() -> None:
    """It has to survive an email attachment, Windows and Linux."""
    name = artefact_name("log", game_id("Team X!", "b/c", DATE), 3)
    assert not set(name) & set('<>:"/\\|?*')
    assert name.endswith(".json")


def test_sub_game_numbers_are_zero_padded() -> None:
    """`g10` sorting before `g2` is the kind of thing nobody notices until they
    are reading twelve files at midnight looking for the one that failed."""
    identifier = game_id("a", "b", DATE)
    assert "_g03.json" in artefact_name("log", identifier, 3)
    assert artefact_name("log", identifier, 2) < artefact_name("log", identifier, 10)


def test_whole_match_artefacts_carry_no_sub_game_number() -> None:
    identifier = game_id("a", "b", DATE)
    assert "_g" not in artefact_name("result", identifier).removeprefix("result_")


def test_the_id_is_stable_across_calls() -> None:
    """Computed independently on two machines, so it cannot vary."""
    assert len({game_id("a", "b", DATE) for _ in range(10)}) == 1
