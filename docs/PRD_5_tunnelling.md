# PRD 5 — Cloud Exposure and Tunnelling
### Layer 5 of 7 · milestone M5 · owner [I]

**Covers:** FR-5.1, FR-5.2 · **Book:** Chapter 2 §2.4 · **Depends on:** Layers 1–4
**Exit criterion:** an agent on a remote machine connects through a public URL and plays a
complete 6-sub-game series against the local agent.

---

## 1. Purpose

Move from a simulation on one machine to a genuinely distributed system on the public internet.
From this layer on, the failure modes are real: latency, dropped connections, and an opponent who
disappears mid-protocol.

The book is blunt about the significance: a system that runs on the developer's machine is not
finished; it is finished when it survives failures, load and disconnection.

---

## 2. Background

Most machines sit behind a firewall and network address translation, so they cannot be reached
directly from the internet. A tunnelling tool creates a public URL that traverses NAT and forwards
to the local port — the practical answer to the same problem STUN addresses at protocol level.

The consequence for this project: **tunnel resilience is game resilience.** If a tunnel drops, the
opponent cannot verify moves and the turn synchronisation deadlocks. A dropped tunnel is not a
networking inconvenience; it is a lost match.

---

## 3. Requirements

### 3.1 Exposure

| ID | Requirement |
|---|---|
| 5.1 | The local FastMCP server is exposed publicly via ngrok (M#10). |
| 5.2 | The public URL is obtained programmatically at startup, not copied by hand. |
| 5.3 | Use the account's **static dev domain** (`*.ngrok-free.dev`), so the address survives restarts. |
| 5.4 | Localtonet is documented as a fallback and selectable by config. |

**Static domain — decided.** Every free ngrok account is now assigned a permanent dev domain.
This matters because with a rotating URL, a tunnel restart mid-series strands the opponent at a
dead address, and every match would need the URL re-exchanged during negotiation. A fixed address
goes into the declaration JSON once and stays valid. Reserving a *custom* name still needs a paid
plan; we do not need one.

Free-plan limits, comfortably above a league series: 20 000 HTTP requests/month, 1 GB/month,
3 concurrent endpoints. A 6-sub-game series at ~35 steps and 4 protocol messages per step is on
the order of 1 000 requests.

### 3.2 Resilience

| ID | Requirement |
|---|---|
| 5.5 | Detect tunnel loss and attempt reconnection. |
| 5.6 | After reconnect, re-run the handshake — the opponent must not be left talking to a stale session. |
| 5.7 | Tunnel health feeds the Watchdog (Layer 6). A dead tunnel triggers a controlled action within `watchdog_timeout_sec`. |
| 5.8 | If reconnection fails within the deadline, end in a clean `TECHNICAL_LOSS` with a persisted log — **never** a hang. |

Losing on a technical fault is bad. Hanging is worse: it wastes the opponent's time, produces no
log, and leaves the match unresolvable, which under M#35 costs *both* teams their points.

### 3.3 Configuration

| ID | Requirement |
|---|---|
| 5.9 | `NGROK_AUTHTOKEN` from the environment, never committed (M#39). |
| 5.10 | Our port and the opponent's URL live in the **private** `game.toml` `[network]` section. |
| 5.11 | Our public URL is published in the declaration JSON at match start. |

### 3.4 Latency

| ID | Requirement |
|---|---|
| 5.12 | Measure round-trip latency during the rehearsal; record p50 and p95. |
| 5.13 | If p95 approaches `response_timeout_sec` (30 s), raise the timeout **by mutual agreement** — raising is always legal, lowering never is (M#12). |

---

## 4. Interface

```python
# core/infra/tunnel.py
TunnelManager(authtoken: str, port: int, domain: str | None)
  .start() -> str            # returns the public URL
  .is_alive() -> bool
  .restart() -> str
  .stop() -> None
```

Manual equivalent, for debugging:

```powershell
ngrok http 8081 --url YOUR-DOMAIN.ngrok-free.dev
```

---

## 5. Constraints

- Files ≤150 lines.
- No test may open a real tunnel. `TunnelManager` is tested against a mocked process.
- The tunnel must not be a hard dependency of Layers 1–4: local development continues on
  `127.0.0.1` without ngrok installed.

---

## 6. Alternatives considered

| Decision | Alternative | Why rejected |
|---|---|---|
| ngrok | Localtonet as primary | ngrok is the book's named example, better documented, and now offers a free static domain. Localtonet is kept as a documented fallback |
| Static dev domain | Dynamic URL re-exchanged per match | A restart mid-series would strand the opponent at a dead address |
| Programmatic tunnel management | Start ngrok by hand before each match | A manual step before a graded match is a step that gets forgotten |
| Reconnect then technical loss | Retry indefinitely | An unbounded wait is the deadlock the Deadline Tracker exists to prevent (M#6) |
| Public tunnel | Direct IP / port forwarding | Requires router access neither team controls, and would not work from a university network |

---

## 7. Test scenarios

| # | Scenario | Expected |
|---|---|---|
| T5.1 | Start the tunnel | Public URL returned; server reachable through it |
| T5.2 | Restart the tunnel | Same static domain returned |
| T5.3 | Simulated tunnel death | Detected within `watchdog_timeout_sec` |
| T5.4 | Reconnect succeeds | Handshake re-run; match resumes |
| T5.5 | Reconnect fails | Clean `TECHNICAL_LOSS`, log persisted, no hang |
| T5.6 | Missing `NGROK_AUTHTOKEN` | Readable startup error, not a stack trace |
| T5.7 | Two-machine rehearsal | Full 6-sub-game series over the public internet |
| T5.8 | Latency measurement | p50 and p95 recorded; margin against 30 s assessed |
| T5.9 | Opponent disconnects mid-`AWAITING_REVEAL` | Controlled transition to `TECHNICAL_LOSS` |

T5.7 needs both team members and a second machine — it cannot be simulated. **Book the slot in
advance;** it is the only task in the project with a hard human-availability dependency.

---

## 8. Traceability

| Rule | Where |
|---|---|
| M#10 | §3.1 — public exposure mandatory for league play |
| M#6, M#7 | §3.2 — deadline and watchdog integration |
| M#12 | §3.4 — timeouts may be raised, never lowered |
| M#39 | §3.3 — authtoken never committed |
| F | `response_timeout_sec` 30, `watchdog_timeout_sec` 60 |

**TODO tasks:** 5.1.1 – 5.3.2 · **Milestone:** M5

**Sources:** [Static dev domains for all ngrok users](https://ngrok.com/blog/free-static-domains-ngrok-users) · [ngrok Domains documentation](https://ngrok.com/docs/gateway/domains)
