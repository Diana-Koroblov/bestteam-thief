"""Unit tests for the line-of-code counter.

Covers the happy path and the error path of every public function, per the
excellence guide's testing rules (§6.1).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.shared.loc_counter import count_code_lines, find_oversized, iter_python_files


def _write(tmp_path: Path, name: str, body: str) -> Path:
    """Write *body* to *name* under *tmp_path* and return the path."""
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_blank_lines_do_not_count(tmp_path: Path) -> None:
    """Whitespace-only lines are excluded."""
    path = _write(tmp_path, "m.py", "x = 1\n\n\n   \ny = 2\n")
    assert count_code_lines(path).code_lines == 2


def test_comment_lines_do_not_count(tmp_path: Path) -> None:
    """Lines whose first non-space character is '#' are excluded."""
    path = _write(tmp_path, "m.py", "# header\nx = 1\n    # indented note\ny = 2\n")
    assert count_code_lines(path).code_lines == 2


def test_a_file_of_only_comments_counts_as_zero(tmp_path: Path) -> None:
    """200 comment lines still count as zero code lines."""
    path = _write(tmp_path, "m.py", "# note\n" * 200)
    assert count_code_lines(path).code_lines == 0


def test_docstrings_do_not_count(tmp_path: Path) -> None:
    """Module, class and function docstrings are documentation, not code."""
    body = (
        '"""Module doc.\n\nSpanning several lines.\n"""\n'
        "class C:\n"
        '    """Class doc."""\n'
        "    def m(self):\n"
        '        """Method doc."""\n'
        "        return 1\n"
    )
    path = _write(tmp_path, "m.py", body)
    # class C / def m / return 1
    assert count_code_lines(path).code_lines == 3


def test_a_triple_quoted_assignment_counts_as_code(tmp_path: Path) -> None:
    """A triple-quoted string bound to a name is data, not a docstring."""
    path = _write(tmp_path, "m.py", 'TEMPLATE = """\nline\n"""\n')
    assert count_code_lines(path).code_lines == 3


def test_a_leading_non_string_constant_is_not_a_docstring(tmp_path: Path) -> None:
    """A bare number in first position is code, not documentation."""
    path = _write(tmp_path, "m.py", "42\nx = 1\n")
    assert count_code_lines(path).code_lines == 2


def test_an_empty_body_is_handled(tmp_path: Path) -> None:
    """A module with no statements does not break the docstring scan."""
    path = _write(tmp_path, "m.py", "\n\n")
    assert count_code_lines(path).code_lines == 0


def test_unparseable_file_still_counts(tmp_path: Path) -> None:
    """A syntax error loses the docstring exemption but never crashes the guard."""
    path = _write(tmp_path, "m.py", "def broken(:\n    pass\n")
    assert count_code_lines(path).code_lines == 2


def test_total_lines_reports_every_physical_line(tmp_path: Path) -> None:
    """total_lines is the raw physical count, for context in reports."""
    path = _write(tmp_path, "m.py", "# c\n\nx = 1\n")
    report = count_code_lines(path)
    assert report.total_lines == 3
    assert report.code_lines == 1


def test_iter_python_files_skips_excluded_directories(tmp_path: Path) -> None:
    """__pycache__ and friends are never walked."""
    _write(tmp_path, "core/keep.py", "x = 1\n")
    _write(tmp_path, "core/__pycache__/skip.py", "x = 1\n")
    found = {p.name for p in iter_python_files(tmp_path, roots=("core",))}
    assert found == {"keep.py"}


def test_iter_python_files_tolerates_a_missing_root(tmp_path: Path) -> None:
    """A configured root that does not exist is skipped, not an error."""
    assert list(iter_python_files(tmp_path, roots=("nope",))) == []


def test_find_oversized_returns_offenders_worst_first(tmp_path: Path) -> None:
    """Offenders are sorted by code_lines, descending."""
    _write(tmp_path, "core/small.py", "x = 1\n" * 2)
    _write(tmp_path, "core/medium.py", "x = 1\n" * 6)
    _write(tmp_path, "core/large.py", "x = 1\n" * 9)

    offenders = find_oversized(tmp_path, limit=5, roots=("core",))

    assert [p.path.name for p in offenders] == ["large.py", "medium.py"]
    assert [p.code_lines for p in offenders] == [9, 6]


def test_find_oversized_returns_empty_when_all_within_limit(tmp_path: Path) -> None:
    """The happy path returns no offenders."""
    _write(tmp_path, "core/ok.py", "x = 1\n" * 3)
    assert find_oversized(tmp_path, limit=150, roots=("core",)) == []


@pytest.mark.parametrize("count", [149, 150])
def test_limit_is_inclusive(tmp_path: Path, count: int) -> None:
    """150 lines passes; the breach begins at 151."""
    _write(tmp_path, "core/edge.py", "x = 1\n" * count)
    assert find_oversized(tmp_path, roots=("core",)) == []


def test_one_line_over_the_limit_fails(tmp_path: Path) -> None:
    """151 code lines is a breach."""
    _write(tmp_path, "core/edge.py", "x = 1\n" * 151)
    offenders = find_oversized(tmp_path, roots=("core",))
    assert len(offenders) == 1
    assert offenders[0].code_lines == 151
