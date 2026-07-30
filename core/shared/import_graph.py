"""Build a module dependency graph from Python source, using only the AST.

Used to reverse-engineer an unfamiliar codebase (lecture L07) by turning it into
an Obsidian vault: one note per module, one wikilink per internal import. The
graph is also useful on our own tree, as evidence that the layering rules in
``PLAN.md`` are actually respected.

Only *internal* imports become edges. Standard library and third-party imports
are dropped, because the question this answers is "how do our own pieces depend
on each other", not "what do we install".
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

from core.shared.constants import EXCLUDED_DIR_NAMES

__all__ = ["ModuleNode", "module_name", "discover_modules", "build_graph"]


@dataclass
class ModuleNode:
    """One module and its place in the dependency graph.

    Attributes:
        name: Dotted module path, e.g. ``police_thief.domain.smell``.
        path: File location.
        summary: First line of the module docstring, if any.
        code_lines: Non-blank, non-comment lines.
        imports: Internal modules this one depends on.
        imported_by: Internal modules that depend on this one.
    """

    name: str
    path: Path
    summary: str = ""
    code_lines: int = 0
    imports: set[str] = field(default_factory=set)
    imported_by: set[str] = field(default_factory=set)

    @property
    def package(self) -> str:
        """Return the parent package, or ``root`` for a top-level module."""
        parts = self.name.split(".")
        return ".".join(parts[:-1]) if len(parts) > 1 else "root"

    @property
    def is_package(self) -> bool:
        """True when this module is a package's own ``__init__``."""
        return self.path.name == "__init__.py"

    @property
    def group(self) -> str:
        """Package used to tag and colour the note.

        A package's ``__init__`` belongs to *itself*, not to its parent — so
        ``domain/__init__.py`` colours as ``domain`` rather than as the root.
        """
        return self.name if self.is_package else self.package

    @property
    def degree(self) -> int:
        """Total connections, in and out."""
        return len(self.imports) + len(self.imported_by)


def module_name(path: Path, source_root: Path) -> str:
    """Return the dotted module name for *path* relative to *source_root*."""
    relative = path.relative_to(source_root).with_suffix("")
    parts = list(relative.parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def discover_modules(source_root: Path) -> dict[str, Path]:
    """Map every importable module under *source_root* to its file."""
    found: dict[str, Path] = {}
    for path in sorted(source_root.rglob("*.py")):
        if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
            continue
        name = module_name(path, source_root)
        if name:
            found[name] = path
    return found


def _resolve(target: str, known: set[str]) -> str | None:
    """Return the longest known module that *target* refers to, or None."""
    parts = target.split(".")
    for cut in range(len(parts), 0, -1):
        candidate = ".".join(parts[:cut])
        if candidate in known:
            return candidate
    return None


def _absolute_target(node: ast.ImportFrom, current: str, is_package: bool) -> str:
    """Resolve a relative ``from . import x`` against the importing module.

    Level 1 means "the package containing this module" — which for a package's
    own ``__init__`` is the package itself, and for a plain module is its parent.
    Each extra level climbs one more.
    """
    if not node.level:
        return node.module or ""
    parts = current.split(".")
    if not is_package:
        parts = parts[:-1]
    parts = parts[: max(0, len(parts) - (node.level - 1))]
    return ".".join(parts + ([node.module] if node.module else []))


def _imports_of(tree: ast.AST, current: str, known: set[str], is_package: bool) -> set[str]:
    """Return the internal modules imported by a parsed source tree."""
    edges: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if (hit := _resolve(alias.name, known)) and hit != current:
                    edges.add(hit)
        elif isinstance(node, ast.ImportFrom):
            base = _absolute_target(node, current, is_package)
            if not base:
                continue
            for alias in node.names:
                hit = _resolve(f"{base}.{alias.name}", known) or _resolve(base, known)
                if hit and hit != current:
                    edges.add(hit)
    return edges


def build_graph(source_root: Path) -> dict[str, ModuleNode]:
    """Return every module under *source_root*, with internal edges resolved."""
    from core.shared.loc_counter import count_code_lines

    files = discover_modules(source_root)
    known = set(files)
    graph: dict[str, ModuleNode] = {}

    for name, path in files.items():
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, UnicodeDecodeError, SyntaxError):
            graph[name] = ModuleNode(name=name, path=path, summary="(unparseable)")
            continue
        doc = ast.get_docstring(tree) or ""
        graph[name] = ModuleNode(
            name=name,
            path=path,
            summary=doc.strip().splitlines()[0] if doc.strip() else "",
            code_lines=count_code_lines(path).code_lines,
            imports=_imports_of(tree, name, known, path.name == "__init__.py"),
        )

    for node in graph.values():
        for target in node.imports:
            graph[target].imported_by.add(node.name)
    return graph
