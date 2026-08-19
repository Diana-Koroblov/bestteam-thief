# Team bestteam — match terms and requirements

**Group id:** `bestteam` · **Members:** Itay Malich, Diana Koroblov
**Contact:** itay.malich2@gmail.com
**Counted series played:** 2, against two distinct opponents (imreeyal 2026-08-18, vibecode 2026-08-19)
**Last updated:** 2026-08-19

Send this whole document to any team that wants a series with us, and expect us to send it to
them. It is both the opening message and the specification: what we run, what we will not move,
and the exact information we need back.

**Read §1 and §3 first.** §1 is the terms. §3 is the one question that decides whether the rest
of this document even applies to you, because we speak two protocols and they sign *different
byte payloads over the same game*. A team that skips §3 and compares the wrong digest concludes
we have diverged when we have not — that has happened to us in both directions now, and it
costs a letter each time.

Our counted figure is **2**, and §8 explains why we make that number mechanical rather than
remembered.

---

## 1. The terms

Every value below is at or above the Appendix F minimum. Rule 12 permits raising a term and
never lowering one, and we will not sign a lowered minimum even if you ask — agreeing to an
illegal value disqualifies **both** teams, so "the opponent proposed it" is not a defence. Our
own reviewer refuses our own file on the same rule.

| Key | Value | Appendix F status |
|---|---|---|
| board / `grid_size` | `7` | minimum |
| `num_agents` | `2` | fixed |
| `cop_start` | `[0, 0]` | negotiable |
| `thief_start` | `[3, 3]` | negotiable |
| `axis_origin_corner` | `"top-left"` | negotiable |
| `axis_start_index` | `0` | negotiable |
| `map_area` / `setting` | `"New York"` | negotiable |
| `hint_max_words` | `15` | negotiable |
| `move_set` | `N, S, E, W, STAY` | fixed |
| `max_barriers` | `14` | minimum |
| `max_moves` | `35` | minimum |
| `survival_threshold` | `35` | minimum |
| scoring | 20 / 5 / 5 / 10, tie `2`, technical `0` | fixed |
| `pheromone_center_intensity` | `0.9` | fixed |
| `pheromone_decay` | `0.1` | fixed |
| `pheromone_grid_size` | `5` | fixed |
| `pheromone_min_center_intensity` | `0.5` | negotiable |
| `num_games` | `6` | fixed |
| `response_timeout_sec` | `30` | negotiable |
| `watchdog_timeout_sec` | `60` | negotiable |

**`max_moves` and `survival_threshold` are both minimums and we refuse to sign them unequal.**
Appendix F permits raising them independently; the win conditions are only defined when they
match, so a config carrying 35 and 40 is legal by the letter and produces a game with no
defined outcome. Raise them together or not at all.

### Starting cells

`cop_start [0, 0]`, `thief_start [3, 3]` — **not** opposite corners. Row 0 at the top, index
origin 0, so `[0,1]` is one cell **East** of the cop's start. Say your reading of `[0,1]` back
to us if there is any doubt; it is one line and it has caught a real disagreement.

### Series shape

Six sub-games, roles alternating. **The thief opens.**

**A split is not a plan, and this is the one thing we insist on having in writing.**
"Alternating" says how many sub-games each side takes and says nothing about who opens as
which. Two teams that both say "alternating" and each assume they are cop first build
mirror-image plans that meet cop-on-cop — and the failure is genuinely nasty: the sub-games
where the plans happen to coincide settle normally while the rest are refused, so it reads as
an intermittent network fault rather than a disagreement about the fixture. **We voided a whole
window this way on 2026-08-18.** Two of six settled cleanly, four were refused, and nobody
understood why for twenty minutes.

So say it as a sentence — *"alternating, you open as cop on the odd sub-games"* — and we will
set ours to match and read it back to you before either process arms. Our handshake does refuse
a role collision and a sub-game-number mismatch outright rather than deadlocking on them, but
that is a backstop, not a substitute for the sentence.

### The Barrier Law

A barrier goes on the cop's own cell or one orthogonal step from it, never on the cell the
thief occupies. Placing one costs the turn and travels as `STAY`. The cell is declared openly
in the same turn's reveal **and** sealed inside that step's commitment as an optional
`barrier_cell` key carrying `[row, col]`; the key is present only on turns that place one, so a
turn without a barrier hashes exactly as it would if this clause did not exist.

### Capture resolution — settled in writing, because no digest covers it

These four are **not keys in the signed contract** under either shape in §3. They bind because
they are agreed here, in writing, as pairing terms. Matching digests prove the *rulebook*
matches and prove nothing at all about these, so please answer them explicitly rather than
assuming the hash covered them — every one is a config flag on our side, so taking your reading
costs us an edit and not a code change.

- **`capture.resolution` = `after_moves`.** Actions resolve simultaneously; positions are
  evaluated once both moves have been applied. A barrier placed on a cell the thief has
  already vacated does not capture.
- **`capture.swap_is_capture` = `false`.** Two agents exchanging cells in the same turn is
  **not** a capture.
- **`capture.stay_counts_as_move` = `false`.** This is what makes rule 47 reachable at all
  (§5).
- **`pheromones.field_includes_current_turn` = `true`.** The field we transmit includes that
  turn's own deposit.

---

## 2. Our endpoints

| Role | MCP endpoint |
|---|---|
| Cop (police) | `https://itinerary-single-overjoyed.ngrok-free.dev/mcp` |
| Thief | `https://denotatively-sciuroid-florine.ngrok-free.dev/mcp` |

**Two reserved ngrok domains, one per role, on two separate ngrok accounts.** Reserved, not
quick tunnels — they do not rotate on restart, so you never need to ask us for a fresh URL
mid-session. Two distinct hostnames, not two paths on one host: MCP over HTTP needs session
affinity per `mcp-session-id`, and a proxy that does not pin a session to one backend kills
every handshake while a plain HTTPS probe to the same URL answers perfectly.

**Please note the pairing above, because we have published it the other way round.** Two
earlier drafts of ours name `denotatively` as the cop and `itinerary` as the thief. That is
wrong and superseded; the live clones are authoritative and they read as the table above. If
you are working from an older letter of ours, use this one.

**Reading a health check.** A browser or plain `curl` gets `406` or a JSON-RPC error — that is
us **healthy**, an HTTP client talking to an MCP endpoint. `502` means nothing is listening,
`530` means the tunnel is down, and ngrok's `ERR_NGROK_3200` (served as `404`) means the domain
resolves but no agent is connected. Any of those is worth a message. Only an MCP session proves
a door works.

If you would rather not guess, run our probe — it needs no config and no agreed terms and works
against a peer who has not finished setting up:

```bash
uv run python -m core probe https://itinerary-single-overjoyed.ngrok-free.dev/mcp
```

---

## 3. Which protocol — please answer this one first

This is the single question that has cost us the most match time, and it is the reason a digest
of ours may not match a digest of yours even when neither side has done anything wrong.

- **Four mailboxes** (`negotiate` / `receive_turn` / `receive_control` / `submit_audit`) →
  the Appendix D reference implementation. We connect with `--protocol reference`.
- **Six tools** (`receive_commit` / `receive_reveal` / `final_reveal` / …) → our native
  commit–reveal surface. We connect with no flag.

**We speak both, in full.** The reference path is not a rehearsal-only bridge on our side — it
files the same four artefacts in the league schema and reports exactly as the native path does.
Whichever you built, we adapt. We just need to know before we arm.

Easiest answer: call `tools/list` on your own endpoint and paste us the names.

### The two contract shapes, and why the digest depends on your answer

This is the part worth reading twice.

**On the reference protocol** the signed contract is a **flat, fourteen-key** payload. It
carries no team names, so it is opponent-independent and identical for everyone:

```
{"axis_origin_corner":"top-left","axis_start_index":0,"barriers_max":14,"board_size":7,"cop_start":[0,0],"decay_per_step":0.1,"emit_intensity":0.9,"hint_max_words":15,"max_steps":35,"min_center_intensity":0.5,"num_games":6,"setting":"New York","smell_grid_size":5,"thief_start":[3,3]}
```

```
terms sha256 = a284082dfb1572236f1b614d29295a99625539c7d33a096f7f8921bafbc3d08d
```

That digest is derived by our own loader from our own shipped `config/<role>/game.json`, not
copied from anyone. If yours differs, one of us has a term wrong and it is worth finding before
we dial.

**On our native protocol** the signed contract is the **nine-key nested Appendix F shape**, and
it includes `agreed_between`. That makes it opponent-**dependent** by construction:

```
config_sha256 (bestteam ↔ vibecode)  = d16427a258a6cecaebd4b6f85463aa6d2daa22d1c24c06725140ea1a7b153618
config_sha256 (bestteam ↔ <you>)     = computed once you send your group id
```

So on the native path we cannot send you a digest before you send us your id, and any digest we
sent beforehand would only guarantee a refused handshake.

**The failure this prevents.** We spent two letters with imreeyal chasing a mismatch —
`17606f14` against `cca1243e` — over content that differed in **no rule at all**. The cause was
contract *shape*: our file carried six keys theirs never did, and our own reviewer would have
refused their nine-key file at the handshake. Neither side was wrong about the game. So before
comparing a digest with us, name the protocol you are comparing under. A digest is only
meaningful against a stated shape.

**Canonicalisation, in both cases:** `json.dumps(payload, sort_keys=True, separators=(",",
":"), ensure_ascii=False)`, UTF-8, **no trailing newline**. This is not a hash of the file's
raw bytes. Two teams holding byte-identical *content* still differ on a raw sha over key order,
indentation and a trailing newline — and on Windows-versus-Linux CRLF, which will bite you
silently. If your number differs, check the construction before hunting for a content
difference. We did it the other way round and it cost us the two letters above.

---

## 4. Scent — we carry both models, and we transmit every turn

Rule 23 requires the emission and decay model to be exchanged and locked before a series. It
does not require it to be *ours*, so we carry both behind a config flag rather than argue about
it. Agreeing to your reading costs us a config edit, not a code change.

| | **subtractive** (the simulator) | **multiplicative** (PAGE 43-44) |
|---|---|---|
| decay | absolute, `τ ← τ − ρ` | relative, `τ ← (1−ρ)·τ` |
| our `pheromones.decay_model` | `subtractive` | `multiplicative` |
| our declared digest | `81ebee59640e80eae8ca9ee5f86abd26e7edf5cdbb27d15925cb6ee45ca6ddf4` | `934c220d5bf62acaa3297c6c9d723ea954c220260b02292ca17f6d5daef9f4d9` |

**We declare `subtractive` by default**, digest `81ebee59…`, rings `0.90 / 0.60 / 0.30` from
`round(0.9 · max(0, 1 − chebyshev/3), 2)`.

**Settle it on the worked number, not on the digest.** Two correct implementations of the same
physics hash differently, because the fingerprint payload is not itself standardised. The field
is unambiguous where the hash is not, so here is our one-line test — please answer it with your
own number:

> At `ρ = 0.1`, a centre cell at `0.900` becomes **`0.800`** after one turn under subtractive
> decay, and **`0.810`** under multiplicative. **Which number does your code print?**

If you say `0.810` and we say `0.800` we are running different physics, and the end-of-match
audit reports forgery against two honest teams. We are happy to play either. We are not happy
to discover the difference at sub-game 4.

**Sampling.** A field revealed at turn *k* is first acted on when deciding turn *k+1*
(`sampling_mode: end_of_previous_full_turn`), because turn *k*'s own move was committed before
that reveal could arrive. Each peer seals a digest of its emitted field inside that step's
commitment, so neither of us can tailor a grid after seeing the other's.

**Both sides transmit scent every turn.** We do, and we ask the same of you: a populated grid,
the agreed model's field around your true current cell, peak `0.9` — not an empty map, not an
omitted key, not a field centred anywhere but where you actually are. A series where one side
broadcasts and the other does not is one team playing with perfect information against a
blindfolded opponent, and the board result says nothing about either strategy.

If your build cannot transmit, tell us **before** we agree terms and we will either play it as
a declared asymmetry with that fact in both reports, or decline — your choice, made in writing,
in advance. What we cannot do is find out at the audit.

Hints are separate and stay free: send them, withhold them, or lie in them, as rules 26–27
permit. A hint over 15 words is a term breach rather than a clever play.

---

## 5. Commit–reveal, and how an audit passes

Every turn carries a commitment; nonces are released at the end of the mini-game and each step
is re-hashed.

```
commit = sha256( canonical_json(payload) + "|" + nonce )
nonce  = 16 random bytes, hex (32 characters), never reused across steps or games
```

The `|` is a literal character in the hashed text. The payload is canonical JSON — sorted keys,
**compact** separators — the same recipe as the config digest in §3 and deliberately **not**
the same as the report signature in §7, which is spaced.

**The offline vector.** Payload:

```
{"hint":"","intent":"probe east","move":"MOVE:E","position":[3,4],
 "role":"thief","state":"ok","step":1,"sub_game":1}
```

with nonce `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa` (32 `a`s) gives:

```
4047830b8108320cbf48c1c1e1f09c6c0d47da51c225ce2cf40c7857cefc3030
```

Our implementation reproduces that. Run it on yours and paste the digest you get — "the
reference implementation" is not an answer either of us can check, and this is the one setting
that fails every audit while the board agrees perfectly.

### Rules 46 and 47 — we concede from the state, without being asked

A barrier arriving on our thief's own cell (rule 46), and a thief sealed in by any mix of
walls, board edges and the cop's cell (rule 47), are both captures. **We concede both from the
state alone, and we concede them whether or not a claim arrives.** Both are decidable without
knowing where the cop stands, which is exactly what makes them answerable on a wire where
neither peer learns the other's position.

We got this wrong once and played on from a position we had already lost. It is now decided in
`core/domain/rules.py` and tested from a replayed real position, on both protocols.

**Please confirm you do the same.** If your build has no concept of losing by being walled in,
say so plainly and we will treat every seal as a survival and score it that way — no argument
at the audit, no voided games. A cop that concludes an immobilisation the thief never
acknowledges files a result its opponent contradicts, and rules 33–35 void that mini-game for
*both* teams at zero each — strictly worse for the winner than the survival they declined.

One detail worth stating because it is a real fork: rule 47 is decided by whether a legal
**move** exists, not counting `STAY`. If `STAY` counts as an available move, rule 47 becomes
unreachable and the mechanic does not exist at all. Ours is `stay_counts_as_move: false`.

### The audit is pushed both ways

At the end of every mini-game we call **your** `submit_audit` with our reveal, and we
independently expect **you** to call **ours**. Two outbound calls, one from each side; neither
is a reply to the other. A peer whose implementation only *answers* an incoming audit rather
than initiating its own sees nothing wrong at all while we record a skip — and rule 18 keeps
the nonces sealed once the moment has passed, so it cannot be repaired afterwards.

The envelope is exactly three fields: `{"sender": …, "records": […], "result_claim": …}`. A
missing field and an extra field both raise in the peer's process. `result_claim` is how you
believe the game ended; stating it there is what lets a disagreement surface at audit time
instead of in two contradictory reports.

---

## 6. Identifiers both sides compute independently

Neither of us sends these; we each derive them and they must agree.

```
pair     = sorted([your_group_id, "bestteam"])
game_id  = f"{pair[0]}-vs-{pair[1]}"
seed     = canonical_json(the flat 14 terms) + "|" + "|".join(pair)
game_uid = UUID from the first 16 bytes of sha256(seed)
```

Alphabetical, not "whoever spoke first". Derived from the **flat** terms only, never from the
whole `game.json`, and `game_uid` never crosses the wire in either direction — a derived id
that is also transmitted is an id two peers can silently disagree about.

---

## 7. The report

Rules 33–35 void a series **for both teams** when the two reports contradict each other, so
this section is where a won series gets thrown away.

**`roles` is keyed by group id**, not by role name:

```json
"roles": {"bestteam": "police", "your-group-id": "thief"}
```

Keying by group is what makes the mapping identical on both machines regardless of which side
builds it, and it matches the lecturer's golden artifact. Keyed by role name it silently
changes the signature below while every visible outcome still agrees.

**`mutual_agreement.sha256`** is signed over exactly three keys — `game_id`, `aggregate`,
`sub_games` — and nothing else. Not `game_uid`, not `groups`, not timestamps, not token spend,
not file paths, not `steps`. Serialisation is **sorted keys, `ensure_ascii=False`, and the
interpreter's default separators `", "` and `": "`** — the **spaced** form, not the compact one
used everywhere else in this project. The signature is computed **before** the field is
inserted into the document, so it is excluded from its own preimage.

Each row carries `sub_game_number`, `roles`, `result`, `winner_group` and `score`, with `roles`
and `score` keyed by group id and rows sorted by number. The aggregate derives from those same
rows, and a series tie adds `tie_score` to both totals **inside** the signed aggregate.

**Per-repo commit hashes.** We run two processes out of two repositories, so `github_commit`
differs per sub-game: our cop repo's HEAD on the sub-games we play cop, our thief repo's on the
others. A single commit stamped across all six rows is wrong in half of them, and rule 53 is
precisely the rule that asks which code played a given game. We shipped that bug ourselves and
fixed it on 2026-08-18.

**No `league` block.** We used to add one to uncounted files as the record of why the file does
not count. It is retired: what marks a series friendly is the recipient channel, never a field,
and a key of our own invention costs a diff against every other team's artefact in the one file
both sides byte-compare.

**Where reports go.** Counted series to `rmisegal+uoh26finalgame@gmail.com`, from each team
separately. Friendlies to the two teams only — never to the lecturer.

---

## 8. What we need from you

Copy this block, fill it in, send it back in one message.

```
group_id            (exactly as your handshake declares it — case sensitive)
group_name
members
agent email

protocol            four mailboxes (reference) / six tools (native)   <- §3, answer first
cop endpoint        https://.../mcp
thief endpoint      https://.../mcp
endpoint stability  reserved/permanent, or rotates on restart?

cop repo            https://github.com/...
cop commit          (full 40 hex, the commit you will play from)
thief repo          https://github.com/...
thief commit        (full 40 hex)

terms hash          under the shape you named above — say which
scent model         subtractive or multiplicative, and YOUR number for
                    0.900 after one decay step at rho 0.1  (§4)
commit-reveal       run the §5 vector and paste the digest you get
roles keying        confirm keyed by group id (§7)
rules 46 / 47       confirm you concede a wall-on-cell and a seal-in, and
                    whether STAY counts as a legal move for rule 47
capture resolution  simultaneous or sequential, and does a cell-swap capture?
two processes       yes / no, and one hostname per process or two paths on one
role plan           as a SENTENCE, e.g. "alternating, you open as cop on odds"
watchdog / retries  your per-turn deadline and retry policy, in seconds
step convention     does step 1 mean before or after the first move?
counted so far      how many COUNTED series, and against whom
schedule            when you want the warm-up, and when the counted series
```

### Ours, in the same shape

```
group_id            bestteam
group_name          bestteam
members             Itay Malich, Diana Koroblov
agent email         itay.malich2@gmail.com

protocol            both — reference (four mailboxes) and native (six tools)
cop endpoint        https://itinerary-single-overjoyed.ngrok-free.dev/mcp
thief endpoint      https://denotatively-sciuroid-florine.ngrok-free.dev/mcp
endpoint stability  two reserved ngrok domains on two separate accounts;
                    permanent, one hostname per process, never rotate

cop repo            https://github.com/Diana-Koroblov/bestteam-cop
cop commit          da8b5cc41daccb24bdc2aad31105553cca72c7cd      (branch itay)
thief repo          https://github.com/Diana-Koroblov/bestteam-thief
thief commit        fa9147d31cd1103569ae62485874c3a213ef24e1      (branch itay)

terms hash          a284082dfb1572236f1b614d29295a99625539c7d33a096f7f8921bafbc3d08d
                    (reference/flat 14-key shape — the native digest needs your id, §3)
scent model         subtractive, 81ebee59640e80eae8ca9ee5f86abd26e7edf5cdbb27d15925cb6ee45ca6ddf4
                    0.900 -> 0.800 after one step at rho 0.1
                    multiplicative also available: 934c220d..., 0.900 -> 0.810
commit-reveal       4047830b8108320cbf48c1c1e1f09c6c0d47da51c225ce2cf40c7857cefc3030
roles keying        keyed by group id
rules 46 / 47       both conceded from state, without waiting for a claim;
                    stay_counts_as_move = false
capture resolution  simultaneous (after_moves); a cell-swap does NOT capture
two processes       yes — two repositories, two processes, two hostnames, always
role plan           alternating; we are happy to open as either, say which
watchdog / retries  30 s response window, 60 s watchdog, 5 s backoff, 3 retries;
                    we wait several minutes for a peer inside its own mini-game
step convention     step 1 is the state AFTER the first move
counted so far      2 — imreeyal 2026-08-18 (40-60), vibecode 2026-08-19 (30-90)
```

**On that last figure.** Rule 38 judges a counted count on whether the two teams' files agree
about it, so we do not carry ours in a person's head. It is parsed out of `docs/LEAGUE_LOG.md`
by `core/shared/league_log.py`, which counts the rows whose opponent cell is filled and
**refuses to hand the handshake a number** when the table and the stated total disagree. If our
declared count is ever wrong, the cause is a row we failed to file, not a number we chose.

**Commit hashes.** We declare the published heads, never our development tree — a hash nobody
can resolve is worth nothing. Our runner refuses to start when the head it is about to declare
is dirty, has no remote, or sits on no remote branch. We re-send the pair after any push before
we play, and we ask the same of you: step 0 reads `git rev-parse HEAD`, so a commit you make
after messaging us silently invalidates what you sent.

### The green light

When you can send these, we are ready to dial without further discussion:

```
protocol named, and the digest compared under that shape (§3)   confirmed
terms hash matches under the named shape                        confirmed
commit-reveal vector gives 4047830b...                          confirmed
scent model named, and your 0.900-after-one-step number given   confirmed
you transmit a populated smell_grid EVERY turn (§4)             confirmed
roles keyed by group id in the report (§7)                      confirmed
two processes, one hostname each, both live now                 confirmed  <urls>
both repos public, both commits pushed and resolving            confirmed  <hashes>
role plan as a sentence, not just a split (§1)                  confirmed
rules 46 and 47 conceded from state (§5)                        confirmed
a FRESH negotiate opens every mini-game (§9)                    confirmed
submit_audit pushed BOTH ways at each game end (§5)             confirmed
both processes stay up for all six windows, idle or not (§9)    confirmed
```

---

## 9. How a series runs on the wire

Per **mini-game**, not per series:

```
negotiate      the agreed terms, sent FRESH for every mini-game
               -> handshake locked
receive_turn   alternating, until a capture or step 35
               -> the game ends
submit_audit   pushed BOTH ways
               -> then the next mini-game begins with a NEW negotiate,
                  at the other role
```

**We re-negotiate before every mini-game.** Roles alternate, so each window opens with a fresh
`negotiate` and the session re-binds. If your side holds one session for the whole series and
waits for a `receive_turn` after a game ends, our next `negotiate` is not what you are waiting
for and the series stalls at the handover.

**Both your processes must stay up for the entire series**, not just their own windows. Your
cop plays three of six and your thief the other three, so each sits idle for half the match —
but an idle process still has to answer, because the next window arrives at it. A process that
exits after its own mini-game kills the series at the next handover, and from our side that is
indistinguishable from you going offline.

**Retarget per window.** Our cop dials your thief and our thief dials your cop, and which one
we are talking to changes at every mini-game boundary. A client built once at start-up and
never re-pointed sends half the series to the wrong door.

**Two processes is a requirement, not our topology preference.** Appendix ה Table 7 rule 1
requires the cop's code and the thief's code to run in two completely separate processes;
§2.4.2 disqualifies a solution even when the game works technically, and the sanction is
`כישלון מוחלט`. We run two processes out of two repositories against every opponent, and we
will not run unsplit to accommodate a peer that cannot retarget.

---

## 10. Before we play — real defects, ours included

None of these is hypothetical and none is a criticism. Every one cost somebody a mini-game.

1. **`roles` keyed by role name instead of group id.** Breaks the report signature while every
   outcome still agrees, so it reads as a contradiction when it is a keying difference.
2. **A digest compared under the wrong contract shape** (§3). Ours against imreeyal's:
   `17606f14` vs `cca1243e`, over content that differed in no rule. Two letters.
3. **A role split agreed as a shape and not as a sentence** (§1). Cost us four refused sub-games
   out of six on 2026-08-18, looking exactly like an intermittent network fault.
4. **One commit stamped on all six sub-games** while running two processes (§7). Ours. Fixed
   2026-08-18.
5. **A config artefact filed with `role_split` and the scent digest empty.** Ours — and the field
   that would have explained a voided window was the blank one. Fixed 2026-08-18, after an
   opponent had to write and ask us what changed between two windows and the honest answer was
   that our own file could not tell them.
6. **A series that stops early.** Survival is judged at 35 and 35 means 35. A loop that stops at
   25 and files the result as complete disagrees with our log for every remaining step.
7. **`tamper_forfeit` with `tampered: false`.** A report awarding a forfeit for tampering while
   its own audit block says nothing was tampered with is self-contradictory, and rule 35 voids
   both teams' reports on a contradiction.
8. **Token counts read from step 0 only.** If your per-step records carry them, say so. We found
   our own reader taking peer tokens from step 0 and filing zeros for a peer who had published
   them all along.
9. **Two doors on one hostname differing only by path.** MCP over HTTP needs session affinity; a
   proxy that does not pin a session to one backend dies with `Session terminated` while a plain
   HTTPS probe to the same URL answers perfectly.
10. **`negotiate` with no top-level sender identity.** Put `sender` and `group_id` at the top
   level, not only inside a nested identity block, or the session cannot be bound.
11. **A retry loop with no backoff.** Bounded exponential backoff with a ceiling. Ours is 5 s and
   3 retries.
12. **A declared commit that does not resolve.** A private or unpushed repo returns `404` and the
   hash points at nothing anyone can inspect: survivable in a friendly, not under rules 49 and 53.

### The ngrok request ceiling — worth knowing before it happens to us jointly

A free ngrok endpoint stops completing the TLS handshake at roughly **120 requests a minute**,
and the failure is a bare `ConnectError` with **nothing at all in the agent's own log**,
because the connection never becomes a request. It is per endpoint, and your calls to us spend
our minute as well as yours. We pace our outbound at 100/min against the 30 s response window;
a sub-game costs about 70 requests. Two of our own rehearsals died at step 9 this way before we
understood it.

### Two more, briefly

**Your busy-peer timeout has to tolerate a whole mini-game.** A peer inside its own game cannot
answer yours for minutes at a stretch. Ours waits several minutes before calling a peer absent.
Forty seconds of patience has scored a technical outcome against a completely healthy opponent
in this league.

**Our text layer costs zero tokens.** It runs on a local template provider, so the whole series
spends nothing against the 200k budget. Movement is never decided by a model on our side (Ch.
6). Yours is private to you and we are not asking.

---

## 11. How a series with us runs

1. **Protocol and terms.** You answer §3, then confirm §1 by digest under that shape.
2. **Warm-up, uncounted.** One or two, as many as you like. Reports to the two of us only,
   nothing to the lecturer, and it costs neither of us one of our ten counted slots. It is the
   cheapest place for a protocol mismatch to surface, which is the whole reason we ask for one.
3. **Counted.** One series, both teams email the lecturer separately. We compare
   `mutual_agreement.sha256` before either of us sends, and if it differs we find out why first —
   a contradiction costs us both more than a loss does.
4. **Afterwards, verify from the logs together.** Both scoreboards must mirror, every audit row
   must pass, and any sealed-thief or barrier-on-cell position must resolve the same way in both
   replays.

We do not accept a technical win we did not earn on the board. If our endpoint is down, our
tunnel dropped or our process crashed, tell us and we will replay the sub-game. We ask the same
of you, and we have handed an opponent our own diagnostic findings when the fault was theirs
and again when it was ours.

## 12. What we will not do

- Sign a lowered Appendix F minimum, or an unequal `max_moves` / `survival_threshold`.
- Compare a digest without both sides naming the contract shape it is computed over.
- Play a series where the role plan exists only as a split and not as a sentence.
- Run one process instead of two, whatever your topology.
- Declare a commit from our development tree, or one that does not resolve on a public remote.
- Edit a log, a config or an artefact once a series has started.
- Claim a technical result where the board result is recoverable.

— bestteam
  Itay Malich, Diana Koroblov
  itay.malich2@gmail.com
