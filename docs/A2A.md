# A2A coordination — what we expose, and what we found

The Rulebook makes MCP the project requirement and A2A a *strongly recommended*
complement for task hand-off between agents (Ch. 2.3, [9]). This is that
complement: two read-only endpoints for readiness and debugging. **No game
message goes through them.** Commits, reveals, barrier declarations and capture
claims stay on the six MCP tools, where they are sealed, logged and replayable
(M#18) — a move that arrived over an unaudited side channel could not be
verified afterwards by anyone, including us.

---

## What we serve

Every server we stand up carries these, with no flag to remember: `peer --serve`,
`play`, and both protocols. They ride the **same port and the same tunnel** as
`/mcp`, because we have one reserved domain and a second process would need a
second public URL.

| Path | Method | What it is |
|---|---|---|
| `/.well-known/agent-card.json` | GET | The Agent Card. |
| `/.well-known/agent.json` | GET | Same card. Earlier A2A revisions spelled it this way. |
| `/message:send` | POST | The path nis-yar1 asked us for. |
| `/a2a/message:send` | POST | The path nis-yar1's own server answers on. |
| `/mcp` | POST | The game. Unchanged. |

Four paths for two endpoints is deliberate. A2A has moved the card between two
spellings, and their note asks for `POST /message:send` while their server
serves `/a2a/message:send`; picking one and being wrong is a 404 discovered on
the morning of a match. Both request envelopes are accepted too — the REST form
their note documents, and the JSON-RPC form the specification uses — and the
reply comes back in whichever arrived.

The card's URLs are read off the **incoming request** (`X-Forwarded-Proto` /
`X-Forwarded-Host`, then `Host`), never off our config. The same process answers
on `http://127.0.0.1:8081` during a rehearsal and on the ngrok domain during a
match, and a hardcoded card would be wrong half the time.

Nothing private is published. The card carries the team, the members, the two
repositories, the MCP tool names, the negotiated timeouts and `config_sha256` —
all of which the opponent receives at Step-0 anyway. The LLM provider is private
per peer under Appendix F Table 21 and is **not** in it; neither is anything
from `game.toml`.

## Running it

```powershell
# Publish (any of these; the A2A routes are always on)
uv run python -m core peer --role cop --serve --tunnel

# Print exactly what a peer would be told, without serving
uv run python -m core a2a --role cop

# Check a peer: card, message endpoint, and that MCP has all six tools.
# Exits non-zero if any is unusable.
uv run python -m core a2a --role cop --probe https://them.trycloudflare.com
```

`--probe` opens a **new connection for every request**. That is not caution for
its own sake — see the keep-alive finding below.

---

## Our reply to nis-yar1

Their five questions, answered. Paste as-is; the same text comes back from our
`/message:send`, which is the point of having one.

> 1. **Agent Card**: `https://denotatively-sciuroid-florine.ngrok-free.dev/.well-known/agent-card.json`
> 2. **A2A message**: `https://denotatively-sciuroid-florine.ngrok-free.dev/message:send`
>    (also served at `/a2a/message:send` — use either)
> 3. **MCP game**: `https://denotatively-sciuroid-florine.ngrok-free.dev/mcp`,
>    exposing `negotiate`, `receive_commit`, `receive_reveal`, `declare_barrier`,
>    `capture_claim`, `final_reveal`.
> 4. **First commit**: confirmed. Our runner pushes `receive_commit` for step 0
>    as soon as negotiation is settled, without waiting for yours, and then waits
>    for yours. Every step is symmetric — both sides push a commit, then both
>    reveal. Neither peer is the initiator, so there is nothing to take turns
>    about and no deadlock if you do the same.
> 5. **Timeouts: not as proposed.** We run **30 s per message at every step,
>    step 0 included**, with one retry — so 60 s of patience before a technical
>    loss — and a 60 s watchdog. We do not implement 60 s at step 0 and 10 s
>    afterwards, and we would rather not: 10 s is tight enough to fail an honest
>    turn on a home connection, and a technical loss scores 0 for the side that
>    timed out. These three values are `network_and_league` in the `game.json` we
>    have both hashed. Changing any of them changes `config_sha256`, so it has to
>    be agreed and re-packed **before** the match, not discovered during it.
>
> Our `config_sha256` is `a58adb10a4cfaebf896d8e9eaff1f729de3bd55ee2d78aafadaec53401f32e55`.
> If yours differs we are not playing the same game and the handshake will refuse.
>
> The URL is an ngrok tunnel and is live only while our peer is running. Ask us
> to bring it up before you probe.

## What we found probing yours (13/08)

Run for run: `uv run python -m core a2a --role cop --probe https://inches-drawings-dem-extends.trycloudflare.com`

**Your MCP server is healthy and speaks our protocol.** It exposes nine tools —
our six plus `receive_turn`, `submit_audit` and `receive_control` — so the
friendly can run on the native commit/reveal path with no compatibility layer on
either side. That settles C-019 for this match.

Three things on the A2A half, in the order they will bite:

1. **`POST /message:send` returns 404 on your host.** It is the path your own
   note asks *us* to expose, and only `/a2a/message:send` answers on yours. We
   serve both; a peer that reads your note and calls the documented path gets a
   404 from you.
2. **Your endpoint 400s on a reused connection.** The first request on a fresh
   connection returns 200; the second on the same socket returns
   `400 Bad request syntax` with a `BaseHTTPRequestHandler` HTML error page —
   the signature of a handler that does not read the request body, leaving the
   next request parsed from the middle of the previous one. Every pooling client
   hits this: `httpx`, `requests.Session`, a browser. Draining
   `Content-Length` bytes in every branch — the 404 branch included — fixes it,
   or send `Connection: close`. It cost us one wrong diagnosis before we
   isolated it, and it is the kind of fault that reads as "their server is
   down".
3. **Your Agent Card declares no `url`.** The endpoint is in
   `supportedInterfaces[].url`, which is not a field any A2A revision defines —
   the spec uses `url` plus `additionalInterfaces`. A strict client cannot
   discover your endpoint from your card. Ours reads both, so this is
   cosmetic between us and fatal against anyone else's tooling.

Also: your coordinator replies with a Task whose artifact is
`"received: <our text>"`. It echoes rather than answers, so we still do not have
your five confirmations — in particular **who sends the first `receive_commit`**
and **which timeouts you actually enforce**, which is the one that decides
whether a slow turn is a technical loss.

---

## Why this is not the game channel

A2A manages a task lifecycle between agents; it does not seal anything. Our
audit trail is the commit-reveal log: a digest published before the move, the
nonce revealed after, and a replay that recomputes both (M#18, M#20). A move
delivered over A2A would have no digest to check and no line in the log, so
`replay --headless` could not verify the sub-game it belonged to and the result
would not be defensible.

So a coordination message that mentions `receive_commit`, `receive_reveal`,
`final_reveal`, `declare_barrier`, `capture_claim`, a digest or a nonce is
answered with a refusal rather than silently accepted, and the refusal names
what was wrong. Being told "send that through MCP" is recoverable in seconds;
discovering after a series that half of it happened off the record is not.
