"""**Milestone M6, made observable** (TODO 6.QG.4).

    uv run python scripts/demo_m6.py

Runs three turns of the real four-phase protocol, then audits the log — first
honestly, then after tampering with it the way a losing opponent would. The DoD
says M6 must be *observed*: a move committed then revealed with a valid nonce,
Step-0 verifying hardware, and the audit passing.

Nothing here is a simulation. Same `TurnExchange`, same `seal`, same
`audit_log` that play a graded match.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.crypto.audit import StepRecord, audit_log  # noqa: E402
from core.crypto.commitment import seal  # noqa: E402
from core.protocol.four_phase import ProtocolError, TurnExchange  # noqa: E402
from core.protocol.step_zero import build  # noqa: E402

__all__ = ["main"]

MOVES = [("N", "truth"), ("E", "lie"), ("S", "truth")]


def main() -> int:
    """Play three sealed turns, then audit the log honestly and dishonestly."""
    print("M6 - commit, acknowledge, reveal, audit\n")

    declaration = build("bestteam", "cop", 1, "llama3.1:8b", ROOT)
    hardware = declaration.payload["hardware"]
    print(f"  Step-0  {hardware['os']}, {hardware['cpu_cores']} cores, gpu={hardware['gpu']}")
    print(f"          commit {declaration.payload['github_commit'][:12]}")
    print(f"          digest {declaration.digest[:32]}...\n")

    log: list[StepRecord] = []
    for step, (move, intent) in enumerate(MOVES, start=1):
        state = {"step": step, "cop": [0, 0], "thief": [6, 6]}
        sealed = seal(state, move, intent)

        exchange = TurnExchange(step=step)
        exchange.commit("us", sealed.digest)
        exchange.commit("them", "opponent-digest")
        exchange.acknowledge("us")
        exchange.acknowledge("them")
        # Note what does NOT travel here: the nonce (M#18).
        exchange.reveal("us", {"move": move, "intent": intent, "hint": "..."})
        exchange.reveal("them", {"move": "W", "intent": "truth", "hint": "..."})

        log.append(StepRecord(step, sealed.digest, state, move, intent, sealed.nonce))
        print(f"  step {step}  move={move:<4} intent={intent:<6} "
              f"settled={exchange.settled}  digest={sealed.digest[:16]}...")

    print("\n  --- phase 3 refuses to leak the nonce ---")
    try:
        blocked = TurnExchange(step=9)
        blocked.commit("us", "a")
        blocked.commit("them", "b")
        blocked.acknowledge("us")
        blocked.acknowledge("them")
        blocked.reveal("us", {"move": "N", "nonce": "deadbeef"})
    except ProtocolError as refused:
        print(f"  refused: {refused}")

    print("\n  --- the audit ---")
    print(f"  honest log      : {audit_log(log).describe()}")

    forged = list(log)
    forged[1] = StepRecord(**{**forged[1].__dict__, "move": "W"})
    print(f"  one move changed: {audit_log(forged).describe()}")

    replayed = list(log)
    replayed[2] = StepRecord(**{**replayed[0].__dict__, "step": 3})
    print(f"  step 1 replayed : {audit_log(replayed).describe()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
