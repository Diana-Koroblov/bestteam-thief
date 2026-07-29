# PRD 2 — FastMCP Infrastructure
### Layer 2 of 7 · milestone M2 · owner [D]

**Covers:** FR-2.1 … FR-2.6 · **Book:** Chapter 2 · **Depends on:** Layer 1
**Exit criterion:** a message leaving peer A over localhost is received and decoded correctly at
peer B, with the two peers running as separate OS processes.

---

## 1. Purpose

Prove the pipe works before loading it with anything complex. This layer moves *pure geometry*
between two processes — no natural language, no scent, no cryptography. If a message cannot make
the trip reliably, nothing built on top of it can be debugged, because every fault becomes a
multi-variable investigation.

---

## 2. Background

The architecture is symmetric peer-to-peer over Model Context Protocol, implemented with FastMCP.
The central insight: **each agent is simultaneously a server and a client.** It exposes tools the
opponent invokes, and it invokes the opponent's tools. There is no strong side and no weak side,
and there is no third party holding the truth.

This is the direct extension of lecture L09 (two agents conversing over MCP and calling external
tools), hardened for an adversarial setting: there, the goal was cooperation; here, every statement
the opponent makes requires verification.

---

## 3. Requirements

### 3.1 Process separation — the disqualifying requirement

| ID | Requirement |
|---|---|
| 2.1 | Cop and Thief run as two **completely separate OS processes** (M#1). |
| 2.2 | **No shared memory, no shared live-state module, no shared variables** between the two sides (M#2). |
| 2.3 | Separate config directories: `config/police/` vs `config/thief/`. |
| 2.4 | An automated test asserts no import path connects the live Cop process to the live Thief process. |

Sharing state is not a bug to be fixed later — it voids the solution even if the game "works"
technically, because it hands one side a back door into the other's local truth and breaks the
zero-trust model the whole architecture rests on.

The risk is concentrated in **local development**, where one team builds both agents on one
machine. In a league match the separation is inherent — different machines, different countries.
That is precisely why the discipline must be enforced by a test rather than by good intentions.

### 3.2 Server

| ID | Requirement |
|---|---|
| 2.5 | Each peer runs its own FastMCP server, tools registered with `@mcp.tool`. |
| 2.6 | Bind `0.0.0.0` on the configured port so a tunnel can expose it later (Layer 5). |
| 2.7 | The server holds **no game logic** — it is a communication surface only. |

### 3.3 Client

| ID | Requirement |
|---|---|
| 2.8 | The client addresses exactly **one** URL: the opponent's. No code path can reach a second peer. |
| 2.9 | Every call carries a deadline (Layer 6 makes it enforceable; the parameter exists from here). |
| 2.10 | Auth, transport and timeout failures raise **distinct typed exceptions** — never a bare `Exception`. |

### 3.4 Orchestrator

| ID | Requirement |
|---|---|
| 2.11 | The Orchestrator is the **single gateway** to all subsystems (M#3). |
| 2.12 | Peripheral modules never import one another; an import-graph test enforces it. |
| 2.13 | The Orchestrator coordinates only. It contains no decision logic and no low-level transport. |

### 3.5 Tool surface

Full contracts in `PRD_6_commit_reveal.md` and `PRD_negotiation.md`. Registered here as stubs so
the transport can be exercised end-to-end:

| Tool | Purpose |
|---|---|
| `receive_commit(hash, step)` | Accept the opponent's sealed move |
| `acknowledge(step)` | Confirm we are locked |
| `receive_reveal(move, hint, intent, step)` | Accept the opened move. **Nonce not accepted here** |
| `final_reveal(nonces)` | End-of-match disclosure only |
| `capture_claim()` / `capture_response()` | Truthful capture exchange (M#21) |
| `declare_barrier(cell)` | Exact cell, truthfully (M#15) |
| `negotiate(config_hash, game_count, scent_model_hash)` | Pre-match handshake |

Tools are produced by **factory functions** — one factory per tool, capturing the peer's state at
startup. Adding a tool costs one factory plus one registration line.

### 3.6 Transport scope

| ID | Requirement |
|---|---|
| 2.14 | Localhost is permitted **only** during early development (M#10). League play requires a public tunnel — Layer 5. |

---

## 4. Interface

```python
# core/infra/mcp_server.py
build_server(role: str, config: Config) -> FastMCP

# core/infra/mcp_client.py
MCPClient(opponent_url: str, timeout_sec: float)
  .call(tool: str, **kwargs) -> dict        # raises MCPAuthError | MCPTransportError | MCPTimeoutError

# core/runtime/orchestrator.py
Orchestrator(config, role)
  .start() / .stop()
  .subsystems -> MCPConnector | DecisionModule | LogManager | DeadlineTracker | Watchdog

# CLI
uv run python -m core peer --role police
uv run python -m core peer --role thief
```

---

## 5. Constraints

- Every file ≤150 lines. Split the server into construction and tool registration if needed.
- The server module must not import `core.domain.rules` — physics enforcement belongs to the
  runtime, not the transport.
- `asyncio` stays inside `core/infra`. The turn loop is synchronous; async must not leak upward.

---

## 6. Alternatives considered

| Decision | Alternative | Why rejected |
|---|---|---|
| FastMCP | Raw JSON-RPC over httpx | The Streamable HTTP transport needs an `initialize` handshake and a session header echoed on every request; hand-rolling it was already tried in HW6 and every call failed |
| One client, one URL | A client able to address both peers | HW6 did this and it is the shape of a shared-truth back door. Structurally preventing it is cheaper than auditing for it |
| Factory per tool | One large registration function | Factories keep files under the line limit and make each tool independently testable |
| Synchronous turn loop | Async throughout | The turn loop is inherently sequential — commit, wait, reveal. Async would add concurrency without concurrency to exploit |

---

## 7. Test scenarios

| # | Scenario | Expected |
|---|---|---|
| T2.1 | Start both peers as subprocesses | Two distinct PIDs, two config directories |
| T2.2 | Import-graph scan from `police/` | No module under `thief/` reachable, and vice versa |
| T2.3 | Geometric message A → B over localhost | Received and decoded identically |
| T2.4 | Call an unknown tool | `MCPCallError`, peer stays alive |
| T2.5 | Call with a bad token | `MCPAuthError`, distinct from transport failure |
| T2.6 | Opponent unreachable | `MCPTransportError` within the deadline, no hang |
| T2.7 | Malformed payload | Rejected with a typed error, peer stays alive |
| T2.8 | Peripheral module imports another peripheral | Import-graph test fails |
| T2.9 | Two peers, same config file | Identical `config_sha256` |
| T2.10 | Grep `core/ui/` for `core.domain` imports | No matches — SDK facade respected |

---

## 8. Traceability

| Rule | Where |
|---|---|
| M#1 | §3.1 — two separate processes |
| M#2 | §3.1 — no shared state, test-enforced |
| M#3 | §3.4 — Orchestrator as single gateway |
| M#10 | §3.6 — localhost is development only |
| M#26, M#27 | Deferred to Layer 4; this layer carries pure geometry |

**TODO tasks:** 2.1.1 – 2.4.2 · **Milestone:** M2
