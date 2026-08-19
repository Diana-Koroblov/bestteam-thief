# Opening message — to any team we have not played

<!--
NOT PART OF THE MESSAGE. Stripped from the .txt; these are notes to us.

  1. Fill in <TEAM> everywhere before sending. Send from itay.malich2@gmail.com.
  2. Attach match-terms-bestteam.txt — the same content in full detail. This message
     is the part a team can act on without opening anything.
  3. Re-run `git rev-parse HEAD` in BOTH published clones and correct the two commit
     lines in §1 if they have moved. Step 0 reads the head at match time, so a commit
     made after this message goes out silently invalidates what it declares.
  4. Regenerate the .txt after any edit:
     uv run python <scratchpad>/md2txt.py docs/correspondence/opening-message-any-team.md
-->

Subject: bestteam ↔ <TEAM> — a friendly first: our endpoints, our terms, both digests, and
the four things we need back from you

Hi <TEAM> —

We are **bestteam** (University of Haifa, Orchestration of AI Agents), and we would like to
play you — **a friendly first, then a counted series if it goes cleanly**.

A friendly is uncounted: nothing is mailed to the lecturer, no league row is filed on either
side, and it costs neither of us one of our ten counted slots. It is the cheapest possible
place for a protocol mismatch to surface, and every mismatch we have hit in this league would
have been caught in one.

Everything you need to set up against us is below, so you can diff it against your build
before we connect rather than at the handshake. Our whole side is stated; nothing is held
back for the day.

---

## 1. Who we are

| | |
|---|---|
| Group id | `bestteam` (case sensitive, exactly as our handshake declares it) |
| Members | Itay Malich, Diana Koroblov |
| Contact for everything | itay.malich2@gmail.com |
| Counted series played | **2** — see below |

Two roles, two repositories, two processes, always. Nothing is shared between them at runtime
except the wire.

    cop repo     https://github.com/Diana-Koroblov/bestteam-cop
    cop commit   da8b5cc41daccb24bdc2aad31105553cca72c7cd   (branch itay)

    thief repo   https://github.com/Diana-Koroblov/bestteam-thief
    thief commit fa9147d31cd1103569ae62485874c3a213ef24e1   (branch itay)

Both public, both resolving, both clones clean against `origin/itay`. **We declare published
heads, never our development tree** — our runner refuses to start when the head it is about
to declare is dirty, has no remote, or sits on no remote branch, because a hash you cannot
fetch is worth nothing to you. If we push before we play, we re-send the pair in the thread
and ask the same of you.

### Our counted record, declared up front

**We have played two counted series, both six sub-games of six, both lost:**

    imreeyal   2026-08-18   40 - 60
    vibecode   2026-08-19   30 - 90

Roles alternated in both, with us as cop on the odd sub-games. Every audit settled, every
report went to the lecturer, and both opponents' files agree with ours.

So unless you are one of those two, **this would be our third counted series and our third
distinct opponent** — a first meeting between our two groups, which is what sets the
first-meeting flag and the diversity reward on both sides.

We will also say the obvious thing about those two scorelines rather than let you discover it:
we have not won a counted series yet. You are not walking into a trap. What we can promise is
that the protocol side is thoroughly exercised — both series settled 6/6 with every commitment
re-hashed and no dispute about a single sub-game.

We state it plainly because rule 38 judges the figure on whether our two files agree about
it, and a wrong declaration disqualifies the project rather than costing a point. Ours is not
carried in anyone's head: it is parsed out of `docs/LEAGUE_LOG.md` by code that counts the
filled rows and **refuses to hand the handshake a number at all** when the table and the
stated total disagree. If it is ever wrong, the cause is a row we failed to file, not a
figure somebody typed — and we would rather you checked it against your own record than took
our word for it.

Please send us yours in the same form: **how many counted series, and against whom.**

## 2. Our endpoints

    our cop     https://itinerary-single-overjoyed.ngrok-free.dev/mcp
    our thief   https://denotatively-sciuroid-florine.ngrok-free.dev/mcp

**Two reserved ngrok domains, one per role, on two separate ngrok accounts.** Reserved, not
quick tunnels: they do not rotate on restart, so we will never have to hand you a fresh URL
mid-session. Two distinct hostnames rather than two paths on one host, deliberately — MCP
over HTTP needs session affinity per `mcp-session-id`, and a proxy that does not pin a
session to one backend kills every handshake while a plain HTTPS probe to the same URL
answers perfectly.

Point your peer at whichever of ours is the opposite role to the one you are running, and
expect to re-point at every sub-game boundary: our cop dials your thief and our thief dials
your cop.

**A `406` or a JSON-RPC error from `curl` means we are healthy** — that is an HTTP client
talking to an MCP endpoint. `502` means nothing is listening, `530` means the tunnel is down,
`ERR_NGROK_3200` means the domain resolves but no agent is connected. Any of those is worth a
message. If you would rather not guess, this needs no config and no agreed terms and works
against a peer that has not finished setting up:

    uv run python -m core probe https://itinerary-single-overjoyed.ngrok-free.dev/mcp

## 3. Which protocol do you speak? — please answer this one first

This is the single question that has cost us the most match time, and it decides which digest
we should even be comparing.

- **Four mailboxes** (`negotiate` / `receive_turn` / `receive_control` / `submit_audit`) →
  the Appendix D reference implementation. We connect with `--protocol reference`.
- **Six tools** (`receive_commit` / `receive_reveal` / `final_reveal` / …) → our native
  commit–reveal surface. We connect with no flag.

**We speak both, in full.** The reference path is not a rehearsal-only bridge on our side; it
files the same four artefacts in the league schema and reports exactly as the native path
does. Whichever you built, we adapt.

Easiest answer: call `tools/list` on your own endpoint and paste us the names.

**Why it matters for the digest.** The two protocols sign different payloads over the same
game. The reference path signs a flat fourteen-key contract carrying no team names, so it is
the same for everyone:

    terms sha256 = a284082dfb1572236f1b614d29295a99625539c7d33a096f7f8921bafbc3d08d

Our native path signs the nine-key nested Appendix F shape instead, which includes
`agreed_between` and is therefore **opponent-dependent** — so on that path we cannot quote
you a digest until you send us your group id, and one sent beforehand would only guarantee a
refused handshake.

Both are legitimate and they are not comparable. We spent two letters with a previous
opponent chasing a mismatch — `17606f14` against `cca1243e` — over content that differed in
**no rule at all**; the cause was contract shape, not a term. So please name the shape you
are comparing under, and we will do the same.

Canonicalisation either way: `json.dumps(payload, sort_keys=True, separators=(",", ":"),
ensure_ascii=False)`, UTF-8, **no trailing newline**. Not a hash of the file's raw bytes —
two teams holding byte-identical content still differ on a raw sha over key order,
indentation, a trailing newline, or Windows-versus-Linux CRLF.

## 4. The terms

7×7, cop starts `(0,0)`, thief starts `(3,3)` — **not** opposite corners, row 0 at the top,
index origin 0. 35 moves, survival judged at 35, 14 barriers, `N/S/E/W/STAY`, six sub-games,
scoring 20/5/5/10, tie 2, technical 0, hints capped at 15 words, setting "New York", 30 s
response window, 60 s watchdog.

Every value is at or above the Appendix F minimum. Rule 12 permits raising a term and never
lowering one, and we will not sign a lowered minimum even if you ask — agreeing to an illegal
value disqualifies **both** teams. We also refuse to sign `max_moves` and
`survival_threshold` unequal: both are minimums and may legally be raised independently, but
the win conditions are only defined when they match.

### The clauses no digest covers — please answer these explicitly

These bind only because they are agreed in writing. Matching digests prove the *rulebook*
matches and prove nothing about any of them. **Every one is a config value on our side, so
taking your reading costs us an edit and not a code change** — if yours differ, say so and we
will almost certainly just take yours.

- **Scent.** We transmit a populated field every turn, centred on our true current cell, peak
  `0.9`, including that turn's own deposit, with a digest of it sealed inside that step's
  commitment so neither side can tailor a grid after seeing the other's. We ask the same of
  you — a series where one side broadcasts and the other does not is one team playing with
  perfect information against a blindfolded opponent.
- **Decay.** We declare **subtractive**, `τ ← τ − ρ`, so a centre at `0.900` reads **`0.800`**
  after one turn at `ρ = 0.1`, in flat Chebyshev rings of `0.90 / 0.60 / 0.30`. Digest
  `81ebee59640e80eae8ca9ee5f86abd26e7edf5cdbb27d15925cb6ee45ca6ddf4`.
  We also implement the **book** model, `τ ← (1−ρ)·τ`, giving `0.810` and the radial figure
  printed on PAGE 44. Tell us which you run and we will match it.
- **Capture** resolves after both moves are applied (simultaneous). A barrier placed on a
  cell the thief has already vacated does not capture. **A cell swap is not a capture.**
- **Rules 46 and 47.** A barrier on our thief's own cell, and a thief sealed in by any mix of
  walls, board edges and the cop's cell, are both captures, and **we concede both from the
  state alone, without waiting for a claim.** Rule 47 is decided on whether a legal *move*
  exists, not counting `STAY` — if `STAY` counted, the rule would be unreachable. If your
  build has no concept of losing by being walled in, say so and we will score every seal as a
  survival instead, with no argument at the audit.
- **Barriers.** A placement costs the turn and travels as `STAY`. The cell is declared openly
  in that turn's reveal and also sealed in the commitment as an optional `barrier_cell` key,
  present only on turns that place one — so a turn without a barrier hashes exactly as it
  would without the clause.

> **Please answer the decay one with your own worked number.** If your model prints `0.810`
> and ours prints `0.800` we are running different physics, and the end-of-match audit
> reports forgery against two honest teams. We are happy to play either. We are not happy to
> discover the difference at sub-game 4.

### Commit–reveal

`sha256( canonical_json(payload) + "|" + nonce )`, the `|` a literal character, nonce 16
random bytes as 32 hex characters, never reused across steps or games. Test vector — payload
`{"hint":"","intent":"probe east","move":"MOVE:E","position":[3,4],"role":"thief",`
`"state":"ok","step":1,"sub_game":1}` with nonce `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa` gives:

    4047830b8108320cbf48c1c1e1f09c6c0d47da51c225ce2cf40c7857cefc3030

Run it and paste what you get. It takes a minute and it is the one setting that fails every
audit while the board agrees perfectly.

### The report

`roles` keyed by **group id**, not by role name — `{"bestteam": "police", "<TEAM>": "thief"}`.
`mutual_agreement.sha256` signed over exactly `game_id`, `aggregate` and `sub_games`, in the
**spaced** form (`json.dumps` defaults, not the compact form used everywhere else), computed
before the field is inserted into its own document. Because we run two processes,
`github_commit` differs per sub-game — our cop repo's head on the ones we play cop, our
thief repo's on the others.

Rules 33–35 void a series **for both teams** when the two reports contradict each other, so
we would like to compare signatures before either of us sends anything.

## 5. Four things we need back

1. **Your protocol** — six tools or four mailboxes (§3).
2. **Your group id**, exactly as you spell it.
3. **Both your MCP endpoints**, one per role, and whether each is permanent or rotates on
   restart. If they rotate, re-send immediately before we dial.
4. **The role plan as a sentence** — and this is the one we will insist on getting in
   writing.

   A split says how many sub-games each side takes and never who opens as which. Two teams
   agreeing "alternating" and each assuming they are cop first build mirror-image plans that
   meet cop-on-cop, and the failure is ugly: the sub-games where the plans happen to coincide
   settle normally while the rest are refused, so it reads as an intermittent network fault
   rather than a disagreement about the fixture. **We voided a whole window this way on
   2026-08-18** — two of six settled cleanly, four were refused, and nobody understood why
   for twenty minutes.

   So say it like this: *"alternating, you open as cop on the odd sub-games"*. We will set
   ours to match and read it back to you before either process arms.

Also useful, and required if we make it counted: **both your head commits**, pushed, as bare
40-character hashes, plus your per-turn deadline, your retry policy, and whether your step 1
means before or after the first move (ours means after).

## 6. On the day

- We come up **five minutes early** and post both URLs and both declared heads in the thread
  before either process arms. Please bring your tunnels up before we dial, not after — a door
  that is not yet connected looks identical to one that is broken.
- **Both processes must stay up for the whole series**, not just their own windows. Each of
  ours sits idle for half the match but still has to answer, because the next window arrives
  at it. A process that exits after its own mini-game kills the series at the next handover,
  and from the other side that is indistinguishable from going offline.
- **We re-negotiate before every mini-game.** Roles alternate, so each window opens with a
  fresh `negotiate` carrying the identical terms. If your side holds one session for the
  whole series and waits for a `receive_turn` after a game ends, our next `negotiate` is not
  what you are waiting for and the series stalls at the handover.
- **The audit is pushed both ways.** At each game end we call your `submit_audit` with our
  reveal and independently expect you to call ours. Neither is a reply to the other, and a
  build that only answers an incoming audit sees nothing wrong while its peer records a skip.
- **Watch the request budget.** A free ngrok endpoint stops completing the TLS handshake at
  roughly **120 requests a minute**, and the failure is a bare `ConnectError` with nothing at
  all in the agent's own log, because the connection never becomes a request. It is per
  endpoint, and your calls to us spend our minute. We pace our outbound at 100/min; a
  sub-game costs about 70 requests. Two of our own rehearsals died at step 9 this way.
- **Give a busy peer time.** A peer inside its own mini-game cannot answer yours for minutes
  at a stretch. We wait up to 15 minutes before calling a peer absent; 40 seconds of patience
  has scored a technical outcome against a completely healthy opponent in this league.
- **Our text layer costs zero tokens** — a local template provider, so the whole series spends
  nothing against the 200k budget. Movement is never decided by a model on our side (Ch. 6).
  Yours is private to you and we are not asking.
- **Afterwards we would like to verify from the logs together**: both scoreboards must
  mirror, every audit row must pass, and any sealed-thief or barrier-on-cell position must
  resolve the same way in both replays.

We do not accept a technical win we did not earn on the board. If our endpoint is down, our
tunnel dropped or our process crashed, tell us and we will replay the sub-game. We ask the
same of you, and we have handed opponents our own diagnostic findings when the fault was
theirs and again when it was ours.

## 7. Timing

**Our calendar is open — name any hour and we will take it.** Today, tomorrow, late evening,
whatever fits around your side. If the friendly goes cleanly we are happy to run the counted
series straight afterwards, or on a separate day if you would rather; entirely your call.

A friendly mails the lecturer nothing. If you would like the four artefacts and the closing
result anyway, we will send them to your inbox and ours only — say the word and give us an
address. A counted series is a separate agreement, with both reports going to
`rmisegal+uoh26finalgame@gmail.com` from each team separately, because a missing or
contradictory report scores 0 for both of us.

Attached is our full terms-and-requirements document. Nothing in it contradicts anything
above; it exists so that the detail is answerable from a file rather than from a thread.

— bestteam
  Itay Malich, Diana Koroblov
  itay.malich2@gmail.com
