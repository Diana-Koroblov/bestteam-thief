# Reconciled: cca1243e reproduces on both our roles — but we moved the six keys rather than deleting them, and your second pin is not independent

Subject: bestteam ↔ imreeyal — cca1243e CONFIRMED both roles, item 9 closed; heads
re-declared. One correction and one defect you should have: your "bound twice" pin is
computed FROM the key you asked us to drop, and our reviewer would have refused your file

Hi imreeyal —

**Reconciled, shipped, and this letter is the item-5 re-declaration you asked for.**

Standing items first, so this letter stands on its own:

- **Artefacts line, paid:** `artefacts: 14 file(s)` — 1 declaration + 6 config + 6 log +
  1 result, for `bestteam-vs-imreeyal` / `ffad01a2-4965-be0b-c708-3cdbedd7373a`.
- **The ten confirmations stand** exactly as sent: 1 confirmed (lecturer alone,
  `rmisegal+uoh26finalgame@gmail.com`, no redirect), 2 confirmed, 3 corrected and fixed
  (`games_played_including_this` now files before+1 on a counted series, pinned by tests),
  4 confirmed (derived, not claimed), 5 re-declared below, 6 confirmed and your LEAVE IT
  adopted, 7 confirmed (app published to production), 8 confirmed, 9 closed by this letter,
  10 confirmed.
- **Item 6 uid: LEAVE IT**, on your declaration. The counted shares the pairing uid with the
  friendlies by design, and our archive plus a fresh empty `--out` carries the load.

Now the substance.

**Reconciled.** Dropping your six from our shared contract gives, on both our cop and
thief role directories, byte for byte:

    cca1243e9a4b06611f77c98077613056a7490a5b27c0da1da06fc26f33b1a513

Nine top-level keys: `agreed_between`, `board_and_agents`, `movement_and_barriers`,
`network_and_league`, `pheromones`, `rate_limiter_gatekeeper`, `schema_version`,
`scoring`, `world`. Your diagnosis was right in every particular, including that it was
our file carrying the excess and not yours. Item 9 is closed from our side.

Three things you should know before you treat that as finished.

## 1. We moved the six keys. We did not delete them — and deleting them is not safe

Your instruction was "drop the six keys, re-derive". We dropped them from the **contract**
and put the same six values into our **private** config, which our loader merges underneath
the shared file. The digest you asked for is what we now publish and what we will file; the
values still reach the code.

We did it that way because we checked what deleting them outright would do, and it is bad
in three separate ways:

- **`capture.resolution`, `capture.stay_counts_as_move`, `capture.swap_is_capture`** are
  read through a *required* lookup in our rules engine. Absent, it raises. A peer that
  cannot build its rules engine does not play a degraded match, it takes a **technical
  loss worth 0 to both of us**.
- **`pheromones.decay_model`** is read with a default of `"multiplicative"`. Absent, our
  code would have silently played and filtered on the model we did **not** agree — the
  exact blur we fixed on 16/08, arriving back through a config edit.
- **`seal_scent_digest`** and **`seal_barrier_cell`** default to `false`. Absent, we would
  have quietly stopped sealing both, changing our commitment shape under an opponent
  auditing against the old one.

We are telling you the mechanism rather than just the digit because "we dropped the keys"
and "we dropped the keys and kept the values" produce identical `config_sha256` and
completely different matches. You should know which one you are playing.

## 2. Your second pin is not independent — it is computed from the key you asked us to drop

You wrote, to reassure us: *"the subtractive model is bound twice outside the contract —
scent_model_sha256 81ebee59 sealed inside every step-0 declaration."*

The value is right and we send it: `81ebee59…` is the registry's named bundle for
subtractive, and both our roles declare exactly that. No disagreement on the number.

The correction is about *why* it is safe. On our side that declaration is a lookup **keyed
on `pheromones.decay_model`** — the very key you asked us to drop. Delete it, let it default
to multiplicative, and the same line declares `934c220d…` instead. The second pin does not
hold the first steady; it follows it.

So the reassurance is right about the outcome and wrong about the mechanism, and the
difference is not academic: a team that had followed it literally would have deleted the
key, defaulted to multiplicative, declared the *other* registry hash, and blurred its own
filter — while the contract digest you asked for matched perfectly. That is precisely the
failure this reconciliation existed to prevent, which is why we moved the key rather than
deleting it, and why we are saying so rather than accepting a reassurance we could not
reproduce from our own code.

## 3. Reconciling found a defect that would have refused YOUR file at the handshake

This is the one you should care about most, and we would not have found it by editing JSON.

Our config reviewer — the thing that reads your proposed `game.json` and exits non-zero
rather than let us sign something illegal — treated an **absent `version` key as an illegal
value**. Your nine-key contract carries no `version`. So our own reviewer, run against the
contract we had just spent two letters agreeing with you, would have listed it as illegal
and refused it. Minutes before a match, on the file we asked you for.

Its own module docstring names this exact failure first: *"Refusing a legal proposal...
would produce a green suite while losing a match."* It was doing precisely that.

Fixed to the same rule as everything else here — absence is silence, a stated incompatible
version is a claim — in both the reviewer and the loader.

Two things worth saying about it. First, it is independent of the digest: it would have
fired whether or not we reconciled, because it is about the **shape** of your file rather
than its content. Second, **check your side.** If your kit refuses an absent `version` and
we ever send you a contract shaped like the one you asked us to adopt, the same thing
happens in the other direction — and neither of us would suspect the reviewer, because both
files would be correct.

## Also, a gap of ours, since we are listing them

Our filed config artefact from the 2200 window carries `scent_model_digest` and `role_split`
as **empty strings**. Not a rule breach and not a mismatch, but the filed artefact should
record the numbers it was played under, and ours does not. We are noting it rather than
quietly fixing it because you have our 2200 file and will see it.

## Heads — re-declared, live, and verified against the remote

The reconciliation is a config commit, so the pair moved exactly as you said it would. This
is the re-declaration; both are already on `origin/itay` and checked against the remote
rather than against our local clones:

    cop    51dbf196b45b659e9ff0b6b0cd81d33e6ac497ff   (bestteam-cop,   origin/itay)
    thief  8ecb84892371f6e2ca5ca881e6f152bdbceeba78   (bestteam-thief, origin/itay)

Verified rather than asserted, and it took longer than "drop six keys" suggests: both roles
produce `cca1243e`, all six moved values still resolve, the rules engine builds from them,
the scent model still reads subtractive, and the **full suite is green — 1803 passed, 92%
coverage** — with lint, file-size and secret-scan gates clear. We skipped only the
192-sub-game strategy benchmark, which a configuration change does not exercise.

That run mattered. Making the contract match yours broke **thirty** of our own tests, and
working through them is how we found the reviewer defect in section 3. A team that had edited the
JSON and pushed would have had a matching digest, a green-looking repository, and a
handshake that refuses you.

**Order accepted: reconciliation first, then the friendly — and the reconciliation is now
done and pushed.** The pair above is live on `origin/itay`, the published contract at both
repositories hashes to `cca1243e`, and nothing further will land.

Confirm `cca1243e` against our heads and we will say **"up"** in one line and hold doors.
The friendly then proves three things at once rather than one: your two endorsed
check-lines, the corrected league counter, and the corrected config artefact — all in a
series that can be re-run, which is exactly the argument you made back to us.

Your pair, unchanged and pinned on our side: cop `bdbce8a2…` / thief `aa9c5c0b…`.

— bestteam
   Itay Malich, Diana Koroblov
   itay.malich2@gmail.com
