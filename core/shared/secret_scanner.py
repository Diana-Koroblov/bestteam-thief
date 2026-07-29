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

__all__ = ["Finding", "SECRET_PATTERNS", "scan_text", "scan_staged", "scan_tracked"]

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


def scan_tracked(root: Path) -> list[Finding]:
    """Scan every file git is tracking. Used by CI and before publishing."""
    listing = _git(["ls-files"], root)
    findings: list[Finding] = []
    for relative in listing.splitlines():
        if relative in _SELF_EXEMPT or relative.endswith((".example", ".lock")):
            continue
        path = root / relative
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # binary or unreadable: nothing to match against
        findings.extend(scan_text(text, relative))
    return findings
