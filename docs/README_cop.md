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

## Quality gates

Run before every commit. All four are enforced in CI.

```bash
uv run ruff check .                        # zero violations
uv run python scripts/check_file_size.py   # no file over 150 code lines
uv run python scripts/scan_secrets.py      # no API keys or private keys
uv run pytest                              # coverage >= 85%
```

## Documentation

| Document | Contents |
|---|---|
| `docs/PRD.md` | Requirements, KPIs, binding parameters, acceptance criteria |
| `docs/PLAN.md` | Architecture, C4 diagrams, state machine, data schemas, ADRs |
| `docs/TODO.md` | Task breakdown by phase, with owner and definition of done |
| `docs/CONTRADICTIONS.md` | Rulebook contradictions found, choices made, and why |
| `docs/PROMPT_LOG.md` | The prompts used to build this system |

## Licence and attribution

Coursework for the University of Haifa. The example simulator by Dr. Yoram Segal
(`rmisegal/Game-P2P-Cop-Chase`) was studied as reference material under its educational-use licence;
this implementation is our own.
