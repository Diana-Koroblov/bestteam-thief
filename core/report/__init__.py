"""Match artefacts: the JSON a grader actually reads (TODO 7.2).

Four files per match, all named from one shared `game_id` so reports from ten
teams cannot collide in the grader's inbox.

Everything here is written as **UTF-8 bytes**, explicitly. Team names and hints
may be Hebrew, and a Windows console defaults to cp1252 — which raises
`UnicodeEncodeError` mid-match on Diana's machine and never on a CI runner. That
cost us an afternoon in 6.5.2 and is now a rule rather than a memory.
"""

from core.report.artefacts import (
    ArtefactError,
    build_config_snapshot,
    build_declaration,
    build_result,
    payload_digest,
    write,
)
from core.report.identifiers import artefact_name, game_id
from core.report.match_log import build_log, build_step, records, verify_log

__all__ = [
    "ArtefactError",
    "game_id",
    "artefact_name",
    "build_declaration",
    "build_config_snapshot",
    "build_log",
    "build_step",
    "build_result",
    "records",
    "verify_log",
    "payload_digest",
    "write",
]
