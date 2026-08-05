# Traceability Matrix

Generated from `PRD.md`. Every functional requirement maps to the PRD that specifies it, the TODO
tasks that implement it, and the rule or parameter that mandates it.

`M#n` = mandatory rule (Appendix E) · `F` = binding value (Appendix F) · `X` = excellence guide

| FR | Requirement | Specified in | TODO tasks | Mandated by |
|---|---|---|---|---|
| FR-1.1 | Square grid of side `[board size]` (default 7×7), origin and index base loa... | `PRD_1_base_logic.md` | 1.1.1 - 1.5.5 | F |
| FR-1.2 | Move set is exactly 4 orthogonal directions plus STAY. Diagonal moves must ... | `PRD_1_base_logic.md` | 1.1.1 - 1.5.5 | M#13, M#14, F |
| FR-1.3 | On a turn where the Cop forgoes movement it may place one barrier on its ow... | `PRD_1_base_logic.md` | 1.1.1 - 1.5.5 | Ch. 3 |
| FR-1.4 | Barriers are permanent and impassable to both players. Quota `[barrier quot... | `PRD_1_base_logic.md` | 1.1.1 - 1.5.5 | F |
| FR-1.5 | A barrier placed on the Thief's current cell counts as a capture (Cop wins) | `PRD_1_base_logic.md` | 1.1.1 - 1.5.5 | M#46 |
| FR-1.6 | A Thief with no legal move at all counts as captured | `PRD_1_base_logic.md` | 1.1.1 - 1.5.5 | M#47 |
| FR-1.7 | Every barrier placement is truthfully declared with its exact cell. Hidden ... | `PRD_1_base_logic.md` | 1.1.1 - 1.5.5 | M#15, M#16 |
| FR-1.8 | Capture when the Cop lands on the Thief's cell and issues a Capture Claim | `PRD_1_base_logic.md` | 1.1.1 - 1.5.5 | Ch. 3 |
| FR-1.9 | Thief wins by surviving `[survival threshold]` (default 35) valid steps | `PRD_1_base_logic.md` | 1.1.1 - 1.5.5 | F |
| FR-1.10 | Scoring: capture 20/5, survival 5/10, tie 2/2, technical loss 0/0 | `PRD_1_base_logic.md` | 1.1.1 - 1.5.5 | M#48, F |
| FR-1.11 | Both peers compute the identical transition function from the identical sha... | `PRD_1_base_logic.md` | 1.1.1 - 1.5.5 | Ch. 3 |
| FR-2.1 | Cop and Thief run as two **completely separate processes** | `PRD_2_mcp_infra.md` | 2.1.1 - 2.4.2 | M#1 |
| FR-2.2 | No shared memory, no shared live-state module, no shared variables between ... | `PRD_2_mcp_infra.md` | 2.1.1 - 2.4.2 | M#2 |
| FR-2.3 | Each peer runs its own FastMCP server exposing tools via `@mcp.tool`, and i... | `PRD_2_mcp_infra.md` | 2.1.1 - 2.4.2 | Ch. 2 |
| FR-2.4 | Separate config directories per role (`config/police/` vs `config/thief/`) | `PRD_2_mcp_infra.md` | 2.1.1 - 2.4.2 | Ch. 2.4.2 |
| FR-2.5 | The Orchestrator is the single entry point to all subsystems; peripheral mo... | `PRD_2_mcp_infra.md` | 2.1.1 - 2.4.2 | M#3 |
| FR-2.6 | Localhost is permitted for early development only | `PRD_2_mcp_infra.md` | 2.1.1 - 2.4.2 | M#10 |
| FR-3.1 | A decision module separate from the transport layer, wired into `PeerRuntim... | `PRD_3_strategy_baseline.md` | 3.1.1 - 3.4.1 | Ch. 6 |
| FR-3.2 | Baseline policy: shortest legal path to a known target, computed with no ma... | `PRD_3_strategy_baseline.md` | 3.1.1 - 3.4.1 | Ch. 10 milestone 3 |
| FR-3.3 | Brains are pluggable: `police_class` / `thief_class` in the private config ... | `PRD_3_strategy_baseline.md` | 3.1.1 - 3.4.1 | Appendix F §5 |
| FR-3.4 | Movement decisions are always algorithmic Python. The LLM never decides a move | `PRD_3_strategy_baseline.md` | 3.1.1 - 3.4.1 | M#25, Ch. 6 |
| FR-4.1 | Pheromone emission field of size `[scent field size]` (5×5) around the agen... | `PRD_4_scent_and_belief.md` | 4.1.1 - 4.6.4 | F |
| FR-4.2 | Decay at end of each full turn: `τ(t+1) = max(0, (1−ρ)·τ(t) + Δτ)` with ρ =... | `PRD_4_scent_and_belief.md` | 4.1.1 - 4.6.4 | F, Ch. 4 |
| FR-4.3 | Emission and decay are symmetric: both agents emit, each reads only the opp... | `PRD_4_scent_and_belief.md` | 4.1.1 - 4.6.4 | Ch. 4 |
| FR-4.4 | The emission/decay model, plus a concrete numeric example, is exchanged and... | `PRD_4_scent_and_belief.md` | 4.1.1 - 4.6.4 | M#23 |
| FR-4.5 | Full Bayesian posterior over all cells, updated from scent likelihood and h... | `PRD_4_scent_and_belief.md` | 4.1.1 - 4.6.4 | Ch. 6 |
| FR-4.6 | All inter-agent communication is in free natural language | `PRD_4_scent_and_belief.md` | 4.1.1 - 4.6.4 | M#26 |
| FR-4.7 | Direct numeric position protocols are prohibited; outgoing text is scanned ... | `PRD_4_scent_and_belief.md` | 4.1.1 - 4.6.4 | M#27 |
| FR-4.8 | Each hint is capped at `[hint word limit]` (15) words, enforced for every p... | `PRD_4_scent_and_belief.md` | 4.1.1 - 4.6.4 | F |
| FR-4.9 | An `Intent` flag (`truth` / `lie`) is committed alongside the move | `PRD_4_scent_and_belief.md` | 4.1.1 - 4.6.4 | Ch. 5 |
| FR-4.10 | Optional real-world landmark flavour driven by `[map area]` | `PRD_4_scent_and_belief.md` | 4.1.1 - 4.6.4 | F |
| FR-5.1 | The local FastMCP server is exposed to the public internet via a tunnel (ng... | `PRD_5_tunnelling.md` | 5.1.1 - 5.3.2 | M#10 |
| FR-5.2 | Tunnel health is a Watchdog input; a dropped tunnel triggers reconnect and ... | `PRD_5_tunnelling.md` | 5.1.1 - 5.3.2 | Ch. 2, Ch. 8 |
| FR-6.1 | Four-phase protocol per step: `Commit` → `Acknowledge` → `Reveal` → `Final ... | `PRD_6_commit_reveal.md` | 6.1.1 - 6.5.4 | Ch. 5 |
| FR-6.2 | `H = SHA256(State ‖ Move ‖ Intent ‖ Nonce)` over **canonical JSON** (sorted... | `PRD_6_commit_reveal.md` | 6.1.1 - 6.5.4 | M#17, Ch. 5 |
| FR-6.3 | Nonce generated with `secrets.token_hex(16)`, kept absolutely secret until ... | `PRD_6_commit_reveal.md` | 6.1.1 - 6.5.4 | M#18 |
| FR-6.4 | Verification uses `secrets.compare_digest` | `PRD_6_commit_reveal.md` | 6.1.1 - 6.5.4 | Ch. 5 |
| FR-6.5 | Any hash mismatch at audit voids the match technically | `PRD_6_commit_reveal.md` | 6.1.1 - 6.5.4 | M#19 |
| FR-6.6 | Capture claims must be answered truthfully; false capture claims are prohib... | `PRD_6_commit_reveal.md` | 6.1.1 - 6.5.4 | M#21, M#22 |
| FR-6.7 | Step-0 declaration before the first move: OS, CPU cores/frequency, RAM, GPU... | `PRD_6_commit_reveal.md` | 6.1.1 - 6.5.4 | M#24, M#53 |
| FR-6.8 | LLM token consumption is metered, locked at Step-0, and reported | `PRD_6_commit_reveal.md` | 6.1.1 - 6.5.4 | M#54 |
| FR-7.1 | Live GUI displays **local truth only**: own position, own sensed scent, own... | `PRD_7_reporting.md` | 7.1.1 - 7.5.4 | M#8 |
| FR-7.2 | The full objective board state must **never** be displayed in the live GUI | `PRD_7_reporting.md` | 7.1.1 - 7.5.4 | M#9 |
| FR-7.3 | Replay Viewer: load a saved log, step forwards/backwards, re-hash each entr... | `PRD_7_reporting.md` | 7.1.1 - 7.5.4 | M#20 |
| FR-7.4 | One `TAMPERED` verdict voids the match immediately | `PRD_7_reporting.md` | 7.1.1 - 7.5.4 | Ch. 7 |
| FR-7.5 | Automated end-of-match reporting via Gmail API | `PRD_7_reporting.md` | 7.1.1 - 7.5.4 | M#32 |
| FR-7.6 | The report is a structured JSON **attachment**. Free-text reports are prohi... | `PRD_7_reporting.md` | 7.1.1 - 7.5.4 | M#33, M#34 |
| FR-7.7 | Both teams agree the result and **each sends its own report separately** | `PRD_7_reporting.md` | 7.1.1 - 7.5.4 | M#35 |
| FR-7.8 | Reports go to `rmisegal+uoh26finalgame@gmail.com` | `PRD_7_reporting.md` | 7.1.1 - 7.5.4 | M#51 |
| FR-7.9 | Gmail access uses OAuth 2.0 with **send-only** scope | `PRD_7_reporting.md` | 7.1.1 - 7.5.4 | M#30 |
| FR-7.10 | Four JSON artefacts per match: declaration, config, log, result — named fro... | `PRD_7_reporting.md` | 7.1.1 - 7.5.4 | Ch. 9 |
| FR-7.11 | Mutual log audit completed before agreeing the shared result JSON | `PRD_7_reporting.md` | 7.1.1 - 7.5.4 | M#36 |
| FR-8.1 | Strict game-phase state machine; illegal transitions raise immediately | `PRD_state_machine.md` | 6.4.1 - 6.4.4 | M#4, M#5 |
| FR-8.2 | Deadline Tracker: every MCP request carries an expiry; expiry is a failure,... | `PRD_state_machine.md` | 6.4.1 - 6.4.4 | M#6 |
| FR-8.3 | Watchdog: background heartbeat monitor performing controlled shutdown with ... | `PRD_state_machine.md` | 6.4.1 - 6.4.4 | M#7 |
| FR-8.4 | Gatekeeper with three cumulative gates: quota manager → token bucket → DOS ... | `PRD_state_machine.md` | 6.4.1 - 6.4.4 | M#28, M#29 |
| FR-8.5 | Honest declaration of counted games played, at the start of every match | `PRD_state_machine.md` | 6.4.1 - 6.4.4 | M#37, M#38 |
| FR-8.6 | One counted match per opponent. Warm-up matches are uncounted and allowed | `PRD_state_machine.md` | 6.4.1 - 6.4.4 | M#52 |
| FR-8.7 | The shared config is byte-identical on both sides and cryptographically locked | `PRD_state_machine.md` | 6.4.1 - 6.4.4 | M#11 |
| FR-8.8 | Appendix F minimums may be raised by agreement, never lowered | `PRD_state_machine.md` | 6.4.1 - 6.4.4 | M#12 |
---

## Cross-cutting PRDs

| PRD | Covers | TODO tasks |
|---|---|---|
| `PRD_negotiation.md` | Pre-match handshake, config locking, honest game-count declaration | 9.1.1 - 9.1.5 |
| `PRD_state_machine.md` | Phase transitions, deadline tracking, watchdog | 6.4.1 - 6.4.4 |
| `PRD_strategy_advanced.md` | Expectimax, barrier-trap planning, scent-aware evasion, unexploitable defaults, opponent profiling, bluff policy | 8.1.1 - 8.3.7 |

## Administrative rules — deliberately not in a layer PRD

Ten mandatory rules govern submission and league conduct rather than any build layer, so they have
no home in a layer PRD. They are tracked in `TODO.md` Phase 11 and `LEAGUE_LOG.md`.

| Rule | Requirement | Tracked in |
|---|---|---|
| M#31 | Minimum 2 counted matches vs. different teams | `LEAGUE_LOG.md`, TODO 9.2.3 |
| M#40 | Credentials listed in `.gitignore` | TODO 0.1.4 (done) |
| M#41 | Annotated Git tag `v1.0-submission` | TODO 11.1.3 |
| M#42 | Academic README in both repositories | TODO 10.4.x |
| M#43 | Moodle Word template filled, saved as PDF, fields unmoved | TODO 11.2.1 |
| M#44 | Each member submits individually on Moodle | TODO 11.2.4, 11.2.5 |
| M#45 | 8-character team ID (`bestteam`) | `PRD.md` header |
| M#50 | Each repo contains README, `config/`, PRDs, PLAN, TODO | TODO 11.1.2 |
| M#52 | One counted match per opponent; warm-ups uncounted | `LEAGUE_LOG.md`, TODO 9.2.x |
| M#55 | Self-grade for code quality only, never league result | TODO 11.2.3 |

All 55 mandatory rules are cited in `TODO.md`; this table explains why these ten appear there
rather than in a PRD.

## Documents that are not PRDs

| Document | Purpose |
|---|---|
| `PRD.md` | Product requirements: goals, KPIs, binding parameters, acceptance criteria |
| `PLAN.md` | Architecture, C4 diagrams, state machine, data schemas, ADR-001..007 |
| `TODO.md` | Task breakdown by phase, with owner and definition of done |
| `SETUP.md` | External account setup, verified against the live consoles |
| `CONTRADICTIONS.md` | Rulebook contradictions found, choices made, and the reasoning |
| `PROMPT_LOG.md` | The prompts used to build the system - assessed material |
| `LEAGUE_LOG.md` | Match record, scheduling pipeline, per-match checklist |
