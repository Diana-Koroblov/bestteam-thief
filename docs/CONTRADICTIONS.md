# Documented Contradictions and Interpretation Choices

The rulebook grants academic freedom where it contradicts itself, on one condition: *state where you
found the contradiction, what you chose, and why.* It guarantees that a documented, reasoned choice
is not held against the team.

This file is that record. Each entry is also summarised in the README of both repositories.

---

## C-001 — `num_games`: 1 in the sample config, 6 in Appendix F

| | |
|---|---|
| **Where** | Appendix F table 18 vs. the sample `config/game.json` in Appendix B |
| **The conflict** | Appendix F lists `[number of sub-games]` = **6**, status *fixed*. The sample config ships `"num_games": 1`, annotated as a single example sub-game. |
| **Our choice** | **6.** |
| **Why** | The book states plainly that Appendix F is the sole source of truth for numeric values, and that where the book and the sample code repository disagree, the book governs. The sample's `1` is a development convenience for running a single sub-game; the accompanying text itself notes that a full league series requires the full count. |
| **Effect** | `config/<role>/game.json` ships `"num_games": 6`. A negotiated match may raise it by mutual agreement; it is never lowered. |

---

## C-002 — Do docstrings count toward the 150-line limit?

| | |
|---|---|
| **Where** | Excellence guide §3.2 vs. §3.3 |
| **The conflict** | §3.2 caps every source file at 150 lines of code, excluding blank lines and comment lines. §3.3 *mandates* a detailed docstring on every module, class and function. The guide does not say which category a docstring falls into. |
| **Our choice** | **Docstrings are documentation, not code, and are excluded from the count.** |
| **Why** | Counting them would place the two requirements in direct opposition: the better a file is documented, the closer it would sit to the limit, creating an incentive to under-document exactly where the guide demands the opposite. Reading a docstring as a comment resolves the tension in the direction both sections point. |
| **Scope of the exemption** | Only genuine docstrings — the leading string expression of a module, class or function. A triple-quoted string bound to a variable is data and counts as code. Implemented in `core/shared/loc_counter.py` via `ast`, and unit-tested. |
| **Transparency** | `FileReport` carries both `code_lines` (the enforced metric) and `total_lines` (every physical line), so the raw size of a file is always visible and nothing is hidden by the interpretation. |

---

## C-003 — Board size: 7×7 in Appendix F, 10×10 in the belief-map figure

| | |
|---|---|
| **Where** | Appendix F table 13 vs. figure 8 in Chapter 6 |
| **The conflict** | Appendix F sets `[board size]` = 7 (minimum). The Bayesian belief-map illustration in Chapter 6 is drawn on a 10×10 grid and its caption reads "for example 10×10". |
| **Our choice** | **7×7 as the default**, with the board size read from config and never hardcoded. |
| **Why** | The book's own framing rule states that figures and examples illustrate but do not bind, and that Appendix F is the only binding source for quantities. 7 is a *minimum*, so a 10×10 board remains legal if both teams agree — our engine handles any size without a code change. |
| **Effect** | `grid_size` is a config value. Tests parametrise over 5×5, 7×7 and 10×10 to keep the engine size-agnostic. |

---

## C-004 — Line endings and the byte-identical config requirement

| | |
|---|---|
| **Where** | M#11 (shared config must be byte-identical on both sides) vs. cross-platform Git defaults |
| **The problem** | Not a contradiction in the book, but a trap it does not mention. Git on Windows checks files out with CRLF by default; on macOS and Linux with LF. Two teams on different platforms would hold configs that are semantically identical but **byte-different**, so `config_sha256` would not match and the handshake would refuse the match before the first move. |
| **Our choice** | Pin LF for all text files via `.gitattributes` (`* text=auto eol=lf`), published to both repositories. |
| **Why** | M#11 is enforced on bytes, not meaning. The failure would appear only when playing an opponent on a different operating system — the worst possible moment to discover it. |
| **Effect** | `.gitattributes` is in `SHARED_PATHS` and unit-tested. Opponents on any platform hash the same bytes. Also silences Git's CRLF warnings on Windows. |

---

## Template for future entries

```markdown
## C-00N — short title

| | |
|---|---|
| **Where** | chapter / appendix / file |
| **The conflict** | what the two sources say |
| **Our choice** | what we implemented |
| **Why** | the reasoning |
| **Effect** | what changes in the code or config |
```
