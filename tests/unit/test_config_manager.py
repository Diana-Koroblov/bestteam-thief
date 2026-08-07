"""Unit tests for configuration loading, merging and fingerprinting.

The three guarantees under test: the shared contract always wins over private
preferences, an incompatible version fails loudly, and the digest covers the
shared contract and nothing else.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.crypto.canonical import digest
from core.shared.config_manager import (
    Config,
    ConfigError,
    ConfigRuleError,
    ConfigVersionError,
    load_config,
)
from tests.paths import PRESENT_ROLES, role_dir, shared_config

SHIPPED = shared_config()

# Each published repository ships one role only, so cross-role comparisons can
# only run in the working tree. See tests/paths.py.
BOTH_ROLES = pytest.mark.skipif(
    len(PRESENT_ROLES) < 2,
    reason="only one role is published to this repository (ADR-001)",
)


def _write(directory: Path, shared: dict, private: str = "") -> Path:
    """Write a throwaway role directory. Named to avoid shadowing ``role_dir``."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "game.json").write_text(json.dumps(shared), encoding="utf-8")
    if private:
        (directory / "game.toml").write_text(private, encoding="utf-8")
    return directory


@pytest.mark.parametrize("role", PRESENT_ROLES)
def test_loads_every_shipped_configuration(role: str) -> None:
    config = load_config(role_dir(role))
    assert config.get("board_and_agents.grid_size") == 7
    assert config.get("network_and_league.num_games") == 6


@BOTH_ROLES
def test_both_roles_ship_an_identical_shared_contract() -> None:
    """M#11 requires byte-identical shared config; our two roles must not drift."""
    digests = {load_config(role_dir(role)).shared_digest() for role in PRESENT_ROLES}
    assert len(digests) == 1


@BOTH_ROLES
def test_private_settings_differ_between_roles() -> None:
    assert load_config(role_dir("police")).get("identity.role") == "cop"
    assert load_config(role_dir("thief")).get("identity.role") == "thief"


@pytest.mark.parametrize("role", PRESENT_ROLES)
def test_each_role_declares_itself(role: str) -> None:
    """Runs in every repository: the one role present must name itself correctly."""
    expected = {"police": "cop", "thief": "thief"}[role]
    assert load_config(role_dir(role)).get("identity.role") == expected


def test_shared_overrides_private(tmp_path: Path) -> None:
    """A local edit must never be able to change agreed physics."""
    role = _write(tmp_path / "role", SHIPPED, 'version = "1.00"\n[world]\nmap_area = "Haifa"\n')
    config = load_config(role)
    assert config.get("world.map_area") == "New York"


def test_private_fills_gaps(tmp_path: Path) -> None:
    role = _write(tmp_path / "role", SHIPPED, 'version = "1.00"\n[ui]\ncell_pixels = 32\n')
    assert load_config(role).get("ui.cell_pixels") == 32


def test_digest_ignores_private_settings(tmp_path: Path) -> None:
    """Two peers with different ngrok domains must still agree on the digest."""
    first = _write(tmp_path / "a", SHIPPED, 'version = "1.00"\n[network]\npublic_domain = "a.dev"\n')
    second = _write(tmp_path / "b", SHIPPED, 'version = "1.00"\n[network]\npublic_domain = "b.dev"\n')
    assert load_config(first).shared_digest() == load_config(second).shared_digest()


def test_digest_is_the_canonical_hash_of_the_shared_file(tmp_path: Path) -> None:
    role = _write(tmp_path / "role", SHIPPED)
    assert load_config(role).shared_digest() == digest(SHIPPED)


def test_missing_shared_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="missing shared configuration"):
        load_config(tmp_path)


def test_malformed_json_raises(tmp_path: Path) -> None:
    (tmp_path / "game.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid JSON"):
        load_config(tmp_path)


def test_malformed_toml_raises(tmp_path: Path) -> None:
    role = _write(tmp_path / "role", SHIPPED, "this is not toml =\n")
    with pytest.raises(ConfigError, match="not valid TOML"):
        load_config(role)


def test_missing_private_file_is_fine(tmp_path: Path) -> None:
    role = _write(tmp_path / "role", SHIPPED)
    assert load_config(role).private == {}


def test_incompatible_version_raises(tmp_path: Path) -> None:
    shared = dict(SHIPPED, version="2.00")
    role = _write(tmp_path / "role", shared)
    with pytest.raises(ConfigVersionError, match="cannot read"):
        load_config(role)


def test_missing_version_raises(tmp_path: Path) -> None:
    shared = {key: value for key, value in SHIPPED.items() if key != "version"}
    role = _write(tmp_path / "role", shared)
    with pytest.raises(ConfigVersionError, match="<none>"):
        load_config(role)


def test_same_major_version_is_accepted(tmp_path: Path) -> None:
    role = _write(tmp_path / "role", dict(SHIPPED, version="1.07"))
    assert load_config(role).get("scoring.tie_score") == 2


def test_the_shipped_contract_declares_the_book_s_schema(tmp_path: Path) -> None:
    """Appendix B.3 fixes the field **names**, and this is one of them.

    An opponent building to the book looks for `schema_version` by name; a file
    that only carries our own `version` tells them nothing about its layout.
    """
    from core.shared.config_manager import SCHEMA_VERSION

    assert SHIPPED["schema_version"] == SCHEMA_VERSION
    assert load_config(_write(tmp_path / "role", SHIPPED)).shared["schema_version"] == "1.2"


def test_a_different_major_schema_is_refused(tmp_path: Path) -> None:
    """A 2.x layout has moved a key we read; guessing which one loses a match."""
    role = _write(tmp_path / "role", dict(SHIPPED, schema_version="2.0"))
    with pytest.raises(ConfigVersionError, match="schema_version"):
        load_config(role)


def test_an_absent_schema_version_is_accepted(tmp_path: Path) -> None:
    """Refusing an unlabelled file would forfeit a fixture and prove nothing.

    A *stated* incompatible schema is a claim about the layout; silence is not.
    """
    shared = {key: value for key, value in SHIPPED.items() if key != "schema_version"}
    assert load_config(_write(tmp_path / "role", shared)).get("scoring.tie_score") == 2


def test_agreed_between_reads_the_parties_named_in_the_contract(tmp_path: Path) -> None:
    """Ours ships as a one-name proposal; a signed contract names both."""
    assert load_config(_write(tmp_path / "role", SHIPPED)).agreed_between == ["bestteam"]
    signed = load_config(_write(tmp_path / "b", dict(SHIPPED, agreed_between=["us", "them"])))
    assert signed.agreed_between == ["us", "them"]


def test_agreed_between_survives_a_malformed_value(tmp_path: Path) -> None:
    """It is a label, not physics: a wrong shape must not stop a match starting."""
    role = _write(tmp_path / "role", dict(SHIPPED, agreed_between="bestteam"))
    assert load_config(role).agreed_between == []


def test_illegal_config_raises(tmp_path: Path) -> None:
    shared = json.loads(json.dumps(SHIPPED))
    shared["scoring"]["capture_cop"] = 25
    role = _write(tmp_path / "role", shared)
    with pytest.raises(ConfigRuleError, match="capture_cop"):
        load_config(role)


def test_rule_enforcement_can_be_disabled_to_inspect_a_proposal(tmp_path: Path) -> None:
    """We must be able to load an opponent's illegal proposal in order to quote it."""
    shared = json.loads(json.dumps(SHIPPED))
    shared["movement_and_barriers"]["max_moves"] = 20
    role = _write(tmp_path / "role", shared)
    assert load_config(role, enforce_rules=False).get("movement_and_barriers.max_moves") == 20


def test_require_returns_a_value_and_raises_when_absent(tmp_path: Path) -> None:
    config: Config = load_config(_write(tmp_path / "role", SHIPPED))
    assert config.require("scoring.survival_thief") == 10
    with pytest.raises(ConfigError, match="required configuration key is missing"):
        config.require("nothing.here")


REQUIRED_SECTIONS = (
    "identity",
    "game",
    "network",
    "strategy",
    "trash_talk",
    "llm",
    "email",
    "ui",
    "logging",
)


@pytest.mark.parametrize("role", PRESENT_ROLES)
def test_private_skeleton_has_every_required_section(role: str) -> None:
    private = load_config(role_dir(role)).private
    assert set(REQUIRED_SECTIONS) <= set(private)


@pytest.mark.parametrize("role", PRESENT_ROLES)
def test_private_config_does_not_mirror_negotiated_physics(role: str) -> None:
    """A second copy of an agreed value is a second thing that can drift."""
    private = load_config(role_dir(role)).private
    assert set(private) & set(SHIPPED) == {"version"}


@pytest.mark.parametrize("role", PRESENT_ROLES)
def test_rate_limits_meet_the_appendix_f_minimums(role: str) -> None:
    path = role_dir(role) / "rate_limits.json"
    limits = json.loads(path.read_text(encoding="utf-8"))
    floors = SHIPPED["rate_limiter_gatekeeper"]
    assert limits["version"] == SHIPPED["version"]
    for key, floor in floors.items():
        assert limits[key] >= floor, key
