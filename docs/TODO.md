# Task List (TODO)
## Distributed Cops-and-Robbers over a Peer-to-Peer Network

**Version:** 1.00 | **Team:** `bestteam` | **Deadline:** 12/08/2026 23:59

**Owners:** `[D]` Diana · `[I]` Itay · `[B]` both · 🧑 action outside the codebase
**Priority:** P0 blocks the grade · P1 blocks a layer · P2 quality/points · P3 optional
**References:** `M#n` = mandatory rule, Appendix E · `F` = value, Appendix F · `X` = excellence guide

---

### ⚠️ Standing rule — 150 lines, checked on every file

Every time a `.py` file is created **or modified**, run the size check before committing.
A file over 150 LOC (blanks and comments excluded) is **split, never compressed**.

Split strategies: extract helper functions · extract a mixin · 50/50 logical halves ·
extract constants to `constants.py` · extract models to their own module.

```
uv run python scripts/ship.py -m "..."       # gates + commit + publish, fail-fast
uv run python scripts/check_file_size.py     # the size gate on its own
uv run pytest tests/test_file_size.py        # same check, inside the suite
```

This is a Quality Gate item in **every** phase. Not optional, not deferred — a 400-line module
discovered on 11 Aug is a day you do not have.

---

## Phase 0: Specification & Accounts
**Priority:** P0 | **Status:** In Progress ◐ | **Target:** 28–30 Jul
**DoD:** PRD/PLAN/TODO approved; both repos live with collaborators; every external account
working; ≥4 league matches booked; 10 per-algorithm PRDs written; CI green.

### 0.1 Repository & Skeleton
- [x] 0.1.1 [D] - Create `bestteam-cop` and `bestteam-thief` on GitHub | DoD: Both repos exist and are reachable.
- [x] 0.1.2 [D] - Create the working tree: `core/` (domain, crypto, protocol, runtime, infra, shared, sdk, ui), `police/`, `thief/`, `config/police/`, `config/thief/`, `docs/`, `tests/`, `scripts/`, `notebooks/`, `results/`, `assets/` | DoD: Every package has `__init__.py`; all importable.
- [x] 0.1.3 [D] - Create `pyproject.toml` as the single dependency source of truth | DoD: `uv sync` completes; `uv run ruff check .` returns 0 violations.
  - [x] 0.1.3.a [D] - Project metadata, version `1.00`, `requires-python >=3.10` | DoD: `uv sync` resolves.
  - [x] 0.1.3.b [D] - Ruff config: line-length 100, `select = ["E","F","W","I","N","UP","B","C4","SIM"]` | DoD: `ruff check` runs clean on the empty tree. (X §7.1)
  - [x] 0.1.3.c [D] - Coverage config with `fail_under = 85` | DoD: Suite fails below threshold, not just warns. (X §6.2)
- [x] 0.1.4 [D] - Create `.gitignore` excluding `.env`, `credentials.json`, `token.json`, `*.pem`, `*.key`, `client_secret*.json` | DoD: `git status` shows no secrets before the first commit. (M#39, M#40)
- [x] 0.1.5 [D] - Create `.env-example` with placeholders for `GMAIL_CREDENTIALS_PATH`, `GMAIL_TOKEN_PATH`, `GROQ_API_KEY`, `OLLAMA_BASE_URL`, `NGROK_AUTHTOKEN` | DoD: Committed; real `.env` absent from the repo. (X §7.4)
- [X] 0.1.6 [D] - Add Itay as collaborator on both repos | DoD: Itay can push to both.
- [X] 0.1.11 🧑 [D] - Grant the `workflow` token scope so `.github/workflows/` can be pushed | DoD: `gh auth refresh -h github.com -s workflow` (or an SSH remote, or a PAT with `workflow`); `publish.py` completes without a rejected push.
- [x] 0.1.13 [D] - Add `scripts/ship.py` — one command for gates + commit + publish | DoD: **Verified** — a lint error halts at step 2/6 and a failing test at step 5/6, both with nothing committed or pushed; the happy path lands on both remotes. Staging runs *before* the secret scan so brand-new files are covered. Output streams live.
- [x] 0.1.14 [D] - Add `core/shared/env.py` — the single place `.env` is loaded | DoD: `require()` raises an actionable error naming the SETUP step; `redact()` never prints a full secret; `optional()` returns a default. 13 unit tests. No module reads `os.environ` directly, so behaviour is identical in VS Code, plain PowerShell, on Itay's machine and in CI.
- [x] 0.1.12 [D] - Add `.gitattributes` pinning LF | DoD: Prevents a CRLF/LF mismatch from breaking the byte-identical shared-config handshake between teams on different operating systems. See CONTRADICTIONS C-004. (M#11)
- [x] 0.1.7 [D] - Write `scripts/check_file_size.py` | DoD: Bloating a file to 151 LOC makes it exit 1; removing one line makes it exit 0. **Verified both directions.** Logic lives in `core/shared/loc_counter.py`; the script is a thin CLI.
  - [x] 0.1.7.a [D] - Walk `core/`, `police/`, `thief/`, `tests/`, `scripts/` for `*.py` | DoD: `__pycache__` and `.venv` excluded.
  - [x] 0.1.7.b [D] - Count lines that are neither blank nor pure comment | DoD: A 200-line file of comments passes; 151 lines of code fails.
  - [x] 0.1.7.c [D] - Print offenders sorted descending with line counts; exit 1 if any | DoD: Output names the file and the count.
- [x] 0.1.8 [D] - Write `tests/test_file_size.py` wrapping the same check | DoD: `uv run pytest tests/test_file_size.py` fails when a file is oversized. **Verified.** Counter itself unit-tested in `tests/unit/test_loc_counter.py` (17 tests, 100 % coverage).
- [x] 0.1.9 [D] - Add `.pre-commit-config.yaml` with ruff, file-size and secret-scan hooks | DoD: A commit containing a 160-line file is refused locally. One-time setup: `uv run pre-commit install`. Secret scan is `scripts/scan_secrets.py` (pure Python, works on Windows; staged + `--tracked` modes), logic in `core/shared/secret_scanner.py`, 9 unit tests.
- [x] 0.1.10 [D] - Create `.github/workflows/ci.yml`: `uv sync` → `ruff check` → `check_file_size.py` → `scan_secrets.sh` → `pytest` | DoD: All four steps pass locally; no bare `pip` or `python -m` calls in the YAML. (X §8.4)

### 0.2 🧑 USER ACTION — External accounts
> **PAUSE — I stop here. These need a browser and your credentials; I cannot do them.**
> **Step-by-step guide: `docs/SETUP.md`. Verify with `uv run python scripts/check_setup.py`.**

- [ ] 0.2.1 🧑 [D] - Google Cloud project + Gmail API + Google Auth platform, **send-only** scope `gmail.send` | DoD: `credentials.json` saved **outside** both repos; `check_setup.py` reports Gmail credentials OK. See SETUP 0.2.1. (M#30)
  - [ ] 0.2.1.a 🧑 [D] - Create the project and enable the Gmail API | DoD: API shows as Enabled in the console.
  - [ ] 0.2.1.b 🧑 [D] - Configure Branding + Audience (**External**), add yourself as a test user, add scope `gmail.send` | DoD: Consent screen saved with exactly one scope. SETUP 0.2.1.b-d
  - [ ] 0.2.1.c 🧑 [D] - Create OAuth client ID (**Desktop app**), download `credentials.json` | DoD: File on disk in `C:\Users\diana\.p2p-secrets\`, path in `.env`, **not** inside either repo. SETUP 0.2.1.e-f
  - [ ] 0.2.1.d 🧑 [D] - ⚠️ **Publish the app** (Testing → In production) | DoD: Audience page reads *In production*. **Skipping this makes the refresh token expire after 7 days and silently breaks league reporting mid-project** — an unsent report scores 0 for **both** teams. SETUP 0.2.1.g (M#35)
- [ ] 0.2.2 🧑 [D] - Groq API key at console.groq.com/keys | DoD: Key starts with `gsk_`; `uv run python -c "import os;from dotenv import load_dotenv;load_dotenv();print(os.getenv('GROQ_API_KEY'))"` prints it, not `None`.
- [ ] 0.2.3 🧑 [I] - Install Ollama and pull a model small enough for the 30 s step deadline | DoD: A 15-word prompt returns in under 10 s at `localhost:11434`. (PRD Q3)
- [ ] 0.2.4 🧑 [B] - ngrok accounts + authtokens on both machines | DoD: `ngrok http 8801` yields a public URL on each machine.
- [x] 0.2.5 [D] - Decide: static ngrok domain or dynamic URLs? | DoD: **Answered — static.** ngrok now assigns every free account a permanent `*.ngrok-free.dev` dev domain, so no paid plan and no per-match URL exchange is needed. Recorded in PRD Q5 and SETUP 0.2.5.
- [ ] 0.2.6 🧑 [B] - Note each machine's static ngrok domain in `config/<role>/game.toml` | DoD: Both domains recorded; `ngrok http 8801 --url <domain>` works on each machine.

### 0.3 🧑 USER ACTION — League scheduling ⏰ **DO THIS FIRST**
> **PAUSE — This is the binding constraint on the final grade, and it is not a coding task.**
> Two matches passes. Diversity reward is 10 points per new opponent. League position spans
> 25 grade points. Every day of delay shrinks the pool of teams still free.

- [ ] 0.3.1 🧑 [B] - Contact 6–8 teams; agree dates and roles | DoD: ≥4 confirmed slots in a shared calendar with team names, contacts and times. (M#31)
- [ ] 0.3.2 🧑 [B] - Book one **warm-up** (uncounted) match for ~8 Aug | DoD: A friendly team confirmed for protocol shakedown. (M#52)
- [x] 0.3.3 [D] - Create `docs/LEAGUE_LOG.md` — one row per opponent: date, role, result, reports sent, commit hash | DoD: Table skeleton committed; filled as matches complete. (M#37)

### 0.4 Specification documents
- [x] 0.4.1 [D] - `docs/PRD.md` | DoD: All 55 mandatory rules and 31 Appendix F values traced.
- [x] 0.4.2 [D] - `docs/PLAN.md` | DoD: C4 diagrams, state machine, data schemas, ADR-001..007.
- [x] 0.4.3 [D] - `docs/TODO.md` | DoD: This file.
- [x] 0.4.4 [D] - Seven layer PRDs | DoD: All seven exist with requirements, I/O, constraints, alternatives, test scenarios. (X §2.3)
  - [x] 0.4.4.a [D] - `PRD_1_base_logic.md` | DoD: Board, movement, barriers, capture, scoring specified.
  - [x] 0.4.4.b [D] - `PRD_2_mcp_infra.md` | DoD: Tool contracts and process separation specified.
  - [x] 0.4.4.c [D] - `PRD_3_strategy_baseline.md` | DoD: `BrainBase` interface and baseline policy specified.
  - [x] 0.4.4.d [D] - `PRD_4_scent_and_belief.md` | DoD: Emission/decay maths and Bayesian update specified.
  - [x] 0.4.4.e [I] - `PRD_5_tunnelling.md` | DoD: Exposure, NAT traversal, reconnection specified.
  - [x] 0.4.4.f [D] - `PRD_6_commit_reveal.md` | DoD: Canonical JSON, nonce, four phases, audit, Step-0 specified.
  - [x] 0.4.4.g [D] - `PRD_7_reporting.md` | DoD: Gatekeeper, Gmail, four JSON artefacts, GUI, Replay specified.
- [x] 0.4.5 [D] - Three algorithm PRDs | DoD: All three exist. Plus `TRACEABILITY.md` mapping all 60 FRs to a PRD and TODO tasks — verified programmatically, 0 untraced.
  - [x] 0.4.5.a [D] - `PRD_strategy_advanced.md` | DoD: Expectimax, barrier-trap planning, scent-aware evasion specified.
  - [x] 0.4.5.b [D] - `PRD_negotiation.md` | DoD: Handshake, config locking, game-count declaration specified.
  - [x] 0.4.5.c [D] - `PRD_state_machine.md` | DoD: Transition table, deadlines, watchdog specified.
- [x] 0.4.6 [D] - Open `docs/PROMPT_LOG.md` and keep it running from today | DoD: Six entries logged with goal, prompt, result, problem, iteration and transferable lesson, plus five extracted rules. Assessed material. (X §8.3)
- [x] 0.4.7 [D] - Open `docs/CONTRADICTIONS.md` | DoD: Three entries logged — C-001 `num_games` 1-vs-6, C-002 docstrings vs. the 150-line rule, C-003 board size 7×7 vs. the 10×10 figure. Template included for future entries.

### 0.5 Reference material
- [ ] 0.5.1 [B] - Clone and run `rmisegal/Game-P2P-Cop-Chase` in two PowerShell terminals | DoD: A full match observed end-to-end; notes in `docs/REFERENCE_NOTES.md`.
- [ ] 0.5.2 [D] - Build a Graphify knowledge graph of the reference repo | DoD: Graph screenshot in `assets/`; three architectural findings written up for the README. *(P2)*
- [ ] 0.5.3 [D] - Read the reference repo's `RESEARCH-REPORT-Performance-Analysis.md` | DoD: Provider rate limits and fallback design understood; informs task 4.5.

### ✅ Phase 0 Quality Gate
- [ ] 0.QG.1 [D] - `uv run ruff check .` | DoD: `All checks passed.`
- [ ] 0.QG.2 [D] - `uv run python scripts/check_file_size.py` | DoD: No file over 150 LOC.
- [ ] 0.QG.3 [D] - Secret scan on both repos | DoD: Zero matches for `gsk_`, `sk-ant`, `BEGIN PRIVATE KEY` in tracked files **or history**. (M#39)
- [ ] 0.QG.4 [B] - PRD, PLAN and the 10 sub-PRDs reviewed and approved | DoD: Both members signed off; no code written before this passes. (X §2.5)

---

## Phase 1: Base Logic (Layer 1)
**Priority:** P0 | **Status:** Not Started ☐ | **Target:** 31 Jul – 1 Aug
**DoD:** Two agents move legally on a 7×7 grid; a 15th barrier is rejected; all three capture
conditions fire correctly; scoring matches Appendix F; coverage ≥85 % on `core/domain`.

### 1.1 Configuration foundation
- [ ] 1.1.1 [D] - `core/shared/version.py` with `VERSION = "1.00"` | DoD: Matches `pyproject.toml` and every config `version` key; asserted by a unit test. (X §8.1)
- [ ] 1.1.2 [D] - `core/shared/constants.py` — immutable non-negotiable constants only | DoD: No value that belongs in config lives here. (X §7.2)
- [ ] 1.1.3 [D] - `config/<role>/game.json` with all 31 Appendix F defaults | DoD: Every key from PRD §5 present; the two role copies are byte-identical. (M#11, F)
- [ ] 1.1.4 [D] - `config/<role>/game.toml` private skeleton with explanatory comments | DoD: `[game]`, `[network]`, `[strategy]`, `[trash_talk]`, `[llm]`, `[email]` present. **Move the recorded ngrok domains from SETUP 0.2.5 into `[network]`** — Diana's is `customs-countdown-uncork.ngrok-free.dev`. (Appendix B)
- [ ] 1.1.5 [D] - `config/<role>/rate_limits.json` | DoD: `requests_per_minute`, `concurrent_requests`, `retry_backoff_sec`, `max_retries`, `queue_depth` present; versioned. (F, X §5.2)
- [ ] 1.1.6 [D] - `core/shared/config_manager.py` — load, merge, validate | DoD: File ≤150 lines; split into loader + validator if needed.
  - [ ] 1.1.6.a [D] - Load private TOML then shared JSON | DoD: Missing JSON falls back to TOML defaults cleanly.
  - [ ] 1.1.6.b [D] - JSON **overlays** TOML for every shared key | DoD: Unit test proves a private file cannot weaken a signed value. (Appendix B)
  - [ ] 1.1.6.c [D] - Version compatibility check at startup | DoD: Mismatch raises `ConfigVersionError` with a readable message.
  - [ ] 1.1.6.d [D] - Minimum-direction validator | DoD: A config lowering `max_barriers` below 14 raises; raising it to 20 passes. (M#12)
  - [ ] 1.1.6.e [D] - `config_sha256()` over canonical JSON | DoD: Both peers compute the same digest for the same file.

### 1.2 Board & movement
- [ ] 1.2.1 [D] - `core/domain/board.py` — dimensions, bounds, passability | DoD: 7×7 read from config; no hardcoded size; out-of-bounds and barrier cells both report impassable.
- [ ] 1.2.2 [D] - `core/domain/actions.py` — **4 orthogonal directions + STAY only** | DoD: No diagonal exists anywhere in the enum or the delta table. (M#14, F)
- [ ] 1.2.3 [D] - `core/domain/movement.py` — legal move resolution | DoD: Diagonal input raises; out-of-bounds raises; barrier cell raises; STAY is legal. (M#13)
- [ ] 1.2.4 [D] - `get_legal_moves(pos, barriers, board)` | DoD: Returns exactly the passable neighbours plus STAY; empty-except-STAY case handled.

### 1.3 Barriers
- [ ] 1.3.1 [D] - `core/domain/barriers.py` — `BarrierManager` | DoD: File ≤150 lines. (M#15, M#46, F)
  - [ ] 1.3.1.a [D] - `__init__` reads quota from config; rejects negative | DoD: Quota 14 default; `-1` raises `ValueError`.
  - [ ] 1.3.1.b [D] - `can_place(target, cop_pos, is_forgoing_move)` | DoD: Legal only on the Cop's own cell or one of the 4 orthogonal neighbours, and only when forgoing movement. Diagonal-adjacent rejected.
  - [ ] 1.3.1.c [D] - `place()` enforces the quota | DoD: 15th placement rejected with quota 14.
  - [ ] 1.3.1.d [D] - Permanence — no removal API exists | DoD: A blocked cell stays blocked for the rest of the sub-game.
  - [ ] 1.3.1.e [D] - Placement on the Thief's current cell returns `CAPTURE` | DoD: Unit-tested. (M#46)
- [ ] 1.3.2 [D] - Truthful barrier declaration in the move record | DoD: Every placement carries its exact cell into the signed record; no hidden placement path exists. (M#15, M#16)

### 1.4 Game state, capture & scoring
- [ ] 1.4.1 [D] - `core/domain/game_state.py` — frozen dataclass | DoD: Positions, barriers, step count, barriers placed; immutable.
- [ ] 1.4.2 [D] - `core/domain/rules.py` — terminal condition detection | DoD: All four paths unit-tested.
  - [ ] 1.4.2.a [D] - Cop lands on the Thief's cell + Capture Claim → Cop wins | DoD: Tested. (Ch. 3)
  - [ ] 1.4.2.b [D] - Barrier placed on the Thief's cell → Cop wins | DoD: Tested. (M#46)
  - [ ] 1.4.2.c [D] - Thief with **no** legal move at all → captured | DoD: Tested with a fully enclosed thief. (M#47)
  - [ ] 1.4.2.d [D] - Thief survives `survival_threshold` valid steps → Thief wins | DoD: Tested at exactly 35 and at 34. (F)
- [ ] 1.4.3 [D] - `core/domain/scoring.py` — capture 20/5, survival 5/10, tie 2/2, technical loss 0/0 | DoD: All values read from config, zero numeric literals. (M#48, F)
- [ ] 1.4.4 [D] - Series aggregation across 6 sub-games, with tie detection | DoD: Equal cumulative totals award `tie_score` to both sides. (F)

### 1.5 Tests
- [ ] 1.5.1 [D] - `tests/conftest.py` shared fixtures: `minimal_config`, `board_7x7`, `game_state_factory`, `barrier_manager`, `mock_llm_provider`, `mock_mcp_peer` | DoD: Each fixture used by ≥1 test.
- [ ] 1.5.2 [D] - Unit tests for board, movement, actions | DoD: Happy path and error path per public function. (X §6.1)
- [ ] 1.5.3 [D] - Unit tests for barriers, including all five sub-cases of 1.3.1 | DoD: Every branch covered.
- [ ] 1.5.4 [D] - Unit tests for rules and scoring | DoD: All four terminal conditions covered.
- [ ] 1.5.5 [D] - Unit tests for the config manager, incl. the overlay and minimum-direction rules | DoD: `ConfigVersionError` and minimum-violation both asserted.

### ✅ Phase 1 Quality Gate
- [ ] 1.QG.1 [D] - `uv run ruff check .` | DoD: 0 violations.
- [ ] 1.QG.2 [D] - `uv run python scripts/check_file_size.py` | DoD: No file over 150 LOC. Split anything that grew.
- [ ] 1.QG.3 [D] - `uv run pytest --cov` | DoD: All pass; coverage ≥85 % on `core/domain` and `core/shared`.
- [ ] 1.QG.4 [D] - **Milestone M1 observed** | DoD: Two agents move legally on a 7×7 grid; a 15th barrier is rejected; coordinate overlap triggers capture. Behaviour *seen*, not merely coded.

---

## Phase 2: FastMCP Infrastructure (Layer 2)
**Priority:** P0 | **Status:** Not Started ☐ | **Target:** 2 Aug
**DoD:** Two fully separate processes exchange a geometric message over localhost and decode it
correctly; the Orchestrator is the only inter-module path; no import path joins the live roles.

### 2.1 Protocol contracts
- [ ] 2.1.1 [D] - `core/protocol/schemas.py` — message dataclasses | DoD: Commit, Ack, Reveal, FinalReveal, CaptureClaim, BarrierDeclaration, Negotiation all defined.
- [ ] 2.1.2 [D] - `core/protocol/tools.py` — one factory per MCP tool | DoD: Factory pattern; a new tool needs one factory + one registration line.
  - [ ] 2.1.2.a [D] - `receive_commit(hash, step)` | DoD: Stores the hash, returns an acknowledgement.
  - [ ] 2.1.2.b [D] - `acknowledge(step)` | DoD: Confirms the opponent is locked.
  - [ ] 2.1.2.c [D] - `receive_reveal(move, hint, intent, step)` | DoD: Nonce **not** accepted at this stage. (M#18)
  - [ ] 2.1.2.d [D] - `final_reveal(nonces)` | DoD: Accepted only at end of match.
  - [ ] 2.1.2.e [D] - `capture_claim()` / `capture_response()` | DoD: Truthful answer required. (M#21)
  - [ ] 2.1.2.f [D] - `declare_barrier(cell)` | DoD: Exact cell declared. (M#15)
  - [ ] 2.1.2.g [D] - `negotiate(config_hash, game_count, scent_model_hash)` | DoD: Handshake payload complete. (M#37)

### 2.2 Transport
- [ ] 2.2.1 [D] - `core/infra/mcp_server.py` — FastMCP server per peer | DoD: Tools registered via `@mcp.tool`; binds `0.0.0.0` so a tunnel can reach it. (Ch. 2)
- [ ] 2.2.2 [D] - `core/infra/mcp_client.py` — client addressing exactly **one** opponent URL | DoD: No code path can reach a second peer; a deadline is attached to every call.
- [ ] 2.2.3 [D] - Structured error handling: auth failure, transport failure, timeout | DoD: Each raises a distinct typed exception, never a bare `Exception`.

### 2.3 Runtime skeleton
- [ ] 2.3.1 [D] - `core/runtime/orchestrator.py` — single gateway to all five subsystems | DoD: No peripheral module imports another; verified by an import-graph test. (M#3)
- [ ] 2.3.2 [D] - `core/runtime/peer_runtime.py` — negotiate → turn loop → audit | DoD: Runs exactly one role, chosen by CLI flag.
- [ ] 2.3.3 [D] - `core/sdk/peer_sdk.py` — the single public facade | DoD: `grep -r "from core.domain" core/ui/` returns nothing. (X §4.1)
- [ ] 2.3.4 [D] - CLI entry point: `uv run python -m core peer --role police|thief` | DoD: Two separate OS processes, two separate config dirs. (M#1, M#4)

### 2.4 Separation enforcement
- [ ] 2.4.1 [D] - `tests/integration/test_process_separation.py` | DoD: Asserts no module reachable from `police/` imports anything under `thief/`, and vice versa. (M#2)
- [ ] 2.4.2 [D] - `tests/integration/test_localhost_roundtrip.py` | DoD: Spawns both peers as subprocesses; a message from A decodes correctly at B.

### ✅ Phase 2 Quality Gate
- [ ] 2.QG.1 [D] - `uv run ruff check .` | DoD: 0 violations.
- [ ] 2.QG.2 [D] - `uv run python scripts/check_file_size.py` | DoD: No file over 150 LOC.
- [ ] 2.QG.3 [D] - `uv run pytest --cov` | DoD: All pass; coverage ≥85 %.
- [ ] 2.QG.4 [D] - **Milestone M2 observed** | DoD: A message leaving peer A over localhost is received and decoded correctly at peer B, in two separate terminals.

---

## Phase 3: Baseline Strategy (Layer 3)
**Priority:** P1 | **Status:** Not Started ☐ | **Target:** 3 Aug
**DoD:** Given a known target, the agent computes and walks the shortest legal path unaided.

- [ ] 3.1.1 [D] - `core/domain/brain_base.py` — abstract `BrainBase` | DoD: `_pick_move(observation)` abstract; `_decide_move()` overridable for the Cop's barrier choice. (Appendix F §5)
- [ ] 3.1.2 [D] - Brain loading from `[strategy] police_class` / `thief_class` in `package.module:Class` form | DoD: Empty section falls back to the built-in baseline; a bad path raises at startup, not mid-match.
- [ ] 3.2.1 [D] - `police/brain.py` baseline — BFS shortest path to a known target | DoD: Respects barriers and bounds; deterministic on a fixed board.
- [ ] 3.2.2 [I] - `thief/brain.py` baseline — distance maximisation | DoD: Never voluntarily enters a cell with no exit other than the one it came from.
- [ ] 3.3.1 [D] - Wire the brain into `PeerRuntime` between hint-decode and commit-pack | DoD: Exactly the insertion point Ch. 6 specifies; verified by a call-order test.
- [ ] 3.3.2 [D] - Guard: the LLM is never consulted for a movement decision | DoD: An architecture test asserts no import of `core.infra.llm` from any brain module. (M#25)
- [ ] 3.4.1 [D] - Unit tests for both baselines | DoD: Fixed-board scenarios with asserted move sequences.

### ✅ Phase 3 Quality Gate
- [ ] 3.QG.1 [D] - `uv run ruff check .` | DoD: 0 violations.
- [ ] 3.QG.2 [D] - `uv run python scripts/check_file_size.py` | DoD: No file over 150 LOC.
- [ ] 3.QG.3 [D] - `uv run pytest --cov` | DoD: All pass; coverage ≥85 %.
- [ ] 3.QG.4 [D] - **Milestone M3 observed** | DoD: Agent computes and walks the shortest path to a known target with no manual intervention.

---

## Phase 4: Language & Scent (Layer 4) ⚠️ **HIGHEST RISK**
**Priority:** P0 | **Status:** Not Started ☐ | **Target:** 4–5 Aug
**DoD:** Free-text hints drive inference; the scent map updates and decays each step; the belief
posterior shifts measurably; the verbal layer emits a truthful or deceptive hint at ≤15 words.
Most of the schedule slack is allocated here — if anything slips, it slips here.

### 4.1 Scent engine
- [ ] 4.1.1 [D] - `core/domain/scent.py` — 5×5 radial emission field, centre τ=0.9 | DoD: Reproduces the rulebook's figure values (0.9 / 0.62 / 0.42 / 0.20 / 0.14 / 0.04). (F)
- [ ] 4.1.2 [D] - Decay `τ(t+1) = max(0, (1−ρ)·τ(t) + Δτ)`, ρ=0.10, applied at end of each **full** turn | DoD: A single deposit crosses half-peak around turn 7, as the book states. (F, Ch. 4)
- [ ] 4.1.3 [D] - Symmetry: both agents emit; each reads only the opponent's field | DoD: A test asserts an agent cannot sample its own trail. (Ch. 4)
- [ ] 4.1.4 [D] - Truncation at zero | DoD: Intensity never goes negative.
- [ ] 4.1.5 [D] - Scent-model exchange payload: formula + a concrete numeric example, hashed | DoD: Both peers agree the digest before the series opens. (M#23)

### 4.2 Belief engine
- [ ] 4.2.1 [D] - `core/domain/belief.py` — full 7×7 posterior | DoD: Sums to 1.0 within float tolerance after every update.
  - [ ] 4.2.1.a [D] - Uniform initialisation | DoD: Each cell 1/49 at step 0.
  - [ ] 4.2.1.b [D] - Prediction step: motion model, one orthogonal step or stay | DoD: Mass spreads only to legal neighbours.
  - [ ] 4.2.1.c [D] - Update from scent likelihood | DoD: Unit-tested against a worked example from Ch. 4.
  - [ ] 4.2.1.d [D] - Update from hint likelihood, scaled by the reliability coefficient | DoD: A hint contradicted by the scent field moves mass *away* from the claim.
  - [ ] 4.2.1.e [D] - Mask barriers and own cell, then renormalise | DoD: Blocked cells hold exactly 0.
- [ ] 4.2.2 [I] - Per-opponent **reliability coefficient** tracked across the series | DoD: Converges toward 0 against a consistently lying opponent, toward 1 against a truthful one. *(Original extension — README material.)*
- [ ] 4.2.3 [D] - `argmax`, entropy and marginal helpers | DoD: Used by the strategy layer and the GUI heatmap.

### 4.3 Natural language — outbound
- [ ] 4.3.1 [I] - `core/infra/llm/base.py` — `TextProvider` interface | DoD: One method, `generate(prompt, max_words) -> str`.
- [ ] 4.3.2 [I] - `template` provider — pre-written bank, zero tokens | DoD: Default; works fully offline. (F)
- [ ] 4.3.3 [I] - `ollama` provider — `localhost:11434` | DoD: Itay's machine produces a hint in under 10 s.
- [ ] 4.3.4 [D] - `groq` provider, routed through the Gatekeeper | DoD: No direct SDK call outside this module; Diana's machine produces a hint.
- [ ] 4.3.5 [I] - Automatic fallback to `template` on **any** provider error or timeout | DoD: Killing Ollama mid-match degrades quality but does not lose the match. (ADR-003)
- [ ] 4.3.6 [I] - `every_n_steps` throttle | DoD: LLM invoked every 2–3 turns; other turns use the template bank.
- [ ] 4.3.7 [D] - Hint word cap of 15, enforced for **every** provider including the LLM system prompt | DoD: An over-long generation is regenerated or truncated at a word boundary. (F)
- [ ] 4.3.8 [D] - Outbound coordinate scanner | DoD: Any text containing bare numeric coordinates is rejected and regenerated. Port HW6's `_COORD_RE`. (M#27)
- [ ] 4.3.9 [D] - Free natural language enforced — no structured position protocol anywhere | DoD: Architecture test asserts no numeric position field on the hint channel. (M#26)
- [ ] 4.3.10 [I] - Optional `map_area` landmark flavour | DoD: With `"New York"` set, hints reference real landmarks; empty string yields generic ones. (F) *(P2)*

### 4.4 Natural language — inbound
- [ ] 4.4.1 [D] - `core/domain/hint_parser.py` — free text → directional intent + confidence | DoD: Port and adapt HW6's parser; low confidence defers to the belief map alone.
- [ ] 4.4.2 [I] - Bluff classification: compare the claim against the observed scent field | DoD: Feeds the reliability coefficient in 4.2.2.
- [ ] 4.4.3 [I] - Behavioural profiling across sub-games | DoD: Opponent's lie rate and hint style recorded in the log. *(P2)*

### 4.5 Intent flag
- [ ] 4.5.1 [D] - `Intent` enum (`truth` / `lie`) chosen by the brain, not the LLM | DoD: Present in the hashed record; the LLM receives it as an instruction, never decides it. (Ch. 5)

### 4.6 Tests
- [ ] 4.6.1 [D] - Scent emission and decay unit tests | DoD: Values match the book's figures to 2 decimal places.
- [ ] 4.6.2 [D] - Belief update unit tests | DoD: Posterior sums to 1; contradicted hints move mass correctly.
- [ ] 4.6.3 [I] - Provider tests with a mocked transport | DoD: No test touches a live API. (X §6.1)
- [ ] 4.6.4 [D] - Word-cap and coordinate-scanner tests | DoD: A 20-word hint and a `(3,4)` hint are both rejected.

### ✅ Phase 4 Quality Gate
- [ ] 4.QG.1 [D] - `uv run ruff check .` | DoD: 0 violations.
- [ ] 4.QG.2 [D] - `uv run python scripts/check_file_size.py` | DoD: No file over 150 LOC. `belief.py` and `scent.py` are the likeliest to breach — split early.
- [ ] 4.QG.3 [D] - `uv run pytest --cov` | DoD: All pass; coverage ≥85 %.
- [ ] 4.QG.4 [B] - **Milestone M4 observed** | DoD: Free-text report drives inference; scent map updates and decays each step; the verbal layer emits a truthful or deceptive hint.

---

## Phase 5: Cloud Exposure (Layer 5)
**Priority:** P0 | **Status:** Not Started ☐ | **Target:** 6 Aug
**DoD:** An agent on a remote machine connects via a public URL and plays a complete series.

- [ ] 5.1.1 [I] - `core/infra/tunnel.py` — ngrok lifecycle | DoD: Public URL obtained programmatically at startup. Public exposure is mandatory for league play. (M#10)
- [ ] 5.1.2 [I] - Localtonet fallback path | DoD: Documented in the README; switchable by config. *(P2)*
- [ ] 5.2.1 [I] - Drop detection + reconnect + re-handshake | DoD: A tunnel killed mid-match recovers or ends in a clean `TECHNICAL_LOSS` — never a hang.
- [ ] 5.2.2 [I] - Tunnel health wired into the Watchdog input | DoD: Dead tunnel triggers a controlled action within `watchdog_timeout_sec`.
- [ ] 5.3.1 [B] - Two-machine rehearsal, Diana ↔ Itay over the public internet | DoD: A full 6-sub-game series completes end-to-end.
- [ ] 5.3.2 [B] - Latency measurement under the 30 s response timeout | DoD: p95 round-trip recorded; timeout raised by agreement if the margin is thin. (F, M#12)

### ✅ Phase 5 Quality Gate
- [ ] 5.QG.1 [I] - `uv run ruff check .` | DoD: 0 violations.
- [ ] 5.QG.2 [I] - `uv run python scripts/check_file_size.py` | DoD: No file over 150 LOC.
- [ ] 5.QG.3 [I] - `uv run pytest --cov` | DoD: All pass; coverage ≥85 %.
- [ ] 5.QG.4 [B] - **Milestone M5 observed** | DoD: Remote machine plays a full series via ngrok against the local agent.

---

## Phase 6: Security & Cryptography (Layer 6)
**Priority:** P0 | **Status:** Not Started ☐ | **Target:** 7 Aug
**DoD:** A move is committed then revealed with a valid nonce; Step-0 verifies hardware and commit
hash; the end-of-match audit passes; any tampering is detected.

### 6.1 Cryptographic core
- [ ] 6.1.1 [D] - `core/crypto/canonical.py` — `json.dumps(sort_keys=True, separators=(",", ":"))` | DoD: Two independent processes produce byte-identical output for the same payload. **Divergence here means both teams score 0.**
- [ ] 6.1.2 [D] - `core/crypto/nonce.py` — `secrets.token_hex(16)` | DoD: An architecture test asserts `random` is never imported for nonce generation. (M#18)
- [ ] 6.1.3 [D] - `core/crypto/commit_reveal.py` | DoD: File ≤150 lines.
  - [ ] 6.1.3.a [D] - `commit(state, move, intent) -> (hash, nonce)` over `SHA256(State‖Move‖Intent‖Nonce)` | DoD: Same inputs with different nonces yield different hashes. (M#17)
  - [ ] 6.1.3.b [D] - `verify(...)` using `secrets.compare_digest` | DoD: A single flipped bit is detected.
  - [ ] 6.1.3.c [D] - Nonce retained locally, never transmitted before the final audit | DoD: A test asserts no reveal payload contains a nonce. (M#18)
- [ ] 6.1.4 [D] - `core/crypto/audit.py` — mutual end-of-match audit | DoD: Re-hashes every step of both logs; any mismatch → technical loss for the forging side. (M#19)

### 6.2 Four-phase protocol
- [ ] 6.2.1 [D] - Phase 1 Commit — send hash only | DoD: No payload content leaves before the ack.
- [ ] 6.2.2 [D] - Phase 2 Acknowledge — opponent confirms lock | DoD: Reveal is impossible before both sides have acked.
- [ ] 6.2.3 [D] - Phase 3 Reveal — move + hint, nonce withheld | DoD: Tested.
- [ ] 6.2.4 [D] - Phase 4 Final Reveal — all nonces at end of match | DoD: Triggered only in the terminal state.
- [ ] 6.2.5 [D] - Truthful capture response is cryptographically bound | DoD: Denying a real capture is detectable at audit. (M#21, M#22)

### 6.3 Step-0 declaration
- [ ] 6.3.1 [I] - `core/shared/system_info.py` — OS, CPU cores/frequency, RAM, GPU/VRAM | DoD: Works on both machines; degrades gracefully with no GPU.
- [ ] 6.3.2 [D] - `core/protocol/step_zero.py` — signed declaration | DoD: Includes hardware, LLM model name, code version, team name, sub-game number **and `github_commit`**. (M#24, M#53)
- [ ] 6.3.3 [D] - Read the current commit hash at runtime | DoD: Matches `git rev-parse HEAD`; a dirty tree raises a warning before a graded match.
- [ ] 6.3.4 [I] - Token meter, locked at Step-0 | DoD: Cumulative LLM tokens reported in the result JSON. (M#54)

### 6.4 Reliability patterns
- [ ] 6.4.1 [D] - `core/runtime/phase_machine.py` — explicit transition table | DoD: `WAITING_FOR_OPPONENT → COMPUTING_MOVE → COMMITTING → AWAITING_REVEAL → VERIFYING`, plus terminal `TECHNICAL_LOSS`. Illegal transition raises. (M#4, M#5)
- [ ] 6.4.2 [D] - `core/runtime/deadline_tracker.py` | DoD: Every MCP request carries an expiry; expiry triggers a controlled retry then technical loss — never continued waiting. (M#6)
- [ ] 6.4.3 [D] - `core/runtime/watchdog.py` — heartbeat monitor | DoD: No heartbeat for `watchdog_timeout_sec` → persist state → controlled shutdown. (M#7)
- [ ] 6.4.4 [D] - State persistence for recovery | DoD: A killed process leaves a loadable snapshot.

### 6.5 Tests
- [ ] 6.5.1 [D] - Commit-reveal round trip and tamper detection | DoD: Every mutation of state/move/intent/nonce is caught.
- [ ] 6.5.2 [D] - Cross-process canonical serialisation test | DoD: Two subprocesses agree on the digest.
- [ ] 6.5.3 [D] - State machine legal/illegal transition matrix | DoD: Every illegal pair asserted to raise.
- [ ] 6.5.4 [D] - Deadline and watchdog tests with a simulated stall | DoD: No test sleeps longer than 2 s (clock injected).

### ✅ Phase 6 Quality Gate
- [ ] 6.QG.1 [D] - `uv run ruff check .` | DoD: 0 violations.
- [ ] 6.QG.2 [D] - `uv run python scripts/check_file_size.py` | DoD: No file over 150 LOC.
- [ ] 6.QG.3 [D] - `uv run pytest --cov` | DoD: All pass; coverage **≥95 %** on `core/crypto` — this module cannot afford a gap.
- [ ] 6.QG.4 [D] - **Milestone M6 observed** | DoD: Move committed then revealed with a valid nonce; Step-0 verifies hardware; audit passes.

---

## Phase 7: Reporting & Visualisation (Layer 7)
**Priority:** P0 | **Status:** Not Started ☐ | **Target:** 8 Aug
**DoD:** A match summary reaches the lecturer's inbox as a JSON attachment; the Live GUI shows local
truth only; the Replay App reproduces a recorded series with `Verified OK`.

### 7.1 Gatekeeper
- [ ] 7.1.1 [D] - Port `rate_limiter.py`, `queue_manager.py`, `call_logger.py` from HW6 | DoD: Adapted to the new config layout; tests ported.
- [ ] 7.1.2 [D] - `core/shared/gatekeeper.py` — three cumulative gates | DoD: Only a request clearing all three reaches the API.
  - [ ] 7.1.2.a [D] - Quota manager — daily ceiling | DoD: Exhausted quota blocks every further send.
  - [ ] 7.1.2.b [D] - Token bucket `tokens ← min(C, tokens + r·Δt)`, allow iff `tokens ≥ 1` | DoD: A burst empties the bucket and subsequent sends are blocked. (M#28)
  - [ ] 7.1.2.c [D] - **DOS detector** — abnormal send pattern locks the pipe | DoD: A simulated infinite loop triggers `LOCKED` rather than account suspension. (M#29)
- [ ] 7.1.3 [D] - HTTP 429 honoured with backoff, never blind retry | DoD: A mocked 429 produces a wait, not an immediate resend. (Ch. 9)
- [ ] 7.1.4 [D] - Naming discipline for the three meanings of "token" | DoD: Rate-limiter tokens, LLM tokens and OAuth tokens use distinct identifiers throughout. (Ch. 9)

### 7.2 JSON artefacts
- [ ] 7.2.1 [D] - `declaration_<game_id>.json` builder | DoD: Teams, members, **four** repo links, MCP URLs, hardware, LLM model, token cap, timings.
- [ ] 7.2.2 [D] - `config_<game_id>_g<NN>.json` builder | DoD: The locked negotiated parameters; committed to the repo per match. (Appendix F §2)
- [ ] 7.2.3 [D] - `log_<game_id>_g<NN>.json` builder | DoD: Commits, reveals, moves, hints, nonces, hashes — sufficient for full replay verification.
- [ ] 7.2.4 [D] - `result_<game_id>.json` builder | DoD: Per-sub-game and cumulative scores, `github_commit`, total tokens, four repo links. (M#49, M#53, M#54)
- [ ] 7.2.5 [D] - Shared `game_uid`; filenames derived from `game_id` | DoD: Files from different matches can never collide. (Ch. 9)

### 7.3 Gmail delivery
- [ ] 7.3.1 [D] - Port `gmail_sender.py`, send-only scope, routed through the Gatekeeper | DoD: Reporting is fully automated with no human step; no direct Gmail call bypasses the gates. (M#30, M#32)
- [ ] 7.3.2 [D] - Report sent as a JSON **attachment**, never free text | DoD: A test asserts the body carries no report data. (M#33, M#34)
- [ ] 7.3.3 [D] - Recipient `rmisegal+uoh26finalgame@gmail.com` from config | DoD: Not hardcoded; test config points elsewhere. (M#51)
- [ ] 7.3.4 [D] - Each team sends its **own** report independently | DoD: No code path sends on the opponent's behalf. (M#35)

### 7.4 Live GUI — local truth only
- [ ] 7.4.1 [D] - `core/ui/live_gui.py` in Tkinter | DoD: File ≤150 lines; split widgets into `core/ui/widgets.py`. (ADR-005)
  - [ ] 7.4.1.a [D] - Belief heatmap, intensity ∝ posterior | DoD: Darker red = higher probability.
  - [ ] 7.4.1.b [D] - Own position and known barriers | DoD: Rendered distinctly.
  - [ ] 7.4.1.c [D] - Turn banner: green `YOUR TURN` / grey `LOCKED` | DoD: Input ignored while locked.
- [ ] 7.4.2 [D] - **Local-truth enforcement test** | DoD: Asserts the GUI layer never receives the opponent's true position. Failing this is project disqualification. (M#8, M#9)

### 7.5 Replay Viewer
- [ ] 7.5.1 [D] - `core/ui/replay.py` — load a log, step forward/back | DoD: Controls work on a saved match. (M#20)
- [ ] 7.5.2 [D] - Live re-hash of every entry | DoD: Recomputes `SHA256` from the revealed nonce and move and compares to the stored commitment.
- [ ] 7.5.3 [D] - Green `Verified OK` / red `TAMPERED` | DoD: A deliberately altered log produces `TAMPERED`; one such verdict voids the match. (Ch. 7)
- [ ] 7.5.4 [D] - `PeerSdk` is the only path used by GUI, Replay, CLI and tests | DoD: `grep -r "from core.domain" core/ui/` returns nothing. (X §4.1)

### ✅ Phase 7 Quality Gate
- [ ] 7.QG.1 [D] - `uv run ruff check .` | DoD: 0 violations.
- [ ] 7.QG.2 [D] - `uv run python scripts/check_file_size.py` | DoD: No file over 150 LOC. GUI modules breach most often — split into widgets/controller.
- [ ] 7.QG.3 [D] - `uv run pytest --cov` | DoD: All pass; coverage ≥85 % (GUI rendering excluded via `omit`).
- [ ] 7.QG.4 [D] - **Milestone M7 observed** | DoD: Summary reaches the inbox; GUI shows live state; Replay reproduces a recorded series with `Verified OK`.

---

## Phase 8: Advanced Strategy — the competitive edge
**Priority:** P1 | **Status:** Not Started ☐ | **Target:** starts once Phase 4 lands; runs parallel to 5–7
**DoD:** The advanced brains beat the Phase 3 baselines in ≥70 % of self-play sub-games.
**This is where the league grade lives.**

### 8.1 Cop — barrier-trap planning
- [ ] 8.1.1 [D] - Expectimax over the belief map, depth 2–3 | DoD: Beats the baseline Cop in self-play.
- [ ] 8.1.2 [D] - Barrier placement scored by reduction in the Thief's 3-step reachable-cell count | DoD: Greedy blocking replaced by cage construction.
- [ ] 8.1.3 [D] - Self-entrapment guard | DoD: A placement that reduces the Cop's own mobility below a threshold is rejected. (Ch. 3 warning)
- [ ] 8.1.4 [D] - Barrier budget pacing across 35 steps | DoD: Barriers remain available for the endgame squeeze.
- [ ] 8.1.5 [D] - Entropy-aware pursuit on a bimodal posterior | DoD: Chooses the move that best splits the modes rather than chasing the argmax.

### 8.2 Thief — scent-aware evasion
- [ ] 8.2.1 [I] - Escape-route maximisation under the belief map | DoD: Beats the baseline Thief in self-play.
- [ ] 8.2.2 [I] - Trail-aware movement — treat one's own emission as a cost | DoD: Avoids re-emitting at full strength in a cul-de-sac.
- [ ] 8.2.3 [I] - False-anchor tactic: lay a strong trail, then break away | DoD: Measurably increases survival rate against the baseline Cop. *(Original extension.)*
- [ ] 8.2.4 [I] - Endgame switch to safety once guaranteed evasion covers the remaining steps | DoD: Survival rate rises in the last third of a sub-game.

### 8.3 Shared
- [ ] 8.3.1 [D] - Bluff strategy driven by the reliability coefficient | DoD: Lies more when the opponent is believed to trust; tells truth when profiling suggests they discount everything.
- [ ] 8.3.2 [B] - Self-play harness: advanced vs. baseline, 100 sub-games | DoD: Win rate reported; ≥70 % required to adopt.
- [ ] 8.3.3 [D] - Unit tests for every scoring heuristic | DoD: Deterministic on fixed boards; coverage ≥85 %.

### ✅ Phase 8 Quality Gate
- [ ] 8.QG.1 [B] - `uv run ruff check .` | DoD: 0 violations.
- [ ] 8.QG.2 [B] - `uv run python scripts/check_file_size.py` | DoD: No file over 150 LOC. Brains grow fast — split search, scoring and policy.
- [ ] 8.QG.3 [B] - `uv run pytest --cov` | DoD: All pass; coverage ≥85 %.
- [ ] 8.QG.4 [B] - Self-play benchmark | DoD: Advanced brains win ≥70 % against the baselines.

---

## Phase 9: League Play
**Priority:** P0 | **Status:** Not Started ☐ | **Target:** 9–11 Aug
**DoD:** ≥4 counted matches against different teams, each with agreed result and both reports sent.
Graded matches are hosted from Itay's machine on Ollama (zero tokens). (ADR-003)

### 9.1 Pre-match protocol — repeat for every match
- [ ] 9.1.1 [B] - Negotiate the shared config; exchange and verify `config_sha256` | DoD: Byte-identical on both sides; play refused on mismatch. (M#11)
- [ ] 9.1.2 [B] - Exchange the scent model plus a worked numeric example; lock the digest | DoD: Both sides confirm identical interpretation. (M#23)
- [ ] 9.1.3 [B] - Declare counted games played so far, honestly | DoD: Recorded in the declaration JSON. A false declaration disqualifies the project. (M#37, M#38)
- [ ] 9.1.4 [B] - Exchange Step-0 declarations incl. commit hash | DoD: Tree clean; hash matches `git rev-parse HEAD`. (M#53)
- [ ] 9.1.5 [B] - Record any negotiated rule extension | DoD: Written into the config JSON and `docs/CONTRADICTIONS.md`.

### 9.2 Matches
- [ ] 9.2.1 [B] - Warm-up match (uncounted) | DoD: Protocol bugs shaken out before anything counts. (M#52)
- [ ] 9.2.2 [B] - Counted match 1 | DoD: Result agreed; both reports sent.
- [ ] 9.2.3 [B] - Counted match 2 | DoD: **Minimum for a passing grade reached.** (M#31)
- [ ] 9.2.4 [B] - Counted match 3 | DoD: Different team; diversity reward earned.
- [ ] 9.2.5 [B] - Counted match 4 | DoD: Different team.
- [ ] 9.2.6 [B] - Counted matches 5–8 | DoD: Each vs. a different team; max 10 total. (F)

### 9.3 Post-match protocol — repeat for every match
- [ ] 9.3.1 [B] - Mutual log audit, all nonces revealed | DoD: Completed **before** agreeing the result. (M#36)
- [ ] 9.3.2 [B] - Agree the result with the opponent | DoD: Both sides hold the same figures.
- [ ] 9.3.3 [B] - Send our own result JSON | DoD: Delivery confirmed in the sent folder.
- [ ] 9.3.4 [B] - **Confirm the opponent actually sent theirs** | DoD: Explicit confirmation obtained. A missing or contradictory report voids the match and scores 0 **for both teams**. (M#35)
- [ ] 9.3.5 [B] - Commit the config JSON and match log to both repos | DoD: Reproducible after the fact. (Appendix F §2.4)
- [ ] 9.3.6 [D] - Update `docs/LEAGUE_LOG.md` | DoD: Row complete with date, role, result, reports, commit hash.

### ✅ Phase 9 Quality Gate
- [ ] 9.QG.1 [B] - ≥4 counted matches completed | DoD: `LEAGUE_LOG.md` shows ≥4 rows, all different opponents.
- [ ] 9.QG.2 [B] - Zero matches lost to technical failure | DoD: No `TECHNICAL_LOSS` caused by our side.
- [ ] 9.QG.3 [B] - Zero audit failures | DoD: No `TAMPERED` verdict in any match.
- [ ] 9.QG.4 [B] - **Milestone M8 observed** | DoD: All counted matches reported by both sides.

---

## Phase 10: Research & Documentation
**Priority:** P2 | **Status:** Not Started ☐ | **Target:** parallel with Phase 9, 9–12 Aug
**DoD:** Sensitivity study complete; notebook with quality visualisations; academic README complete
in both repos. If the schedule slips, cut from here — never from Phase 9.

### 10.1 Parameter sensitivity
- [ ] 10.1.1 [D] - Sweep harness, one-at-a-time | DoD: Reproducible runs written to `results/`.
- [ ] 10.1.2 [D] - Sweep ρ (scent decay) | DoD: Win rate vs. ρ plotted; the book's claim about trail length checked empirically.
- [ ] 10.1.3 [D] - Sweep barrier quota | DoD: Cop win rate vs. quota plotted.
- [ ] 10.1.4 [D] - Sweep board size | DoD: Effect on match length quantified.
- [ ] 10.1.5 [I] - Sweep hint reliability and `every_n_steps` | DoD: Token cost vs. benefit quantified.

### 10.2 Analysis notebook
- [ ] 10.2.1 [D] - `notebooks/results_analysis.ipynb` | DoD: Methodical analysis, LaTeX equations, academic citations. (X §9.2)
- [ ] 10.2.2 [D] - Visualisations | DoD: High resolution, labelled axes, consistent accessible palette. (X §9.3)
  - [ ] 10.2.2.a [D] - Belief heatmap snapshots | DoD: Shows convergence onto the opponent.
  - [ ] 10.2.2.b [D] - Scent decay curves | DoD: Single deposit vs. re-emission, as in the book's figure.
  - [ ] 10.2.2.c [D] - Win-rate bars by opponent and role | DoD: Both roles represented.
  - [ ] 10.2.2.d [I] - Reliability coefficient over time | DoD: Demonstrates we detected opponent deception. *(Showpiece.)*
  - [ ] 10.2.2.e [D] - Token cost breakdown | DoD: Feeds both the README and the result JSON. (X §11.1)
- [ ] 10.2.3 [D] - Belief-convergence animated GIF | DoD: Embedded in the README. *(P3)*

### 10.3 Written artefacts
- [ ] 10.3.1 [D] - `docs/RESEARCH-REPORT-Performance-Analysis.md` | DoD: Modelled on the reference repo's, applied to our stack and providers.
- [ ] 10.3.2 [D] - Edge-case catalogue with screenshots | DoD: Opponent disconnect · malformed hint · tunnel drop mid-protocol · LLM timeout · hash mismatch. Each ends in a clean technical loss with a persisted log. (X §6.3, Ch. 11)
- [ ] 10.3.3 [D] - Nielsen 10-heuristics GUI evaluation | DoD: Table with pass/partial and documented mitigations. (X §10.1)
- [ ] 10.3.4 [D] - ISO/IEC 25010 quality table | DoD: All eight dimensions addressed against this architecture. (X §13)
- [ ] 10.3.5 [D] - Finalise `docs/CONTRADICTIONS.md` | DoD: Each contradiction, our choice and our reasoning.
- [ ] 10.3.6 [D] - Finalise `docs/PROMPT_LOG.md` | DoD: Prompts, context, outputs, iterations, lessons. (X §8.3)

### 10.4 Academic README — both repos
- [ ] 10.4.1 [D] - §1 Dec-POMDP formalism | DoD: State space, observations, uncertainty described. (Ch. 9)
- [ ] 10.4.2 [D] - §2 FastMCP orchestration dilemmas | DoD: Turn management, network failure handling, Gatekeeper and Orchestrator roles.
- [ ] 10.4.3 [D] - §3 Strategies implemented | DoD: Belief map, heuristics, barrier planning, evasion.
- [ ] 10.4.4 [D] - §4 Learning curves | DoD: **N/A — no RL used.** State this explicitly rather than omitting the section. (ADR-002)
- [ ] 10.4.5 [D] - §5 Screenshots — **absolute requirement** | DoD: Belief heatmap from the Live GUI **and** `Verified OK` from the Replay App. (Ch. 9)
- [x] 10.4.6 [D] - §6 Cross-link to the companion repo | DoD: Present from the first commit — `docs/README_cop.md` and `docs/README_thief.md` each link the other repo and are published as each repo's `README.md`. (M#49)
- [ ] 10.4.7 [D] - Installation, usage, configuration, licence sections | DoD: README readable as a full user manual. (X §2.1)

### ✅ Phase 10 Quality Gate
- [ ] 10.QG.1 [D] - `uv run ruff check .` | DoD: 0 violations.
- [ ] 10.QG.2 [D] - `uv run python scripts/check_file_size.py` | DoD: No file over 150 LOC.
- [ ] 10.QG.3 [D] - `uv run pytest --cov` | DoD: All pass; coverage ≥85 %.
- [ ] 10.QG.4 [B] - README complete in **both** repos | DoD: All six mandatory sections present in each. (M#42)

---

## Phase 11: Submission
**Priority:** P0 | **Status:** Not Started ☐ | **Target:** 12 Aug — **finish by midday, not 23:00**
**DoD:** Both repos tagged and shared; Moodle PDF submitted individually by each member.

### 11.1 Publication
- [x] 11.1.1 [D] - `scripts/publish.py` — split publication | DoD: **Verified** against two real clones: cop repo has no `thief/`, thief repo has no `police/`, and a planted stale directory is removed on the next publish. Split defined as data in `core/shared/publish_spec.py` and unit-tested. (ADR-001)
  - [x] 11.1.1.a [D] - Copy `core/ + police/ + config/police/` into the cop clone | DoD: Tree correct.
  - [x] 11.1.1.b [D] - Copy `core/ + thief/ + config/thief/` into the thief clone | DoD: Tree correct.
  - [x] 11.1.1.c [D] - Pre-push secret scan; abort on any hit | DoD: **Verified** — a planted Groq key makes publish exit 1 and push nothing to either repo. Six key patterns covered. (M#39)
  - [x] 11.1.1.d [D] - Commit and push both | DoD: Both remotes updated.
- [ ] 11.1.2 [D] - Verify each repo contains README, `config/`, PRD files, PLAN, TODO | DoD: All five present in both. (M#50)
- [ ] 11.1.3 [D] - Annotated tag `v1.0-submission` in both repos | DoD: `git tag -a v1.0-submission -m "..."` pushed; `git show` points at the intended commit. (M#41)
- [ ] 11.1.4 [D] - Share both repos with `rmisegal@gmail.com`, or make public | DoD: Lecturer can access both. (Appendix C)

### 11.2 🧑 USER ACTION — Moodle
> **PAUSE — I cannot submit on Moodle. Both members must do this separately.**

- [ ] 11.2.1 🧑 [D] - Download the Word template from Moodle; fill fields **without moving or altering any field**; save as PDF | DoD: PDF ready; layout untouched. (M#43)
- [ ] 11.2.2 🧑 [D] - Include both repo links and the 8-character team ID `bestteam` | DoD: Both links present. (M#45, M#49)
- [ ] 11.2.3 🧑 [D] - Self-grade for **code quality only** — never based on the league result | DoD: Justification references coverage, architecture and documentation, not wins. (M#55)
- [ ] 11.2.4 🧑 [D] - Diana submits on Moodle | DoD: Submission confirmed.
- [ ] 11.2.5 🧑 [I] - Itay submits on Moodle **separately** | DoD: Submission confirmed. No individual submission means no grade for that member. (M#44)

### ✅ Phase 11 Quality Gate — final pre-submission checklist (Ch. 11 §11.5)
- [ ] 11.QG.1 [B] - Base logic runs a full race without crashing; scoring enforced | DoD: Observed.
- [ ] 11.QG.2 [B] - FastMCP over a **public** URL, not localhost | DoD: Observed.
- [ ] 11.QG.3 [B] - Commit-reveal active; audit passes with no forgery detected | DoD: Observed.
- [ ] 11.QG.4 [B] - Scent map and belief map computed and influencing decisions | DoD: Observed.
- [ ] 11.QG.5 [B] - Live GUI and Replay App both run; Replay shows `Verified OK` | DoD: Observed.
- [ ] 11.QG.6 [B] - Both teams sent JSON reports for every counted match | DoD: Confirmed per row of `LEAGUE_LOG.md`.
- [ ] 11.QG.7 [B] - Two repos, cross-linked, accessible, tagged | DoD: Verified from a logged-out browser.
- [ ] 11.QG.8 [B] - ≥2 counted matches vs. different teams | DoD: ≥4 achieved.
- [ ] 11.QG.9 [B] - Coverage ≥85 %, ruff clean, no file >150 LOC, no secrets | DoD: CI green on the tagged commit.
- [ ] 11.QG.10 [B] - Each member submitted individually on Moodle | DoD: Both confirmed.

---

## Continuous gates — run before every commit

`uv run python scripts/ship.py -m "..."` runs all of these in order, then commits and publishes.
It halts at the first failure and pushes nothing. The individual commands are for debugging.

| Check | Command | Threshold |
|---|---|---|
| Lint | `uv run ruff check .` | 0 violations |
| **File size** | `uv run python scripts/check_file_size.py` | **no file > 150 LOC** |
| Tests | `uv run pytest` | all pass |
| Coverage | `uv run pytest --cov` | ≥ 85 % |
| Secrets | `scripts/publish.py --scan-only` | 0 |

---

## Critical path

**0.3.1 (book opponents) → Phase 1 → 2 → 3 → 4 → 5 → 6 → 7 → Phase 9 (league) → Phase 11.**

Phase 8 starts as soon as Phase 4 lands and runs alongside 5–7. Phase 10 runs alongside Phase 9.

Phase 4 carries the most schedule risk and holds the most slack. If a layer slips, cut P2/P3 items
from Phase 10 — **never** from Phase 9. Every additional counted match against a new opponent is
worth up to 10 league points, and league position spans 25 grade points.
