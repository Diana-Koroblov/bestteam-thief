"""The mechanism choices, and the clause that states them (TODO 9.1.5-9.1.7).

PRD_negotiation §3.6: Appendix F's status column settles every *value*, so two
honest peers can only ever disagree about a **mechanism** — and a mechanism
discovered mid-match is unresolvable and voids the result for both teams (M#35).

The tests that matter here are the ones that would pass under a broken
implementation for the wrong reason: a clause that quotes a number instead of
computing it, and a comparison that treats an opponent's silence as agreement.
"""

from __future__ import annotations

import copy
from dataclasses import replace

import pytest

from core.protocol.readings import (
    COMPONENT_ORDER,
    READINGS,
    clause,
    disagreements,
    readings_of,
    unsigned,
)
from core.shared.config_spec import PARAMETERS


@pytest.fixture
def ours(minimal_config) -> dict:
    """What the shipped configuration says we play under."""
    return readings_of(minimal_config)


def reconfigured(config, path: str, value):
    """Return *config* with one merged key changed.

    Deep-copied: `minimal_config` is session-scoped, and mutating it in place
    leaks into every test that runs afterwards — which is how a suite acquires
    failures that depend on the order it happened to run in.
    """
    merged = copy.deepcopy(config.merged)
    node = merged
    *parents, leaf = path.split(".")
    for key in parents:
        node = node[key]
    node[leaf] = value
    return replace(config, merged=merged)


# --- what gets declared ------------------------------------------------------


def test_every_reading_is_an_appendix_f_parameter(ours: dict) -> None:
    """**The guard against a typo'd path.** `config.get` answers None for a key
    that does not exist, which renders as the string `'None'` — a reading that
    compares equal to another peer's `'None'` and agrees about nothing.

    Because every path here is also in the Appendix F table, `load_config`
    already refuses a configuration that omits one, and the failure surfaces at
    load rather than as a plausible-looking handshake.
    """
    known = {parameter.path for parameter in PARAMETERS}
    assert {path for path, _ in READINGS} <= known
    assert COMPONENT_ORDER not in known, "the component order is structural, not configurable"


def test_the_component_order_is_declared_even_though_no_flag_holds_it(ours: dict) -> None:
    """C-010: the published starts (0,0) and (3,3) are order-invariant, so a
    disagreement about (row,col) vs (x,y) stays invisible until the first
    asymmetric coordinate — by which time it has already decided a sub-game."""
    assert ours[COMPONENT_ORDER] == "row,col"


def test_booleans_are_spelled_the_way_json_spells_them(ours: dict) -> None:
    """An opponent writing in any other language sends `true`. A comparison that
    only ever matched Python's `True` would report every honest peer as a
    disagreement and refuse every match."""
    assert ours["capture.swap_is_capture"] == "true"
    assert ours["capture.stay_counts_as_move"] == "false"


# --- comparing two peers -----------------------------------------------------


def test_a_stated_contradiction_is_reported(ours: dict) -> None:
    """Whichever model we play, the *other* one must read as a disagreement.

    Derived rather than written down: this asserted a literal ``subtractive``
    until the shipped config was negotiated onto subtractive for a match, at
    which point "theirs" equalled ours and the test passed by agreeing with
    itself instead of by detecting anything.
    """
    mine = ours["pheromones.decay_model"]
    other = "multiplicative" if mine == "subtractive" else "subtractive"
    theirs = dict(ours, **{"pheromones.decay_model": other})
    assert any("decay_model" in item for item in disagreements(ours, theirs))


def test_silence_is_not_a_contradiction(ours: dict) -> None:
    """**The distinction that decides fixtures.** These fields are our own
    extension of Appendix F; a peer that never built them is not disagreeing
    with us, and refusing over a rule the book does not state forfeits a match
    for nothing (PRD_negotiation §3.6b)."""
    assert disagreements(ours, {}) == []
    assert unsigned(ours, {}) == sorted(ours)


def test_a_disagreement_names_the_contradiction_it_belongs_to(ours: dict) -> None:
    """With no referee, the citation is the entire remedy: we have to be able to
    say *which* clause they are on the other side of."""
    theirs = dict(ours, **{"capture.swap_is_capture": "false"})
    assert "C-006c" in disagreements(ours, theirs)[0]


def test_two_peers_running_this_code_agree(ours: dict) -> None:
    assert disagreements(ours, ours) == [] and unsigned(ours, ours) == []


# --- the clause a human pastes -----------------------------------------------


def test_the_worked_example_is_computed_from_the_model_we_play(minimal_config) -> None:
    """**M#23's whole point, and the one number that identifies an opponent's
    lineage.** The book's multiplicative decay takes 0.900 to 0.810; the
    reference simulator's subtractive decay takes it to 0.800. A clause that
    quoted the figure instead of computing it would keep saying 0.810 after the
    flag was flipped — agreeing, in writing, to physics we were not running.
    """
    multiplicative = reconfigured(minimal_config, "pheromones.decay_model", "multiplicative")
    assert "0.810" in clause(multiplicative)
    assert "0.800" in clause(reconfigured(minimal_config, "pheromones.decay_model", "subtractive"))


def test_the_clause_follows_the_capture_flag(minimal_config) -> None:
    """N15 is a config flag so we can play either reading without a code change.
    The sentence has to move with it or we would be agreeing to one and playing
    the other."""
    assert "vacated does not capture" in clause(minimal_config)
    flipped = reconfigured(minimal_config, "capture.resolution", "on_placement")
    assert "vacated captures" in clause(flipped)


def test_the_clause_states_when_a_field_may_be_acted_on(minimal_config) -> None:
    """9.1.7. An opponent acting on the *current* turn's field is revealing
    before committing, which is the single attack commit-reveal exists to
    prevent — so the timing has to be in the text they agree to, not only in
    our own head."""
    assert "end_of_previous_full_turn" in clause(minimal_config)
    assert "turn k+1" in clause(minimal_config)


def test_the_clause_names_no_coordinate_the_opponent_could_misread(minimal_config) -> None:
    """C-010 says confirm with a worked example, never a label. `[0,1]` read as
    row 0 column 1 is one cell East; read as (x, y) it is one cell South."""
    text = clause(minimal_config)
    assert "[0,1]" in text and "East" in text
