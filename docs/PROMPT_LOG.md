# Prompt Engineering Log

Required by the excellence guide (§8.3) and by the rulebook's submission
checklist, which states plainly that *knowing how to define and specify the
instructions an agent needs in order to produce the requested code* is itself
part of the assessed task (Ch. 11 §11.5a).

This is therefore not a diary. It is evidence of method: what we asked for, what
came back, what was wrong with it, and what we changed.

---

## How to add an entry

```markdown
### YYYY-MM-DD — short title
**Goal:** what we were trying to produce
**Context given:** which documents/files the agent was working from
**Prompt (abridged):** the instruction, trimmed to its substance
**Result:** what came back
**Problem:** what was wrong, if anything
**Iteration:** how the instruction changed
**Lesson:** the transferable rule
```

---

## Lessons so far

Rules extracted from the entries below, applied to every later prompt.

1. **Specify the source of truth, not just the task.** "Use Appendix F for every
   numeric value" prevented the agent inventing plausible-but-wrong constants.
2. **Ask for the failure mode, not only the feature.** Requesting "and prove it
   fails when it should" surfaced two bugs that a happy-path request would have
   shipped.
3. **Name the platform.** Omitting "this runs on Windows" produced a bash-only
   secret scanner that would have broken the publish pipeline.
4. **Make the agent cite the rule.** Requiring `M#n` references next to each
   requirement turned an unverifiable document into a checkable one.
5. **Verification beats assertion.** "Run it and show me the output" caught a
   hardcoded limit that reading the code had not.

---

## Entries

### 2026-07-28 — Analyse the rulebook and produce a work plan
**Goal:** A grounded plan from a 160-page Hebrew rulebook plus a 39-page quality guide.
**Context given:** Both PDFs, and the HW6 codebase as the starting point.
**Prompt (abridged):** Analyse the final-project rulebook together with the excellence
requirements and produce a structured summary: work plan from step 0, code-reuse mapping
against HW6, mandatory architecture, technical recommendations with justification, and
excellence/competitive notes.
**Result:** `FINAL_PROJECT_BRIEF.md`.
**Problem:** None in the output, but the extraction needed care — the Hebrew PDF reversed
character order under naive extraction, which would have corrupted every quoted value.
**Iteration:** Switched extraction tool and verified all 31 Appendix F values programmatically
against the book's own sample config rather than trusting the read.
**Lesson:** When a document is the source of truth, verify the *extraction* before trusting
anything derived from it.

### 2026-07-28 — Specification documents
**Goal:** PRD, PLAN and TODO good enough that the grader can reconstruct our reasoning.
**Context given:** The brief, both source PDFs, the HW6 tree.
**Prompt (abridged):** Write PRD.md, PLAN.md and TODO.md for the new architecture; trace every
mandatory rule; record architectural decisions with alternatives and rationale.
**Result:** Three documents; all 55 mandatory rules cited; 7 ADRs.
**Problem:** Three rules were referenced in prose but not in the machine-checkable `M#n` form,
so a completeness check missed them.
**Iteration:** Normalised every citation to `M#n` and re-ran the check until zero were missing.
**Lesson:** Choose a citation format a script can verify, then actually run the script. "I
mentioned it somewhere" is not traceability.

### 2026-07-28 — The 150-line guard
**Goal:** Enforce the file-size rule continuously rather than discovering violations at the end.
**Prompt (abridged):** Build a checker that walks the source tree, counts lines that are neither
blank nor comments, and fails with a sorted list of offenders.
**Result:** `loc_counter.py` plus a CLI and a pytest guard.
**Problem:** The first version exposed `FileReport.is_oversized`, which compared against the
global constant and so silently disagreed with a custom `--limit`. A test caught it.
**Iteration:** Removed the property; the limit belongs to the query, not to the file. Added a
docstring note explaining the absence so nobody reinstates it.
**Lesson:** A convenience property that captures global state is a bug waiting for a second
caller. Write the test that passes a different value.

### 2026-07-28 — Cross-platform correctness
**Goal:** A publish pipeline that works on the machine it will actually run on.
**Problem:** The secret scanner was written as a bash script. On Windows `bash` is not
dependable on PATH, and the publish aborts if the scan cannot run — so the whole pipeline
would have failed on the user's machine while passing in the Linux test environment.
**Iteration:** Rewrote it in Python, kept the shell file as a deprecation stub, and added a test
asserting that prose *about* secrets does not trigger a false positive.
**Lesson:** State the target platform in the prompt. An agent will happily optimise for the
environment it can see rather than the one that matters.

### 2026-07-28 — Prove the guards fail
**Goal:** Confidence that the quality gates actually block bad changes.
**Prompt (abridged):** Do not just show the checks passing — plant a 151-line file, a fake API
key and a failing test, and show each one being caught.
**Result:** All three blocked; publish exited 1 with nothing pushed.
**Problem:** The secret pattern `BEGIN PRIVATE KEY` matched our own documentation *about*
secrets, so a clean tree failed the scan.
**Iteration:** Anchored the pattern on the full PEM header including dashes.
**Lesson:** A checker that cries wolf gets disabled, which is worse than not having one. Test
the false-positive path as deliberately as the true-positive path.

### 2026-07-28 — Verify external setup against live documentation
**Goal:** Instructions for Google Cloud, Groq, Ollama and ngrok that actually match the consoles.
**Prompt (abridged):** Before writing the guide, check the current documentation — these UIs
change.
**Result:** Two material corrections. Google renamed "OAuth consent screen" to "Google Auth
platform", so older instructions point at menus that no longer exist. And a project left in
*Testing* status issues refresh tokens that expire after 7 days — which, on a 15-day project,
would have silently broken automated league reporting mid-series, scoring 0 for both teams.
**Lesson:** Training data goes stale in exactly the places that waste the most time — console
menus and platform policies. Check before writing instructions someone will follow literally.

### 2026-07-28 — Verify a second model's claims against the source
**Goal:** Decide whether three additional "contradictions" suggested by NotebookLM belonged in
`CONTRADICTIONS.md`.
**Prompt (abridged):** Another model proposed three gaps. Are they worth adding? How do we verify
the first one?
**Result:** None were added. Checking each against the rulebook: the visibility-radius "conflict"
described HW6, not the book, which has no such parameter; the three-meanings-of-token "conflict" is
explicitly disambiguated by the book itself in a Chapter 9 callout; and the architectural claim —
that the reference simulator is a monolith with a shared-truth backdoor — was **false**. Reading the
cloned repository showed a single `opponent_url` per client, separate config directories per role,
and a CLI documented as *"Two terminals, two peers, no central server."* The description it gave was
an exact match for HW6, which it had in context.
**But the verification paid for itself.** Reading the code to disprove one claim surfaced four real
divergences worth far more: subtractive rather than multiplicative decay (0.80 vs 0.81 from the same
input), the scent field being transmitted rather than sampled, that field sitting outside the
cryptographic seal, and a `Board` that defaults to illegal king movement.
**Lesson:** A plausible-sounding claim from a model is a hypothesis, not a finding. Check it against
the primary source before writing it down — and check it by reading, not by asking another model.
Padding a graded artefact with unverified claims converts evidence of careful work into evidence of
the opposite. The check is also rarely wasted: going to the source to disprove one thing tends to
turn up several others.
