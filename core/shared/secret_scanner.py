"""Detect committed credentials before they reach either repository.

Appendix E rules #39 and #40: a secret pushed once is considered permanently
exposed. Deleting it in a later commit does not help — it stays in the Git
history. The only reliable defence is never committing it.

Pure Python rather than a shell script so the same check runs on Windows,
macOS and the CI runner without depending on `bash` being on PATH.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "Finding",
    "SECRET_PATTERNS",
    "scan_text",
    "scan_staged",
    "scan_tracked",
    "scan_history",
]

# Anchored on real key shapes. The PEM header keeps its dashes so that prose
# such as "no BEGIN PRIVATE KEY in the repo" does not trip the scan.
SECRET_PATTERNS: tuple[tuple[str, str], ...] = (
    ("Groq API key", r"gsk_[A-Za-z0-9]{20,}"),
    ("Anthropic API key", r"sk-ant-[A-Za-z0-9-]{24,}"),
    ("OpenAI API key", r"sk-[A-Za-z0-9]{32,}"),
    ("Google API key", r"AIza[A-Za-z0-9_-]{30,}"),
    ("Private key block", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("Google OAuth client secret", r"GOCSPX-[A-Za-z0-9_-]{20,}"),
)

_COMPILED = tuple((label, re.compile(pattern)) for label, pattern in SECRET_PATTERNS)

# The scanner's own pattern table would otherwise match itself.
_SELF_EXEMPT = ("core/shared/secret_scanner.py", "tests/unit/test_secret_scanner.py")


@dataclass(frozen=True)
class Finding:
    """One suspected secret.

    Attributes:
        label: Human-readable kind, e.g. "Groq API key".
        location: File path or diff position where it was seen.
        line: The offending line, truncated for safe display.
    """

    label: str
    location: str
    line: str

    def __str__(self) -> str:
        """Render the finding for terminal output."""
        return f"  {self.label}\n    {self.location}\n    {self.line[:100]}"


def _is_exempt(relative: str) -> bool:
    """Return True for files whose contents are documentation, not credentials.

    Only two things are exempt: the scanner's own pattern table and its tests,
    which necessarily contain every shape it looks for, and lockfiles, which are
    machine-generated hashes.

    ``.env-example`` is deliberately **not** exempt. It is the single most likely
    place for someone to paste a real key "just to test", and the whole point of
    this scan is to catch that before it is pushed. Its placeholders are written
    short enough (``gsk_replace_me``) not to match a real key's shape.
    """
    return relative in _SELF_EXEMPT or relative.endswith(".lock")


def scan_text(text: str, location: str = "<text>") -> list[Finding]:
    """Return every suspected secret in *text*."""
    findings: list[Finding] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for label, pattern in _COMPILED:
            if pattern.search(line):
                findings.append(Finding(label, f"{location}:{number}", line.strip()))
    return findings


def _git(args: list[str], root: Path) -> str:
    """Run a git command in *root* and return stdout, or an empty string."""
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False
    )
    return result.stdout if result.returncode == 0 else ""


def scan_staged(root: Path) -> list[Finding]:
    """Scan changes staged for commit. Used by the pre-commit hook."""
    diff = _git(["diff", "--cached", "-U0"], root)
    added = "\n".join(
        line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")
    )
    return scan_text(added, "staged changes")


def scan_history(root: Path) -> list[Finding]:
    """Scan every line ever added on any branch (M#39, 0.QG.3).

    ``scan_tracked`` only sees the current checkout, so a key that was committed
    and then deleted passes it while remaining permanently readable in the
    history. This walks the full diff of every reachable commit instead.

    A hit here cannot be fixed by editing a file. The history must be rewritten
    and the key rotated, because it is already public.

    Added lines are grouped by the file they belong to so the same exemptions
    apply as in ``scan_tracked`` — without them the scanner's own pattern table
    and test fixtures report themselves. Reported line numbers count added lines
    for that file across all commits, not positions in any single revision.
    """
    added: dict[str, list[str]] = {}
    current = "<unknown>"
    for line in _git(["log", "--all", "-p", "-U0", "--no-color"], root).splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
        elif line.startswith("+") and not line.startswith("+++") and not _is_exempt(current):
            added.setdefault(current, []).append(line[1:])

    findings: list[Finding] = []
    for path, lines in added.items():
        findings.extend(scan_text("\n".join(lines), f"git history: {path}"))
    return findings


def scan_tracked(root: Path) -> list[Finding]:
    """Scan every file git is tracking. Used by CI and before publishing."""
    listing = _git(["ls-files"], root)
    findings: list[Finding] = []
    for relative in listing.splitlines():
        if _is_exempt(relative):
            continue
        path = root / relative
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # binary or unreadable: nothing to match against
        findings.extend(scan_text(text, relative))
    return findings
