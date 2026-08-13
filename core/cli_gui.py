"""Watching a real match while it happens (TODO 7.4.1, 9.2, M#8, M#9).

    python -m core play --role cop --gui --opponent https://them.ngrok-free.dev/mcp

`core/ui/live_gui.py` has existed since Phase 7 and nothing could reach it
during a match. `--gui` was a flag on the `peer` subcommand only, and there it
was a **dead end**: it opened the window and returned, so the choice was to
watch a board that never moved or to play a match with nothing to watch.

The cost was not cosmetic. Ch. 7.3 has each side running its software out of a
dedicated GUI, and Ch. 9.4 makes a screen capture of the **belief map** an
absolute submission requirement. The only capture obtainable was step 0, where
the prior is uniform and every cell renders at peak intensity — a flat wash of
red that demonstrates a working renderer and nothing whatever about belief.

**Tk owns the main thread; the match runs beside it.** Not a preference on
Windows — Tk must be created and pumped from the thread that owns it, and
`asyncio.run` blocks whichever thread it is on. So the match goes to a worker
and the window keeps the main thread, which is also the arrangement `LiveGui`
was designed for: it polls a provider on a timer and never drives the turn
loop, because a window running the loop would freeze for the length of a 30 s
response timeout and a frozen window mid-match looks exactly like a crash.

**Closing the window never forfeits the match.** The worker is not a daemon and
is joined afterwards, so a human who shuts the display still gets the sub-games
played, the artefacts filed and the report sent. The alternative — a display
whose close button is a technical loss — would be a trap that scores 0.
"""

from __future__ import annotations

import argparse
import asyncio
import threading
from typing import Any

__all__ = ["play_with_window"]

# Any non-zero code would be indistinguishable from a refused handshake, and a
# crash inside the worker must not read as "the opponent turned us down".
CRASHED = 70


def play_with_window(sdk: Any, spec: Any, args: argparse.Namespace, plan: Any, prepared: Any) -> int:
    """Play the series in a worker thread while the Live GUI holds this one.

    Args:
        sdk: The `PeerSDK`. Only `gui_state` and `ui_cell_pixels` are read here
            — never `board_view`, which carries both true positions and would
            be project disqualification on a screen (M#9).
        spec: The server spec from `sdk.server_spec`.
        args: The parsed `play` arguments.
        plan: The `(sub_game, role)` pairs this process plays.
        prepared: The set of sub-games already reset.

    Returns:
        The match's exit code, so `--gui` changes what is on screen and nothing
        about what the command means to a script.
    """
    from core.cli_play import _run

    outcome: dict[str, Any] = {}

    def run_match() -> None:
        try:
            outcome["code"] = asyncio.run(_run(sdk, spec, args, plan, prepared))
        except BaseException as error:  # noqa: BLE001 - re-raised on the main thread
            outcome["error"] = error

    # Not a daemon. A daemon thread is killed the instant the window closes,
    # which would abandon a series mid-sub-game and leave the opponent playing
    # against a peer that had quit — the M#35 failure, caused by a close button.
    worker = threading.Thread(target=run_match, name="match", daemon=False)
    worker.start()

    _open_window(sdk, args, worker)

    # The window is gone; the match may not be. Waiting is what lets a human
    # close the display the moment the scoreboard prints without losing the
    # report that goes out immediately after it.
    worker.join()
    if "error" in outcome:
        raise outcome["error"]
    return int(outcome.get("code", CRASHED))


def _open_window(sdk: Any, args: argparse.Namespace, worker: threading.Thread) -> None:
    """Show the Live GUI until the match ends or the human closes it.

    A failure to open is reported and then ignored. Tkinter is unavailable on a
    headless box and on some minimal Python builds, and a missing display is
    not a reason to abandon a graded match that is already under way — the
    match is the deliverable and the window is a view of it.
    """
    from core.ui.live_gui import LiveGui

    title = f"p2p-chase - {sdk.role.value} vs {args.opponent}"
    try:
        LiveGui(
            sdk.gui_state,
            int(sdk.ui_cell_pixels),
            title=title,
            keep_open=worker.is_alive,
        ).run()
    except Exception as error:  # noqa: BLE001 - a display is never worth the match
        print(f"  ! the Live GUI could not open ({type(error).__name__}: {error});")
        print("    the match continues without it - watch this terminal instead.")
