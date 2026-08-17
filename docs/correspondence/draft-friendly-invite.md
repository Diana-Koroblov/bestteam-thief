# Draft — friendly match invitation to a new team

Fill in `<TEAM>` and `<DATE>` before sending. Send from **itay.malich2@gmail.com**.

Subject: bestteam ↔ <TEAM> — friendly (uncounted) at 15:00 on <DATE>: our endpoints, our
terms, and the four things we need back from you

Hi <TEAM> —

We are **bestteam** (University of Haifa, Orchestration of AI Agents). We would like to play
you a **friendly — uncounted, M#52** — at **15:00 on <DATE>**. Nothing is mailed to the
lecturer, no league row is filed on either side, and it costs neither of us one of our ten
counted slots. It is the cheapest place for a protocol mismatch to surface, which is the
whole reason we are asking for one before any counted talk.

Everything you need to set up against us is below. We have put our own side in full so you
can diff it against yours before we connect rather than at the handshake.

---

## 1. Who we are

| | |
|---|---|
| Team id | `bestteam` |
| Members | Itay Malich, Diana Koroblov |
| Cop repository | https://github.com/Diana-Koroblov/bestteam-cop |
| Thief repository | https://github.com/Diana-Koroblov/bestteam-thief |
| Counted matches played so far | **0** (M#37, honest declaration) |
| Contact for everything | itay.malich2@gmail.com |

The two roles are two separate repositories and two separate processes. Nothing is shared
between them at runtime except the wire.

**The commits we will declare** are the published heads, not our development tree — you can
fetch and audit both:

    cop    fc01a448101a8a9c748dc9d48468bb633487e042   (bestteam-cop, origin/main)
    thief  57e3cdafad031ed2cf8cfc0df3052b97ce9af837   (bestteam-thief, origin/main)

We will re-confirm both in this thread immediately before the slot if anything lands between
now and then. Our runner now refuses to start when the head it is about to declare is dirty,
has no remote, or sits on no remote branch — a declared hash you cannot resolve is worth
nothing, so we made it mechanical rather than a habit.

## 2. Our endpoints

We hold **two reserved ngrok domains, one per role**, so both of our processes are publicly
reachable for the whole match and we do not have to hand a single domain back and forth at
each sub-game boundary:

    our cop    https://denotatively-sciuroid-florine.ngrok-free.dev/mcp
    our thief  https://itinerary-single-overjoyed.ngrok-free.dev/mcp

Point your peer at whichever of these is the opposite role to the one you are running.
If you hold only one domain and have to reuse it across your two roles, say so — we will
run the sub-games in blocks so your two processes never need to be up at once.

## 3. Which protocol do you speak? (please answer this one first)

This is the single question that has cost us the most match time, so we ask it days ahead
rather than at the slot.

- **Six tools** (`receive_commit` / `receive_reveal` / `final_reveal` / …) → our native
  commit-reveal surface. We connect with no flag.
- **Four mailboxes** (`negotiate` / `receive_turn` / `submit_audit` / …) → the Appendix D
  example repository. We connect with `--protocol reference`.

We speak **both**, in full — the reference path is not a rehearsal-only bridge on our side;
it files the same four artefacts in the league schema and reports exactly as the native path
does. So whichever you built, we adapt. We just need to know which before we arm.

Easiest answer: call `tools/list` on your own endpoint and paste us the names. If you would
rather we found out ourselves, send us your URL and we will run

    uv run python -m core probe https://your-domain/mcp

which needs no config and no agreed terms, and works against a peer who has not finished
setting up.

## 4. Our terms, in full

These are the clauses no Appendix settles. Every one of them is a config flag on our side, so
**agreeing to your reading costs us a config edit and not a code change** — if any of these
differ from yours, tell us and we will almost certainly just take yours.

**Capture resolution.** Actions resolve simultaneously; positions are evaluated after both
moves are applied. A barrier placed on a cell the thief has vacated does not capture. A thief
whose four orthogonal neighbours are all blocked by barriers and/or board edges is captured,
regardless of the availability of STAY. Two agents exchanging cells in the same turn does not
capture.

**Scent.** Each peer transmits its own scent field with every turn message, including that
turn's deposit. Decay is subtractive: at rho = 0.1 a centre cell at 0.900 becomes **0.800**
after one turn. A field revealed at turn k is first acted on when deciding turn k+1 (sampling
mode: `end_of_previous_full_turn`), because turn k's own move was committed before that reveal
could arrive. Each peer seals a digest of its emitted field inside that step's commitment.

> **Please answer this one explicitly with your own worked number.** If your model says
> **0.810** rather than 0.800 we are running different physics, and the end-of-match audit
> reports forgery against two honest teams. We have both readings behind a flag and are happy
> to play either — but not to discover the difference mid-series.

**Barriers.** A placement costs the turn's move, which travels as STAY, and the exact cell is
declared openly in the same turn's reveal. The cell is also sealed inside that step's
commitment as an optional `barrier_cell` key carrying `[row, col]`. The key is present only on
turns that place one, so a turn without a barrier hashes exactly as it would without this
clause.

**Coordinates.** A position is `(row, col)`, origin top-left, indexed from 0. Worked example:
we read `[0,1]` as row 0, column 1 — one cell **East** of the cop's start.

**Walls that capture (M#46 / M#47).** We concede both from the state alone, and we concede
them whether or not a claim arrives: a barrier arriving on our thief's own cell, and a thief
imprisoned by any mix of walls, board edges and the cop's cell. Both are decidable without
knowing where the cop stands, which is what makes them answerable on a wire where neither
peer learns the other's position. We got this wrong once and lost a sub-game we should have
conceded on the turn the cage closed; it is now tested from a replayed real position.

**Everything else is the book's**, unchanged: 7×7, cop starts `(0,0)`, thief `(3,3)`, 35
moves, 14 barriers, `N/S/E/W/STAY`, scoring 20/5/5/10, tie 2, technical loss 0, 30 s response
window, 60 s watchdog, six sub-games.

    scent_model_sha256   71399f21ebc2d0c5f079771f98a8a837001c1e34f25ab8510ce20803da76ea80

The full `game.json`, the `config_sha256` over it, and a `handshake.json` showing exactly what
our peer puts on the wire come as a three-file pack in the next message — **as soon as you
send your team id**. The id goes into `agreed_between` inside the shared contract, which
changes the digest, so sending you a digest before we have your id would only guarantee a
refused handshake. Load the file we send byte-identically; a differing digest refuses the
match rather than starting one that cannot be audited (M#11).

## 5. Four things we need back from you

1. **Your protocol** — six tools or four mailboxes (§3).
2. **Your team id**, exactly as you spell it, so it can go into `agreed_between`.
3. **Your public MCP URL(s)**, and whether you hold one domain or two.
4. **Which role you take in sub-games 1–3.** We propose a **3-3 split** and are happy either
   way. This is the flag that cannot be defaulted safely: both of our processes are told the
   same value and yours is told the opposite, so "3-3" agreed by both of us settles nothing
   about who opens as cop. Say plainly, e.g. *"we open as thief"*, and we will set ours to
   match.

Also useful, and required if we ever make this counted: **your head commit**, pushed, as a
bare 40-character `git rev-parse HEAD`. We will carry the full 40 rather than truncating.

## 6. On the day

- We come up **5 minutes early** and post both our URLs and both declared heads in this
  thread before either process arms.
- Please keep an eye on the **request budget**: a free ngrok endpoint stops completing the
  TLS handshake at roughly **120 requests a minute**, and the failure is a bare
  `ConnectError` with nothing at all in the agent's own log, because the connection never
  becomes a request. It is per endpoint, and your calls to us spend our minute. We pace our
  outbound at 100/min against the 30 s response window; a sub-game costs about 70 requests.
  Two of our own rehearsals died at step 9 this way, so it is worth knowing what it looks
  like before it happens to us jointly.
- Our text layer runs on a local template provider — **zero tokens for the whole series**.
  Movement is never decided by a model on our side (Ch. 6). Yours is private to you and we
  are not asking.
- **Reporting:** a friendly mails the lecturer nothing. If you would like the four artefacts
  and the closing result anyway, we will send them to your inbox and ours only — say the word
  and give us an address. If we later agree to make a match counted, that is a separate
  conversation with both reports going, because a missing or contradictory report is 0 for
  both teams (M#35).
- Afterwards we would like to **verify from the logs together**: both scoreboards must
  mirror, every audit row passes, and any sealed-thief or barrier-on-cell position resolves
  the same way in both replays.

If 15:00 does not work, name any other time — our T is flexible and we would rather move than
rush the terms.

— bestteam
   Itay Malich, Diana Koroblov
   itay.malich2@gmail.com
