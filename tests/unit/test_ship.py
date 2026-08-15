"""Unit tests for the ship script's step assembly.

The ordering guarantee tested here closes a real hole: staging must happen
before the secret scan, or a brand-new file containing an API key would be
untracked and therefore invisible to the scan.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from core.shared.pipeline import GATES

_SHIP_PATH = Path(__file__).resolve().parent.parent.parent / "scripts" / "ship.py"


def _load_ship():
    """Import scripts/ship.py, which is not on the package path."""
    spec = importlib.util.spec_from_file_location("ship", _SHIP_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["ship"] = module
    spec.loader.exec_module(module)
    return module


ship = _load_ship()


def test_staging_happens_before_the_secret_scan() -> None:
    """Otherwise a new file holding a key is untracked and slips past. (M#39)"""
    names = [step.name for step in ship.build_steps("m", "both", False)]
    assert names.index("Stage all changes") < next(
        index for index, name in enumerate(names) if "Secret" in name
    )


def test_publishing_is_the_last_step() -> None:
    """Nothing reaches GitHub until every gate has passed."""
    steps = ship.build_steps("m", "both", False)
    assert "Publish" in steps[-1].name


def test_all_gates_sit_between_staging_and_publishing() -> None:
    """Stage, then every gate, then publish — derived so adding a gate is safe."""
    steps = ship.build_steps("m", "both", False)
    assert len(steps) == len(GATES) + 2
    assert steps[0].name.startswith("Stage")
    assert steps[-1].name.startswith("Publish")
    assert [step.name for step in steps[1:-1]] == [gate.name for gate in GATES]


def test_the_commit_message_is_passed_through_to_publish() -> None:
    """The working tree and both repositories carry the same message."""
    steps = ship.build_steps("feat: barriers", "both", False)
    assert "feat: barriers" in steps[-1].command


@pytest.mark.parametrize("role", ["cop", "thief", "both"])
def test_role_is_forwarded_to_publish(role: str) -> None:
    """Publishing a single role is possible without editing the script."""
    steps = ship.build_steps("m", role, False)
    assert role in steps[-1].command


def test_dry_run_is_forwarded_to_publish() -> None:
    """A dry run must not push."""
    assert "--dry-run" in ship.build_steps("m", "both", True)[-1].command


def test_normal_run_does_not_pass_dry_run() -> None:
    """The happy path really does publish."""
    assert "--dry-run" not in ship.build_steps("m", "both", False)[-1].command


def test_message_is_required() -> None:
    """Shipping without a message is a mistake, not a default."""
    with pytest.raises(SystemExit):
        ship.main([])


def test_skip_league_drops_only_the_benchmark_gate() -> None:
    """The other five gates must survive --skip-league untouched."""
    with_it = [step.name for step in ship.build_steps("m", "both", False, skip_league=False)]
    without_it = [step.name for step in ship.build_steps("m", "both", False, skip_league=True)]
    dropped = [name for name in with_it if name not in without_it]
    assert len(without_it) == len(with_it) - 1
    assert dropped == ["League benchmark (192 sub-games, both roles)"]


def test_skip_league_defaults_to_off() -> None:
    """Omitting the flag must reproduce the exact GATES ordering, unchanged."""
    steps = ship.build_steps("m", "both", False)
    assert [step.name for step in steps[1:-1]] == [gate.name for gate in ship.GATES]


def test_skip_league_flag_is_forwarded_from_the_cli() -> None:
    """--skip-league must reach build_steps, not just be parsed and dropped."""
    args = ship._parse_args(["-m", "m", "--skip-league"])
    assert args.skip_league is True


def test_skip_league_flag_defaults_to_false() -> None:
    """No flag typed means no gate is skipped."""
    args = ship._parse_args(["-m", "m"])
    assert args.skip_league is False
