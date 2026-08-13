# bestteam — Cop Agent
## Distributed Cops-and-Robbers over a Peer-to-Peer Network

> **Companion repository (Thief agent): https://github.com/Diana-Koroblov/bestteam-thief**
> The two agents are developed as a matched pair and run as two completely separate processes.

University of Haifa · Orchestration of AI Agents · 2026
Team ID: `bestteam`

---

> **Status: in development.** The full academic report — Dec-POMDP formalism, FastMCP orchestration
> dilemmas, strategies implemented, screenshots of the belief heatmap and the `Verified OK` replay —
> lands here before submission. See `docs/TODO.md` phase 10 for what is still outstanding.

---

## What this is

An autonomous **Cop** agent that pursues a Thief across a 7×7 grid, over a real peer-to-peer network,
with **no central server and no referee**. The agent is simultaneously an MCP server (exposing tools
the opponent calls) and an MCP client (calling the opponent's tools).

It never observes the true world state. It builds a probabilistic belief about the Thief's position
from two sources: a decaying pheromone trail, and a free-text verbal hint that may be a deliberate
lie. Integrity without a judge is enforced by SHA-256 commit-reveal and a mutual end-of-match audit.

## Repository separation

This repository contains the shared `core/` engine and **only** the Cop role: `police/` and
`config/police/`. It does not contain the Thief's brain or configuration — those live in the
companion repository. The two peers communicate exclusively over MCP; no import path joins their
running processes.

Both repositories are published from one working tree by `scripts/publish.py`, which enforces the
split. See `docs/PLAN.md` ADR-001.

## Quick start

```bash
uv sync --all-extras --dev          # uv only; pip/venv are not used in this project
cp .env-example .env                # then fill in your own credentials
uv run python -m core peer --role police
```

## Network exposure

Both machines sit behind NAT, so neither can reach the other directly. A tunnelling agent publishes
a public URL that forwards to the local FastMCP port. Public exposure is mandatory for league play
(rule M#10); local development needs none of it and continues to run on `127.0.0.1`.

```bash
uv run python -m core peer --role police --serve --tunnel
```

`core/infra/tunnel.py` starts the agent, **reads the public URL back from the agent's own local
API**, and prints it. It is read back rather than computed from config on purpose: a tunnel that
failed to start otherwise looks identical to one that worked, right until the opponent cannot reach
us mid-match. The authtoken comes from `NGROK_AUTHTOKEN` in `.env` and is passed through the child
process's environment, never on the command line where the process table would expose it (M#39).

The manual equivalent, for debugging:

```bash
ngrok http 8081 --url YOUR-DOMAIN.ngrok-free.dev
```

A **reserved static domain** keeps the address alive across a restart, so it goes into the
declaration once instead of being re-exchanged per match. Set it in `.env` as `NGROK_DOMAIN`, not in
committed config: a domain is bound to one ngrok account, and a committed one fails with
`ERR_NGROK_320` for everybody else — which is a tunnel that cannot start, therefore no public URL,
therefore no league match (M#10). Leaving it empty is legal; the agent then assigns a random URL and
`core/infra/tunnel.py` reads it back.

### If the tunnel drops

`core/runtime/tunnel_supervisor.py` restarts it, re-runs the handshake so the opponent is not left
talking to a stale session, and gives up after three attempts. It feeds the watchdog only while the
tunnel is healthy, so a tunnel that cannot be revived ends the sub-game in a clean `TECHNICAL_LOSS`
within `watchdog_timeout_sec` rather than hanging. A hang is worse than a loss: it produces no log
and scores 0 for *both* teams.

### Fallback provider

ngrok is primary. **Localtonet** is the documented fallback, selected by config rather than by a
code change:

```toml
# config/police/game.toml
[network]
tunnel_provider = "localtonet"   # ngrok | localtonet
```

with `LOCALTONET_AUTHTOKEN` in `.env`. Its argument form in `core/infra/tunnel.py` has never been
run against a live Localtonet account — confirm it against their docs before a graded match, not
during one.

## Quality gates

One command runs every gate, commits, and publishes to both repositories. It stops at the first
failure and pushes nothing unless all four gates are green.

```bash
uv run python scripts/ship.py -m "feat: barriers and capture rules"
```

The gates individually, for debugging:

```bash
uv run ruff check .                        # zero violations
uv run python scripts/check_file_size.py   # no file over 150 code lines
uv run python scripts/scan_secrets.py      # no API keys or private keys
uv run pytest                              # coverage >= 85%
```

## Reference implementation — reverse engineering

Before writing our own agent we analysed the course's reference simulator
([`rmisegal/Game-P2P-Cop-Chase`](https://github.com/rmisegal/Game-P2P-Cop-Chase)) by turning it into
a knowledge graph, following the technique from lecture L07.

![Module dependency graph of the reference implementation](assets/reference-graph.png)

`scripts/make_graph_vault.py` parses every module with Python's `ast` and emits an Obsidian vault —
one note per module, one wikilink per **internal** import. Standard-library and third-party imports
are dropped, because the question is how the pieces depend on each other, not what gets installed.
**60 modules, 123 internal edges, 2,949 lines of code.**

*Orphan nodes are hidden in the figure.* Every one of them is an empty `__init__.py` — packaging
scaffolding with no dependencies in either direction. We checked before hiding them: the generated
index lists every unimported module, and the set is exactly the package initialisers plus
`__main__`, so no real code is concealed by the filter.

| Colour | Package | Modules | Role |
|---|---|---|---|
| Red | `domain` | 12 | Board, rules, scent, belief, crypto, negotiation |
| Green | `peer` | 10 | Runtime, handshake, turn loop, sealing |
| Gold | `gui` | 10 | Live view and replay |
| Light green | `infra` | 5 | MCP transport, LLM providers, email |
| Teal | `report` | 6 | The four JSON artefacts |
| Blue | `sdk` | 3 | Public facade |
| Navy | `shared` | 6 | Config, gatekeeper, rate limiter |
| Purple | `strategy` | 3 | Trash-talk providers |
| Magenta | root | 5 | `constants`, `exceptions`, `cli`, `__main__` |

### What the graph showed us

**The hubs are the leaves.** `exceptions` (imported by 14) and `constants` (11) are the most depended
upon modules in the codebase and depend on nothing themselves — cross-cutting concerns sitting
correctly at the bottom of the dependency order.

**`peer.runtime` is the orchestrator**, with 16 connections, more than any other node. It matches the
Orchestrator pattern the rulebook prescribes in Chapter 8: a single component that reaches every
subsystem while the peripheral modules do not reach each other.

**No dead code.** The only modules nothing imports are the package `__init__` files and `__main__` —
every other module is reachable from an entry point.

Reading the code alongside the graph also produced four documented divergences between the
simulator and the rulebook, recorded in [`docs/CONTRADICTIONS.md`](docs/CONTRADICTIONS.md) as C-005
through C-009 — including a decay formula that yields 0.80 where the book specifies 0.81, which the
mandatory pre-match worked example (M#23) is designed to catch.

## Documentation

| Document | Contents |
|---|---|
| `docs/MATCHDAY.md` | **How to play another group, start to finish** — setup, the terms to agree, the two commands, reporting |
| `docs/SETUP.md` | The four external accounts: Gmail OAuth, Groq, Ollama, ngrok |
| `docs/PRD.md` | Requirements, KPIs, binding parameters, acceptance criteria |
| `docs/PLAN.md` | Architecture, C4 diagrams, state machine, data schemas, ADRs |
| `docs/TODO.md` | Task breakdown by phase, with owner and definition of done |
| `docs/CONTRADICTIONS.md` | Rulebook contradictions found, choices made, and why |
| `docs/PROMPT_LOG.md` | The prompts used to build this system |

## Licence and attribution

Coursework for the University of Haifa. The example simulator by Dr. Yoram Segal
(`rmisegal/Game-P2P-Cop-Chase`) was studied as reference material under its educational-use licence;
this implementation is our own.
