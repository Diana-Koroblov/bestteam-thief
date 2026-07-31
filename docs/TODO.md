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

- [x] 0.2.1 🧑 [D] - Google Cloud project + Gmail API + Google Auth platform, **send-only** scope `gmail.send` | DoD: `credentials.json` saved **outside** both repos; `check_setup.py` reports Gmail credentials OK. See SETUP 0.2.1. (M#30)
  - [x] 0.2.1.a 🧑 [D] - Create the project and enable the Gmail API | DoD: API shows as Enabled in the console.
  - [x] 0.2.1.b 🧑 [D] - Configure Branding + Audience (**External**), add yourself as a test user, add scope `gmail.send` | DoD: Consent screen saved with exactly one scope. SETUP 0.2.1.b-d
  - [x] 0.2.1.c 🧑 [D] - Create OAuth client ID (**Desktop app**), download `credentials.json` | DoD: **Verified 28/07** — `check_setup.py` confirms a Desktop client at `C:\Users\diana\.p2p-secrets\credentials.json`, outside both repos. SETUP 0.2.1.e-f
  - [x] 0.2.1.d 🧑 [D] - ⚠️ **Publish the app** (Testing → In production) — **confirmed 28/07: Publishing status = In production** | DoD: Audience page reads *In production*. **`check_setup.py` cannot verify this — publishing status is not exposed in `credentials.json` or by any API. Confirm by eye.** **Skipping this makes the refresh token expire after 7 days and silently breaks league reporting mid-project** — an unsent report scores 0 for **both** teams. SETUP 0.2.1.g (M#35)
- [x] 0.2.2 🧑 [D] - Groq API key at console.groq.com/keys | DoD: **Verified 28/07** — `check_setup.py` reports `gsk_xJkR...(56 chars)`.
- [ ] 0.2.3 🧑 [I] - Install Ollama and pull a model small enough for the 30 s step deadline | DoD: A 15-word prompt returns in under 10 s at `localhost:11434`. (PRD Q3)
- [ ] 0.2.4 🧑 [B] - ngrok accounts + authtokens on both machines | DoD: **Diana verified 28/07** — installed and configured, static domain `customs-countdown-uncork.ngrok-free.dev`. **Itay pending.**
- [x] 0.2.5 [D] - Decide: static ngrok domain or dynamic URLs? | DoD: **Answered — static.** ngrok now assigns every free account a permanent `*.ngrok-free.dev` dev domain, so no paid plan and no per-match URL exchange is needed. Recorded in PRD Q5 and SETUP 0.2.5.
- [ ] 0.2.6 🧑 [B] - Note each machine's static ngrok domain in `config/<role>/game.toml` | DoD: Both domains recorded; `ngrok http 8801 --url <domain>` works on each machine.

### 0.3 🧑 USER ACTION — League scheduling ⏰ **DO THIS FIRST**
> **PAUSE — This is the binding constraint on the final grade, and it is not a coding task.**
> Two matches passes. Diversity reward is 10 points per new opponent. League position spans
> 25 grade points. Every day of delay shrinks the pool of teams still free.

- [ ] 0.3.1 🧑 [B] - Contact 6–8 teams; agree dates and roles | DoD: ≥4 confirmed slots in a shared calendar with team names, contacts and times. (M#31)
- [ ] 0.3.2 🧑 [B] - Book one **warm-up** (uncounted) match for ~8 Aug | DoD: A friendly team confirmed for protocol shakedown. (M#52)
  - **📋 Checklist to run *during* the warm-up — these can only be done against a real opponent over a real tunnel, and the match is the one chance to collect them:**
  - [ ] 0.3.2.a - **Measure per-message latency** (this is task **2.5.4**, and it decides **2.5.2**) | DoD: median and worst-case seconds per game message written into `LEAGUE_LOG.md`.
    - Read it straight off the server log: each game message currently costs a full MCP session — `POST initialize · POST notify · GET · POST call · POST · DELETE`. Time the gap between the first and last line of one such block.
    - **Act only if worst case > ~5 s** — a sixth of the 30 s response budget spent on transport alone. Then, and only then, rewrite `OpponentClient` to hold one session for the match. Below 5 s, close 2.5.4 and leave 2.5.2 as decided.
  - [ ] 0.3.2.b - **Confirm the coordinate convention with a worked example** (C-010, negotiation item N18) | DoD: both sides state in writing that `[0,1]` is one cell **East** of `[0,0]`.
    - Mirrored coordinates make the log audit report forgery against two honest teams. This is the cheapest possible thing to check and the most expensive to discover late.
  - [ ] 0.3.2.c - **Verify their `num_games`** | DoD: their config says **6**, not 1.
    - The reference implementation ships `num_games: 1` (C-001). Anyone who copied it will propose 1, and Appendix F marks it **fixed** — accepting it means *both* teams deviate from a fixed value.
  - [ ] 0.3.2.d - **Exchange the scent worked example** (N3, C-007) | DoD: they confirm 0.9 decays to **0.81** after one turn, not 0.80.
    - 0.80 means they built on the reference's subtractive decay. Catching it before the match also tells us which implementation they are running.
  - [ ] 0.3.2.e - **Agree the 3–3 role split** (C-011, N17) | DoD: written into the negotiation payload.
  - [ ] 0.3.2.f - **Record their tunnel URL and whether `/mcp` needs the trailing slash** | DoD: noted in `LEAGUE_LOG.md`; ours strips it either way (2.5.1).
- [x] 0.3.3 [D] - Create `docs/LEAGUE_LOG.md` — one row per opponent: date, role, result, reports sent, commit hash | DoD: Table skeleton committed; filled as matches complete. (M#37)

### 0.4 Specification documents
- [x] 0.4.1 [D] - `docs/PRD.md` | DoD: All 55 mandatory rules and 32 Appendix F values traced (recount 30 Jul: Tables 13–19 hold 32 rows, not 31 — see docs/PARAMETERS.md).
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
  - **Re-audited 31/07** after Diana pointed out that Appendix F is the single source of truth for every quantitative value, so a *fixed*, *minimum* or *negotiable* parameter can never be in conflict — only mechanisms and timing can. Two of these three original entries did not survive the test: **C-001** became a reference-implementation defect (6 is *fixed*; the reference is simply non-conformant) and **C-003** was removed entirely (7×7 is a *minimum*, so a 10×10 figure is a legal raised value). C-002 stands — it is a real self-contradiction, in the excellence guide rather than the rulebook.

### 0.5 Reference material
- [x] 0.5.1 [D] - Clone and read `rmisegal/Game-P2P-Cop-Chase` | DoD: **Done 28/07.** Confirmed genuinely two-process (refuting a claimed monolith). Four divergences found and logged: C-005 (field transmitted, not sampled), C-007 (subtractive vs multiplicative decay), C-008 (scent field unsealed), C-009 (Board defaults to king moves). Still to do: run a live match in two terminals.
- [x] 0.5.2 [D] - Graphify knowledge graph of the reference repo | DoD: **Done 30/07.** `assets/reference-graph.png` committed to both repos; README section with colour key and three findings published.
  - [x] 0.5.2.a [D] - `core/shared/import_graph.py` + `scripts/make_graph_vault.py` | DoD: **Done 28/07.** AST-based; only internal imports become edges; relative imports resolve; a broken file never aborts the walk. 13 unit tests. Verified against the reference repo: **60 modules, 123 internal edges, 2 949 code lines.**
  - [x] 0.5.2.b 🧑 [D] - Open the vault in Obsidian and screenshot Graph View | DoD: `assets/reference-graph.png` committed. Two display settings first: filter out the generated summary note with `-file:_index` (otherwise it appears as a hub that does not exist in the real architecture), and turn off **Show orphans** (they are all empty `__init__.py` files). Both are noted in the README caption.
  - [x] 0.5.2.c [D] - Write up three architectural findings for the README | DoD: **Done 28/07.** Section added to both READMEs: hubs are the dependency-free leaves (`exceptions` 14, `constants` 11); `peer.runtime` is the orchestrator at 16 connections; no dead code. Plus the colour key and a pointer to C-005…C-009.
- [x] 0.5.3 [D] - Read the reference repo's `RESEARCH-REPORT-Performance-Analysis.md` | DoD: Provider rate limits and fallback design understood; informs task 4.5. — findings in **`docs/REFERENCE_PERFORMANCE_NOTES.md`**.
  - **No config change after all.** I first raised `every_n_steps` 1 → 3; **Diana caught that this was wrong and it is reverted.** The book (Ch. 6.5.1) frames the parameter purely as a token-budget question, and our providers — `template` and `ollama` — spend **zero** tokens, so there is no budget to protect. Raising it would only have cost verbal variety in a graded layer. Separately: `every_n_steps` controls how often the **model** runs, *not* whether a hint is sent — a hint goes out every turn regardless, because the commit seals it (Ch. 5.3.1); the template writes it on the skipped turns.
  - **Confirmed our existing choices:** `template` default, `ollama` for graded matches, movement never delegated to a model, template fallback on provider error.
  - **For task 4.5:** demand is ~0.5 RPM against a 30 RPM budget, so the Gatekeeper never trips in normal play — it is insurance, must **queue rather than error**, and its retry budget (3 × 5 s) must stay inside the 30 s response timeout. That is why `max_retries` stays at the Appendix F minimum.
  - **Scheduling consequence:** a 6-sub-game series is ~2.3 h of wall-clock at the speed of the *slower* peer. Ten opponents ≈ 20+ hours of match time to coordinate. Sharpens the deadline on 0.3.1.

### ✅ Phase 0 Quality Gate
- [x] 0.QG.1 [D] - `uv run ruff check .` | DoD: `All checks passed.` — runs as gate 1 of `ship.py` on every push, so it cannot regress silently.
- [x] 0.QG.2 [D] - `uv run python scripts/check_file_size.py` | DoD: No file over 150 LOC. — gate 2 of `ship.py`.
- [x] 0.QG.3 [D] - Secret scan on both repos | DoD: Zero matches for `gsk_`, `sk-ant`, `BEGIN PRIVATE KEY` in tracked files **or history**. (M#39)
  - The **"or history"** half was not actually covered: `scan_tracked` only sees the current checkout, so a key committed and then deleted passes it while staying readable forever in the log. Added `scan_history()` and `scripts/scan_secrets.py --history --root <repo>`.
  - Run on all three trees — working tree, `bestteam-cop`, `bestteam-thief` — across all 11 commits: **clean**. Tracked scan clean on all three too.
  - Caught two bugs in the scanner while proving it: the history scan initially reported our own test fixture (it lacked the per-file exemption the tracked scan has), and the `.example` suffix exemption never actually matched `.env-example` — a no-op that looked like it worked. `.env-example` is now deliberately **not** exempt, since it is the likeliest place for someone to paste a real key.
  - ⏰ **Re-run before submission.** History grows; a clean scan today says nothing about a commit made next week.
- [x] 0.QG.4 [B] - PRD, PLAN and the 10 sub-PRDs reviewed and approved | DoD: **`PRD_1_base_logic.md` approved 30/07** — the five design decisions (diagonals removed from the enum, the three capture-resolution defaults, config-driven values, immutable state, no randomness) all accepted. Remaining sub-PRDs are approved at the start of their own phase. (X §2.5)

---

## Phase 1: Base Logic (Layer 1)
**Priority:** P0 | **Status:** ✅ Complete — all gates green, M1 observable | **Target:** 31 Jul – 1 Aug
**DoD:** Two agents move legally on a 7×7 grid; a 15th barrier is rejected; all three capture
conditions fire correctly; scoring matches Appendix F; coverage ≥85 % on `core/domain`.

### 1.1 Configuration foundation
- [x] 1.1.1 [D] - `core/shared/version.py` with `VERSION = "1.00"` | DoD: Matches `pyproject.toml` and every config `version` key; asserted by a unit test. (X §8.1)
- [x] 1.1.2 [D] - `core/shared/constants.py` — immutable non-negotiable constants only | DoD: No value that belongs in config lives here. (X §7.2)
- [x] 1.1.3 [D] - `config/<role>/game.json` with all 32 Appendix F defaults | DoD: Every key from PRD §5 present; the two role copies are byte-identical. (M#11, F)
  - Verified byte-identical by `sha256sum` **and** by `test_both_roles_ship_an_identical_shared_contract`.
  - Carries our negotiated additions too: `capture.*` (C-006) and `pheromones.decay_model` / `field_includes_current_turn` / `seal_scent_digest` (C-005, C-007, C-008).
- [x] 1.1.4 [D] - `config/<role>/game.toml` private skeleton with explanatory comments | DoD: `[game]`, `[network]`, `[strategy]`, `[trash_talk]`, `[llm]`, `[email]` present. **Move the recorded ngrok domains from SETUP 0.2.5 into `[network]`** — Diana's is `customs-countdown-uncork.ngrok-free.dev`. (Appendix B)
  - ⚠️ **Deviation, deliberate:** `[game]` holds *local run settings only* (seed, self-play opponent, step delay). It does **not** mirror the negotiated physics, because a second copy of an agreed value is a second thing that can drift while the shared digest still matches. Enforced by `test_private_config_does_not_mirror_negotiated_physics`.
- [x] 1.1.5 [D] - `config/<role>/rate_limits.json` | DoD: `requests_per_minute`, `concurrent_requests`, `retry_backoff_sec`, `max_retries`, `queue_depth` present; versioned. (F, X §5.2)
- [x] 1.1.6 [D] - `core/shared/config_manager.py` — load, merge, validate | DoD: File ≤150 lines; split into loader + validator if needed.
  - Split as predicted: `config_manager.py` (load/merge/version/digest) + `config_spec.py` (the Appendix F table as data). Both well under 150 LOC.
  - [x] 1.1.6.a [D] - Load private TOML then shared JSON | DoD: Missing JSON falls back to TOML defaults cleanly.
  - [x] 1.1.6.b [D] - JSON **overlays** TOML for every shared key | DoD: Unit test proves a private file cannot weaken a signed value. (Appendix B)
  - [x] 1.1.6.c [D] - Version compatibility check at startup | DoD: Mismatch raises `ConfigVersionError` with a readable message.
  - [x] 1.1.6.d [D] - Minimum-direction validator | DoD: A config lowering `max_barriers` below 14 raises; raising it to 20 passes. (M#12)
  - [x] 1.1.6.e [D] - `config_sha256()` over canonical JSON | DoD: Both peers compute the same digest for the same file.
    - Shipped as `Config.shared_digest()`, over `core/crypto/canonical.py`. Hashes the **shared** file only — including private settings would make two correctly-agreed peers disagree, because their ngrok domains differ.
- [x] 1.1.7 [D] - `core/crypto/canonical.py` pulled forward from Phase 6 | DoD: Exactly one canonical serialiser exists in the repo; every digest in the project routes through it. (M#11, M#17, M#23)
  - Pulled forward because the config digest needs it *now*, and a second serialiser written later in Phase 6 is precisely the divergence that scores 0 for both teams.
- [x] 1.1.8 [D] - Unit tests for 1.1 | DoD: 171 pass, coverage 95.16 %; `config_manager.py` and `config_spec.py` both at 100 %.

### 1.2 Board & movement
- [x] 1.2.1 [D] - `core/domain/board.py` — dimensions, bounds, passability | DoD: 7×7 read from config; no hardcoded size; out-of-bounds and barrier cells both report impassable.
  - `is_passable` deliberately makes an **edge and a wall indistinguishable**. They have identical consequences for mobility, and treating them alike is what makes the corner case of M#47 fall out instead of needing special handling.
  - Constructor rejects `grid_size < 7`, so an illegal config fails at startup rather than three turns into a match. Tested at sizes 7, 9, 10, 15 and with `origin_index = 1` (T1.18).
- [x] 1.2.2 [D] - `core/domain/actions.py` — **4 orthogonal directions + STAY only** | DoD: No diagonal exists anywhere in the enum or the delta table. (M#14, F)
  - `Direction` inherits from `str`, so a move serialises as `"N"` and not `"Direction.N"`. A move that hashed differently on each peer would fail every commitment check.
  - Guarded by a test asserting `abs(dr) + abs(dc) <= 1` for every delta, so a diagonal cannot be reintroduced by a careless port of the reference `Board` (C-009).
- [x] 1.2.3 [D] - `core/domain/movement.py` — legal move resolution | DoD: Diagonal input raises; out-of-bounds raises; barrier cell raises; STAY is legal. (M#13)
  - Raises rather than falling back to STAY: an opponent's illegal move is a technical loss in our favour, and silently absorbing it would cost us the point.
  - T1.17 verified — the same `(state, action)` on two independent `Board` instances yields identical results, **errors included**.
- [x] 1.2.4 [D] - `get_legal_moves(pos, barriers, board)` | DoD: Returns exactly the passable neighbours plus STAY; empty-except-STAY case handled.
  - STAY is always present and always **first**, so a search tie broken by iteration order resolves the same way on both peers.
  - Added `is_immobilised()` alongside it. The two are deliberately separate: STAY is always legal, so "has no legal move" is never true and cannot be the M#47 test. M#47 is **adjacency** — see C-006a.

### 1.3 Barriers
- [x] 1.3.1 [D] - `core/domain/barriers.py` — `BarrierManager` | DoD: File ≤150 lines. (M#15, M#46, F) — 111 LOC.
  - [x] 1.3.1.a [D] - `__init__` reads quota from config; rejects negative | DoD: Quota 14 default; `-1` raises `ValueError`.
  - [x] 1.3.1.b [D] - `can_place(target, cop_pos, is_forgoing_move)` | DoD: Legal only on the Cop's own cell or one of the 4 orthogonal neighbours, and only when forgoing movement. Diagonal-adjacent rejected.
    - Backed by `rejection_for()` returning a `RejectionReason` enum rather than a bare bool, checked in the order a reviewer would ask them. `can_place` is a thin wrapper. The reason string is what we quote when refusing an opponent's claim.
  - [x] 1.3.1.c [D] - `place()` enforces the quota | DoD: 15th placement rejected with quota 14.
    - Also tested: a **rejected** placement never costs quota.
  - [x] 1.3.1.d [D] - Permanence — no removal API exists | DoD: A blocked cell stays blocked for the rest of the sub-game.
    - Enforced by the *absence* of an API, not a flag. A test asserts `remove`/`clear`/`reset`/`undo`/`delete`/`pop` do not exist, so nobody adds one "just for testing".
  - [x] 1.3.1.e [D] - Placement on the Thief's current cell returns `CAPTURE` | DoD: Unit-tested. (M#46)
    - `place()` also returns `CAPTURE` when the barrier seals the Thief's **last orthogonal exit** (M#47). Both live in one call because a separate capture check is exactly what gets forgotten.
- [ ] 1.3.2 [D] - Truthful barrier declaration in the move record | DoD: Every placement carries its exact cell into the signed record; no hidden placement path exists. (M#15, M#16)
  - [x] 1.3.2.a [D] - Single placement path, cell always carried | DoD: `place()` is the only way a barrier reaches the board, and every result — including every rejection — returns a `Placement` naming the exact cell. There is no API that blocks a cell without producing a declarable record.
  - [ ] 1.3.2.b [D] - Wire the declaration into the signed record | DoD: The cell appears inside the commit hash, so a placement cannot be altered after the fact. **Blocked on Phase 6** (commit-reveal); the domain half is done.

### 1.4 Game state, capture & scoring
- [x] 1.4.1 [D] - `core/domain/game_state.py` — frozen dataclass | DoD: Positions, barriers, step count, barriers placed; immutable.
  - `advanced()` always increments the step, rather than leaving it to each caller. A turn that forgets to count is a step the Thief survived for free, and survival is what the Thief wins on.
  - `barriers_placed` is stored, not derived from `len(barriers)`. If a negotiated rule ever blocks a cell without spending quota, a derived value would be silently wrong instead of loudly stale.
  - Hashability is tested, because commit-reveal hashes the state a move was made against (Ch. 5.3.1) — a mutable object with an identity cannot serve as that.
- [x] 1.4.2 [D] - `core/domain/rules.py` — terminal condition detection | DoD: All four paths unit-tested.
  - Built as a `Rules` value resolved **once** from config, not a function that re-parses config per call: expectimax evaluates this thousands of times per turn, and re-reading config in the hot loop is both slow and a chance for the two peers to drift. This is a deliberate deviation from the `terminal_state(state, config)` signature in PRD 1 §4.
  - [x] 1.4.2.e [D] - Capture-resolution config flags: `capture.resolution`, `capture.stay_counts_as_move`, `capture.swap_is_capture` | DoD: All three implemented, not merely defaulted — an opponent may agree the opposite reading. Defaults `after_moves` / `false` / `true`. See CONTRADICTIONS C-006, PRD 1 §3.4b.
    - Each flag is tested in **both** settings, and `test_before_moves_judges_the_pre_move_snapshot` shows the same transition producing opposite verdicts under the two readings — which is precisely why the flag has to be signed rather than assumed.
  - [x] 1.4.2.a [D] - Cop lands on the Thief's cell + Capture Claim → Cop wins | DoD: Tested. (Ch. 3)
  - [x] 1.4.2.b [D] - Barrier placed on the Thief's cell → Cop wins | DoD: Tested. (M#46) — lives in `BarrierManager.place()` (1.3.1.e); `rules.py` covers the resulting state.
  - [x] 1.4.2.c [D] - Thief with **no** legal move at all → captured | DoD: Tested with a fully enclosed thief. (M#47)
    - Also tested cornered (2 barriers) and against an edge (3), since edges block exactly as barriers do.
  - [x] 1.4.2.d [D] - Thief survives `survival_threshold` valid steps → Thief wins | DoD: Tested at exactly 35 and at 34. (F)
    - Capture is checked **before** survival: a Thief caught on step 35 was caught, not saved by the clock.
- [x] 1.4.3 [D] - `core/domain/scoring.py` — capture 20/5, survival 5/10, tie 2/2, technical loss 0/0 | DoD: All values read from config, zero numeric literals. (M#48, F)
  - **Confirmed from the book, not inferred:** a technical loss pays **0 to both sides** — Ch. 3.5, *"ההפסד הטכני מאפס את שני הצדדים כאחד"*, explicitly so that neither side can win by making the other time out. Nothing we build should ever stress an opponent's clock; there is no upside.
  - `score()` **raises** on a `TIE` verdict rather than returning a value. A tie is a series-level result, and quietly returning something for a single sub-game would hide the mistake.
- [x] 1.4.4 [D] - Series aggregation across 6 sub-games, with tie detection | DoD: Equal cumulative totals award `tie_score` to both sides. (F)
  - The tie is decided on **cumulative points**, not sub-games won: 3 captures and 3 survivals is 75-45, not a draw.
  - ⚠️ **New contradiction found while testing — C-013.** A series in which every sub-game ended in a technical loss is also arithmetically level, at 0-0, so a literal reading pays both teams the tie bonus for a series neither played. That inverts the incentive Ch. 3.5 exists to create. We pay the bonus only when at least one sub-game produced a real result. Cheap to raise at negotiation, awkward to argue afterwards.

### 1.4b Connectivity — added 31/07, not in the original plan
- [x] 1.4.5 [D] - `core/domain/connectivity.py` — `reachable`, `are_connected`, `region_size`, `exit_count` | DoD: 100 % covered; the corridor self-trap is a named test case.
  - **Why it was added mid-phase.** Diana looked at the demo's scenario 2 and asked whether the cop realises it is now blocked. It does not — and nothing in the codebase could have told it. Rows 0 and 2 fully walled leaves the cop in a **7-cell corridor** with the thief loose in the other 28. The cop can never reach it again, the thief runs out the clock, and barriers are permanent so nothing recovers it.
  - Ch. 3.4 warns about exactly this — *"מבלי לחסום בטעות את נתיבי הגישה של עצמו"* — and we had the warning in three documents but no primitive that could enforce it.
  - **The distinction the module exists to protect:** *separation* is the failure, *confinement* is the win. A small region shared with the thief is a winning position; a large region the cop cannot enter is a lost one. They look similar on a board and are opposite in value, so it is computed, never eyeballed. Both cases are tests.
  - `exit_count` is the endgame counter (drive it to 1, then the last wall captures under M#47). `region_size` is the honest measure of thief freedom — a thief with four open neighbours inside a nine-cell room is nearly caught, and a test pins that.
  - Feeds the cop's connectivity constraint and the exit-count-1 win condition in `PRD_strategy_advanced.md`; Phase 4 now has its geometry ready.

### 1.5 Tests
- [x] 1.5.1 [D] - `tests/conftest.py` shared fixtures: `minimal_config`, `board_7x7`, `game_state_factory`, `barrier_manager`, `mock_llm_provider`, `mock_mcp_peer` | DoD: Each fixture used by ≥1 test.
  - Shipped: `minimal_config`, `board_7x7`, `game_state_factory`, `barrier_manager`, plus `rules` and `score_table`. Each is used by at least one test — the local duplicates in `test_rules.py` and `test_barriers.py` were deleted rather than left alongside.
  - `minimal_config` loads the **real shipped config**, not a hand-built dict. A fixture that invented its own values would keep passing after the shipped file drifted from Appendix F, which is the one thing these tests exist to catch.
  - ⚠️ **`mock_llm_provider` and `mock_mcp_peer` deliberately not written.** The interfaces they would double do not exist yet — the provider seam lands in Phase 7, the MCP peer in Phase 2. A mock written before its interface is a mock of a guess. Moved to those phases; the reason is recorded at the top of `conftest.py` so it does not look like an oversight.
- [x] 1.5.2 [D] - Unit tests for board, movement, actions | DoD: Happy path and error path per public function. (X §6.1) — `tests/unit/test_board.py` (11) + `test_movement.py` (26). `core/domain/board.py`, `actions.py` and `movement.py` all at **100 %** coverage.
- [x] 1.5.3 [D] - Unit tests for barriers, including all five sub-cases of 1.3.1 | DoD: Every branch covered. — `tests/unit/test_barriers.py` (29 tests), `core/domain/barriers.py` at **100 %**.
- [x] 1.5.4 [D] - Unit tests for rules and scoring | DoD: All four terminal conditions covered. — `test_game_state.py` (12), `test_rules.py` (20), `test_scoring.py` (16). `game_state.py`, `rules.py` and `scoring.py` all at **100 %**; all of `core/domain` is at 100 %.
- [x] 1.5.5 [D] - Unit tests for the config manager, incl. the overlay and minimum-direction rules | DoD: `ConfigVersionError` and minimum-violation both asserted. — done alongside 1.1 in `tests/unit/test_config_manager.py`, `test_config_spec.py`, `test_canonical.py`.

### ✅ Phase 1 Quality Gate
- [x] 1.QG.1 [D] - `uv run ruff check .` | DoD: 0 violations.
- [x] 1.QG.2 [D] - `uv run python scripts/check_file_size.py` | DoD: No file over 150 LOC. Split anything that grew. — largest is `barriers.py` at 111.
- [x] 1.QG.3 [D] - `uv run pytest --cov` | DoD: All pass; coverage ≥85 % on `core/domain` and `core/shared`. — **322 pass, 96.82 % overall; every one of the eight `core/domain` modules at 100 %.**
- [x] 1.QG.3b [D] - `uv run python scripts/check_split_repos.py` — **new standing gate** | DoD: The suite passes in a simulated `bestteam-cop` tree *and* a simulated `bestteam-thief` tree, each holding only its own role.
  - **Why it exists:** CI run #8 failed on *both* repositories while every local gate was green. `tests/unit/test_config_*.py` referenced `config/police/` at module level; that path does not exist in the thief repository, so the suite died at import (exit code 2, not a test failure). The working tree holds both roles and therefore **structurally cannot** reproduce a split-only failure.
  - **The pattern to follow:** never name a role directory literally in a test. Derive it from `tests/paths.PRESENT_ROLES` / `role_dir()`, and mark cross-role comparisons with `@BOTH_ROLES` so they skip where only one role ships.
  - Now runs automatically as the last gate in `scripts/ship.py`, so it cannot be forgotten. It is *not* in `ci.yml` — CI already runs inside a split repository, where there is nothing left to split.
- [x] 1.QG.4 [D] - **Milestone M1 observed** | DoD: Two agents move legally on a 7×7 grid; a 15th barrier is rejected; coordinate overlap triggers capture. Behaviour *seen*, not merely coded.
  - `uv run python scripts/demo_m1.py` — plays all three scenarios against the **real** engine (no mocks, no doubles) and prints the board after every turn. Added `core/ui/render.py` for plain-text boards; it stays useful after the Tkinter GUI lands, for reading a failed match out of a log.
  - The demo prints the **config digest** it ran under, so what you watched is provably what was signed.
  - Guarded by `tests/integration/test_demo_m1.py` (5 tests). A demonstration nobody executes rots within a week, and this one is the evidence for a milestone — so a domain change that breaks it now fails the suite instead of being discovered when someone tries to show it working.
  - Also the first genuine end-to-end exercise of the layer: config load → board → movement → barriers → rules → scoring, through the real entry points.
  - 🧑 **USER ACTION — run it yourself.** ✅ **Done 31/07.** Diana ran it and questioned scenario 2, which was right to question — see below.
  - **Scenario 2 was rewritten after that first run.** The original spent the quota by teleporting the Cop to each of the 14 cells, which rendered as `C` sitting inside a wall (`# # # # # # C`). Placing on your own cell *is* legal (Ch. 3.4 allows «התא שבו הוא עומד»), so the state was not illegal — but it was **unreachable by legal play**, and a demo whose whole job is to make behaviour trustworthy must not show a board no game could produce. The Cop now patrols row 1 and walls the rows above and below, one legal turn at a time.
  - The rewrite made the scenario say something the old one could not: **14 walls cost 26 of 35 turns, leaving 9 to chase.** That is the `PARAMETERS.md` §4.1 argument — the scarce resource is turns, not barriers — visible on screen instead of asserted in a document.
  - Two bugs surfaced in the rewrite and were fixed: the route only placed 12 barriers, and the "15th placement" was refused for `ALREADY_BLOCKED` rather than `QUOTA_EXHAUSTED`, so it was not demonstrating the quota at all. It now targets a free adjacent cell, so the refusal can only be about the quota. Three further tests pin all of this.

---

## Phase 2: FastMCP Infrastructure (Layer 2)
**Priority:** P0 | **Status:** ✅ Complete — M2 observed 31/07 on Diana's machine | **Target:** 2 Aug
**DoD:** Two fully separate processes exchange a geometric message over localhost and decode it
correctly; the Orchestrator is the only inter-module path; no import path joins the live roles.

### 2.1 Protocol contracts
- [x] 2.1.1 [D] - `core/protocol/schemas.py` — message dataclasses | DoD: Commit, Ack, Reveal, FinalReveal, CaptureClaim, BarrierDeclaration, Negotiation all defined. **CaptureResponse added** — the claim and the answer are separate messages, and M#21 binds the answer.
  - `KIND` is a `ClassVar`, not a field, so a `Commit` can never be constructed calling itself a `Reveal`. The wire still carries an explicit tag, added in `payload()`, so a receiver never infers the type from its shape.
  - `payload()` converts tuples to lists, because JSON has no tuple: a peer that received a message and re-serialised it would otherwise hash different bytes from the peer that sent it. Tested by round-tripping through `digest()`.
  - Every message carries its own `step` and `role`. A payload that cannot say which turn it belongs to cannot be audited, and replaying an old step is the cheapest attack available.
- [x] 2.1.2 [D] - `core/protocol/tools.py` — one factory per MCP tool | DoD: Factory pattern; a new tool needs one factory + one registration line. — 6 factories in `TOOL_BUILDERS`, asserted by test.
  - **Nothing in this layer imports FastMCP.** Each factory takes a handler and returns a plain callable, so the whole protocol is testable with no server, socket or event loop. The transport never learns the rules.
  - Every tool validates before delegating, and raises `ProtocolError` — distinct from a transport failure, because a dropped connection is bad luck and a malformed payload is the opponent's bug. With no referee, *"your step 7 commit arrived with no digest"* is the entire remedy available to us, so it has to be quotable.
  - [x] 2.1.2.a [D] - `receive_commit(hash, step)` | DoD: Stores the hash, returns an acknowledgement.
  - [x] 2.1.2.b [D] - `acknowledge(step)` | DoD: Confirms the opponent is locked. — returned by `receive_commit` rather than a separate round trip.
  - [x] 2.1.2.c [D] - `receive_reveal(move, hint, intent, step)` | DoD: Nonce **not** accepted at this stage. (M#18) — a payload carrying `nonce` is **actively rejected**, not merely ignored.
  - [x] 2.1.2.d [D] - `final_reveal(nonces)` | DoD: Accepted only at end of match.
  - [x] 2.1.2.e [D] - `capture_claim()` / `capture_response()` | DoD: Truthful answer required. (M#21)
  - [x] 2.1.2.f [D] - `declare_barrier(cell)` | DoD: Exact cell declared. (M#15) — a malformed cell is refused; a declaration that cannot be read is not a declaration.
  - [x] 2.1.2.g [D] - `negotiate(config_hash, game_count, scent_model_hash)` | DoD: Handshake payload complete. (M#37) — also carries `role_split` (C-011) and a `readings` map for the C-006 / C-010 mechanism choices, so every open reading is signed rather than assumed.
- [x] 2.1.3 [D] - `core/crypto/commitment.py` — pulled forward, since the schemas are meaningless without it | DoD: `seal()` / `verify()` over `SHA256(state ‖ move ‖ intent ‖ nonce)`; 100 % covered.
  - Tests are written as the three attacks the scheme exists to stop: **no time travel** (the state is in the hash, so a step-4 commit cannot be replayed at step 9), **no revision** (a changed move or intent fails), **no dictionary attack** (20 seals of the same move produce 20 digests).
  - `secrets`, not `random` — a predictably seeded generator would let an opponent reproduce every nonce in the match.
  - `commitment_payload()` is a single named function so the hashed field set can never drift between the peer that seals and the peer that verifies.

### 2.2 Transport
- [x] 2.2.1 [D] - `core/infra/mcp_server.py` — FastMCP server per peer | DoD: Tools registered via `@mcp.tool`; binds `0.0.0.0` so a tunnel can reach it. (Ch. 2)
  - Split into `build_server_spec()` (pure, testable) and `create_server()` (touches FastMCP). The FastMCP import is **lazy**, so every test in this layer runs with no server, socket or event loop — asserted by a test that reads the source.
  - `LISTEN_HOST = "0.0.0.0"` with the reason recorded next to it: a tunnel forwards to the host interface, so a server on loopback is reachable from the same machine and nowhere else. That failure surfaces only when a real opponent connects.
  - `_wrap()` converts a `ProtocolError` into a structured reply instead of letting it escape. Their malformed payload is not our crash — as a traceback it would hand the opponent a stack trace and leave our log with nothing. A test confirms genuine bugs still raise.
- [x] 2.2.2 [D] - `core/infra/mcp_client.py` — client addressing exactly **one** opponent URL | DoD: No code path can reach a second peer; a deadline is attached to every call.
  - 🔴 **Rewritten 31/07 — the first version was not MCP at all.** It posted plain JSON to `/tools/<name>`, which no FastMCP server answers. Every unit test passed because they mocked HTTP. Caught by the 2.4.2 round trip; see that entry for the full account.
  - **M#4 is enforced structurally, not by convention.** The URL is a frozen constructor field and *no method takes a URL*. A test walks every public method's signature and fails if any accepts `url`/`host`/`peer`/`target`, so a second opponent is not something this class can be persuaded into.
  - `timeout_sec` is a constructor field too, so a call cannot be made without a deadline. Ch. 8.4.1: a request with no deadline is the direct route to a frozen loop, a fired watchdog and a technical loss worth 0 to **both** teams.
- [x] 2.2.3 [D] - Structured error handling: auth failure, transport failure, timeout | DoD: Each raises a distinct typed exception, never a bare `Exception`.
  - Four types, and the distinction decides what the runtime does next: `AuthError` **never** retry (that hands a stranger a second attempt) · `TransportError` retry within the backoff budget · `DeadlineError` **never** retry (the window is spent; another attempt walks into the watchdog) · `RemoteToolError` the network worked and our payload did not, so the opponent's detail is preserved verbatim.
  - Tested through `httpx.MockTransport` rather than live sockets — the whole request path runs, headers and timeouts included, with no port to make the suite flaky.

### 2.3 Runtime skeleton
- [x] 2.3.1 [D] - `core/runtime/orchestrator.py` — single gateway to all five subsystems | DoD: No peripheral module imports another; verified by an import-graph test. (M#3) — the graph test itself is 2.4.1, still open.
  - Everything is built from the signed config — board size, start positions, terminal conditions, scoring. No literals, so what we play is provably what was agreed.
  - `connect()` **refuses a second opponent** rather than replacing it silently (M#4). Silent replacement would let a second peer take over a match already in progress.
  - `advance()` is the only way state changes, and it keeps the previous state. A transition that bypassed it would be invisible to the replay audit.
- [x] 2.3.2 [D] - `core/runtime/peer_runtime.py` — negotiate → turn loop → audit | DoD: Runs exactly one role, chosen by CLI flag. — the **receiving** half; the turn loop needs a strategy and lands in Phase 3.
  - **The ordering gate is the point.** A reveal with no matching commit is refused: accepting one would let the opponent see our move and then choose theirs, which is the single failure commit-reveal exists to prevent.
  - Also refused: anything before the handshake agreed (M#11) · a second commit or reveal for a step already recorded · a message claiming **our own role** (otherwise we can be fed our own commitments and record them as theirs) · a barrier declared by the thief (Ch. 3.4) · a final reveal missing any committed step, since an unverifiable step is treated as forgery.
  - A digest mismatch **refuses the match**. Two peers enforcing different physics produce a game the audit reports as forgery against two honest teams.
  - `on_capture_claim` answers from the rules engine, never from what is convenient (M#21). A false denial is caught by the audit without exception.
- [x] 2.3.3 [D] - `core/sdk/peer_sdk.py` — the single public facade | DoD: `grep -r "from core.domain" core/ui/` returns nothing. (X §4.1) — checked by a test that reads every file under `core/ui/`.
  - `BoardView` is flat plain types only. A UI holding a live `GameState` would keep a reference to a position the engine has already replaced, and would render last turn while claiming to show this one.
  - Exposes `own_room()` and `own_exits()` deliberately: those are the numbers that decide whether a barrier is safe to place.
- [x] 2.3.4 [D] - CLI entry point: `uv run python -m core peer --role police|thief` | DoD: Two separate OS processes, two separate config dirs. (M#1, M#4)
  - `--role` is **required with no default**. A process that guessed its own role could be started twice as the same side, and the resulting match would be unauditable.
  - Asking a published repository for the role it does not ship fails with a message saying so, rather than a missing-file error three frames deep.
  - Verified live: the cop reports 3 legal moves from its corner, the thief 5 from the centre, and both print the same config digest.

### 2.4 Separation enforcement
- [x] 2.4.1 [D] - `tests/integration/test_process_separation.py` | DoD: Asserts no module reachable from `police/` imports anything under `thief/`, and vice versa. (M#2) — 9 tests over the **real** parsed import graph, not a grep.
  - Also enforces M#3: a peripheral subsystem (`protocol`, `infra`, `ui`) may reach the foundations (`domain`, `shared`, `crypto`) but **never sideways**; only the gateway (`runtime`, `sdk`, `__main__`) may join two.
  - ⚠️ **It immediately caught a real violation:** `core.infra.mcp_server` imported `core.protocol.tools`. A transport that knows the rules is exactly the sideways edge M#3 forbids. Fixed by moving the error guard into `core/protocol/tools.py` as `guard()` / `build_guarded_tools()`, so the server now takes plain callables and imports nothing from the protocol. The gateway does the wiring, in `PeerSDK.server_spec()`.
  - Two tests guard against the check becoming vacuous: one asserts downward edges *do* exist, one asserts the graph is non-empty. A separation test that silently walked nothing would pass forever.
  - `build_graph()` gained a `packages` argument. The graph now covers shipped code only — tests reach across subsystems on purpose, so including them makes it not an architecture graph. Side effect: the walk went from **23 s to 0.9 s**.
- [x] 2.4.2 [D] - `tests/integration/test_localhost_roundtrip.py` | DoD: Spawns both peers as subprocesses; a message from A decodes correctly at B.
  - 🔴 **This test found the worst bug in the project so far, and it is worth recording why.** The 2.2 client posted plain JSON to `/tools/<name>`. All 22 of its unit tests passed — they mocked HTTP, so they proved the mock worked. **FastMCP speaks JSON-RPC over streamable HTTP, so no opponent's server would ever have answered us.** The two peers would simply have failed to connect on match day, and nothing short of an exchange over the genuine protocol could have shown it.
  - `OpponentClient` now uses `fastmcp.Client`. `call()` is async, and a `transport` field accepts an in-process FastMCP server — which is what makes a genuine protocol round trip testable with no socket, and will also drive self-play.
  - All exception classification moved into one `classify()` function, so a new failure mode has exactly one place to be mapped instead of being absorbed by whichever `except` was nearest.
  - 10 tests over the real protocol: commit → ack, two full commit/reveal turns, geometry surviving the encoding (C-010), barrier declaration (M#15), out-of-order reveal refused, nonce-in-reveal refused (M#18), handshake match and mismatch (M#11), a real transport failure arriving typed, and every tool actually reachable via `list_tools`.
  - **Deviation from the DoD, stated plainly:** this uses FastMCP's in-process transport rather than two OS subprocesses. Everything except the socket is the production path — real server, real client, real protocol, real registration. Two genuine processes over a real port is **2.QG.4** — which turned out to need only two terminals on one machine, not a second machine. Splitting it that way avoids a flaky port-binding test in CI while still proving the protocol works.

### ✅ Phase 2 Quality Gate
- [x] 2.QG.1 [D] - `uv run ruff check .` | DoD: 0 violations. — gate 1 of `ship.py`, so it cannot regress unnoticed.
- [x] 2.QG.2 [D] - `uv run python scripts/check_file_size.py` | DoD: No file over 150 LOC. — gate 2 of `ship.py`.
- [x] 2.QG.3 [D] - `uv run pytest --cov` | DoD: All pass; coverage ≥85 %. — **486 pass, 95.46 %.**
- [x] 2.QG.4 [D] - **Milestone M2 observed** | DoD: A message leaving peer A over localhost is received and decoded correctly at peer B, in two separate terminals. — **observed 31/07 on Diana's machine.**
  - `uv run python -m core peer --role thief --serve` in one terminal, `--role police --handshake --opponent http://127.0.0.1:8082/mcp` in the other. Two OS processes, two config directories, a real uvicorn server and a real `fastmcp.Client` over TCP. Negotiate agreed on `629839fe...`, the commit was acknowledged, the reveal returned `{'received': True, 'step': 0}`.
  - ⚠️ I had told Diana this gate needed Itay's machine. **Wrong** — the DoD says *localhost, two terminals*, which is one machine. A second machine is only needed to prove an *opponent's independently written code* interoperates, which is the warm-up match (0.3.2), not this.
  - Added `--serve`, `--handshake` and `--port` to the CLI to make the gate runnable at all.

### 🔎 Findings from the M2 server log — Diana sent the raw output, which is the only reason these were caught
- [x] 2.5.1 [D] - Strip the trailing slash from the opponent URL | DoD: `OpponentClient.target` normalises `/mcp/` to `/mcp`; unit-tested.
  - The log showed a **307 Temporary Redirect before every single 200**. FastMCP serves at `/mcp`, so `/mcp/` cost an extra round trip on every request. Invisible on localhost; against a real opponent it doubled the network cost of every message inside a 30-second budget. Confirmed fixed on Diana's machine: the second log is all 200s.
- [x] 2.5.3 [D] - Exit quietly on Ctrl-C | DoD: `server stopped.` instead of a ten-frame asyncio/anyio traceback.
  - Ctrl-C is the *normal* way to stop a server. A tool that prints a frightening traceback during routine use teaches whoever is watching to ignore tracebacks — the habit that hides a real one mid-match.
- [x] 2.5.2 [D] - **Decision: keep one MCP session per call.** Reviewed 31/07, no code change. | DoD: the reasoning is recorded and the trigger for revisiting is written down.
  - This is a **decision, not pending work**. Nothing is blocked and nothing is half-finished; the current behaviour is what we intend to ship unless 2.5.4 says otherwise.
  - **My original justification for changing it was wrong, and Diana caught it by asking what the rulebook actually says.** I claimed our Gatekeeper's DOS detector (M#29) would lock the pipe on this pattern. It would not: Ch. 9.3 figure 13 shows the pipeline as `Outgoing report → Quota Manager → Token Bucket → DOS Detector → **Gmail API**`, and its stated purpose is «מונע השעיית החשבון בידי ספק השירות». It guards **outgoing email and LLM calls**, never peer MCP traffic. Nothing in the Gatekeeper ever sees an opponent request.
  - **The rulebook is silent on MCP connection lifecycle** — no session rule, no keep-alive, no reuse requirement. The only related mandates are the Deadline Tracker (Ch. 8.4.1, already satisfied) and the Watchdog (Ch. 8.4.2). The one weak signal is the book's own watchdog example calling `controlled_shutdown()  # release MCP connections, close logs` — you cannot release what you never held — but that is a comment in an example, not a rule.
  - **Reusing a session is a trade, not a win.** A session per call is *more* resilient: each call reconnects, so a dead connection heals itself. A persistent session adds a stale-session failure mode needing reconnect logic. Six requests per message is the price of that resilience, and resilience is worth more than speed when a frozen turn is a technical loss worth 0 to both teams.
  - **What remains true:** six round trips instead of one inside a 30 s budget. Negligible on localhost; roughly 1.2 s vs 0.2 s per message over ngrok at ~200 ms a trip. Real, nowhere near fatal.
- [ ] 2.5.4 [D] - Measure per-message latency over a real tunnel ⏰ **do this during the warm-up match (0.3.2)** | DoD: median and worst-case seconds per game message recorded in `LEAGUE_LOG.md`.
  - **The only thing that would reopen 2.5.2.** Trigger to act: worst-case per-message latency above ~5 s, i.e. a sixth of the 30 s response budget spent on transport alone. Below that, leave it.
  - Costs nothing extra: the warm-up match has to happen anyway, and the numbers come from the server log we already print.

---

## Phase 3: Baseline Strategy (Layer 3)
**Priority:** P1 | **Status:** In Progress ⏳ (3.1–3.4 done; 3.5 self-play next) | **Target:** 3 Aug
**DoD:** Given a known target, the agent computes and walks the shortest legal path unaided.

- [x] 3.1.1 [D] - `core/domain/brain_base.py` — abstract `BrainBase` | DoD: `_pick_move(observation)` abstract; `decide()` overridable for the Cop's barrier choice. (Appendix F §5)
  - **`Observation` deliberately excludes the opponent's position.** In a real match nobody has it. Passing it here would produce a strategy that wins in self-play and collapses against a real peer — and we would not find out until a graded match. A test asserts the field does not exist.
  - `Decision.__post_init__` refuses a decision that moves *and* places a barrier. Ch. 3.4 makes them mutually exclusive, so an illegal combination is unconstructable rather than caught later.
  - `most_likely_opponent()` breaks ties on coordinates, not dict order, so two peers replaying the same belief reach the same cell. Order-dependent ties would make a log unverifiable.
- [x] 3.1.2 [D] - Brain loading from `[strategy] police_class` / `thief_class` in `package.module:Class` form | DoD: Empty section falls back to the built-in baseline; a bad path raises at startup, not mid-match. — `core/runtime/brain_loader.py`, loaded eagerly in `PeerSDK.__init__`.
  - Four distinct failures, each named: malformed path, missing module, missing class, not a `BrainBase`. All raise `BrainLoadError` **at startup**, where the only cost is a message — a typo discovered on turn one is a technical loss worth 0 to both teams.
- [x] 3.2.1 [D] - `police/brain.py` baseline — BFS shortest path to a known target | DoD: Respects barriers and bounds; deterministic on a fixed board. — plus `core/domain/pathfinding.py` (`shortest_path`, `distance_map`, `first_step_towards`).
  - **Places no barriers, on purpose.** A baseline that walled badly could strand itself (see `connectivity.py`), and every later A/B would then be measuring "better than a self-trapping cop" — not a useful floor. Barrier strategy arrives in Phase 4 with the belief filter that makes it safe.
  - Holds position when it believes nothing, and says so when the thief is unreachable. Walking into a wall repeatedly would hide a lost sub-game in the log.
- [x] 3.2.2 [I] - `thief/brain.py` baseline — distance maximisation | DoD: Never voluntarily enters a cell with no exit other than the one it came from. — **written by [D] rather than [I]**, so Itay is not blocking Phase 3; his review still wanted.
  - Scored on three keys in order: **not a dead end** (the DoD), then distance, then **region size**. Raw distance alone would send the thief into a large-looking corner a single wall can seal — space matters more than metres.
- [x] 3.3.1 [D] - Wire the brain into `PeerRuntime` between hint-decode and commit-pack | DoD: Exactly the insertion point Ch. 6 specifies; verified by a call-order test. — `PeerRuntime.observe()` / `.decide()`, tested in `tests/unit/test_brain_seam.py`.
  - `belief()` returns a **uniform** posterior for now. A placeholder with the right *shape*: Phase 4 replaces the contents with the Bayesian update and no brain has to change, because the type it already consumes is correct.
- [x] 3.3.2 [D] - Guard: the LLM is never consulted for a movement decision | DoD: An architecture test asserts no import of `core.infra.llm` from any brain module. (M#25)
  - Three graph tests: no brain reaches anything matching `llm|groq|ollama|anthropic|openai`; no brain reaches `core.infra` or `core.protocol` (a strategy that could send its own messages could bypass commit-reveal); and a third asserting both brains are actually **in** the graph, so the first two cannot pass by inspecting nothing.
- [x] 3.4.1 [D] - Unit tests for both baselines | DoD: Fixed-board scenarios with asserted move sequences. — 27 tests in `tests/unit/test_brains.py`, including a full six-move corner-to-centre walk and a determinism check running each brain 25 times on one observation.

### 3.5 Self-play harness — **moved here from Phase 8**
Strategy is the grade, and you cannot tune what you cannot measure. Every change from this point on
is A/B'd against the baseline rather than trusted. Costs nothing: no MCP, no LLM, no tokens.

- [x] 3.5.1 [D] - Headless match runner: engine + two brains in one process, no network, no LLM | DoD: 100 sub-games complete in seconds; seeded and reproducible. — `core/runtime/selfplay.py` + `scripts/selfplay.py`.
  - **It is not a referee.** It applies the same `core.domain` rules both peers enforce independently. Rules of its own would make every measurement meaningless.
  - Both agents decide **simultaneously**, as commit-reveal requires. Deciding sequentially would let the second brain react to the first and quietly inflate whichever role moved last.
  - `_uniform_belief()` is deliberately identical to `PeerRuntime.belief()`, and a test asserts the harness and the live runtime build the same observation. A harness that fed brains better information than a real match provides would measure a strategy nobody can play — and we would find out in a graded match.
- [x] 3.5.2 [D] - Per-turn ASCII board render | DoD: Shows positions, barriers, belief peak, thief exit count. Watchable in the terminal, free. — `scripts/selfplay.py --show`, reusing `core/ui/render.py`.
  - Prints **both sides' reasons** under each board, so a surprising game explains itself instead of being an unmotivated sequence of moves.
- [x] 3.5.3 [D] - A/B report: win rate by role, steps to capture, captures per barrier spent, which win condition fired | DoD: Printed as a table. — `scripts/selfplay.py --games N`.
  - Scores through `core.domain.scoring`, so the table is tied to Appendix F rather than inventing its own arithmetic.
  - No seed recorded because **nothing is random yet** — both baselines are deterministic and a batch of 20 produces 20 identical games. A seed will be needed the moment a tactic samples anything; noted rather than faked.
- [x] 3.5.4 [D] - **Cop self-separation counter** | DoD: Reports how often the cop stranded believed thief-mass outside its own component. **Must be 0.** (PRD advanced §3.2) — reported per batch and printed as a loud warning when non-zero.
  - Currently 0 trivially, because the baseline places no barriers. The counter exists **now** so that the moment barrier strategy arrives, a self-trapping cop appears as a number rather than as a mysterious run of losses.
- [ ] 3.5.5 [D] - Ablation switches for each tactic | DoD: Any tactic can be toggled off from config, so its contribution is measurable in isolation. — **deferred to Phase 4, honestly: there are no tactics to ablate yet.** Building switches for behaviours that do not exist would be scaffolding around nothing. `scripts/selfplay.py --cop/--thief` already swaps whole strategies, which is the coarse version.

### 📊 First measurement — the baseline is not a pursuit strategy
Twenty sub-games, baseline against baseline:

| metric | value |
|---|---|
| cop win rate | **0.000** |
| mean steps | 35.0 |
| barriers spent | 0 |
| cop separations | 0 |
| cop / thief points | 100 / 200 |

**This is the harness working, not failing.** With a *uniform* belief the cop has no information: every cell is equally likely, so the "peak" is an artefact of tie-breaking rather than a sighting. It walks to a corner and waits while the thief runs out the clock.

The number says plainly where the cop's grade actually comes from — the **belief filter in Phase 4**, not from pathfinding. `test_the_baseline_cop_does_not_yet_catch_the_thief` records it as a test, so when the belief filter starts working that test fails and we notice.

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
- [ ] 4.1.6 [D] - Scent field **transmission** (not sampling) | DoD: Our field is sent inside each turn message and the opponent's is merged on receipt. `scent_field_includes_current_turn` default `true`, matching the reference. Uncertainty survives because both peers then move again, leaving ≤5 candidates. See CONTRADICTIONS C-005.
- [ ] 4.1.7 [D] - `decay_model` config key: `multiplicative` (book, default) and `subtractive` (reference) | DoD: Both implemented. At ρ=0.10 the book gives 0.9→**0.81**, the reference 0.9→**0.80** — the M#23 worked example catches the mismatch before a move is played. See CONTRADICTIONS C-007.
- [ ] 4.1.8 [D] - **Seal a digest of our emitted scent field** in the per-step commit payload | DoD: The reference leaves `smell_grid` outside the seal, so a fabricated field passes audit undetected. We close it on our side regardless of what the opponent does. See CONTRADICTIONS C-008.
- [ ] 4.1.9 [D] - Residual emission recovery | DoD: Implemented under both decay models — strongest available signal, and both sides can compute it.

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
- [ ] 7.1.5 [D] - Queue rather than error when the bucket is full | DoD: A saturated limiter blocks the caller until a slot frees; it never raises. Erroring is indistinguishable from a forfeit, and demand (~0.5 RPM) is 60× below the 30 RPM budget, so this path should never fire in a real match. (`REFERENCE_PERFORMANCE_NOTES.md` §5)
- [ ] 7.1.6 [D] - Startup check: metered provider ⇒ `every_n_steps ≥ 3` | DoD: With `provider` in {`groq`, `claude_api`, `claude_cli`} and `every_n_steps < 3`, startup refuses with a message naming both keys. `template` and `ollama` are exempt — they spend zero tokens, so 1 is correct there and gives the richest verbal game.
  - **Why a check and not a comment:** at `every_n_steps = 1` a 6-sub-game series makes 210 model calls instead of ~70 (~52k tokens on a paid tier). The safe value depends on the provider, and the provider is set per machine in `.env` — so the two can drift apart silently on someone else's laptop. See `REFERENCE_PERFORMANCE_NOTES.md` §2.
  - Retry budget must stay inside the response timeout: 3 × 5 s backoff + request time < 30 s. A fourth retry would not fit, which is why `max_retries` stays at the Appendix F minimum.

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
**DoD:** The advanced brains beat the Phase 3 baselines in ≥70 % of self-play sub-games, measured on
the harness built at 3.5.
**This is where the league grade lives.** See `PRD_strategy_advanced.md`.

### 8.1 Cop — the role that breaks ties
Between two competent teams every sub-game ends in survival, the series ties, and each takes 2.
The cop carries a 15-point spread against the thief's 5, and is the only role that can win outright.

- [ ] 8.1.1 [D] - Expectimax over the belief map, depth 2–3 | DoD: Beats the baseline cop; completes well inside the 30 s step deadline.
- [ ] 8.1.2 [D] - **Connectivity constraint** replacing the old mobility guard | DoD: Hard penalty ∝ believed thief-mass outside `component(cop)`. **Co-confinement is rewarded, not rejected** — sealing yourself in with the thief is the winning move. (PRD advanced §3.2)
- [ ] 8.1.3 [D] - Reward shrinking the **shared** component | DoD: `−β·|component containing both|`; smaller is better.
- [ ] 8.1.4 [D] - **Wall-behind-yourself rule** | DoD: A placement that puts the wall between cop and thief is rejected. Sealing the thief away from you guarantees its survival.
- [ ] 8.1.5 [D] - Diagonal minimum cuts | DoD: Placements extending a diagonal chain are preferred — a diagonally-connected wall cannot be crossed on a 4-connected grid, so it is the cheapest cut. 4 barriers seal a 6-cell corner.
- [ ] 8.1.6 [D] - Cycle elimination as the barrier objective | DoD: Prefer placements that destroy cycles. A region the thief can circle is a region it survives in.
- [ ] 8.1.7 [D] - **One-placement rule** | DoD: Reject any cut that cannot be completed with one further placement. Each placement gifts the thief a free step, so a two-barrier seal leaks.
- [ ] 8.1.8 [D] - **Win condition: drive thief exit count to 1 while adjacent to that exit** | DoD: The evaluation targets this state explicitly, not generic region shrinkage.
- [ ] 8.1.9 [D] - Three-phase plan: herd (0 barriers) → seal → squeeze | DoD: Transitions driven by measured state — thief edge-adjacency, exit count, belief entropy — never by turn number.
- [ ] 8.1.10 [D] - Opponent-type gate on the phasing | DoD: Flee-greedy thief → chase, no early barriers (the board's edges corner it for free). Orbiting thief → spend barriers early to cut the cycle.
- [ ] 8.1.11 [D] - Entropy-aware pursuit on a multimodal posterior | DoD: Chooses the information-revealing move over the argmax chase.
- [ ] 8.1.12 [D] - No barrier while belief entropy is high | DoD: A barrier placed where the thief probably is not can open a route *for* it.

### 8.2 Thief — full tactic set, value measured not assumed
Retained in full. Whether each tactic earns its keep is settled by ablation (8.3.4), not by prior belief.

- [ ] 8.2.1 [I] - Escape-route maximisation under the belief map | DoD: Beats the baseline thief.
- [ ] 8.2.2 [I] - **Never let exit count reach 1** while the cop is within placement range | DoD: The mirror of the cop's win condition; the single most valuable line in the thief's evaluation.
- [ ] 8.2.3 [I] - Scent-aware movement — own emission treated as a cost | DoD: Avoids lingering in cul-de-sacs where re-emission plateaus at full strength.
- [ ] 8.2.4 [I] - **Cycle preservation** | DoD: Prefers regions that still contain a cycle; tracks the cop's remaining barriers as the measure of how many cycles it can still destroy.
- [ ] 8.2.5 [I] - False-anchor tactic | DoD: Lay a strong trail, then break away. Triggered only when estimated payoff exceeds the turns spent.
- [ ] 8.2.6 [I] - Measure the false anchor | DoD: Survival rate with and without, against **both** the baseline cop and our own advanced cop. Adopted for graded matches only if it wins.

### 8.3 Shared
- [ ] 8.3.1 [D] - **Unexploitable default** | DoD: Near-ties resolved by a seeded random choice (seed logged); no fixed lie schedule; no rhythmic movement pattern. Unexploitability is the floor, exploitation is upside.
- [ ] 8.3.2 [D] - Opponent profiling — **at most 4 traits, confidence-gated** | DoD: Barrier rate (public under M#15), flee-greediness, hint-responsiveness, reliability `r`. Below the confidence threshold, behaviour stays on the unexploitable default. ~200 steps per series cannot support more without fitting noise.
- [ ] 8.3.3 [D] - Profile resets between opponents | DoD: Accumulates across the 6 sub-games of a series; cleared for a new team, since teams may change code between matches.
- [ ] 8.3.4 [D] - **Cheap-truth bluff policy** | DoD: Compute the hint's information value beyond what our scent already reveals. Low → tell the truth free and bank credibility. High → consider a lie weighted by credibility banked. As cop, spend it in Phase A to herd.
- [ ] 8.3.5 [D] - Disable the verbal layer when hint-responsiveness ≈ 0 | DoD: An opponent who ignores hints makes the tokens pure waste.
- [ ] 8.3.6 [B] - Self-play benchmark on the 3.5 harness | DoD: ≥100 sub-games, both roles, seeded; adopt only on ≥70 % against the control.
- [ ] 8.3.7 [D] - Unit tests for every scoring heuristic | DoD: Deterministic on fixed boards; coverage ≥85 %.

### ✅ Phase 8 Quality Gate
- [ ] 8.QG.1 [B] - `uv run ruff check .` | DoD: 0 violations.
- [ ] 8.QG.2 [B] - `uv run python scripts/check_file_size.py` | DoD: No file over 150 LOC. Brains grow fastest — split search, evaluation and policy.
- [ ] 8.QG.3 [B] - `uv run pytest --cov` | DoD: All pass; coverage ≥85 %.
- [ ] 8.QG.4 [B] - Self-play benchmark | DoD: Advanced brains win ≥70 % against the baselines; **cop self-separation rate is 0**.

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
- [ ] 9.1.6 [B] - **Agree the capture-resolution clause in writing** | DoD: M#46 timing, M#47 vs STAY, and the swap case all settled before the first move. With no referee, a disagreement found mid-match is unresolvable and can void the result for **both** teams (M#35). See PRD_negotiation §3.6.
- [ ] 9.1.7 [B] - **Agree the scent sampling mode** | DoD: `end_of_previous_full_turn` proposed; recorded in the config JSON as part of the M#23 exchange. See CONTRADICTIONS C-005.
- [ ] 9.1.8 [B] - **Confirm the role split across the series** | DoD: How the 6 sub-games divide between cop and thief. Do not assume 3/3 — the scoring analysis depends on it.

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
