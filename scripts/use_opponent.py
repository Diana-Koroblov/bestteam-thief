"""Switch the shared contract to one opponent's agreed terms, without re-typing them.

    uv run python scripts/use_opponent.py --list
    uv run python scripts/use_opponent.py --team yanell11
    uv run python scripts/use_opponent.py --team yanell11 --dry-run

Playing several opponents out of one working tree means `config/police/game.json`
and `config/thief/game.json` hold whichever team we negotiated with *last* - and
re-typing the diff by hand each time a match is retried is exactly how a stale
term (wrong setting, wrong decay model) survives into a handshake. Each opponent
instead gets one folder under `config/opponents/<team_id>/`:

    game.json   the full negotiated contract, copied byte-identical into BOTH
                config/police/game.json and config/thief/game.json
    match.json  what is not IN game.json but still varies per opponent: which
                wire protocol they speak, who opens, the role-split shape,
                whether the match is counted, and their last-declared commit

This only replaces the two `game.json` files. It does not commit or publish -
run `scripts/ship.py` afterwards for that, same as any other config change.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.shared.config_spec import violations  # noqa: E402

OPPONENTS_DIR = ROOT / "config" / "opponents"
TARGETS = (ROOT / "config" / "police" / "game.json", ROOT / "config" / "thief" / "game.json")


def _flatten(data: Any, prefix: str = "") -> dict[str, Any]:
    """Return *data* as {dotted.path: leaf value}, for a readable diff."""
    if not isinstance(data, dict):
        return {prefix: data}
    out: dict[str, Any] = {}
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        out.update(_flatten(value, path))
    return out


def _diff(old: dict, new: dict) -> list[str]:
    """Return one readable line per leaf that *new* changes relative to *old*."""
    before, after = _flatten(old), _flatten(new)
    lines = []
    for path in sorted(set(before) | set(after)):
        was, now = before.get(path, "<absent>"), after.get(path, "<absent>")
        if was != now:
            lines.append(f"  {path}: {was!r} -> {now!r}")
    return lines


def list_opponents() -> int:
    """Print every known profile and whether its match.json is fully settled."""
    if not OPPONENTS_DIR.is_dir():
        print(f"no {OPPONENTS_DIR} yet")
        return 0
    for folder in sorted(OPPONENTS_DIR.iterdir()):
        match_path = folder / "match.json"
        if not (folder / "game.json").is_file():
            continue
        match = json.loads(match_path.read_text()) if match_path.is_file() else {}
        unsettled = [k for k, v in match.items() if v in (None, [], "")]
        status = "ready" if not unsettled else f"not settled: {', '.join(unsettled)}"
        print(f"  {folder.name:<12} {status}")
    return 0


def apply_opponent(team: str, dry_run: bool) -> int:
    """Copy *team*'s profile into both game.json files and print the play commands."""
    folder = OPPONENTS_DIR / team
    game_path, match_path = folder / "game.json", folder / "match.json"
    if not game_path.is_file():
        print(f"[FAIL]  no profile at {game_path}", file=sys.stderr)
        return 1

    profile = json.loads(game_path.read_text())
    breaches = violations(profile)
    if breaches:
        print("[FAIL]  this profile breaches Appendix F - fix it before playing:")
        for line in breaches:
            print(f"    {line}")
        return 1

    current = json.loads(TARGETS[0].read_text()) if TARGETS[0].is_file() else {}
    diff = _diff(current, profile)
    print(f"[ .. ]  {team}: {len(diff)} field(s) changing")
    for line in diff:
        print(line)

    if dry_run:
        print("[ OK ]  dry run - nothing was written")
        return 0

    for target in TARGETS:
        shutil.copy2(game_path, target)
    print(f"[ OK ]  wrote {team}'s contract into {TARGETS[0]} and {TARGETS[1]}")

    match = json.loads(match_path.read_text()) if match_path.is_file() else {}
    unsettled = [k for k in ("protocol", "first", "role_split") if not match.get(k)]
    if unsettled:
        print(f"[WARN]  {match_path} is missing: {', '.join(unsettled)} - settle with them first")
        return 0

    flag = " --protocol reference" if match["protocol"] == "reference" else ""
    counted = " --counted" if match.get("counted") else ""
    report_to = ",".join(match.get("report_to") or [])
    if not match.get("counted") and report_to:
        counted = f' --report-to "{report_to}"'
    # Opponents that run two processes (like us) declare one commit and one
    # endpoint PER ROLE. Our cop always faces their thief and vice versa, so
    # each of our two invocations needs the OTHER role's commit/URL. Falls
    # back to a single their_commit/placeholder URL for an opponent (like
    # yanell11) that only ever gave us one of each.
    for role, other in (("cop", "thief"), ("thief", "cop")):
        commit_value = match.get(f"their_commit_{other}") or match.get("their_commit")
        commit = f" --their-commit {commit_value}" if commit_value else ""
        opponent = match.get(f"their_endpoint_{other}") or "https://<THEIR-URL>/mcp"
        print(
            f"\nuv run python -m core play --role {role}{flag} --tunnel "
            f'--first {match["first"]} --role-split {match["role_split"]}{commit} '
            f"--out results\\{counted} --opponent {opponent}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse the command line and dispatch. Returns a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--team", help="Opponent folder name under config/opponents/.")
    parser.add_argument("--list", action="store_true", help="List known opponent profiles.")
    parser.add_argument("--dry-run", action="store_true", help="Show the diff, write nothing.")
    args = parser.parse_args(argv)

    if args.list or not args.team:
        return list_opponents()
    return apply_opponent(args.team, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
