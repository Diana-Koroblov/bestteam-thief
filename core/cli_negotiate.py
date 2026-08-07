"""The pre-match protocol, as a command (TODO 9.1).

    python -m core negotiate --role cop                        our side, printed
    python -m core negotiate --role cop --pack outbox/         what we send them
    python -m core negotiate --role cop --review their.json    what they sent us
    python -m core negotiate --role cop --opponent <url> --out results/

Split out of `cli_commands.py` at 110 of its 150 lines rather than compressed
into it. The seam is real: `serve`, `handshake` and `replay` each do one thing to
a running peer, and this is a four-part protocol that happens once per match,
from a terminal, minutes before the first move.

**Everything here exits non-zero when the answer is no.** A refused match costs
nothing and a disputed one scores 0 for both teams (M#35), so a script that reads
the exit code must never start a match the comparison rejected.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.sdk.peer_sdk import PeerSDK

__all__ = ["negotiate"]

PACK_README = """# Pre-match agreement - {team}

Everything in this directory is what we propose for our match. Three files:

| File | What to do with it |
|---|---|
| `game.json` | The shared contract. Load it **byte-identically**; a differing digest refuses the match rather than starting one that cannot be audited (M#11). |
| `handshake.json` | Exactly what our peer sends on the wire, so you can diff it against yours before we connect. |
| this file | The clauses that are not in any Appendix and must be agreed in writing. |

## Digests to compare

    config_sha256      {config}
    scent_model_sha256 {scent}
    github_commit      {commit}

We have played **{games}** counted matches so far (M#37), and we propose a
**{split}** role split across the six sub-games (N17 - it is in no Appendix, so
silence would mean we each assume something different).

## The clauses

{clause}

## What we need back

1. Your `config_sha256` over the file above, or your counter-proposal.
2. Your decay model's worked example. **If your answer is 0.800 rather than
   0.810 we are running different physics** and the end-of-match audit would
   report forgery against two honest teams - so it is worth settling now.
3. Whether the three capture readings above match your implementation.
4. Your counted-match total, and the role split you expect.

We are happy to play either reading of any of these; all of them are config
flags on our side, so agreeing costs us a config change and not a code change.
"""


def negotiate(sdk: PeerSDK, args: argparse.Namespace) -> int:
    """Run whichever part of the pre-match protocol was asked for."""
    if args.review:
        return _review(sdk, Path(args.review))

    prematch = sdk.prematch
    prematch.role_split = args.role_split
    ours = prematch.proposal()
    print(f"config_sha256     : {ours.config_digest}")
    print(f"scent_model_sha256: {ours.scent_model_digest}")
    print(f"github_commit     : {ours.step_zero.get('github_commit', '')}")
    print(f"counted matches   : {ours.game_count}  (from docs/LEAGUE_LOG.md, M#37)")
    print(f"role split        : {ours.role_split}")
    print(f"\n--- paste this to the opponent (9.1.6) ---\n{prematch.clause()}\n")

    if args.pack:
        print(f"pack written      : {_pack(sdk, prematch, ours, Path(args.pack))}\n")
    if not args.opponent:
        _print_warnings(prematch.warnings())
        return 0

    import asyncio

    return asyncio.run(_exchange(sdk, prematch, ours, args))


def _review(sdk: PeerSDK, path: Path) -> int:
    """Report what an opponent's proposed config would commit us to (TN.6-TN.8).

    Deliberately before our own proposal is built: reviewing *their* file must
    not fail because *our* league log has a typo in it. Exits 1 on an Appendix F
    breach, because agreeing to one disqualifies both teams and "they proposed
    it" is not a defence (M#12).
    """
    from core.shared.config_review import review_file

    found = review_file(path, sdk.shared_config)
    print(f"reviewing {path}\n")
    print(found.report())
    return 0 if found.playable else 1


def _pack(sdk: PeerSDK, prematch, ours, directory: Path) -> Path:
    """Write everything an opponent needs, in one directory (9.1.1-9.1.8).

    One command rather than a terminal dump a human retypes into an email. The
    config travels as the **file we hash**, not as a description of it: a
    paraphrase is exactly how two peers come to hold configurations that differ
    in a byte and agree in prose.
    """
    directory.mkdir(parents=True, exist_ok=True)
    _write(directory / "game.json", json.dumps(sdk.shared_config, indent=2, sort_keys=True))
    _write(directory / "handshake.json", json.dumps(ours.payload(), indent=2, sort_keys=True))
    _write(
        directory / "AGREEMENT.md",
        PACK_README.format(
            team=sdk.team_name,
            config=ours.config_digest,
            scent=ours.scent_model_digest,
            commit=ours.step_zero.get("github_commit", ""),
            games=ours.game_count,
            split=ours.role_split,
            clause=prematch.clause(),
        ),
    )
    return directory


def _write(path: Path, body: str) -> None:
    """Write UTF-8 bytes explicitly; a team name may be Hebrew and a Windows
    console is cp1252. Same reason `report/artefacts.write` does it."""
    path.write_bytes((body + "\n").encode("utf-8"))


async def _exchange(sdk: PeerSDK, prematch, ours, args: argparse.Namespace) -> int:
    """Send our handshake, settle the reply, and file the outcome."""
    from core.infra.errors import PeerError
    from core.protocol.tools import decode_negotiation

    if sdk.opponent is None:
        sdk.connect(args.opponent)
    # Only one side of this exchange receives a verdict. Whoever answers raises;
    # whoever asked gets a remote error string. Without this catch the initiator
    # would learn of a refusal as a traceback and file nothing - losing the
    # record of the outcome most likely to be argued about.
    try:
        theirs = decode_negotiation(await sdk.opponent.call("negotiate", ours.payload()))
    except PeerError as error:
        locked, theirs = prematch.refused(str(error)), None
    else:
        locked = prematch.settle(theirs)

    print(f"result            : {locked.result}")
    # Printed only when they answered. After a refusal these sit at their zero
    # values, and "they declare 0 counted matches" is a sentence about a peer we
    # never heard from - a plausible wrong figure, which the artefact rules rank
    # below an absent one because it prompts no question.
    if theirs is not None:
        print(f"their commit      : {locked.their_commit or '(none declared)'}")
        print(f"they declare      : {locked.their_games_played} counted match(es)")
    for reason in locked.reasons:
        print(f"  REFUSED: {reason}")
    _print_warnings(prematch.warnings())
    if args.out:
        print(f"\nagreement written : {_file(locked, ours, theirs, Path(args.out))}")
    return 0 if locked.agreed else 1


def _print_warnings(found: list[str]) -> None:
    """Print what a human still has to settle, or say that nothing is open."""
    if not found:
        print("nothing outstanding.")
        return
    print("SETTLE BEFORE THE FIRST MOVE (M#35):")
    for warning in found:
        print(f"  ! {warning}")


def _file(locked, ours, theirs, directory: Path) -> Path:
    """Write the agreement beside the match artefacts (N10, 9.3.5).

    Named from the shared ``game_id`` so both teams' files carry the same
    identifier, and from the opponent's **declared** team name rather than one
    we typed. ``theirs`` is None when they refused before declaring anything,
    and ``unknown`` says exactly that rather than inventing a name.
    """
    from core.report.artefacts import write
    from core.report.identifiers import game_id

    declared = theirs.step_zero if theirs is not None else {}
    ours_team = str(ours.step_zero.get("team_name", "")) or "unknown"
    theirs_team = str(declared.get("team_name", "")) or "unknown"
    identifier = game_id(ours_team, theirs_team, locked.agreed_at[:10])
    return write(locked.payload(), directory, f"agreement_{identifier}.json")
