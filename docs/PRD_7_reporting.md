# PRD 7 — Reporting, GUI and Replay
### Layer 7 of 7 · milestone M7 · owner [D]

**Covers:** FR-7.1 … FR-7.11 · **Book:** Chapters 7 and 9, Appendix A · **Depends on:** Layers 1–6
**Exit criterion:** a match summary reaches the lecturer's inbox as a JSON attachment; the Live GUI
shows local truth only; the Replay App reproduces a recorded series with `Verified OK`.

---

## 1. Purpose

The outermost shell: how the system is watched while it runs, proved afterwards, and reported.
Built last because it consumes every layer beneath it.

Two of the requirements here are **disqualifying if got wrong** — displaying the objective board
state in the live GUI, and failing to send the result report — so this layer carries more
project-ending risk per line than any other except cryptography.

---

## 2. Background

### 2.1 Two axes of observation

The Live GUI answers *what is happening now?* The Replay Viewer answers the harder question:
*did what is claimed to have happened actually happen?* They are not the same tool and neither
substitutes for the other.

In a distributed system with no referee, match history is not held by a trusted authority — it
sits in a local file on each player's disk. That invites rewriting the past to win retroactively.
Cryptography turns that log from a forgeable document into evidence.

### 2.2 Local truth

Each interface shows only what its own agent legitimately knows: own position, own sensed scent,
own belief map, hints received. **There is no bird's-eye view.** This follows directly from the
Dec-POMDP formalism — each agent's observation is a strict subset of the true state, so an
interface exposing the full state would break the game's own rules.

### 2.3 Automation and its hazard

Automated reporting removes human delay but hands a live email account to code that might contain
a bug. The question the Gatekeeper exists to answer: what happens when a loop starts firing
thousands of messages a minute? Exceeding Google's quota returns HTTP 429, and blindly retrying
after one risks account suspension — which would cost every remaining match.

---

## 3. Requirements

### 3.1 Gatekeeper — three cumulative gates (M#28, M#29)

```
outgoing ──► Quota Manager ──► Token Bucket ──► DOS Detector ──► Gmail API
   report      │ full            │ empty          │ anomaly
               ▼                 ▼                ▼
            Rejected           Blocked          LOCKED
```

| ID | Requirement |
|---|---|
| 7.1 | **Quota manager** — daily ceiling; once exhausted nothing further goes out. |
| 7.2 | **Token bucket** — `tokens ← min(C, tokens + r·Δt)`, allow iff `tokens ≥ 1`. Separates sustained rate (`r`) from burst size (`C`). |
| 7.3 | **DOS detector** — abnormal send patterns lock the pipe entirely, sacrificing one report to save the account. |
| 7.4 | HTTP 429 is honoured with backoff. Never blind retry. |
| 7.5 | Every external call is logged for the cost analysis. |
| 7.6 | All parameters come from `rate_limits.json`. No hardcoded limits. |

**Naming discipline.** "Token" means three unrelated things in this project: rate-limiter tokens,
LLM tokens, and OAuth tokens. Identifiers must keep them distinct — `rate_tokens`, `llm_tokens`,
`oauth_token`. The book calls this out explicitly, which suggests it has caused confusion before.

### 3.2 The four JSON artefacts

| Artefact | Filename | Contents |
|---|---|---|
| Declaration | `declaration_<game_id>.json` | Teams, members, **four** repo links, MCP URLs, hardware, LLM model, token cap, timings |
| Config | `config_<game_id>_g<NN>.json` | The negotiated, cryptographically locked sub-game parameters |
| Log | `log_<game_id>_g<NN>.json` | Commits, reveals, moves, hints, nonces, hashes — enough for full replay verification |
| Result | `result_<game_id>.json` | Per-sub-game and cumulative scores, `github_commit`, total tokens, four repo links |

| ID | Requirement |
|---|---|
| 7.7 | All four share a `game_uid`; filenames derive from `game_id` so files from different matches cannot collide. |
| 7.8 | The result JSON is the one emailed. |
| 7.9 | Four repo links: both of ours, both of the opponent's (M#49). |
| 7.10 | Config and log are committed to both repositories after each match. |

### 3.3 Delivery

| ID | Requirement |
|---|---|
| 7.11 | Gmail API over OAuth 2.0, **send-only** scope (M#30). |
| 7.12 | Sent as a JSON **attachment**. Free-text reports are rejected outright (M#33, M#34). |
| 7.13 | Recipient `rmisegal+uoh26finalgame@gmail.com`, from config, never hardcoded (M#51). |
| 7.14 | Each team sends its **own** report. No code path sends on the opponent's behalf (M#35). |
| 7.15 | All Gmail traffic routes through the Gatekeeper. |

**M#35 is the harshest rule in the book:** if either side fails to report, or the two reports
disagree, the match is void and **both teams score 0**. Winning on the board is worth nothing if
the opponent forgets to send. The per-match checklist in `LEAGUE_LOG.md` therefore requires
explicit confirmation that the opponent has sent theirs before the session is closed.

### 3.4 Live GUI — local truth only

| ID | Requirement |
|---|---|
| 7.16 | Tkinter. Belief heatmap: deeper red = higher posterior. |
| 7.17 | Own position and known barriers rendered distinctly. |
| 7.18 | Turn banner: green `YOUR TURN` when the opponent's server hands over; grey `LOCKED` after the commit is sent. Input ignored while locked. |
| 7.19 | The full objective board state must **never** be displayed (M#8, M#9). |
| 7.20 | An automated test asserts the GUI layer never receives the opponent's true position. |

7.20 is not defensive programming, it is insurance against a project-ending mistake. The banner is
also more than decoration: it is the visible face of the asynchronous state machine, and it
prevents a race where both sides act on the same step.

### 3.5 Replay Viewer — a mandatory deliverable

| ID | Requirement |
|---|---|
| 7.21 | Load a saved log; step forward and backward (M#20). |
| 7.22 | Re-hash every entry from the revealed nonce and move; compare to the stored commitment. |
| 7.23 | Green `Verified OK` on match; red `TAMPERED` on any mismatch. |
| 7.24 | One `TAMPERED` voids the match. No appeal, no retrospective correction. |
| 7.25 | A screenshot showing `Verified OK` is a required submission artefact. |

### 3.6 SDK

| ID | Requirement |
|---|---|
| 7.26 | GUI, Replay, CLI and tests reach the system **only** through `PeerSdk` (X §4.1). |
| 7.27 | `grep -r "from core.domain" core/ui/` returns nothing. |

---

## 4. Interface

```python
# core/shared/gatekeeper.py
Gatekeeper(limits: RateLimits, logger: CallLogger)
  .execute(call: Callable, *args, **kwargs) -> Any    # raises GatekeeperLocked | QuotaExhausted
  .status() -> QueueStatus

# core/protocol/artefacts.py
build_declaration(...) -> dict
build_config_snapshot(...) -> dict
build_log(...) -> dict
build_result(...) -> dict

# core/infra/gmail_sender.py
GmailSender(config, gatekeeper)
  .send_result(result_path: Path) -> None            # attachment only

# core/ui/live_gui.py
LiveGui(sdk: PeerSdk)      # receives an Observation, never a GameState

# core/ui/replay.py
ReplayViewer(log_path: Path)
  .verify_all() -> AuditResult
```

---

## 5. Constraints

- Files ≤150 lines. GUI modules breach most often — split widgets from controller from the outset.
- `core/ui/*` is excluded from coverage (rendering), but the **local-truth test is not** — it is a
  correctness test, not a rendering test.
- No test may contact the live Gmail API.
- The GUI runs on the UI thread; the match loop must not block it.

---

## 6. Alternatives considered

| Decision | Alternative | Why rejected |
|---|---|---|
| Tkinter | PyQt | Both named in the book; Tkinter is stdlib, adds no dependency, and screenshots identically on both machines |
| Tkinter | pygame (HW6's choice) | A game loop for two static panels with a timer; threading friction for no benefit |
| Observation into the GUI | `GameState` filtered at render time | Filtering at render is one forgotten branch away from disqualification. Never handing over the data is safer |
| Three cumulative gates | Rate limiting alone | The DOS detector is separately mandated (M#29) and guards against our own bugs, not the provider's limits |
| JSON attachment | JSON in the body | M#34 rejects non-attachment reports outright |
| Sender routed via Gatekeeper | Direct API call | The book treats the Gatekeeper as the sole path for outbound traffic |

---

## 7. Test scenarios

| # | Scenario | Expected |
|---|---|---|
| T7.1 | Burst of sends | Bucket empties; further sends blocked, not crashed |
| T7.2 | Quota exhausted | Every subsequent send rejected |
| T7.3 | Simulated infinite loop | DOS detector locks the pipe |
| T7.4 | Mocked HTTP 429 | Backoff, not immediate retry |
| T7.5 | Build all four artefacts | Correct filenames from `game_id`; shared `game_uid` |
| T7.6 | Result JSON | Contains four repo links, `github_commit`, total tokens |
| T7.7 | Send a report | JSON attachment present; body carries no report data |
| T7.8 | Recipient address | Read from config, not a literal |
| T7.9 | GUI receives data | Only an `Observation`; no opponent position field exists |
| T7.10 | Grep `core/ui/` for `core.domain` | No matches |
| T7.11 | Replay a clean log | `Verified OK` on every step |
| T7.12 | Replay a log with one altered move | `TAMPERED`, naming the step |
| T7.13 | Banner state after commit | `LOCKED`; input ignored |
| T7.14 | Belief heatmap render | Deepest cell equals `belief.argmax()` |

---

## 8. Traceability

| Rule | Where |
|---|---|
| M#8, M#9 | §3.4 — local truth only; no objective board view |
| M#20 | §3.5 — Replay Viewer is a mandatory deliverable |
| M#28, M#29 | §3.1 — token bucket and DOS detector |
| M#30 | §3.3 — send-only OAuth scope |
| M#32 | §3.3 — automated reporting |
| M#33, M#34 | §3.3 — structured JSON attachment only |
| M#35 | §3.3 — both teams report separately |
| M#49 | §3.2 — four repo links in the JSON |
| M#51 | §3.3 — the lecturer's reporting address |

**TODO tasks:** 7.1.1 – 7.5.4 · **Milestone:** M7
