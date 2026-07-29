# PRD — State Machine and Reliability Patterns
### Cross-cutting · owner [D] · built in Layer 6, relied on from Layer 2

**Book:** Chapter 8 · **Covers:** FR-8.1 … FR-8.3
**Exit criterion:** illegal transitions raise immediately; an expired request becomes a failure
rather than a longer wait; a frozen process shuts down cleanly with its state persisted.

---

## 1. Purpose

Keep the agent alive and lawful when the world misbehaves. The book's framing is worth quoting
directly: *your code quality is measured not when everything works, but when something breaks.*
An agent that beats a friendly opponent but collapses against a hostile one has solved only the
easy version of the problem.

Three mechanisms, three different failure modes:

| Mechanism | Guards against | Scope |
|---|---|---|
| State machine | Illegal sequencing, silent deadlock | Game flow |
| Deadline Tracker | An opponent who never answers | One request |
| Watchdog | A frozen or crashed process | The whole system |

---

## 2. Background

A peer-to-peer match has no scheduler. Both sides act on their own clock, and the only thing
keeping them in step is the protocol itself. Without explicit sequencing, two peers can each wait
for the other indefinitely — a deadlock that produces no error message, no log, and no result. In a
league that costs both teams their points (M#35), so an unhandled wait is worse than an outright
loss.

The book's remedy is the standard stability toolkit: never wait unbounded on an external resource,
make illegal states unrepresentable, and assume the network, the model and the opponent will each
fail at the worst possible moment.

---

## 3. The state machine

### 3.1 States and legal transitions

```
        ┌──────────────────────────┐
   ┌───►│ WAITING_FOR_OPPONENT     │
   │    └────────────┬─────────────┘
   │                 ▼
   │    ┌──────────────────────────┐
   │    │ COMPUTING_MOVE           │──┐
   │    └────────────┬─────────────┘  │
   │                 ▼                │
   │    ┌──────────────────────────┐  │
   │    │ COMMITTING               │  │
   │    └────────────┬─────────────┘  │
   │                 ▼                │
   │    ┌──────────────────────────┐  │
   │    │ AWAITING_REVEAL          │──┤
   │    └────────────┬─────────────┘  │
   │                 ▼                │
   │    ┌──────────────────────────┐  │
   └────┤ VERIFYING                │  │
        └──────────────────────────┘  │
                                      ▼
                         ┌──────────────────────────┐
                         │ TECHNICAL_LOSS (terminal)│
                         └──────────────────────────┘
```

| From | Legal targets |
|---|---|
| `WAITING_FOR_OPPONENT` | `COMPUTING_MOVE` |
| `COMPUTING_MOVE` | `COMMITTING`, `TECHNICAL_LOSS` |
| `COMMITTING` | `AWAITING_REVEAL` |
| `AWAITING_REVEAL` | `VERIFYING`, `TECHNICAL_LOSS` |
| `VERIFYING` | `WAITING_FOR_OPPONENT` |
| `TECHNICAL_LOSS` | — (terminal) |

### 3.2 Requirements

| ID | Requirement |
|---|---|
| S1 | Transitions are declared in an explicit table, not scattered through `if` statements (M#4). |
| S2 | Any target not listed for the current state **raises immediately** (M#5). |
| S3 | Only the two states that wait on the network may exit to `TECHNICAL_LOSS`. |
| S4 | `TECHNICAL_LOSS` is terminal — no path leads out of it. |
| S5 | Every transition is logged with a timestamp for the audit trail. |

S2 is the design point. An illegal transition is a *logic bug*, and a bug that raises during
development is infinitely cheaper than one that deadlocks during a graded match. Failing loudly at
the wrong moment beats failing silently at the worst moment.

---

## 4. Deadline Tracker

| ID | Requirement |
|---|---|
| D1 | Every MCP request carries a timestamp and an expiry (M#6). |
| D2 | Default `response_timeout_sec` = 30, negotiable upward. |
| D3 | On expiry: one controlled retry, then `TECHNICAL_LOSS`. |
| D4 | An expired request is a **failure**, never an invitation to keep waiting. |
| D5 | The clock is injectable so tests need no real sleeping. |

The book is emphatic on D4: leaving a request hanging without an expiry is the direct recipe for
deadlock — the main loop blocks, the watchdog sees no heartbeat, and the match collapses. Every
request must carry an expiry, and on expiry the system either retries deliberately or declares a
technical loss and closes the turn cleanly.

---

## 5. Watchdog

| ID | Requirement |
|---|---|
| W1 | Background monitor of the main loop's heartbeat (M#7). |
| W2 | No heartbeat for `watchdog_timeout_sec` (default 60) → intervene. |
| W3 | Intervention is: persist state, release MCP connections, close logs, exit cleanly. |
| W4 | Persisted state must be sufficient to reconstruct the match log for the audit. |
| W5 | Tunnel health is a watchdog input (PRD 5 §3.2). |

The distinction from the Deadline Tracker matters: the tracker guards a single request, the
watchdog guards the process. A model that hangs, a thread that deadlocks, or a tunnel that dies
produces no failed request at all — there is simply nothing happening, and only a heartbeat monitor
notices.

W3's priority is preserving evidence. A crash that loses the log means the match cannot be audited,
which under M#36 blocks agreeing a result — turning a recoverable fault into a void match.

---

## 6. Interface

```python
# core/runtime/phase_machine.py
class GamePhaseMachine:
    TRANSITIONS: dict[str, set[str]]
    state: str
    def transition(self, target: str) -> str      # raises IllegalTransitionError

# core/runtime/deadline_tracker.py
class DeadlineTracker:
    def __init__(self, timeout_sec: float, clock: Callable[[], float] = time.monotonic) -> None
    def start(self, request_id: str) -> None
    def expired(self, request_id: str) -> bool
    def remaining(self, request_id: str) -> float

# core/runtime/watchdog.py
class Watchdog:
    def __init__(self, timeout_sec: float, on_timeout: Callable[[], None]) -> None
    def heartbeat(self) -> None
    def check(self) -> Literal["ALIVE", "SHUTDOWN"]
```

---

## 7. Constraints

- Files ≤150 lines.
- No test sleeps longer than 2 seconds — the clock is injected.
- The state machine imports nothing from `core.infra`: it sequences, it does not communicate.
- The watchdog runs on a background thread and must not touch game state directly; it signals
  through the Orchestrator (M#3).

---

## 8. Alternatives considered

| Decision | Alternative | Why rejected |
|---|---|---|
| Explicit transition table | Conditionals at each call site | Scattered rules cannot be reviewed as a whole and drift as the code grows |
| Raise on illegal transition | Log a warning and continue | A warning during a graded match is a warning nobody reads. Undefined state is how deadlocks start |
| One controlled retry | Retry with exponential backoff | The opponent is also on a clock; a long backoff risks *their* timeout firing and turning our caution into a mutual technical loss |
| Injected clock | `time.sleep` in tests | A suite that takes minutes stops being run before every commit |
| Watchdog persists then exits | Attempt in-place recovery | Recovering a process whose failure mode is unknown risks corrupting the log, which is the one artefact that must survive |

---

## 9. Test scenarios

| # | Scenario | Expected |
|---|---|---|
| TS.1 | Every legal transition in the table | Accepted |
| TS.2 | Every illegal pair | Raises `IllegalTransitionError` |
| TS.3 | Exit from `TECHNICAL_LOSS` | Raises — terminal |
| TS.4 | `COMMITTING` → `TECHNICAL_LOSS` | Raises — not a network-waiting state |
| TS.5 | Full legal turn cycle | Returns to `WAITING_FOR_OPPONENT` |
| TS.6 | Request answered inside the deadline | No intervention |
| TS.7 | Request expires | One retry, then `TECHNICAL_LOSS` |
| TS.8 | Opponent disconnects during `AWAITING_REVEAL` | Controlled transition to `TECHNICAL_LOSS`, log persisted |
| TS.9 | Heartbeat every second for 5 s (injected clock) | `ALIVE` throughout |
| TS.10 | Heartbeat stops for `watchdog_timeout_sec + 1` | `SHUTDOWN`; state persisted |
| TS.11 | Persisted state reloaded | Match log reconstructible for audit |
| TS.12 | Tunnel death reported to the watchdog | Intervention within the timeout |

---

## 10. Traceability

| Rule | Where |
|---|---|
| M#4 | §3.2 — state machine mandatory |
| M#5 | §3.2 — illegal transitions rejected |
| M#6 | §4 — deadline tracking, expiry is failure |
| M#7 | §5 — watchdog, controlled shutdown |
| M#3 | §7 — watchdog signals through the Orchestrator |
| M#36 | §5 — preserving the log keeps the audit possible |
| F | `response_timeout_sec` 30, `watchdog_timeout_sec` 60 |

**TODO tasks:** 6.4.1 – 6.4.4, 6.5.3, 6.5.4 · **Milestone:** M6
