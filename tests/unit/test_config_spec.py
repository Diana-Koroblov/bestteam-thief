"""Unit tests for the Appendix F parameter table.

The table exists so that an illegal match configuration is caught before the
match rather than argued about after it, when both teams have already scored 0.
"""

from __future__ import annotations

import copy

import pytest

from core.shared.config_spec import (
    FIXED,
    MINIMUM,
    NEGOTIABLE,
    PARAMETERS,
    dotted_get,
    invariant_violations,
    violations,
)
from tests.paths import shared_config


@pytest.fixture
def legal_config() -> dict:
    """The shipped configuration, which must be legal by construction.

    Read via ``tests.paths`` rather than a literal role directory, because each
    published repository ships only its own role's config.
    """
    return shared_config()


def test_every_parameter_has_a_known_status() -> None:
    assert {p.status for p in PARAMETERS} <= {FIXED, MINIMUM, NEGOTIABLE}


def test_parameter_paths_are_unique() -> None:
    """A duplicated path would let one entry silently mask another."""
    paths = [p.path for p in PARAMETERS]
    assert len(paths) == len(set(paths))


def test_shipped_config_is_legal(legal_config: dict) -> None:
    assert violations(legal_config) == []


def test_defaults_alone_are_legal() -> None:
    """The published defaults must satisfy the table that describes them."""
    built: dict = {}
    for parameter in PARAMETERS:
        node = built
        *parents, leaf = parameter.path.split(".")
        for key in parents:
            node = node.setdefault(key, {})
        node[leaf] = parameter.default
    assert violations(built) == []


def test_lowering_a_minimum_is_reported(legal_config: dict) -> None:
    """M#12: minimums may be raised by agreement, never lowered."""
    config = copy.deepcopy(legal_config)
    config["movement_and_barriers"]["max_barriers"] = 10
    found = violations(config)
    assert any("max_barriers" in message and "minimum" in message for message in found)


def test_raising_a_minimum_is_allowed(legal_config: dict) -> None:
    config = copy.deepcopy(legal_config)
    config["board_and_agents"]["grid_size"] = 10
    assert violations(config) == []


def test_changing_a_fixed_value_is_reported(legal_config: dict) -> None:
    config = copy.deepcopy(legal_config)
    config["scoring"]["capture_cop"] = 25
    found = violations(config)
    assert any("capture_cop" in message and "FIXED" in message for message in found)


def test_adding_a_diagonal_move_is_reported(legal_config: dict) -> None:
    """C-009: the reference implementation defaults to king movement. Ours must not."""
    config = copy.deepcopy(legal_config)
    config["movement_and_barriers"]["move_set"] = ["N", "S", "E", "W", "NE", "STAY"]
    assert any("move_set" in message for message in violations(config))


def test_changing_a_negotiable_value_is_allowed(legal_config: dict) -> None:
    config = copy.deepcopy(legal_config)
    config["world"]["map_area"] = "Haifa"
    config["network_and_league"]["response_timeout_sec"] = 45
    assert violations(config) == []


def test_missing_key_is_reported(legal_config: dict) -> None:
    """An absent value is a value neither peer actually agreed on."""
    config = copy.deepcopy(legal_config)
    del config["scoring"]["tie_score"]
    assert any("scoring.tie_score" in message for message in violations(config))


def test_dotted_get_returns_nested_values(legal_config: dict) -> None:
    assert dotted_get(legal_config, "pheromones.pheromone_grid_size") == 5


def test_dotted_get_returns_default_for_unknown_path(legal_config: dict) -> None:
    assert dotted_get(legal_config, "no.such.path", "fallback") == "fallback"


def test_dotted_get_raises_without_a_default(legal_config: dict) -> None:
    with pytest.raises(KeyError):
        dotted_get(legal_config, "no.such.path")


def test_dotted_get_handles_a_scalar_midway(legal_config: dict) -> None:
    """Walking through a non-mapping must fail cleanly, not raise TypeError."""
    assert dotted_get(legal_config, "scoring.tie_score.deeper", None) is None


def test_appendix_f_has_thirty_two_rows() -> None:
    """Tables 13-19 hold 32 parameters. Our additions are counted separately."""
    additions = {
        "scoring.technical_loss",
        "pheromones.pheromone_min_center_intensity",
        "pheromones.decay_model",
        "pheromones.field_includes_current_turn",
        "pheromones.seal_scent_digest",
        "movement_and_barriers.seal_barrier_cell",
        "capture.resolution",
        "capture.stay_counts_as_move",
        "capture.swap_is_capture",
    }
    from_book = [p for p in PARAMETERS if p.path not in additions]
    assert len(from_book) == 32
    counts = {status: sum(1 for p in from_book if p.status == status) for status in
              (FIXED, MINIMUM, NEGOTIABLE)}
    assert counts == {FIXED: 14, MINIMUM: 9, NEGOTIABLE: 9}


def test_shipped_config_satisfies_our_invariants(legal_config: dict) -> None:
    assert invariant_violations(legal_config) == []


def test_unequal_move_cap_and_survival_threshold_is_reported(legal_config: dict) -> None:
    """Legal under Appendix F, but the win conditions do not cover it.

    Not a contradiction — both values are minimums and raising either is
    permitted. It is a degenerate configuration, so the guard is deliberately
    separate from the Appendix F check. See docs/PARAMETERS.md 4.2.
    """
    config = copy.deepcopy(legal_config)
    config["movement_and_barriers"]["survival_threshold"] = 40
    found = invariant_violations(config)
    assert len(found) == 1
    assert "PARAMETERS.md 4.2" in found[0]
    # Appendix F itself is content with the raised minimum. That is the point.
    assert violations(config) == []


def test_raising_both_limits_together_is_allowed(legal_config: dict) -> None:
    config = copy.deepcopy(legal_config)
    config["movement_and_barriers"]["max_moves"] = 45
    config["movement_and_barriers"]["survival_threshold"] = 45
    assert violations(config) == []
    assert invariant_violations(config) == []


# --- the split that reviewing an opponent's proposal needed (TODO 9.1.1) -----


def test_the_rows_we_invented_are_marked_as_ours() -> None:
    """It was a comment until an opponent's proposal had to be reviewed, and the
    distinction turned out to decide fixtures: a peer sending a plain Appendix F
    config is missing all eight and is entirely legal."""
    from core.shared.config_spec import PARAMETERS

    ours = {parameter.path for parameter in PARAMETERS if parameter.ours}
    assert ours == {
        "pheromones.pheromone_min_center_intensity",
        "pheromones.decay_model",
        "pheromones.field_includes_current_turn",
        "pheromones.seal_scent_digest",
        "movement_and_barriers.seal_barrier_cell",
        "capture.resolution",
        "capture.stay_counts_as_move",
        "capture.swap_is_capture",
    }


def test_an_absent_key_is_not_an_illegal_one() -> None:
    """The two call for opposite responses. Refusing a peer for not carrying a
    key we invented forfeits a fixture over a rule the book does not state; not
    refusing a lowered minimum disqualifies **both** teams (M#12)."""
    from core.shared.config_spec import classify
    from tests.paths import shared_config

    proposal = shared_config()
    proposal["pheromones"].pop("decay_model")
    proposal["movement_and_barriers"]["max_barriers"] = 10
    illegal, absent = classify(proposal)
    assert any("max_barriers" in item for item in illegal)
    assert any("decay_model" in item for item in absent)
    assert not any("decay_model" in item for item in illegal)


def test_violations_still_reports_both_together() -> None:
    """`load_config` refuses on either, and must keep doing so: for our *own*
    configuration an absent key is a value we cannot play with either way."""
    from core.shared.config_spec import classify, violations
    from tests.paths import shared_config

    proposal = shared_config()
    proposal["pheromones"].pop("decay_model")
    illegal, absent = classify(proposal)
    assert violations(proposal) == illegal + absent
    assert violations(proposal), "an absent key still makes our own config unplayable"


def test_legality_is_decided_by_the_status_column() -> None:
    """One predicate, two callers. `classify` wants a sentence and the reviewer
    wants a boolean, and the first version of the reviewer disagreed with
    `classify` about a lowered minimum — listing it as a legal judgement call
    four lines below refusing it."""
    from core.shared.config_spec import FIXED, MINIMUM, NEGOTIABLE, Parameter, legal

    assert legal(Parameter("p", MINIMUM, 14), 20) and legal(Parameter("p", MINIMUM, 14), 14)
    assert not legal(Parameter("p", MINIMUM, 14), 13)
    assert legal(Parameter("p", FIXED, 20), 20) and not legal(Parameter("p", FIXED, 20), 21)
    assert legal(Parameter("p", NEGOTIABLE, "New York"), "Tel Aviv")
