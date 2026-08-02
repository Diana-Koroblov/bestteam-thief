"""Show the verbal layer working, on whichever provider this machine has.

    uv run python scripts/hint_demo.py                    # template, offline
    uv run python scripts/hint_demo.py --provider groq    # Diana's machine
    uv run python scripts/hint_demo.py --provider ollama  # Itay's machine

The ``--provider`` flag exists so nobody has to set an environment variable
correctly under pressure. The syntax differs between PowerShell, cmd and bash,
and getting it wrong fails **silently** — straight into the template bank, which
looks exactly like success.

Prints the provider that **actually** wrote each line, which is the whole point:
the fallback is deliberately silent during a match, so this is the only way to
confirm Groq or Ollama is really being used rather than quietly erroring.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.domain.intent import Intent  # noqa: E402
from core.infra.llm import build_writer  # noqa: E402
from core.shared.config_manager import load_config  # noqa: E402
from core.shared.env import load_env  # noqa: E402

__all__ = ["main"]

TURNS = [("north", Intent.TRUTH), ("west", Intent.LIE), ("", Intent.TRUTH)]


def main(argv: list[str] | None = None) -> int:
    """Write one hint per direction and report which provider produced it."""
    parser = argparse.ArgumentParser(description="Exercise the verbal channel.")
    parser.add_argument(
        "--provider",
        choices=("template", "ollama", "groq"),
        help="Override for this run only. Without it, .env then game.toml decide.",
    )
    args = parser.parse_args(argv)

    # Must happen before build_writer: the keys live in .env, and nothing inside
    # core calls load_dotenv on its own (see core/shared/env.py).
    found = load_env(ROOT)
    if args.provider:
        os.environ["P2P_LLM_PROVIDER"] = args.provider

    role = "police" if (ROOT / "config" / "police" / "game.json").is_file() else "thief"
    writer = build_writer(load_config(ROOT / "config" / role))

    print(f"  .env loaded     : {'yes' if found else 'NO - no .env file found'}")
    print(f"  provider asked  : {writer.provider.name}")
    print(f"  word cap        : {writer.max_words}")
    print(f"  never fabricate : {', '.join(writer.forbidden) or '(none)'}\n")

    used = set()
    for step, (direction, intent) in enumerate(TURNS, start=1):
        hint = writer.write(direction, intent, step)
        used.add(hint.provider)
        print(f"  turn {step}  [{intent.value:5}]  {hint.text}")
        print(f"            written by: {hint.provider}")
        for problem in hint.rejected:
            print(f"            rejected  : {problem}")

    _verdict(writer.provider.name, used)
    return 0


def _verdict(asked: str, used: set[str]) -> None:
    """Say plainly whether the requested provider actually spoke.

    Without this the output looks identical whether Groq answered or the key was
    missing — which is precisely the failure that would otherwise surface
    mid-match, when it is far too late to fix.
    """
    if asked == "template":
        print("\n  OK - template bank, offline and free. This is the committed default.")
    elif used == {asked}:
        print(f"\n  OK - {asked} wrote every line.")
    else:
        print(
            f"\n  *** {asked} was requested but did NOT write these lines. ***"
            "\n      The 'rejected' lines above say why - usually a missing key in"
            "\n      .env, or the service unreachable. A match would still run,"
            "\n      on template output, which is the point of the fallback."
        )


if __name__ == "__main__":
    raise SystemExit(main())
