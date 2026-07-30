"""Unit tests for the module dependency graph.

The behaviour that matters: only *internal* imports become edges, relative
imports resolve correctly, and a broken file never crashes the walk.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.shared.import_graph import build_graph, discover_modules, module_name


@pytest.fixture
def sample(tmp_path: Path) -> Path:
    """A small package: board <- smell <- runtime, plus an external import."""
    pkg = tmp_path / "app"
    (pkg / "domain").mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "domain" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "domain" / "board.py").write_text('"""Board geometry."""\nX = 1\n', encoding="utf-8")
    (pkg / "domain" / "smell.py").write_text(
        '"""Smell mechanics.\n\nSecond line ignored.\n"""\n'
        "import json\n"
        "from app.domain.board import X\n",
        encoding="utf-8",
    )
    (pkg / "runtime.py").write_text(
        "from app.domain import smell\nimport httpx\n", encoding="utf-8"
    )
    return tmp_path


def test_module_name_strips_init(tmp_path: Path) -> None:
    """A package's __init__.py is named for the package itself."""
    assert module_name(tmp_path / "app" / "__init__.py", tmp_path) == "app"


def test_module_name_is_dotted(tmp_path: Path) -> None:
    """Paths become dotted module paths."""
    assert module_name(tmp_path / "app" / "domain" / "board.py", tmp_path) == "app.domain.board"


def test_discover_skips_pycache(tmp_path: Path) -> None:
    """Build artefacts are never walked."""
    (tmp_path / "app" / "__pycache__").mkdir(parents=True)
    (tmp_path / "app" / "__pycache__" / "x.py").write_text("", encoding="utf-8")
    (tmp_path / "app" / "real.py").write_text("", encoding="utf-8")
    assert set(discover_modules(tmp_path)) == {"app.real"}


def test_internal_imports_become_edges(sample: Path) -> None:
    """`from app.domain.board import X` links smell to board."""
    graph = build_graph(sample)
    assert "app.domain.board" in graph["app.domain.smell"].imports


def test_external_imports_are_ignored(sample: Path) -> None:
    """json and httpx are not part of our architecture."""
    graph = build_graph(sample)
    assert graph["app.domain.smell"].imports == {"app.domain.board"}
    assert graph["app.runtime"].imports == {"app.domain.smell"}


def test_reverse_edges_are_populated(sample: Path) -> None:
    """Each node knows who depends on it."""
    graph = build_graph(sample)
    assert graph["app.domain.board"].imported_by == {"app.domain.smell"}


def test_from_package_import_module_resolves(sample: Path) -> None:
    """`from app.domain import smell` targets the module, not the package."""
    graph = build_graph(sample)
    assert "app.domain.smell" in graph["app.runtime"].imports


def test_summary_is_the_first_docstring_line(sample: Path) -> None:
    """Notes carry a one-line description, not the whole docstring."""
    assert build_graph(sample)["app.domain.smell"].summary == "Smell mechanics."


def test_package_property(sample: Path) -> None:
    """Package is used to tag and colour notes."""
    graph = build_graph(sample)
    assert graph["app.domain.board"].package == "app.domain"
    assert graph["app"].package == "root"


def test_degree_counts_both_directions(sample: Path) -> None:
    """Degree drives the 'busiest modules' table."""
    graph = build_graph(sample)
    assert graph["app.domain.smell"].degree == 2


def test_relative_import_resolves(tmp_path: Path) -> None:
    """`from .board import X` inside a package links correctly."""
    pkg = tmp_path / "app"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "board.py").write_text("X = 1\n", encoding="utf-8")
    (pkg / "smell.py").write_text("from .board import X\n", encoding="utf-8")
    graph = build_graph(tmp_path)
    assert "app.board" in graph["app.smell"].imports


def test_self_import_is_not_an_edge(tmp_path: Path) -> None:
    """A module importing its own package must not link to itself."""
    pkg = tmp_path / "app"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "solo.py").write_text("import app.solo\n", encoding="utf-8")
    assert build_graph(tmp_path)["app.solo"].imports == set()


def test_unparseable_file_does_not_crash(tmp_path: Path) -> None:
    """One broken file must not abort the whole walk."""
    (tmp_path / "broken.py").write_text("def oops(:\n", encoding="utf-8")
    (tmp_path / "fine.py").write_text("X = 1\n", encoding="utf-8")
    graph = build_graph(tmp_path)
    assert graph["broken"].summary == "(unparseable)"
    assert "fine" in graph


def test_empty_source_yields_empty_graph(tmp_path: Path) -> None:
    """No Python files means no graph, not an exception."""
    assert build_graph(tmp_path) == {}
