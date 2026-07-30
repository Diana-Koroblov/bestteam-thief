"""Generate an Obsidian vault from a Python codebase, for Graph View (L07).

    uv run python scripts/make_graph_vault.py --source ../Game-P2P-Cop-Chase/src
    uv run python scripts/make_graph_vault.py --source . --out vaults/our-project

One note per module, one wikilink per internal import. Open the output folder in
Obsidian as a vault and press Ctrl+G for the dependency graph.

Notes are tagged by package, so Obsidian's Graph View can colour by layer:
Settings → Graph view → Groups → add a query such as ``tag:#domain``.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.shared.import_graph import ModuleNode, build_graph  # noqa: E402

__all__ = ["main", "note_name", "render_note", "render_index"]


def note_name(module: str) -> str:
    """Return a flat, link-safe note name for a dotted module path."""
    return module.replace(".", "-")


def render_note(node: ModuleNode) -> str:
    """Return the Markdown for one module note."""
    tag = node.package.replace(".", "/")
    lines = [
        "---",
        f"tags: [{tag}]",
        f"loc: {node.code_lines}",
        "---",
        f"# {node.name}",
        "",
    ]
    if node.summary:
        lines += [f"> {node.summary}", ""]
    lines += [
        f"**Package:** `{node.package}`  ",
        f"**Code lines:** {node.code_lines}  ",
        f"**Depends on:** {len(node.imports)} · **Depended on by:** {len(node.imported_by)}",
        "",
        "## Imports",
    ]
    lines += [f"- [[{note_name(m)}]]" for m in sorted(node.imports)] or ["_(none)_"]
    lines += ["", "## Imported by"]
    lines += [f"- [[{note_name(m)}]]" for m in sorted(node.imported_by)] or ["_(none)_"]
    return "\n".join(lines) + "\n"


def render_index(graph: dict[str, ModuleNode], source: Path) -> str:
    """Return an overview note: size, hubs, and modules nothing imports."""
    by_degree = sorted(graph.values(), key=lambda n: (-n.degree, n.name))
    hubs = sorted(graph.values(), key=lambda n: (-len(n.imported_by), n.name))[:10]
    orphans = [n for n in graph.values() if not n.imported_by and not n.name.endswith("__init__")]

    lines = [
        "# Index",
        "",
        f"Generated from `{source}`.",
        "",
        f"- **Modules:** {len(graph)}",
        f"- **Internal edges:** {sum(len(n.imports) for n in graph.values())}",
        f"- **Total code lines:** {sum(n.code_lines for n in graph.values())}",
        "",
        "## Most depended upon",
        "",
        "| Module | Imported by | Depends on | LOC |",
        "|---|---|---|---|",
    ]
    lines += [
        f"| [[{note_name(n.name)}]] | {len(n.imported_by)} | {len(n.imports)} | {n.code_lines} |"
        for n in hubs
    ]
    lines += [
        "",
        "## Busiest modules (total connections)",
        "",
    ]
    lines += [f"- [[{note_name(n.name)}]] — {n.degree}" for n in by_degree[:10]]
    lines += [
        "",
        "## Nothing imports these",
        "",
        "Entry points, or dead code — worth checking which.",
        "",
    ]
    lines += [f"- [[{note_name(n.name)}]]" for n in orphans[:20]] or ["_(none)_"]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Write the vault. Returns 0 on success."""
    parser = argparse.ArgumentParser(description="Generate an Obsidian vault from Python source.")
    parser.add_argument("--source", type=Path, required=True, help="Directory containing packages.")
    parser.add_argument("--out", type=Path, default=ROOT / "vaults" / "reference-graph")
    parser.add_argument("--clean", action="store_true", help="Delete the output folder first.")
    args = parser.parse_args(argv)

    source = args.source.resolve()
    if not source.is_dir():
        raise SystemExit(f"Source directory not found: {source}")

    graph = build_graph(source)
    if not graph:
        raise SystemExit(f"No Python modules found under {source}")

    if args.clean and args.out.exists():
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True, exist_ok=True)

    for node in graph.values():
        (args.out / f"{note_name(node.name)}.md").write_text(render_note(node), encoding="utf-8")
    (args.out / "_index.md").write_text(render_index(graph, source), encoding="utf-8")

    edges = sum(len(n.imports) for n in graph.values())
    print(f"Vault written to {args.out}")
    print(f"  {len(graph)} modules, {edges} internal edges")
    print("\nOpen it in Obsidian:  Open folder as vault -> select the folder above -> Ctrl+G")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
