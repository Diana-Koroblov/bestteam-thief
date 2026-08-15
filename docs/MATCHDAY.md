# Match Day — playing another group

Everything here has been run end to end. The scoreboard, the four artefacts and
the `Verified OK` replay in this document come from a real two-process match over
HTTP, not from the test suite.

Read it in order on the day: **set up → agree the terms → play → report.** Each
section is what the one before it makes possible, and the two that most often go
wrong are the ones with no code in them at all.

---

## Before match day

Once per machine, and once more the morning of a counted match.

```powershell
uv sync --all-extras --dev          # uv only; pip/venv are not used here
uv run python scripts/check_setup.py
```

`check_setup.py` checks the `.env` file, the credentials path, the Gmail token,
Ollama, the ngrok binary and authtoken, the reserved domain and which trash-talk
provider this machine will actually use. Every failure it reports names the
`docs/SETUP.md` step that fixes it.

**Read the Ollama and provider lines together.** They are the one pair that can
both look fine and still cost the match. `P2P_LLM_PROVIDER=ollama` against a
service that is not answering does not fail — every turn pays the provider
timeout and then writes the template hint anyway, which is up to 8 s a turn on
top of a 30 s response window. On Windows the daemon does not start on demand:

```powershell
Get-Process ollama -ErrorAction SilentlyContinue   # nothing = it is not running
ollama serve                                       # in its own terminal, leave it up
ollama pull llama3.1:8b                            # the model named in [llm]
```

`ollama list` **hangs** rather than erroring when the daemon is down, which is a
confusing way to discover it. If you are not going to keep that terminal open,
set `P2P_LLM_PROVIDER=template` and play — it is the book's own default, costs
zero tokens, and movement is never decided by a model (Ch. 6).

**Three values in `.env` are facts about the computer, not about the match.** None
of them is negotiated and none belongs in a committed file:

| Variable | Why it is not in `game.toml` |
|---|---|
| `NGROK_DOMAIN` | The reserved domain is bound to one ngrok account, which makes it an account credential in everything but name. Committed, it fails with `ERR_NGROK_320` for anyone else — and a tunnel that cannot start means no public URL and no league match (M#10). Empty is legal: the agent then assigns a random URL, which is read back rather than computed. |
| `P2P_LLM_PROVIDER` | Private per peer under Appendix F Table 21. `ollama` is preferred — zero tokens, which is scored (ADR-003) — **but only while it is actually running**, so check it below. `template` is the safe answer otherwise. |
| `NGROK_AUTHTOKEN` | A secret. Nothing that identifies an account belongs in a committed file (M#39, M#40). |

`P2P_PUBLIC_DOMAIN` is the old name for the first of these. It is still read, but
last; delete it from `.env` if it is still there.

**Commit before a counted match.** The handshake prints *"working tree is DIRTY"*
otherwise, and the declared commit hash is what makes the result reproducible
after the fact (M#53).

```powershell
uv run python scripts/ship.py -m "chore: clean tree for the match vs <them>"
```

---

## Before you connect

**1. Agree the terms in writing.** Send the opponent a pack and read theirs:

```powershell
uv run python -m core negotiate --role cop --pack outbox\
uv run python -m core negotiate --role cop --review their-game.json
```

`--review` exits non-zero on an Appendix F breach. Agreeing to one disqualifies
**both** teams (M#12), and "they proposed it" is not a defence.

**2. Settle the five things no Appendix decides.** These are the ones that void a
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

**4. Write their team id into the contract, then re-send the pack.** Both
`config/police/game.json` and `config/thief/game.json` ship with
`"agreed_between": ["bestteam"]`, and the handshake warns about it every time.
Add the opponent:

```json
"agreed_between": ["bestteam", "their-team-id"],
```

Two things follow, in this order:

- **The two files must stay byte-identical.** They are the same shared contract
  and both of our processes hash it; a match played under two versions of our own
  config is one our own two halves cannot agree on.
- **This changes `config_sha256`.** So do it *before* the final pack goes out, and
  re-run `--pack` afterwards. Editing it after they have loaded your `game.json`
  means their digest no longer matches yours and the handshake refuses — which is
  the correct outcome, and an avoidable way to lose a booked slot.

**5. Probe them before you play them.** Which protocol an opponent speaks, and
whether their server is even up, are facts about their running process — not
things to agree by chat and discover at the handshake. Two friendly slots were
lost that way on 13/08 (C-019).

```powershell
uv run python -m core probe https://their-domain.ngrok-free.dev/mcp
```

It lists the tools their MCP server actually exposes and says what to do about
them: six means ours and no flag, four mailboxes means `--protocol reference`,
and anything else is named rather than guessed at. Exit 0 means playable. It
needs no role and no config, so it runs from a fresh clone and against a peer
who has not finished setting up.

> **Retired 15/08: the A2A complement.** This step used to run
> `core a2a --role cop --probe <host>`, which also fetched an Agent Card and
> posted to an A2A message endpoint. Both are gone — the league coordinates
> over the human channel, and the card asked nothing a match depends on. The
> old command was actively misleading twice over: it failed the whole verdict
> unless the card *and* the A2A endpoint *and* MCP all answered, so an opponent
> who never built A2A read as `NOT READY`; and it checked their tools against
> our six only, so the reference implementation's perfectly playable four came
> back as five missing tools.

---

## Playing

One command per role. It serves, negotiates, plays, audits and files.

```powershell
# terminal 1 - the Cop repository
uv run python -m core play --role cop --tunnel --first cop --out results\ --counted `
    --opponent https://their-domain.ngrok-free.dev/mcp

# terminal 2 - the Thief repository, after sub-game 3
uv run python -m core play --role thief --tunnel --first cop --out results\ --counted `
    --opponent https://their-domain.ngrok-free.dev/mcp
```

**`--counted` is what actually mails the report.** Without it the series is
played and filed exactly as normal and the message is never sent, which under
M#35 is 0 for both teams. It is opt-in rather than automatic because the two
mistakes are not equally bad: a forgotten flag is one command to recover
(`send_report.py`, printed in the same breath), and a rehearsal that mails the
lecturer a fabricated league result cannot be withdrawn. Put it on **both**
terminals — whichever files the sixth sub-game is the one that sends.

**`--opponent` is always *their* URL, never ours**, and it is the same value in
both terminals: they hold one reserved domain too, mapped to whichever of their
two processes is running. Ours is what the command prints on startup, and the
line to paste into the chat window is spelled out for you:

```
role            : cop  (AdvancedCop)
our url         : https://denotatively-sciuroid-florine.ngrok-free.dev/mcp
give them       : --opponent https://denotatively-sciuroid-florine.ngrok-free.dev/mcp
their url       : https://their-domain.ngrok-free.dev/mcp
```

Check `their url` against what they sent. Pointing `--opponent` at our own URL
does not quietly half-work: the peer negotiates with itself, both sides claim
the same role, and `settle` refuses with *"we both propose to play cop"* — exit
1, no move sent (C-011). Confusing for a second, then obvious.

**One after the other, not side by side.** The Cop listens on 8081 and the Thief
on 8082 (`[network] listen_port`), and one reserved ngrok domain maps to exactly
one of them at a time. Start the second terminal when the first has finished its
three sub-games and its `--linger` has run out. The opponent keeps the *same*
`--opponent` URL across the whole match, because it is the domain that is fixed
and not the port behind it.

In this working tree both roles are present, so both terminals run from here. In
the published repositories they are two clones — each ships one role (ADR-001),
and asking a Cop repository for `--role thief` says so plainly rather than
failing later on a missing file.

| Flag | Default | Notes |
|---|---|---|
| `--first` | `cop` | Negotiated. See above. |
| `--role-split` | `3-3` | Blocks in order; `1-1-1-1-1-1` swaps every sub-game. |
| `--wait` | 120 s | Keeps retrying the handshake while they start up. Only a transport failure is retried — a refusal on the merits is reported at once. |
| `--linger` | 20 s | Keeps serving after our last sub-game so **they** can finish auditing our log. Do not set this to 0. |
| `--out` | none | Omit for a warm-up, so a rehearsal leaves nothing that looks like a league match. |
| `--tunnel` | off | Required for league play (M#10); omit for a local rehearsal. |
| `--counted` | off | **A league match: mail the report.** See above. Ignored when the opponent's team name is our own, because a self-match has no second reporter. |
| `--protocol` | `native` | Which wire protocol to speak. **Ask them before the slot** — see below. |
| `--gui` | off | Watch it happen: own position, own barriers, the belief heat map, the hints received. Local truth only (M#8, M#9). **Closing the window does not forfeit** — the match plays on and the report still goes. Ch. 9.4 wants a capture of the heat map, so take one mid-series rather than at step 0, where the prior is uniform and the board is a flat wash. |

A refused handshake exits **1** with no move sent. That is the correct outcome —
a match played under configs differing by one byte cannot be audited.

### Which protocol do they speak? Ask first, not at the slot

**This is the question that has cost us the most match time.** Our native
surface is six synchronous tools; the Appendix D example repository exposes four
fire-and-forget mailboxes, and most teams built on it (C-019). The two cannot
talk to each other, and the failure looks like a network fault rather than a
mismatch — an unrecognised tool, a reply of the wrong shape, or a peer that
simply never answers.

```powershell
# them: negotiate / receive_turn / submit_audit  ->  the example repository
uv run python -m core play --role cop --protocol reference --tunnel `
    --opponent https://their-domain/mcp

# them: receive_commit / receive_reveal / final_reveal  ->  ours
uv run python -m core play --role cop --tunnel --opponent https://their-domain/mcp
```

One message settles it, and it can be sent days ahead: *"call `tools/list` on
your own endpoint and send us the names."* Six tools means `native`; four means
`reference`. `python -m core probe <their-url>` asks the same question directly
and answers it for you.

**`--protocol reference` is a full league path, not a rehearsal-only one.** It
files the four artefacts in the league's own schema (`core/compat/
league_report.py`) and mails the closing report, gated exactly as the native
path is: `--out` to file, `--report-to` for an uncounted friendly send to the
two teams' own inboxes, `--counted` for a league one to the lecturer. Since
most of the league built on the example repository (C-019), this is the path a
counted match against them runs on.

> **Corrected 15/08.** This section used to say `--protocol reference` "plays
> and audits but files nothing — no artefacts, no report, no league row" and
> that "a counted match still runs on the native path". That was true when the
> bridge was written and stopped being true when the league path landed. Read
> literally, it ruled out counted matches against most of the league.

**Play a warm-up against them first if there is time.** Uncounted matches are
explicitly permitted (M#52) and they are where protocol bugs surface, at no cost
to either side. Run it exactly as above but **without `--out`**, so nothing is
filed that a grader could mistake for a league match, and record what you learned
in the warm-up table of `docs/LEAGUE_LOG.md`.

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

Both appeared on every rehearsal, and each means a step above was skipped. They
are warnings rather than refusals because either one can be legitimate in a
rehearsal — and neither is, in a counted match.

- *"working tree is DIRTY"* — commit first. The declared commit hash is what
  makes the result reproducible (M#53). See **Before match day**.
- *"agreed_between names bestteam"* — the opponent's team id is not in the shared
  config, so the filed snapshot will not record who agreed to it. See step 4 of
  **Before you connect**, and note that fixing it changes the digest.

---

## The whole thing, in ten lines

For the second match, when you no longer need the prose.

```powershell
uv run python scripts/check_setup.py                                  # once, per machine
uv run python scripts/ship.py -m "chore: clean tree for <them>"       # M#53

uv run python -m core negotiate --role cop --pack outbox\             # send them this
uv run python -m core negotiate --role cop --review their-game.json   # exit 1 = refuse
#   settle: role split, decay 0.81, capture readings, sampling, axes, --first
#   add their team id to BOTH game.json files, then re-send the pack

#   --opponent is always THEIR public MCP URL, and the same one both times:
#   they hold one reserved domain too, mapped to whichever of their two
#   processes is running. OURS is printed on startup - that is what they need.
uv run python -m core play --role cop   --tunnel --first cop --out results\ --counted --opponent https://THEIR-domain.ngrok-free.dev/mcp
uv run python -m core play --role thief --tunnel --first cop --out results\ --counted --opponent https://THEIR-domain.ngrok-free.dev/mcp
#   --counted is what mails the report. Without it: filed, never sent, 0 both (M#35)

uv run python -m core replay results\log_<game_id>_g01.json --headless # Verified OK
#   confirm they sent their report; add the row to docs/LEAGUE_LOG.md
```
