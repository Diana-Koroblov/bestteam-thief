# Product Requirements Document (PRD)
## Distributed Cops-and-Robbers over a Peer-to-Peer Network

| | |
|---|---|
| **Version** | 1.00 |
| **Team** | `bestteam` (8-character team ID, no spaces — M#45) |
| **Repositories** | `bestteam-cop`, `bestteam-thief` |
| **Course** | Orchestration of AI Agents, Dept. of Computer Science, University of Haifa, 2026 |
| **Rulebook** | `police_thief_p2p.pdf` v3.0.0 — Appendix F is the sole source of truth for numeric values |
| **Quality standard** | `software_submission_guidelines.pdf` v3.00 |
| **Deadline** | 12/08/2026, 23:59 (hard) |
| **Status** | Draft — awaiting approval before any code is written |

---

## 1. Overview and context

### 1.1 What we are building

Two autonomous, structurally symmetric agents — a **Cop** and a **Thief** — that pursue and evade each
other on a discrete `[board size]` grid across a series of `[number of sub-games]` sub-games, over a
real peer-to-peer network, **with no central server and no referee**.

Each agent is simultaneously an MCP **server** (exposing tools the opponent calls) and an MCP
**client** (calling the opponent's tools). Neither agent observes the true world state. Each builds a
probabilistic belief about its opponent's position from two sources: the opponent's decaying
pheromone trail, and a free-text verbal hint that may be a deliberate lie. Integrity without a judge
is enforced cryptographically via SHA-256 commit-reveal plus a full mutual log audit.

### 1.2 The problem this solves

Centralised multi-agent systems delegate truth, arbitration and trust to a server. Removing that
server is not a simplification — it forces every guarantee to be rebuilt from below: coordination
without a scheduler, trust without an authority, and decision-making under an information fog that
the adversary is actively trying to thicken. This project is a scale model of the question that
defines distributed AI systems in production.

### 1.3 Actors

| Actor | Role |
|---|---|
| **Our Cop peer** | Autonomous process; pursues, places barriers, claims capture |
| **Our Thief peer** | Autonomous process; evades, survives to the step threshold |
| **Opponent peer** | A different team's agent, running on a machine we do not control, over the public internet |
| **Lecturer** | Receives the signed JSON result report by email; grades the two repositories |
| **Team members** | Diana (dev machine: no GPU → Groq), partner (dev machine: GPU-capable → Ollama; hosts graded matches) |

### 1.4 Explicitly out of scope

- Reinforcement learning. The rulebook classes it as "one optional tool", states it was never taught
  in the course, and presents heuristics as fully competitive. See ADR-002 in `PLAN.md`.
- Any central match server, shared database, or third-party arbiter.
- Human-in-the-loop play. Both agents are fully autonomous once a match starts.
- Training or fine-tuning any model.

---

## 2. Goals and success metrics

### 2.1 Primary goal

Place as high as possible in the league. Grade band: **last place = 75, first place = 100.**

### 2.2 Measurable KPIs

| # | KPI | Target | Floor | Source |
|---|---|---|---|---|
| K1 | Counted league matches vs. **different** teams | 6–8 | **2** | Appendix F, M#31 |
| K2 | Matches lost to technical failure (crash, timeout, deadlock) | **0** | 0 | Ch. 8 |
| K3 | Matches voided for hash mismatch or `TAMPERED` | **0** | 0 | Rules #19, #22 |
| K4 | Result reports delivered by both sides | **100 %** | 100 % | Rule #35 |
| K5 | Test coverage | ≥ 90 % | **85 %** | Excellence guide §6.2 |
| K6 | Ruff violations | **0** | 0 | Excellence guide §7.1 |
| K7 | Files over 150 LOC | **0** | 0 | Excellence guide §3.2 |
| K8 | Token consumption per series | ≈ 0 for graded matches | ≤ `[token budget per series]` | Appendix F, Ch. 5 |
| K9 | Secrets committed to either repo | **0** | 0 | Rules #39, #40 |

### 2.3 The four success metrics (Ch. 11)

The rulebook states these four decide a team's success. Each maps to a concrete deliverable.

| Metric | Our evidence |
|---|---|
| **Coordination** | Symmetric FastMCP P2P peers, turn state machine, no central scheduler |
| **Adaptation** | Full Bayesian posterior over the board, updated from scent likelihood and a reliability-weighted verbal hint |
| **Integrity** | Commit-reveal over SHA-256, mutual audit, Replay Viewer showing `Verified OK` |
| **Architecture** | Orchestrator gateway, Gatekeeper, Deadline Tracker, Watchdog, strict state machine |

---

## 3. Functional requirements

Requirements are grouped by the rulebook's seven mandated build layers (Ch. 10). Each layer must run
end-to-end before the next is started. `M` = mandatory rule from Appendix E, `F` = value from
Appendix F, `X` = excellence-guide requirement.

### Layer 1 — Base logic

| ID | Requirement | Ref |
|---|---|---|
| FR-1.1 | Square grid of side `[board size]` (default 7×7), origin and index base loaded from config | F |
| FR-1.2 | Move set is exactly 4 orthogonal directions plus STAY. Diagonal moves must be rejected | M#13, M#14, F |
| FR-1.3 | On a turn where the Cop forgoes movement it may place one barrier on its own cell or one of the 4 orthogonally adjacent cells | Ch. 3 |
| FR-1.4 | Barriers are permanent and impassable to both players. Quota `[barrier quota]` (default 14) is enforced | F |
| FR-1.5 | A barrier placed on the Thief's current cell counts as a capture (Cop wins) | M#46 |
| FR-1.6 | A Thief with no legal move at all counts as captured | M#47 |
| FR-1.7 | Every barrier placement is truthfully declared with its exact cell. Hidden or misreported placement is prohibited | M#15, M#16 |
| FR-1.8 | Capture when the Cop lands on the Thief's cell and issues a Capture Claim | Ch. 3 |
| FR-1.9 | Thief wins by surviving `[survival threshold]` (default 35) valid steps | F |
| FR-1.10 | Scoring: capture 20/5, survival 5/10, tie 2/2, technical loss 0/0 | M#48, F |
| FR-1.11 | Both peers compute the identical transition function from the identical shared config | Ch. 3 |

### Layer 2 — FastMCP infrastructure

| ID | Requirement | Ref |
|---|---|---|
| FR-2.1 | Cop and Thief run as two **completely separate processes** | M#1 |
| FR-2.2 | No shared memory, no shared live-state module, no shared variables between the two sides | M#2 |
| FR-2.3 | Each peer runs its own FastMCP server exposing tools via `@mcp.tool`, and its own client calling the opponent's server | Ch. 2 |
| FR-2.4 | Separate config directories per role (`config/police/` vs `config/thief/`) | Ch. 2.4.2 |
| FR-2.5 | The Orchestrator is the single entry point to all subsystems; peripheral modules never call each other directly | M#3 |
| FR-2.6 | Localhost is permitted for early development only | M#10 |

### Layer 3 — Blind strategy

| ID | Requirement | Ref |
|---|---|---|
| FR-3.1 | A decision module separate from the transport layer, wired into `PeerRuntime` between hint-decode and commit-pack | Ch. 6 |
| FR-3.2 | Baseline policy: shortest legal path to a known target, computed with no manual intervention | Ch. 10 milestone 3 |
| FR-3.3 | Brains are pluggable: `police_class` / `thief_class` in the private config point at a `BrainBase` subclass overriding `_pick_move` (and `_decide_move` for the Cop) | Appendix F §5 |
| FR-3.4 | Movement decisions are always algorithmic Python. The LLM never decides a move | M#25, Ch. 6 |

### Layer 4 — Natural language and scent

| ID | Requirement | Ref |
|---|---|---|
| FR-4.1 | Pheromone emission field of size `[scent field size]` (5×5) around the agent, centre intensity `[scent centre intensity]` (0.9), radial falloff | F |
| FR-4.2 | Decay at end of each full turn: `τ(t+1) = max(0, (1−ρ)·τ(t) + Δτ)` with ρ = `[scent decay rate]` (0.10) | F, Ch. 4 |
| FR-4.3 | Emission and decay are symmetric: both agents emit, each reads only the opponent's field | Ch. 4 |
| FR-4.4 | The emission/decay model, plus a concrete numeric example, is exchanged and cryptographically locked before the series begins | M#23 |
| FR-4.5 | Full Bayesian posterior over all cells, updated from scent likelihood and hint likelihood scaled by a per-opponent reliability coefficient | Ch. 6 |
| FR-4.6 | All inter-agent communication is in free natural language | M#26 |
| FR-4.7 | Direct numeric position protocols are prohibited; outgoing text is scanned and rejected if it contains bare coordinates | M#27 |
| FR-4.8 | Each hint is capped at `[hint word limit]` (15) words, enforced for every provider including the LLM system prompt | F |
| FR-4.9 | An `Intent` flag (`truth` / `lie`) is committed alongside the move | Ch. 5 |
| FR-4.10 | Optional real-world landmark flavour driven by `[map area]` | F |

### Layer 5 — Cloud exposure

| ID | Requirement | Ref |
|---|---|---|
| FR-5.1 | The local FastMCP server is exposed to the public internet via a tunnel (ngrok or Localtonet) | M#10 |
| FR-5.2 | Tunnel health is a Watchdog input; a dropped tunnel triggers reconnect and re-handshake, not a hang | Ch. 2, Ch. 8 |

### Layer 6 — Security and cryptography

| ID | Requirement | Ref |
|---|---|---|
| FR-6.1 | Four-phase protocol per step: `Commit` → `Acknowledge` → `Reveal` → `Final Audit` | Ch. 5 |
| FR-6.2 | `H = SHA256(State ‖ Move ‖ Intent ‖ Nonce)` over **canonical JSON** (sorted keys, fixed separators) so both peers hash byte-identical input | M#17, Ch. 5 |
| FR-6.3 | Nonce generated with `secrets.token_hex(16)`, kept absolutely secret until the end-of-match audit | M#18 |
| FR-6.4 | Verification uses `secrets.compare_digest` | Ch. 5 |
| FR-6.5 | Any hash mismatch at audit voids the match technically | M#19 |
| FR-6.6 | Capture claims must be answered truthfully; false capture claims are prohibited | M#21, M#22 |
| FR-6.7 | Step-0 declaration before the first move: OS, CPU cores/frequency, RAM, GPU/VRAM, LLM model name, code version, team name, sub-game number, **and the GitHub commit hash actually played** — signed | M#24, M#53 |
| FR-6.8 | LLM token consumption is metered, locked at Step-0, and reported | M#54 |

### Layer 7 — Reporting and visualisation

| ID | Requirement | Ref |
|---|---|---|
| FR-7.1 | Live GUI displays **local truth only**: own position, own sensed scent, own belief heatmap, turn banner | M#8 |
| FR-7.2 | The full objective board state must **never** be displayed in the live GUI | M#9 |
| FR-7.3 | Replay Viewer: load a saved log, step forwards/backwards, re-hash each entry, show `Verified OK` or `TAMPERED` | M#20 |
| FR-7.4 | One `TAMPERED` verdict voids the match immediately | Ch. 7 |
| FR-7.5 | Automated end-of-match reporting via Gmail API | M#32 |
| FR-7.6 | The report is a structured JSON **attachment**. Free-text reports are prohibited | M#33, M#34 |
| FR-7.7 | Both teams agree the result and **each sends its own report separately** | M#35 |
| FR-7.8 | Reports go to `rmisegal+uoh26finalgame@gmail.com` | M#51 |
| FR-7.9 | Gmail access uses OAuth 2.0 with **send-only** scope | M#30 |
| FR-7.10 | Four JSON artefacts per match: declaration, config, log, result — named from `game_id` / sub-game number, sharing a `game_uid` | Ch. 9 |
| FR-7.11 | Mutual log audit completed before agreeing the shared result JSON | M#36 |

### Cross-cutting — reliability and league conduct

| ID | Requirement | Ref |
|---|---|---|
| FR-8.1 | Strict game-phase state machine; illegal transitions raise immediately | M#4, M#5 |
| FR-8.2 | Deadline Tracker: every MCP request carries an expiry; expiry is a failure, not a reason to keep waiting | M#6 |
| FR-8.3 | Watchdog: background heartbeat monitor performing controlled shutdown with state persistence | M#7 |
| FR-8.4 | Gatekeeper with three cumulative gates: quota manager → token bucket → DOS detector | M#28, M#29 |
| FR-8.5 | Honest declaration of counted games played, at the start of every match | M#37, M#38 |
| FR-8.6 | One counted match per opponent. Warm-up matches are uncounted and allowed | M#52 |
| FR-8.7 | The shared config is byte-identical on both sides and cryptographically locked | M#11 |
| FR-8.8 | Appendix F minimums may be raised by agreement, never lowered | M#12 |

---

## 4. Non-functional requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-1 | **Structure** | `README.md` at user-manual level in each repo; `docs/` with `PRD.md`, `PLAN.md`, `TODO.md`; a dedicated PRD per algorithm/mechanism (X, M#50) |
| NFR-2 | **Architecture** | All business logic reachable only through the `PeerSdk` facade. GUI, CLI, Replay and tests contain zero business logic (X §4.1) |
| NFR-3 | **OOP** | No duplicated logic. Shared behaviour lives in base classes or mixins; each mixin covers exactly one concern (X §4.2) |
| NFR-4 | **File size** | No source file exceeds 150 lines of code, blanks and comments excluded. Enforced by an automated test (X §3.2) |
| NFR-5 | **Testing** | TDD; every public function has at least one test; happy path and error path both covered; coverage ≥ 85 %, suite fails below it (X §6) |
| NFR-6 | **Linting** | Zero `ruff` violations with `select = ["E","F","W","I","N","UP","B","C4","SIM"]` (X §7.1) |
| NFR-7 | **Configuration** | Zero hardcoded configurable values. Shared/negotiated data in JSON, private per-peer data in TOML, rate limits in `config/rate_limits.json`, immutable constants in `constants.py` (X §7.2, Appendix B) |
| NFR-8 | **Secrets** | Environment variables only. `.env-example` committed with dummy values; `.gitignore` excludes `.env`, `credentials.json`, `token.json`, `*.pem`, `*.key` (X §7.4, M#39, M#40) |
| NFR-9 | **Packaging** | `uv` exclusively. `pip`, `venv`, `python -m`, `virtualenv` are forbidden. `pyproject.toml` is the single dependency source of truth; `uv.lock` committed (X §8.4) |
| NFR-10 | **Versioning** | Code version in `core/shared/version.py`, config version keys in every JSON, all starting at `1.00`. Version compatibility validated at startup (X §8.1) |
| NFR-11 | **Reliability** | Every foreseeable failure — opponent disconnect, malformed hint, tunnel drop mid-protocol, LLM timeout, hash mismatch — ends in a clean `TECHNICAL_LOSS` with a persisted log. Never a hang, never an unhandled traceback (Ch. 11) |
| NFR-12 | **Computational fairness** | Prefer algorithmic efficiency over raw compute. Graded matches run at effectively zero API tokens (Ch. 5, Ch. 9) |
| NFR-13 | **Observability** | Structured logging throughout; every external API call recorded by the Gatekeeper's call logger |
| NFR-14 | **Usability** | GUI evaluated against Nielsen's 10 heuristics; every screen and state screenshotted (X §10) |
| NFR-15 | **Reproducibility** | Annotated Git tag `v1.0-submission`; the exact commit hash played is recorded per match (M#41, M#53) |
| NFR-16 | **Research** | Parameter sensitivity study plus an analysis notebook with quality visualisations (X §9) |
| NFR-17 | **Prompt log** | `docs/PROMPT_LOG.md` recording the significant prompts used to build the system. Defining good agent instructions is explicitly part of the assessed task (X §8.3, Ch. 11 §11.5a) |

---

## 5. Binding parameters

All numeric values come from **Appendix F only**. `minimum` may be raised by mutual agreement and
never lowered; `fixed` cannot change at all; `negotiable` is free by agreement.

| Parameter | Config key | Default | Status |
|---|---|---|---|
| Board size | `board_and_agents.grid_size` | 7 | minimum |
| Number of agents | `board_and_agents.num_agents` | 2 | fixed |
| Axis origin corner | `board_and_agents.axis_origin_corner` | `top-left` | negotiable |
| Axis start index | `board_and_agents.axis_start_index` | 0 | negotiable |
| Thief start | `board_and_agents.thief_start` | `[3,3]` | negotiable |
| Cop start | `board_and_agents.cop_start` | `[0,0]` | negotiable |
| Map area | `world.map_area` | `New York` | negotiable |
| Hint word limit | `world.hint_max_words` | 15 | negotiable |
| Move set | `movement_and_barriers.move_set` | `N,S,E,W,STAY` | fixed |
| Barrier quota | `movement_and_barriers.max_barriers` | 14 | minimum |
| Max moves | `movement_and_barriers.max_moves` | 35 | minimum |
| Survival threshold | `movement_and_barriers.survival_threshold` | 35 | minimum |
| Scent centre intensity | `pheromones.pheromone_center_intensity` | 0.9 | fixed |
| Scent decay ρ | `pheromones.pheromone_decay` | 0.10 | fixed |
| Scent field size | `pheromones.pheromone_grid_size` | 5 | fixed |
| Capture — Cop / Thief | `scoring.capture_cop` / `capture_thief` | 20 / 5 | fixed |
| Survival — Cop / Thief | `scoring.survival_cop` / `survival_thief` | 5 / 10 | fixed |
| Tie score | `scoring.tie_score` | 2 | fixed |
| Technical loss | `scoring.technical_loss` | 0 | fixed |
| Sub-games per series | `network_and_league.num_games` | 6 | fixed |
| Diversity reward | `network_and_league.diversity_reward` | 10 | fixed |
| Min games to pass | `network_and_league.min_games_to_pass` | 2 | fixed |
| Max games per team | `network_and_league.max_games_per_team` | 10 | fixed |
| Token budget per series | `network_and_league.token_budget_per_series` | 200 000 | negotiable |
| Response timeout | `network_and_league.response_timeout_sec` | 30 | negotiable |
| Watchdog timeout | `network_and_league.watchdog_timeout_sec` | 60 | negotiable |
| Requests per minute | `rate_limiter_gatekeeper.requests_per_minute` | 30 | minimum |
| Concurrent requests | `rate_limiter_gatekeeper.concurrent_requests` | 2 | minimum |
| Retry backoff | `rate_limiter_gatekeeper.retry_backoff_sec` | 5 | minimum |
| Max retries | `rate_limiter_gatekeeper.max_retries` | 3 | minimum |
| Queue depth | `rate_limiter_gatekeeper.queue_depth` | 100 | minimum |

### 5.1 Documented discrepancy — `num_games`

Appendix F table 18 lists `[number of sub-games]` = **6**, status *fixed*. The sample
`config/game.json` in Appendix B ships `"num_games": 1`, annotated as "a single example sub-game",
with the text noting that a full league series requires `[number of sub-games]` sub-games.

**Our reading:** Appendix F governs. We default to **6** and treat the sample's `1` as a
single-sub-game development convenience. Recorded here and in the README per the rulebook's
academic-freedom clause, which guarantees a documented, reasoned choice is not penalised.

---

## 6. Assumptions, dependencies and constraints

### 6.1 Assumptions

- Opponent teams implement the same protocol from the same rulebook. Where their reading differs from
  ours, the pre-match negotiation resolves it and the resolution is recorded in the config JSON.
- Both team members can be online simultaneously for scheduled matches.
- Opponents will be reachable and responsive within the submission window.

### 6.2 Dependencies

| Dependency | Purpose | Risk if unavailable |
|---|---|---|
| FastMCP | Mandated transport | Blocking — no substitute permitted |
| ngrok / Localtonet | Public exposure | Blocking for league play; Localtonet is the documented fallback |
| Gmail API + OAuth 2.0 | Mandated reporting | Blocking — unreported match scores 0 |
| Ollama (partner's machine) | Zero-token verbal layer | Degrades to `template`; no match is lost |
| Groq API (Diana's machine) | Verbal layer during development | Degrades to `template`; no match is lost |
| Opponent availability | League matches | **Highest-risk item in the project** |

### 6.3 Hardware constraint and its consequence

Diana's machine has no GPU and cannot host a local model; the partner's machine can. This shapes two
decisions:

1. The verbal-layer provider is a **private, per-peer, per-machine** setting (`[trash_talk] provider`
   in the TOML), never part of the shared negotiated config. Diana develops against Groq; the partner
   develops against Ollama.
2. **Graded matches are hosted from the partner's machine using Ollama**, so token consumption in the
   result JSON is effectively zero. Computational fairness is scored: the lecturer normalises results
   to reward strong outcomes achieved on modest resources. A low token count is an advantage, not an
   admission.

Both providers fall back to `template` automatically on error or timeout, so a provider outage can
never cost a match.

### 6.4 Constraints

- **15 days.** Every design decision is weighed against schedule risk.
- The rulebook's layered build order is followed; skipping layers is explicitly warned against.
- The book overrides the reference code repository wherever they conflict.
- Where the book contradicts itself, we choose, document the contradiction, and justify the choice in
  the README. The rulebook guarantees a documented reasoned choice is not penalised.

---

## 7. Acceptance criteria

The project is complete when all of the following are observed — not intended, **observed**:

- [ ] Base logic runs a full race without crashing; scoring rules enforced correctly
- [ ] FastMCP peers communicate over a **public URL**, not localhost
- [ ] Commit-reveal active; end-of-match audit completes with no forgery detected
- [ ] Scent map and belief map are computed and demonstrably influence decisions
- [ ] Live GUI and Replay App both run; Replay shows a valid `Verified OK` stamp
- [ ] Both teams send JSON reports via Gmail API after each match
- [ ] Two GitHub repos, cross-linked, accessible to the lecturer, tagged `v1.0-submission`
- [ ] Academic README complete in both repos, including belief-heatmap and `Verified OK` screenshots
- [ ] At least **2** counted matches against different teams (target: 6–8)
- [ ] Coverage ≥ 85 %, ruff clean, no file over 150 LOC, no secrets in either repo
- [ ] Moodle PDF submitted individually by each team member, with a self-grade for **code quality only**

---

## 8. Milestones

| Milestone | Date | Binary exit criterion |
|---|---|---|
| M0 — Specification approved | 30 Jul | PRD, PLAN, TODO reviewed and signed off |
| M1 — Base logic | 1 Aug | Two agents move legally; 15th barrier rejected; capture fires on overlap |
| M2 — MCP infrastructure | 2 Aug | Message from peer A decodes correctly at peer B |
| M3 — Blind strategy | 3 Aug | Agent computes and walks the shortest path to a known target unaided |
| M4 — Language + scent | 5 Aug | Free text drives inference; scent decays each step; LLM emits truth or lie |
| M5 — Cloud exposure | 6 Aug | Remote machine plays a full series against the local agent |
| M6 — Security | 7 Aug | Move committed then revealed with a valid nonce; Step-0 verifies hardware |
| M7 — Reporting shell | 8 Aug | Summary reaches the lecturer's inbox; GUI live; Replay reproduces a recorded series |
| M8 — League | 9–11 Aug | ≥ 4 counted matches completed and reported |
| M9 — Submission | 12 Aug | Tagged, documented, submitted by midday |

---

## 9. Open questions

| # | Question | Owner | Needed by |
|---|---|---|---|
| Q1 | Team member Moodle IDs for the declaration JSON | Diana | M6 |
| Q2 | Partner's GitHub handle for repo collaboration | Diana | M0 |
| Q3 | Which Ollama model on the partner's machine (size vs. latency under the 30 s step deadline) | Partner | M4 |
| Q4 | Which 6–8 opponent teams, and on what dates | Both | **Start now** |
| ~~Q5~~ | ~~ngrok reserved domain or dynamic URLs?~~ **Answered:** static. Every free ngrok account now gets a permanent `*.ngrok-free.dev` dev domain — no paid plan, no per-match URL exchange. See `SETUP.md` 0.2.5. | — | done |
