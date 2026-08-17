# Reply to imreeyal — sealed-record reader in, result reshaped to your template, heads posted; and one item in your list we have no record of

Subject: bestteam ↔ imreeyal — all four changes shipped and pushed; heads below;
verification friendly agreed; and please tell us what the step-1 scent frame is

Hi imreeyal —

Everything you asked for is in, shipped and pushed. Heads at the bottom. One item in your
verification list we cannot confirm because we have never heard of it — §5 below, and it
is the only thing standing between us and naming the T.

**The score is untouched throughout: 40–60, 4–2 to imreeyal.**

---

## 1. §2 — corrected, and the sealed record is now the source

Your copy and ours agree on your column: `5bf3cfc…` in all six.

    g01: 662d2866... -> 5bf3cfcce27a05a6c16263fa1314f8533bf1657f
    g03: 662d2866... -> 5bf3cfcce27a05a6c16263fa1314f8533bf1657f
    g05: 662d2866... -> 5bf3cfcce27a05a6c16263fa1314f8533bf1657f

    consensus before : ff77bb1d6e31751a...
    consensus after  : ff77bb1d6e31751a...  UNCHANGED

**The reader now takes your commit from your sealed step-0 record**, with the handshake
identity block kept only as a cross-check and `--their-commit` left as an operator
override above both. Precedence is strongest-source-first, exactly as you put it.

We took your two-channel rule further than you asked, because your own sentence made the
case for it: *"a mismatch between a peer's OWN two channels is itself a finding"*. So a
divergence is not a tie we break quietly — we file the sealed value **and say so**:

    their two channels disagree: sealed step-0 5bf3cfc... but handshake
    declared 662d286... - filing the sealed one

A silent pick would destroy the only evidence that the disagreement existed, which is
the thing your rule exists to preserve. Four tests pin the precedence, including that a
peer who seals no commit at all still gets its handshake value filed rather than a blank
— sealing nothing is not the same as declaring nothing.

## 2. The result file — rebuilt to your template. Corrected copy attached.

Adopted in full, and the attachment is our re-filed 17/08 copy in the new shape.

- **Top-level keys in your order, and no others.** As it happens our builder already
  constructed them in exactly that sequence; the file didn't show it because our writer
  sorted keys on the way out. The result file now writes in insertion order. Every other
  artefact still sorts — this is the one file two teams diff against each other rather
  than against a previous run of their own, so it is the one that earns the exception.
- **`schema_version` is now `1.1`.** We checked before agreeing rather than after: §9.3.3
  mandates the report's *structure* and pins no version string for it, and the `1.2` we
  had been sending is Appendix B.3's — which belongs to the shared `game.json`, a
  different file with a different schema. So this was ours to align and we have.
- **The `league` block is gone**, everywhere, not just on counted files. Your channel
  argument won it: a friendly is defined by never reaching the grader, so a marker inside
  a file the grader never opens is a diff that buys nothing.
- **Mail subject** is now `Police-Thief series result: winner <group_id> (reported by
  <role>)`, the same string counted or friendly, no suffix. A drawn series sends
  `winner none` rather than a blank, so the subject still parses into four fields.

**One place we resolved an ambiguity in your letter, and you should overrule us if we
read it wrong.** You wrote *"sub-game rows and final_result exactly as your current file
already has them"* — but our rows carried a `steps` field and yours do not, and your
verification item 2 asks for a cross-diff of **zero** differences, which `steps` makes
impossible on every row. Read together with your §5 (*"it stays unfiled"*), we took the
zero-diff reading and **removed `steps` from the filing**. It is not lost: it now lives
as `step_count`, per side, inside our sub-game log — which is where you said the counts
belong and where their disagreement is trivia. Say the word and we will put it back.

## 3. The logs — thank you, and the correction is accepted

Your league math is right and we will stop over-charging ourselves for it: nothing from
16/08 or 17/08 is ever submitted by either team, so the missing artefacts cost the league
nothing. What mattered was that the four kinds exist from here, and they now do —
declaration, config, log, result, written per sub-game.

Consequence #2 stands as we stated it: our acceptance of §2 is corroborated rather than
independent, and we would not have offered it as more than that.

## 4. §1, §3, §4, §5 — closed

Your reader fix is noted as landed and run; our copy is ready and re-filed, so this
friendly's paperwork closes the moment you confirm receipt of the attachment. §3 and §4
close as you state them. §5 closes with `steps` unfiled on both sides — see the
ambiguity note in §2 above for the one decision we made inside it.

## 5. ⚠ The step-1 scent frame — we have no record of this, and will not confirm blind

Your verification list asks us to declare our cop's step-1 scent frame *"clean (fix
landed), or declared beforehand as expected evidence-noise"*, and says *"silent is the
only wrong option"*. You also refer to *"the one-line fix"* as though it is something we
have in hand.

**We have never heard of this.** It is in neither of your previous letters to us, and a
search of our correspondence, our contradictions register and our TODO turns up nothing
about a step-1 frame, a first-frame scent anomaly, or a one-line fix for one. Either a
message went astray between us, or it was raised with a different pairing and reached our
thread by mistake.

We are not going to declare an anomaly clean when we do not know what it is, and we are
not going to declare it noisy either — both would be inventing a position. So, taking the
third option your own rule allows and declaring it openly rather than staying silent:

> **We cannot answer item 3 yet. Tell us what you observed — which sub-game, which frame,
> and what the value was against what you expected — and we will either fix it before the
> window or declare it as expected noise, in writing, before we arm.**

If it turns out to be real, we would rather find it in your description than in a live
series. This is the one item blocking the T.

## 6. The verification friendly — agreed, and agreed for your reasons

Yes, and we would have asked for one if you had not. Four changes on our side have never
run in a live series, and *"a passing test and a working window are different facts"* is
exactly the lesson our own morning taught us: our logs gap survived two complete series
behind two documents that both said the opposite.

Your four checks, with what we will have ready for each:

1. **All four artefact kinds on disk, both sides.** Ours writes `declaration_`,
   `config_…_gNN`, `log_…_gNN` and `result_` per series, and prints an
   `artefacts : N file(s)` line at settlement so the count is visible without a
   directory listing.
2. **Result shape, zero cross-diff.** See §2 — including the `steps` decision, which is
   the one thing that could still put a difference on every row if you overrule us.
3. **Step-1 scent frame.** Blocked on §5.
4. **Your commits from your sealed records, no operator flag.** We will run with no
   `--their-commit` at all, so the derivation has no manual input anywhere in it. Your
   `5bf3cfc…` appearing on all six by itself is the check passing.

Terms unchanged, uncounted, reports to the two teams only, bestteam cop on odds
alternating, **your thief opens sub-game 1** — confirmed on our side, and worth saying
explicitly because our reference wire has the thief open too, so we agree with no change
needed.

## 7. Our heads, pushed, as you asked

Both published and clean before this message went out:

    cop    c05619122c14b081b15172c7157ddd119951838d   (bestteam-cop,   origin/main)
    thief  9e977a47cf6c28c2645a49abd2e4b06d1b376976   (bestteam-thief, origin/main)

Each resolves to `published on origin/main` — our runner refuses to arm on a head that is
dirty, has no remote, or sits on no remote branch, so these are the same hashes our
step-0 records will seal.

Our `config_sha256` is unchanged at `17606f14…` and our `game_uid` still derives to
`ffad01a2…` — the terms have not moved, only the code around them.

---

Answer §5 and name the T, and we are on the tunnel five minutes early.

— bestteam
   Itay Malich, Diana Koroblov
   itay.malich2@gmail.com
