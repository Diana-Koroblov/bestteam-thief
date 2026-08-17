# Reply to yanell11 — decay conceded, one term was going to refuse us, and a wire question you did not ask

Subject: bestteam ↔ yanell11 — you are right about the decay model; `setting` would have
refused the handshake; and we need one more answer about who opens before either of us arms

Hi nell, Yanal —

Thank you for a genuinely useful letter. You listed the terms value by value instead of
leaning on a digest that cannot match, and that is exactly what let us find the one term
that would have refused this match at the handshake. Details below, in the order you
raised them, plus one item you did not raise that matters more than any of them.

**Short version.** You are right about the decay model and we have taken yours. We have
taken your `setting` too — ours said something else, and it would have refused. We will
run **unlabelled**, and your unlabelled `game_uid` reproduces bit-exact on our side. But
we cannot name a start time yet, because your endpoint is down and because our two wires
disagree about **who sends the first message of a sub-game**.

---

## 0. The date, and why we are not proposing a new time in this message

You read it correctly: we meant **Monday 17/08**, today. Our note said "Sunday 16/08",
which was simply wrong — the weekday and the date did not agree with each other, and you
were right to stop and ask rather than assume either half.

That said, 15:00 has now passed while we worked through your terms, and your endpoint is
not up:

    uv run python -m core probe https://counting-truce-childcare.ngrok-free.dev/mcp

    probing https://counting-truce-childcare.ngrok-free.dev/mcp
      unreachable: HTTPStatusError: Server error '502 Bad Gateway'
      Their peer is not running, or the URL is wrong. An ngrok URL is
      live only while their process is up - ask them to start it.

A 502 through a reserved domain is the tunnel answering with nothing behind it, so this
is your process being down rather than the URL being wrong. Nothing to fix if you simply
had not started yet — we mention it only so you know we tried, and so you know the probe
is the check we will run before we arm.

**So: name any slot that suits you**, today or tomorrow. Our T is flexible and we would
rather move than rush §2 below. We are not proposing an hour ourselves because the
answer to §2 may cost us a code change, and we will not book a slot we might not be able
to keep.

## 1. The decay model — conceded, without reservation. You are right.

We have changed it. No flag, no "we support both, pick one": the book is explicit and we
were wrong to have shipped the other value into this conversation.

You quoted the locking box. The formula section says the same thing twice more:

> §4.3 — τᵢⱼ(t+1) = max(0, (1 − ρ)·τᵢⱼ(t) + Δτᵢⱼ)
>
> §4.3 — "ρ — decay rate. Here ρ = 0.10, so the factor (1 − ρ) leaves 90% of the
> existing scent each turn."
>
> §4.4, the lie-detection worked example — "we would expect to find in the north a fresh
> trail at strength about (1 − ρ)·0.9 = 0.9 · 0.9 ≈ 0.81"

Three passages, one reading, and 0.81 is written out as a literal in two of them. Our own
contradictions register has had this as the book's position all along — the subtractive
value was a per-match concession to a different pairing that we should have reopened for
this match instead of inheriting it by silence. That is on us, and it is precisely the
failure your letter was designed to catch.

**The happy consequence: our declared hash is now byte-identical to yours.**

    our scent_model_sha256 : 934c220d5bf62acaa3297c6c9d723ea954c220260b02292ca17f6d5daef9f4d9
    yours                  : 934c220d5bf62acaa3297c6c9d723ea954c220260b02292ca17f6d5daef9f4d9

So this stops being an advisory mismatch that both negotiators log and becomes an
agreement that verifies. Our worked example now reads 0.9 → 0.81.

**One divergence we are declaring rather than letting you discover.** The registry hash
above names `multiplicative_book_v1`, and our *merge* rule differs from that document in
one place: where two emissions land on the same cell we take `max`, where its text pins a
clamped sum. Identical for the single-emission worked example, and identical everywhere
the two fields do not overlap; it can differ where they do. We are declaring the
registry hash because that is the model we are running the physics of, and telling you
about the one place our implementation departs from its prose. If you would rather we
matched the clamped sum exactly, say so and we will change it — it is a small change and
we would rather play your reading than argue for ours.

## 2. ⚠ Who opens a sub-game? This is the one that will cost us the slot.

You settled `turn_order: cop_first` under the capture heading, and for capture we agree
completely. But `turn_order` also decides something the capture discussion does not
touch: **which peer sends the first `receive_turn` of a sub-game, unprompted.**

On this wire there is no separate "your move" signal — receiving a turn message *is* the
turn token. So somebody must speak first with nothing to answer, and our implementation
makes that the **thief**:

    core/compat/session.py

        """**The thief opens.** There is no separate "your move" signal: receiving a
        turn message *is* the turn token, so somebody must send the first one
        unprompted, and the reference makes that the thief. Two peers that both wait,
        or both open, is a sub-game nobody plays."""

        if self.role is Role.THIEF:
            await send_turn(self, None)

Read literally — *"cop commits and sends, thief receives and commits and sends"* — yours
makes that the cop. If we are both right about our own code, then in **sub-game 1**,
where you hold THIEF and we hold COP:

    us   : we are the cop, and on our wire the thief opens  -> we wait
    them : you are the thief, and on your wire the cop opens -> you wait

Both peers wait, both watchdogs fire, and the sub-game is a timeout — a technical loss
for two teams who agreed on every term in the contract. Sub-games 3 and 5 do the same.
Sub-games 2, 4 and 6 fail the other way: we both open, and each of us receives an
unprompted opener where we expected an answer.

**We are not asserting you are wrong.** Your `interop_profile` is `kit`, and the kit's
own wire is the one our module was built against — which is why we think there is a real
chance `cop_first` in your negotiator describes *within-step resolution order* (cop
resolves before thief) while your actual opener is still the thief, exactly as ours is.
In that case we already agree and there is nothing to do.

**So please answer this one precisely, and it is the only thing we are blocked on:**

> In sub-game 1, with you as THIEF and us as COP: which process sends the first
> `receive_turn` call, before it has received anything?

If the answer is "our cop does", tell us and we will make our opener configurable and
re-publish before we play — it is a contained change on our side, and we would rather
spend an hour on it than discover this at 15:00. If the answer is "our thief does, same
as yours", we are already agreed and we can book the slot on your next message.

This is the same class of thing your `game_id` warning is: cheap in writing, expensive in
the logs.

## 3. `setting` — the one term that differed, and it would have refused us

Your list is what caught this, so thank you for writing it out in full. Thirteen of your
fourteen terms matched ours exactly. The fourteenth did not:

    setting: ours='New York'  theirs='Haifa'

Left alone, that is not a warning on our side. Our pairing guard diffs the flat terms and
**refuses** on any difference, before a single move is sent — the correct behaviour, and
a booked slot lost to a string. It was another pairing's value left in our shared config,
the same way the decay model was.

**We have taken yours: `setting` is now `Haifa`.** All fourteen terms now match.

## 4. The series label — let us run unlabelled, and here is our arithmetic

We follow your reasoning about two series colliding, and it is a real hazard. For *this*
match we would rather run **unlabelled**, for two reasons.

First, your unlabelled value is reproducible on our side, exactly:

    game_id  : bestteam-vs-yanell11
    game_uid : b8f8c576-5c08-a5f6-2c4d-d0d97c612b20
    theirs   : b8f8c576-5c08-a5f6-2c4d-d0d97c612b20
    MATCH    : True

That is our own `game_uid()` — the kit's formula, `uuid(sha256(canonical(terms) + "|" +
"|".join(sorted(pair)))[:16])`, verified against the kit's `verify_vectors.py` on our tree
— run against the fourteen agreed terms with `setting: "Haifa"`. Two independent
implementations landing on the same UUID is the strongest evidence either of us has that
we are signing the same fourteen values, so it is worth having for its own sake.

Worth knowing how sharp that is: with our stale `setting` still in place, the same
function returns `02d1f9af-5b6e-5e98-ef7e-6aed579bdd0d`. The uid is a checksum over the
terms, and it caught the New York/Haifa divergence on its own.

Second, the labelled form is a code change on our side that would move us off the kit
vector our uid is currently pinned to, and the collision it prevents cannot arise here:
this is uncounted, nothing is filed to the league inbox by either of us, and it is our
only series against each other. We would rather not fork from the kit's formula for a
friendly.

If you would still prefer the label, we will do it — but then it is a change we make and
re-publish before we play, and we would fold it into the same round as §2 rather than
patching it in on the day.

## 5. Capture semantics — agreed, and a correction to our own earlier note

Agreed on both clauses you agreed, and on your reading of the other two.

**The correction is ours to make.** Our invitation said *"actions resolve simultaneously;
positions are evaluated after both moves are applied"* and *"two agents exchanging cells
does not capture"*. That describes our **native** engine, which is not the wire we will
be playing you on. On the reference wire our session is strictly alternating already —
one commitment per step, our cop applies its move and then claims its own post-move cell,
your thief answers that claim honestly on its next outbound turn. There is no point at
which two moves resolve into one board state.

So: **yes, we confirm strict alternation**, and we confirm the two clauses you set aside
cannot arise. We should have distinguished our two paths in the first letter rather than
sending you our native reading for a reference-wire match.

For completeness, since they sit in the config we both hash: `capture.resolution =
after_moves`, `capture.stay_counts_as_move = false`, `capture.swap_is_capture = false`.
None is in the fourteen signed terms and none can be reached under alternation.

We also concede both wall rules from the state alone, whether or not a claim arrives — a
barrier landing on our thief's own cell, and our thief imprisoned by any mix of walls and
board edges. We got that wrong once and lost a sub-game we should have conceded on the
turn the cage closed; it is now tested from a replayed real position.

## 6. Your ask: `github_commit` from both our processes. Yes, and it is sealed.

Confirmed, and it is already how ours works — our step-0 record seals `github_commit`
inside the commitment for that sub-game's first turn, so you read it out of the
disclosure you audit rather than out of this email. Each of our two processes declares
its own repository's head, so across the six sub-games you will have audited both.

We run two repositories, one per role, two separate processes, nothing shared at runtime
but the wire:

    cop    https://github.com/Diana-Koroblov/bestteam-cop
    thief  https://github.com/Diana-Koroblov/bestteam-thief

**We are deliberately not declaring the heads in this message.** The `setting` and decay
changes above are staged and not yet pushed, and §2 may add one more. A hash we declare
now is a hash you cannot resolve to the code we actually run, which is exactly the
failure your last opponent handed you. You will get both 40-character heads, pushed and
clean, in the message that answers §2 — before either process arms, and we will re-verify
them in-thread if anything lands in between. Our runner refuses to start when the head it
is about to declare is dirty, has no remote, or sits on no remote branch.

## 7. Endpoints, pacing, and the rest

**Our endpoints — two reserved domains, one per role**, so both our processes stay
publicly reachable for the whole series with no rebinding at a sub-game boundary:

    our cop    https://denotatively-sciuroid-florine.ngrok-free.dev/mcp
    our thief  https://itinerary-single-overjoyed.ngrok-free.dev/mcp

Point whichever role you are running at the opposite one. Your single endpoint is not a
problem for us — sub-games are sequential, so only one of your roles is ever live.

**Series shape confirmed**, exactly as you set it out: 6 sub-games, alternating
1-1-1-1-1-1; you THIEF in 1, 3, 5 and COP in 2, 4, 6; us the mirror. This is the flag
that cannot be defaulted safely, so for the avoidance of doubt: **we open as COP.**

**`config_sha256`.** Ours is now `d7b41a527464ca31dc21b124570e4f4dcf9e2cbf65faf826432c17daee1ee494`.
Agreed that it will not equal yours and that this is expected — different kits digest
different term sets. Ours refuses on the flat terms, not on that digest, which is why §3
mattered and this does not.

**Pacing.** Noted, and reciprocated. We pace outbound at 100/min against the 30 s
response window, hold one MCP session for the whole match rather than one per message,
and a sub-game costs us about 70 requests. Our figure for where a free endpoint stops
completing TLS is ~120/min; yours may differ, and the budget is per endpoint, so your
calls spend our minute and ours spend yours. We lost two rehearsals at step 9 to exactly
this, so we are glad you raised it.

**Uncounted, and nothing is mailed to the lecturer** — agreed and reciprocated. Our
reporting is opt-in behind a flag we will not be setting. If you would like the four
artefacts and the closing result anyway, we will send them to **nellkh2007@gmail.com**
and **itay.malich2@gmail.com** only.

**Counted matches played so far: 0.** Honest declaration, same as yours.

**Afterwards**, we would like to verify from the logs together: both scoreboards
mirroring, every audit row passing, and any sealed-thief or barrier-on-cell position
resolving the same way in both replays.

---

One question blocks us — §2 — and everything else in this letter is settled or conceded.
Answer that and name an hour, and we will send you two clean heads and be on the tunnel
five minutes early.

— bestteam
   Itay Malich, Diana Koroblov
   itay.malich2@gmail.com
