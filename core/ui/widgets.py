"""Tkinter drawing shared by the Live GUI and the Replay Viewer (ADR-005).

Split from both controllers because GUI modules are what breach the 150-line
rule first (PRD 7 §5), and because the two surfaces draw the same board for
different reasons — one from a live belief, one from a saved log.

**This module decides nothing.** It takes a `GuiState` and paints it. Every
question about what may be shown was already answered by the type: there is no
opponent position in a `GuiState` because there is nowhere to put one (M#8,
M#9). A widget layer that filtered would be a widget layer that could forget to.

Excluded from coverage — asserting on canvas rectangles tests Tkinter, not the
game. The *rules* it draws by, `heat_colour` and `banner`, live in
`core/sdk/view_state.py` where they are tested as arithmetic.
"""

from __future__ import annotations

from typing import Any

from core.sdk.view_state import GuiState, heat_colour

__all__ = ["draw_board", "draw_banner", "BOARD_BG", "BARRIER_FILL", "OWN_FILL", "GRID_LINE"]

BOARD_BG = "#ffffff"
GRID_LINE = "#d0d7de"
BARRIER_FILL = "#24292f"
OWN_FILL = "#0969da"
HOTTEST_OUTLINE = "#b00000"


def draw_board(canvas: Any, state: GuiState, cell_pixels: int = 64) -> None:
    """Repaint *canvas* from *state*.

    Painted back to front so nothing important is buried: the belief heatmap
    first, then barriers, then our own marker. An agent drawn under a wall would
    be a rendering bug that looks exactly like a rules bug.
    """
    canvas.delete("all")
    for row in range(state.grid_size):
        for column in range(state.grid_size):
            _draw_cell(canvas, state, (row, column), cell_pixels)

    _draw_own_marker(canvas, state, cell_pixels)


def _draw_cell(canvas: Any, state: GuiState, cell: tuple[int, int], size: int) -> None:
    """Draw one square: heat, or barrier, plus the grid line."""
    row, column = cell
    left, top = column * size, row * size
    fill = BARRIER_FILL if cell in state.barriers else heat_colour(state.heat(cell))
    canvas.create_rectangle(left, top, left + size, top + size, fill=fill, outline=GRID_LINE)

    if cell == state.hottest() and cell not in state.barriers:
        # Outlined rather than recoloured, so the peak is findable at a glance
        # without lying about its intensity relative to its neighbours.
        canvas.create_rectangle(
            left + 2, top + 2, left + size - 2, top + size - 2,
            outline=HOTTEST_OUTLINE, width=2,
        )


def _draw_own_marker(canvas: Any, state: GuiState, size: int) -> None:
    """Draw where we are — the one position anyone knows for certain."""
    row, column = state.own_position
    inset = size // 5
    canvas.create_oval(
        column * size + inset, row * size + inset,
        (column + 1) * size - inset, (row + 1) * size - inset,
        fill=OWN_FILL, outline="",
    )


def draw_banner(label: Any, state: GuiState) -> None:
    """Set the turn banner's text and colour (7.4.1.c).

    The visible face of the asynchronous state machine, not decoration: it is
    what stops both sides acting on the same step.
    """
    text, colour = state.banner()
    label.configure(text=text, background=colour, foreground="#ffffff")
