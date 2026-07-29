# PRD 6 — Commit-Reveal, Audit and Step-0
### Layer 6 of 7 · milestone M6 · owner [D]

**Covers:** FR-6.1 … FR-6.8 · **Book:** Chapter 5 · **Depends on:** Layers 1–5
**Exit criterion:** a move is committed then revealed with a valid nonce; Step-0 verifies hardware
and commit hash; the end-of-match audit passes.

---

## 1. Purpose

Make cheating mathematically impossible rather than socially discouraged. With no referee, three
frauds are otherwise available: changing a move after seeing the opponent's, rewriting history
afterwards, and denying a previous position or statement. Cryptographic commitment closes all
three.

**Coverage target for `core/crypto` is ≥95 %, not 85 %.** A gap here is not a missing feature; it
is an undetected forgery or — worse — a false accusation against an honest opponent.

---

## 2. Background

The mechanism is the classic "coin flipping by telephone" construction: each party commits to a
choice while it is still sealed, and only once both are locked is anything revealed. Changing a
choice after the fact would break a signature already in the opponent's hands.

It carries the spirit of a zero-knowledge proof: at commit time the opponent gains **certainty
that a decision exists and is fixed**, and **zero information about its content**. Only at reveal
does content appear, and even then it can be checked against the original commitment.

The nonce does two jobs. It makes repeated identical actions hash differently, and it defeats a
dictionary attack — without it the move space is small enough to pre-hash exhaustively in
milliseconds.

---

## 3. Requirements

### 3.1 Canonical serialisation — the highest-risk detail

| ID | Requirement |
|---|---|
| 6.1 | Every hashed record is serialised as `json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")`. |
| 6.2 | A cross-process test proves two independent interpreters produce byte-identical output. |

If two peers serialise differently — different key order, different separator spacing, different
line endings — every verification fails, the audit reports forgery on both sides, and **both teams
score 0**. This is the single most consequential line of code in the project, and it is why
`.gitattributes` pins LF (see `CONTRADICTIONS.md` C-004).

### 3.2 The commitment

| ID | Requirement |
|---|---|
| 6.3 | `H_commit = SHA256(State ‖ Move ‖ Intent ‖ Nonce)` over canonical JSON (M#17). |
| 6.4 | Nonce from `secrets.token_hex(16)`. An architecture test asserts `random` is never used for it. |
| 6.5 | The real sealed record is richer than the four core fields — it also carries the hint text, intent classification, step number and role. |
| 6.6 | Verification uses `secrets.compare_digest`, not `==`. |

`State` binds the commitment to one specific step, so an old commitment cannot be replayed in a
new context. `Intent` forces the agent to declare *in advance* whether the accompanying sentence
is true, which is what prevents claiming afterwards that a lie was "meant" all along.

### 3.3 The four phases

| Phase | Direction | Content |
|---|---|---|
| 1 · Commit | both ways | `H_commit` only. No content leaves. |
| 2 · Acknowledge | both ways | "I am locked." Reveal is impossible before both sides have acknowledged. |
| 3 · Reveal | both ways | Move and hint. **Nonce withheld.** |
| 4 · Final Audit | both ways | All nonces, once, at end of match. |

| ID | Requirement |
|---|---|
| 6.7 | The nonce is kept absolutely secret until the final audit (M#18). A test asserts no reveal payload contains one. |
| 6.8 | Acknowledgement gates reveal — an implementation that reveals early destroys the entire guarantee. |
| 6.9 | Capture claims are answered truthfully and the answer is cryptographically bound (M#21, M#22). |

Withholding the nonce through phase 3 prevents reverse-engineering commitments before the match
ends, while still allowing moves to be exchanged and physics to be checked each turn.

### 3.4 Audit

| ID | Requirement |
|---|---|
| 6.10 | At match end each side recomputes every one of the opponent's hashes from the revealed data and compares to the original commitment. |
| 6.11 | **Any** mismatch is a technical loss for the forging side (M#19). No tolerance, no discretion. |
| 6.12 | The audit must complete **before** the result is agreed (M#36). |

SHA-256 is sensitive to a single bit, so there is no "nearly matches". The cryptography decides,
not human judgement — which is precisely the point of having no referee.

### 3.5 Step-0 declaration

| ID | Requirement |
|---|---|
| 6.13 | Before the first move, collect and sign: OS, CPU cores and frequency, RAM, GPU/VRAM, LLM model name, code version, team name, sub-game number. |
| 6.14 | Include **`github_commit`** — the exact commit hash being played (M#53). |
| 6.15 | Warn loudly if the working tree is dirty before a graded match: the declared hash would not describe the code actually running. |
| 6.16 | Meter LLM token consumption, lock it at Step-0, and report it in the result JSON (M#54). |

The purpose is computational fairness: the lecturer normalises league scores to reward strong
results achieved on modest resources. Code may change between matches — that is explicitly
allowed — but each match must declare which version played, so any result can be reproduced.

---

## 4. Interface

```python
# core/crypto/canonical.py
canonical_bytes(payload: dict) -> bytes

# core/crypto/nonce.py
new_nonce() -> str                       # secrets.token_hex(16)

# core/crypto/commit_reveal.py
commit(record: MoveRecord) -> tuple[str, str]          # (h_commit, nonce)
verify(record: MoveRecord, nonce: str, h_commit: str) -> bool

# core/crypto/audit.py
audit_log(entries: list[LogEntry], nonces: dict[int, str]) -> AuditResult
# AuditResult: VERIFIED | TAMPERED(step, expected, actual)

# core/protocol/step_zero.py
build_declaration(config, role, sub_game: int) -> SignedDeclaration
```

---

## 5. Constraints

- Files ≤150 lines. `commit_reveal.py` splits into commit and verify if needed.
- `core/crypto` imports nothing from `core.infra` or `core.runtime` — it must be testable with no
  network and no clock.
- Never log a nonce before the final audit. A nonce in a debug line during a live match is a leaked
  commitment.
- Coverage ≥95 % on `core/crypto`.

---

## 6. Alternatives considered

| Decision | Alternative | Why rejected |
|---|---|---|
| Canonical JSON | Pickle, or concatenated strings | Pickle is not cross-language and not stable across versions; naive concatenation is ambiguous when a field contains the separator |
| `secrets.token_hex(16)` | `random`, or a counter | `random` is predictable from observed output; a counter is trivially guessable, defeating the nonce's entire purpose |
| `compare_digest` | `==` | Timing side channel. Negligible here, but writing the insecure form in a project *about* cryptographic integrity is indefensible |
| Nonce held to final audit | Reveal the nonce each turn | Would let the opponent reverse-engineer commitment structure mid-match |
| Four phases | Three (no acknowledgement) | Without the ack, the first revealer is exposed to an opponent who has not yet locked |
| Absolute audit failure | Warn and continue | M#19 is explicit: forgery scores 0. Softening it would be a rule violation |

---

## 7. Test scenarios

| # | Scenario | Expected |
|---|---|---|
| T6.1 | Commit then verify with correct data | `True` |
| T6.2 | Alter `Move` before verification | `False` |
| T6.3 | Alter `State` | `False` |
| T6.4 | Alter `Intent` | `False` |
| T6.5 | Alter `Nonce` | `False` |
| T6.6 | Same record, two commits | Different hashes (nonce differs) |
| T6.7 | Canonical bytes from two subprocesses | Byte-identical |
| T6.8 | Key order permuted in the input dict | Same digest |
| T6.9 | Scan reveal payloads | No nonce present |
| T6.10 | Full clean match, then audit | `VERIFIED` |
| T6.11 | Alter one logged move, then audit | `TAMPERED` naming the exact step |
| T6.12 | Audit attempted before all nonces revealed | Refused, not a false pass |
| T6.13 | Step-0 on a clean tree | `github_commit` equals `git rev-parse HEAD` |
| T6.14 | Step-0 on a dirty tree | Loud warning |
| T6.15 | Token meter across a series | Total matches the sum of provider calls |
| T6.16 | Import scan of `core/crypto` | No `import random` |

---

## 8. Traceability

| Rule | Where |
|---|---|
| M#17 | §3.2 — SHA-256 commit-reveal |
| M#18 | §3.3 — nonce secret until final audit |
| M#19 | §3.4 — any mismatch is a technical loss |
| M#21, M#22 | §3.3 — truthful capture claims, bound cryptographically |
| M#24 | §3.5 — signed hardware declaration |
| M#36 | §3.4 — audit precedes agreeing the result |
| M#53 | §3.5 — commit hash per match |
| M#54 | §3.5 — token consumption reported |

**TODO tasks:** 6.1.1 – 6.5.4 · **Milestone:** M6
