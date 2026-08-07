"""Show this machine's Step-0 declaration (TODO 6.3, M#24, M#53).

    uv run python scripts/step_zero_demo.py

Run once on each machine. It is how 6.3.1's "works on both machines" is closed,
and it is worth reading before the first graded match: the warnings at the
bottom are the things a grader would otherwise discover for us.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.infra.llm.factory import model_name  # noqa: E402
from core.protocol.step_zero import build  # noqa: E402
from core.shared.config_manager import load_config  # noqa: E402

__all__ = ["main"]


def main() -> int:
    """Build the declaration and print it, warnings last."""
    role = "police" if (ROOT / "config" / "police" / "game.json").is_file() else "thief"
    config = load_config(ROOT / "config" / role)
    declaration = build(
        team_name=str(config.get("identity.team_name", "bestteam")),
        role="cop" if role == "police" else "thief",
        sub_game=1,
        # Not `llm.ollama_model`, which this script used to read directly: on a
        # machine whose .env selects template or groq that declares a model we
        # never call, and Appendix F Table 21 makes the model the declared thing.
        llm_model=model_name(config),
        repo=ROOT,
    )

    # Bytes, not print: a Windows console is cp1252 and a Hebrew team name
    # would raise UnicodeEncodeError here. See TODO 6.5.2.
    body = json.dumps(declaration.payload, indent=2, sort_keys=True, ensure_ascii=False)
    sys.stdout.buffer.write((body + "\n").encode("utf-8"))

    print(f"\n  digest: {declaration.digest}")
    warnings = declaration.warnings()
    if not warnings:
        print("  no warnings - this machine is ready for a graded match.")
    for warning in warnings:
        print(f"  *** {warning} ***")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
