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

### 🧑‍🤝‍🧑 ITAY — START HERE (added 02/08)

> **Do these five in order. Steps 1–3 are prerequisites for everything else and take under an
> hour; do not skip to Phase 5 without them, because 5.1.1 cannot be tested on a machine whose
> test suite does not run.**
>
> **1. Get the repo running.** Clone `bestteam-cop`, then:
> ```
> uv sync --all-extras --dev
> copy .env-example .env          # PowerShell: Copy-Item .env-example .env
> uv run pytest
> ```
> DoD: **all tests pass** on your machine. If they do not, stop and tell Diana — a difference
> between our two machines is exactly the class of bug that decides a match, and one has already
> bitten us (`update_from_hint` overwrote mass, worked on Linux, failed on Windows).
>
> **2. You do NOT need a Groq API key.** Leave `GROQ_API_KEY` out of your `.env` entirely.
> You run `ollama`; Diana runs `groq`. The provider choice is **private per peer** and never
> negotiated (Appendix F Table 21). Never ask for or accept a copy of her key.
>
> **3. Ollama — this is task 0.2.3, and it is yours alone.**
> ```
> ollama pull llama3.1:8b
> ollama serve
> uv run python scripts/hint_demo.py --provider ollama
> ```
> DoD: it prints `OK - ollama wrote every line`, in under 10 s. That also closes **4.3.3**.
> ⚠️ If it prints `ollama was requested but did NOT write these lines`, the fallback caught an
> error and the run is **not** a pass — the output looks fine either way, which is why the
> verdict line exists.
>
> **4. ngrok — task 0.2.4 + 0.2.6.** Create the account, install, note your permanent
> `*.ngrok-free.dev` domain, and record it in `config/thief/game.toml`. Diana's is already done
> (`customs-countdown-uncork.ngrok-free.dev`). DoD: `ngrok http 8081 --url <your-domain>` works.
>
> **5. Then Phase 5 — `core/infra/tunnel.py` (5.1.1) onward.** That is the real work and it is
> yours: Phase 5 is the only layer that genuinely needs two machines. Diana is on **Phase 6**
> (crypto), which is entirely in-process and does not block you or wait on you.
>
> 🔒 **Never commit `.env`.** Never paste a key or token into chat. A secret sent once is
> permanently exposed (M#39, M#40).

### 0.2 🧑 USER ACTION — External accounts
> **PAUSE — I stop here. These need a browser and your credentials; I cannot do them.**
> **Step-by-step guide: `docs/SETUP.md`. Verify with `uv run python scripts/check_setup.py`.**

- [x] 0.2.1 🧑 [D] - Google Cloud project + Gmail API + Google Auth platform, **send-only** scope `gmail.send` | DoD: `credentials.json` saved **outside** both repos; `check_setup.py` reports Gmail credentials OK. See SETUP 0.2.1. (M#30)
  - [x] 0.2.1.a 🧑 [D] - Create the project and enable the Gmail API | DoD: API shows as Enabled in the console.
  - [x] 0.2.1.b 🧑 [D] - Configure Branding + Audience (**External**), add yourself as a test user, add scope `gmail.send` | DoD: Consent screen saved with exactly one scope. SETUP 0.2.1.b-d
  - [x] 0.2.1.c 🧑 [D] - Create OAuth client ID (**Desktop app**), download `credentials.json` | DoD: **Verified 28/07** — `check_setup.py` confirms a Desktop client at `C:\Users\diana\.p2p-secrets\credentials.json`, outside both repos. SETUP 0.2.1.e-f
  - [x] 0.2.1.d 🧑 [D] - ⚠️ **Publish the app** (Testing → In production) — **confirmed 28/07: Publishing status = In production** | DoD: Audience page reads *In production*. **`check_setup.py` cannot verify this — publishing status is not exposed in `credentials.json` or by any API. Confirm by eye.** **Skipping this makes the refresh token expire after 7 days and silently breaks league reporting mid-project** — an unsent report scores 0 for **both** teams. SETUP 0.2.1.g (M#35)
- [x] 0.2.2 🧑 [D] - Groq API key at console.groq.com/keys | DoD: **Verified 28/07** — `check_setup.py` reports `gsk_xJkR...(56 chars)`.
- [x] 0.2.3 🧑 [I] - Install Ollama and pull a model small enough for the 30 s step deadline | DoD: **Verified 02/08** — `hint_demo.py --provider ollama` printed `OK - ollama wrote every line` on `llama3.1:8b`. Closes 4.3.3. Full suite on Itay's machine: 815 passed, 22 skipped, coverage 92.94 % — no cross-machine divergence. (PRD Q3)
- [x] 0.2.4 🧑 [B] - ngrok accounts + authtokens on both machines | DoD: **Diana verified 28/07** — static domain `customs-countdown-uncork.ngrok-free.dev`. **Itay verified 02/08** — ngrok 3.39.10, `check_setup.py` reports installed and configured, static domain `denotatively-sciuroid-florine.ngrok-free.dev`.
- [x] 0.2.5 [D] - Decide: static ngrok domain or dynamic URLs? | DoD: **Answered — static.** ngrok now assigns every free account a permanent `*.ngrok-free.dev` dev domain, so no paid plan and no per-match URL exchange is needed. Recorded in PRD Q5 and SETUP 0.2.5.
- [~] 0.2.6 🧑 [B] - Note each machine's static ngrok domain in `config/<role>/game.toml` | DoD: **Tunnels verified on both machines 02/08** — `ngrok http 8081 --url <domain>` opens on Diana's and on Itay's (`denotatively-sciuroid-florine.ngrok-free.dev`). Both domains are recorded in the SETUP 0.2.5 table. **Still open:** only Diana's domain is in `config/police/game.toml`; that file is committed with a single value and there is no per-machine override, unlike `P2P_LLM_PROVIDER` which has one in `.env`. Deciding the mechanism belongs to 5.1.1 — the `TunnelManager(domain=...)` argument has to come from somewhere. (PRD 5.10)

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
- [x] 1.3.2 [D] - Truthful barrier declaration in the move record | DoD: Every placement carries its exact cell into the signed record; no hidden placement path exists. (M#15, M#16)
  - [x] 1.3.2.a [D] - Single placement path, cell always carried | DoD: `place()` is the only way a barrier reaches the board, and every result — including every rejection — returns a `Placement` naming the exact cell. There is no API that blocks a cell without producing a declarable record.
  - [x] 1.3.2.b [I] - Wire the declaration into the signed record | DoD: **Done 07/08.** The cell is inside the commit hash as an optional `barrier_cell` key, so a placement cannot be altered after the fact. Six tests: a changed cell fails verification, a walled turn and a still turn seal differently, a turn with no barrier hashes exactly as before, tuple and list cells seal identically, and both log paths (sealed / declared-only) audit clean.
    - **Why it mattered more than the checkbox suggests.** A placement costs the move, so it travels as `STAY` — the four sealed fields of Ch. 5.3.1 could not tell standing still apart from walling a cell. A cop could seal `STAY`, read the thief's reveal, and only then declare which of five adjacent cells it walled, with every step still auditing clean. It is the one move in the game that was still revisable after the fact, and it is asymmetric: the thief has no equivalent.
    - **Presence, not value, is the signal** — the same convention as `scent_digest` (C-008). An ordinary turn hashes byte-identically whether or not either peer implements this, so an opponent who declines is still auditable by our code. Negotiated as **N20**, defaulting on; see CONTRADICTIONS C-018.
    - The log keeps `barrier_cell` for the reader on every placement and `sealed_barrier_cell` only when it went into the hash. Deriving one from the other would make a peer that declares without sealing fail its own audit — legal behaviour, and what an opponent running the plain book does.

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
  - **Confirmed from the book, not inferred:** a technical loss pays **0 to both sides** — Ch. 3.5, *"a technical loss zeroes both sides alike"*, explicitly so that neither side can win by making the other time out. Nothing we build should ever stress an opponent's clock; there is no upside.
  - `score()` **raises** on a `TIE` verdict rather than returning a value. A tie is a series-level result, and quietly returning something for a single sub-game would hide the mistake.
- [x] 1.4.4 [D] - Series aggregation across 6 sub-games, with tie detection | DoD: Equal cumulative totals award `tie_score` to both sides. (F)
  - The tie is decided on **cumulative points**, not sub-games won: 3 captures and 3 survivals is 75-45, not a draw.
  - ⚠️ **New contradiction found while testing — C-013.** A series in which every sub-game ended in a technical loss is also arithmetically level, at 0-0, so a literal reading pays both teams the tie bonus for a series neither played. That inverts the incentive Ch. 3.5 exists to create. We pay the bonus only when at least one sub-game produced a real result. Cheap to raise at negotiation, awkward to argue afterwards.

### 1.4b Connectivity — added 31/07, not in the original plan
- [x] 1.4.5 [D] - `core/domain/connectivity.py` — `reachable`, `are_connected`, `region_size`, `exit_count` | DoD: 100 % covered; the corridor self-trap is a named test case.
  - **Why it was added mid-phase.** Diana looked at the demo's scenario 2 and asked whether the cop realises it is now blocked. It does not — and nothing in the codebase could have told it. Rows 0 and 2 fully walled leaves the cop in a **7-cell corridor** with the thief loose in the other 28. The cop can never reach it again, the thief runs out the clock, and barriers are permanent so nothing recovers it.
  - Ch. 3.4 warns about exactly this — *"without accidentally blocking its own access routes"* — and we had the warning in three documents but no primitive that could enforce it.
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
  - **Scenario 2 was rewritten after that first run.** The original spent the quota by teleporting the Cop to each of the 14 cells, which rendered as `C` sitting inside a wall (`# # # # # # C`). Placing on your own cell *is* legal (Ch. 3.4 allows «the cell it is standing on»), so the state was not illegal — but it was **unreachable by legal play**, and a demo whose whole job is to make behaviour trustworthy must not show a board no game could produce. The Cop now patrols row 1 and walls the rows above and below, one legal turn at a time.
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
  - **My original justification for changing it was wrong, and Diana caught it by asking what the rulebook actually says.** I claimed our Gatekeeper's DOS detector (M#29) would lock the pipe on this pattern. It would not: Ch. 9.3 figure 13 shows the pipeline as `Outgoing report → Quota Manager → Token Bucket → DOS Detector → **Gmail API**`, and its stated purpose is «prevents account suspension by the service provider». It guards **outgoing email and LLM calls**, never peer MCP traffic. Nothing in the Gatekeeper ever sees an opponent request.
  - **The rulebook is silent on MCP connection lifecycle** — no session rule, no keep-alive, no reuse requirement. The only related mandates are the Deadline Tracker (Ch. 8.4.1, already satisfied) and the Watchdog (Ch. 8.4.2). The one weak signal is the book's own watchdog example calling `controlled_shutdown()  # release MCP connections, close logs` — you cannot release what you never held — but that is a comment in an example, not a rule.
  - **Reusing a session is a trade, not a win.** A session per call is *more* resilient: each call reconnects, so a dead connection heals itself. A persistent session adds a stale-session failure mode needing reconnect logic. Six requests per message is the price of that resilience, and resilience is worth more than speed when a frozen turn is a technical loss worth 0 to both teams.
  - **What remains true:** six round trips instead of one inside a 30 s budget. Negligible on localhost; roughly 1.2 s vs 0.2 s per message over ngrok at ~200 ms a trip. Real, nowhere near fatal.
- [ ] 2.5.4 [D] - Measure per-message latency over a real tunnel ⏰ **do this during the warm-up match (0.3.2)** | DoD: median and worst-case seconds per game message recorded in `LEAGUE_LOG.md`.
  - **The only thing that would reopen 2.5.2.** Trigger to act: worst-case per-message latency above ~5 s, i.e. a sixth of the 30 s response budget spent on transport alone. Below that, leave it.
  - Costs nothing extra: the warm-up match has to happen anyway, and the numbers come from the server log we already print.

---

## Phase 3: Baseline Strategy (Layer 3)
**Priority:** P1 | **Status:** ✅ Complete — M3 observed 31/07; ablation switches deferred to Phase 4 | **Target:** 3 Aug
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
  - Scored on three keys in order: **not a dead end** (the DoD), then **safety-adjusted distance**, then region size.
  - 🔴 **Fixed 31/07 after Diana watched a game and said the thief was only running away.** She was right, and the first version was worse than I had claimed: it ran to **(6,6)** — the farthest cell from the believed cop, and also the cell a cop seals with **two** barriers under M#47 — and sat there for 29 turns. Two keys had failed silently: `region_size` is **49 for every cell** on an open board, so it discriminated nothing; and the dead-end veto only fires at *one* exit, so a two-exit corner passed.
  - Fix: `EXIT_WEIGHT = 2` — one missing exit costs two steps of distance. From the centre the thief now prefers (5,5) at distance 10 with four exits over (6,6) at distance 12 with two. Measured after: final cell **(5,5)**, **zero** corner cells entered, mean exits **4.0**. Two regression tests pin it, and the constant is settled properly by ablation in 8.2.6.
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
- [x] 3.QG.1 [D] - `uv run ruff check .` | DoD: 0 violations. — gate 1 of `ship.py`.
- [x] 3.QG.2 [D] - `uv run python scripts/check_file_size.py` | DoD: No file over 150 LOC. — it rejected one of my own test files during this phase; split, not compressed.
- [x] 3.QG.3 [D] - `uv run pytest --cov` | DoD: All pass; coverage ≥85 %. — **535 pass, 95.3 %.**
- [x] 3.QG.4 [D] - **Milestone M3 observed** | DoD: Agent computes and walks the shortest path to a known target with no manual intervention. — `uv run python scripts/selfplay.py --games 20 --oracle --show`.
  - Self-play alone could **not** show this: with a uniform belief the cop has no target to walk to. So the harness gained an `--oracle` flag that collapses the belief to the thief's true cell — a *known* target, exactly what the DoD asks for.
  - Result: **win rate 1.000, capture in a mean of 10 steps**, no manual intervention.
  - **The flag is worth more than the checkbox.** The gap between oracle and normal play — 1.000 against 0.000 — is precisely what a perfect belief is worth. Phase 4's filter is now judged against a measured ceiling instead of an opinion.
  - Guarded: `oracle` is a harness parameter only. `PeerRuntime` has no equivalent, asserted by a test, so a perfect belief can never leak into a real match.

---

## Phase 4: Language & Scent (Layer 4) ⚠️ **HIGHEST RISK**
**Priority:** P0 | **Status:** In Progress ⏳ (4.1 scent + 4.2.1/4.2.3 belief done; language layer next) | **Target:** 4–5 Aug

### 📊 What the belief filter was worth — measured, 20 sub-games, baseline vs baseline
| cop's belief | win rate | mean steps | points |
|---|---|---|---|
| uniform (no information) | 0.000 | 35.0 | 100 / 200 |
| **Bayesian filter** | **1.000** | **14.0** | **400 / 100** |
| oracle (perfect knowledge) | 1.000 | 10.0 | 400 / 100 |

The filter reaches the **oracle's win rate**, paying four extra steps for not knowing exactly where the thief is. That is close to all of the value a perfect belief could offer, and it is the number Phase 4 existed to produce.

`test_the_baseline_cop_does_not_yet_catch_the_thief` was written in Phase 3 to fail the moment this worked. It now reads `test_the_belief_filter_is_what_makes_the_cop_work` — the improvement announced itself instead of being assumed.
**DoD:** Free-text hints drive inference; the scent map updates and decays each step; the belief
posterior shifts measurably; the verbal layer emits a truthful or deceptive hint at ≤15 words.
Most of the schedule slack is allocated here — if anything slips, it slips here.

### 4.1 Scent engine
- [x] 4.1.1 [D] - `core/domain/scent.py` — 5×5 radial emission field, centre τ=0.9 | DoD: Reproduces the rulebook's figure values (0.9 / 0.62 / 0.42 / 0.20 / 0.14 / 0.04). (F)
  - **📐 The exact grid, read off the book's figure (Ch. 4, "5×5 scent emission field, centre τ = 0.9"). Ship this table, not a formula:**
    ```
    0.04  0.14  0.20  0.14  0.04
    0.14  0.42  0.62  0.42  0.14
    0.20  0.62  0.90  0.62  0.20      <- centre = the emitting agent
    0.14  0.42  0.62  0.42  0.14
    0.04  0.14  0.20  0.14  0.04
    ```
  - The values are radial in **squared Euclidean distance** from the centre: d²=0→0.90, 1→0.62, 2→0.42, 4→0.20, 5→0.14, 8→0.04.
  - ⚠️ **The book states no emission formula.** Ch. 4.3 defines `∆τij` only as «determined by the radial proximity of the cell to the centre emission centre» — determined by *radial proximity*, 0.9 at the centre, 0 when far. The figure's 25 numbers are the entire specification. (The **decay** formula *is* stated: `τ(t+1) = max(0, (1−ρ)·τ(t) + ∆τ)`.)
  - A Gaussian `τ = 0.9·exp(−k·d²)` reproduces all six values at k ≈ 0.377 — but that is **my reverse-engineering, not the book's**. It was run as a sanity check that the figure is genuinely radial rather than 25 arbitrary numbers, and it passed. `k = 0.377` appears nowhere in the rulebook and is not used in the code.
  - ⚠️ **Ship the table, because the table is what the book publishes.** M#23 makes the scent model part of the signed agreement, and the exchange is a *worked example* — both peers must produce byte-identical numbers. Shipping a closed form would mean shipping a **reconstruction** of a specification the book never wrote down, and an opponent reconstructing it slightly differently would fail the digest for a reason neither side could find.
  - This also gives 4.1.5 its content: the exchanged payload is these 25 numbers plus the decay model, hashed.
  - ✅ **Built 31/07** in `core/domain/scent.py`. All 25 cells asserted against the figure, not a spot check. Corner emission is **not** clamped — an agent at an edge simply leaves a smaller trail, and a weak edge reading is itself evidence of an edge.
- [x] 4.1.2 [D] - Decay `τ(t+1) = max(0, (1−ρ)·τ(t) + Δτ)`, ρ=0.10 | DoD: A single deposit crosses half-peak around turn 7, as the book states. (F, Ch. 4) — asserted; 0.9 reaches half-peak on turn **7** exactly.
- [x] 4.1.3 [D] - Symmetry: both agents emit; each reads only the opponent's field | DoD: A test asserts an agent cannot sample its own trail. (Ch. 4) — each `Side` in the harness holds its own trail and belief; `observe()` only ever takes the *opponent's*.
- [x] 4.1.4 [D] - Truncation at zero | DoD: Intensity never goes negative. — cells at or below zero are dropped, not clamped. A negative reading would put belief mass on cells the opponent has never visited.
- [x] 4.1.5 [D] - Scent-model exchange payload: formula + a concrete numeric example, hashed | DoD: Both peers agree the digest before the series opens. (M#23) — `core/crypto/scent_model.py`, digest `f9d248c2...`.
  - Carries a **worked example with the number**, not just a model name: `0.90 → 0.81`. A label can be agreed while the arithmetic still differs; a number cannot. If their example says **0.80** they built on the reference (C-007), which tells us both that the model must be settled *and* which implementation we are facing.
  - The emission table travels as `distance² → intensity` rather than 25 cells: same information, half the payload, and a disagreement about one radius is obvious instead of hidden among 25 numbers differing in one place.
- [x] 4.1.6 [D] - Scent field **transmission** (not sampling) | DoD: Our field is sent inside each turn message and the opponent's is merged on receipt. `scent_field_includes_current_turn` default `true`, matching the reference. Uncertainty survives because both peers then move again, leaving ≤5 candidates. See CONTRADICTIONS C-005.
  - 🐛 **This was ticked for a whole phase with nothing implementing it, and it is the most expensive defect the project has had.** `Reveal` carried no scent field, no codec read one, and `PeerRuntime.belief()` returned a uniform placeholder. The consequence is not subtle: a uniform posterior measures **5.61 bits** against `confident_bits = 3.5`, so a live Cop would have sat in HERD for all 35 turns and **never placed a barrier** — which PRD §2.1 calls the only way the Cop can win. Everything Phase 8 built was inert on the wire. Fixed 06/08: `Reveal.scent`, `scent.encode/decode`, and `core/runtime/local_truth.py`.
  - 🐛 **And the harness had been reading the opponent's *current-turn* deposit**, one turn fresher than commit-reveal can deliver: our move for turn *k* is sealed before their reveal for turn *k* arrives, so their field for turn *k* is first usable at turn *k+1*. With both trails in one process nothing stopped it. **Every Phase 8 number was measured through that hole** — see the corrected tables in §8.3.
  - The guard that should have caught it, `test_the_harness_shows_brains_no_more_than_a_real_match_does`, asserted that the live belief was non-empty and summed to 1.0 — true of the uniform placeholder and of every posterior ever. It now runs the shared filter alongside and asserts equality.
  - **One filter now, not two.** `core/domain/filter.py` is used by both the harness and the live runtime, so the two cannot drift again without a test failing.
- [x] 4.1.7 [D] - `decay_model` config key: `multiplicative` (book, default) and `subtractive` (reference) | DoD: Both implemented. At ρ=0.10 the book gives 0.9→**0.81**, the reference 0.9→**0.80**. See CONTRADICTIONS C-007. — both implemented and both tested, so we can play under whichever was signed.
- [x] 4.1.8 [D] - **Seal a digest of our emitted scent field** in the per-step commit payload | DoD: The reference leaves `smell_grid` outside the seal, so a fabricated field passes audit undetected. See CONTRADICTIONS C-008.
  - ⚠️ **Corrected from "regardless of what the opponent does" — that would have been a serious mistake.** The opponent recomputes our digests during the end-of-match audit using *their* payload builder. Sealing unilaterally would make **every digest we ever sent** fail their verification, and the sanction for a mismatch is a total technical loss. Sealing alone is worse than not sealing.
  - So it is **opt-in and negotiated (N13c)**, and "off" means the key is *absent*, not `null`. `test_the_payload_is_byte_identical_when_sealing_is_off` asserts that on the canonical bytes, since those are what get hashed.
- [x] 4.1.9 [D] - Residual emission recovery | DoD: Implemented under both decay models — strongest available signal, and both sides can compute it. — `core/domain/scent_residual.py`.
  - A reading becomes a **timestamp**: not "they were near here" but "they were near here, *n* turns ago".
  - Both models inverted, because C-007 means we may play either. Note the finding: at 0.81 **both return 1 turn**, so a single early reading cannot tell them apart — the divergence only appears further down the curve, by which point the match is already being played on a wrong assumption. That is the argument for settling it at the handshake via the M#23 digest rather than inferring it.
  - Refuses to date a trace older than 25 turns. A confident timestamp on a faded trace is worse than none: it sends the Cop chasing where the Thief *used to be*.

### 4.2 Belief engine
- [x] 4.2.1 [D] - `core/domain/belief.py` — full 7×7 posterior | DoD: Sums to 1.0 within float tolerance after every update.
  - **A distribution, not a point estimate.** "Probably (5,5)", "(5,5) at 0.9" and "(5,5) at 0.11 with everywhere else nearly as likely" call for completely different play, and only a posterior tells them apart.
  - **Prediction runs before the update, always.** The opponent moved since we last looked, so the prior must widen *before* new evidence narrows it. Updating against a stale prior is how a filter becomes confidently wrong.
  - A collapsed posterior falls back to uniform rather than raising: every hypothesis being ruled out is always an error, never a fact — the opponent *is* somewhere — and crashing mid-match is a technical loss worth 0 to both teams.
  - [x] 4.2.1.a [D] - Uniform initialisation | DoD: Each cell 1/49 at step 0. — entropy log₂49 ≈ **5.61 bits**, asserted.
  - [x] 4.2.1.b [D] - Prediction step: motion model, one orthogonal step or stay | DoD: Mass spreads only to legal neighbours. — mass is split **evenly**; weighting one direction would be us inventing evidence we do not have.
  - [x] 4.2.1.c [D] - Update from scent likelihood | DoD: Unit-tested against a worked example from Ch. 4. — one reading takes entropy **5.61 → 0.74 bits** and puts p ≈ **0.905** on the true cell.
  - ⚠️ **Silence is not absence** (Ch. 4's own phrase), enforced in two places: an empty field leaves the belief *untouched*, and a silent cell keeps a floor likelihood rather than being ruled out. A filter that sharpened on nothing would manufacture confidence — and a thief who noticed could walk us into it deliberately. Two tests named for it.
  - [x] 4.2.1.d [D] - Update from hint likelihood, scaled by the reliability coefficient | DoD: A hint contradicted by the scent field moves mass *away* from the claim. — `core/domain/belief_hints.py`. **The scent is a fact; the hint is an argument** — the only channel where the opponent gets a vote on what we believe, so it is the only one scaled by a learned coefficient. Two gates must both open: the parser understood it *and* the record says it is worth something. Tilt is capped at 0.35 so words can never outweigh the scent, and never drive a cell to zero.
  - [x] 4.2.1.e [D] - Mask barriers and own cell, then renormalise | DoD: Blocked cells hold exactly 0. — our own cell too: if the opponent were there the sub-game would already be over.
- [x] 4.2.2 [I] - Per-opponent **reliability coefficient** tracked across the series | DoD: Converges toward 0 against a consistently lying opponent, toward 1 against a truthful one. *(Original extension — README material.)* — `core/domain/reliability.py`.
  - **A Beta posterior, not a running average.** A mean reads 1.00 after one truthful hint — total certainty at exactly the moment an opponent's first claim is least representative, and the moment a clever one would spend a cheap truth to buy it. Beta(1,1) gives **0.67** instead.
  - **A systematic liar is worth more than an honest opponent.** At 0.05, "I am going north" is evidence for *south* — a reliably inverted signal is still a signal. Only a *mixed* record is genuinely worthless, and it correctly sits at 0.5.
  - Updates are weighted by parser confidence, so a deliberately vague opponent cannot dilute their own record.
  - An unverifiable claim returns **None, not False**. Scoring "could not check" as a lie would let a stationary opponent accumulate a reputation they never earned.
- [x] 4.2.3 [D] - `peak`, `entropy` and `normalise` helpers | DoD: Used by the strategy layer and the GUI heatmap. — `peak` breaks ties on coordinates so two peers replaying one log agree; `entropy` in bits is how we report *"the filter works"* without cherry-picking a game.

### 4.3 Natural language — outbound
- [x] 4.3.1 [I] - `core/infra/llm/base.py` — `TextProvider` interface | DoD: One method, `generate(prompt, max_words) -> str`.
- [x] 4.3.2 [I] - `template` provider — pre-written bank, zero tokens | DoD: Default; works fully offline. (F)
- [x] 4.3.3 [I] - `ollama` provider — `localhost:11434` | DoD: **Verified 02/08 on Itay's machine** — three hints written by `ollama` on `llama3.1:8b`, verdict line `OK - ollama wrote every line`. No Groq key present, which is the point: the fallback never fired. See 4.3.4.b.
- [x] 4.3.4 [D] - `groq` provider, routed through the Gatekeeper | DoD: No direct SDK call outside this module; Diana's machine produces a hint. — code complete; the Gatekeeper half is enforced (no key or URL exists outside `core/infra/llm/remote.py`).
  - [x] 4.3.4.a 🧑 **DIANA — DONE 02/08.** Real key in `.env`, verified by running `uv run python scripts/hint_demo.py --provider groq` and reading `OK - groq wrote every line`.
    - ⚠️ **The proof is the run, not the file.** A wrong or placeholder key fails *silently* into the template bank and the output still looks fine. Only the verdict line distinguishes them. Re-run it after any `.env` edit.
  - ❌ **4.3.4.b — ITAY does NOT need a Groq key, and must not be sent one.**
    - Itay runs `ollama`, which is local, free and unmetered — that is exactly why graded matches run on his machine (Appendix F Table 21; the provider choice is private per peer and never negotiated).
    - His `.env` needs no `GROQ_API_KEY` line at all. `OLLAMA_BASE_URL` already defaults to `http://localhost:11434`, so he needs Ollama *installed and running*, not configuration.
    - 🔒 **The key is never shared, never committed, never pasted into chat.** One key, one machine. A secret sent once is considered permanently exposed (M#39, M#40).
    - His check is the same command with a different flag: `uv run python scripts/hint_demo.py --provider ollama`, which also satisfies 4.3.3's "a hint in under 10 s".
- [x] 4.3.5 [I] - Automatic fallback to `template` on **any** provider error or timeout | DoD: Killing Ollama mid-match degrades quality but does not lose the match. (ADR-003)
- [x] 4.3.6 [I] - `every_n_steps` throttle | DoD: LLM invoked every 2–3 turns; other turns use the template bank. — **deliberately set to 1, not 2–3.** The book frames this purely as a token budget (Ch. 6.5.1); `template` and `ollama` spend zero tokens, so there is no budget to protect and 1 buys the richest verbal game. A startup guard (7.1.6) forces it to 3 if a metered provider is ever selected.
- [x] 4.3.7 [D] - Hint word cap of 15, enforced for **every** provider including the LLM system prompt | DoD: An over-long generation is regenerated or truncated at a word boundary. (F)
- [x] 4.3.8 [D] - Outbound coordinate scanner | DoD: Any text containing bare numeric coordinates is rejected and regenerated. Port HW6's `_COORD_RE`. (M#27)
- [x] 4.3.9 [D] - Free natural language enforced — no structured position protocol anywhere | DoD: Architecture test asserts no numeric position field on the hint channel. (M#26)
- [x] 4.3.10 [I] - **Landmarks are OFF unless `map_area` is negotiated** — inverted after a live leak: Groq truthfully said "heading north towards the old warehouse", then on a deliberately-empty hint said "near the old warehouse". No compass word, so every rule passed — but an opponent who paired warehouse↔north on turn 1 reads the second as north anyway. The model had built a **private codebook** out of its own flavour text. Originally 4.3.10 [I] - Optional `map_area` landmark flavour | DoD: With `"New York"` set, hints reference real landmarks; empty string yields generic ones. (F) *(P2)*

### 4.4 Natural language — inbound
- [x] 4.4.1 [D] - `core/domain/hint_parser.py` — free text → directional intent + confidence | DoD: Port and adapt HW6's parser; low confidence defers to the belief map alone.
  - **Report confidence, never just a direction.** "I might drift north" (0.45) and "I am going north" (0.90) are different evidence; collapsing them lets a vague opponent steer our belief for free.
  - **Negation weakens rather than flips.** "Not north" does not become "south" — flipping would let a single word push our belief harder than any plain statement could, and both repositories are public.
  - **Two bearings in one sentence yields nothing** (0.1). Picking the first would make a smokescreen *more* effective than silence.
- [x] 4.4.2 [I] - Bluff classification: compare the claim against the observed scent field | DoD: Feeds the reliability coefficient in 4.2.2. — `claim_matches_scent()` checks the claimed bearing against how the scent peak actually moved.
- [x] 4.4.3 [I] - Behavioural profiling across sub-games | DoD: Opponent's lie rate and hint style recorded in the log. — `core/domain/opponent_model.py`. *(Original extension — README material.)*
  - ⚠️ **Superseded by `core/domain/opponent_profile.py` in 8.3, and nothing imports it.** The reason is in its signature: `record` and `predict` take an *observed opponent position*, and no peer ever has one (M#8). It is a correct model of a game we do not play. Kept, annotated, and off every code path — the honest record of a design built, tested, then found to need information the rules withhold. What replaced it profiles from the belief peak's trajectory and is deliberately coarser for it.
  - **The scoring says where to look.** Capture pays the Cop **20** and the Thief 5; survival pays the Thief **10** and the Cop 5. Our three Cop games are worth double our three Thief games — and it is in the Cop games that we observe *their* Thief. Modelling their Thief is the highest-value inference in the series.
  - **Never sacrifice a sub-game to probe.** Recording is free; a deliberately weak move to test their response risks 15 points to buy information worth less. We play to win every game and learn from what happens anyway.
  - ⚠️ **Determinism does not imply predictability.** Their move depends on their belief about *us*, which we cannot see, so the same board can legitimately produce different moves. A state→move lookup would be confidently wrong. We model the **conditional response** — given roughly where we are relative to them, which way do they go — which marginalises over the hidden belief instead of pretending to reconstruct it.
  - **With ~100 samples, test a hypothesis; do not fit a policy.** `flee_rate` checks the one that pays: if their Thief simply maximises distance (as the book's baseline does, and as most teams will build), it is **herdable** — a greedy fleer always takes the bait of the furthest cell and can be walked into a corner.
  - The model **abstains** below 4 samples in a bucket. A confident wrong prediction actively degrades a belief filter that already has the scent field, which cannot lie.
- [ ] 4.4.4 [I] ⏸️ **DEFERRED TO PHASE 7 ABLATION — recency-weighted reliability** *(Diana's proposal, 02/08)*
  - **The weakness is real.** A Beta posterior is *exchangeable*: 12 truths then 2 lies scores identically to 2 lies then 12 truths. "Build trust, then spend it at the decisive turn" is exactly the strategy it cannot see. `test_the_beta_score_is_blind_to_ordering` asserts the blindness so nobody removes it by accident.
  - **But the attack is already bounded, and that is the decisive fact.** Measured: at *maximum* trust one hint moves the northern-half belief mass from 0.429 to **0.449 — two percentage points**. Reputation is backward-looking and the betrayal is the last event in the sub-game, so detecting it a turn later cannot help. `MAX_TILT = 0.35` is what makes the attack survivable, and it is already in force.
  - **Prepared, not enabled.** `Reliability.timeline`, `decayed_coefficient(gamma)` and `turns_since_last_lie()` all exist and are tested. Nothing in the belief path reads them. Phase 7 A/Bs them against **real opponents** rather than against sequences we invented.
  - ❌ **Proximity-weighted trust is rejected, not deferred** *(Diana's second proposal)*. Two reasons. (1) Circular: the Cop's "distance to the thief" is itself a belief, so believing-they-lie-because-they-are-close would feed the loop that produced the closeness. (2) Deeper — it is a **prior on lying, not evidence of a lie**. Folding it into the coefficient would mean we could no longer say "this opponent lied 31% of the time" honestly, because the number would blend observation with speculation, and that number is README material. If we ever want it, it belongs in the *decision* layer (how far to act on a hint this turn), never in the *reputation* layer.

### 4.5 Intent flag
- [x] 4.5.1 [D] - `Intent` enum (`truth` / `lie`) chosen by the brain, not the LLM | DoD: Present in the hashed record; the LLM receives it as an instruction, never decides it. (Ch. 5)

### 4.6 Tests
- [x] 4.6.1 [D] - Scent emission and decay unit tests | DoD: Values match the book's figures to 2 decimal places.
- [x] 4.6.2 [D] - Belief update unit tests | DoD: Posterior sums to 1; contradicted hints move mass correctly.
- [x] 4.6.3 [I] - Provider tests with a mocked transport | DoD: No test touches a live API. (X §6.1)
- [x] 4.6.4 [D] - Word-cap and coordinate-scanner tests | DoD: A 20-word hint and a `(3,4)` hint are both rejected.

### ✅ Phase 4 Quality Gate
- [x] 4.QG.1 [D] - `uv run ruff check .` | DoD: 0 violations.
- [x] 4.QG.2 [D] - `uv run python scripts/check_file_size.py` | DoD: No file over 150 LOC. — `belief.py` split into `belief.py` + `belief_hints.py`, `test_reliability.py` into two, exactly as predicted.
- [x] 4.QG.3 [D] - `uv run pytest --cov` | DoD: All pass; coverage ≥85 %. — **705 tests, 94.89 %**.
- [x] 4.QG.4 [B] - **Milestone M4 observed** | DoD: Free-text report drives inference; scent map updates and decays each step; the verbal layer emits a truthful or deceptive hint. — `uv run python scripts/demo_m4.py`.
  - 🔴 **Building the demo caught a bug that would have cost us the league silently.** The parser scored *"I am heading north, you will never catch me"* at 0.315 — below the usable threshold — so the hint was discarded. Two compounding faults: the negation scan ran over the whole sentence, and hints are **taunts**, so "never" appears in nearly every one; and "no" was matched by prefix, making `"north".startswith("no")` true so **every northward hint negated itself**.
  - **The failure has no symptom.** An ignored hint looks exactly like an opponent who said nothing useful. We would have played every match with a dead verbal channel and never known. Only running the loop end to end and *reading the output* exposed it — which is the entire argument for milestones being *observed* rather than asserted.
  - Negation now scopes **forward**, as in English, and matches whole words. Eight parametrised tests hold the line between "not going north" (0.315, discarded) and "north, you will never catch me" (0.900, used).

---

## Phase 5: Cloud Exposure (Layer 5)
**Priority:** P0 | **Status:** ◐ Code complete (03/08) — every task that one machine can finish is done; 5.3.1, 5.3.2 and M5 need both machines | **Target:** 6 Aug
**DoD:** An agent on a remote machine connects via a public URL and plays a complete series.

> **⏰ THE BOOKING IS THE BOTTLENECK.** Everything below that code can settle is settled. What
> remains is 5.3.1/5.3.2/5.QG.4, and none of them can be simulated: they need Diana and Itay on
> two machines at the same time. It is the only hard human-availability dependency in the project.
> **Book the slot now** — the code has been waiting since 03/08, and a slot booked late is a
> milestone observed late.

- [x] 5.1.1 [I] - `core/infra/tunnel.py` — ngrok lifecycle | DoD: **Done 03/08.** `TunnelManager(authtoken, port, domain).start()/is_alive()/restart()/stop()`, wired into the CLI as `--serve --tunnel`. The URL is **read back from the agent's own local API**, not computed from config: a tunnel that failed to start otherwise looks identical to one that worked until the opponent cannot reach us mid-match. The authtoken travels in the child's environment, never in argv, because the process table is readable by every process on the machine (M#39, M#10).
- [x] 5.1.2 [I] - Localtonet fallback path | DoD: **Done 03/08.** `[network] tunnel_provider = "ngrok" | "localtonet"` in `game.toml`, documented in both READMEs under *Network exposure*. ⚠️ The localtonet argument form in `core/infra/tunnel.py` has **never been run against a live account** — confirm it against their docs before a graded match, not during one. *(P2)*
- [x] 5.2.1 [I] - Drop detection + reconnect + re-handshake | DoD: **Done 03/08.** `core/runtime/tunnel_supervisor.py`: three bounded reconnects, then a clean `TECHNICAL_LOSS`. **Reconnection is not complete until the handshake has been re-run** — a tunnel that is up while the opponent still holds a stale session looks healthy from here and is worse than one plainly down (PRD 5 req. 5.6). A failing re-handshake therefore counts as a failed reconnect.
- [x] 5.2.2 [I] - Tunnel health wired into the Watchdog input | DoD: **Done 03/08.** The watchdog is beaten only while the tunnel is up, so an unrevivable tunnel ends the sub-game within `watchdog_timeout_sec` with nobody deciding that it should. The supervisor **also** runs its own outage clock: starving the watchdog only bounds the outage if the tunnel is its sole heartbeat source, and the turn loop beats the same watchdog. Two independent clocks, so the bound holds either way.
- [ ] 5.3.1 🧑 [B] - Two-machine rehearsal, Diana ↔ Itay over the public internet | DoD: A full 6-sub-game series completes end-to-end. **Cannot be simulated — book the slot.** Run `--serve --tunnel` on one machine and `--handshake --opponent <public-url>` on the other.
- [ ] 5.3.2 🧑 [B] - Latency measurement under the 30 s response timeout | DoD: p95 round-trip recorded; timeout raised by agreement if the margin is thin. (F, M#12) — **the instrument is built and tested** (`core/infra/latency.py`: p50/p95 nearest-rank, `verdict()`, `recommended_timeout()`); what is missing is the two-machine reading it is meant to record. Raising is legal by mutual agreement, lowering never is, so a thin margin has exactly one remedy.

### ✅ Phase 5 Quality Gate
- [x] 5.QG.1 [I] - `uv run ruff check .` | DoD: **0 violations, 03/08.**
- [x] 5.QG.2 [I] - `uv run python scripts/check_file_size.py` | DoD: **No file over 150 LOC, 03/08.**
- [x] 5.QG.3 [I] - `uv run pytest --cov` | DoD: **899 passed, coverage 95.45 %, 03/08.** Split-repository suite green on both published repos. No test opens a real tunnel (PRD 5 §5): the process, the agent API and the clock are all injected, so T5.1–T5.6 and T5.9 run against fakes in microseconds.
- [ ] 5.QG.4 🧑 [B] - **Milestone M5 observed** | DoD: Remote machine plays a full series via ngrok against the local agent. **Blocked on 5.3.1 only.**

---

## Phase 6: Security & Cryptography (Layer 6)
**Priority:** P0 | **Status:** ✅ **Complete** (02/08, five days early) | **Target:** 7 Aug

> ### ✅ **Phase 6 does NOT depend on Phase 5. Start it now.**
> Commit-reveal, canonical JSON, the audit, the phase machine, the watchdog and Step-0 all run
> **in-process**. None of them touches a tunnel: the crypto that protects a match is the same
> whether the bytes travel over ngrok or over a function call, which is what makes it testable
> without a second machine at all.
>
> Phase 5 is a *transport* layer. The only items there that genuinely need two machines are
> **5.3.1** (the rehearsal) and **5.3.2** (latency), both already marked `[B]`.
>
> Phase 6 is also where the worst-case risk in the whole project lives — **6.1.1**, canonical
> serialisation. If two peers serialise the same payload differently, every digest mismatches and
> **both teams score 0**. That is worth more attention than a tunnel, and it is entirely ours.
>
> Partly built already: `core/crypto/canonical.py` and `core/crypto/commitment.py` landed in
> Phase 1–4 and are covered by tests.
**DoD:** A move is committed then revealed with a valid nonce; Step-0 verifies hardware and commit
hash; the end-of-match audit passes; any tampering is detected.

### 6.1 Cryptographic core
- [x] 6.1.1 [D] - `core/crypto/canonical.py` — `json.dumps(sort_keys=True, separators=(",", ":"))` | DoD: Two independent processes produce byte-identical output for the same payload. **Divergence here means both teams score 0.** — proven in a real `subprocess`, not a thread: hash seed, dict ordering, locale and float repr are all per-*interpreter*, so a thread would share them and prove nothing. Payload deliberately awkward — `0.1 + 0.2`, `10**18`, Hebrew text, nesting, reversed key order.
- [x] 6.1.2 [D] - `secrets.token_hex(16)` (lives in `commitment.py`, not a separate `nonce.py` — 12 lines did not warrant a module) | DoD: An architecture test asserts `random` is never imported for nonce generation. (M#18) — `random` is seeded predictably; an opponent who guessed the seed could reproduce every nonce, and the scheme would collapse **silently while still appearing to work**.
- [x] 6.1.3 [D] - ~~`core/crypto/commit_reveal.py`~~ → **`core/crypto/commitment.py`** (built in Phase 1; the plan assumed a filename we had already chosen differently) | DoD: File ≤150 lines. ✅
  - [x] 6.1.3.a [D] - `seal(state, move, intent) -> Sealed` over `SHA256(State‖Move‖Intent‖Nonce)` | DoD: Same inputs with different nonces yield different hashes. (M#17) — 50 seals of identical inputs give 50 distinct digests.
  - [x] 6.1.3.b [D] - `verify(...)` using `secrets.compare_digest` | DoD: A single flipped bit is detected.
    - ⚠️ **Was using `==` until 02/08.** Being honest about the threat: a timing attack is *not* realistic here — the audit runs offline, at the end, over a log the opponent already holds, so there is no secret for a timing difference to leak. But constant-time comparison is what the primitive is for, it costs nothing measurable, and reaching for `==` on a digest is the habit that eventually gets used somewhere it does matter. An architecture test now asserts it against the source.
  - [x] 6.1.3.c [D] - Nonce retained locally, never transmitted before the final audit | DoD: A test asserts no reveal payload contains a nonce. (M#18) — enforced in `four_phase.reveal()`, which **raises** on a nonce rather than stripping it: silently removing it would hide the bug that put it there.
- [x] 6.1.4 [D] - `core/crypto/audit.py` — mutual end-of-match audit | DoD: Re-hashes every step of both logs; any mismatch → technical loss for the forging side. (M#19)
  - 🔴 **A test written to find a replay hole found one.** Re-hashing every seal and checking that step numbers increase is **not enough**: a genuine step-1 commitment relabelled as step 4 still matches its own sealed state, and the outer numbers still ascend. Nothing compared the *declared* step against the one sealed **inside** the state. `commitment.py` promises "no time travel"; the promise only holds if the audit checks it.
  - Reordering is caught for the same reason — every individual seal in a reordered log verifies, because the forger touched no single record. Only the **sequence** is the lie.
  - **An empty log does not pass.** A missing log is not a clean one; treating them alike would let a peer escape the audit by sending nothing — the cheapest possible forgery.
  - **Never raises.** A forged log is an expected input, not an exception. Raising would stop at the first fault, and the *pattern* of failures is what distinguishes a bug from a forgery.
  - **Reports evidence, decides nothing.** Sanctions belong to the rules layer; if this module decided outcomes, a scoring change could alter what counts as proof (M#19).

### 6.2 Four-phase protocol
- [x] 6.2.1 [D] - Phase 1 Commit — send hash only | DoD: No payload content leaves before the ack. — **this is what makes it safe to be the peer who sends first**, which somebody always has to be over a network. A second commit from the same side is refused: that is precisely the change-after-seeing the hash exists to prevent.
- [x] 6.2.2 [D] - Phase 2 Acknowledge — opponent confirms lock | DoD: Reveal is impossible before both sides have acked. — the attack it stops: revealing to an opponent who has **not** confirmed they are locked in hands them our move while they are still free to choose theirs. One peer acking twice cannot stand in for the other acking once.
- [x] 6.2.3 [D] - Phase 3 Reveal — move + hint, nonce withheld | DoD: Tested.
  - ⚠️ **A reveal carrying a nonce raises — and that guard protects our own code more than the opponent's.** Leaking it per turn would quietly dismantle the end-of-match audit *while every other test still passed*: the moves would all verify, just a turn too early to be worth anything.
- [x] 6.2.4 [D] - Phase 4 Final Reveal — all nonces at end of match | DoD: Triggered only in the terminal state.
  - **The nonce is the hinge of the whole protocol.** Per-turn verification sounds better and is worse: a peer that verified turn 4 and disliked the result could abandon the match before turn 5 and argue afterwards. Withholding until the end means the only moment to walk away is after every move is already sealed.
- [x] 6.2.5 [D] - Truthful capture response is cryptographically bound | DoD: Denying a real capture is detectable at audit. (M#21, M#22) — falls out of 6.1.4: the move that produced the capture is sealed, so denying it means revealing a move whose digest does not match.

### 6.3 Step-0 declaration
- [~] 6.3.1 [I] - `core/shared/system_info.py` — OS, CPU cores/frequency, RAM, GPU/VRAM | DoD: Works on both machines; degrades gracefully with no GPU. — **written and tested; needs one run on Itay's machine to close.** ⏰ He runs `uv run python scripts/step_zero_demo.py` during setup.
  - **Degrade, never fail.** An unreadable field reports `unknown` and the match starts. Refusing to play because we could not read a CPU frequency would turn a cosmetic gap into a forfeit. `"none"` for GPU is a *real answer* — Diana's machine has none and plays anyway.
  - No `psutil`: one fewer thing to install correctly on two machines under deadline, and every field the rulebook asks for is reachable from the standard library.
- [x] 6.3.2 [D] - `core/protocol/step_zero.py` — signed declaration | DoD: Includes hardware, LLM model name, code version, team name, sub-game number **and `github_commit`**. (M#24, M#53)
  - **It pins the code for the whole series.** `github_commit` is inside the digest, so a peer cannot quietly swap in a different agent between sub-games and still match what it signed at Step-0.
  - The **sub-game number is sealed too**, closing the same replay hole the move audit closes (6.1.4): a declaration signed for sub-game 1 cannot be re-presented as sub-game 4 with different code underneath.
  - ⚠️ **Declares the model, never the provider.** Appendix F Table 21 keeps the provider private per peer; naming `groq` or `ollama` would leak a choice the rulebook does not negotiate, and hint at our latency budget.
- [x] 6.3.3 [D] - Read the current commit hash at runtime | DoD: Matches `git rev-parse HEAD`; a dirty tree raises a warning before a graded match.
  - **A dirty tree is declared, not hidden** (`<sha>-dirty`). With uncommitted changes the declared commit does not describe the running code, so the reproducibility claim is simply false — better said before the match than discovered by a grader after.
  - **Warnings are returned, never raised.** Whether to play a graded match against an unverifiable opponent is a judgement for the people involved, not a decision a dataclass gets to make.
  - 🚀 **Cached** — and that is correctness, not only speed. The test suite exposed the cost (9.86 s → 0.86 s), but the real reason is that the declared commit must be *the same value all series*: re-reading it mid-match could return something other than what we signed.
- [x] 6.3.4 [I] - Token meter, locked at Step-0 | DoD: Cumulative LLM tokens reported in the result JSON. (M#54) — **`core/infra/llm/meter.py`.** Both model-backed providers record the `usage` block the endpoint returns into one `TokenMeter`, owned by `LocalTruth` and read by `SeriesRunner` once per sub-game. The reported figure was the literal `0` in `filing.py` until now: honest on `template` and a **false declaration** on either provider our `.env` files actually select (M#38). Three decisions: the count is what the provider reported and never an estimate, a call whose usage we could not read is counted as `unmetered` rather than free, and the series total is summed from the **merged** rows — a process-local meter sees only its own three sub-games under a 3-3 split, which is the same trap `merge_rows` exists to fix for the points.

### 6.4 Reliability patterns
- [x] 6.4.1 [D] - `core/runtime/phase_machine.py` — explicit transition table | DoD: `WAITING_FOR_OPPONENT → COMPUTING_MOVE → COMMITTING → AWAITING_REVEAL → VERIFYING`, plus terminal `TECHNICAL_LOSS`. Illegal transition raises. (M#4, M#5)
  - **A hang is worse than a loss.** A peer stalling on a message that never arrives takes the opponent down with it, and the match ends with *no result for either side* — the one outcome nobody can appeal. Hence the shape: `TECHNICAL_LOSS` is reachable from **every** live phase, asserted by a test parametrised over the enum, so adding a phase later without a failure edge breaks the build instead of shipping a hang.
  - **Terminal means terminal** — no outgoing edges at all, so a lost sub-game cannot quietly resume and start sending moves after the result was recorded, and a completed one cannot be downgraded.
  - `fail()` is a **no-op when already terminal**: the watchdog and the deadline tracker can both fire on one stalled turn, and the second must not raise while the first is being handled.
  - Written as a table, not as `if` statements, because M#4 requires "which module changed the state" to have exactly one answer. A transition scattered across five call sites has five.
- [x] 6.4.2 [D] - `core/runtime/deadline_tracker.py` | DoD: Every MCP request carries an expiry; expiry triggers a controlled retry then technical loss — never continued waiting. (M#6)
  - **Exactly one retry.** Not zero — a single dropped packet on a home connection is common and cheap to survive. Not `max_retries` — three attempts at 30 s each would blow past the 60 s watchdog and turn a recoverable blip into the very hang the timeout exists to prevent.
  - **It returns a decision, never acts on one.** The tracker knows *when* to give up; only the phase machine may decide what that does to the sub-game (M#4). Merging them would put the power to end a match inside a timer.
- [x] 6.4.3 [D] - `core/runtime/watchdog.py` — heartbeat monitor | DoD: No heartbeat for `watchdog_timeout_sec` → persist state → controlled shutdown. (M#7)
  - **Catches what the deadline tracker cannot**: a peer not waiting on anything because it never got as far as sending. Deadlocked thread, brain stuck in a loop, exception swallowed with no deadline outstanding — from outside all three look identical, and that is silence.
  - **Persists before shutting down.** A killed process that left nothing behind cannot be audited, and the audit is what proves we played honestly. Losing a sub-game is survivable; losing the evidence is not.
  - **Fires exactly once**, and a late heartbeat cannot resurrect a recorded loss. Polled every second on a dead process it would otherwise persist sixty times, and the last write — made while already tearing down — is the one most likely to leave a truncated file.
  - ⚖️ Asserted rather than assumed: **60 s ≥ 30 s × 2 attempts**, so the watchdog and the tracker cannot race. Appendix F's defaults sit exactly on that boundary.
- [x] 6.4.4 [D] - State persistence for recovery | DoD: A killed process leaves a loadable snapshot. — `core/runtime/snapshot.py`, wired into the watchdog's `on_shutdown` so state reaches the disk *before* the verdict returns.
  - **Atomic** — temp file then `os.replace`, atomic on Windows and POSIX alike. A process dying mid-write would otherwise leave half-written JSON, and a truncated snapshot is **worse than none**: it looks recoverable right up until it is parsed.
  - **Never raises.** This runs *during* a failure; an exception here would replace a recorded technical loss with an unhandled traceback and lose the original reason with it. A missing file and a corrupt one both read as `None`, because the caller's response to each is identical.
  - Explicit UTF-8 with `ensure_ascii=False`, per the 6.5.2 lesson. Keys sorted so two snapshots diff cleanly by eye.

### 6.5 Tests
- [~] 6.5.1 [D] - Commit-reveal round trip and tamper detection | DoD: Every mutation of state/move/intent/nonce is caught. — all four fields covered by a parametrised test; the four-phase protocol tests (6.2) still to come.
- [x] 6.5.2 [D] - Cross-process canonical serialisation test | DoD: Two subprocesses agree on the digest. — `tests/unit/test_canonical_cross_process.py`.
  - 🪟 **It earned its keep on the first Windows run.** The child process died with `UnicodeEncodeError` before it could report anything: a cp1252 console cannot `print` Hebrew. The canonical bytes were correct all along — the *platform* could not carry them. Invisible on Linux and on any CI runner.
  - **The rule this pins down: canonical output is bytes.** Anything turning it back into console text must say UTF-8 explicitly. `sys.stdout.buffer` bypasses the console codec, which is the only reliable answer.
  - Also removed `check=True` from the subprocess call: it raises carrying only an exit code, which hid the child's real traceback and made the first failure unreadable. We surface stderr instead.
  - ✅ Audited the rest of the codebase for the same fault — **every** `open` / `write_text` already passes `encoding=`. Nothing else to fix, but see the 7.2 note.
- [x] 6.5.3 [D] - State machine legal/illegal transition matrix | DoD: Every illegal pair asserted to raise. — **all 49 ordered pairs**, generated with `itertools.product` rather than hand-listed. A machine tested only on the paths someone thought of has untested paths, and the untested one is what fires during a graded match.
- [x] 6.5.4 [D] - Deadline and watchdog tests with a simulated stall | DoD: No test sleeps longer than 2 s (clock injected). — **no test sleeps at all.** The clock is a number the test passes in, so a 60 s timeout is checked in microseconds. These paths fire only when something has already gone wrong, making them the least likely to be exercised by accident and the most expensive to get wrong.

### ✅ Phase 6 Quality Gate
- [x] 6.QG.1 [D] - `uv run ruff check .` | DoD: 0 violations.
- [x] 6.QG.2 [D] - `uv run python scripts/check_file_size.py` | DoD: No file over 150 LOC.
- [x] 6.QG.3 [D] - `uv run pytest --cov` | DoD: All pass; coverage **≥95 %** on `core/crypto` — this module cannot afford a gap. — **818 tests**; `canonical.py`, `commitment.py`, `scent_model.py` at 100 %, `audit.py` at 96 %.
- [x] 6.QG.4 [D] - **Milestone M6 observed** | DoD: Move committed then revealed with a valid nonce; Step-0 verifies hardware; audit passes. — `uv run python scripts/demo_m6.py`.
  - Runs the **real** protocol — same `TurnExchange`, `seal` and `audit_log` that play a graded match — then audits the log honestly *and* after tampering, so the audit is seen catching something rather than merely returning OK:
    ```
    honest log      : Verified OK - 3 steps re-hashed, no mismatch
    one move changed: FAILED - first at step 2: digest does not match the revealed move, intent and nonce
    step 1 replayed : FAILED - first at step 3: replays the commitment sealed for step 1
    ```
  - The nonce refusal is demonstrated live, not asserted: `refused: us included a nonce in a step reveal; nonces are withheld until the final reveal (M#18)`.

---

## Phase 7: Reporting & Visualisation (Layer 7)
**Priority:** P0 | **Status:** ✅ **Complete** (03/08, five days early) — 7.1–7.5 all done; M7 needs one observed run | **Target:** 8 Aug
**DoD:** A match summary reaches the lecturer's inbox as a JSON attachment; the Live GUI shows local
truth only; the Replay App reproduces a recorded series with `Verified OK`.

> **Note on ownership.** Every task in this phase is marked **[D]**. 7.1 was built by [I] on 03/08
> anyway — the Gatekeeper blocks 7.3, and Phase 5 was finished and waiting on a two-machine slot.
> Reassign the rest or leave it; the split is worth agreeing before 7.3 starts.
>
> ⚠️ **This note used to say 7.3 was waiting on "the Gmail OAuth consent that only Diana's account
> has completed", and that was wrong in both directions.** The sending account is **Itay's**
> (`[email] sender = itay.malich2@gmail.com`), his own `credentials.json` and `token.json` sit in
> `C:\Users\itaym\.p2p-secrets\`, and the consent has been run there. Verified 11/08: `check_setup.py`
> reports both files present, and the token holds exactly one scope, `gmail.send` (M#30), with a
> refresh token — so the expired access token renews silently inside `build_transport()`. SETUP 0.2.1
> documents Diana's machine paths; it is not a claim about whose account sends.

### 7.1 Gatekeeper — ✅ complete 03/08
- [x] 7.1.1 [D] - Port `rate_limiter.py`, `queue_manager.py`, `call_logger.py` from HW6 | DoD: **Done 03/08 — written fresh, not ported.** No HW6 tree exists in this workspace, so there was nothing to adapt; the three modules were written against the current config layout directly. All limits load from `rate_limits.json` via `core/shared/rate_limits.py` (req. 7.6) — no limit has a default in code, and a missing key is named rather than guessed.
- [x] 7.1.2 [D] - `core/shared/gatekeeper.py` — three cumulative gates | DoD: **Done 03/08.** `execute()` / `status()`; a call must clear all three. ⚠️ **Gate order reversed from PRD 7 §3.1** — see CONTRADICTIONS **C-014**: the drawn order leaves the detector blind once the quota is spent, which is exactly when a runaway loop is running. Exceptions are `GatekeeperLockedError` / `QuotaExhaustedError`, also C-014: ruff `N818` rejects the PRD's names and 7.QG.1 requires zero violations.
  - [x] 7.1.2.a [D] - Quota manager — daily ceiling | DoD: **Done 03/08.** 50/day, rolling on the **UTC** calendar day. Counted on the attempt, not on success: a failing loop still reached the provider, and a quota that counted only successes would let exactly that loop run free.
  - [x] 7.1.2.b [D] - Token bucket `rate_tokens ← min(C, rate_tokens + r·Δt)` | DoD: **Done 03/08.** Starts full, `C = 5` (one report plus its three retries, with one spare), `r` = 30/min. (M#28)
  - [x] 7.1.2.c [D] - **DOS detector** — abnormal send pattern locks the pipe | DoD: **Done 03/08.** 20 calls in 10 s = 120 RPM, 240× measured demand and unreachable by a match. The lock is **terminal until `reset()`** — a detector that timed out would let the same loop resume at the rate that tripped it. (M#29)
- [x] 7.1.3 [D] - HTTP 429 honoured with backoff, never blind retry | DoD: **Done 03/08.** Constant 5 s × 3, not exponential: the whole sequence has to finish inside one 30 s response window and doubling leaves it in three steps. Detection is duck-typed on `status_code`, so `core/shared/` needs no HTTP dependency. A non-429 failure is not retried at all. (Ch. 9)
- [x] 7.1.4 [D] - Naming discipline for the three meanings of "token" | DoD: **Done 03/08.** `rate_tokens` / `llm_tokens` / `oauth_token` (the last reserved for 7.3). Enforced by an AST test that walks every module on the outbound path and fails on a bare `token`/`tokens` binding — a comment would not have survived the next file. (Ch. 9)
- [x] 7.1.5 [D] - Queue rather than error when the bucket is full | DoD: **Done 03/08.** A saturated bucket delays; it never raises. Two bounded exceptions, both argued in the module: a queue deeper than `queue_depth` refuses (at 0.5 RPM, 100 waiters is a loop, not traffic), and a wait outliving the 30 s response window raises `QueueDeadlockError` — this process is single-threaded, so a slot nobody can free is a deadlock, and **a hang is worse than a loss**. (`REFERENCE_PERFORMANCE_NOTES.md` §5)
- [x] 7.1.6 [D] - Startup check: metered provider ⇒ `every_n_steps ≥ 3` | DoD: **Done 03/08.** `core/shared/provider_budget.py`, called from the CLI — deliberately **not** from `PeerSDK.__init__`, so it stops a human about to play a match rather than failing the suite on whichever machine's `.env` selects a metered provider. Resolves the provider the same way `build_provider` does (env over file); asking the question differently is how a check passes while the thing it checks is misconfigured.
  - **Why a check and not a comment:** at `every_n_steps = 1` a 6-sub-game series makes 210 model calls instead of ~70 (~52k tokens on a paid tier). The safe value depends on the provider, and the provider is set per machine in `.env` — so the two can drift apart silently on someone else's laptop. See `REFERENCE_PERFORMANCE_NOTES.md` §2.
  - Retry budget must stay inside the response timeout: 3 × 5 s backoff + request time < 30 s. A fourth retry would not fit, which is why `max_retries` stays at the Appendix F minimum.

### 7.2 JSON artefacts
> 🪟 **Every file write here must pass `encoding="utf-8"` explicitly, and every console print of a
> payload must go through `sys.stdout.buffer`.** Team names and hints may be Hebrew, and on a
> Windows console the default codec is cp1252 — which raises `UnicodeEncodeError` mid-match on
> the machine we play from and never on a CI runner. Found the hard way in 6.5.2.
- [x] 7.2.1 [D] - `declaration_<game_id>.json` builder | DoD: Teams, members, **four** repo links, MCP URLs, hardware, LLM model, token cap, timings. — `core/report/artefacts.py`.
  - [x] 7.2.1.a [D] - **Call it.** The builder had three callers and all three were tests, so a real match filed a config snapshot, six logs and a result — three of the four artefacts Ch. 9.3.3 names. `core/runtime/live.declare` assembles it from the settled handshake and `cli_play._series` files it **before the first move**, so an interrupted series still leaves the declaration it was played under. `MatchFiling.result` closes it with `ended_utc`, because that is the one moment a series is known to be over. The start time is read back from disk rather than re-stamped: both role processes write this file and the later one would otherwise open the match window after three sub-games had been played. `test_the_series_files_all_four_artefacts` used to write the declaration itself, which is exactly why it never caught this.
  - [x] 7.2.1.b [D] - **Members over the wire.** `identity.members` is declared in Step-0, so the opponent's roster arrives the only way it can — Ch. 9.3.3 wants both groups *and their members* and nothing else in the handshake asks. Additive and read defensively: a peer that sends none is recorded as an empty list, never guessed. ⚠️ Our two names are in both `game.toml`s and must be checked against the Moodle form before a graded match.
  - [x] 7.2.1.c [D] - **The hardware declaration is signed** (M#24). Both peers' Step-0 payloads are filed whole, each beside its digest — ours as sealed, **theirs recomputed over the bytes they sent**, because a digest a peer supplies for its own declaration proves nothing. A machine restated later contradicts a value the opponent already holds.
  - [x] 7.2.1.d [D] - **The four repository links** (M#49). ✅ **Done 13/08.** `repositories` was four empty strings in every artefact and could not have been filled in: the URLs lived only in README prose and nothing exchanged them. Ours now come from `[identity] repo_cop` / `repo_thief`, the opponent's ride in their Step-0 payload, and `live._repos` assembles all four onto the filing — one assignment, because the declaration and the result both need them and are written at different times. Verified in a live localhost match: all four present in both artefacts.
  - A **missing** repo link is recorded as `""`, never omitted. Dropping the key would make an incomplete report look complete; an empty string shows a reader *which* one is absent.
  - Timestamps are **UTC**. Both peers share a timezone today and may not tomorrow, and two reports disagreeing about when a match happened is a needless question for a grader.
- [x] 7.2.2 [D] - `config_<game_id>_g<NN>.json` builder | DoD: **Done 03/08.** `build_config_snapshot()` in `core/report/artefacts.py`. The **shared** contract only — private settings are not part of the agreement and including them would make two correctly-agreed peers file contradicting snapshots. Carries `role_split`, `scent_model_digest` and the C-006/C-010 `readings`, which Appendix F does not cover at all. (Appendix F §2)
  - **`config_sha256` is recomputed here, never copied from the caller**, and the handshake's agreed digest is *checked* against it when supplied. A snapshot asserting agreement on a config it does not contain is not merely wrong — it is evidence for the wrong thing, and would be quoted in a dispute to prove a match was played under parameters nobody agreed to. It raises `ArtefactError` rather than writing. (M#11)
- [x] 7.2.3 [D] - `log_<game_id>_g<NN>.json` builder | DoD: **Done 03/08.** `core/report/match_log.py`.
  - **"Sufficient for full replay verification" is a round trip, not a field list**, so the module ships the inverse (`records()`, `verify_log()`) and the test does the trip: seal real commitments → build → write → read off disk → re-hash → `Verified OK`. Off disk specifically, because JSON has no tuple and that is where it would bite. The Replay Viewer (7.5.2) calls the same path, so the viewer and the test check one thing rather than two similar things.
  - **Nonces are merged from the `FinalReveal`, not carried per step** (M#18) — the shape mirrors the protocol instead of pretending the nonce was available at commit time. A step whose nonce never arrived is written with an empty one and listed in `unverifiable_steps`: dropping it would produce a shorter log that audits *clean*, which is precisely the forgery the audit exists to catch.
  - `scent_digest` is **omitted when unused, never `null`** — mirroring `commitment_payload` exactly, because the replay rebuilds the hashed payload from this file and a stray `null` would fail every digest in an honest match (C-008).
- [x] 7.2.C [I] - **Cross-artefact consistency test** — `tests/unit/test_artefact_consistency.py` | DoD: **Added 03/08, and it caught a real one.** The four builders were written one at a time and every per-file test passed, but the log carried neither `created_utc` nor `code_version` while the other three had since 7.2.1. Nothing compared them, so nothing noticed. The comparison is now a test: shared `game_id`, common fields, UTC timestamps, matching `sub_game` between config and log, distinct filenames, and no artefact leaking the private provider (Table 21).
  - Also fixed while auditing: `payload_digest()` existed but was neither exported nor used; `build_result`'s `total_tokens` parameter became `total_llm_tokens`, since 7.1.4 requires saying *which* of the three kinds of token a name means.
  - ⚠️ **PRD 7 §4 places these in `core/protocol/artefacts.py`; they live in `core/report/`.** Not worth moving — artefacts are reports, not protocol, and `core/report/` is the better home — but the PRD's interface sketch and the tree disagree, so read the tree.
- [x] 7.2.4 [D] - `result_<game_id>.json` builder | DoD: Per-sub-game and cumulative scores, `github_commit`, total tokens, four repo links. (M#49, M#53, M#54)
  - **Totals are summed here, never passed in.** A caller supplying its own total could disagree with the per-sub-game rows printed in the same file, and a report that contradicts itself is worse than one that is merely wrong.
- [x] 7.2.5 [D] - Shared `game_uid`; filenames derived from `game_id` | DoD: Files from different matches can never collide. (Ch. 9) — `core/report/identifiers.py`.
  - **Derived, not generated.** Two peers each rolling their own id would produce two ids for one match, and the pair of reports would read as two separate games that each side won. It is hashed from the two team names *sorted* plus the date, so the derivation is symmetric and neither peer has to remember to order them.
  - 🐛 **Caught while testing:** two Hebrew team names both sanitise to an empty filename. Hashing the *sanitised* form would have given them the same id — exactly the collision this function exists to prevent. The fingerprint is taken from the originals, and each side gets a short readable stand-in (`team310f02-vs-team787be7`).
  - Sub-game numbers zero-padded (`g03`), so `g10` cannot sort before `g2` in a directory listing.

### 7.3 Gmail delivery — ✅ complete 03/08
- [x] 7.3.1 [D] - Port `gmail_sender.py`, send-only scope, routed through the Gatekeeper | DoD: **Done 03/08.** `core/infra/gmail_sender.py`; `sdk.mailer()` wires it to the peer's single Gatekeeper. Every send goes through `execute()` — a direct API call would walk around the three gates that stand between a bug and a suspended account. `build_transport()` refreshes the stored OAuth token silently, so there is **no human step at send time**; the one-time consent is SETUP 0.2.1. (M#30, M#32)
- [x] 7.3.2 [D] - Report sent as a JSON **attachment**, never free text | DoD: **Done 03/08.** The body is a fixed two-line sentence and the test asserts the game id, the totals and every score are **absent** from it — a grader parsing the attachment must not find a second, possibly disagreeing, copy in the prose. The JSON is attached as bytes, never decoded, so a Hebrew team name is not mangled by a cp1252 console on the way out. (M#33, M#34)
- [x] 7.3.3 [D] - Recipient `rmisegal+uoh26finalgame@gmail.com` from config | DoD: **Done 03/08.** `[email] recipient` in both `game.toml`s; neither address has a default, because a default recipient is a hardcoded lecturer address by another name. A test asserts the string does not appear in the module source at all. (M#51)
- [x] 7.3.4 [D] - Each team sends its **own** report independently | DoD: **Done 03/08.** Checked structurally rather than by intent: a test reads `send_result`'s signature and asserts no parameter anywhere names whose report it is. A peer that "helpfully" filed for both would produce exactly the disagreeing pair M#35 voids matches over.
  - ✅ **The trigger landed in 9.5.8 (09/08).** For five days this read *"nothing calls `send_result()` yet — `[email] send_on_series_end = true` describes a hook the turn loop owns, and the turn loop is Phase 9"*. The turn loop arrived on 08/08 and did not pick the hook up: the sender, the transport and the Gatekeeper wiring were all done and tested, and the only caller in the tree was the setup self-test. `core/runtime/reporting.py` is the trigger.

### 7.4 Live GUI — local truth only — ✅ complete 03/08
- [x] 7.4.1 [D] - `core/ui/live_gui.py` in Tkinter | DoD: **Done 03/08.** 62 and 40 code lines; widgets split into `core/ui/widgets.py` as ADR-005 requires. The window polls a provider on a timer and **never drives the match** — a GUI running the turn loop would freeze for a 30 s response timeout, and a frozen window mid-match looks exactly like a crashed peer. Launch with `uv run python -m core peer --role police --gui`.
  - ⚠️ **`--gui` and `--serve` do not currently combine.** `--gui` is dispatched first and returns, so adding `--serve` opens the window and never starts the server. Not a one-line fix: `FastMCP.run()` blocks and `uvicorn` installs signal handlers that only work on the main thread, so serving alongside Tkinter needs the server in a worker thread and that needs testing on both machines. Until the turn loop exists (Phase 9) the window shows the starting position either way, so this is deferred to whoever wires the loop — **it must be resolved before the M7 screenshot of live state.**
  ![alt text](image.png)
  - [x] 7.4.1.a [D] - Belief heatmap, intensity ∝ posterior | DoD: **Done 03/08.** Normalised against the peak, not absolute: a uniform prior over 47 cells peaks at 0.021 and would render as a blank board, hiding the one thing the heatmap exists to show. `heat_colour()` interpolates toward dark red so the ordering survives a greyscale printout, and T7.14 is asserted — the deepest cell *is* `belief.argmax()`.
  - [x] 7.4.1.b [D] - Own position and known barriers | DoD: **Done 03/08.** Painted back to front — heat, then barriers, then our marker — so an agent is never buried under a wall by the drawing order.
  - [x] 7.4.1.c [D] - Turn banner: green `YOUR TURN` / grey `LOCKED` | DoD: **Done 03/08.** `accepts_input()` lives on the state, not in the event handler, so "are we allowed to move?" has one answer a test can ask directly. Accepting a keystroke while locked would let a human change a move the opponent already holds a digest of — commit-reveal defeated through the keyboard.
- [x] 7.4.2 [D] - **Local-truth enforcement test** | DoD: **Done 03/08 — `tests/unit/test_local_truth.py`, checked three ways.** (1) By type: `GuiState` has no field that could hold the opponent's position. (2) By construction: it is built from an `Observation`, which has no such field either, so there is nothing to build it from. (3) By import: `core/ui/` reaches nothing below `core/sdk/`. **Not a filter applied at render time** — filtering works until somebody adds a debug label, and that failure is silent, visible only on screen, and worth the whole project. (M#8, M#9)
  - 🐛 **Caught by writing it: `core/ui/render.py` had been importing `core.domain.board` since Phase 1.** A live breach of X §4.1 and 7.5.4 that survived because the old boundary test in `test_peer_sdk.py` only looked for `core.runtime`, `core.protocol` and `core.infra` — never `core.domain`. The renderer now duck-types the board and the new test walks the AST, which also catches `import core.domain.board` that a grep for `from core.domain` would miss.

### 7.5 Replay Viewer — ✅ complete 03/08
- [x] 7.5.1 [D] - `core/ui/replay.py` — load a log, step forward/back | DoD: **Done 03/08.** Model in `core/report/replay.py` beside the log it replays; window in `core/ui/replay.py`. The cursor clamps rather than wraps — a viewer that looped would make "is this the last step?" unanswerable from the screen. (M#20)
- [x] 7.5.2 [D] - Live re-hash of every entry | DoD: **Done 03/08.** Via `verify_log()`, the same call 7.2.3 was built around, so the viewer and the log-format test check one thing rather than two similar things. **The whole log is audited before the first frame is drawn** — a viewer verifying lazily as the cursor moved would show a green banner on a log whose forgery sits at step 30 and which nobody clicked as far as.
- [x] 7.5.3 [D] - Green `Verified OK` / red `TAMPERED` | DoD: **Done 03/08.** Per-step verdicts are recomputed rather than read from the audit's failure list: an ordering or duplication failure is about the log's *shape* and says nothing about whether that seal is genuine, so conflating them would point the viewer at the wrong row. A log that cannot be verified at all **refuses to open** — a green banner over an unverifiable file is worse than no viewer, because it looks like evidence. (Ch. 7)
  - `python -m core replay <log.json> --headless` prints the verdict and **exits 1 on TAMPERED**, so a log can be checked from CI without a display. 7.24 is not a verdict that should require a human to be looking at a window.
- [x] 7.5.4 [D] - `PeerSdk` is the only path used by GUI, Replay, CLI and tests | DoD: **Done 03/08.** `core/sdk/replay_sdk.py` and `core/sdk/view_state.py` are the two facades; the AST test in `test_local_truth.py` supersedes the weaker substring check in `test_peer_sdk.py`, which had been passing over a real breach. (X §4.1)

### ✅ Phase 7 Quality Gate
- [x] 7.QG.1 [D] - `uv run ruff check .` | DoD: **0 violations, 03/08.**
- [x] 7.QG.2 [D] - `uv run python scripts/check_file_size.py` | DoD: **No file over 150 LOC, 03/08.** The GUI modules did not breach; `core/__main__.py` did — it reached 149 of 150 while gaining `--gui` and `replay`, so the command bodies moved to `core/cli_commands.py`. Parsing and dispatch stayed. The architecture test caught the new module joining two subsystems and it is now listed in `GATEWAY`, which records where the CLI lives rather than widening M#3.
- [x] 7.QG.3 [D] - `uv run pytest --cov` | DoD: **1047 passed, coverage 96.19 %, 03/08.** Split-repository suite green on both published repos. `core/ui/*` stays excluded from coverage (rendering), but the local-truth test is **not** — it is a correctness test, not a rendering test.
- [ ] 7.QG.4 🧑 [B] - **Milestone M7 observed** — **1 of 3 done, 05/08** | DoD: Summary reaches the inbox; GUI shows live state; Replay reproduces a recorded series with `Verified OK`. **The only part of Phase 7 code cannot finish.** Three human steps, none blocked by anything but a person:
  - [x] **Send one real message through the live path.** ✅ **Done 11/08.** `uv run python scripts/gmail_consent.py --test-to itay.malich2@gmail.com` — Gatekeeper, message builder and Gmail API, end to end, confirmed received. The body carries no match data and the payload is an attached `gmail_selftest.json`, so the format a grader parses is JSON and never free text (M#33, M#34). ⚠️ **This was recorded as "blocked on Diana's OAuth consent" and it never was:** the sender is Itay's account, his credentials and token are in `C:\Users\itaym\.p2p-secrets\`, and the consent had already been run. The *report* for a real match still needs a match to report — 9.5.8 sends it when the sixth sub-game files.
  - [x] **Screenshot the Live GUI** — `uv run python -m core peer --role police --gui`. **Captured 05/08, `docs/evidence/m7-live-gui.png`.** Banner, 7×7 heatmap, own marker, status line. ⚠️ It shows the **starting position**, which is honest and not yet the whole DoD: at step 0 the prior is uniform, so every cell renders at peak intensity and the board is a flat wash of red. That is the heatmap telling the truth — a uniform posterior has no structure to show — but a screenshot of *evolving* belief needs the turn loop (Phase 9) and the `--gui`/`--serve` combination noted under 7.4.1.
  - [x] **Screenshot `Verified OK`** — ✅ **Captured 11/08, `docs/evidence/m7-replay-verified-ok.png`**, with its source log beside it as `docs/evidence/replay-source-log_g01.json`. ⚠️ **This was recorded as blocked on Phase 9 because "self-play produces no seals to verify", and that is true of `scripts/selfplay.py` and false of `tests/integration/series_harness.py`** — four peers through the real handshake, real commitments, real nonces, `verify_log` green. The frame shown is **step 9/12, a `STAY` that walls a cell**, chosen deliberately: see the bug below. Replace it with a frame from a counted match once one exists; nothing about the tool changes, only the provenance of the log.
  - 🐛 **The viewer contradicted its own banner, and this screenshot is what found it.** `ReplaySession.step_ok` re-hashed with `scent_digest` and **without** `sealed_barrier_cell`, so it rebuilt a payload the sealing peer never hashed. `verify_all` goes through `match_log.records`, which reads both keys — so the window showed a green **Verified OK** over a red **MISMATCH**, on an honest log, on the one artefact whose entire job is to prove integrity. A placement moves as `STAY`, so the accused steps were exactly the Cop's most consequential. Fixed in `core/report/replay.py`; three tests in `test_replay.py` — the walling step verifies, every step mark agrees with the whole-log verdict on clean logs, and a forged barrier cell is still caught so the fix is not a blanket pass. **`sealed_log()` never placed a barrier, which is why five earlier tests over this file all passed.**

## Phase 8: Advanced Strategy — the competitive edge
**Priority:** P1 | **Status:** ✅ **Complete 06/08** — 8.1 ✅ · 8.2 ✅ 05/08 · 8.3 ✅ 06/08 · gate closed | **Target:** starts once Phase 4 lands; runs parallel to 5–7
**DoD:** The advanced brains beat the Phase 3 baselines in ≥70 % of self-play sub-games, measured on
the harness built at 3.5.
**This is where the league grade lives.** See `PRD_strategy_advanced.md`.

### 8.1 Cop — the role that breaks ties — ✅ complete 05/08
Between two competent teams every sub-game ends in survival, the series ties, and each takes 2.
The cop carries a 15-point spread against the thief's 5, and is the only role that can win outright.

**Shipped as five modules, not one brain.** `police/search.py` (expectimax), `police/evaluation.py`
(what a position is worth), `police/barrier_policy.py` (whether to wall, and which), `police/phases.py`
(which plan is in force), `police/advanced.py` (the 4-step turn), over a new shared primitive
`core/domain/cuts.py`. The split is the 150-LOC rule doing its job — 8.QG.2 predicted brains grow
fastest — and it is why each rule below could be tested on a hand-drawn board rather than inferred
from a self-play batch.

**Measured against the baseline, 16 mirrored openings, same engine a graded match runs on**
(`tests/integration/test_advanced_selfplay.py`):

| | captures | mean steps | barriers | **self-separations** |
|---|---|---|---|---|
| baseline cop | 16/16 | 17.75 | 0 | **0** |
| advanced cop | 16/16 | **9.00** | 12 | **0** |

Win rate saturates because the baseline thief loses to both — the honest metric is time to capture,
and it halves. A win-rate comparison worth making needs 8.2's thief to lose to.

⚠️ **Not yet fielded.** `[strategy] cop_class` is unset, so both peers still load the baseline. The
project's own rule is measure-then-adopt (8.3.6, 8.QG.4), and adopting before the Phase 8 gate would
be exactly the shortcut that rule exists to prevent. One line switches it when the gate is green.

- [x] 8.1.1 [D] - Expectimax over the belief map, depth 2–3 | DoD: **Done 05/08 — `police/search.py`.** Depth from `[strategy] search_depth` (A1.3) via a new `BrainBase.configure` hook, since the loader builds every brain the same way. **17.5 ms per turn at depth 3** on the worst case (open board, uniform belief) against a 30 s deadline; 71 ms at depth 4. Chance nodes propagate the posterior with the same `predict` the live filter uses — a search using a different transition model would be searching a game the filter is not playing.
- [x] 8.1.2 [D] - **Connectivity constraint** replacing the old mobility guard | DoD: **Done 05/08.** Hard penalty ∝ believed thief-mass outside `component(cop)`, weighted 400 against the next term's 0.6: stranding is not a weak position, it is a lost sub-game. **Co-confinement scores strictly higher than staying outside** on the same walls and the same belief — asserted, because the two boards look nearly identical and are opposite in value. (PRD advanced §3.2)
- [x] 8.1.3 [D] - Reward shrinking the **shared** component | DoD: **Done 05/08.** `−β·|component|·mass_inside`. Weighted by the mass actually in the region, so walling an empty corner scores exactly zero — otherwise the cop spends its quota tidying the far side of the board.
- [x] 8.1.4 [D] - **Wall-behind-yourself rule** | DoD: **Done 05/08.** Expressed as a *mass comparison* rather than a geometric between-ness test, which also catches the subtle case: a wall that looks behind us but closes the last corridor round a region.
  - 🐛 **Caught by the end-to-end test: the guard refused the winning move.** Sealing the thief's last exit puts it outside our component *by construction*, so a check reading the belief as it stood before the placement saw the worst thing on the board and vetoed a capture. Stranding is now judged on the mass that **survives** the placement — mass a wall captures is not mass we failed to reach. Before the fix the cop placed **0 barriers across all 16 openings** and still won every one, so nothing about the result looked wrong.
- [x] 8.1.5 [D] - Diagonal minimum cuts | DoD: **Done 05/08 — `cuts.diagonal_support`.** Off-board corners count alongside placed ones: the board edge is wall we did not pay for, and a scoring that ignored it would send the cop off to rebuild the border it already had.
- [x] 8.1.6 [D] - Cycle elimination as the barrier objective | DoD: **Done 05/08 — `cuts.region_has_cycle`.** Counted, not searched: a connected region has a cycle exactly when its edge count reaches its vertex count. Cheaper than a back-edge hunt on 49 cells and it cannot miss a cycle the way a traversal with a visited-set bug can.
- [x] 8.1.7 [D] - **One-placement rule** | DoD: **Done 05/08.** Implemented as *never start a cut you cannot finish*: sealing a cell means blocking every exit it has, so its exit count after this wall is a lower bound on the walls still needed, and a placement is refused when that exceeds the remaining quota. The literal reading — refuse anything not one wall from a seal — would forbid every barrier until the endgame and contradict §3.4's Phase B, which spends 4–6.
- [x] 8.1.8 [D] - **Win condition: drive thief exit count to 1 while adjacent to that exit** | DoD: **Done 05/08 — `evaluation.endgame_mass`.** Targeted explicitly, weighted 60. A cop rewarded only for smaller regions shrinks them from the wrong side and never takes the last step. **Standing *on* the last exit counts too** — Ch. 3.4 lets the cop wall its own cell, and an adjacency-only test scored the strongest position on the board at zero.
- [x] 8.1.9 [D] - Three-phase plan: herd (0 barriers) → seal → squeeze | DoD: **Done 05/08 — `police/phases.py`.** Entropy, exit count and region size drive every transition. ⚠️ The shipped `barrier_hold_until_turn = 8` contradicts A1.11 head-on; reconciled by making it **suppressive only** — it can hold us in HERD and can never itself cause a wall. Recorded as **CONTRADICTIONS C-015**; measured inert across all 16 openings.
- [x] 8.1.10 [D] - Opponent-type gate on the phasing | DoD: **Done 05/08.** Two coarse traits behind a 6-sample gate (8.3.2). Profiled from the **belief peak's trajectory**, not from sight — `core/domain/opponent_model.py` takes an observed position and the cop never has one (M#8). A fleer earns a stricter sealing threshold; an orbiter triggers SEAL wherever it stands and lifts the turn floor.
- [x] 8.1.11 [D] - Entropy-aware pursuit on a multimodal posterior | DoD: **Done 05/08, and the requirement needed correcting first.** A1.13 asks for the move that most reduces expected entropy after the next observation. **That term is identically zero here**: our sensor is the opponent's transmitted scent field, which arrives whole and reads the same whichever cell we stand on. There is no information to gather by moving. What multimodality actually changes is which move is *cheapest*, and belief-weighted expected distance gets it right where an argmax chase does not — asserted against the baseline on a posterior whose peak is a peak only because ties break on coordinates, six steps away, while three quarters of the mass sits two steps away. A1.14 then falls out free: a concentrated posterior makes the two objectives the same objective.
- [x] 8.1.12 [D] - No barrier while belief entropy is high | DoD: **Done 05/08.** Two independent guards — the phase machine holds HERD, and `rejection_for` refuses regardless of phase. Redundant on purpose: a bad wall is permanent, and permanence earns the second check.

**Also touched, deliberately.** `BrainBase.configure` (a no-op hook, so the baselines need no config
and the loader stays uniform); `load_brain(spec, role, config)`; the M#25 architecture test, which
keyed on the module *name* `"brain"` and would have waved all five new strategy modules through — it
now covers the role packages, which is what the rule always meant.

- 🐛 **The split-repository gate caught two things the other four gates could not.** (1) The new
  police unit tests imported `police.*` at module level, which kills the thief repo during
  *collection* — before any skip marker runs, so `needs_brain` cannot help. Fixed with
  `collect_ignore_glob` in `tests/conftest.py` plus a `test_cop_` filename prefix, so a role-only
  test says so in its own name. (2) A **pre-existing break in the uncommitted 7.3 work**:
  `test_the_mailer_shares_the_peers_one_gatekeeper` paired `PRESENT_ROLES[0]` with a hardcoded
  `Role.COP`, so the thief repo tried to load the police brain. Both were invisible to ruff, pytest
  and the LOC check in a working tree that holds both roles.

### 8.2 Thief — full tactic set, value measured not assumed — ✅ complete 05/08
Retained in full. Whether each tactic earns its keep is settled by ablation (8.3.4), not by prior belief.

**Shipped as four modules**: `thief/evaluation.py` (what a position is worth), `thief/search.py`
(expectimax, depth 2), `thief/trail.py` (our own emission, reconstructed), `thief/anchor.py` (the
false anchor), assembled in `thief/advanced.py`.

⛔ **SUPERSEDED 06/08 — the table below was measured through the 4.1.6 scent-timing
defect.** The harness fed both belief filters the opponent's *current-turn*
deposit, which commit-reveal cannot deliver. No brain changed; the measurement
did. **The current figures are in §8.3.6**, and the summary of what moved is:
the baseline cop fell from 48/48 captures to 27/48 (most of its old score came
from scent it could not have read yet), the advanced cop still captures 48/48,
and the advanced thief survives 42/48 against the baseline cop and 40/48 against
our own advanced cop. **Every 8.2 adoption decision survived the re-measurement**,
including 8.2.6's rejection of the false anchor. Kept as the record of what was
measured at the time.

**The full 2×2, 48 mirrored openings, `survival_threshold = 35`**, measured after the C-006b
barrier-timing fix (`tests/integration/test_advanced_thief_selfplay.py`):

| thief survival | baseline thief | advanced thief |
|---|---|---|
| **baseline cop** | 0/48 · 14.67 steps | **46/48** · 34.38 steps |
| **advanced cop** | 0/48 · 8.17 steps · 24 walls | **40/48** · 30.42 steps · 41 walls |

**Self-separations are 0 in every cell.**

Survival rate is the honest metric here and it does **not** saturate: the baseline thief survives
nothing, so every point above zero is real. That is the reverse of 8.1, where both cops caught the
baseline thief every time and time-to-capture had to stand in.

⚠️ **The advanced cop's 8.1 numbers were measured against the baseline thief only.** Against a
competent evader it captures 8 of 48. That is the real competitive picture and it is not a regression
— it is the first honest measurement of the cop.

🐛 **8.2 also found a rules defect in the engine, and fixing it was worth four sub-games.** The turn
loop handed `BarrierManager.place` the **pre-move** thief position, so a thief stepping onto the cell
the cop was walling ended the turn standing *inside* the barrier and walked out again next turn — a
state no rule describes. Found because the advanced thief reaches positions the baseline never did.
Resolved as a **capture** (M#46 under `after_moves`, which is C-006b's own stated rule); see
CONTRADICTIONS C-006b and `tests/unit/test_simultaneous_barrier.py`. It also cleared 8.QG.4's
separation blocker: the four "self-separations" were `are_connected` failing to reach a thief inside
a wall, not the cop walling itself off.

- [x] 8.2.1 [I] - Escape-route maximisation under the belief map | DoD: **Done 05/08 — 0/48 → 46/48 survivals against the baseline cop.** `k_step_reach` five steps out, weighted by the posterior over the cop rather than a point estimate (A2.2). Depth 2, not the cop's 3: the cop is hunting and needs to see a capture coming, we are running and what kills an evader is the one-move blunder into a sealable cell.
- [x] 8.2.2 [I] - **Never let exit count reach 1** while the cop is within placement range | DoD: **Done 05/08 — `evaluation.capture_risk`, weighted 400 against the next term's 30.** All three endings checked, because the cop takes whichever is available: no exits at all (M#47), one exit the cop can wall (§2.2), or the cop simply adjacent. **Standing *on* our last exit counts** — Ch. 3.4 lets the cop wall its own cell, and an adjacency-only test misses the most dangerous square on the board. Returned as mass, not a veto: a 30% chance of capture is a price to weigh.
- [x] 8.2.3 [I] - Scent-aware movement — own emission treated as a cost | DoD: **Done 05/08 — `thief/trail.py`.** `Observation` carries no record of what we have emitted, so the brain **reconstructs** it from its own position history — exact, not estimated, and it behaves identically in self-play and in a real match (a field plumbed through `PeerRuntime` would be empty, since `belief()` is still the Phase 4 placeholder). The decay rate and model come from the *negotiated* `[pheromones]` section, because C-007 means either model may have been signed.
  - 🔬 **The DoD's premise turned out to be false, and this is the finding of 8.2.** It says re-emission "plateaus at full strength", implying lingering is loud. It does not accumulate at all: `scent.merge` keeps the **maximum**, so re-emitting on a cell you already occupy restores exactly the values already there. Five turns of standing still produces a field byte-for-byte identical to one turn — 25 cells, total intensity 7.14 — while five turns of *moving* leaves 34 cells and 12.51. **Movement accumulates scent; repetition does not.** Measured in `test_thief_trail.py`.
- [x] 8.2.4 [I] - **Cycle preservation** | DoD: **Done 05/08.** Reuses `cuts.region_has_cycle` — the same primitive the cop uses to *destroy* cycles, which is the point: 8.1.6 and this are the two sides of one measurement. `evaluation.seal_pressure` prices the cop's remaining quota (A2.8), so fourteen walls and two walls are read as the different games they are.
- [x] 8.2.5 [I] - False-anchor tactic | DoD: **Built 05/08, and shipped disabled — see 8.2.6.** A2.10 enforced literally: `payoff` is the head start the break can actually convert, bounded by how far the cop must travel, against a `cost` of the turns spent. Danger cancels it mid-bluff in either stage, because a tactic that ran to completion regardless would be a scripted sequence and A3.2 forbids exactly that.
  - 🐛 **The gate was `risk <= 0.0` and never once fired.** `belief.normalise` leaves unreachable cells holding denormals around 1e-18, so on a board where nothing could reach us the comparison was still false. Both ablation arms came back byte-identical, which reads exactly like *"the tactic does nothing"* rather than *"the tactic never ran"* — the most dangerous kind of null result. Now a stated 2% policy threshold.
- [x] 8.2.6 [I] - Measure the false anchor | DoD: **Done 05/08 — measured, and it loses. Shipped `false_anchor = false`.**

| 48 openings vs advanced cop | survivals | mean steps |
|---|---|---|
| anchor **off** | **40/48** | 30.42 |
| anchor **on** | 37/48 | 29.17 |

  Three sub-games lost, net. The mechanism explains it: per 8.2.3 the turns bought no extra ambiguity, so *"those turns can be bought cheaply"* is the part of §4.4 that is false — against a closing cop every one of them is distance not gained. The verdict held either side of the C-006b fix (44 → 37 before, 40 → 37 after), which is the strongest evidence available that it is the tactic and not the engine.
  - ✅ **Re-measured 06/08 on the corrected engine and the verdict is unchanged: 40/48 with the anchor off, 36/48 with it on.** This is now the *third* engine the tactic has lost on — before C-006b, after it, and after the 4.1.6 scent-timing fix. A shipped decision resting on a measurement taken through a defect had to be re-run rather than assumed, and this one holds.
  - ⚠️ **A 16-opening sweep said 12/16 → 16/16 and would have had us adopt it.** The narrow set happened to hold exactly the games the tactic fixes and none it breaks. **This is why 8.1's A/B numbers were re-measured on 48 openings too.** The suite keeps the 16-opening version as a fast regression tripwire; the 48-opening figures are the evidence.

**Also fixed.** `selfplay._observe` hardcoded `barriers_remaining = 0` for the thief, while
`PeerRuntime.observe` has always passed the true count for both roles. Every placement is declared
with its exact cell (M#15), so counting what the cop has left is public arithmetic — and a thief
tuned in self-play against a zero would have met a different observation in a graded match. A2.3 and
A2.8 both need the real number.

### 8.3 Shared — ✅ complete 06/08

**The verbal layer is now real.** `hint_parser`, `reliability` and `belief_hints`
were finished in Phase 4 and wired to **nothing**: `Decision` carried no claim or
intent, the harness passed no hints, and neither advanced brain read
`Observation.hints`. 8.3 joined them end to end — the brain decides truth or lie
and which bearing to claim, the harness writes the sentence through the real
`HintWriter` on the template bank (zero tokens, deterministic), and the opponent
parses it, scores it and folds it into its posterior. Only then could 8.3.4 and
8.3.5 be *measured* rather than asserted.

**Shipped as four shared modules**, in `core/domain/` rather than a role package
because both roles need every one of them: `tiebreak.py` (the seeded near-tie
draw), `opponent_profile.py` (the four gated traits), `bluff.py` (truth or lie,
and which bearing), `verbal.py` (the three joined in protocol order). `trail.py`
moved out of `thief/` for the same reason — **both agents emit**, so the Cop
needs its own trail to price a claim against, and a module in `thief/` does not
exist in the Cop's repository.

- [x] 8.3.1 [D] - **Unexploitable default** | DoD: **Done 06/08 — `core/domain/tiebreak.py`.** Actions within ε of the best are drawn from a seeded generator; the seed is `[game] seed` and is recorded in the match log. **The draw is in the brain, never in the search** — `best_move` and `expectimax` stay strictly deterministic, because a search that wobbled internally would make our own log unverifiable, which is a worse problem than being readable. `epsilon = 0` restores the fixed ordering exactly, which is what makes the ablation's control arm a control rather than a second randomiser. No fixed lie schedule and no rhythmic movement follow from 8.3.4 and from the draw respectively.
- [x] 8.3.2 [D] - Opponent profiling — **at most 4 traits, confidence-gated** | DoD: **Done 06/08 — `core/domain/opponent_profile.py`.** Movement style, barrier rate, hint-responsiveness, reliability `r`. Every one answers **`None` below its gate, never a default**: "unknown" and "measured as zero" lead to opposite behaviour, and a trait returning 0.0 before it had evidence would trigger the exploitation it exists to gate.
  - ⚠️ **The four named in A3.6 plus the orbit detection already shipped in 8.1.10 is five.** Resolved by reading flee and orbit as **two thresholds on one measured quantity** — one observation stream, one sample gate, one mutually-exclusive answer — rather than as two traits. Recorded as **CONTRADICTIONS C-016**.
  - 🐛 **`[strategy] max_profiled_traits = 4` had shipped since Phase 0 and was read by nothing.** The weakest possible form of a limit: a fifth trait could have been added without one test noticing. It is now compared against `opponent_profile.TRAITS` by a test, against the **shipped** config rather than a literal.
  - **Hint-responsiveness counts perpendicular moves.** Two of the four bearings are always across the claim, so an opponent moving at random lands there half the time; dropping those samples would leave one-in-four along against three-in-four not-along and report a coin-flipper as strongly responsive. Direction of the reaction is deliberately not assumed — a listening Thief runs *from* a claim and a listening Cop runs *toward* it, so what is measured is the imbalance, not its sign.
- [x] 8.3.3 [D] - Profile resets between opponents | DoD: **Done 06/08.** Two scopes, and keeping them apart is the whole task: trait counters **bank** across the six sub-games of a series, while the trajectory they are measured from — the last peak, the cells already visited, the trail, the draw stream — restarts at every boundary. A cell "revisited" across two different sub-games says nothing about whether this opponent circles. Cleared for a new team by `OpponentProfile.for_opponent`, exposed as `brain.meets(team)`; the ordinary boundary is the **process** (M#1, M#4 — one process, one role, one peer, and no team name crosses the wire), and the hook exists for a series runner that outlives it. Asserted end-to-end on a six-sub-game series, not just on the unit.
- [x] 8.3.4 [D] - **Cheap-truth bluff policy** | DoD: **Done 06/08 — `core/domain/bluff.py`. Measured: worth 8 sub-games in 48 to the Cop, and exactly 0 to the Thief.** Information value is `1 − bearing_leak`: how plainly our own reconstructed field already announces the direction we are about to move in. Low → the truth is free and banks credibility (A3.8). High → consider a lie, weighted by credibility banked (A3.9), claiming the reverse bearing — which is derived from the move we actually chose, so it is board-driven and not a schedule (A3.2).
  - 🐛 **The first information-value measure was saturated on every turn of every game, and the null result would have looked exactly like a tactic that does nothing.** It read the trail's strength at our own cell — but the trail is updated before the claim is chosen, so that cell always carries a full-strength deposit we laid this turn. Every turn priced as "they already know", and no lie was ever eligible. The same failure shape as the false anchor's gate in 8.2.5, caught the same way: by asking why an arm came back suspiciously flat. **A single deposit reveals a position; only the asymmetry between deposits reveals a bearing.**
  - The gradient is taken over the **whole field split along the heading axis**, not over the two adjacent cells: the tail that carries the signal sits two and three cells back, and the neighbouring pair is dominated by this turn's symmetric window. A four-step run north reads 0.13 the narrow way and 0.81 the right way.
  - **The lie draw weights on `trust`, not on the raw coefficient.** Drawing against the coefficient converges to *p* = 0.5 — precisely the "mixed" record `reliability.py` calls worthless, where an opponent ignores our lies *and* our truths, and the bank we spent turns filling buys nothing. `trust` is 0 at a mixed record, so **credibility must be banked before it can be spent** — literally A3.9 — and the loop settles near two truths to one lie.
  - `cheap_truth = 0.60` comes from the measured distribution, not from taste: claiming the way we have actually been walking reads 1.00 after two steps, 0.69 after three, 0.54 after four and 0.31 after six, while a turn reads 0.74 and a reversal 1.00.
- [x] 8.3.5 [D] - Disable the verbal layer when hint-responsiveness ≈ 0 | DoD: **Done 06/08.** Below the floor we claim nothing at all — legal, always truthful, and the correct use of the channel against someone measured deaf. Gated on a **confident** reading: `None` means we have not looked, which is not the same as looking and finding zero, and conflating them is the one way this fires against an opponent who was listening all along.
- [x] 8.3.6 [B] - Self-play benchmark on the 3.5 harness | DoD: **Done 06/08 — `tests/integration/test_advanced_league_benchmark.py`, 192 sub-games, both roles, seeded.** 48 mirrored openings (every cell of the 7×7 bar the centre, where the mirror puts both agents on one square) × the full 2×2 of brains. See the tables below.
  - 🐛 **The 8.2 suite reported every figure as *n*/48 and ran 16.** `range(0, 7, 2)` yields four values per axis, so `OPENINGS` has always held sixteen mirrored pairs. The figures were reproducible at the time — the first ablation's control arm returned 40/48, 30.42 steps and 41 walls exactly — but **no committed test performed the run they came from**, so the eight sub-games between 40/48 and the tripwire's threshold were unguarded. That exactness is also what made the whole set look trustworthy right up until 4.1.6 was found: it was faithfully reproducing a game neither peer can play. Sample sizes are now *asserted* rather than described, and the 16-opening module is honestly relabelled as the fast tripwire it always was.
  - 🐛 **No integration benchmark had ever loaded the shipped configuration.** Brains were built from code defaults, so every config-only setting — search depth, evaluation weights, `false_anchor` — was measured at whatever the dataclass said rather than at what a graded match loads. They agreed by coincidence until 8.3 needed a per-role split (`bluff_enabled` on for the Cop, off for the Thief), which only the config files can express. The benchmark now calls `configure(load_config(role_dir(role)))`.
  - ⚠️ **`test_it_survives_our_own_advanced_cop_most_of_the_time` was a broken gate and 8.3 was the first thing to break it.** Advanced-vs-advanced is zero-sum, so a 70 % floor on the Thief is a 30 % *ceiling* on the Cop — in the role with the 15-point spread. It went red because the Cop's verbal layer started working. A test that fails when the other role improves is measuring the wrong thing; A4.2's gate belongs against the **baselines**, where it is not zero-sum, and that is where it now lives.

#### 📊 8.3.6 — the shipped configuration, 48 openings, 192 sub-games

Re-measured 06/08 with the scent timing corrected (4.1.6). Thief survivals:

| thief survivals | baseline thief | advanced thief |
|---|---|---|
| **baseline cop** | 21/48 · 19.62 steps · 0w | **42/48** · 32.25 steps · 0w |
| **advanced cop** | **0/48** · 8.96 steps · 27w | 40/48 · 31.50 steps · 47w |

**Self-separation is 0 in all four cells.** Both A4.2 gates clear with room: the
Cop captures **48/48** against the baseline Thief and the Thief survives **42/48**
against the baseline Cop.

⚠️ **The baseline Cop's own capture rate fell from 48/48 to 27/48 under the
correction**, so most of what it used to score was borrowed from scent it could
not have read yet. The advanced Cop's 48/48 is unchanged — the gap between the
two is *wider* than the old numbers showed, not narrower.
- [x] 8.3.7 [D] - Unit tests for every scoring heuristic | DoD: **Done 06/08.** `test_tiebreak.py`, `test_opponent_profile.py`, `test_bluff.py`, `test_verbal.py` — 73 new tests, deterministic on fixed boards.

#### 📊 8.3.6 — the ablation, 48 openings, advanced Cop vs advanced Thief

**Re-measured 06/08** once the scent timing was corrected (4.1.6), as a
**leave-one-out from the shipped configuration** rather than a build-up from
zero — which is the form that actually answers *"does each thing we ship earn
its keep?"*. Cop captures out of 48:

| arm | cop captures | mean steps | walls |
|---|---|---|---|
| **SHIPPED** | **8/48** | 31.50 | 47 |
| − cop near-tie draw | 4/48 | 33.75 | 80 |
| − cop verbal layer | 2/48 | 34.79 | 24 |
| − thief near-tie draw | 8/48 | 31.50 | 49 |
| + thief verbal layer | 10/48 | 31.46 | 63 |
| **CONTROL** — no 8.3 on either side | **0/48** | 35.00 | 43 |

⚠️ **The first version of this table was measured through the 4.1.6 timing hole
and its control arm reproduced §8.2's numbers exactly — which is why it looked
trustworthy.** It was: it faithfully measured a game neither peer can play. Every
adoption decision below survived the correction, and two are now better
supported than they were.

**8.3 as a whole is worth 8 captures in 48.** Without it the advanced Cop takes
*nothing* off the advanced Thief; with it, 8. In the role carrying a 15-point
spread against the Thief's 5, that is the phase paying for itself.

**Near-tie draw: adopted for both roles, at different widths.** Removing it from
the Cop halves its captures (8/48 → 4/48). For the Thief it is **measurably
neutral** in the competitive cell (8/48 either way) and is kept anyway, because
A3.1 is a requirement rather than an optimisation: a deterministic tie-break is a
signature an opponent learns for free, and 0.1 buys unexploitability at a
measured cost of zero.

ε was swept rather than left at the first value that worked, and the two roles
came out with **opposite optima** — the sweep below predates the 4.1.6 timing
fix, so read it as *why the widths differ*, not as current absolute figures:

| ε | 0.0 | 0.05 | 0.1 | 0.25 | 0.5 | 1.0 |
|---|---|---|---|---|---|---|
| **Cop** — mean captures/48 vs our advanced Thief, 3 seeds | 14.0 | 15.3 | 14.0 | 15.3 | **18.0** | — |
| **Thief** — mean survivals/48 vs the baseline Cop, 5 seeds | 46.0 | 46.4 | **46.4** | 44.0 | 44.0 | 44.6 |
| **Thief** — range over those seeds | 46–46 | 44–48 | 44–48 | 40–48 | 40–48 | 43–48 |

**Shipped: `tie_epsilon = 0.5` for the Cop, `0.1` for the Thief.** Not a
contradiction — ε is in *evaluation units* and the two evaluations do not share
a scale. The Cop's is dominated by separation at 400 and capture at 1000, so
moves within half a point really are interchangeable and shaking the pursuit
line out of a deterministic groove finds captures. The Thief's largest
positional term is 2.0 per cell of escape room, so half a point there spans
genuinely different moves: at 0.5 it costs 2.4 sub-games on average and doubles
the spread, and actions that far apart are not ties. **A single shared ε would
have been wrong for one of the two roles, and 0.5 was wrong for the Thief.**

**Verbal layer: adopted for the Cop, `bluff_enabled = false` for the Thief.**
It is the **largest single contributor in Phase 8**: removing it from the Cop
drops captures from 8/48 to 2/48, three quarters of everything 8.3 is worth.
Turning it *on* for the Thief hands the Cop two more captures (8 → 10), so the
Thief ships silent. A3.10 explains the asymmetry — the lie's job is *herding*,
and the Cop is the role that herds; the Thief has nothing to herd and most of
its turns are cheap truths, which simply help a listening opponent.

⚠️ **Under the old timing this read as "neutral for the Thief", and the decision
to ship it off rested on the argument that measured-nothing against unmeasured
downside is not a trade.** The correction turned that argument into evidence: it
is not neutral, it costs two sub-games. Same decision, and now it does not need
the argument. Revisit in Phase 9 against real opponents, where 8.3.5 switches it
off automatically for anyone who ignores hints anyway.

**Barrier rate is measured and deliberately not acted on.** §5.2 says it should
drive the Thief — a Cop that never walls cannot catch us — and the change cannot
be measured here, because **the only opponent in this repository that exhibits
the trait is one we already beat 48 out of 48**. The baseline Cop places no
barriers and the advanced Cop spends its quota, so self-play holds no game where
acting on a low barrier rate could change an outcome. Reported in
`describe()` and left there, in the same posture as `decayed_coefficient`.

### ✅ Phase 8 Quality Gate — closed 06/08
- [x] 8.QG.1 [B] - `uv run ruff check .` | DoD: **0 violations, 06/08**, with 8.3 landed.
- [x] 8.QG.2 [B] - `uv run python scripts/check_file_size.py` | DoD: **No file over 150 LOC, 06/08.** Fourteen strategy and verbal-layer modules now, not one over the limit — the split doing its job rather than luck.
- [x] 8.QG.3 [B] - `uv run pytest --cov` | DoD: **1306 pass, coverage 96.1 %, 06/08.**
  - ⚠️ **The benchmark cost the commit gate 11 minutes and now has its own.** 192 sub-games of expectimax run in 2:00 untraced and **12:14 under `--cov`** — a 6× tracing penalty that took `ship.py`'s test gate from 4:47 to 15:48, on the path used for every single commit. Split: `pyproject.toml` deselects `-m 'not slow'` from the default run, and `pipeline.GATES` gains a sixth step running `pytest -m slow --no-cov`. It is **deselected, never skipped** — it still blocks every commit, because a headline number nobody re-checks is precisely how the 16-vs-48 discrepancy survived a whole phase. Nothing is lost to the missing trace: `police/` and `thief/` already report 98–100 % from the unit suite. Default gate is back to **4:07**, plus 2:00 for the benchmark.
- [x] 8.QG.4 [B] - Self-play benchmark | DoD: **Closed 06/08 on 192 sub-games at the shipped configuration.**
  - Both halves clear 70 % against the **baselines**, which is where A4.2's gate belongs: the cop captures **48/48** in 8.96 mean steps where the baseline cop manages 27/48 in 19.62; the thief survives **42/48** where the baseline thief survives 21/48. Re-measured 06/08 on the corrected engine (4.1.6).
  - ✅ **Self-separation is 0 in all four cells of the matrix.** It briefly read 4 against the advanced thief in 8.2, which turned out to be `are_connected` failing to reach a thief standing *inside* a barrier rather than the cop walling itself off — the C-006b defect above. Fixed at the cause; the counter is measuring what it claims to.
  - The 8.2 note "win rates are in… the cop captures 16/16" described the **16-opening** tripwire while reading as though it were the 48-opening run. Both numbers now say which set they came from, and the set is asserted in the test rather than described in prose.

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

#### ⚙️ 9.1 machinery — landed 06/08, boxes stay open until a real opponent ticks them

Every DoD above ends in *"both sides confirm"*, so none of them can be closed by code. What code can
do is make each one **executable and evidenced** instead of remembered, which is what landed:

```
uv run python -m core negotiate --role cop                        # our side + the clause
uv run python -m core negotiate --role cop --pack outbox/         # what we send them
uv run python -m core negotiate --role cop --review their.json    # what they sent us
uv run python -m core negotiate --role cop --opponent <url> --out results/
uv run python scripts/rehearse_handshake.py                       # warm-up, handshake only
```

Every one exits non-zero when the answer is no, so a match cannot be started from a script that
ignored the verdict.

- **`--pack`** writes the three files an opponent needs into one directory: `game.json` (the file
  they load byte-identically — the config travels as *the file we hash*, never as a paraphrase),
  `handshake.json` (exactly what our peer sends, so they can diff before connecting) and
  `AGREEMENT.md` (the clauses, the digests, and the four things we need back). A test asserts the
  digest of the file we send equals the figure printed beside it — if those ever diverge the
  handshake refuses and the fixture is lost to a formatting decision nobody looked at.
- **`--review`** reads a `game.json` **they** proposed and splits it into refuse / settle / legal
  changes / unrecognised. `load_config(enforce_rules=False)` was written for exactly this and had
  no caller but a test — the same wired-to-nothing shape as the verbal layer and 4.1.6. It runs
  *before* our own proposal is built, so reviewing their file cannot fail because our league log
  has a typo.
- **`rehearse_handshake.py`** runs the whole protocol between two local peers over the real FastMCP
  transport (M#52 permits warm-ups). It proves the exchange serialises, registers, decodes and
  settles end to end — both bugs found this phase were of exactly that shape, invisible to unit
  tests and fatal on the wire. It proves **nothing** about agreement: identical peers always agree,
  which is why every refusal is unit-tested against hand-built messages instead. The artefact is
  filed under a `bestteam-vs-bestteam` game id, because a rehearsal that could be mistaken for a
  counted match would be worse than no rehearsal.
- 🐛 **Our `PARAMETERS` table mixes Appendix F's rows with six we invented, and `violations()`
  reported a missing key as illegal.** An opponent sending a plain Appendix F config carries none
  of `decay_model`, `capture.*` or `seal_scent_digest` — and we would have refused them over rules
  the book does not state. `Parameter.ours` makes the distinction machine-readable (it was a
  comment) and `classify()` splits *illegal* from *absent*: the first refuses under M#12, the
  second is settled with a human. Same "silence is not disagreement" mistake as the handshake, in a
  second place.
- ⚠️ **The first reviewer contradicted itself**, listing a lowered minimum as a legal judgement call
  four lines below refusing it. One `config_spec.legal()` predicate now answers both callers. A
  document that argues with itself in front of the opponent it is meant to convince is worse than
  one that is simply wrong.
- ⚠️ **`core.cli_negotiate` was caught by the M#3 layering test on the run that created it** — a new
  module quietly acquiring gateway privileges is not something anyone spots in review, which is the
  whole reason the architecture is written down rather than remembered.

- **`core/protocol/negotiation.py`** — PRD_negotiation §4's interface, at last, in three functions
  rather than one and with the network taken out (**C-017**). `settle()` returns `AGREED` or one of
  five refusals and knows nothing about the environment, so every refusal is provokable from two
  plain dataclasses instead of only the one the happy path reaches.
  **`core/protocol/agreement.py`** holds the verdict and the artefact;
  **`core/runtime/prematch.py`** gathers the environment half — git, the league log, the provider.
- ⚠️ **The handshake is asymmetric and only one side gets a verdict.** Whoever answers raises a
  `ProtocolError`; whoever asked receives it as a remote error string. Found by the CLI test, which
  expected exit 1 and got a traceback. `REFUSED_BY_OPPONENT` is that case, and it files the record
  with their wording preserved — a refusal is the outcome most likely to be argued about, so it is
  the one that most needs to be on disk.
- 🐛 **`on_negotiate` echoed the opponent's own values back at them.** `game_count`, `role_split`
  and `readings` were copied from the incoming message into the reply, so the exchange was
  structurally incapable of detecting the disagreements it exists to detect — agreement was
  guaranteed, because we repeated whatever arrived. 9.1.2, 9.1.3, 9.1.6 and 9.1.8 all had a field
  on the wire and **no comparison behind it**. Same shape as 4.1.6: the DoD was ticked, the
  plumbing was absent, and nothing failed loudly enough to say so.
- **Silence warns, contradiction refuses.** Half of this handshake is our own extension of Appendix
  F. A peer that never built `scent_model_digest` is not disagreeing with us, and refusing would
  forfeit a fixture over a rule the book does not state (§3.6b); a peer that sent one and disagrees
  refuses the match. The two paths are tested separately, because collapsing them is the cheap
  mistake in either direction.
- 9.1.3 🐛 **the counted total is read from `docs/LEAGUE_LOG.md`, never typed.** Nothing takes the
  number as a parameter, and `counted_matches()` refuses when the table and the prose total
  disagree rather than guessing which is true. Zero is a legitimate declaration today, so a
  parser that fell back to it would have been indistinguishable from a working one — and M#38
  disqualifies the **whole project** for that single value. Booked fixtures and warm-ups sit under
  their own headings and are never counted.
- 9.1.4 🐛 **the Step-0 declaration named the wrong model.** Its only caller read
  `llm.ollama_model` directly, so a machine whose `.env` selected `template` or `groq` declared
  Ollama anyway. Appendix F Table 21 makes the *model* the declared thing and the *provider*
  private, so that was a false declaration, not a cosmetic one. Now resolved through
  `factory.model_name`, which asks the provider that will really be called.
- 9.1.7 **the sampling mode is sealed, not just written down.** `field_includes_current_turn` said
  what the field *contains*; nothing said when a received field may be *acted on*. Both are now
  inside the M#23 digest (`sampling_mode = end_of_previous_full_turn`). The lag is forced by
  commit-reveal rather than chosen — but an opponent acting on the current turn's field is
  revealing before committing, and this is the field in which they say so. See C-005.
- 9.1.6 **the clause is generated from the live config, never quoted.** The worked scent example is
  computed, so it reads 0.810 under the book's decay and 0.800 under the reference's — the number
  that identifies which implementation an opponent built on. A clause with the figure typed into it
  would keep saying 0.810 after the flag was flipped: agreeing, in writing, to physics we were not
  running.
- **The agreement artefact carries what was agreed, not only that it was.** `agreement_<game_id>.json`
  holds the scent-model payload, the readings, the clause text and every unsettled warning beside
  the two digests. A hash proves agreement and says nothing about its content, and the file is read
  months later by someone who was not in the conversation.
- 🐛 **`scripts/step_zero_demo.py` had the same wrong-model defect** and is fixed alongside it.
- Tests: `test_negotiation.py` (20), `test_prematch.py` (12), `test_readings.py` (11),
  `test_league_log.py` (14), `test_config_review.py` (16), `test_cli_negotiate.py` (15, driving
  `python -m core negotiate` and the rehearsal against a live peer), four added to
  `test_config_spec.py`, plus two end-to-end handshakes in `test_localhost_roundtrip.py`.
  **94 in total.**

**What remains, and it is not code.** All eight boxes need a second party. The commands above
produce everything a fixture needs; `LEAGUE_LOG.md`'s scheduling table is empty, and until a row
in it is filled the honest declaration stays **0 counted matches** — which is itself below the
M#31 minimum of 2, and the handshake says so every time it runs.

### 9.2 Matches
- [x] 9.2.0 [D] - **A command that plays one.** `python -m core play` — serves, negotiates, plays this repository's share of the six sub-games, audits, files the four artefacts and prints a scoreboard both sides can read out. | DoD: **Verified 08/08 by two processes over real HTTP** — 3 sub-games, 35 steps each, both scoreboards mirroring (15-30 / 30-15), all six audits `passed`, 7 artefacts filed per side, and `replay --headless` returning `Verified OK - 35 steps re-hashed, no mismatch`. `MatchDriver` and `SeriesRunner` already existed; nothing outside `tests/` could reach them, so the project could play only against itself. Wiring in `core/cli_play.py` + `core/runtime/live.py`; scoreboard in `core/report/scoreboard.py`. Procedure in **docs/MATCHDAY.md**.
  - [x] 9.2.0.a [D] - **Race fixed: the reset that deleted the opponent's opening commit.** `start_sub_game` clears every inbox keyed by step, and our *inbound* `on_negotiate` agrees the moment they call it — so from that instant they may commit, while this process is still in its own handshake. Any reset sequenced later deleted a commit already received; their reveal was then refused as unsealed and an untouched sub-game scored `TECHNICAL_LOSS`. Now reopened **before the server starts**, and once per sub-game via `live.reopen`. | DoD: Invisible to the in-process suite, which is why it is called out; it lost all three sub-games on the first two-process run and none since. 8 unit tests in `tests/unit/test_live_play.py`.
  - [x] 9.2.0.b [D] - `--linger`, so the peer that finishes first stays up | DoD: Their closing exchange calls **our** tools; exiting immediately left the opponent's last sub-game recorded `audit not_run` (M#19, M#36). Now `passed` on all six.
- [ ] 9.2.1 [B] - Warm-up match (uncounted) | DoD: Protocol bugs shaken out before anything counts. (M#52)
- [ ] 9.2.2 [B] - Counted match 1 | DoD: Result agreed; both reports sent.
- [ ] 9.2.3 [B] - Counted match 2 | DoD: **Minimum for a passing grade reached.** (M#31)
- [ ] 9.2.4 [B] - Counted match 3 | DoD: Different team; diversity reward earned.
- [ ] 9.2.5 [B] - Counted match 4 | DoD: Different team.
- [ ] 9.2.6 [B] - Counted matches 5–8 | DoD: Each vs. a different team; max 10 total. (F)

### 9.3 Post-match protocol — repeat for every match
- [ ] 9.3.1 [B] - Mutual log audit, all nonces revealed | DoD: Completed **before** agreeing the result. (M#36)
- [ ] 9.3.2 [B] - Agree the result with the opponent | DoD: Both sides hold the same figures.
- [ ] 9.3.3 [B] - Send our own result JSON | DoD: Delivery confirmed in the sent folder. **Automated in 9.5.8** — the process that files the sixth sub-game sends it and prints where it went; `scripts/send_report.py` covers the series that never reached six, the send that failed, and the result corrected after 9.3.2. The box stays open because "in the sent folder" is a human looking at a mailbox.
- [ ] 9.3.4 [B] - **Confirm the opponent actually sent theirs** | DoD: Explicit confirmation obtained. A missing or contradictory report voids the match and scores 0 **for both teams**. (M#35)
- [ ] 9.3.5 [B] - Commit the config JSON and match log to both repos | DoD: Reproducible after the fact. (Appendix F §2.4)
- [ ] 9.3.6 [D] - Update `docs/LEAGUE_LOG.md` | DoD: Row complete with date, role, result, reports, commit hash.

### 9.4 The match driver — playing a sub-game against a real opponent
- [x] 9.4.1 [D] - One peer's turn loop | DoD: **Done 07/08.** `core/runtime/match_driver.py`. Ordering is the protocol: commit → await theirs → reveal → await theirs → resolve. Every turn passes through `PhaseMachine` (M#4, M#5, which until now no *game* referenced) and every wait carries a `DeadlineTracker` bound (M#6). A dropped peer becomes a recorded technical loss, never a traceback.
- [x] 9.4.2 [D] - One turn planned once | DoD: **Done 07/08.** `core/runtime/turn_plan.py`. 🐛 **Found by the first real match:** the seal and the log line each recomputed the scent digest and the reveal, and both derive from a filter that advances — so all 35 steps failed their own audit and an honest peer looked exactly like a forger.
- [x] 9.4.3 [D] - Nonce exchange and mutual audit | DoD: **Done 07/08.** `core/runtime/match_closing.py`. Their log is **reconstructed** from what we independently hold, never accepted from them (Ch. 5.4, M#18, M#36). Tested both directions, plus a forged reveal that must be caught.

### 9.5 The series — six sub-games, priced and filed
- [x] 9.5.1 [D] - Role plan across the series | DoD: **Done 08/08.** `roles_for` in `core/runtime/series.py`. 🐛 **`"3-3"` is symmetric and settles nothing about who starts as cop** — so the plan is built from the role this process holds, and `negotiation.settle` now refuses two peers claiming the same one. Without it the disagreement surfaced as a rejected opening commit: a technical loss for both teams over something the handshake settles free. (C-011, N17)
- [x] 9.5.2 [D] - Sub-game boundary | DoD: **Done 08/08.** `PeerRuntime.start_sub_game` + `Orchestrator.restart` — both previously **dead code with no caller**. Everything keyed by step must be cleared or the next sub-game's step 0 is refused as already committed; the history must be cleared or their step 0 is audited against a board from a game that ended. The brain is *told* rather than replaced (`BrainBase.restart_sub_game`), because the opponent profile banks across the six and the trail must not.
- [x] 9.5.3 [D] - Series scoring by team, not by role | DoD: **Done 08/08.** `level_series` split out of `aggregate` in `core/domain/scoring.py`. Summing `score()[0]` across a role-swapping series credits us with half the opponent's points — 3 captures as cop and 3 survivals as thief is 90–30, not 75–45.
- [x] 9.5.4 [D] - The four artefacts, written | DoD: **Done 08/08.** `core/runtime/filing.py`. `build_declaration` / `build_config_snapshot` / `build_log` / `build_result` had **no caller at all** — the project could play a match and file nothing. Config snapshot and log per sub-game, written as each finishes so a series that dies at sub-game four keeps the first three.
- [x] 9.5.5 [D] - `result_<game_id>.json` cannot contradict itself | DoD: **Done 08/08.** `totals` is the arithmetic of the rows; the new `series` block is what the tie rule makes of it. A level 45–45 series pays 2–2, and a file showing one number without the other reads as a mistake.
- [x] 9.5.6 [D] - Tests | DoD: **Done 08/08.** `tests/integration/test_series_runner.py` (9, on `series_harness.py`: **four** peers, two per team, roles swapping at sub-game four) and `tests/unit/test_series.py` (15). Every filed log is re-read from disk and re-hashed — the `Verified OK` path (M#20).
- 🐛 **The `[strategy]` key nobody read.** Appendix B.4 and our own `game.toml` both spell it `police_class`; every caller asked for `strategy.cop_class`, which no file contains. Nothing failed — `Config.get` answers None for an absent path and `load_brain` reads None as "use the baseline" — so **a graded match would have fielded the shipped baseline, not the Phase 8 advanced brains.** One definition now, `brain_loader.CONFIG_KEYS`. ✅ **Both `game.toml`s now name a strategy** — see 9.5.7 for which, and why.
- [x] 9.5.7 [D] - **Decide which brain a graded match fields** | DoD: `police_class` / `thief_class` set in both `game.toml`s, or a written decision not to. — **Decided: the advanced brains, both roles.** `police.advanced:AdvancedCop` and `thief.advanced:AdvancedThief`, verified end to end through `brain_for` rather than read off the file: a key that is set and not read is exactly the defect above.
  - **The evidence** (`test_advanced_league_benchmark.py`, 192 sub-games over all 48 mirrored openings, at the shipped config): the advanced Cop captures 48/48 against the baseline Thief where the baseline Cop manages 27/48; the advanced Thief survives 42/48 against the baseline Cop where the baseline Thief manages 21/48. Both clear A4.2's ≥70 % gate, self-separations are 0 in every cell, and all 192 sub-games reached a verdict — so the crash risk that would make a technical loss worth 0 to **both** teams is measured, not assumed.
  - ⚠️ **Every one of those figures is our brains against our own baselines.** That is an A/B, not evidence about a stranger, and Ch. 9.2 warns specifically against overfitting to a single examiner. The first counted match is the first real measurement.
  - ⚠️ **The Cop's edge is mostly verbal, and measured against one listener.** Leave-one-out puts the verbal layer at 8/48 captures on versus 2/48 off — three quarters of what Phase 8.3 is worth — measured against our own Thief, whose hint tilt is capped at `MAX_TILT 0.35`. An opponent that ignores hints, or weights them far harder, moves that number in a direction nobody has measured. 8.3.5 switching bluffing off against a measured-deaf opponent is the hedge, and it needs a real opponent to have anything to measure.
  - **The asymmetry is deliberate:** `bluff_enabled` ships **true** for the Cop and **false** for the Thief, because the lie's job is herding and the Cop is the role that herds (A3.10). It reads as an inconsistency to anyone who has not seen the ablation, so it belongs in the README (10.4.x).
  - **Reverting is one config line, no code change.** Leaving `police_class` / `thief_class` unset falls back to the shipped baselines, which is why fielding the advanced brains is the low-risk choice rather than the bold one — a bad warm-up is recoverable before anything counts.
- [x] 9.5.8 [D] - **One report from two processes, and it sends itself** | DoD: **Done 09/08.** Both gaps between a played match and a reported one, closed together. `core/report/merge.py` + `core/runtime/reporting.py`; 24 tests in `test_result_merge.py` and `test_series_reporting.py`.
  - 🐛 **The second role process overwrote the first's report.** Every artefact is named per sub-game except `result_<game_id>.json`, which names the whole match — so the Thief repository, finishing last under a 3-3 split, replaced a report covering sub-games 1-3 with one covering 4-6. `build_result` sums `totals` from the rows it is handed, so the file was **internally consistent and wrong**: it claimed our half was the series, while the opponent's report of the same match showed six sub-games against our three. A contradictory pair is 0 for **both** teams (M#35) — this is the failure mode where the honest team loses on the paperwork. Rows now merge by sub-game number, ours winning, which is also idempotent under a re-run: a crashed process replaces its own rows and leaves the other half alone. `filing.py`'s own docstring had recorded the defect as *"which is why `scripts/` must merge"*, and no such script was ever written.
  - ⚠️ **`SeriesReport.summary()` cannot be carried into the merged file.** It knows only the half its own process played, so a series level across all six looks decided across three, and the league credit is filed for the wrong number of sub-games. `series_block` recomputes it over the merged rows — and does it by reconstructing the outcomes and calling `level_series`, so the C-013 tie rule keeps one definition and cannot drift between the file and the scoreboard printed beside it.
  - **The report goes out when the sixth row is filed, and not before.** A 3-3 split is two processes, and mailing the first half would put two messages under one `game_id` in the grader's inbox with the earlier disagreeing with the later — the exact contradictory pair M#35 punishes, manufactured by the code written to satisfy it. So the decision is read off the merged file on disk rather than from what this process happens to have played.
  - **Every failure is loud and none is fatal.** The match is over and the artefacts are on disk when this runs; raising would bury the one line the human still has to act on. Every branch that does not send returns `NOT SENT`/`held back` plus the exact command that files it by hand — `scripts/send_report.py`, which is also the path for a series the opponent abandoned at sub-game four, and for a result corrected after the two teams reconcile (9.3.2).
  - 🐛 **Asking whether reporting was switched on required an OAuth token.** `sdk.mailer()` evaluated `build_transport()` as an argument, so a peer with `[email] enabled = false` could not read its own config without the consent flow it had deliberately opted out of. The transport is now built on the first real send.
  - Printed text is ASCII, asserted by a test: an em dash in the one line reporting a successful match is a `UnicodeEncodeError` on a cp1252 console instead of a report.

### 9.6 What a real match found — self-match over MCP, 13/08

The first end-to-end match on this machine: four peers, two teams, real HTTP, real commit-reveal. Pair 2 played clean (35 steps a sub-game, audits passed both sides, mirrored scores). Everything below is a defect it exposed that no test had.

**Read the pattern before the list.** Twelve defects, and 1600 tests at 95 % coverage had caught none of them: every one lives where the code meets something the suite is not allowed to touch — a real GPU, a real ngrok account, a real mailbox, two real processes writing one file, and a human reading a document. Coverage measures which lines ran, not which of them ran against reality. Two of the twelve were introduced by the fix for an earlier one, which is the strongest argument in this section for re-running the rehearsal after every change rather than only after the first.

- [x] 9.6.1 [D] - 🐛 **`--tunnel` could not start at all.** `[network] public_domain` held a domain reserved on another ngrok account: `ERR_NGROK_320`. Public exposure (M#10) was therefore unavailable and **no league match could have been played over the internet** — invisible to every test, because localhost needs no tunnel. The domain now comes from `.env` as `NGROK_DOMAIN` (`tunnel.reserved_domain`): it is account-bound, which makes it a credential in everything but name, and committing it to two public repositories guarantees it goes stale. Committed default is empty, which is legal — the agent then assigns a random URL and `TunnelManager` reads it back. **Verified live:** the tunnel now comes up on our own reserved domain.
- [x] 9.6.2 [D] - 🐛 **The hardware declaration was false** (M#24, FR-6.7). It declared `"gpu": "NVIDIA-SMI has failed because you do not have suffient permissions."` on a machine with a Radeon RX 9070 XT, `"ram_gb": "unknown"`, and 16 cores for an 8-core CPU. Three faults: `nvidia-smi` sits in `system32` as a leftover so the `which` guard passed and its **error text became the GPU name** — nothing checked the return code; `wmic` no longer ships on Windows 11; and `os.cpu_count()` is logical processors under a field called `cpu_cores`. All of it inside a **signed** payload feeding the computational-fairness weighting. Rewritten as `core/shared/hardware.py` (CIM on Windows, `/proc` + `lspci` on POSIX), now declaring model, physical cores, threads, frequency, RAM and every real adapter. 17 tests, each against a fault that shipped.
- [x] 9.6.3 [D] - 🐛 **A refused handshake filed nothing** (M#35). Our outbound handshake failed while our *inbound* server had already agreed, so the opponent played its half against a peer that had quit — scoring three technical losses and filing six rows while we filed three. Two teams, one match, two reports disagreeing about how many sub-games happened: a contradictory pair is **0 for both**, the rule that punishes the honest side for paperwork. `live.forfeit` now files the unplayed sub-games as technical losses, which cost nothing (0-0) and buy a report that agrees with theirs.
- [x] 9.6.4 [D] - 🐛 **Any six-row result mailed the lecturer.** A self-match or rehearsal delivered him a fabricated league report, twice — once per team process. Sending is now opt-in via `--counted`, and a self-match can never send whatever the flag says. The default fails towards silence because the two directions are not symmetric: a forgotten flag costs one command (`send_report.py`, printed in the same breath), and a fake report cannot be withdrawn.
- [x] 9.6.5 [D] - 🐛 **Concurrent writers corrupted `result_<game_id>.json`.** Both role processes file it under one identifier — that is what the merge is for — and overlapping writes spliced two JSON documents together, after which `load_rows` refused the file and reporting stopped dead. `artefacts.write` now stages and `os.replace`s, which is atomic on both platforms. The staged name carries pid **and** a random token: pid alone is shared by threads, which moves the same bug one filename along.
- [ ] 9.6.6 [B] - ⚠️ **Unexplained:** in the failing pair the outbound handshake never connected for 90 s while the same pair connected first try when the opponent was pre-bound, and the final error was an HTTP `illegal request line`. The retry path is correct (`classify` maps unknown failures to `TransportError`, which `_greet` retries), so the peer was genuinely unreachable. Not reproduced since. 9.6.3 makes the consequence survivable either way; worth watching on the first real match.

**Then the walk-through of the runbook found three more.** None is a code path a match exercises — they are the *instructions* and the *setup* around it, which is exactly the layer a test suite cannot reach and a self-match does not read.

- [x] 9.6.7 [D] - 🐛 **Two variables for one domain, and the placeholder won.** 9.6.1 moved the reserved domain to `NGROK_DOMAIN`, but `PeerSDK.tunnel` still applied `P2P_PUBLIC_DOMAIN` *afterwards* — and `.env-example` shipped it holding the literal text `your-domain.ngrok-free.dev`. Copy the example, fill in the domain the file tells you to fill in, and the placeholder overrides it; a placeholder cannot be bound any more than someone else's domain can, so 9.6.1's `ERR_NGROK_320` comes straight back. `tunnel.reserved_domain` is now the single resolver, the SDK no longer re-reads the environment, the old name is read **last** so an existing `.env` still plays, and the placeholder is gone from `.env-example`. `reserved_domain` had **no test at all** — which is how a function written to end a match-day failure acquired a second one. Eight now, including a source-level guard that the SDK never resolves it twice.
- [x] 9.6.8 [D] - 🐛 **The runbook told you how to lose a won match.** `MATCHDAY.md` — walked line by line, as a human would on the day — gave every `play` command without `--counted`. 9.6.4 had made sending opt-in that morning; the document still described the old behaviour, so following it exactly plays six sub-games, files four artefacts, prints the scoreboard and mails **nothing**, which under M#35 is 0 for both teams. Also repaired there: the `.env` table still named `P2P_PUBLIC_DOMAIN`, and the Ollama step said `ollama list` when that command *hangs* rather than erroring if the daemon is down.
**Then the first rehearsal over the real public tunnel found three more.** Cop published on the reserved domain, Thief reached it over the internet, three sub-games each, all six audits passed and all three logs re-hashed `Verified OK`. Everything below is what that run exposed on the way.

- [x] 9.6.10 [D] - 🐛 **The reserved domain never reached ngrok, and 9.6.7 is why.** The rehearsal came up on `https://84b8-5-29-32-69.ngrok-free.app` — a random URL — because `reserved_domain` read `os.environ` directly, and `.env` is not the environment until `env.load_env()` is called. It had always been broken; the duplicate deleted in 9.6.7 was masking it, because that line called `env.optional` two lines later and *that* loads the file. So the domain only ever arrived through the legacy name, and removing the duplicate unpublished it. Now read through `core/shared/env.py`, whose own docstring has said since 0.1.14 that nothing may read `os.environ` directly. **Caught only because the rehearsal asked ngrok's agent API what it had published instead of trusting our own log line** — the code printed a URL either way.
- [x] 9.6.11 [D] - 🐛 **A Windows sharing conflict on the atomic write cost an entire report.** `os.replace` is atomic on Windows but not always *permitted*: `MoveFileEx` fails with `ERROR_ACCESS_DENIED` while another process holds the destination open, and both peers close the declaration in the same instant. The `PermissionError` left `MatchFiling.result` through `SeriesRunner.run`, so the Thief peer — three clean sub-games, every audit passed — printed no scoreboard, filed no `result_<game_id>.json` and sent nothing, while the Cop filed normally. One side reporting and the other silent is precisely the contradictory pair M#35 scores **0 for both teams** over, manufactured by 9.6.5's fix for the corruption. Two layers now: the replace waits out the conflict (20 × 50 ms, then a named `ArtefactError` and no `.tmp` litter), and `result` files the result **first** and closes the declaration after, recording a failure in `close_failure` rather than raising — the declaration is already on disk from before the first move, so all that can be lost is `ended_utc`. Re-run end to end: both peers clean, no stray files, `started_utc` and `ended_utc` both present.
- [x] 9.6.12 [D] - `--headless` replay printed **`Verified OK - Verified OK - 35 steps re-hashed`**. `ReplaySession.describe` prefixed the viewer's badge text onto the audit's own sentence, which already opens with the verdict. That doubled line is what the M#20 deliverable shows.
- [x] 9.6.9 [D] - **`check_setup.py` now prints the two answers it was silent about**: the domain a match would be published on, and which trash-talk provider this machine will really use. The second reads the Ollama result rather than the setting alone, because `ollama` selected while nothing is listening does not fail — it pays `[llm] timeout_sec` on every turn and then writes the template hint anyway. A setting that is fine and a service that is down look identical until you put them on one line.

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
