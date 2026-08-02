"""Match artefacts: the JSON a grader actually reads (TODO 7.2).

Four files per match, all named from one shared `game_id` so reports from ten
teams cannot collide in the grader's inbox.

Everything here is written as **UTF-8 bytes**, explicitly. Team names and hints
may be Hebrew, and a Windows console defaults to cp1252 — which raises
`UnicodeEncodeError` mid-match on Diana's machine and never on a CI runner. That
cost us an afternoon in 6.5.2 and is now a rule rather than a memory.
"""

from core.report.artefacts import build_declaration, build_result, write
from core.report.identifiers import artefact_name, game_id

__all__ = ["game_id", "artefact_name", "build_declaration", "build_result", "write"]
