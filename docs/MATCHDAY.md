# Match Day — playing another group

Everything here has been run end to end. The scoreboard, the four artefacts and
the `Verified OK` replay in this document come from a real two-process match over
HTTP, not from the test suite.

---

## Before you connect

**1. Agree the terms in writing.** Send the opponent a pack and read theirs:

```powershell
uv run python -m core negotiate --role cop --pack outbox\
uv run python -m core negotiate --role cop --review their-game.json
```

`--review` exits non-zero on an Appendix F breach. Agreeing to one disqualifies
**both** teams (M#12), and "they proposed it" is not a defence.

**2. Settle the four things no Appendix decides.** These are the ones that void a
match when discovered mid-play, and a voided match scores 0 for both sides (M#35):

| Term | Ours | Why it must be written down |
|---|---|---|
| Role split | `3-3` | In no Appendix (N17, C-011). See `--first` below. |
| Scent decay | 0.9 → **0.81** after one turn | Multiplicative, not subtractive. 0.80 means different physics and the audit reports forgery against two honest teams (C-007). |
| Capture resolution | `after_moves`, STAY is not a move, swap **is** capture | Three separate readings (C-006). All three are config flags on our side. |
| Scent sampling | `end_of_previous_full_turn` | C-005. |
| Coordinates | `[0,1]` is one cell **East** of `[0,0]` | C-010, N18. |

**3. Decide `--first` with them.** This is the one flag that cannot be defaulted
safely. It names **the role our team holds in sub-games 1–3**. Both of our
processes get the *same* value; the opponent sets the opposite on theirs.

```
we set --first cop     ->  our Cop plays 1-3,  our Thief plays 4-6
they set --first thief ->  their Thief plays 1-3, their Cop plays 4-6
```

Both peers sending the string `"3-3"` settles nothing about who opens as Cop. Get
this wrong in the same direction and both sides field a Cop in sub-game one.

---

## Playing

One command per role. It serves, negotiates, plays, audits and files.

```powershell
# terminal 1 - the Cop repository
uv run python -m core play --role cop --tunnel --first cop --out results\ `
    --opponent https://their-domain.ngrok-free.dev/mcp

# terminal 2 - the Thief repository, after sub-game 3
uv run python -m core play --role thief --tunnel --first cop --out results\ `
    --opponent https://their-domain.ngrok-free.dev/mcp
```

The command prints our public URL on startup — give that to the opponent.

| Flag | Default | Notes |
|---|---|---|
| `--first` | `cop` | Negotiated. See above. |
| `--role-split` | `3-3` | Blocks in order; `1-1-1-1-1-1` swaps every sub-game. |
| `--wait` | 120 s | Keeps retrying the handshake while they start up. Only a transport failure is retried — a refusal on the merits is reported at once. |
| `--linger` | 20 s | Keeps serving after our last sub-game so **they** can finish auditing our log. Do not set this to 0. |
| `--out` | none | Omit for a warm-up, so a rehearsal leaves nothing that looks like a league match. |
| `--tunnel` | off | Required for league play (M#10); omit for a local rehearsal. |

A refused handshake exits **1** with no move sent. That is the correct outcome —
a match played under configs differing by one byte cannot be audited.

## What you should see

```
handshake       : AGREED
game id         : 2026-08-08_bestteam-vs-<them>_cb93b34a
our sub-games   : 1, 2, 3

  sub-game 1  cop    SURVIVAL            5 - 10   35 steps  audit passed
      thief survived 35 of 35 steps
  ...
totals          : us 15 - them 30
league points   : us 15 - them 30  (decided_on_points)
artefacts       : 7 files in results\
report          : held back - result_....json covers 3 of 6 sub-games
  the other role process files the rest and sends then (M#35)
```

`audit passed` on every row is the one to check. `FAILED` means their log did not
re-hash — file it, do **not** score it yourself (M#19).

The second terminal ends the same way but with the report actually gone:

```
report          : sent to rmisegal+uoh26finalgame@gmail.com  (result_....json, 6 sub-games)
  now confirm THEY sent theirs - a missing report is 0 for BOTH (M#35)
```

**The two halves share one report file.** Both processes write
`result_<game_id>.json` and each *merges* into what the other left, keyed by
sub-game number — so the file always describes all six, whichever order the
terminals run in and however many times one is retried. Whoever files the sixth
row sends it. Anything less than six is held back deliberately: two messages
under one `game_id`, the earlier disagreeing with the later, is the
contradictory pair M#35 voids matches over.

## Afterwards

1. **Agree the figures with them** before either side reports. Both scoreboards
   must mirror: our 15-30 is their 30-15.
2. **Verify a log**, which is also a required submission artefact:
   ```powershell
   uv run python -m core replay results\log_<game_id>_g01.json --headless
   ```
   Exit code 0 and `Verified OK - 35 steps re-hashed, no mismatch`.
3. **Confirm they sent theirs.** Ours goes automatically when the sixth sub-game
   is filed; theirs is a question you have to ask. A missing or contradictory
   report voids the match and scores 0 for *both* teams (M#35).
4. **Commit the config JSON and the logs**, and add the row to
   `docs/LEAGUE_LOG.md` — date, role, result, reports sent, commit hash (M#37).

### If the report did not go

The match prints `NOT SENT` with the reason, or `held back` when the series
never reached six sub-games — an opponent who drops at sub-game four leaves a
four-row report that still has to be filed. Either way:

```powershell
uv run python scripts\send_report.py --role cop results\ --dry-run   # see what would go
uv run python scripts\send_report.py --role cop results\             # send it
```

A directory resolves to its newest `result_*.json`; pass the file itself to be
certain. It reads the same `[email]` block and the same Gatekeeper the match
does, so it is not a second send path that could behave differently. Use it too
when the two teams reconcile their scoreboards after the fact and the result
file is corrected — send the corrected one and tell them you have.

## What the tunnel can carry

A free ngrok endpoint stops completing the TLS handshake at about **120
requests a minute**. It is not an HTTP error: the client sees a bare
`ConnectError`, and the agent's own request log shows nothing at all, because
the connection never becomes a request. Two live rehearsals on 08/08 died at
step 9 of sub-game 1 this way — a technical loss for both sides, decided by a
network budget rather than by anything either strategy did.

Two things keep us under it, and both are already in place:

- **One MCP session for the whole match**, not one per message. A session per
  call is an initialize, a notification, a stream, the call and a delete — six
  connections to send one move, and it exhausts the budget in ten turns.
- **`[network] max_calls_per_minute`**, 100 by default, which paces our
  outbound messages at 0.6 s against a 30 s response window.

Consequences worth knowing before you play:

| | |
|---|---|
| Budget is per **endpoint** | Their calls to us spend *our* minute. Pacing our own outbound bounds the joint rate, because they wait on our messages. |
| A sub-game costs ~70 requests | 35 steps, commit and reveal. Roughly 42 s at the shipped pace. |
| Raising the pace is not free | Above ~120 a minute the tunnel refuses, and a refusal mid-sub-game is 0 for both teams. |

If a match ever dies with `ConnectError` and an empty agent log, this is it —
not the opponent, and not their config.

## Two warnings the handshake will print

Both appeared on every rehearsal and both matter:

- *"working tree is DIRTY"* — commit before a counted match. The declared commit
  is what makes the result reproducible (M#53).
- *"agreed_between names bestteam"* — add the opponent's team id to the shared
  config before signing, or the filed snapshot does not record who agreed to it.
