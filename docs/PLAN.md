# Architecture and Planning Document (PLAN)
## Distributed Cops-and-Robbers over a Peer-to-Peer Network

| | |
|---|---|
| **Version** | 1.00 |
| **Team** | `bestteam` |
| **Companion documents** | `PRD.md` (what and why), `TODO.md` (when and by whom) |
| **Status** | Draft — awaiting approval before any code is written |

---

## 1. C4 model

### 1.1 Level 1 — System context

```
                          ┌───────────────────────────┐
                          │        Lecturer           │
                          │  (grades, receives JSON)   │
                          └─────────────▲─────────────┘
                                        │ signed JSON report (attachment)
                                        │
                                 ┌──────┴───────┐
                                 │  Gmail API   │  OAuth 2.0, send-only scope
                                 └──────▲───────┘
                                        │
  ┌─────────────────────────────────────┴──────────────────────────────────┐
  │                     OUR PEER  (one role per process)                    │
  │        bestteam-cop  ── or ──  bestteam-thief                           │
  └───────▲──────────────────────────────────────────────────▲─────────────┘
          │ MCP over public tunnel URL                        │ local HTTP
          │ (commit / ack / reveal / audit)                   │
  ┌───────┴───────────────┐                          ┌────────┴──────────┐
  │  OPPONENT TEAM PEER   │                          │  LLM provider     │
  │  (machine we do not   │                          │  Ollama (local)   │
  │   control)            │                          │  or Groq (cloud)  │
  └───────────────────────┘                          └───────────────────┘
```

There is deliberately **no** box in the middle. No match server, no referee, no shared database.

### 1.2 Level 2 — Containers

| Container | Process | Responsibility |
|---|---|---|
| **Peer runtime** | 1 per role, separate OS process | Negotiation → turn loop → audit |
| **FastMCP server** | inside the peer process | Exposes protocol tools to the opponent |
| **MCP client** | inside the peer process | Calls the opponent's tools at exactly one URL |
| **Live GUI** | inside the peer process (UI thread) | Local truth only |
| **Replay Viewer** | separate CLI/GUI entry point | Offline cryptographic verification of a saved log |
| **Tunnel** | external (`ngrok`) | Public URL, NAT traversal |

### 1.3 Level 3 — Components inside one peer

```
                         ┌──────────────────────────┐
                         │        PeerSdk           │  ← single public facade
                         └────────────┬─────────────┘
                                      │
                         ┌────────────▼─────────────┐
                         │      Orchestrator        │  ← single gateway (M#3)
                         │   + GamePhaseMachine     │
                         └────┬───┬───┬───┬───┬─────┘
              ┌───────────────┘   │   │   │   └───────────────┐
              │                   │   │   └───────┐           │
   ┌──────────▼────────┐ ┌────────▼───────┐ ┌─────▼──────┐ ┌──▼────────────┐
   │  MCP Connector    │ │ Decision Module│ │Log Manager │ │Deadline Track.│
   │ (server + client) │ │ (BrainBase)    │ │(commit log)│ │  + Watchdog   │
   └───────────────────┘ └────────────────┘ └────────────┘ └───────────────┘
```

No arrows between peripheral components — every interaction goes through the Orchestrator. This is
rule M#3, and it is what lets us swap the decision module without touching anything else.

---

## 2. Package layout

```
p2p-chase/                          ← one working tree, two publish targets
├── core/                           ← copied to BOTH repos
│   ├── domain/                     board, movement, barriers, scent, belief,
│   │                               rules, scoring, game_state
│   ├── crypto/                     canonical_json, nonce, commit_reveal, audit
│   ├── protocol/                   mcp tool contracts, negotiation, step-0,
│   │                               message schemas, capture claim
│   ├── runtime/                    peer_runtime, orchestrator, phase_machine,
│   │                               deadline_tracker, watchdog
│   ├── infra/                      llm providers, mcp transport, gmail sender,
│   │                               tunnel manager
│   ├── shared/                     config manager, gatekeeper, rate limiter,
│   │                               queue manager, call logger, system_info,
│   │                               version, constants
│   ├── sdk/                        PeerSdk facade (+ mixins)
│   └── ui/                         live GUI, replay viewer, draw utils
├── police/                         ← ONLY in bestteam-cop
│   └── brain.py                    PoliceBrain(BrainBase)
├── thief/                          ← ONLY in bestteam-thief
│   └── brain.py                    ThiefBrain(BrainBase)
├── config/
│   ├── police/                     ← ONLY in bestteam-cop
│   │   ├── game.toml               private, per-peer, NOT negotiated
│   │   ├── game.json               shared, signed, byte-identical (per match)
│   │   └── rate_limits.json
│   └── thief/                      ← ONLY in bestteam-thief
├── docs/  tests/  scripts/  notebooks/  results/  assets/
├── pyproject.toml  uv.lock  .env-example  .gitignore  README.md
```

### 2.1 Publication model

```
                    p2p-chase/  (one local working tree)
                            │
              ┌─────────────┴──────────────┐
              │   scripts/publish.py       │
              └─────────────┬──────────────┘
        core/ + police/ +   │   core/ + thief/ +
        config/police/      │   config/thief/
              ▼             │             ▼
    ┌──────────────────┐    │    ┌──────────────────┐
    │  bestteam-cop    │◄───┴───►│ bestteam-thief   │
    │  README ─────────┼─────────┼──► cross-link    │
    └──────────────────┘         └──────────────────┘
```

`publish.py` copies the role-relevant subset into two sibling clones, then commits and pushes. The
cop repo never contains `thief/` or `config/thief/`, and vice versa.

Locally, the tree contains both roles so we can run self-play in two terminals for testing. The two
processes still communicate **only over MCP** — there is no import path joining the live Cop process
to the live Thief process. That is the substance of rule M#2, and the publication split is the
visible evidence of it.

---

## 3. Sequence — one game step

```
   Cop peer                                            Thief peer
      │                                                     │
      │ 1. compute move + hint + intent (pure Python)        │
      │    nonce = secrets.token_hex(16)                     │
      │    H = SHA256(canonical_json{state,move,intent,nonce})│
      │                                                     │
      │──────────── receive_commit(H) ──────────────────────►│
      │◄─────────── acknowledge(locked) ────────────────────│
      │                                                     │
      │◄─────────── receive_commit(H') ─────────────────────│
      │──────────── acknowledge(locked) ───────────────────►│
      │                                                     │
      │──────────── receive_reveal(move, hint) ────────────►│   nonce still hidden
      │◄─────────── receive_reveal(move', hint') ───────────│
      │                                                     │
      │ 2. each side validates the opponent's move against   │
      │    the shared physics and rejects if illegal         │
      │ 3. each side applies emission + decay                │
      │ 4. each side updates its Bayesian posterior          │
      │                                                     │
      ╎              ... repeat until terminal ...           ╎
      │                                                     │
      │──────────── final_reveal(all nonces) ──────────────►│   end of match only
      │◄─────────── final_reveal(all nonces) ───────────────│
      │ 5. mutual audit: re-hash every step, compare         │
      │ 6. agree result → each side emails its own JSON      │
```

Every arrow carries a deadline. An expired deadline is a **failure**, never a reason to keep waiting
(M#6).

---

## 4. Game phase state machine

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

Implemented as an explicit transition table. Any target not listed for the current state raises
immediately (M#5) — a logic bug becomes a visible exception at development time rather than a silent
deadlock during a graded match.

---

## 5. Data design

### 5.1 Configuration split

The decision rule, from Appendix B: *"must the opponent agree to this value, or depend on it?"* If
yes it belongs in the shared JSON; if no it stays in the private TOML.

| File | Format | Scope | Signed | Contents |
|---|---|---|---|---|
| `config/<role>/game.json` | JSON | shared, byte-identical | **yes** | Board, movement, barriers, scoring, pheromones, network, league, rate limiter |
| `config/<role>/game.toml` | TOML | private per peer | no | Team identity, port, opponent URL, `[strategy]` brain classes, `[trash_talk]` provider, `[llm]` settings, email target, GUI settings |
| `config/<role>/rate_limits.json` | JSON | private | no | Gatekeeper quota / bucket / DOS thresholds |

JSON values **overlay** the TOML: a private file can never weaken a signed condition. TOML is chosen
for the private file precisely because it supports comments — the `[strategy]` and `[trash_talk]`
sections are self-documenting for whoever edits them.

A fresh `config_<game_id>_g<NN>.json` is produced per match, committed to the repo, so any match is
exactly reproducible (Appendix F §2).

### 5.2 The four JSON artefacts

| Artefact | Filename | Produced | Purpose |
|---|---|---|---|
| Declaration | `declaration_<game_id>.json` | before match | Teams, members, four repo links, MCP URLs, hardware, LLM model, token cap, timings |
| Config | `config_<game_id>_g<NN>.json` | per sub-game | The locked negotiated parameters |
| Log | `log_<game_id>_g<NN>.json` | during sub-game | Commits, reveals, moves, hints, nonces, hashes — feeds the Replay Viewer |
| Result | `result_<game_id>.json` | after match | Per-sub-game and cumulative scores, `github_commit`, total tokens, four repo links — **this is the emailed report** |

All four share a `game_uid`; filenames derive from `game_id` so files from different matches can
never be confused.

### 5.3 Canonical serialisation

Both peers must hash byte-identical input, so every hashed record is serialised as:

```python
json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
```

This is not a stylistic choice. Two peers that serialise differently produce different hashes, every
verification fails, and both teams score zero.

---

## 6. Architectural decision records

### ADR-001 — Shared core, split role packages, script-driven publication

**Status:** accepted
**Context:** The rulebook requires two separate repositories (M#49) and prohibits any shared runtime
state between the Cop and the Thief (M#2). It does not prohibit shared source code — the lecturer's
own reference repository keeps `config/police/` and `config/thief/` in a single tree.
**Alternatives considered:**

| Option | Verdict |
|---|---|
| Two fully independent repos, engine duplicated | Rejected — guaranteed drift over 15 days, double the bug surface |
| Identical mirror pushed to both repos | Rejected — every repo would contain both brains and both config trees, inviting the grader to wonder whether the processes are coupled |
| **Shared `core/`, split role packages, publish script** | **Accepted** |

**Decision:** Develop in one working tree. `scripts/publish.py` pushes `core/ + police/ +
config/police/` to `bestteam-cop` and `core/ + thief/ + config/thief/` to `bestteam-thief`.
**Consequences:** No manual sync burden; each published repo demonstrably contains one role only; the
publish script itself is evidence of separation discipline. Cost: a grader must clone both repos to
run a local self-play match — which is exactly the two-process model the rulebook prescribes, and the
cross-linked READMEs make it explicit.

### ADR-002 — Heuristic movement policy, no reinforcement learning

**Status:** accepted
**Context:** Ch. 6 presents three equal-standing options: pure heuristics, your own heuristic
algorithm, or RL. It states plainly that RL was never taught in the course and that strong agents are
routinely built without it.
**Decision:** Layer 3 ships the mandated baseline (Bayesian posterior + Manhattan minimisation).
Layer 4 onward upgrades to expectimax over the belief map, with barrier-trap planning for the Cop and
scent-aware evasion for the Thief. No RL.
**Rationale:** A deterministic policy is unit-testable, which feeds the 85 % coverage requirement,
which feeds the code-quality grade. RL's only distinct payoff is the learning-curve README section,
which the rulebook makes explicitly conditional. With 15 days, the days RL would consume are worth
more spent on additional league matches — up to 25 grade points.
**Revisit if:** all seven layers are complete and stable before 9 Aug.

### ADR-003 — Per-machine LLM provider, template fallback, algorithmic movement always

**Status:** accepted
**Context:** Ch. 6 forbids delegating movement decisions to a language model — LLMs hallucinate in
Cartesian space. Appendix F defines four provider modes. Our two development machines differ: one has
no GPU, one does.
**Decision:** `[trash_talk] provider` is a private per-peer setting. Diana → `groq`; partner →
`ollama`; **graded matches are hosted from the partner's machine on `ollama`**. Every provider falls
back to `template` automatically on error or timeout. Movement is always pure Python.
**Rationale:** Computational fairness is scored — the lecturer normalises to reward results achieved
on modest resources. Ollama gives genuinely generated free-form language (M#26) at zero API tokens
and no rate limit, and demonstrates lecture L08. The automatic fallback means a provider outage can
degrade quality but can never lose a match.
**Consequence:** All cloud provider traffic routes through the Gatekeeper and is metered against
`[token budget per series]`.

### ADR-004 — Full Bayesian posterior rather than a point estimate

**Status:** accepted
**Context:** On a 7×7 board the posterior is 49 floats — computationally free. A most-likely-cell
estimator discards the distribution shape.
**Decision:** Maintain a full posterior, updated by (1) scent-field likelihood, (2) verbal-hint
likelihood scaled by a per-opponent reliability coefficient, (3) motion model (one orthogonal step or
stay), (4) barrier and own-cell masking, (5) normalisation.
**Rationale:** The distribution is what enables expectimax, entropy-driven exploration, and bluff
detection. The reliability coefficient turns "the opponent lied" into a measurable, plottable
statistic — a genuinely original extension and strong README material.
**Alternative rejected:** particle filter — overkill on 49 cells.

### ADR-005 — Tkinter for both GUI surfaces

**Status:** accepted
**Context:** Ch. 7 names Tkinter and PyQt. The prior HW6 codebase used pygame.
**Decision:** Tkinter for the Live GUI and the Replay Viewer, sharing one widget layer.
**Rationale:** Standard library, no extra dependency, explicitly sanctioned by the rulebook, and the
lowest-risk choice for producing the mandatory screenshots on two different machines. Avoids pygame's
game-loop/threading friction for what is essentially two static panels with a timer.

### ADR-006 — Fresh codebase, deliberate port from HW6

**Status:** accepted
**Context:** HW6 is structurally strong but modelled a centralised, single-team, both-agents-in-one-
process game with 8-directional movement, a Chebyshev visibility radius, and a god-view GUI.
**Decision:** Start from a clean skeleton; port modules individually and deliberately.
**Rationale:** Two HW6 behaviours are outright disqualifying under the new rules — the god-view GUI
(M#9) and diagonal movement (M#14). Refactoring in place risks one of them surviving unnoticed. A
fresh tree makes every carried-over line a conscious choice.
**Port list:** Gatekeeper family, `PeerSdk` facade pattern, NLP parser (including the numeric-
coordinate rejection regex, now binding under M#27), Gmail sender, test conventions, the 150-line
guard test, ruff/coverage config.

### ADR-007 — Local physics enforcement by both peers

**Status:** accepted
**Context:** There is no referee. Each peer holds only its own local truth.
**Decision:** Each peer independently validates every opponent move against the shared config and
rejects illegal moves. Illegal move → opponent's technical loss.
**Rationale:** This is the structural consequence of removing the judge and the deepest change from
HW6, where a single `TurnManager` adjudicated both sides. It requires the shared config to be
byte-identical (M#11), which is why the pre-match handshake locks it cryptographically.

---

## 7. Reliability design

| Pattern | Scope | Trigger | Action |
|---|---|---|---|
| **Deadline Tracker** | one request | Expiry (default 30 s) | Controlled retry, then technical loss |
| **Watchdog** | whole process | No heartbeat (default 60 s) | Persist state, controlled shutdown |
| **Phase machine** | game flow | Illegal transition | Raise immediately |
| **Gatekeeper** | outbound API | Quota full / no token / anomaly | Reject, block, or lock the pipe |
| **Provider fallback** | verbal layer | LLM error or timeout | Silent degrade to `template` |
| **Tunnel monitor** | transport | Tunnel drop | Re-tunnel, re-handshake, resume |

### 7.1 Gatekeeper — three cumulative gates

```
  outgoing ──► Quota Manager ──► Token Bucket ──► DOS Detector ──► Gmail API
   report        │ full            │ empty          │ anomaly
                 ▼                 ▼                ▼
              Rejected           Blocked          LOCKED
```

Token bucket rule: `tokens ← min(C, tokens + r·Δt)`, allow iff `tokens ≥ 1`. Only a request that
clears all three gates reaches the API. HTTP 429 is honoured with backoff — blind retry after a 429
risks account suspension, which would cost every remaining match.

Note the rulebook's warning about the word "token", which means three unrelated things here:
rate-limiter tokens, LLM tokens, and OAuth tokens. Our module and variable names keep them distinct.

---

## 8. Deployment

| Environment | Layers | Transport |
|---|---|---|
| Local single-machine | 1–4 | Two processes, `127.0.0.1`, distinct ports |
| Local two-machine (LAN) | 5 rehearsal | Direct IP |
| **League** | 1–7 | ngrok public URLs, both sides tunnelled |

Graded matches run from the partner's machine (Ollama, zero tokens). Step-0 declares that machine's
actual hardware and the exact commit hash played (M#53).

---

## 9. Extension points

| Extension | Location | Mechanism |
|---|---|---|
| New brain | `police/brain.py`, `thief/brain.py` | Subclass `BrainBase`, override `_pick_move` (+ `_decide_move` for the Cop); select via `[strategy]` in the TOML |
| New LLM provider | `core/infra/llm/` | Implement the `TextProvider` interface; select via `[trash_talk] provider` |
| New MCP tool | `core/protocol/` | Factory per tool, registered with one `mcp.tool()` line |
| New consumer | `core/sdk/` | `PeerSdk` is the only public facade |
| Rule change | `config/<role>/game.json` | Negotiated per match, no code change |

---

## 10. Risk register

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | Cannot schedule enough opponents | Caps final grade | Start outreach immediately; target 6–8; treat as the top-priority task |
| R2 | Opponent interprets a rule differently | Match voids | Pre-match negotiation resolves and records every ambiguity in the config JSON |
| R3 | Tunnel drops mid-protocol | Technical loss | Watchdog + re-handshake + state persistence |
| R4 | Hash mismatch from serialisation divergence | Both teams score 0 | Canonical JSON; exchange a worked numeric example during negotiation |
| R5 | God-view GUI survives from HW6 | **Project disqualified** | Fresh codebase; explicit local-truth test asserting the GUI never receives opponent position |
| R6 | Secret committed | **Project failed** | `.gitignore` from day one; pre-push scan in `publish.py` |
| R7 | Opponent does not send their report | Match voids for both | Confirm their send before closing the session; keep the log as evidence |
| R8 | Layer 4 (scent + belief + NL) overruns | Schedule collapse | Most schedule slack allocated here; baseline from layer 3 remains playable |
| R9 | LLM latency exceeds the step deadline | Technical loss | `step_deadline_seconds` hard cap + automatic `template` fallback |
| R10 | 150-line rule violated late | Quality deductions | Automated guard test from day one, not at the end |

---

## 11. Traceability

Every functional requirement in `PRD.md` maps to a component here and to a task in `TODO.md`. The
per-algorithm PRDs required by the excellence guide (§2.3) are:

| Document | Covers |
|---|---|
| `PRD_1_base_logic.md` | Board, movement, barriers, capture, scoring |
| `PRD_2_mcp_infra.md` | FastMCP server/client, tool contracts, process separation |
| `PRD_3_strategy_baseline.md` | BrainBase, baseline shortest-path policy |
| `PRD_4_scent_and_belief.md` | Emission/decay model, Bayesian posterior, reliability coefficient |
| `PRD_5_tunnelling.md` | Public exposure, NAT traversal, reconnection |
| `PRD_6_commit_reveal.md` | Canonical JSON, nonce, four-phase protocol, audit, Step-0 |
| `PRD_7_reporting.md` | Gatekeeper, Gmail, four JSON artefacts, GUI, Replay Viewer |
| `PRD_strategy_advanced.md` | Expectimax over belief, barrier-trap planning, scent-aware evasion |
| `PRD_negotiation.md` | Pre-match handshake, config locking, game-count declaration |
| `PRD_state_machine.md` | Phase transitions, deadline tracking, watchdog |
