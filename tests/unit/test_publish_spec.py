"""Unit tests for the publish split.

These guard the single invariant that keeps ADR-001 honest: neither repository
may ever receive the other role's package or configuration.
"""

from __future__ import annotations

import pytest

from core.shared.publish_spec import ROLES, SHARED_PATHS, RoleSpec


def test_exactly_two_roles_are_defined() -> None:
    """Cop and Thief, matching the two GitHub repositories. (M#49)"""
    assert [spec.name for spec in ROLES] == ["cop", "thief"]


@pytest.mark.parametrize("spec", ROLES, ids=lambda s: s.name)
def test_role_never_publishes_its_forbidden_paths(spec: RoleSpec) -> None:
    """The published set and the forbidden set never intersect."""
    assert not set(spec.all_paths()) & set(spec.forbidden)


@pytest.mark.parametrize("spec", ROLES, ids=lambda s: s.name)
def test_each_role_publishes_the_shared_core(spec: RoleSpec) -> None:
    """Every repository gets core, docs, tests and the build configuration."""
    published = set(spec.all_paths())
    assert {"core", "docs", "tests", "pyproject.toml"} <= published


def test_the_two_roles_forbid_each_other() -> None:
    """What one role publishes is exactly what the other forbids."""
    cop, thief = ROLES
    assert set(cop.role_paths) == set(thief.forbidden)
    assert set(thief.role_paths) == set(cop.forbidden)


@pytest.mark.parametrize("spec", ROLES, ids=lambda s: s.name)
def test_config_is_role_scoped(spec: RoleSpec) -> None:
    """A repository carries its own config directory and no other."""
    published = set(spec.all_paths())
    assert f"config/{'police' if spec.name == 'cop' else 'thief'}" in published
    assert "config" not in published, "publishing all of config/ would leak the other role"


@pytest.mark.parametrize("spec", ROLES, ids=lambda s: s.name)
def test_pycache_is_never_copied(spec: RoleSpec) -> None:
    """Build artefacts stay out of the published tree."""
    assert "__pycache__" in spec.ignore


def test_repo_directories_are_distinct() -> None:
    """The two clones cannot collide on disk."""
    assert len({spec.repo_dir for spec in ROLES}) == len(ROLES)


def test_match_artefacts_are_published() -> None:
    """`results/` carries per-match config JSONs and logs, required in each repo."""
    assert "results" in SHARED_PATHS


def test_line_ending_policy_is_published() -> None:
    """`.gitattributes` pins LF so the shared config hashes identically on both
    peers' machines. Without it a CRLF checkout breaks the handshake. (M#11)"""
    assert ".gitattributes" in SHARED_PATHS


def test_shared_paths_contain_no_role_packages() -> None:
    """The shared set is genuinely role-neutral."""
    assert not {"police", "thief", "config"} & set(SHARED_PATHS)
