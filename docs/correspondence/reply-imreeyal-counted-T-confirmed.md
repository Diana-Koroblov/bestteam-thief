# COUNTED T CONFIRMED — 20:30 IL tonight. Fix shipped, pair re-declared, pre-T exchange in full

Subject: bestteam ↔ imreeyal — T CONFIRMED 20:30 IL tonight. Artefact fix shipped, heads
re-declared 22e41379 / 67e859b6, and our whole side of the pre-T exchange below in writing

Hi imreeyal —

**T CONFIRMED: 20:30 IL tonight.** No counter-proposal; the time suits us and we would
rather stop waiting on each other too.

## Your three, before the T

**1. Artefact fix — SHIPPED.** `role_split` and `scent_model_digest` are populated in the
filed config snapshot. The scent value is the one we declare on the wire, resolved by the
same lookup our handshake uses — keyed on the negotiated `pheromones.decay_model` — so the
artefact records the number we actually sent rather than a second internal one. Green on our
full suite at 1803 tests, with lint, file-size, secret-scan and split-repository gates clear.

This is the field whose emptiness made you write and ask what changed between our two
windows. Tonight it will read `1-1-1-1-1-1` in every one of the six config artefacts, and
that class of question becomes answerable from a diff.

**2. Heads — RE-DECLARED. This line is that re-declaration.** Verified against the remote
rather than against our clones:

    cop    22e4137970478a4d9890e9fd2f3798b0f95a3b0c   (bestteam-cop,   origin/itay)
    thief  67e859b66c227de3af7e50bc1013faeffa2a6d35   (bestteam-thief, origin/itay)

Nothing lands after this line. The superseded pair `51dbf196` / `8ecb8489` still resolves and
still descends correctly if you want to re-verify either of today's windows against it.

**3. Live mail test — PASSED.** A real send through our Gmail path succeeded today, ahead of
the T and on the same credentials the counted will use. Our OAuth app is published to
production, so the seven-day refresh expiry that bites apps left in Testing does not apply to
us, and the send path is the one routed through our Gatekeeper — every outbound call clears a
token bucket, a daily quota and a DOS detector, so a runaway loop cannot reach the lecturer.

Worth restating one detail, because it looks alarming from outside and is not: our stored
token file shows a past expiry and is not rewritten on use. That is by design — credentials
refresh in memory on each send and the new access token is deliberately not persisted, so a
stale-looking token file is the normal steady state here rather than a symptom. The
successful send is the evidence, not the file's timestamp.

The stop-and-agree-never-silent-resend rule stands: if anything fails at settlement we stop
and agree with you in-thread before any second attempt.

## Pre-T exchange, our half, in writing

**Configured recipient — the lecturer alone.**

    rmisegal+uoh26finalgame@gmail.com

Read from `[email] recipient`, identical in both role configurations, with no `.env`
override. Not you, not our own inboxes, not the friendly redirect we used tonight. One result
email from us per series. Please state yours and we will compare the strings character for
character before either process arms.

**Frozen pairs, re-verified via the API just now.**

    ours    cop   22e4137970478a4d9890e9fd2f3798b0f95a3b0c   (bestteam-cop,       origin/itay)
            thief 67e859b66c227de3af7e50bc1013faeffa2a6d35   (bestteam-thief,     origin/itay)
    yours   cop   c9ae097220e0c7a95816f9eb12514139841372b0   (copthief-p2p-cop,   origin/main)
            thief 65932736d1dec0d73b1f0f406001a9cce8a267e5   (copthief-p2p-thief, origin/main)

Both of ours resolve on `origin/itay` and match our local clones exactly, zero modified files
in each.

**Your re-declared pair is pinned and supersedes `bdbce8a2` / `aa9c5c0b` on our side.** Noted
that it carries your stranger-identity guard and no strategy change. We will re-resolve both
against your remotes at T rather than trusting this paste — the same standard you applied to
us, and the right one.

**Counters, computed from the truth at T rather than typed.** Our identity declares
`counted_games_played = 0` — that is games played *before* this one, read from
`docs/LEAGUE_LOG.md`, which holds zero counted rows and refuses to hand a number to the
handshake if its table and its stated total ever disagree. Yours declares 6. So the counted
artefact will file:

    games_played_including_this   { bestteam: 1, imreeyal: 7 }
    first_meeting_between_groups  true

We have run those two through the shipped code rather than asserting them: they are what our
filer produces given your declared 6, and they are exactly the figures you specified. The
`+1` is the fix you prompted, and tonight is where it executes on a series that counts.

**Diversity.** Derived, not claimed, and not modest — gated on `counted AND first_meeting AND
winner == group`. If you win it prints true for imreeyal and false for us, and we will file
that without argument.

**Ordering we will hold to.** The LEAGUE_LOG row goes in **after** the filing, never before.
Adding it first would make our own counter include this match, turn the `+1` into a double
count, and flip `first_meeting_between_groups` to false — taking the diversity line with it.

## T protocol — confirmed, exactly as the last two windows

Doors up five minutes early and **held**. All four curl-checked. Identity probe on both of
your doors — initialize, then dial what each one *says*, not what its hostname claims. 406 by
T+30s or a kill-and-rename in writing. No debugging inside the window. Stray-process check
after.

Alternating, **bestteam cop on the odd sub-games**, your thief opens g01. Terms `a284082d` /
`81ebee59` / `229ae648` / `020947da` unchanged. Our two processes arm with the identical
`--role-split 1-1-1-1-1-1` and `--first cop` — the pair of arguments whose mismatch void'd
this morning, now stated in writing on both sides rather than typed twice from memory.

**Fresh empty `--out` on our side**, a directory that does not yet exist, and tonight's
friendly artefacts archived out of the way before T. The counted carries the same `game_id`,
`game_uid` and filenames as every friendly — your item 6, and we are not relying on the merge
guard alone to catch it.

## One counted, and it stands forever

Understood and accepted without qualification. Whatever the score, no rematch, no run-it-back
— M#52 and your item 2. Four windows got us to a point where neither of us expects a surprise
tonight, which is the only reason a one-shot series is a reasonable thing to agree to.

We arm on your word. See you at 20:30.

Your re-declared pair, pinned: cop `c9ae0972…` / thief `65932736…`.

— bestteam
   Itay Malich, Diana Koroblov
   itay.malich2@gmail.com
