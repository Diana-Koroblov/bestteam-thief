"""What each role repository receives (ADR-001).

Kept apart from ``scripts/publish.py`` so the split is data rather than logic,
and so it can be unit-tested without touching git or the filesystem.

The invariant this file exists to protect: **the Cop repository never contains
the Thief's brain or configuration, and vice versa.** Sharing source is
permitted; sharing live state is not (M#2), and a repository that visibly holds
only one role leaves no room for doubt about which we did.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["RoleSpec", "SHARED_PATHS", "ROLES"]

# Everything both repositories need. `docs/` carries the PRD, PLAN, TODO and the
# per-algorithm PRDs that M#50 requires in each repository.
SHARED_PATHS: tuple[str, ...] = (
    "core",
    "docs",
    "tests",
    "scripts",
    "notebooks",
    "assets",
    "results",
    "pyproject.toml",
    "uv.lock",
    ".gitignore",
    ".gitattributes",
    ".env-example",
    ".pre-commit-config.yaml",
    ".github",
)


@dataclass(frozen=True)
class RoleSpec:
    """The file set published to one role repository.

    Attributes:
        name: Short role key used on the command line.
        repo_dir: Clone directory name, beside the working tree.
        role_paths: Paths unique to this role.
        forbidden: Paths that must never appear in this repository.
        readme: Source file published as `README.md`.
        ignore: Glob patterns never copied.
    """

    name: str
    repo_dir: str
    role_paths: tuple[str, ...]
    forbidden: tuple[str, ...]
    readme: str
    ignore: tuple[str, ...] = field(
        default=("__pycache__", "*.pyc", ".venv", ".pytest_cache", ".ruff_cache")
    )

    def all_paths(self) -> tuple[str, ...]:
        """Return every path published for this role."""
        return SHARED_PATHS + self.role_paths


ROLES: tuple[RoleSpec, ...] = (
    RoleSpec(
        name="cop",
        repo_dir="bestteam-cop",
        role_paths=("police", "config/police"),
        forbidden=("thief", "config/thief"),
        readme="docs/README_cop.md",
    ),
    RoleSpec(
        name="thief",
        repo_dir="bestteam-thief",
        role_paths=("thief", "config/thief"),
        forbidden=("police", "config/police"),
        readme="docs/README_thief.md",
    ),
)
