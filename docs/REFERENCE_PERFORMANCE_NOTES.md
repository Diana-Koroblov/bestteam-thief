# Reference performance report — what it changes for us

**Source:** `Game-P2P-Cop-Chase/docs/RESEARCH-REPORT-Performance-Analysis.md` (329 lines),
the reference implementation's own benchmarking of LLM cost, rate limits and failure
behaviour. Read for TODO **0.5.3**; feeds task **4.5** (the Gatekeeper) and Phase 7.

Its numbers are measured from the reference *code*, not from the book, and it says so
explicitly: where the two disagree, the report treats the code as ground truth. Provider
caps are 2026 snapshots and approximate. We treat the workload arithmetic as solid and the
per-provider message caps as indicative.

---

## 1. The load, and why it is smaller than it looks

| Quantity | Value | Where it comes from |
|---|---|---|
| Moves per agent per series | 6 × 35 = **210** | `num_games` × `max_moves` |
| LLM calls at `every_n_steps = 3` | **~66–70** | ⌊35/3⌋ × 6 |
| Call rate | **~0.5 / min** — one call every ~2 minutes | 210 moves at ~20 s |
| Series wall-clock | **~140 min (2.33 h)** | same |
| Tokens on a paid provider | ~70 × ~250 ≈ **17.5 k**, **8.75 %** of the 200 k budget | `max_tokens = 200`, Haiku |
| Tokens on `template` or `ollama` | **0** | no API call at all |

The report's central observation: **the bottleneck is not tokens, it is message counts per
rolling window.** Peak demand of 0.5 requests/minute is trivial against any provider's RPM
ceiling. What bites is that 140 minutes fits entirely inside a single 3-, 4- and 5-hour
window, so **there is no mid-series quota reset to lean on**. The comparison is 70 calls
against the per-window cap, directly.

## 2. What we changed as a result — nothing, and here is why

**I initially changed `every_n_steps` from 1 to 3 in both configs. That was wrong, and it has
been reverted.** Diana caught it. The reasoning is worth keeping because the mistake is easy
to repeat.

Two things were conflated:

- **A hint is sent every turn, unconditionally.** Ch. 5.3.1: the agent chooses its move *and*
  the hint together, and the sealed commit covers «הרמז המילולי, סיווג הכוונה, מספר הצעד
  והתפקיד». A turn without a hint would break commit-reveal.
- **`every_n_steps` governs how often the *model* runs**, not whether a hint is sent. On the
  turns the model is skipped, `template` writes the hint instead. The verbal channel never
  goes quiet.

And the decisive point: the book frames this as a **budget** question — «הבחירה כיצד להפעילו
היא בעיקר שאלת תקציב: כמה טוקנים מתוך [אומדן טוקנים לסדרה] אתם מוכנים להוציא על דיבור»
(Ch. 6.5.1). Our two providers spend **zero** tokens. `template` never calls a model at all;
`ollama` is local, unmetered and rate-limit free. There is no budget to protect, so raising
the interval buys nothing and costs two-thirds of our verbal variety — in a project where
the deception layer is graded.

The 17.5 k-token figure in §1 describes `claude_api`. Applying it to a zero-token
configuration was the error.

**`every_n_steps` stays at 1, with a condition attached:** if the provider ever becomes
metered (`groq`, `claude_api`, `claude_cli`), it must rise to 3. At 1 a series makes 210
model calls instead of ~70 — on a paid tier roughly 52 k tokens, and enough to brush the
5-hour message window of every subscription. That pairing is enforced by a startup check
(TODO 7.1.6) rather than left to memory.

Everything the report recommends, we had already chosen independently:

| Report's recommendation | Our decision | Where |
|---|---|---|
| Ship `template` as the default — 0 tokens, offline, instant | Committed default is `template` | `[trash_talk] provider` |
| Ollama is "the correct free choice" — no RPM, no cap, no network | Itay's machine runs `ollama` for graded matches | ADR-003, C-012 |
| Never let the model decide the move | Movement is pure Python expectimax; the model only produces text | Ch. 6, ADR-002 |
| Catch provider errors and fall back to a template line | `allow_template_fallback = true` | `[llm]` |
| Prefer `claude_api` (stateless, 200 tokens) over `claude_cli` | We use neither, but the reasoning is recorded | §4 below |

## 3. The finding that matters most — the fallback is what saves the match

The report is blunt about the difference between the book's design and the code's:

> Old design (book): any block, timeout or quota freezes the game loop → **failed match**.
> New design (code): graceful degradation — the move continues in Python, only the banter
> goes robotic, and **every match completes**.

On free tiers, Claude and Grok both exhaust their quota *mid-game* — Grok in under 20
minutes. Neither has a provider-side fallback; both return a hard error. What rescues the
match is architectural: the exception is caught, the template line is returned, and the
move had already been chosen in Python.

**For us this is a hard requirement, not a nicety.** A frozen game loop is a watchdog
timeout, and a watchdog timeout is a technical loss worth 0 (Appendix F Table 17). Our
`[llm] timeout_sec = 8` sits well inside the 30-second response limit precisely so that a
slow provider degrades instead of forfeiting.

## 4. `claude_cli` — the trap we are already avoiding

Worth recording because it is the report's sharpest warning. The CLI path authenticates via
the browser **subscription** login (the reference deliberately strips `ANTHROPIC_API_KEY`),
so its calls count against the Pro 5-hour and weekly message windows *and* pay the full
Claude Code system-prompt overhead on every call. The reference README records the old
LLM-per-move design at ~2.4 M tokens per sub-game — orders of magnitude over the 200 k
budget.

Seventy heavy CLI calls inside one 5-hour window is exactly what pushes a Pro subscriber
over the edge. `claude_api` with Haiku — stateless, fresh `messages=[...]`, 200 tokens — is
far lighter. We use neither, but if we ever add a cloud provider, it is the API and not the
CLI.

## 5. The Gatekeeper's real job (feeds task 4.5)

The reference measures **0.5 RPM of demand against a 30 RPM local budget**. The gatekeeper
therefore never queues and never trips in normal play. That is not an argument for dropping
it — Appendix F Table 19 makes those limits binding minimums — but it does change what the
component is *for*:

- It is **insurance**, not throughput management. Its value shows up only when something
  bursts: `every_n_steps = 1` with fast pacing, a retry storm, or a strategy change late in
  the project.
- It should **queue rather than error** when full. The reference uses a sliding-window token
  bucket whose `acquire()` blocks; that is the behaviour to copy, because erroring is
  indistinguishable from a forfeit.
- The 5-second retry backoff × 3 attempts must stay **inside** the 30-second response
  timeout. 3 × 5 s = 15 s of backoff plus request time is comfortable; a fourth retry would
  not be. This is a real constraint on task 4.5 and is why `max_retries` stays at its
  Appendix F minimum of 3.

## 6. The scheduling fact nobody mentions

**A full 6-sub-game series takes roughly 2.3 hours of wall-clock**, and it needs both teams
present. Our own peer will be much faster than the reference's ~20 s/move — `template` mode
is instant and our search is budgeted at 20 s worst case — but **a series runs at the speed
of the slower peer**, and we do not control theirs.

Against `docs/PARAMETERS.md` §5.1, which argues for playing as many distinct opponents as
possible for the 10-point diversity reward: ten opponents is on the order of **20+ hours of
match time**, inside a 15-day project, coordinated across ten other teams' calendars.

That does not weaken the argument for playing many opponents — the diversity points still
dominate everything else available to us. It sharpens the deadline on TODO 0.3.1: the
constraint is calendar, not code, and it is the one thing more work on my side cannot fix.
