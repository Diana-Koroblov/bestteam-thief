"""Guard test: no source file may exceed the 150-line limit.

This runs inside the normal suite so the rule is enforced on every `pytest`
invocation, not only when the CLI script is remembered.
"""

from __future__ import annotations

from pathlib import Path

from core.shared.constants import MAX_FILE_LOC
from core.shared.loc_counter import find_oversized

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_no_source_file_exceeds_the_loc_limit() -> None:
    """Every tracked Python file stays within MAX_FILE_LOC code lines."""
    offenders = find_oversized(PROJECT_ROOT)

    detail = "\n".join(
        f"  {report.code_lines} lines - {report.path.relative_to(PROJECT_ROOT)}"
        for report in offenders
    )
    assert not offenders, (
        f"{len(offenders)} file(s) exceed {MAX_FILE_LOC} code lines. Split them:\n{detail}"
    )
