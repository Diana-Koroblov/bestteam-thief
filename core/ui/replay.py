"""The Replay Viewer window (TODO 7.5, M#20, Ch. 7).

A **mandatory deliverable**, and the screenshot showing `Verified OK` is a
required submission artefact (7.25). It answers the question the Live GUI
cannot: not *what is happening* but *did what is claimed to have happened
actually happen?*

The verdict is computed over the whole log before the first frame is drawn, by
`core/report/replay.py`. This module only shows it. That split matters: a viewer
that verified lazily as the cursor moved would display a green banner on a log
whose forgery sits at step 30 and which nobody clicked as far as.

Imports nothing below `core/sdk/` (7.5.4, X §4.1) — the replay model arrives
through `core.sdk.replay_sdk`, and the board is drawn by the same widget layer
as the Live GUI (ADR-005).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.sdk.replay_sdk import ReplaySession, load_replay
from core.sdk.view_state import GuiState
from core.ui.widgets import draw_board

__all__ = ["ReplayViewer", "frame_of"]


def frame_of(session: ReplaySession, grid_size: int) -> GuiState:
    """Return a drawable frame for the step under the cursor.

    Built from the sealed state, which is the point: what is drawn is what was
    *hashed*, not a convenient reconstruction beside it. A viewer that rendered
    from anything else could show a board the commitment never covered.

    The belief is empty — a saved log records what was committed, not what
    either peer believed — so the replay shows a clean board rather than
    inventing a posterior that was never recorded.
    """
    step = session.current() or {}
    sealed = step.get("state") or {}
    own = sealed.get(session.payload.get("role", "cop")) or (0, 0)
    return GuiState(
        grid_size=grid_size,
        own_position=(int(own[0]), int(own[1])),
        barriers=(),
        step=int(step.get("step", 0)),
        locked=True,
    )


class ReplayViewer:
    """A window over a saved log: step through it, and see the verdict.

    Attributes:
        session: The loaded, already-audited log.
        grid_size: Board edge, since a log records positions and not geometry.
    """

    def __init__(self, log_path: Path, grid_size: int = 7, cell_pixels: int = 64) -> None:
        """Load and audit *log_path*, then build the window."""
        import tkinter as tk

        self.session = load_replay(log_path)
        self.grid_size = grid_size
        self.cell_pixels = cell_pixels

        self.root = tk.Tk()
        self.root.title(f"p2p-chase - replay - {Path(log_path).name}")
        span = grid_size * cell_pixels

        text, colour = self.session.verdict
        self.verdict = tk.Label(
            self.root, text=text, background=colour, foreground="#ffffff",
            font=("Segoe UI", 14, "bold"), pady=6,
        )
        self.verdict.pack(fill="x")
        self.canvas = tk.Canvas(self.root, width=span, height=span, highlightthickness=0)
        self.canvas.pack()
        self.status = tk.Label(self.root, text="", anchor="w", padx=8, pady=4)
        self.status.pack(fill="x")

        controls = tk.Frame(self.root)
        controls.pack(fill="x")
        tk.Button(controls, text="< back", command=self.back).pack(side="left", padx=4, pady=4)
        tk.Button(controls, text="forward >", command=self.forward).pack(side="left", pady=4)
        self.root.bind("<Left>", lambda _event: self.back())
        self.root.bind("<Right>", lambda _event: self.forward())

    def back(self) -> None:
        """Step backward and repaint (7.5.1)."""
        self.session.back()
        self.refresh()

    def forward(self) -> None:
        """Step forward and repaint (7.5.1)."""
        self.session.forward()
        self.refresh()

    def summary(self) -> str:
        """One line: position in the log, and whether *this* step re-hashes."""
        if not self.session.total:
            return "empty log - nothing to replay"
        mark = "OK" if self.session.step_ok(self.session.cursor) else "MISMATCH"
        step = self.session.current() or {}
        return (
            f"step {self.session.cursor + 1}/{self.session.total}   "
            f'move {step.get("move", "?")}   {mark}   '
            f'hint: "{step.get("hint", "")}"'
        )

    def refresh(self) -> None:
        """Repaint the board and the status line."""
        draw_board(self.canvas, frame_of(self.session, self.grid_size), self.cell_pixels)
        self.status.configure(text=self.summary())

    def run(self) -> Any:  # pragma: no cover - opens a window
        """Show the window until it is closed."""
        self.refresh()
        self.root.mainloop()
