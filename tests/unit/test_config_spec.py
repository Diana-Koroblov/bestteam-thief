"""Unit tests for the Appendix F parameter table.

The table exists so that an illegal match configuration is caught before the
match rather than argued about after it, when both teams have already scored 0.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from core.shared.config_spec import (
    FIXED,
    MINIMUM,
    NEGOTIABLE,
    PARAMETERS,
    dotted_get,
    violations,
)

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "police" / "game.json"


@pytest.fixture
def legal_config() -> dict:
    """The shipped configuration, which must be legal by construction."""
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


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
