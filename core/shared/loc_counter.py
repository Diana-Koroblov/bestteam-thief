"""Lines-of-code counting for the 150-line rule (excellence guide §3.2).

Counting rules
--------------
A line counts as code unless it is one of:

* blank (whitespace only),
* a pure comment line (first non-space character is ``#``),
* part of a *docstring* — the module, class or function documentation string.

**Why docstrings are excluded.** The excellence guide states that blank and
comment lines do not count, and separately *mandates* a detailed docstring on
every module, class and function (§3.3). Counting docstrings would put those two
requirements in direct conflict: the better a file is documented, the closer it
would sit to the limit. We read a docstring as documentation rather than code.
This interpretation is recorded in ``docs/CONTRADICTIONS.md``.

Only genuine docstrings are excluded. A triple-quoted string assigned to a
variable is data and counts as code.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from core.shared.constants import EXCLUDED_DIR_NAMES, MAX_FILE_LOC, SOURCE_ROOTS

__all__ = ["FileReport", "count_code_lines", "iter_python_files", "find_oversized"]

_DOCSTRING_OWNERS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


@dataclass(frozen=True)
class FileReport:
    """Line accounting for a single source file.

    Attributes:
        path: File location, relative to the project root when available.
        code_lines: Lines that count against the limit.
        total_lines: Every physical line, for context in the report output.

    Note:
        There is deliberately no ``is_oversized`` property. The limit is a
        parameter of :func:`find_oversized`, not a property of a file, and a
        cached global would silently disagree with a custom ``--limit``.
    """

    path: Path
    code_lines: int
    total_lines: int


def _docstring_line_numbers(source: str) -> set[int]:
    """Return every 1-based line number occupied by a docstring.

    A syntax error yields an empty set: an unparseable file is still counted,
    just without the docstring exemption. The linter will flag it separately.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()

    lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, _DOCSTRING_OWNERS):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        # A docstring is a bare string expression in first position.
        if not isinstance(first, ast.Expr) or not isinstance(first.value, ast.Constant):
            continue
        if not isinstance(first.value.value, str):
            continue
        end = first.end_lineno or first.lineno
        lines.update(range(first.lineno, end + 1))
    return lines


def count_code_lines(path: Path) -> FileReport:
    """Count the code lines in *path* under the rules described in the module docstring."""
    source = path.read_text(encoding="utf-8")
    physical = source.splitlines()
    skip = _docstring_line_numbers(source)

    code = 0
    for number, text in enumerate(physical, start=1):
        if number in skip:
            continue
        stripped = text.strip()
        if not stripped or stripped.startswith("#"):
            continue
        code += 1

    return FileReport(path=path, code_lines=code, total_lines=len(physical))


def iter_python_files(root: Path, roots: tuple[str, ...] = SOURCE_ROOTS):
    """Yield every ``.py`` file under *roots*, skipping excluded directories."""
    for name in roots:
        base = root / name
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
                continue
            yield path


def find_oversized(
    root: Path,
    limit: int = MAX_FILE_LOC,
    roots: tuple[str, ...] = SOURCE_ROOTS,
) -> list[FileReport]:
    """Return every oversized file, worst first.

    Args:
        root: Project root directory.
        limit: Maximum permitted code lines per file.
        roots: Top-level directories to walk.
    """
    reports = [count_code_lines(path) for path in iter_python_files(root, roots)]
    offenders = [report for report in reports if report.code_lines > limit]
    return sorted(offenders, key=lambda report: report.code_lines, reverse=True)
