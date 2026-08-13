"""The Live GUI — what this peer knows, and nothing more (TODO 7.4, M#8, M#9).

Shows own position, own barriers, own belief heatmap and the hints received.
**There is no bird's-eye view**, and that is not a UI preference: each agent's
observation is a strict subset of the true state under the Dec-POMDP formalism,
so an interface exposing the full state would break the game's own rules. It is
also project disqualification.

The safety is structural rather than careful. This window is handed a
`GuiState`, which has no field for the opponent's position and no constructor
argument that could supply one. It never sees a `GameState`, never calls
`board_view()` — which does carry both true positions — and imports nothing
below `core/sdk/`. A test checks all three, because "we were careful" is not a
control.

**The window owns the UI thread and never blocks it** (PRD 7 §5). It does not
drive the match; it polls a state provider on a timer. A GUI that ran the turn
loop would freeze for the length of a 30-second response timeout, and a frozen
window during a graded match looks exactly like a crashed peer.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.sdk.view_state import GuiState
from core.ui.widgets import draw_banner, draw_board

__all__ = ["LiveGui", "POLL_MS"]

# Fast enough to feel live, slow enough to leave the interpreter alone between
# frames. The match loop runs elsewhere; this only reads.
POLL_MS = 250


class LiveGui:
    """A window that renders frames from a provider it does not control.

    Attributes:
        provider: Called for each frame. Usually `sdk.gui_state`, but any
            callable returning a `GuiState` works — which is what lets the
            replay of a finished match reuse this window.
        cell_pixels: Square size, from `[ui] cell_pixels`.
    """

    def __init__(
        self,
        provider: Callable[[], GuiState],
        cell_pixels: int = 64,
        title: str = "p2p-chase - live",
        keep_open: Callable[[], bool] | None = None,
    ) -> None:
        """Build the window. Nothing is drawn until :meth:`run`.

        Args:
            keep_open: Asked once per frame. Returning False closes the window,
                which is how a finished match ends its own display instead of
                leaving a dead board on screen waiting for a human. Default
                keeps it open forever, which is what a standalone launch wants.
        """
        import tkinter as tk

        self.provider = provider
        self.cell_pixels = cell_pixels
        self.keep_open = keep_open or (lambda: True)
        self.state = provider()

        self.root = tk.Tk()
        self.root.title(title)
        span = self.state.grid_size * cell_pixels

        self.banner = tk.Label(self.root, text="", font=("Segoe UI", 14, "bold"), pady=6)
        self.banner.pack(fill="x")
        self.canvas = tk.Canvas(self.root, width=span, height=span, highlightthickness=0)
        self.canvas.pack()
        self.status = tk.Label(self.root, text="", anchor="w", padx=8, pady=4)
        self.status.pack(fill="x")

        self.root.bind("<Key>", self.on_key)
        self.pressed: list[str] = []

    def on_key(self, event: Any) -> None:
        """Record a keystroke, or drop it while we are locked (7.4.1.c).

        **Input is ignored while locked**, because our commit is already on the
        wire. Accepting one here would let a human change a move the opponent
        is holding a digest of — which is the whole failure commit-reveal
        exists to prevent, arriving through the keyboard instead of the wire.
        """
        if not self.state.accepts_input():
            return
        self.pressed.append(getattr(event, "keysym", ""))

    def refresh(self) -> None:
        """Pull one frame and repaint."""
        self.state = self.provider()
        draw_banner(self.banner, self.state)
        draw_board(self.canvas, self.state, self.cell_pixels)
        self.status.configure(text=self.summary())

    def summary(self) -> str:
        """One line under the board: step, barrier quota, latest hint."""
        latest = self.state.hints[-1] if self.state.hints else "-"
        return (
            f"step {self.state.step}   "
            f"barriers left {self.state.barriers_remaining}   "
            f'last hint: "{latest}"'
        )

    def _tick(self) -> None:
        """Repaint and schedule the next frame, unless the match is over.

        The final frame is drawn *before* the check, so the last thing on
        screen is the position the match actually ended in.
        """
        self.refresh()
        if not self.keep_open():
            self.root.destroy()
            return
        self.root.after(POLL_MS, self._tick)

    def run(self) -> None:  # pragma: no cover - opens a window
        """Show the window and poll until it is closed."""
        self._tick()
        self.root.mainloop()
