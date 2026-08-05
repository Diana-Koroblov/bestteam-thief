"""The Replay Viewer's only route into the system (TODO 7.5.4, X §4.1).

A three-line facade, and it earns its place. `core/ui/` must import nothing
deeper than `core/sdk/` — checked literally by a test — and the replay model
lives in `core/report/` beside the log it replays. Without this module the
viewer would either reach across that boundary or the model would have to move
somewhere it does not belong.
"""

from core.report.replay import TAMPERED, VERIFIED_OK, ReplayError, ReplaySession, load_replay

__all__ = ["ReplaySession", "load_replay", "ReplayError", "VERIFIED_OK", "TAMPERED"]
