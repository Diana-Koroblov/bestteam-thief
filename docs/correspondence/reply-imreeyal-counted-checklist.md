# Reply to imreeyal — the ten counted confirmations, two corrections and one defect we found in ourselves

Subject: bestteam ↔ imreeyal — ten confirms, artefacts line owed now paid (14), heads
RE-DECLARED per item 5, and one real defect found in our league counters before it filed

Hi imreeyal —

Thank you for the verdict, and for the checklist. Ten answers below, one line apiece as
asked, then the substantiation for the three that are not a plain "confirmed". Two of
those are corrections to us, one is a correction to the framing in item 9.

**Artefacts line owed, paid first: `artefacts: 14 file(s)`** — 1 declaration + 6 config +
6 log + 1 result, for `bestteam-vs-imreeyal` / `ffad01a2-4965-be0b-c708-3cdbedd7373a`.
That closes the window from our side.

---

## The ten, one line each

1. **CONFIRMED.** Recipient is already the lecturer alone — `rmisegal+uoh26finalgame@gmail.com`
   in both role configs, no redirect at you, no `.env` override; we will state it in the pre-T
   exchange and expect yours to match.
2. **CONFIRMED.** One counted per pairing, permanent, whatever the score — no rematch, no run-it-back.
3. **CORRECTED — the defect is ours.** Our `counted_games_played = 0` is truthful and derived,
   but our `games_played_including_this` files the *before* count and would have printed
   bestteam 0 / imreeyal 6 against your 7 / 1; fixing to before+1 on both sides before T.
4. **CONFIRMED.** Diversity is already derived, not claimed, and not modest — gated on
   `counted AND first_meeting AND winner == group`, so a win of yours prints imreeyal true.
5. **RE-DECLARED, and this line is that re-declaration.** The posted pair is superseded: the
   two letters landed after settlement, so the frozen heads are now cop `6adee601…` /
   thief `6c431269…` on `origin/itay`, and nothing lands after this line.
6. **CONFIRMED, and it is worse than you flagged** — not only the same `game_id` and filenames,
   the `game_uid` is identical too; archiving before T and running the counted into an empty `--out`.
7. **CORRECTED — cannot confirm from disk, will verify live.** Our stored token expired
   2026-08-08T17:07:12Z and carries a refresh token, which is fine unless our consent screen
   is still in Testing; we run a real send inside the hour before T and report the result in-thread.
8. **CONFIRMED.** Exactly tonight's shape, with items 3 and 4's league fields as the only deltas.
9. **CONFIRMED on substance, CORRECTED on mechanism.** All four kinds with the 30-second check,
   and our filed config already *is* the shared contract with zero extra keys — but `17606f14` is
   a canonical digest, not a digest of an extended file, and a raw-byte sha cannot match between
   two teams; please tell us what `4e0510ed` is over.
10. **CONFIRMED.** T protocol identical: doors up five early and held, all four curl-checked, identity
    probe by initialize-then-dial-what-it-says, 406 by T+30s or kill-and-rename in writing, no
    debugging inside the window, stray-process check after; alternating, bestteam cop on odds, your
    thief opens g01, terms `a284082d` / `81ebee59` / `229ae648` / `020947da` unchanged.

---

## Item 3 — we found this by checking rather than by answering, and it would have filed

Your lesson from the other pairing is the right lesson and we were about to be the next
example of it, by a different mechanism than theirs. Ours is not a stale constant. It is
an off-by-one hiding behind a correct-sounding field name.

Our identity block declares `counted_games_played = 0`, and that is honest: it is read
from `docs/LEAGUE_LOG.md`, which has zero counted rows, and the reader refuses when the
table and its stated total disagree. No complaint there.

But the *result* field is `games_played_including_this`, and we populate it with the
number that excludes this one. Our filed 2200 artefact says so in as many words:

    games_played_including_this   {"bestteam": 0, "imreeyal": 6}

Against your 7 / 1 that is a visible disagreement on a league line, in front of the
grader, which is exactly the shape item 4 warns about. No test pinned the field, so
nothing would have caught it. Fixing it to before+1 for both sides, and pinning it.

One ordering consequence we will hold to, because it is the other way this field goes
wrong: **the LEAGUE_LOG row gets added after the filing, not before.** Adding it first
would flip `first_meeting_between_groups` to false and take the +10 with it.

## Item 5 — the heads moved, and this is the re-declaration before arming

Full pair, frozen now, both on `origin/itay` and both verified against the remote rather
than against our local clones:

    cop    6adee60190593f1257d4fdad31530bf7042182a5   (bestteam-cop,   origin/itay)
    thief  6c431269d6ebd4145dd9638b00f42ea629d588c8   (bestteam-thief, origin/itay)

What landed was the two letters, as documentation, after your PASS and after the results
were agreed. We are not claiming that as compliant with the letter of the promise — the
promise said settled *and re-declared*, and we did the settled half and are doing the
re-declared half now, in the thread, before arming, which is the procedure item 5
specifies. The old pair `6bec686a` / `f4e113a9` still resolves and still descends
correctly if you want to re-verify tonight's series against it.

## Item 7 — the honest answer is that we do not know yet

Our token file carries `expiry: 2026-08-08T17:07:12Z` and a refresh token. Normally that
is a non-event: the sender refreshes silently on every send, and reports did leave on the
16th and 17th. The risk we are not willing to wave through is that Google expires refresh
tokens after seven days while an OAuth app is still in **Testing** publishing status, and
our file has not been rewritten since the 8th. That is consistent with both "refreshes
work and are not persisted" and "the refresh token is dead", and those two look identical
from here.

Since a dead token at settlement is rule 35 with both teams zeroed, we treat this as
unverified until a real send succeeds. We will run one to ourselves inside the hour
before T and post the result. The stop-and-agree-never-silent-resend rule stands.

## Item 9 — the substance is agreed, the comparison method is not

We agree completely on what must be filed: the shared `game.json`, the private C-00x
flags staying in private config. We checked rather than asserted, and our filed artefact
already satisfies it — the embedded `shared_config` has **zero** keys beyond the
agreement, and its digest equals the digest of our live `config/*/game.json` exactly.

Where we think the framing is off: `17606f14` is not "over our extended file". It is the
**canonical** digest — sorted keys, fixed separators — of precisely the shared contract.
The raw bytes of our copy hash to `01d3e9fe`, and that number is not meaningful to
compare, because two teams holding byte-identical *content* will still differ on raw sha
over key order, indentation and trailing newline. That is the whole reason the protocol
hashes canonically everywhere else.

So `4e0510ed` and `17606f14` disagreeing is not yet evidence of a content difference.
Could you tell us what `4e0510ed` is computed over — raw file bytes, or canonical? If
raw, we would rather compare canonical digests of the shared contract and settle it in
one line before T than discover at settlement that we were comparing two different
questions.

**One thing we are volunteering because you would find it otherwise.** Our
`outbox/game.json` is stale — it is the nis-yar1 pack from the 13th, and it disagrees
with our live imreeyal contract on `decay_model` (multiplicative vs the subtractive we
agreed) and on `swap_is_capture`. It will not be sent and it will not be filed; the filed
contract is `config/*/game.json`. We are telling you because a stale pack in a directory
named outbox is exactly the kind of thing that gets picked up by the wrong hand at T.

## Item 6 — the collision is on the uid too

You flagged `game_id` and filenames. Checking it, `game_uid` repeats as well: all three
windows — the 16th, tonight's friendly and tonight's 2200 — carry
`ffad01a2-4965-be0b-c708-3cdbedd7373a`. It is derived from the pairing, not from the
series, so the counted will carry it too unless one of us changes something.

Archiving and a fresh empty `--out` fixes the Frankenstein risk you actually named, and
we are doing both regardless. But if a grader sees a counted result sharing a uid with
three friendlies, we would rather have decided that on purpose. Happy either way — say
which you prefer and we will match it:

- **leave it** — uid identifies the pairing, and the archive plus fresh `--out` carries the load; or
- **make it per-series** — both sides derive the uid with the series date mixed in, agreed in one line before T.

---

Ten confirmations above, artefacts line paid, heads re-declared and frozen at
`6adee601…` / `6c431269…`. Outstanding from us before T: the item 3 fix, the live mail
verification, and your answer on what `4e0510ed` is over. Outstanding from you: that
last one, and your preference on item 6's uid.

Lock the T whenever you are ready — we will not move anything again without a line here first.

— bestteam
   Itay Malich, Diana Koroblov
   itay.malich2@gmail.com
