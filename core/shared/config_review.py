"""Reading a configuration the **opponent** proposed (TODO 9.1.1, TN.6-TN.8).

`load_config` refuses an illegal configuration, which is right for our own and
useless for theirs: a proposal we cannot load is a proposal we cannot quote back.
Its `enforce_rules=False` escape hatch was written for exactly this and had no
caller until now — the same wired-to-nothing shape as the verbal layer and 4.1.6.

**Why this is not merely a courtesy.** M#12 disqualifies **both** teams for an
illegal value, so "the opponent proposed it" is not a defence. The check that
stops us signing one has to run before we agree, not when we try to load it, and
it has to name the rule so the conversation that follows is about a rule rather
than about whose code refused.

Three lists, because three different things happen next. **Illegal** refuses.
**Absent** is settled with a human before the first move. **Changes** are legal
and are a judgement call — raising a minimum is always permitted and sometimes
against our interest (PRD_negotiation §3.3).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.crypto.canonical import digest
from core.shared import config_spec, version

__all__ = ["Review", "review", "review_file"]


@dataclass(frozen=True)
class Review:
    """What an opponent's proposed shared configuration would commit us to.

    Attributes:
        illegal: Appendix F breaches. Refuse; agreeing disqualifies both (M#12).
        absent: Keys the proposal does not carry, each saying whether it is an
            Appendix F parameter or one of the six we invented.
        changes: Legal differences from our own proposal, with the status that
            makes each one legal.
        unknown: Keys we do not recognise. Not an error — a team may have their
            own extensions exactly as we do — but an unrecognised key is one
            nothing on our side reads, and silently ignoring it is how two peers
            come to believe different things about the same file.
        sha256: What `config_sha256` becomes if we adopt this verbatim, so the
            M#11 comparison can be predicted rather than discovered.
    """

    proposed: dict
    illegal: tuple[str, ...] = ()
    absent: tuple[str, ...] = ()
    changes: tuple[str, ...] = ()
    unknown: tuple[str, ...] = ()
    sha256: str = ""

    @property
    def playable(self) -> bool:
        """Whether signing this would be legal. Not whether it is wise."""
        return not self.illegal

    def report(self) -> str:
        """Return the whole review as text, for a terminal or an email."""
        lines = [f"config_sha256 if adopted: {self.sha256}"]
        for title, items in (
            ("REFUSE - Appendix F breaches (M#12 disqualifies BOTH teams)", self.illegal),
            ("SETTLE BEFORE PLAY - not stated in their proposal", self.absent),
            ("LEGAL CHANGES from ours - judgement call", self.changes),
            ("UNRECOGNISED keys - nothing on our side reads these", self.unknown),
        ):
            if items:
                lines.append(f"\n{title}:")
                lines.extend(f"  - {item}" for item in items)
        if self.playable:
            lines.append("\nNo Appendix F breach: this configuration is legal to sign.")
        return "\n".join(lines)


def _leaf_paths(node: Any, prefix: str = "") -> Iterator[str]:
    """Yield every dotted path to a non-mapping value in *node*."""
    if not isinstance(node, dict):
        return
    for key, value in node.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            yield from _leaf_paths(value, f"{path}.")
        else:
            yield path


def _changes(theirs: dict, ours: dict) -> list[str]:
    """Return the **legal** differences between two proposals, with their status.

    An illegal value is deliberately absent from this list. It is already in
    `illegal`, and a review that offered a lowered minimum as a judgement call
    two lines below refusing it would be a document that contradicts itself in
    front of the opponent it is meant to convince.
    """
    found = []
    for parameter in config_spec.PARAMETERS:
        mine = config_spec.dotted_get(ours, parameter.path, None)
        yours = config_spec.dotted_get(theirs, parameter.path, None)
        if yours is None or mine is None or yours == mine:
            continue
        if not config_spec.legal(parameter, yours):
            continue
        note = f"{parameter.status}"
        if parameter.status == config_spec.MINIMUM:
            note += f", raised above the floor of {parameter.default!r} - always legal (M#12)"
        elif parameter.ours:
            note += ", our own extension"
        found.append(f"{parameter.path}: we propose {mine!r}, they propose {yours!r} ({note})")
    return found


def review(theirs: dict, ours: dict) -> Review:
    """Compare an opponent's proposed shared config against ours and the rules.

    Args:
        theirs: Their ``game.json``, parsed. Never merged with a private file —
            the shared contract is the only part either peer agrees to, and
            merging would review a document neither of us would sign.
        ours: Our own shared config, for the difference report.
    """
    illegal, absent = config_spec.classify(theirs)
    illegal += config_spec.invariant_violations(theirs)
    declared = str(theirs.get("version", ""))
    if not version.is_compatible(declared):
        illegal.append(
            f"version {declared or '<none>'} cannot be read by this code (version "
            f"{version.VERSION}); a config we cannot load is one we cannot audit"
        )
    known = {parameter.path for parameter in config_spec.PARAMETERS} | {"version"}
    return Review(
        proposed=theirs,
        illegal=tuple(illegal),
        absent=tuple(absent),
        changes=tuple(_changes(theirs, ours)),
        unknown=tuple(sorted(set(_leaf_paths(theirs)) - known)),
        sha256=digest(theirs),
    )


def review_file(path: Path, ours: dict) -> Review:
    """Review the proposal saved at *path*.

    Read as raw JSON rather than through `load_config`, which would refuse the
    very files this exists to examine and would layer our private TOML on top of
    a document the opponent never saw.
    """
    import json

    try:
        return review(json.loads(Path(path).read_text(encoding="utf-8")), ours)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read the proposed configuration at {path}: {error}") from error
