# Distributed Cops-and-Robbers over a Peer-to-Peer Network

**Rules and guidelines book for the 2026 final project — Department of Computer Science, University of Haifa**

Dr. Yoram Reuven Segal · © All rights reserved · 2026
Book version 3.0.0 | Example code version 3.0.0

> **Unofficial English translation** of `police_thief_p2p.pdf` (Hebrew), produced for this
> repository. Where this translation and the Hebrew original disagree, **the Hebrew original
> governs**. Section and table numbers follow the original so cross-references still resolve.
> Appendix letters: the Hebrew uses א–ו; here they are **A–F** in the same order.

---

## Abstract

This book is the complete rules and guidelines guide for the final project in *Orchestration of AI
Agents* at the Department of Computer Science, University of Haifa. The project puts students to the
course's culminating development task: building two autonomous, **symmetric** entities — **Cop** and
**Thief** — that face each other in a pursuit race on a board of a given size (say 10×10), with **no
central server** arbitrating between them. Neither of the two sees the true world state: each agent
builds, symmetrically, a belief over the opponent's position out of a decaying scent map and a verbal
hint that may be a lie.

The system is formally modelled as a decentralised, partially observable Markov decision process
(**Dec-POMDP**) and runs over a **peer-to-peer** network in which each agent is simultaneously server
and client over the **Model Context Protocol**, using the **FastMCP** library.

The book covers the full development scope: modelling the problem under uncertainty; the P2P
architecture over FastMCP; board mechanics, barriers and scoring; the scent-trail mechanism based on
stigmergy; the cryptographic **commit-reveal** protocol, which guarantees integrity with no referee
and includes automatic disqualification for forgery; the strategy module built on heuristics and a
language model (with reinforcement learning as **one option only**); the user interface and replay
simulator; and league structure, computational fairness and automated reporting over the Gmail API —
including submission in two GitHub repositories (cop and thief) and a signed JSON report.

Attached to the book are operational appendices, plus an **example code repository** — a basic,
open, public simulation implementation described in Appendix D; a **complete mapping of the mandatory
rules** (Appendix E); and the **binding parameter table** (Appendix F), which is the single source of
truth for quantitative values. Every chapter is anchored to principles taught across the course and
converts them from theory into a live system operating under real network conditions.

---

## A personal word — before you start the race

I am addressing you, the students who have reached this point in the course: the final project is not
another classroom exercise, it is a **race**. Over a full semester you built the infrastructure — you
learned how a neural network learns, how a Transformer listens, how a single agent delegates tasks to
sub-agents, and how two agents talk to each other over an MCP server. Now the moment has come to join
all the pieces into one autonomous entity that goes out into the world and faces another entity you
do not control.

This race differs from everything you have done so far in one essential point: **there is no
referee.** There is no central server holding the truth, settling disputes and protecting you from
cheating. Instead, truth is built bottom-up — by two opponents who do not trust each other but are
obliged to prove their integrity through mathematics. This is exactly the challenge real-world
distributed AI systems face: coordination without a ruler, trust without a central authority, and
sound decision-making under a fog of information.

> ### Why hard rules are actually for your benefit
>
> The rules in this book are iron and that is deliberate. A precise cryptographic protocol, a binding
> JSON structure and hard time limits are not there to make life difficult but to **enable** a fair
> game between groups that do not know each other. The more tightly the specification is drawn, the
> greater your freedom to innovate **inside** the frame — in strategy, in deception, and in
> architecture. Discipline in the details is what releases creativity at scale.

I invite you to read this book not as a list of requirements but as a road map to a system you will
be proud of. Read slowly, build in the priority order defined in the final chapter, and check each
stage before moving on. The real victory is not only in catching the thief — it is in your ability to
build a system that stands up under real network conditions, proves its integrity, and adapts to
uncertainty. That is the skill that will stay with you far beyond this course.

*Dr. Yoram Reuven Segal*

---

## Clarification: what is binding and what is only illustrative

> ### Read before everything — the foundational principle
>
> **The default is that a rule is not binding unless it is explicitly written to be binding.** All
> the figures, examples, code fragments and scenarios in this book are a **means of illustrating**
> how the game is run — they are not the rules of the game and they do not bind the participants,
> unless it is explicitly stated beside them that they are part of the rules and bind the sides.
> Where it is not stated that a rule is binding, the rule **is not** binding, and either side is free
> to agree with the opponent on different behaviour, or to act as it sees fit within the frame of the
> rule.
>
> The only source of obligation is the **binding parameter table** at the end of the book (Appendix
> F). The values defined there are a *minimum*: they may be raised by agreement, but they may not be
> lowered.

> ### Key: code-names for quantitative values
>
> Throughout the book, every quantitative value appears as a **code-name** — a Hebrew phrase in
> square brackets, e.g. `[board size]`, `[barrier quota]` or `[scent decay rate]`. The convention is
> simple: the numeric value is **not** fixed in the body text but only and exclusively in the
> **binding parameter table** at the end of the book (Appendix F). A single value can therefore be
> changed in one place without the book contradicting itself, and every side knows exactly what the
> binding threshold is and what is only an example value.

---

## General guidance for the book and its structure

> ### Academic freedom in case of a contradiction
>
> This book is written to be as consistent as possible, but you may find a **contradiction** in it —
> two places that appear to dictate different behaviour. In such a case you have **academic freedom**
> to choose one of the possibilities and proceed accordingly, **provided you state so explicitly** in
> your report: where you identified the contradiction, what you chose, and why. A reasoned and
> documented choice will not be held against you. Nevertheless, the single binding source of truth
> for quantitative values remains the **binding parameter table** in the final appendix.

**Structure.** The book has 11 chapters and six appendices. The chapters set out the theory, the P2P
architecture, cryptography, the strategy module, the interface and the league. The appendices are:
the Gmail API and OAuth setup guide (Appendix A); the unified configuration-file format (Appendix B);
GitHub submission requirements (Appendix C); the **example code repository** — a basic, open, public
simulation implementation intended for study only (Appendix D); a **mapping of all the mandatory
rules** — do, do not, and recommendations (Appendix E); and finally the **binding parameter table**
(Appendix F), the last appendix and the only binding source for numeric values.

**Keywords:** Dec-POMDP · decentralised multi-agent system · symmetry between agents · P2P network ·
Model Context Protocol · FastMCP · tunnelling (ngrok) · dynamic pheromones and scent trails ·
collective swarm memory · commit-reveal · SHA-256 · zero-knowledge · Bayesian belief map · Manhattan
distance · prompt engineering and LLM strategy · reinforcement learning (an optional tool) · state
machine · orchestrator · watchdog · gatekeeper · token bucket · computational fairness · replay
simulator · Gmail API · OAuth 2.0

---

# 1. Theoretical framework and modelling the problem

## 1.1 Chapter goals

By the end of this chapter you will know: why a distributed cop–thief race is not a single-agent
planning problem but an **orchestration** problem for a multi-agent system; how a competitive
environment under uncertainty is modelled with the Dec-POMDP formalism; and what each component of
the ordered 8-tuple means in practice, from the state space to the discount factor.

## 1.2 From a single agent to systemic orchestration

Distributed Artificial Intelligence deals with the challenge of several autonomous entities acting in
a shared space, where each entity has only partial information about the state of the world and about
the intentions of the others. What is the essential difference between training a single agent in a
static environment and the project before you? In a static environment the world waits patiently for
the agent's decision. Here, by contrast, the world is itself a thinking opponent — the thief plans,
deceives, and changes the face of the board while the cop is trying to infer where it is.

The project therefore moves you from a focus on an **algorithm** to a focus on a **system**. It is
not enough for an agent to *know* how to choose a good move; it must orchestrate communication, lock
signatures, run turns, and recover from failures (the orchestration and reliability architecture is
laid out in Chapter 8) — all against a side you neither rely on nor control. This is the step up the
course was leading to: from the lectures on a single agent and sub-agents, through conversation
between two agents over MCP, to a full autonomous confrontation.

### 1.2.1 A sharp distinction: prompt chaining vs. multi-agent orchestration

To avoid architectural confusion it is important to distinguish two practices that are easy to
mistake for one another. **Prompt chaining** is routing: the output of one model becomes the input of
the next, in a fixed, pre-written linear sequence. **Prompt chaining is not an orchestration
mechanism**: there is no dynamic division of labour, no bidirectional context sharing, and no shared
state management — only a one-way pipe. **Multi-agent orchestration**, by contrast, is *distributed*
management of the division of labour, context sharing, and preservation of system **state** across
agents running **in parallel** — and that is exactly the model this project adopts. It is **strongly
recommended** to read a comprehensive survey of modern orchestration frameworks and protocols [1].

> ### Strongly recommended: three failure modes characteristic of missing orchestration
>
> Without a true orchestration layer, multi-agent systems tend towards three critical failure states.
> It is strongly recommended to know them so as to avoid them:
>
> 1. **Task duplication.** Two or more agents perform the same work, wasting compute and token budget
>    on a duplicated result.
> 2. **Contradictory outputs.** Agents reach conflicting conclusions with no arbitration mechanism,
>    and the system is left without a coherent decision.
> 3. **Convergence failure.** The system does not converge on a solution but enters a loop of mutual
>    responses that does not terminate.

## 1.3 The Dec-POMDP formalism

The environment is formally modelled as a decentralised, partially observable game, known in the
literature as **Dec-POMDP** (Decentralized Partially Observable Markov Decision Process) [2], [3].
This model extends the classic POMDP [4] to the case of several decentralised decision-makers, and
provides a basis for decision-making under critical uncertainty. The problem is defined by the
following ordered 8-tuple:

> **The ordered 8-tuple defining the game space**
>
> ⟨ n, S, {Aᵢ}, P, R, {Ωᵢ}, O, γ ⟩

> **Ordered tuple**
>
> An ordered tuple is an ordered collection of eight components, each with a fixed role and place;
> here it defines the game space in full, from the number of agents to the discount factor.

The variables defining the game space break down as follows:

- **n — number of agents.** Here n = 2 (cop and thief). *Practical meaning:* every decision is taken
  against a single, rational opponent, not against random nature.
- **S — state space: the full world picture.** Contains the exact coordinates of each agent on the
  grid, the layout of the static barriers, and the scent-trail network that changes dynamically each
  step. *Practical meaning:* the state is multidimensional, so an exhaustive **brute-force** scan of
  it is infeasible — a fact that will drive the choice of algorithms in Chapter 6.
- **{Aᵢ} — action space: what each agent may do.** Composed of physical movement actions,
  construction actions (barrier placement), and communication actions (passing hints in natural
  language, which may be lies). *Practical meaning:* the action space mixes **physics** and
  **psychology** together.
- **P — transition function: how the world changes in response to actions.** P(s′ | s, a₁, a₂) defines
  the probability of reaching a new state given the joint actions. *Practical meaning:* since there is
  no central server, both sides must agree on the same transition function — it is encoded in the
  shared configuration file.
- **R — reward function: what pays and what is penalised.** Supplies the incentive to the learning
  algorithm. *Practical meaning:* it translates directly from the scoring table of Chapter 3.
- **{Ωᵢ}, O — observation space: what each agent actually senses.** The heart of the uncertainty. No
  agent sees its opponent. Both cop and thief feed on the opponent's fading scent trails and its
  verbal declarations. *Practical meaning:* this is where each side's need for a probabilistic
  **belief** map over the opponent's position is born.
- **γ — discount factor: how important the future is against the present.** γ ∈ [0,1) sets the weight
  of a future reward against an immediate one. *Practical meaning:* a high γ encourages strategic
  patience (e.g. building a barrier trap over many turns).

**Figure 1.** The true world state S (left) is accessible to no agent; each agent builds its
observation Ωᵢ (right) of the opponent's position from a decaying scent map and a verbal hint — which
may be a lie. The arrangement is symmetric: cop and thief are hidden from one another to exactly the
same degree.

*What the figure shows:* on the left, the full true state — both agent positions and the barriers. On
the right, the same scene as one of the agents (here the cop) experiences it: not a sharp point but a
cloud of probability. *How to read it:* the brighter the shade, the higher the probability that the
opponent is in that cell. *Symmetry:* the picture is identical in reverse for the thief, which builds
a probability cloud over the cop's position in exactly the same way — the arrangement is entirely
two-sided. *"What if" analysis:* if the verbal hint ("I moved north") contradicts the scent map, the
receiving agent must lower its trust coefficient and update its map — a topic opened in Chapter 6.

## 1.4 Uncertainty as a resource, not only an obstacle

It is easy to see partial observability as a limitation alone. But note the deeper insight: the same
uncertainty that troubles the cop is also the thief's **weapon**, and vice versa, because the
arrangement is symmetric. The ability to send a deceptive verbal hint, to manoeuvre the opponent, or
to vanish behind a barrier — all of these are active exploitation of the observation function O. It
is worth stressing: the verbal hint is the **only** channel of deception. The scent, by contrast, is
a natural phenomenon not subject to control — an agent cannot plant a misleading trail somewhere it
has not been; all it can do is strengthen the scent in the cell where it actually is, by lingering
there or returning to it, and that is a cost rather than an advantage, since it helps the opponent
locate it. The project therefore teaches you to think about information not as a fixed input but as a
battlefield: whoever controls the flow of information controls the race.

> ### Connection to the course
>
> The formalism here is not merely abstract. Dec-POMDP ties together three threads from the course:
> the idea of agents and sub-agents in orchestrated work (lecture L05), the conversation between two
> agents over MCP calling external tools (lecture L09), and the distributed conception in which there
> is no central control and no agent sees the full picture (lecture L11). The chapters ahead will
> take each component of the ordered tuple apart into a working code system.

## 1.5 Chapter summary

We modelled the race as a Dec-POMDP: two agents, a multidimensional state space, physical and
communicative actions, and partial observability that is the heart of uncertainty. We understood that
the move from a single agent to systemic orchestration is the core of the challenge, and that
uncertainty is simultaneously an obstacle and a resource. In the next chapter we descend to the
infrastructure that lets the two agents communicate with no referee — the P2P architecture over
FastMCP.

---

# 2. Distributed (P2P) network architecture and the FastMCP infrastructure

## 2.1 Chapter goals

By the end of this chapter you will know: why full decentralisation of **state management** removes
the need for a central referee and replaces it with cryptographic negotiation between peers; how the
MCP protocol and the FastMCP infrastructure let every agent be **server and client simultaneously**;
and why exposing the server to the public internet through a **tunnel**, and total separation of the
work environments, are not recommendations but a necessary condition for the architecture's
legality.

## 2.2 The paradigm shift: full decentralisation of state management

Traditional game architectures put a **game server** at the centre. It holds the **ground truth**,
arbitrates disputes, and updates the clients. But what happens when we remove the referee from the
arena? The project before you does exactly that: it completes the paradigm shift to **full
decentralisation of state management**. There is no longer any central actor whose word is law.

Instead, the game runs over a **peer-to-peer** (P2P) network in which each agent holds its own
**local truth** only. The two sides do not rely on each other, and therefore every move is verified
against the opponent through cryptographic negotiation. This is an essential move from a centralised
world to a distributed one, in which trust is not assumed but built, step by step, out of signatures
and verifications. The professional literature on distributed systems has long warned that removing a
single point of control shifts the centre of gravity from local computation to **coordination**
between components — which is exactly the challenge before you [5].

### 2.2.1 Why not a central server?

A central server is a **single point of failure** and also a single point of trust: whoever holds it
could, in principle, change the results of the game. Decentralisation removes both weaknesses at
once, but the price is high — every agent must verify independently that the opponent has not
cheated. Here the communication protocol enters the picture.

## 2.3 The MCP protocol and language-model integration

Communication between agents rests on an open standard — **MCP** (Model Context Protocol) — which
connects large language models (LLMs) to data sources and external tools [6], [7]. Our implementation
uses the Python library **FastMCP** [8], which simplifies building both server and client.

The central architectural insight is one of **symmetry**: every agent is simultaneously a **server**
(exposing **tools**, e.g. receiving a natural-language message) and also a **client** (calling the
opponent's server to send data or run queries). There is no "strong" side and "weak" side here; both
peers are entirely equal in their network role.

> ### Tool (in MCP)
>
> A tool is a function the server exposes outwards, described by a built-in schema so that the
> calling side (and even a language model) can safely invoke it remotely. In FastMCP a function is
> marked as a tool with the `@mcp.tool` decorator.

The MCP standard is the project's communication backbone for connecting agents to tools and data
sources; alongside it, complementary protocols are consolidating in the industry for managing task
lifecycles and for secure federated communication, which are well worth knowing.

> ### Strongly recommended: complementary communication protocols — A2A and ACP
>
> The MCP standard is the **project requirement** for connecting agents to tools and data, and is not
> to be replaced. Alongside it, it is **strongly recommended** to know two complementary protocols:
>
> - **A2A** (Agent-to-Agent, Google) — full lifecycle management of a task between agents, by passing
>   structured states such as "submitted", "working" and "completed". Strongly recommended for
>   communication and task hand-off between agents.
> - **ACP** (Agent Communication Protocol) — for advanced groups: **federated** communication in a
>   **zero-trust** configuration for multi-participant systems and swarm federations [9].

### 2.3.1 Division of responsibility among the agent's components

The agent architecture breaks into three components with distinct responsibilities. The local server
manages resources and asynchronous communication; the client engine runs the game logic and calls the
strategy model; and the language model supplies the linguistic and psychological layer.

**Table 1 — Division of responsibility among the agent's components and each component's integration
point**

| Component | Areas of responsibility | Integration point |
|---|---|---|
| Local FastMCP server | Resource management, exposing actions to the opponent, processing asynchronous responses | Use of decorators such as `@mcp.tool` to receive cryptographic signatures |
| Client engine | Game logic, calling the strategy model, turn timing | Connecting to the opponent's URL address and invoking its tools over the network |
| Language model (LLM) | Producing natural-language hints, decoding text, and prompt engineering for the psychological game | Access via API: local (Ollama) or cloud (Claude, Gemini) |

**An important distinction:** the language model does not **decide** legal moves — it produces the
rhetorical and deceptive layer of the game. Legal arbitration remains the responsibility of the
client engine and cryptographic verification, and therefore a verbal hint is never trustworthy in
itself. This rhetorical layer can be produced in one of four modes — from a free built-in template
bank (**zero tokens**, the default), through a local Ollama model, up to a cloud model or a CLI — as
detailed in Chapter 6 and in the language-model modes table in Appendix F.

### 2.3.2 A minimal FastMCP server

The code below shows the server's skeleton: creating a FastMCP instance, exposing a single tool that
receives a cryptographic signature from the opponent, and running the server. Note that the
`@mcp.tool` decorator is all that is needed to turn the `receive_move` function into an endpoint the
opponent can call remotely.

```python
from fastmcp import FastMCP

# Each agent runs its own server instance (local truth)
mcp = FastMCP("police_thief_peer")

@mcp.tool
def receive_move(signed_move: str, signature: str) -> dict:
    """Expose an action to the opponent over the network.

    The opponent (acting as a client) calls this tool to submit
    a cryptographically signed move. We verify the signature
    against the shared config before accepting the move.
    """
    is_valid = verify_signature(signed_move, signature)
    # Return an acknowledgement; never trust an unverified move
    return {"accepted": is_valid, "move": signed_move if is_valid else None}

if __name__ == "__main__":
    # Bind the server so a tunnel can expose it publicly
    mcp.run(transport="http", host="0.0.0.0", port=8000)
```

A full running implementation of a FastMCP server and client, alongside the complete game loop, is
available in the example code repository in Appendix D.

> ### Connection to the course
>
> This architecture is the direct extension of lecture L09 and of exercise `ex06`, in which two AI
> agents talked to each other over the MCP protocol and called external tools (for example Google's
> Gmail API). There you learned that an agent can be both server and client, and you ran external
> tool calls; here we turn the friendly conversation into a full competitive confrontation, in which
> every "statement" by the opponent requires verification. If in `ex06` the goal was conversation-
> based cooperation, in the project the goal is to beat an opponent that does not rely on you — and
> whom you do not rely on either.

## 2.4 Tunnelling and environment separation

For the agents to operate as independent entities against other groups across the internet — in the
live league discussed in Chapter 9 — running the servers on `localhost` is permitted **only** during
the early development stages. In practice, every group **must** expose its FastMCP server to the
public internet using a tunnelling tool such as ngrok [10] or Localtonet.

### 2.4.1 Why is a tunnel needed? NAT traversal

Most computers sit behind firewalls and network address translation (NAT), and are therefore not
directly reachable from the internet. A tunnelling tool produces a public **URL** that bypasses the
firewall and performs **NAT traversal** — a fundamental problem in peer-to-peer communication, which
protocols such as STUN were designed to solve by discovering the public address of a private host
[11]. The practical result: the opponent, anywhere in the world, can connect to your server remotely
through that public address.

**Figure 2.** A symmetric P2P structure: every agent is both a server (exposing tools with
`@mcp.tool`) and a client (calling the opponent's tools), and both sides are connected through public
URL addresses created by a tunnel over the internet.

*What the figure shows:* two identical agents in structure, Agent A and Agent B, each with a server
component and a client component, each exposed to the internet through a separate tunnel. *How to
read it:* the middle bidirectional arrow represents the public channel and NAT traversal; the curved
arrows show how one side's client calls a tool on the other side's server — full symmetry, with no
central server between them. *"What if" analysis:* if one of the tunnels drops, the opposing side
loses the ability to verify moves and reaches a **deadlock** in turn timing — so tunnel robustness is
an inseparable part of the game's robustness.

### 2.4.2 Total separation of the work environments

Beyond the tunnel, the architecture demands **total separation** of the work environments. It is
important to distinguish two stages: during the league game itself both groups are anyway separated
inherently — each runs on a different machine, in a different place — and so separation at that stage
is guaranteed automatically. The separation described here matters precisely at the **local
development stage**, when one team builds both the cop and the thief on the same machine; there the
risk of accidental overlap (memory or shared variables) is real, and it may mislead development and
show behaviour that will not be reproduced at all in the league. The cop code and the thief code must
therefore run in **two separate processes**, under fully separate configuration directories — for
example `config/thief/` versus `config/police/` (the configuration file structure is detailed in
Appendix B); and in line with that separation, submission itself is made in two separate repositories
— cop and thief — as detailed in Appendix C. Any attempt to share memory or read shared variables is
not merely a technical bug; it is a violation of the very principles of decentralisation, since it
creates a "back door" through which one agent could see its opponent's local truth.

> ### Binding separation rule
>
> The cop code and the thief code **must** run in two fully separate processes, under separate
> configuration directories (`config/thief/` versus `config/police/`). It is **forbidden** to share
> memory, to link a shared module holding live state, or to read variables shared between the two
> sides. Such sharing gives one side access to the other's "local truth", breaks the architecture's
> **zero-trust** model, and invalidates the solution — even if the game technically "works".

## 2.5 Chapter summary

We saw that the project completes the decentralisation of state management: there is no central
server, and in its place a P2P network in which each peer holds local truth and verifies moves
cryptographically. The MCP protocol, implemented in FastMCP, turns each agent into server and client
simultaneously, while the language model adds the psychological layer. Exposing the server through a
tunnel solves NAT traversal, and process separation plus configuration guard the integrity of the
zero-trust model. In the next chapter we move from the communication infrastructure to the trust
layer itself — the cryptographic mechanisms that let a move be verified against an opponent we do not
rely on.

---

# 3. Physics mechanics, the board and the scoring system

## 3.1 Chapter goals

By the end of this chapter you will know: how a discrete geometric space and a simple set of rules
define a complete confrontation arena; why enlarging `[board size]` (relative to earlier 5×5 versions)
inflates the state space exponentially and frustrates an exhaustive scan; how the advantage of barrier
placement turns the cop into an architect of space; and how a compact scoring table translates a
strategy — heuristic, your own dedicated algorithm, or optionally reinforcement learning — into a
maximisable **reward signal**.

## 3.2 A discrete space and a shared physical contract

Unlike continuous physical simulations, the game takes place in a **discrete** geometric space: a
finite grid of cells in which every position, every move and every mark is exactly countable. But
where do the laws of physics come from when there is no central server enforcing them? Here the
essential design decision of the project is hidden: there is **no external judge** — the laws of
physics are enforced by the agents themselves, each in turn, according to a pre-agreed configuration
file — `config/game.json` — which is shared in full identity between the two sides.

That file is the game's **contract**: board dimensions, starting points, barrier quota and the
scoring figures are encoded in it as hard values. Since both agents load exactly the same file, both
compute the same transition function and the same termination conditions — which pre-empts any
argument about "what the rule is" before play begins. The full structure of the file is detailed in
Appendix B.

> ### The contract is set by negotiation
>
> The game contract is not written from above but set by **negotiation** between each pair of groups,
> and may therefore vary from pair to pair. A necessary condition is that the contract is mutually
> agreed on both sides. That said, it is **forbidden** to weaken or dilute the instructions defined
> in this book: the agreed contract is a floor and not a ceiling. Conversely, groups **are** entitled
> to upgrade the rules — and it is even wise to do so; it is permitted and even desirable to
> **legally exploit any gap not defined here**, for the benefit of both sides or for competitive
> advantage — as long as everything is legal and mutually agreed between the sides.

## 3.3 Board dimensions and starting points

The board default is a grid of size `[board size]` (default 7×7 cells). This enlargement, relative to
earlier versions that used 5×5, is not cosmetic: it enlarges the number of possible state
combinations exponentially. The Dec-POMDP state space (see Chapter 1) grows as the product of both
agent positions and of every possible barrier layout; squaring the board edge raises the number of
cells to the fourth power, and the state space by orders of magnitude. The practical outcome is that
an exhaustive **brute-force** scan of all states becomes computationally infeasible — a difficulty
essential to problems in the Dec-POMDP class [2] — and hence the sides are forced to turn to learning
and heuristics instead of enumerating every state.

**The coordinate system.** Every cell is represented by a pair `(row, col)`. Two agreed parameters
determine how to read that pair: `[axis-system origin]` — the corner in which cell `(0,0)` sits,
default the **top-left** corner (the row axis grows downwards); and `[axis start index]` — the number
each axis begins counting from, default 0 (zero-indexed). Both parameters are subject to negotiation,
but they **must be identical between the sides**: groups that prefer 1-indexing or an origin in a
different corner may agree on that, but if one side counts from 0 and the other from 1, `[3,3]` for
one is not `[3,3]` for the other, and the race falls apart. In this book — and as the default —
implementation of the reference: origin top-left and counting starts at 0; hence the centre of a 7×7
board is `[3,3]` and the corner is `[0,0]`.

The opening points are not random but strategic, and are not fixed in advance: they are set during
the negotiation stage between the two groups, and any legal layout agreed between the sides is
permitted. The layout in which the thief (THIEF) stands at the centre of the board and the cop (COP)
in the corner is an **example** only: a thief at the centre enjoys a maximal number of escape routes
in all directions, while the cop is placed at a defined strategic distance. These positions are
documented in `[opening position – thief]` and `[opening position – cop]` (for example `[3,3]` for the
thief and `[0,0]` for the cop, zero-indexed), are loaded from the file `config/game.json`, and their
exact values are collected in the parameter table in Appendix F. The initial balance of forces can
thus be changed, in line with what is agreed between the sides, without touching the agents' code.

**Figure 3.** A board of size `[board size]` (in the example 7×7, zero-indexed): in the example
layout the thief (T) stands at the centre `[3,3]`, the cop (C) in the corner `[0,0]`, and a number of
barriers (B) the cop has placed. The orange arrow illustrates the legal move set — one cell to each
of the four orthogonal directions, or standing still.

*What the figure shows:* a grid of 49 cells, both agents in their opening positions, a chain of
barriers that has begun to close, and an orange star from which four arrows go out to the adjacent
cells. *How to read it:* the arrows define exactly which transitions are legal from a cell — north,
south, east, west, or stay; there are no diagonals. The barriers (B) are black cells no one may
cross. *"What if" analysis:* had the board been 5×5, the thief at the centre and the cop in the
corner would have been only a few steps apart, and the chase would have been almost decided
immediately; it is precisely the expansion to the current `[board size]` that produces the space
needed for a long chase, for learning, and for manoeuvre.

## 3.4 Movement, barriers and spatial engineering

On every turn an agent may perform a single move: move one cell in one of the four orthogonal
directions (up, down, left, right), or choose to stay in place. **Diagonal movement is forbidden.**
This simple constraint is what gives the chase its network character, and connects it directly to the
"cops and robbers" family of problems and to the pursuit-evasion variant on graphs, studied
mathematically in graph theory [12], [13].

The cop stands on an asymmetric advantage in spatial engineering: on a turn in which it **forgoes
movement**, it may place a physical barrier on any cell one step away from it — the cell it stands on
itself, or one of the four orthogonally adjacent cells. This ability turns it from a passive pursuer
into an architect of the arena.

> ### The barrier rule
>
> On a turn in which the cop forgoes movement, it may place a barrier on any cell one step away from
> it — the cell it stands on, or one of the four orthogonally adjacent cells — and the cell becomes
> **impassable to both players** until the end of the game. A barrier has no reverse: a cell that has
> been blocked stays blocked.
>
> **A capturing placement:** if the cop places a barrier on the cell the thief is standing on, at that
> moment the thief is captured. Likewise, a thief trapped with no legal move at all (all adjacent
> cells blocked by barriers and/or the board edges) is also considered captured.
>
> **Declaration duty:** the cop must declare truthfully every barrier placement and its exact
> location; a barrier may not be placed in hiding, and the cop is forbidden to lie about its
> location. The maximum barrier quota for the cop is `[barrier quota]`, and therefore every placement
> is a resource-management decision: the cop must "squeeze" the thief into a corner without
> accidentally blocking its own access routes.

`[barrier quota]` is the heart of the cop's strategic challenge. A greedily placed barrier may lock
the cop itself behind a wall it has built, or open a new escape gap for the thief. Managing this
resource — when to block, where, and how many barriers to keep for the closing stage — is a strategic
problem in its own right, discussed at length in Chapter 6.

> ### Iron rules: movement and truthful declaration
>
> **No diagonals.** A diagonal move is not legal; an attempt to perform one is rejected by the
> opposing agent, which enforces the physics. **Duty of truth on capture.** When the cop declares a
> **capture claim**, the thief is under a **cryptographic duty** to answer truthfully (the capture
> protocol). An attempt to lie at this stage will necessarily be revealed at the **log-audit** stage
> and will lead to total systemic disqualification. **Open barrier declaration.** The cop must
> declare truthfully every barrier placement and its exact location; a barrier may not be placed in
> hiding, and lying about its location is forbidden. A full mapping of all the binding game rules —
> do, do not, and recommendations — is collected in Appendix E.

## 3.5 Win conditions and the scoring table

The scoring system balances two opposing tensions: the difficulty for the cop of locating a hidden
player, against the difficulty for the thief of surviving in an increasingly hostile, closing
environment. Instead of a binary victory, every end scenario awards each side a different score, and
thereby encodes the **value** of every outcome — a translation from which the reward function R of the
previous chapter is derived directly.

**Table 2 — Scoring table: win conditions and point allocation**

| End event | Win condition | Cop score | Thief score |
|---|---|---|---|
| Successful capture | The cop lands on the thief's cell and declares a Capture Claim | `[capture score – cop]` | `[capture score – thief]` |
| Prolonged survival | The thief survives `[survival threshold]` valid steps with no capture | `[survival score – cop]` | `[survival score – thief]` |
| Technical loss | A side crashes, exceeds time, or commits cryptographic forgery | 0 | 0 |

Note the broken symmetry in the table. A capture awards the cop the highest reward (`[capture score –
cop]`), and embodies its principal aim; but prolonged survival — patience in time of `[survival
threshold]` valid steps with no capture — awards the thief **its** highest reward (`[survival score –
thief]`). A technical loss zeroes both sides alike, thereby incentivising both to preserve protocol
correctness rather than to win "on a timeout".

At the moment of a capture declaration, as noted, the thief is under a cryptographic duty to answer
truthfully. A capture declaration is therefore not a question of trust between opponents but of a
proof verifiable after the fact: every answer is signed and recorded in the log, and any attempt to
deny a true state will be revealed at the log-audit stage and will lead to disqualification. Scoring
thus turns from a declaration by the opponent into a mathematically enforceable fact.

> ### Connection to the course
>
> These simple rules — a finite grid, a single orthogonal move, a known barrier quota, and an
> unambiguous reward signal (the scoring table) — define a **finite, distributed** game in which two
> agents coordinate their actions with no central server and no referee. That is exactly the space
> discussed in *Orchestration of AI Agents*: in lecture L09 we saw two agents conversing over MCP and
> calling external tools, and in lecture L11 we saw a distributed agent swarm coordinating itself with
> no central control. The question of how one converts the scoring table into a game strategy — via
> heuristics, your own dedicated algorithm, or, as **one** possibility only, reinforcement learning —
> is opened in Chapter 6.

## 3.6 Chapter summary

We defined the physical arena of the chase: a discrete space of `[board size]` cells, in which the
laws of physics are enforced by the agents themselves according to a shared configuration contract
set by negotiation between the sides. We saw that expanding from an early 5×5 grid inflates the state
space and frustrates an exhaustive scan; that `[barrier quota]` turns the cop into an architect of
space under a resource-management constraint; and that an asymmetric scoring table translates every
end scenario into a maximisable reward signal. In the next chapter we move from the static rules to
the dynamic strategies the agents deploy to win in this arena.

---

# 4. Dynamic pheromone trails and collective swarm memory

## 4.1 Chapter goals

By the end of this chapter you will know how a simple biological mechanism — dispersing scent trails
and their dissipation — solves, at least partly, the partial-observability problem presented in
Chapter 1. You will understand what **stigmergy** is and why it constitutes an **indirect**
coordination mechanism between agents; you will master the mathematical model of emission and decay
of scent strength in each cell; and you will see how **each agent** leverages its opponent's
historical scent map to expose deceptive verbal hints and to strengthen a probabilistic belief map.

## 4.2 Indirect coordination by changing the environment

How do millions of ants coordinate among themselves with no central commander, no language, and no
shared memory? The answer, discovered by researchers of animal behaviour, is hidden not in the ants
themselves but in the **environment**. Every ant leaves behind a trail of pheromones, and every other
ant reacts to them. The environment itself becomes the shared noticeboard — a mechanism named
**stigmergy**, indirect coordination by changing the environment [14], [15]. That principle, which
underlies the famous ant-colony algorithm [16], is exactly the tool harnessed here to attack
uncertainty.

One of the central contributions to solving our partial-observability problem is, then, the
scent-trail mechanism — a mechanism that drew direct inspiration from the behaviour of ants. The idea
is simple and strong at once, and it is **entirely symmetric**: when an agent moves on the board —
both cop and thief — it scatters behind it **virtual pheromones** that fade with time. No agent sees
this as intentional communication; but its **opponent**, reading the environment, turns this physical
trail into a source of high-value information. The scent is **natural and uncontrollable**: it is
emitted by the very act of movement or of lingering, and no one can plant a misleading trail
somewhere they have not been; all an agent can do is strengthen the scent in the cell it is actually
in, by lingering or returning to it, and that is a cost and not an advantage, since it helps the
opponent locate it. Each side emits its own scent, and each side reads the scent field of its
opponent only.

### 4.2.1 What was taught in lecture L11: dynamic pheromones and swarm memory

The mechanism described here is exactly what was taught in lecture L11 of *Orchestration of AI
Agents*. Instead of central control, the agent swarm coordinates itself through **dynamic pheromone
trails** that encode the contextual efficacy of each action (a successful action updates the swarm's
shared representation — the embedding — and thereby raises the probability of choosing successful
routes in later rounds) — this is **collective memory**, inscribed in the environment rather than in a
single agent's head. Alongside it operates a **decay/fading** mechanism that prevents ossification:
without it the swarm would be locked into a local optimum, because old trails would accumulate for
ever and silence every exploration of new routes. The scent field and the decay rule we define below
are the direct translation of that idea into the cop-and-thief arena.

> ### Connection to the course
>
> In lecture L11 of *Orchestration of AI Agents* we saw a swarm of agents coordinating itself
> **without central control** through **dynamic pheromone trails** and the swarm's **collective
> memory** (in the style of SwarmSys): successes update a shared representation, and a decay mechanism
> prevents ossification in a local optimum. The scent-trail mechanism in this project is the direct
> application of that same idea — indirect and asynchronous coordination, in which a message is not
> sent to anyone but inscribed in the shared environment and waits there for whoever knows how to read
> it. Understanding this pole, alongside the direct coordination we saw in earlier lectures, is
> essential for anyone designing autonomous agent systems.

## 4.3 The emission and decay model

Every time an agent moves or stays in place, a **scent field** of size `[scent field size]` (say 5×5)
is created around its position. At the emission centre — the cell the agent is on — scent strength is
set by `[scent strength at focus]`. The further one moves from the centre, the lower the strength,
falling by a radial distribution: nearby cells absorb high strength, and cells at the edge of the
scent field absorb only a faded remnant. The result is a **concentrated scent signature** marking the
agent's neighbourhood rather than only an isolated point. This holds for both sides equally — cop and
thief both leave a scent field of their own.

At the end of every full turn — that is, after the cop **and** the thief have both completed their
move — all the scent trails existing on the board pass through a process of systemic **decay**. The
decay rate is `[scent decay rate]` per turn. The mathematical update of scent strength in cell (i, j)
is given by:

> **Scent-strength update in a cell**
>
> τᵢⱼ(t + 1) = max( 0, (1 − ρ) · τᵢⱼ(t) + Δτᵢⱼ )

The variables making up the formula break down as follows:

- **τᵢⱼ(t) — scent strength in the cell at the current time.** A continuous value in [0, 0.9]
  expressing how "fresh" the trail in cell (i, j) is. *Practical meaning:* it is in effect the local
  certainty score — a high value hints that the agent whose field we are reading passed here not long
  ago.
- **ρ — decay rate.** Here ρ = 0.10, so the factor (1 − ρ) leaves 90% of the existing scent each turn.
  *Practical meaning:* slow decay is a deliberate planning choice — it leaves a historical trail long
  enough to be tactically useful, but not eternal.
- **Δτᵢⱼ — the new emission.** The strength added to the cell in the current turn, set by the cell's
  radial proximity to the agent's emission centre (and at the centre itself Δτ = 0.9). If the agent is
  far away, Δτᵢⱼ = 0. *Practical meaning:* this is the component connecting the agent's presence with
  the environment — it "writes" to the board.
- **max(0, ·) — clipping at zero.** Guarantees that scent strength is never negative. *Practical
  meaning:* a cell that never absorbed scent, or that has fully decayed, is simply "quiet" — an
  absence of information, not negative information.

The formula embodies a tension between two forces: the component (1 − ρ)·τᵢⱼ(t) is **forgetting** —
the gradual erasure of the past; and the component Δτᵢⱼ is **memory** — the inscription of the
present. The balance between them determines how deep into the past each agent can look at its
opponent's trail.

**Figure 4.** The emission field of size `[scent field size]` around the agent (thief or cop): at the
centre τ = 0.9, and strength decays radially with distance from the centre.

*What the figure shows:* a 5×5 matrix of cells, where the central cell — the emitting agent's
position — is coloured brightest and carries the value 0.90, and the cells around it darken the
further away they are. *How to read it:* brightness represents scent strength τ; the radial fall means
the scent is not a uniform "stain" but a hill whose peak is at the centre. A cell at the corner of the
square receives only a faint remnant, and the cop therefore attributes low certainty to it. *"What if"
analysis:* had emission been pointwise (a single cell at strength 0.9 and zero around it), small
measurement noise would have erased the whole signal; the radial distribution gives the mechanism
robustness, since even if the exact cell is missed, its neighbours still mark the direction.

## 4.4 Tactical use of the scent map

Because scent fades slowly, it leaves behind it a historical **scent trail** — not a snapshot but a
short film of the agent's movement over the last few turns. Every agent can sample the board and
receive the scent map of **its opponent**. Here the step up occurs: crossing that map with the same
opponent's verbal declarations permits **belief modelling** — the ability to strengthen a
probabilistic distribution over the opponent's true position [17]. Full symmetry: the cop reads the
thief's trail, and the thief reads the cop's trail — each side crosses its opponent's scent map
against the verbal hints that opponent supplies.

The next figure illustrates why such a trail survives long enough to be useful.

**Figure 5.** Development of scent strength τᵢⱼ over turns for ρ = 0.10: a single emission and
thereafter pure decay (the trail), against re-emission while the agent lingers.

*What the figure shows:* two curves. One ("single emission") falls exponentially from 0.9 — this is a
cell the agent passed through once and abandoned. The second ("re-emission") stays high as long as the
agent remains in the neighbourhood (turns 1–8), and only after it leaves does it begin to decay. *How
to read it:* the dashed middle line marks half the peak strength; one can see that the single trail
crosses it only around the seventh turn — that is, the scent stays "legible" for roughly six or seven
turns. *"What if" analysis:* had we doubled ρ to 0.20, the curve would have plunged much faster, the
trail would have shortened, and the pursuing opponent would have lost memory of the past; had we
reduced ρ to nearly zero, the board would have filled with eternal scent and lost the ability to
distinguish old from new.

> ### Exposing a lie: the thief "moves north" while the scent is in the south-east
>
> Suppose the cop samples the board and receives the following scent map, concentrated in the
> south-east corner:
>
> - south-east cell (1,4): τ = 0.81 (a very fresh trail).
> - adjacent cell (1,3): τ = 0.63.
> - all cells in the north of the board, e.g. (5,2): τ = 0.00 — entirely empty of scent.
>
> Now the thief's verbal declaration arrives: "I moved north". Let us test the claim quantitatively.
> Had the thief moved north on the last turn, we would expect to find in the north a fresh trail at
> strength about (1 − ρ)·0.9 = 0.9 · 0.9 ≈ 0.81. Instead we measure τ = 0.00 in the north. The gap
> between expected (≈ 0.81) and measured (0.00) is absolute: there is no remnant of scent to support
> the claim, while the entire scent mass is concentrated at the opposite pole of the board.
>
> The cop therefore concludes, with high confidence, that the thief **is lying**. It lowers the trust
> coefficient it attributes to verbal declarations, updates its probability matrix so that most of the
> weight goes to the south-east cells, and re-aims its pursuit vector — not towards the declared
> north, but towards the true scent source. The thief's manipulation thus turns into a double-edged
> sword: the very attempt to deceive, while it is hidden by the evidence of the environment, betrays
> its position.
>
> It is important to stress: the scent map **cannot lie** — it is emitted by the very act of movement
> and is not forgeable. What is exposed here is a **verbal** hint, caught out precisely because the
> environment contradicted it — and not a "lying trail" (no such thing exists). And full symmetry: the
> same process is available to the thief, which crosses the cop's scent trail against the hints the cop
> supplies — each side defends itself by verifying the opponent's words against the unforgeable
> evidence left in the environment.

Updating the full probability matrix — exactly how each agent translates its opponent's scent map and
declaration into a numeric belief map, and how it combines the two pieces of evidence by Bayes' rule
— is detailed in Chapter 6, where we build the **belief** mechanism on the foundations of the present
chapter; this belief map is displayed visually as a heat map in the live interface (Chapter 7).

## 4.5 Chapter summary

We saw how a biological principle — the stigmergy of ants — is translated into an applied mechanism
that eases the partial-observability problem. We defined the emission model of size `[scent field
size]` with `[scent strength at focus]` and a radial distribution, and the decay rule τᵢⱼ(t+1) = max(0,
(1−ρ)τᵢⱼ(t) + Δτᵢⱼ) with ρ = 0.10. We stressed that the mechanism is **symmetric** — both agents emit
scent and each reads its opponent's trail — and that the scent is natural and unforgeable. We saw that
this slow decay produces a historical trail some six turns long, and that crossing it with the
opponent's verbal declarations lets each agent expose deceptive hints. In the next chapter we move
from the trail an agent leaves in the environment to the channel in which it speaks explicitly — and
we examine how verbal communication itself is built, on its questionable reliability.

> ### Cryptographic locking of the emission and decay model before a series
>
> **Before a series opens**, the two groups must exchange between them the **emission and decay
> model** in full — including a **concrete numeric example** (for example: a cell at the centre
> receives τ = 0.9, and after one turn of decay at rate ρ receives 0.9 · (1 − ρ)). The sides must
> verify that they interpret the same formula in exactly the same way, and only afterwards **lock**
> the agreement **cryptographically** — for example by means of a SHA-256 hash of the agreed formula
> together with the numeric example. Any future deviation in the mechanism's behaviour will thus be
> discovered immediately. It is **permitted and even recommended** that one group give the other the
> **shared scent mechanism code** itself, so as to guarantee that both sides run exactly the same
> behaviour — and leave no room for interpretation that would harm the fairness of the series.

---

# 5. Cryptographic security protocol and zero-knowledge

## 5.1 Chapter goals

By the end of this chapter you will know: why a peer-to-peer network with no referee, and without an
objective game manager, suffers a built-in temptation to cheat; how the **commit-reveal** mechanism
based on hash functions turns cheating into something practically impossible; how a mutual audit of
the game logs reveals every forgery after the fact; and how a signed hardware declaration at "step
zero" guarantees computational fairness between competitors with machines of very different power.

## 5.2 The temptation to cheat in a referee-less network

Imagine a chess game in which there is no shared physical board and no supervisor overseeing the
rules; each player holds a private copy of the board and reports its moves to the other. In a
distributed system of this kind — a peer-to-peer (P2P) network in which the two agents talk to each
other directly over a FastMCP server, with no objective game manager — a built-in temptation to cheat
is born. Three kinds of fraud threaten the integrity of the race: **time travel** — changing a move
already made; changing a move **after** the opponent's move is revealed; and denying a position or an
earlier declaration. As long as each side is both the player and the recorder of its own protocol,
nothing stops it rewriting history in its favour.

The solution is not judicial but mathematical. Instead of relying on trust, the system rests on the
**commit-reveal** mechanism, based on cryptographic hash functions. The founding idea, known in the
literature as "coin flipping by telephone" [18], is this: each side is required to **commit** to its
decision while it is still sealed and closed, and only after the opponent has locked in its own is the
decision **revealed**. This removes the possibility of changing a choice after the fact, since the
change would break the cryptographic signature already transmitted.

> ### Connection to the course
>
> In the course *Orchestration of AI Agents*, in lecture L09, you saw how two AI agents talk to each
> other over MCP and call external tools — two independent processes exchanging messages directly, with
> no central component supervising them. This chapter adds to that same architecture of agent-to-agent
> tool calls its **integrity** layer: when there is no trustworthy central server dictating one truth,
> the need to ensure the integrity of distributed communication must derive from cryptography itself.
> That is the principle distinguishing a **fragile** distributed system from a **reliable** one.

## 5.3 The commit-reveal mechanism over SHA-256

At every game step each agent performs four mandatory cryptographic stages, in order. These stages
turn every move into an **obligating event** that cannot be denied or changed after the fact.

> ### Nonce — a number used once
>
> A **nonce** (short for *number used once*) is a unique random string created afresh for every
> commitment. It has a double role. First, it guarantees that if an agent repeats exactly the same
> action, the resulting hash will be different every time. Second, it frustrates a **dictionary
> attack** — an attempt by the opponent to guess the sealed content by pre-hashing all the plausible
> possibilities. Without a nonce, the small move space would allow every commitment to be cracked in a
> fraction of a second.

### 5.3.1 Stage 1 — Commit

The agent chooses its physical move and the hint it will send (including the **Intent** flag stating
whether the hint is truthful or a lie), and draws a unique **nonce**. The four data components are
concatenated together and encoded into a single cryptographic hash. The agent transmits, via the
FastMCP server, the signature H_commit **only** — not its content.

> **The cryptographic commitment signature**
>
> H_commit = SHA256( State ‖ Move ‖ Intent ‖ Nonce )

The symbol ‖ is the **concatenation** operator: it glues the byte representations of the components to
one another into a single continuous string, before applying the hash function. It is not numeric
addition but adjoining of byte sequences. In the reference implementation the concatenation is done
by **canonical** JSON serialisation (sorted keys and fixed separators), so that both peers hash
**identical** bytes exactly; the record actually signed is richer than the four fields here and also
includes the verbal hint, the intent classification, the step number and the role. The formula's
variables break down as follows:

- **H_commit — the commitment signature.** A 256-bit string produced by the SHA-256 function [19].
  *Practical meaning:* this is the move's "fingerprint"; it is sent to the opponent but exposes
  nothing about its content.
- **State — the board state.** The state snapshot the move is based on, which fixes the commitment to
  a specific game step. *Practical meaning:* prevents reuse of an old commitment in a new context.
- **Move — the physical action.** The chosen move (movement, barrier placement, etc.). *Practical
  meaning:* this is the core one seeks to lock against change.
- **Intent — the intent flag.** A value stating whether the accompanying verbal hint is true (`truth`)
  or misleading (`lie`). *Practical meaning:* obliges the agent to declare its honesty in advance, so
  that it cannot later claim it "lied on purpose".
- **Nonce — a number used once.** A cryptographic random string. *Practical meaning:* guarantees hash
  uniqueness and frustrates a dictionary attack, as explained above.

### 5.3.2 Stages 2–4 — Acknowledge, Reveal, Audit

After the commitment the protocol continues with three further stages:

- **Acknowledge.** The opponent confirms it has received the commitment and is locked in on it. This
  acknowledgement prevents the sender withdrawing its commitment, and at the same time guarantees the
  reveal will occur only once both sides have already fixed their moves.
- **Reveal.** The agent sends the opponent the action (Move) and the verbal sentence. The **nonce**
  stays hidden at this stage, so as to prevent reverse-engineering of the signatures before time.
- **Final reveal / Audit.** Only at the end of the game are all the nonce values exposed, for a full
  mutual audit.

**Figure 6.** The message-exchange sequence between cop and thief across the four commit-reveal
stages: Commit → Acknowledge → Reveal → Audit. Note that the nonce is exposed only at the final audit
stage, at the end of the game.

*What the figure shows:* two vertical lifelines (Cop on the left, Thief on the right) and horizontal
arrows describing the message order from top to bottom. First the sealed commitment passes, then the
locking acknowledgement, thereafter the mutual reveal of the moves, and finally — at the end of the
game — the exposure of all the nonces. *How to read it:* the time separation between commitment and
reveal is the cryptographic heart; once H_commit is sent the move is mathematically **locked**, even
though its content is not yet known. *"What if" analysis:* if an agent tries at stage 3 to reveal a
move that does not match the commitment it sent at stage 1, the hash recomputed at the audit stage
will not match the original H_commit — and the cheating is exposed unambiguously.

The code below illustrates both ends of the mechanism: `commit()`, which creates the signature, and
`verify()`, which reconstructs and compares it. Note the use of the `secrets` module for drawing a
cryptographic nonce, and not `random`, which is too predictable.

```python
import hashlib
import json
import secrets

def commit(state: str, move: str, intent: str) -> tuple[str, str]:
    # Generate a fresh cryptographic nonce (defeats dictionary attacks)
    nonce = secrets.token_hex(16)
    # Serialize the fields as CANONICAL JSON (sorted keys, fixed separators)
    # so BOTH peers hash byte-identical input. The reference code seals a
    # richer record (hint, verdict, step, role, sub_game); the core is shown.
    payload = json.dumps({"state": state, "move": move,
                          "intent": intent, "nonce": nonce},
                         sort_keys=True, separators=(",", ":"))
    h_commit = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    # Send only h_commit now; keep nonce secret until the final audit
    return h_commit, nonce

def verify(state: str, move: str, intent: str,
           nonce: str, h_commit: str) -> bool:
    # Re-synthesize the opponent's hash from the revealed data
    payload = json.dumps({"state": state, "move": move,
                          "intent": intent, "nonce": nonce},
                         sort_keys=True, separators=(",", ":"))
    recomputed = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    # Any mismatch proves tampering occurred
    return secrets.compare_digest(recomputed, h_commit)
```

> ### The zero-knowledge frame
>
> The commit-reveal mechanism embodies the spirit of a **zero-knowledge** proof [20]: every agent —
> cop and thief alike — **proves** that it chose a legal move and fixed it, without exposing before
> time what the move is. At the commitment stage the opponent receives absolute certainty that a
> locked decision exists — but zero knowledge of its content. Only at the reveal is the content
> exposed, and only then can it be verified against the original commitment. Commitment is thus
> separated from disclosure.

## 5.4 Mutual audit and log integrity

The reliability of the whole system rests on a **post-mortem integrity check**. At the end of the game
the cop agent submits its full log, including the SHA-256 exposures of every step, and so does the
thief. Each side takes the opponent's State, Move, Intent and the exposed Nonce, **reconstructs** the
data, hashes it afresh, and compares the result against the signature declared at the commitment
stage. This principle, in which a short cryptographic fingerprint attests to the integrity of a whole
block of data, also underlies hash-based signature schemes [21]. This verification is realised
visually, step by step, in the replay simulator of Chapter 7.

> ### Forgery entails a technical loss
>
> Any mismatch between the recomputed hash and the hash declared at the commitment stage proves
> unambiguously that **tampering** occurred. There is no room here for interpretation or statistical
> doubt: the SHA-256 function is sensitive to every single bit, and therefore a tiny change in a move
> changes the signature entirely. The group takes a heavy **technical loss** — total loss of the game,
> irrespective of the result on the board. Cryptography, not human judgement, is what decides.

## 5.5 Step-zero and computational fairness

A competition between agents raises a question of justice: is it right that an agent running on a
modest laptop should compete on the same terms as an opponent running on a supercomputer able to
perform a deep tree search or run a heavy language model? **Computational fairness** requires that a
material advantage should not decide the race by itself — a principle that is weighted into the league
score (Chapter 9). Therefore, before the first move, **"step zero"** is performed.

At this step the agents gather their machine specification: the operating system (OS), the number of
processor cores and its frequency (CPU), the memory size (RAM), the presence of a graphics
accelerator and video memory (GPU/VRAM), and the name of the running language model. Alongside the
hardware specification, the step-zero declaration also documents the **code version**, the **group
name** and the **sub-game number**. The whole specification is packed into a JSON string and signed
cryptographically with a pre-supplied key, so that it cannot be forged after the fact. In parallel,
all the language model's **token** consumption is monitored and locked cryptographically too, in order
to prevent denial of the compute resources actually consumed.

> ### Mandatory: the commit identifier in the agreement declaration
>
> Alongside the hardware specification, each side declares at step zero also the **commit hash in
> GitHub** on which the code ran in that game. It is **permitted** to change, update and improve the
> code **between games** — but in every game it is **mandatory to record in the declaration the exact
> commit identifier that was played**, so that the examiner can reconstruct exactly the version that
> competed. This identifier is also included in the closing JSON file sent by email (the field
> `github_commit`, see Chapter 9).

In computing the league score a **normalisation** formula is applied that grants bonuses to
algorithmically efficient solutions — those that achieved good results with minimal resource
consumption. The incentive is thus reversed: not raw hardware power is rewarded, but the algorithm's
**sophistication**. A light and fast solution running on a modest machine and beating a heavy opponent
is a development victory over brute computational force.

## 5.6 Chapter summary

We saw that in a referee-less peer-to-peer network trust cannot be an assumption — it must be
**proven**. The commit-reveal mechanism over SHA-256 locks every move in a cryptographic signature
before its content is exposed, thereby frustrating time travel, after-the-fact change and denial. A
mutual audit of the logs at the end of the game exposes every forgery and punishes it with a technical
loss, while step-zero and the signed hardware declaration guarantee that fairness is preserved even
between machines of unequal power. The next chapter continues from the integrity layer to the strategy
layer: how an agent builds a belief map and takes good decisions under the uncertainty preserved here
honestly.

---

# 6. The strategy module and decision-making

## 6.1 Chapter goals

By the end of this chapter you will understand why the agent's driving logic must be independent and
must never rely on a language model for spatial computation; and you will know a range of alternative,
**equally weighted** paths for realising the movement policy — distance heuristics (Manhattan combined
with a Bayesian belief map), your own heuristic algorithm, and reinforcement learning as **one optional
possibility only**. It is important to stress: the course did **not** teach reinforcement learning, and
it is entirely possible to build a strong agent using heuristics alone, with no RL at all. **The
movement decision always remains in the algorithm's hands**; the language model is integrated not as a
navigation engine but as a behaviour analyser and a generator of computed text for the verbal game —
and that too with token consumption tunable down to zero.

## 6.2 Why a separate strategy module is needed

The simulator infrastructure built in earlier chapters — the central orchestrator (Chapter 8) — manages
the pipeline: passing messages, signature locking, and turn management. But note the essential
distinction: an infrastructure that knows how to **pass** a message does not know **what** to decide.
The agent's driving logic must be smart and independent, and must never blindly rely on a language
model — because language models tend to **hallucinate** in Cartesian spaces and to confuse directions,
distances and coordinates.

From this a clear development requirement follows: students must implement a **separate strategy
module**, connected to the **PeerRuntime** layer at a precise point — immediately after decoding the
incoming hint, and before packing the outgoing **Commit**. Between these two points sits the whole of
the agent's intelligence: updating the belief, choosing the legal move, and composing the deception
text. This separation is not architectural fastidiousness; it is the boundary dividing a generic
communication component from a thinking agent.

An example implementation of a minimal strategy module (**without** strategic depth, as an educational
starting point) is available in the code repository of Appendix D. In the reference implementation the
module is selected in the private configuration file, in the `[strategy]` section: the keys
`police_class` and `thief_class` point at **your** "brain" class, which inherits from `BrainBase` and
overrides `_pick_move` (and for the cop also `_decide_move` — barrier choice). Leaving the section empty
runs the built-in heuristic brain (see the strategy-module selection table in Appendix F and
`docs/STRATEGY.md`).

**Figure 7.** The decision flow inside the strategy module: the incoming hint is decoded, the belief map
is updated by Bayes' rule, the movement policy (heuristic, your own algorithm, or optionally Q) chooses
a legal move, the language model composes the deception text, and everything is packed into the Commit.

*What the figure shows:* a chain of five stages enclosed in a dashed box marking the strategy module's
boundary inside PeerRuntime — from the incoming hint (left) to the outgoing Commit. *How to read it:*
the Cartesian stage (choosing the move) and the verbal stage (the deception text) are clearly separated;
the language model receives the movement decision as a given fact. *"What if" analysis:* if the language
model were permitted to choose the move itself, a single Cartesian hallucination would translate
directly into an illegal or suicidal move; the separation guarantees the algorithm preserves move
legality with no dependence on the model.

## 6.3 Reinforcement learning — one optional tool

Before diving into details, let us stress: reinforcement learning is **one of the possibilities** for
realising the movement policy — an optional tool only, and not "what the course taught". The course did
**not** teach reinforcement learning at all, and many groups will build a winning agent with no RL, on
the basis of the two algorithmic paths described below: pure heuristics (Manhattan combined with a
Bayesian belief), or your own heuristic algorithm. In all three paths **the movement decision remains in
the algorithm's hands**, and the language model serves the verbal layer only. The chapter presents the
three paths as of equal value; the choice among them is the group's.

Since the grid is bounded to `[board size]` (default 7×7), the state space is finite — though very
large, given the combination of both players' positions and the barrier layout. That finiteness is the
condition that enables groups choosing this route to train the agent with classical reinforcement
learning methods, foremost **Q-Learning** [22], [23]. On this path the agent maintains a table (or
network) mapping every possible state to the weights of the actions available in it, and updates those
values by the **Bellman** equation [24].

> **Strongly recommended (further reading)**
>
> For groups wishing to go deeper into developing advanced victory tactics, it is **recommended** to read
> about the **AgentNet** environment for decentralised evolutionary coordination of LLM-based
> multi-agent systems [25] — an approach complementing the reinforcement-learning path with ideas of
> population evolution.

For groups choosing it, the Q-value update follows the Bellman equation:

> **Q update by the Bellman equation**
>
> Q(s, a) ← Q(s, a) + α [ r + γ · maxₐ′ Q(s′, a′) − Q(s, a) ]

The equation's components break down as follows:

- **Q(s, a) — the action value.** The current estimate of the accumulated reward expected from
  performing action a in state s. *Practical meaning:* this is the cell in the table the agent updates
  and out of which it chooses its continuation.
- **r — the immediate reward.** The reward received right after the action, derived directly from the
  scoring table. *Practical meaning:* capture or survival translated into a concrete number driving the
  learning.
- **α — learning rate.** α ∈ (0,1] sets how much weight is given to new information against accumulated
  knowledge. *Practical meaning:* an α that is too high causes volatility and forgetting of previous
  experience; one that is too low slows convergence.
- **γ — discount factor.** γ ∈ [0,1) sets the importance of the future reward — long-range capture or
  survival — against immediate scoring. *Practical meaning:* a high γ encourages strategic patience,
  e.g. building a barrier trap over many turns.
- **maxₐ′ Q(s′, a′) — the optimal future value.** The best estimate of the reward from the next state
  s′. *Practical meaning:* here future knowledge is "bled" back into the present, and lets the agent
  plan beyond a single step.

To avoid getting stuck in fixed loops during the chase, an **epsilon-greedy** mechanism is combined:
with small probability ε the agent chooses a completely random action instead of the action with the
highest Q-value. This mechanism encourages **exploration** of new escape or pursuit routes and prevents
over-**exploitation** of a policy caught in a loop.

Whoever chooses the RL path will notice that the project has a thinking opponent, and therefore — if you
used reinforcement learning — it is in fact a case of **multi-agent reinforcement learning** [26], [27],
in which the learning environment itself changes as the opponent learns and improves. That said, this is
one path among several, and it is not necessary.

### 6.3.1 Two equal alternatives without RL

Reinforcement learning is, as noted, one possibility only. Two further paths, of equal value, allow a
strong agent to be built without it — and in both, as in RL, the movement decision remains entirely
algorithmic:

- **Pure heuristics (Manhattan + Bayes).** One may entirely forgo learning and rely on a deterministic
  decision rule: update the belief map by Bayes' rule, and then choose on every turn the legal move that
  minimises the Manhattan distance to the cell of highest belief. This is a simple, transparent path,
  easily debugged — and often competitively close to RL. This is the default policy of the reference
  implementation.
- **Your own heuristic algorithm.** One may plan a richer movement policy combining the belief map, the
  scent maps, exploitation of barriers, and forward search (for example minimax or expectimax against
  the opponent's belief) — all in deterministic and transparent code. Here too there is no training
  stage, and the spatial logic stays in your hands and not in the language model's.

The three paths — RL, heuristics, and your own algorithm — are equal-rights citizens for the movement
policy; in all of them the spatial decision remains algorithmic, and the language model separately
serves the verbal game, as described in the rest of the chapter. Choose the one matching the group's
resources and style.

```python
import random

def q_update(Q, s, a, r, s_next, actions, alpha=0.1, gamma=0.95):
    # Bellman update: blend old estimate with the observed target
    best_next = max(Q[(s_next, a2)] for a2 in actions)   # max_a' Q(s',a')
    td_target = r + gamma * best_next                    # r + gamma * max Q
    td_error = td_target - Q[(s, a)]                     # temporal-difference
    Q[(s, a)] += alpha * td_error                        # move toward target
    return Q[(s, a)]

def choose_action(Q, s, actions, epsilon=0.1):
    # epsilon-greedy: explore with prob epsilon, else exploit the best Q
    if random.random() < epsilon:
        return random.choice(actions)                    # exploration
    return max(actions, key=lambda a: Q[(s, a)])         # exploitation
```

## 6.4 Distance heuristics and the belief heat map

The two sides are entirely symmetric: neither of them sees its opponent's true position. Each side knows
where it itself is, and receives **the opponent's scent map** (each side senses the other side's scent
field, not its own) and a verbal hint that may be a lie. Each side therefore builds a **belief map** of
its own: a matrix of size `[board size]` (say 10×10) representing the statistical probability that the
hidden opponent is in each cell [17]. Thus the cop builds a belief over the thief's position out of the
scent map and the hints it received; and symmetrically the thief builds a belief over the hidden cop's
position out of the cop's scent map and its hints, and uses it to plan an **escape** route. On every
incoming hint the side applies Bayes' rule to update the probabilities, placing a **reliability**
coefficient on the text — since the text may be a lie. The cop then seeks to **minimise** the Manhattan
distance to the cell of highest probability, while the thief seeks to maximise it and get away.

> **Manhattan distance on an orthogonal grid**
>
> D = |x_cop − x_target| + |y_cop − y_target|

The formula's components break down as follows:

- **(x_cop, y_cop) — the cop's position.** The agent's known coordinates. *Practical meaning:* this is
  the only certain component of the equation.
- **(x_target, y_target) — the target cell.** The cell of highest belief, taken from the belief map,
  arg maxₛ b(s). *Practical meaning:* the target is not the "true" thief but the best probabilistic
  guess about it.
- **D — Manhattan distance.** The sum of the absolute differences on both axes. *Practical meaning:*
  this function suits orthogonal movement on a grid where there is no diagonal movement, and it is
  therefore an **admissible** estimate of the minimal number of steps.

> ### A movement decision by Manhattan distance
>
> Suppose the cop stands at cell (2,2), and the belief map places the probability peak at cell (5,5).
> Then D = |5−2| + |5−2| = 3+3 = 6. Among the legal actions, east (3,2) gives D = 5 and north (2,3) also
> gives D = 5, while west (1,2) gives D = 7. The agent will therefore choose the eastern or northern
> move — both minimise D by one step — and will prefer between them by the Q-value. Thus the
> probabilistic logic (choosing the target) and the learning logic (choosing the move) combine.

**Figure 8.** A Bayesian belief map of size `[board size]`: every cell coloured by the probability b(s)
that the hidden opponent is in it, after a Bayes update on a scent hint. Shown here is the cop's map
(belief over the thief); the thief holds a symmetric map of its own (belief over the cop). The star
marks arg maxₛ b(s), the blue square marks the position of the side holding the map, and the dark
squares are barriers with zero belief.

*What the figure shows:* a grid of size `[board size]` in which the probability concentration (the
brighter shade) centres around a single cell, while the rest of the board carries a uniform low belief;
the map holder and the barriers are marked separately. Recall that both sides hold such a map — the
cop's over the thief and the thief's over the cop. *How to read it:* the star is the target to which the
Manhattan distance will be aimed (for the cop) or from which one will move away (for the thief); the
brightness expresses the certainty that remained after the update. *"What if" analysis:* if a new hint
contradicts the previous one, the probability mass is reinterpreted — the peak may migrate or split into
two foci, and the cop will be forced to decide which direction to aim at first.

## 6.5 Language-model integration for prompt engineering

Even though the spatial logic is handled entirely by the algorithm, the language model remains critical
to the **verbal** game. The strategy module instructs the client to use a **tool** against the FastMCP
server to collect data, builds a rich **prompt** including the statistics and the scent maps, and sends
it to the language model to compose computed deception text — or a psychological analysis of the
opponent's language. The language model thus acts as a **bluff classifier** and a behavioural profiler,
while the algorithm preserves the legality of movement. This division of labour — language to the model,
space to the algorithm — is the heart of the agent's planning, and rests on the attention capabilities of
the **Transformer** architecture [28].

> ### Do not rely on a language model for spatial reasoning
>
> Never pass to the language model the decision on the movement step itself. Language models tend to
> **hallucinate** when computing coordinates, directions and distances in Cartesian space, and are
> liable to return with full confidence an illegal move, a move that collides with a barrier, or a move
> that moves away from the target [29]. The model's role is verbal only: composing text, classifying
> bluffs, and profiling. Spatial arbitration is reserved for the algorithm, which is the only thing
> capable of guaranteeing mathematical legality.

Despite the blanket prohibition above, a **single exception** is defined — conditional on the express
agreement of both sides — which justifies separate treatment.

> ### An exception by mutual agreement: a language-model-based tactic
>
> The default and the recommendation remain unambiguous: the decision on the move is **algorithmic**,
> and the language model serves the verbal layer only. That said, as part of the rules system, which is
> subject to negotiation, **both sides may agree in advance** — at the pre-game negotiation stage — to
> permit also a **language-model-based tactic** for deciding the move, instead of exclusive reliance on
> the algorithm. This permission is valid **only** by express and documented mutual agreement between
> the groups; one side may not adopt such a tactic unilaterally. Even under such an agreement, the local
> algorithm must still enforce the legality of the move (and reject any illegal move the model
> proposes), and the risk of spatial hallucinations — as described in the warning above — remains the
> responsibility of the group that chose it. The reference implementation and the default of the book
> remain algorithmic.

### 6.5.1 How the bluff text is produced — four operating modes

Since the movement decision is entirely algorithmic, the language model is required **only** for the
verbal layer — and therefore the choice of how to operate it is mainly a question of **budget**: how
many tokens out of `[token estimate per series]` you are willing to spend on speech. The reference
implementation offers four modes, selected in the private configuration file (`[trash_talk] provider`;
full detail in the language-model modes table in Appendix F):

- **`template`** — **the default.** Ready deception sentences, chosen in advance in Python code, with no
  network dependence. This is **zero tokens**. This is the recommended path: it directs full attention
  to the movement algorithm.
- **`ollama`** — a **local** language model via Ollama (e.g. at `localhost:11434`) — zero API tokens and
  no rate limit.
- **`claude_api`** — a small cloud model (e.g. Haiku) through the API — real consumption counted against
  `[token estimate per series]`, subject to the account's rate limit.
- **`claude_cli`** — running `claude -p` through the Claude Code CLI — the highest cost, subject to a
  subscription.

The `every_n_steps` parameter runs the model only once every so many turns and reduces consumption
further. The practical meaning: a group can play a whole series of `[number of sub-games]` sub-games at
**zero tokens** (in `template` or `ollama` mode), and the whole competition then turns on the quality of
the movement algorithm.

**Location-dependent hints.** The content of the hints may lean on `[game arena]` — the agreed fictional
region in which the game "takes place" (for example New York, London or Paris). When it is defined, the
hints embed real landmarks from that region ("slipping past Times Square"), which makes the verbal game
richer and more suggestive; in the absence of a definition (default `""`), generic landmarks are used.
This too applies in the token-free template mode, and therefore costs nothing. Every hint is capped at
`[hint word limit]` words (default 15) — a limit applied both to the template and to the language model,
which also receives the limit in its system prompt. `[game arena]` and `[hint word limit]` are agreed
and signed conditions like the rest of the game conditions (see Appendix F).

> ### Connection to the course
>
> The strategy module leans on a number of layers from the course *Orchestration of AI Agents*. **The
> movement decision is algorithmic**, and the language model is responsible for the verbal layer only —
> analysing the opponent's language and composing deception text — in the spirit of the
> agents-and-orchestration approach taught in L05. The language model's ability to analyse the
> opponent's language and generate deception text rests on the deep-learning foundations (neurons,
> gradient, loss function) from L02 and on the attention mechanism of the Transformer architecture from
> L04 [28]. Running a local language model through Ollama as you practised in L08 lets the agent produce
> the verbal layer with no dependence on an external service and at zero API tokens, thereby preserving
> full autonomy against the opponent. Reinforcement learning was **not** taught in the course and is one
> possibility only — alongside heuristics and your own algorithm — an additional tool in the box, not a
> foundation stone.

## 6.6 Chapter summary

We built an independent strategy module connected to PeerRuntime between decoding the incoming hint and
packing the Commit, and clearly separated the spatial logic from the verbal logic. We saw three equal
paths for the movement policy: pure heuristics (a Bayesian belief map and Manhattan distance), your own
heuristic algorithm, and reinforcement learning as one optional possibility (not taught in the course) —
and in all of them spatial arbitration remains in the algorithm's hands. We saw how each side — cop and
thief, symmetrically — builds a belief map over the hidden opponent out of the other side's scent map,
and how the language model serves the verbal game only — and is never entrusted with the exact spatial
computation — in four operating modes whose cost ranges from zero tokens upwards.

---

# 7. User interface (GUI) and the replay simulator

## 7.1 Chapter goals

By the end of this chapter you will know: why real-time monitoring (**observability**) is an integral
component in developing complex P2P systems and not external decoration; how a mathematical probability
table is translated into an accessible **heat map** visualisation in the cop's local interface; how a
turn banner reflects the race's asynchronous synchronisation mechanism; and — above all — how to build a
**Replay Viewer** that serves as a reliable evidence system, cryptographically verifying every past step
and identifying any attempt to forge the game log.

## 7.2 Two axes: live monitoring vs. retrospective witness

An integral part of developing a complex P2P system is the ability to monitor the agents' actions in real
time and to verify their legality after the fact. These two needs define the two tools this chapter deals
with, and they do not overlap. The live GUI answers the question "what is happening now?", while the
replay simulator answers the harder question: "did what was claimed to have happened in the past actually
happen as claimed?"

The distinction is not merely technical but essential. In a distributed environment with no central
referee, the game history is not stored with a trustworthy authority — it is kept in a local log file at
each player. This fact opens a temptation: a player might try to rewrite its past in order to win after
the fact. The chapter before you shows how encryption (on which we leaned in Chapter 5) turns the log
from a forgeable document into an unimpeachable evidence document.

> ### Local truth
>
> Local truth is a design principle under which each agent's interface shows only the information
> accessible **to it** — its own position, the scent map it senses, and the hints it received — and never
> the full objective board state. There is no "bird's-eye view" showing both sides' positions
> simultaneously. This principle follows directly from the Dec-POMDP formalism (Chapter 1): each agent's
> observation Ωᵢ is a proper subset of the true state S, and therefore an interface exposing the full S
> would break the rules of the game.

## 7.3 The live GUI: heat map and turn banner

Each side — cop and thief — runs its software out of a dedicated GUI (for example Tkinter or PyQt). As
made clear in the definition of local truth, the interface does not expose the objective board state but
only the local truth. Two central display mechanisms turn the race's abstract mathematics into
controlled, accessible information for the students.

### 7.3.1 Heat map visualisation

The heat-map mechanism is entirely symmetric: each of the two sides runs its own GUI, and in each a
dynamically changing grid displays that agent's belief map regarding **the opponent** only. For the cop,
cells in which the probability of the thief's presence is high — given the hints it received and the
thief's scent map that it senses — are coloured in intensifying shades of red; and in parallel and
identically, the thief's window displays its belief map regarding the cop's position, built out of the
cop's scent map and the hints the thief received. Neither side sees the opponent's position but only a
probability estimate updated in real time. Thus the probability table, which is an abstract object, is
translated for each agent into visual, controlled and accessible information: the student is not required
to read a matrix of numbers but to identify the focus of suspicion at a glance. This is a direct
application of the belief map built in earlier chapters.

### 7.3.2 Turn indicator

To reflect the asynchronous synchronisation mechanism, the interface includes a turn-state banner. The
banner lights green when the opponent's MCP server has signalled that the turn has passed to the local
agent. The moment the local agent has chosen its move, signed it with a Commit and transmitted it to the
opponent, the banner turns grey and the interface locks until the turn is received back. This banner is
not merely a graphical flourish; it is a visual representation of the state machine that prevents the
player acting outside its turn.

**Figure 9.** A mock-up of the cop's live interface: a belief grid in which the intensity of red
expresses the probability of the thief's presence (T?), alongside a turn-state banner lit green (YOUR
TURN) when the turn is received, and grey (LOCKED) after the Commit is transmitted.

*What the figure shows:* on the left, a 3×3 grid representing the cop's window; the darkest cell is
marked T? and expresses the highest probability of the thief's presence, while cell C marks the cop's own
position. On the right, the banner's two states: green (YOUR TURN) and grey (LOCKED). *How to read it:*
the stronger the red shade, the higher the probability accumulated from the scent map and the hints; the
green banner signals that the turn has been received from the opponent's MCP and action is possible, and
the grey signals that the interface is locked. *"What if" analysis:* if the player tries to press a move
while the banner is grey, the interface ignores the input — the lock enforces the asynchronous turn and
prevents a **race condition** in which both sides act simultaneously on the same step.

## 7.4 The replay viewer and integrity enforcement

Building a **Replay Viewer** is a mandatory submission requirement. Its purpose is to supply trustworthy
evidence at the end of the game. The player loads the final log file (for example
`logs/police_match.json`), and the viewing user can step forward and backward in time using control
buttons. The tool's distinction is not in its graphical display but in the cryptographic verification: at
every step the engine runs a live verification function that takes the **nonce** and the move appearing
in the exposed log, re-encodes them with SHA-256 [19], and compares against the original **commitment**
value.

If the values match, a green "**Verified OK**" stamp is shown. If the smallest change is found in the
past data — an attempt to forge the log — the viewer prints a glaring red "**TAMPERED**" banner and the
game is immediately void. This principle rests directly on the collision-resistance property of the hash
function we saw in Chapter 5: since it is impossible to find an alternative input yielding the same hash,
any change in a (nonce, move) pair is necessarily revealed.

**Figure 10.** The cryptographic verification flow in the replay simulator: reading a log entry,
recomputing SHA-256 over the nonce and the move, comparing against the commitment value, and branching to
a green "Verified OK" stamp or a red "TAMPERED" banner that voids the game.

*What the figure shows:* a chain of four stages — reading the log entry, recomputing the hash, a decision
junction (`equals commit?`), and two possible outcomes: a green box (Verified OK) or a red box
(TAMPERED). *How to read it:* the flow is deterministic — for any given input the same result is always
obtained; the central junction is the decision point at which the step's fate is decided. *"What if"
analysis:* if a player changed a single move in the log but left the original commitment value, the
recomputed hash would yield a different value, the junction would branch to the `no` route, and the red
banner would appear — the game is void even if the change was tiny.

## 7.5 The verification engine: a code sketch

The simulator's heart is a single step function applied to every entry. It receives a log entry,
recomputes the hash over the concatenation of the nonce and the move, compares against the stored
commitment value, and returns a status. The commit-reveal schema that this engine verifies was defined in
full in Chapter 5.

```python
import hashlib

def verify_step(entry):
    # Recompute the commitment from the visible log fields.
    payload = f"{entry['nonce']}|{entry['move']}".encode("utf-8")
    recomputed = hashlib.sha256(payload).hexdigest()

    # Compare against the original commitment stored in the log.
    if recomputed == entry["commit"]:
        return "Verified OK"   # green stamp: reveal matches commit
    # Any mismatch means the past data was altered.
    return "TAMPERED"          # red banner: disqualify the match

def replay(log):
    # Walk every recorded step; the whole match is void on first tamper.
    for entry in log:
        if verify_step(entry) == "TAMPERED":
            return "TAMPERED"
    return "Verified OK"
```

The `verify_step` function illustrates the principle: the nonce and the visible move are re-encoded, and
the comparison against the stored `commit` is binary — there is no "almost matching". The `replay`
function walks the whole log; one failure is enough to void the entire game. *Note:* the sketch
simplifies the input for illustration; in practice the signature covers the full step components — State,
Move, Intent and the nonce — as detailed in the protocol of Chapter 5.

> ### Submission requirement and disqualification
>
> Building the Replay Viewer is a **mandatory submission requirement** of the project, and not an
> optional component. Moreover, one **TAMPERED** result — meaning discovery of even the tiniest change in
> the log's past data — **voids the game** immediately. There is no appeal and no retrospective
> correction: the cryptographic evidence system was designed precisely so that there should be no room
> for human judgement on the question of whether the log was forged. A screen capture of the viewer with
> the `Verified OK` indication — alongside a capture of the belief map in the Live GUI — are part of the
> submission requirements (Appendix C); an example implementation of the viewer and the interface is
> available in the code repository of Appendix D.

> ### Connection to the course
>
> The need to monitor agents and verify their actions after the fact is a direct expression of the
> **observability** principle from production-systems development [30]: a system you cannot look inside
> is a system you cannot operate and cannot trust. The live interface and the replay simulator are two
> forms of monitoring a distributed system [5] — one in real time and the other after the fact. From a
> course perspective, this chapter is a direct continuation of the lecture on AI agents and sub-agents
> (L05): there we learned about agents and sub-agents, an orchestrator, commands and skills, as well as
> token consumption and the context windows of agent systems. Just as an agent needs **agent tooling** to
> act, the developer needs tools to see what the agent did, to follow its behaviour and to prove after
> the fact that it acted properly — this is precisely **observability** of agent systems.

## 7.6 Chapter summary

We saw that monitoring is not an appendix but an integral component in a P2P system: the live interface
translates the belief map into an accessible heat map and reflects the asynchronous synchronisation in a
turn banner, all under the local-truth principle that permits no bird's-eye view. The replay simulator,
by contrast, turns the log from a forgeable document into cryptographic evidence: every step passes a
live SHA-256 verification, and every tiny change activates the red TAMPERED banner and voids the game.

---

# 8. Agent architecture design and deep reliability mechanisms

## 8.1 Chapter goals

By the end of this chapter you will know: why an autonomous game agent is not a linear script but a
distributed system requiring meticulous development under the **separation of concerns** principle; how
the **Orchestrator** template concentrates all the sub-systems behind a single entry gate and subjects
the game flow to a legal state machine; and what the stability patterns — **Deadline Tracker** and
**Watchdog** — are that protect the agent against freezing and against disconnections in a peer-to-peer
network.

## 8.2 Separation of concerns as a principle

Why does a system that wins in simulation sometimes fail in a real game against a remote opponent? The
answer is usually not in the decision algorithm but in the development of the system around it. An agent
participating in an AI-based multi-participant game cannot, as the protocols recommend for this field,
mix in one piece of code the management of communication, decision-making and log recording. Such a
mixture gives birth to a fragile system in which a fault in one sub-system brings all of them down.

The development solution is division into modules with clear, isolated responsibility, coordinated by a
single central component. The chapter before you deals with the architectural skeleton: how to build an
**orchestrator** serving as a single gate to all the sub-systems, and how to wrap it in a reliability
layer that assumes in advance that the world — the network, the model, and the opponent — will fail at
exactly the critical moment [30].

## 8.3 The Orchestrator template and the state machine

> ### Orchestrator
>
> A central software component serving as the **single entry point** to all the agent's sub-systems. It
> is responsible for initiating connections, running the decision module, coordinating between
> components, and communicating with the log managers — but it does not itself contain decision logic or
> low-level communication. Its role is to coordinate, not to execute.

The whole game is controlled by a meticulous **state machine** guaranteeing that only legal transitions
between game stages are possible. The stage of waiting for the opponent (`WAITING_FOR_OPPONENT`) can
transition only to the move-computation stage (`COMPUTING_MOVE`), and that in turn to the commitment
stage (`COMMITTING`), and so on. An illegal transition is rejected immediately, thereby avoiding
**deadlock** states in which both sides wait for one another for ever.

> ### Deadlock
>
> A state in which two or more entities wait for a resource or a message held by the other, such that
> none can advance. In a peer-to-peer system with no central referee, a deadlock can freeze a whole game
> with no error message at all. A state machine that blocks illegal transitions is the first line of
> defence against deadlock.

**Figure 11.** The legal state machine of a single game turn: the system passes in cycles between
waiting for the opponent, computing a move, committing, waiting for the reveal, and verification; a
dashed error arrow leads from every communication stage to a technical loss.

*What the figure shows:* five valid states arranged in a loop — `WAITING_FOR_OPPONENT`,
`COMPUTING_MOVE`, `COMMITTING`, `AWAITING_REVEAL` and `VERIFYING` — where verification returns the system
to waiting for the next turn. In addition an error state appears, `TECHNICAL_LOSS`, to which dashed
arrows lead. *How to read it:* the solid arrows are the only legal transitions; any attempt to jump from
one state to a state that is not a legal target for it is rejected. The dashed arrows represent an
emergency exit — a transition to a communication stage that failed. *"What if" analysis:* if the opponent
disconnects during `AWAITING_REVEAL`, the system does not get stuck in eternal waiting but passes in a
controlled fashion to `TECHNICAL_LOSS` and reports the result — exactly the behaviour a legal state
machine guarantees.

```python
class GamePhaseMachine:
    # Transition table: each state maps to its set of legal successors
    TRANSITIONS = {
        "WAITING_FOR_OPPONENT": {"COMPUTING_MOVE"},
        "COMPUTING_MOVE":       {"COMMITTING", "TECHNICAL_LOSS"},
        "COMMITTING":           {"AWAITING_REVEAL"},
        "AWAITING_REVEAL":      {"VERIFYING", "TECHNICAL_LOSS"},
        "VERIFYING":            {"WAITING_FOR_OPPONENT"},
        "TECHNICAL_LOSS":       set(),   # terminal state
    }

    def __init__(self):
        self.state = "WAITING_FOR_OPPONENT"

    def transition(self, target):
        # Reject any transition not listed in the table
        if target not in self.TRANSITIONS[self.state]:
            raise ValueError(
                f"Illegal transition: {self.state} -> {target}")
        self.state = target
        return self.state
```

The class keeps the current state, and every transition request is checked against the set of legal
targets. An illegal transition raises an exception immediately instead of leaving the system in an
undefined state — thus a bug turns into a visible logic error caught at development time, and not into a
quiet deadlock at game time.

## 8.4 Reliability patterns: Deadline Tracker and Watchdog

Peer-to-peer (P2P) systems are inherently exposed to disconnections and to critical delays in the
language model. A robust agent cannot assume every request will be answered; it must implement active
tracking patterns distinguishing "still waiting" from "failed and must act" [30]. The two central
patterns here are the **Deadline Tracker** and the **Watchdog**. A complementary reliability pattern —
the **Gatekeeper**, which regulates outgoing mail — is discussed in the league context in Chapter 9.

### 8.4.1 Deadline Tracker

Every request sent over the FastMCP server carries a **timestamp** and an **expiry deadline**. If the
answer has not arrived within the allotted time, the system performs a **retry** or transmits a
technical-loss message. This pattern is a concrete realisation of the **timeout** template from the
stability literature: never wait without a bound for an external resource not under your control.

> ### A missed deadline is a failure, not patience
>
> A request whose expiry deadline has passed **must** be treated as a failure, and not as an invitation
> to wait longer. Leaving a request "hanging" with no expiry deadline is the direct recipe for deadlock:
> the main process gets stuck waiting, the watchdog identifies that there is no heartbeat, and the game
> collapses. Every request over MCP must carry an expiry deadline, and on its expiry the system must
> perform a controlled retry, or declare a technical loss and close the turn cleanly.

### 8.4.2 Watchdog

While the Deadline Tracker guards a single request, the **Watchdog** guards the whole system. It is an
independent background process monitoring the main game loop. If it identifies that the system has frozen
for long minutes with no **heartbeat** — following a model crash or a communication failure — it can
perform a **controlled shutdown** and preserve **state persistence** for later recovery.

**Figure 12.** The orchestrator serves as a single gate branching to five sub-systems: the MCP connector,
the decision module, the log manager, the deadline tracker and the watchdog. All inter-module
communication passes through it.

*What the figure shows:* a highlighted central component — the Orchestrator — from which arrows go out to
five separate modules: MCP Connector, Decision Module, Log Manager, Deadline Tracker and Watchdog. *How
to read it:* each arrow represents a single control channel; there are no arrows between the peripheral
modules themselves, thereby realising the single-gate principle — no module knows its fellow directly,
but only the orchestrator. *"What if" analysis:* if we wanted to replace the decision engine with another
module, it would be enough to replace a single module and keep the same interface against the
orchestrator; the rest of the system is unaffected — that is the power of separation of concerns.

```python
import time

def watchdog_check(last_heartbeat, timeout_sec=180):
    # last_heartbeat: epoch time of the main loop's last signal
    elapsed = time.time() - last_heartbeat
    if elapsed > timeout_sec:
        # Main loop appears frozen: persist state and shut down cleanly
        persist_state()          # save game state for later recovery
        controlled_shutdown()    # release MCP connections, close logs
        return "SHUTDOWN"
    return "ALIVE"
```

The process compares the time elapsed since the last heartbeat against a fixed threshold. As long as the
main loop emits a pulse at a regular rate, the watchdog does not intervene. But if more than the set
threshold has passed — a sign that the model crashed or communication got stuck — it saves the state and
performs a controlled shutdown, so that it will be possible to recover later instead of losing the whole
game.

> ### Connection to the course
>
> The idea of the orchestrator as a single entry gate to sub-agents is not new to you. In lecture L05,
> which dealt with agents and sub-agents, you saw how a supervisory agent (Orchestrator) delegates work
> to a set of sub-agents through a single gate: it operates **skills** and **commands**, and concentrates
> all the information flow between them instead of every component turning directly to its fellow. The
> game agent's Orchestrator is exactly that pattern, hardened for competitive game conditions: the
> sub-systems (MCP connector, decision module, log manager, deadline tracker and watchdog) are the
> "sub-agents", and the delegation through a single gate — that same separation of concerns — is what
> allows each component to be replaced, checked and fixed separately. Since both sides in the game are
> built symmetrically, each of them runs an orchestrator and a state machine of its own by exactly the
> same pattern.

## 8.5 Chapter summary

We saw that a reliable game agent is built on two development pillars: coordination and reliability. The
orchestrator concentrates all the sub-systems behind a single gate and subjects the game flow to a state
machine that blocks illegal transitions and prevents deadlock. The Deadline Tracker and Watchdog patterns
assume in advance that the network and the model will fail, and supply retry, controlled shutdown and
state preservation instead of a quiet crash.

---

# 9. League, computational fairness and automated reporting

## 9.1 Chapter goals

By the end of this chapter you will know: why the cop–thief project is not tested under closed laboratory
conditions but in a dynamic academic league in which agents produced by different teams compete against
each other in real time; how the "diversity incentive" and "computational fairness" shape the league's
scoring function; and what the **Gatekeeper** template is — the three cumulative protection mechanisms
without which automated reporting over the Gmail API is liable to collapse into flooding servers or an
account block.

## 9.2 The league: from the laboratory to the arena

What distinguishes a programming exercise from a live system? An exercise proves itself against a single,
known examiner; a live system must survive against opponents it has never seen. The project before you
belongs to the second kind. It is not submitted under closed laboratory conditions but is required to
prove itself in a **dynamic academic league** — an arena in which agents from different creators compete
against each other in real time, with no central referee and no pre-written schedule.

This structure changes the rules of the game fundamentally. Success is no longer measured against a fixed
test scenario but against a changing population of opponents, each bringing its own strategy,
architecture and failures. An agent that excelled against one opponent may fail utterly against another —
and that is exactly the educational goal: to train **robust** systems, not solutions **overfitted** to a
single examiner.

### 9.2.1 League structure and score weighting

Every group is required to play against **different** opponents, and the league score is derived from the
collection of those games. To prevent exploitation of a weakness and to encourage new challenges, the
system applies a **diversity incentive**: a win over an opponent you have not yet played awards the full
reward (`[diversity reward]`). But **you may not play the same game again against the same group.**
Against every existing opponent **exactly one counted game** is played. Warm-up games (warm-ups), which
are not counted, are permitted and even recommended, for testing and calibration before the counted game.
Once the game has ended, **both groups have agreed its result**, they send the game-closing notification
to the lecturer, and the meeting against that opponent is **sealed** — you may not continue playing
against it for scoring purposes.

> ### Game-count declaration
>
> At the opening of every game, each group declares to its opponent how many counted games it has played
> so far, and the diversity-incentive weighting is set by the mutual declarations. The declaration is not
> a matter of trust: at the end of every legal game **both groups** send the game summary to the lecturer
> (see §9), and therefore at any moment it is known to the lecturer how many counted games each group has
> actually played. **A false declaration** discovered at the project-checking stage **disqualifies the
> declaring group.**

The minimum threshold requirement for passing the project is modest but unambiguous: proper operation of
at least `[minimum games to pass]` against different groups. Conversely, the number of counted games is
also capped from above: each group may play at most `[maximum games per group]` counted games, so as to
preserve the frame of a balanced and fair league. Alongside the diversity incentive, the principle of
**computational fairness** operates: the system reduces the scoring advantage of whoever leans on extreme
cloud resources, and rewards algorithmically efficient development running on limited machines. In other
words, the league rewards **sophistication in development**, not raw compute power — since a clever
algorithm on a modest machine deserves a higher score than a wasteful algorithm on server farms.

> ### Tie rule
>
> If the accumulated score of **all the sub-games** between a pair of groups ends in a **tie** — that is,
> the sum of points of both groups is identical — each group receives `[tie score]` points. Thus no
> meeting is left without a scoring decision, and an equal result too is translated into a fair credit to
> both sides. The binding value of `[tie score]` is defined in the parameter table (Appendix F).

## 9.3 Automated reporting over the Gmail API

At the end of every legal game against an opposing group, there is no longer room for human intervention
in reporting. **Each of the two groups** is programmed to send separately — **each group by itself** — a
summary notification to the lecturer via the Gmail API [32]; it is not enough that only one side sends.
Automation is both a blessing and a trap in one: it guarantees uniform and immediate reporting, but it
entrusts to code — which may contain a bug — the key to a live email account. What happens when an
infinite loop begins firing thousands of messages a minute?

> ### Reporting address to the lecturer — mandatory
>
> At the end of every legal game, both agents automatically send the closing report to the lecturer's
> mail address:
>
> `[agent reporting address]`
>
> This is the only and mandatory address for sending reports; it must be defined as the target fixed in
> the mail-sending code of each of the two agents.

> ### Connection to the course
>
> This chapter leans on lecture L09, and precisely on exercise `ex06` — a conversation between two agents
> over MCP, in which an agent calls an external tool through a uniform protocol. Note the essential
> difference between the goals: in `ex06` the goal was to succeed in **conversation-based** communication
> between two agents — proving the very ability to coordinate and exchange messages. In the project
> before you the goal is much higher: to succeed in **public** communication — not local and not over
> `localhost` — and to run a full game with **no referee and no central server**. The reporting here is
> therefore genuinely "agent-to-agent": the cop is not talking to a human but ordering an external tool —
> Google's **Gmail** — to deliver a state to its autonomous peer and to the course's servers. The
> critical difference is that Gmail is a **quota-managed** resource in the real world: one call too many,
> and the service provider blocks you. Autonomous reporting in a public environment therefore requires a
> protection layer that was not needed in `ex06` — the **Gatekeeper** template we will now unfold.

### 9.3.1 The Gatekeeper template and the three protection mechanisms

To prevent severe failures — flooding mail servers (spamming) or exceeding Google's quotas (Rate Limit
429) — it is **recommended** to implement in the communication module the **Gatekeeper** template — a
reliability pattern from the Watchdog and Deadline-Tracker family discussed in Chapter 8 — composed of
three cumulative protection mechanisms:

> ### Clarification of terms: three kinds of "token"
>
> The word "token" appears in the project in three **entirely different** contexts, and they are not to
> be confused:
>
> - **Rate token (Token Bucket)** — accompanying units of load in the rate-limiter component below. They
>   are not related to a language model at all.
> - **Language-model tokens (LLM tokens)** — units of text consumed in every call to a language model,
>   which are measured, budgeted and cryptographically locked at step zero (Chapter 5).
> - **OAuth tokens (Access / Refresh Token)** — authorisation approvals against Gmail (see Appendix A).
>
> In the rest of this chapter, "token" always means a **rate token** — and not a language-model token.

- **Quota Manager.** A counter tracking the number of actions performed on a given day, preventing
  exceeding half the daily safety threshold. This is the last line against an account block: if the quota
  is exhausted, not one further request goes out.
- **Token Bucket Rate Limiter.** An algorithm bounding the rate of injecting requests to the API [33].
  Every report needs a valid "rate token" for a defined time window; the absence of a rate token blocks
  the send. Thus **bursts** that might trigger an immediate block at the provider's end are prevented. Do
  not confuse these rate tokens with language-model tokens.
- **DOS Detector.** Identifies anomalous sending patterns indicating a bug or an infinite loop in the
  agent's code. Once such a pattern is identified, the Gatekeeper locks access to the API entirely and
  prevents the account being suspended by the service provider — a known principle in systems
  development, **backpressure** and "circuit breaker" [30].

**Figure 13.** An outgoing report passes through three cumulative protection gates before it reaches the
Gmail API: the quota manager, the token bucket and the DOS detector. Each gate may divert the request to
a rejection or lock branch.

*What the figure shows:* an outgoing report (left) flows through three sequential gates — quota manager,
token bucket and DOS detector — until it reaches the Gmail API (right). From each gate a red failure
branch splits off. *How to read it:* only a request that has passed all three gates reaches the API; a
failure at any gate stops the request as early as possible, on the "fail fast" principle. *"What if"
analysis:* if the DOS detector identifies an infinite loop, it locks the whole pipe (LOCKED) — and
sacrifices the single report in order to save the whole account from suspension.

### 9.3.2 The token-bucket rate limiter: the mathematical rule

The heart of the rate limiter is a simple update rule: rate tokens fill continuously at a fixed rate r up
to a capacity ceiling, and are consumed one unit per report. A request is permitted only if a whole rate
token remains in the bucket. Again: these are load-regulating rate tokens, not language-model tokens.

> **Token-Bucket update rule**
>
> tokens ← min( C, tokens + r · Δt ),  allow ⟺ tokens ≥ 1

The variables defining the rule:

- **C — the capacity.** The maximum number of tokens the bucket can hold. *Practical meaning:* C
  determines the size of the permitted burst — how many reports may be sent "all at once" after a quiet
  period.
- **r — the fill rate.** The number of tokens added per unit time. *Practical meaning:* r is the stable
  average rate permitted in the long run; it must stay below Google's API quota.
- **Δt — the elapsed time interval.** The time since the previous update. *Practical meaning:* the more
  time has passed between reports, the fuller the bucket becomes — quiet is rewarded with future burst
  capacity.

**Total practical meaning:** the rule separates the average rate (controlled by r) from the momentary
burst (controlled by C). A report is received only when tokens ≥ 1; otherwise it is blocked until
continuous filling accumulates a whole token. The agent thus sends freely when throughput is low, but is
gently braked the moment it tries to break the safety threshold.

**Figure 14.** The token level in the bucket over time (r = 0.8, C = 5): continuous filling against
drainage in bursts. Green dots = report permitted; red X = report blocked when the bucket emptied at the
time of the burst.

*What the figure shows:* the blue curve is the token level in the bucket over time. In normal throughput
the bucket fills up and permits reports (green dots), but at the time of the marked burst (around t = 18)
the request rate empties the bucket, and every further report is blocked (red X). *How to read it:* the
rising slope reflects the fill rate r; every sharp fall is a token consumed by a report; the dashed
ceiling is the capacity C. *"What if" analysis:* if we raise r, the bucket recovers faster and blocks
fewer reports — but we risk exceeding the API quota; if we reduce C, we choke legitimate bursts. Choosing
r and C is therefore a balance between throughput and safety.

```python
import time

class TokenBucket:
    """Simple token-bucket rate limiter for outgoing API reports."""

    def __init__(self, capacity: float, refill_rate: float):
        self.capacity = capacity          # max tokens the bucket holds
        self.refill_rate = refill_rate    # tokens added per second
        self.tokens = capacity            # start full
        self.last = time.monotonic()      # last refill timestamp

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last
        # continuous refill, clamped to capacity
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last = now

    def allow(self, cost: float = 1.0) -> bool:
        """Return True and spend a token if one is available, else block."""
        self._refill()
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False                      # caller must back off / retry later
```

### 9.3.3 The mandatory signed JSON report structure

The game report is not free text. It is packed in a uniform, mandatory JSON structure, and is sent as a
file attached to the mail message. The JSON contains all the identity details of the group, its GitHub
addresses, its FastMCP server addresses, cryptographically signed hardware declarations, the game's
timestamp, and mutual-agreement confirmations backed by SHA-256. Any attempt to send an open report
(plaintext), which is not machine-readable, leads to the report's rejection.

> ### Mandatory: agreement on the result and two separate reports
>
> At the end of the game **both groups are obliged to agree its result**, and **each group is obliged to
> send by itself** the game closing report to the lecturer — separately and in the mandatory format. The
> reporting is not the responsibility of one side alone. **If a report is not received from one of the
> sides, that side will not earn points for the game** — even if it won on the board. Agreement on the
> result and the sending of two separate reports are the condition for both groups to earn the points due
> to them.

The whole report is sent as an attached JSON file, and a full example of it is attached to this book as
the file `[results file]`. In practice, **four example JSON files** are attached to the book, covering the
full lifecycle of the game; the variable-name of each is defined in the variables table in Appendix F:

- **`[declaration file]` — pre-game declaration.** Concentrates all the **fixed** data of the whole game
  (all the sub-games): the identity of both groups and their members, the addresses of the cop and thief
  repositories, the MCP server addresses, the hardware specifications, the language model, the agreed
  token ceiling, and the game's start and end times. Its role: to fix, cryptographically signed,
  everything that does not change during the game.
- **`[configuration file]` — the agreed configuration.** All the quantitative parameters of the sub-game
  (Appendix F), cryptographically locked and identical between the sides. Its role: to define the laws of
  physics and scoring both groups agreed to.
- **`[log file]` — the sub-game log.** A step-by-step record: commit-reveal commitments, moves, hints and
  the discussion fields with the language model, alongside the nonce and the hash. Its role: to enable
  full cryptographic verification in the replay simulator (Chapter 7).
- **`[results file]` — the final results report.** A summary of all the sub-games: each group's score in
  each sub-game and the accumulated result, for weighting the league score by the lecturer. This is the
  mandatory report sent by email to `[agent reporting address]`.

The four files carry the shared identifier (`game_uid`), and each file's name is derived from the game
identifier (`game_id`) and the sub-game number (`<NN>`) — so that files from different games are never
mixed. The mandatory fields in the report include the GitHub links of **both** groups, the commit
identifier of each sub-game (Chapter 5), and the total tokens consumed.

> ### Iron rules: 429 Rate Limit and a machine-readable report
>
> **Quota and rate.** Exceeding Google's API quota is returned as the HTTP error 429 (Too Many Requests).
> This error is not a passing fault — blind insistence and immediate repeated sending may lead to the
> account being suspended by the provider. The 429 must be respected, one must **back off**, and wait for
> the next time window. **Report format.** A report must be JSON, structured, uniform and machine-readable,
> sent as an attached file. Any attempt to send an open report in free text (plaintext), which cannot be
> automatically parsed, will lead to **rejection of the report** — and the meaning of a rejection may be
> the loss of that round's league points.

The report's security layer rests not on raw passwords but on controlled authorisation. The agent's access
to Gmail does not depend on a user password but on scoped **OAuth** authorisation tokens measured by the
OAuth 2.0 standard [34], which enables granting a **scoped** permission and revoking it when needed. The
full setup process of OAuth and of the Gmail API authorisations is detailed in Appendix A.

## 9.4 GitHub submission: structure, contents, two repositories

Submission is done in **GitHub**. **Every repository must be accessible to the lecturer**: either
**public**, or **shared** explicitly with the lecturer's address `[lecturer address]`. **Every group
submits two separate repositories**: one repository for the cop agent and a second repository for the
thief agent, and supplies **two links** — a link to the cop repository and a link to the thief
repository.

> ### Two repositories, a cross-link (mandatory), and two links in the submission
>
> Every group develops two agents — cop and thief — in two separate GitHub repositories, accessible to
> the lecturer (public or shared with `[lecturer address]`). It is **mandatory** that the `README.md`
> file of each repository include the link to the other repository: the cop's README points at the thief
> repository, and vice versa. The file submitted in Moodle must contain **both** links (cop and thief),
> and in the closing email — in the attached JSON file — **four links** appear: group A's two links and
> group B's two links.

### 9.4.1 Mandatory repository contents

Every GitHub repository must include, at the very least: a `README.md` file (the academic report, see
below); configuration files (`config/`); **PRD** (product requirements document) files used to build the
code; a work-plan file (**PLAN**); and task files (**TODO**). These files tell the story of the
development and let the examiner reconstruct the way the work was done — and not only the final result.
The full submission guide — branches, version tagging, and a checklist — is collected in Appendix C.

### 9.4.2 README contents

The heart of the documentary submission is the extended academic report in the `README.md` file at the
root of every repository. The list below details the mandatory components — the absence of any of them
subtracts from the submission:

> ### Mandatory contents of the academic report in the README
>
> 1. **The chosen Dec-POMDP model.** A scientific description of the formalism you adopted for modelling
>    the race — the state space, the observations, and the uncertainty — as unfolded in Chapter 1.
> 2. **FastMCP orchestration dilemmas.** A discussion of the development quandaries around communication
>    between the agents: turn management, handling network failure, and the roles of the Gatekeeper and
>    the Orchestrator (Chapter 2, Chapter 8).
> 3. **The strategies implemented.** Detail of the decision-making mechanism you chose — heuristics
>    (Manhattan distance, Bayesian belief map), a language-model-based strategy (LLM), or, as an optional
>    possibility, Q-Learning (Chapter 6).
> 4. **Learning curves (if RL was used).** If you trained the agent with reinforcement learning — learning
>    curves as empirical evidence of policy convergence.
> 5. **Screen captures — an absolute requirement.** From the Live GUI (the belief map) and from the replay
>    application (Replay App) demonstrating `Verified OK` (Chapter 7).
> 6. **A link to the companion repository.** The link to the group's second GitHub repository (cop/thief),
>    as required above.

## 9.5 Chapter summary

We saw that the project is tested not in a closed laboratory but in a live league, in which the diversity
incentive rewards facing new opponents and computational fairness rewards algorithmic wisdom over raw
compute power. We unpacked automated reporting over the Gmail API and the Gatekeeper template — quota
manager, token bucket and DOS detector — as a protection layer without which an autonomous agent could
bring disaster on a live account. We covered the mathematical token-bucket rule and the signed, mandatory
JSON structure.

---

# 10. A recommended priority order in development, and the development process

## 10.1 Chapter goals

This chapter is an **assembly** chapter, and it is entirely a **recommendation**: having understood the
theory, the board, the communication and the strategy, the decisive question remains — in what **order**
is it worth building all of these? By the chapter's end you will know: why it is recommended that a
complex multi-agent system be built in graded layers and not all at once; what the recommended priority
order of the seven stages is; which **milestones** it is recommended should work before moving to the
next stage; and why skipping over the foundations to encryption or the cloud is liable to be a recipe for
failure.

## 10.2 Why we build in layers

The great temptation of a beginning developer is to build the most **impressive** system first — the
encryption, the tunnels to the cloud, the artificial intelligence that composes lies. But a distributed
system is not a tower built from the roof downwards. What is the risk in placing the encryption layer
above communication infrastructure that has not been proven? When an encrypted message does not reach its
destination, we shall not know whether the culprit is the cryptography, the server, or the basic logic — a
multiplication of unproven variables turns every fault into an uninvestigable one.

The principle of **incremental delivery** dictates that every layer is built, tested and stabilised
**before** the layer above it [5]. Every stage ends in a system that runs end-to-end, even if narrow in
scope. Thus at any moment the space of possible faults is confined to the last layer added. On the other
side stands the same principle of **production readiness**: a system is not considered finished when it
runs on the developer's machine, but when it stands up under failures, under load and under
disconnections of the real world [30].

> ### Recommended: layer-on-layer building with several PRD files
>
> A recommended way of applying graded building is to split the software specification into several
> separate **PRD** (Product Requirements Document) files, one per layer. Start from the first PRD,
> generate the code from it, check that everything works properly — and only then add the next layer's
> PRD. Thus every layer is defined, produced and tested separately, and the fault space is minimised to
> the last layer added at any moment. A good PRD definition for an AI agent is a skill in its own right —
> see the file "Recommendations for writing and submitting software with the help of AI agents" in the
> course introduction.

> ### Connection to the course
>
> This chapter is the convergence point of the whole course, from L01 to L11. The graded development
> process is exactly the software development lifecycle (**SDLC**) in the vibe-coding approach that
> opened the course (L01): define a target goal in natural language, implement, test, and extend. The
> layers themselves recycle the whole learning journey — the deep learning foundations (L02 to L04):
> neurons and backpropagation, sequences and RNN/LSTM, Transformers and self-attention; agents, the
> orchestrator and token consumption (L05) and assembling teams of agents and tools (L06); the knowledge
> graph of Graphify (L07) and running a local language model (L08); the conversation between two agents
> over MCP (L09) and distilling from the cloud to the local model (L10); and finally the agent swarm with
> dynamic pheromone trails and collective memory (L11). The final project is not a new subject but the
> **integration** of everything you learned.

## 10.3 The seven stages of the recommended priority order — seven PRD files

To rein in the project's complexity, a recommended graded ladder of development priorities is offered. It
is recommended to realise every stage as a **separate PRD** file, and in order, so that every stage lays a
solid foundation on which the one after it leans — seven stages, seven PRD files.

**Stage 1: base logic.** The game's physical kernel, with no communication or intelligence: the grid of
size `[board size]` (default 7×7), the movement rules, `[barrier quota]`, and simple capture identification
based on coordinate overlap. The whole system runs in a single process. *Practical meaning:* if two agents
cannot move correctly on a local board, there is no point connecting a network between them (Chapter 3).

**Stage 2: basic FastMCP infrastructure.** Separate the agents into separate processes: set up the servers
and program the **tools** to send and receive **pure** geometric information over Localhost [8]. The
agents still speak in numeric coordinates only. *Practical meaning:* the aim is to prove that the pipe
works — that a message leaving one agent reaches the other — before we load it with complex content
(Chapter 2).

**Stage 3: a "blind" strategy module.** Wire a first version of the strategy module — a simple
decision-making tool operating in a world of full and precise information. The choice of implementation is
in your hands: a direct heuristic (Manhattan distance, Bayesian belief), a movement policy based on a
language model mapped directly to a step, or — optionally — Bellman/Q-Learning equations to find the
shortest route [22]. The module is "blind" in the sense that there is not yet scent, natural language, or
deception. *Practical meaning:* thus we isolate the correctness of the decision-making core from the noise
of uncertainty (Chapter 6).

**Stage 4: natural language and scent integration.** The step-up stage. Replace the exact coordinates in
reporting with free language; embed the dynamic pheromone equations and their decay; and in parallel
insert the language model for inference and for composing lies. *Practical meaning:* here the uncertainty
that is the heart of the project is born — the combination of scent dynamics (Chapter 4) with strategic
inference (Chapter 6). This is the most sensitive stage, and therefore it comes only after the
infrastructure and the logic have been proven.

**Stage 5: cloud exposure and tunnelling.** Move from Localhost to public addresses using ngrok or
Localtonet, and connect agents from remote machines [10]. *Practical meaning:* from this moment the system
is no longer a simulation on one machine but a real distributed system, with all the challenges of latency
and disconnection it has (Chapter 2, now beyond the network).

**Stage 6: security and cryptography.** Only when the remote communication works do we wrap it in
commit-reveal mechanisms, write the nonce generator, and integrate the hardware declaration (Step-0).
*Practical meaning:* encryption adds a trust layer above communication that has already been proven
reliable — an operational order that prevents confusion between a network fault and a cryptography fault
(Chapter 5).

**Stage 7: reporting and visualisation shell.** Finally the external shell: connecting the Gmail API
through OAuth 2.0 (Appendix A), completing the GUI, and polishing the replay application. *Practical
meaning:* this is the experience and documentation layer, built last because it consumes all the layers
beneath it (Chapters 9 and 7).

**Table 3 — Mapping the seven stages (seven PRD files) to the book's chapters**

| Stage (PRD) | What is built | Relevant chapter |
|---|---|---|
| 1 | Grid `[board size]`, movement rules, `[barrier quota]`, capture identification | Chapter 3 |
| 2 | FastMCP servers and geometric tools over Localhost | Chapter 2 |
| 3 | Initial strategy module: heuristic, LLM policy, or Bellman/Q-Learning (optional) | Chapter 6 |
| 4 | Natural language, scent equations and decay, LLM integration for deception | Chapter 4, Chapter 6 |
| 5 | Move to public addresses and tunnelling (ngrok/Localtonet) | Chapter 2 |
| 6 | Commit-Reveal, nonce generator, hardware declaration (Step-0) | Chapter 5 |
| 7 | Gmail API over OAuth 2.0, GUI, Replay application | Chapter 9, Chapter 7, Appendix A |

**Figure 15.** A road map for development as ascending stairs: every stage rests on its predecessor, and
only after it has run end-to-end is the next stage added.

*What the figure shows:* seven numbered boxes descending as stairs, with a cumulative build arrow
connecting each stage to the next. *How to read it:* the stair structure stresses that there are no jumps
— every step rests on the one below it, just as every code layer rests on the stability of its
predecessor. *"What if" analysis:* if we drop a stair — say jump from stage 2 straight to stage 6 — the
stairs above it hang in the air: the commit-reveal mechanism would be built over communication that has
not been proven, and every fault would become a multivariate, unsolvable investigation. A local example
implementation of stages 1–4 and 6–7 is available in the code repository of Appendix D.

## 10.4 Milestones and development discipline

The power of the recommended priority order lies in consistency of application. For every stage it is
recommended to define a discrete milestone: a binary criterion it is desirable should hold before moving
on. A milestone is not "the code was written" but "the behaviour was observed end-to-end" — precisely the
spirit of production readiness [30]. A list of all the mandatory rules — do, do not, and recommendations —
is concentrated as a single categorical mapping in Appendix E.

> ### Tagging checklist for milestones
>
> Verify that each item actually works and is observed **before** moving to the next stage:
>
> - **Stage 1:** two agents move legally on a grid of `[board size]`; a barrier beyond `[barrier quota]`
>   is rejected; coordinate overlap triggers a capture.
> - **Stage 2:** a geometric message leaving agent A over Localhost is received and correctly decoded at
>   agent B.
> - **Stage 3:** given a known target position, the agent computes and executes the shortest route with no
>   manual intervention.
> - **Stage 4:** a report in free language is translated into an inference; the scent map is updated and
>   decays each step; the LLM produces a hint (truth or lie).
> - **Stage 5:** an agent on a remote machine connects through ngrok and plays a full round against the
>   local agent.
> - **Stage 6:** a move committed in Commit and then revealed in Reveal with a valid nonce; Step-0
>   verifies hardware.
> - **Stage 7:** a game summary is sent in Gmail; the GUI displays the state; the Replay App replays a
>   recorded round.

> ### Recommended: do not skip ahead
>
> It is recommended not to approach cryptography or the cloud before the base logic and the MCP
> infrastructure over Localhost work end-to-end. Skipping over the foundations may not save time but
> double it: a fault in the upper layer will hide behind instability in the layer beneath it, and you will
> lose hours investigating a source that does not exist. It is recommended to build the stairs from the
> bottom up.

## 10.5 Chapter summary

We set out the recommended priority order in development, in seven stages — from base logic, through the
MCP infrastructure, a blind strategy, language and scent, cloud, security, and up to the reporting shell —
and recommended realising every stage as a separate PRD file, as a direct application of the principles of
incremental delivery and production readiness.

---

# 11. Summary and looking ahead

## 11.1 Chapter goals

By the end of this chapter you will understand why the project before you is not a programming assignment
alone but an exercise in the heart of **complex systems development** under real network conditions; you
will identify the four metrics determining the group's success — coordination, adaptation, integrity and
architecture — and you will know how the skills you acquired reflect in distributed AI systems in
industry.

## 11.2 The arc of the book: from modelling uncertainty to a live league

When we opened the book, we framed the race as a Dec-POMDP: two decentralised agents, a multidimensional
state space, and partial observability that is the heart of uncertainty (Chapter 1) [2]. That distinction
was the starting point for everything that came after it, because from the moment we accepted that there
is no central server and no external referee, we were forced to build the rules of the game, the trust,
and the arbitration from the foundations.

From the abstract modelling of uncertainty we moved to the infrastructure that lets two strangers
communicate with no intermediary — the P2P architecture over FastMCP (Chapter 2). But communication
between opponents lacking trust requires a mechanism that prevents cheating: so we dived into the
cryptography of Commit-Reveal and the proofs of integrity (Chapter 5) [20], which turn a verbal promise
into a mathematically enforced contract. In parallel, we learned how an agent can act wisely precisely
when it does not see its opponent: through scent trails inspired by stigmergy (Chapter 4) [14], which
convert distributed spatial memory into computable probability.

On this infrastructure we placed the decision brain. The belief map and the choice algorithm (Chapter 6)
taught the agent to weigh immediate reward against strategic patience, and to translate a decaying scent
field into a move. And then — after the engine ran — we assembled around it the development envelope
(Chapter 10) which guarantees that code stands up under malicious input and does not crash, and the Live
GUI and Replay tools (Chapter 7), which turn an opaque run into a transparent, auditable game. Finally we
went out from the laboratory into the world: the live league, games against other groups, and reporting
results over the Gmail API (Chapter 9). Every layer rests on its predecessor; remove one course and the
whole tower sways.

## 11.3 The project as systems development, not as a programming exercise

What is the essential difference between a programming exercise and systems development? A programming
exercise is tested in a sterile environment in which the input is predictable and there is no opponent. A
system, by contrast, is measured in a noisy world: communication lines drop, an opponent sends a distorted
message, the local clock drifts, and a public URL address disconnects in mid-turn. The project before you
forces you to face all of these at once.

That is the insight to carry from here onward: the quality of your code is measured not when everything is
fine but when something breaks. An agent that wins against a friendly opponent but crashes against a
hostile opponent has not really solved the problem — it has only solved its easy version. That distinction
separates whoever wrote a program from whoever developed a system.

## 11.4 The four metrics of success

**Table 4 — The project's success metrics and the submission criterion**

| Metric | Its expression in the project | Chapter |
|---|---|---|
| Coordination | Turn management, the P2P protocol over FastMCP, and synchronising two agents with no central referee | Chapter 2 |
| Adaptation | Both agents cope symmetrically with uncertainty: each side builds a belief over the opponent's position out of its decaying scent map and a verbal hint, and updates a probabilistic belief map | Chapter 4, Chapter 6 |
| Integrity | Preventing cheating with SHA-256 and Commit-Reveal, and a full **audit** | Chapter 5 |
| Architecture | Adherence to the Gatekeeper and Orchestrator templates and code robust to failures | Chapter 8, Chapter 10 |
| Submission criterion | The whole project — code, structure and submission — is tested against the file "Recommendations for writing and submitting software with the help of AI agents" in the course introduction | Course introduction |

*How to read the table:* every row is a question the real world will ask of your system. Does it know how
to coordinate with a side it does not control? Does it adapt when information is partial? Does it stay
honest when cheating pays? And does its architecture hold up under load and failure? A group that answers
yes to all four is not only running an agent — it is operating a system.

> ### Beyond the course
>
> The four metrics are not unique to the cop–thief race; they are the currency of every distributed AI
> system in industry, and they connect directly to three layers of the course. Distributed coordination is
> exactly the challenge of two agents talking over MCP and calling external tools (lecture L09), and of
> mass production of agent teams with tools such as LangChain, LangGraph and CrewAI (lecture L06) [5].
> Adaptation under uncertainty drew its inspiration from the distributed agent swarm of lecture L11:
> dynamic scent trails and a collective swarm memory in which successes update a shared representation and
> a decay mechanism prevents ossification — all with no supervisory controller. Cryptographic integrity is
> the basis of **supply-chain security**, of model signing, and of distributed commerce. And robust
> architecture — the Gatekeeper and Orchestrator templates — is exactly what separates a demo that works
> once from a production service that runs for months.

## 11.5 Final pre-submission checklist

> ### Final pre-submission checklist
>
> Go over every item and verify that it is marked in practice, not only in intent:
>
> - **Working base logic:** the game engine runs a full race with no crash, and the scoring rules (Chapter
>   3) are properly enforced.
> - **FastMCP over a public URL:** both agents communicate over the P2P protocol (Chapter 2) through an
>   accessible address, not only on `localhost`.
> - **Commit-Reveal and a passing audit:** the commit-reveal mechanism (Chapter 5) is active, and the audit
>   completes successfully with no forgery identified.
> - **Scent map and belief map:** the stigmergy trails (Chapter 4) and the belief map (Chapter 6) are
>   computed and actually influence decisions.
> - **Live GUI and Replay App with `Verified OK`** (Chapter 7): the viewing tools display the game in real
>   time and in replay, with a valid verification stamp.
> - **Gmail API reporting as JSON — from both sides:** at the end of the game both groups agree the result,
>   and each group sends by itself the closing report in the JSON format structured through the Gmail API
>   (Chapter 9); if one side does not send a report — that side does not earn points. For setting up the
>   authorisations see Appendix A.
> - **A GitHub repository with a Git Tag and an academic README:** the code is tagged in a version and
>   accompanied by a README in order; for the submission procedure see Appendix C.
> - **At least `[minimum games to pass]` games against different groups:** completing `[minimum games to
>   pass]` runs against at least that many different opponents in the live league (Chapter 9); for the
>   shared configuration file see Appendix B, and for the binding values see the central parameter table in
>   Appendix F.
> - **No secrets uploaded to the repository** (`.gitignore`): verified.

> ### Submission list: Moodle, GitHub and PDF report
>
> a. Part of the assignment is knowing how to define and characterise for the agent the instructions
>    suitable for producing the requested code. Verify that attached to the GitHub is a folder containing
>    the markdown files (the PRD files), and at the root a readable `GitHub` (`README.md`). Verify that the
>    whole project and the code stand up to all the guidance in the file "Recommendations for writing and
>    submitting software with the help of AI agents" in the course introduction; checking the assignment
>    will be carried out according to the principles in that file.
> b. Submission is done in **Moodle** according to the fixed instructions. The software code must be
>    submitted on GitHub and shared with the lecturer.
> c. **Each group member** submits the assignment in Moodle **separately**.
> d. Groups submitting must supply a **unique 8-character identification code**, with no spaces.
> e. The Moodle model includes a Word file with a template for producing the PDF file for submission. **Do
>    not change fields or move locations in the template** — only fill in the details, save as PDF and
>    submit.
> f. A **self-grade must be given for code quality only** — not for the league game result. A self-grade
>    based on the game result distorts the criterion for measuring code quality.

## 11.6 Looking ahead: towards distributed autonomous AI

The race you built is a miniature model of the question that will accompany the field of artificial
intelligence in the coming decade: how do many autonomous entities — which do not rely on one another, do
not see the full picture, and are not subject to a central controller — act together coherently, soundly
and robustly? This is not a theoretical question. It is at the heart of distributed multi-agent AI
systems, which research is only beginning to exhaust; multi-agent reinforcement learning [26] is but one
of the optional tools some groups may choose alongside LLM-based strategies and heuristics.

If you learned one thing here that will stay with you, let it be this: a good distributed system is not a
collection of clever agents but an architecture that lets mediocre agents act together in trust, in
adaptation, and in robustness. That capability — to coordinate, to adapt, to preserve integrity and to
develop correctly — you carry out of this book with you. Go out and build.

---

# References

1. *LLM-Based Multi-Agent Orchestration: A Survey of Frameworks, Communication Protocols, and Emerging Patterns*, arXiv preprint, 2025.
2. D. S. Bernstein, R. Givan, N. Immerman, and S. Zilberstein, "The complexity of decentralized control of Markov decision processes," *Mathematics of Operations Research*, vol. 27, no. 4, 819–840, 2002. doi: 10.1287/moor.27.4.819.297
3. F. A. Oliehoek and C. Amato, *A Concise Introduction to Decentralized POMDPs* (SpringerBriefs in Intelligent Systems). Springer, 2016. doi: 10.1007/978-3-319-28929-8
4. L. P. Kaelbling, M. L. Littman, and A. R. Cassandra, "Planning and acting in partially observable stochastic domains," *Artificial Intelligence*, vol. 101, no. 1–2, 99–134, 1998. doi: 10.1016/S0004-3702(98)00023-X
5. S. Newman, *Building Microservices: Designing Fine-Grained Systems*, 2nd ed. O'Reilly Media, 2021.
6. Anthropic. "Introducing the Model Context Protocol." https://www.anthropic.com/news/model-context-protocol
7. Model Context Protocol. "Model context protocol specification." https://modelcontextprotocol.io/specification
8. J. Lowin. "FastMCP: The fast, Pythonic way to build MCP servers and clients." https://gofastmcp.com/
9. Krishnan, *Beyond Context Sharing: A Unified Agent Communication Protocol (ACP)*, arXiv preprint, 2025.
10. ngrok. "ngrok documentation: Secure tunnels to localhost." https://ngrok.com/docs
11. J. Rosenberg, R. Mahy, P. Matthews, and D. Wing, "Session traversal utilities for NAT (STUN)," IETF, RFC 5389, 2008. doi: 10.17487/RFC5389
12. R. Nowakowski and P. Winkler, "Vertex-to-vertex pursuit in a graph," *Discrete Mathematics*, vol. 43, no. 2–3, 235–239, 1983. doi: 10.1016/0012-365X(83)90160-7
13. T. D. Parsons, "Pursuit-evasion in a graph," *Theory and Applications of Graphs, LNM*, vol. 642, 426–441, 1978. doi: 10.1007/BFb0070400
14. G. Theraulaz and E. Bonabeau, "A brief history of stigmergy," *Artificial Life*, vol. 5, no. 2, 97–116, 1999. doi: 10.1162/106454699568700
15. E. Bonabeau, M. Dorigo, and G. Theraulaz, *Swarm Intelligence: From Natural to Artificial Systems*. Oxford University Press, 1999.
16. M. Dorigo, V. Maniezzo, and A. Colorni, "Ant system: Optimization by a colony of cooperating agents," *IEEE Trans. SMC-B*, vol. 26, no. 1, 29–41, 1996. doi: 10.1109/3477.484436
17. S. Thrun, W. Burgard, and D. Fox, *Probabilistic Robotics*. MIT Press, 2005.
18. M. Blum, "Coin flipping by telephone: A protocol for solving impossible problems," *COMPCON*, 1983, 133–137.
19. NIST, "Secure hash standard (SHS)," FIPS PUB 180-4, 2015. doi: 10.6028/NIST.FIPS.180-4
20. S. Goldwasser, S. Micali, and C. Rackoff, "The knowledge complexity of interactive proof systems," *SIAM J. Computing*, vol. 18, no. 1, 186–208, 1989. doi: 10.1137/0218012
21. R. C. Merkle, "A digital signature based on a conventional encryption function," *CRYPTO '87, LNCS*, vol. 293, 369–378, 1987. doi: 10.1007/3-540-48184-2_32
22. C. J. C. H. Watkins and P. Dayan, "Q-learning," *Machine Learning*, vol. 8, no. 3–4, 279–292, 1992. doi: 10.1007/BF00992698
23. R. S. Sutton and A. G. Barto, *Reinforcement Learning: An Introduction*, 2nd ed. MIT Press, 2018.
24. R. Bellman, "A Markovian decision process," *J. Mathematics and Mechanics*, vol. 6, no. 5, 679–684, 1957.
25. *AgentNet: Decentralized Evolutionary Coordination for LLM-Based Multi-Agent Systems*, arXiv preprint, 2025.
26. L. Buşoniu, R. Babuška, and B. De Schutter, "A comprehensive survey of multiagent reinforcement learning," *IEEE Trans. SMC-C*, vol. 38, no. 2, 156–172, 2008. doi: 10.1109/TSMCC.2007.913919
27. R. Lowe, Y. Wu, A. Tamar, J. Harb, P. Abbeel, and I. Mordatch, "Multi-agent actor-critic for mixed cooperative-competitive environments," *NeurIPS*, 2017.
28. A. Vaswani et al., "Attention is all you need," *NeurIPS*, 2017.
29. Z. Ji et al., "Survey of hallucination in natural language generation," *ACM Computing Surveys*, vol. 55, no. 12, 1–38, 2023. doi: 10.1145/3571730
30. M. T. Nygard, *Release It! Design and Deploy Production-Ready Software*, 2nd ed. Pragmatic Bookshelf, 2018.
31. E. Gamma, R. Helm, R. Johnson, and J. Vlissides, *Design Patterns: Elements of Reusable Object-Oriented Software*. Addison-Wesley, 1994.
32. Google. "Gmail API: Usage limits and sending email." https://developers.google.com/gmail/api/reference/quota
33. A. S. Tanenbaum and D. J. Wetherall, *Computer Networks*, 5th ed. Pearson, 2011.
34. D. Hardt, "The OAuth 2.0 authorization framework," IETF, RFC 6749, 2012. doi: 10.17487/RFC6749

---

# Appendix A: Gmail API and OAuth 2.0 setup guide

The project's automated reporting infrastructure — in which the agent sends to itself, to the instructor
or to the team status reports at the end of every run — rests on the ability to send email
programmatically through the **Gmail API**. But a modern and secure approach does not use the ordinary
user password: instead it rests on a secured **token** issued under the **OAuth 2.0** standard [34]. That
standard separates the user's identity from the permission granted to the application, and thereby allows
the agent to act on your behalf without your personal secret ever being exposed in code. This appendix
leads you, step after step, from setting up the project in the cloud to the first authorisation flow that
grants the agent full autonomy [32].

## A.1 The five setup steps

The full process is composed of five ordered stages. Perform them in order; skipping a stage (especially
configuring the consent screen) will cause the authorisation flow to fail at a later and more confusing
stage.

### A.1.1 Step 1: opening a project and enabling the service in the Cloud Console

Enter the **Google Cloud Console** and create a new project (or choose an existing one). Inside the
project, go to the API library and explicitly enable the **Gmail API** service. This action signals to
Google's infrastructure that your project is permitted to call the mail endpoints.

### A.1.2 Step 2: configuring the consent screen (OAuth Consent Screen)

Configure the **OAuth Consent Screen** — the screen on which Google informs the user which permissions the
application is requesting. Choose **External** mode (for users outside the organisation) or **Internal**
(inside a Google Workspace organisation), and add the students' mail addresses to the group of authorised
**Test Users**. While the application is in **Testing** mode, only users on the list will be able to
complete this authorisation flow.

### A.1.3 Step 3: restricting the permissions to the necessary minimum (Scope Restriction)

Define the permission **scope** to the absolute necessary minimum: `https://www.googleapis.com/auth/gmail.send`.
That scope permits **sending** mail — and nothing more. Never grant read permission to a project that has
no need of it. This is a fundamental principle of information security: the less an application can do,
the smaller the damage if it leaks.

### A.1.4 Step 4: creating access credentials (Create Credentials)

On the Credentials page create an **OAuth Client ID** of type **Desktop Application**. Download the
`credentials.json` file to the project's local working directory. It is an **absolute duty** to add this
file to `.gitignore` **before** pushing code to GitHub, in order to prevent secret exposure (in a public
repository — to the whole world; and in a private repository shared with the lecturer — to them too as
well). Forgetting at this stage is one of the most common and most dangerous faults in cloud-based
projects.

### A.1.5 Step 5: the first authorisation flow (First Authorization Flow)

On the first run of the code, Google's official libraries will open a browser window and ask you to
approve the authorisation. On approval, the file `token.json` is automatically created, containing a
short-lived **Access Token** alongside a long-lived **Refresh Token**. Thanks to the Refresh Token, the
agent will be able to send reports fully autonomously — for many months and with no further manual
intervention.

> ### Critical: never push secrets to the repository
>
> The two files `credentials.json` (the application's secret identifier) and `token.json` (the signed
> tokens) are **secrets**. Pushing them to GitHub is equivalent to publishing the entry key to your
> mailbox in public. Add the two lines `credentials.json` and `token.json` to the `.gitignore` file
> **before** the first commit. Remember: once a secret has been pushed to even one commit, it remains in
> the Git history — deleting it from the current code is not enough; you must **rotate** the credentials
> in the console.

## A.2 Anatomy of a token: Access vs. Refresh

To understand why the infrastructure works with no passwords, one must distinguish the two kinds of token
the OAuth 2.0 standard defines [34].

> ### Access Token vs. Refresh Token
>
> **Access Token** — a **short-lived** token (usually expiring within about an hour) attached to every API
> request and actually authorising it. Its rapid expiry narrows the risk window if it leaks.
>
> **Refresh Token** — a **long-lived** token that is not sent to the mail API itself, but serves to obtain
> a new Access Token when the previous one has expired. This is what grants the agent its long-range
> autonomy: as long as the Refresh Token is valid, there is no need for repeated human intervention.

> ### The principle of least privilege
>
> Note that we asked for the scope `gmail.send` only, and not a broader scope such as `gmail.modify` or
> `mail.google.com`. This is a direct application of the **least privilege** principle: grant a component
> exactly the permissions it needs for its task — and no more. A reporting agent only needs to **send**;
> there is therefore no reason it should be able to **read** or **delete** mail. Narrowing the scope turns
> a stolen token from a powerful interface into a limited and almost harmless tool.

## A.3 Implementation: a minimal send-only flow in Python

```python
import base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Least-privilege scope: send only, no read/modify access
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

def get_service():
    # Reuse token.json if it exists; otherwise run the consent flow once
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    return build("gmail", "v1", credentials=creds)

def send_report(service, to_addr, subject, body):
    message = MIMEText(body)               # build a plain-text MIME message
    message["to"] = to_addr
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return service.users().messages().send(
        userId="me", body={"raw": raw}).execute()

if __name__ == "__main__":
    svc = get_service()
    send_report(svc, "grader@example.com", "Run report", "Episode finished.")
```

In practice, on the first run the token-loading call is replaced by
`InstalledAppFlow.from_client_secrets_file(...)` in the authorisation flow, which produces `token.json`;
all subsequent runs load the existing token and refresh it automatically.

## A.4 Summary of files

Only two files are required for the infrastructure; both are secret and both must be included in
`.gitignore`.

**Table 5 — Files required for the OAuth infrastructure, their source and sensitivity**

| File | Source | Contents | Add to `.gitignore`? |
|---|---|---|---|
| `credentials.json` | Downloaded from the console | The application's secret identifier | Yes — mandatory |
| `token.json` | Created on the first run | Access and refresh tokens | Yes — mandatory |

---

# Appendix B: A uniform format for the configuration file

## B.1 Why a shared constitution? A configuration file in a world with no referee

In a distributed P2P game, in which the two agents confront one another directly with no central server
acting as referee, a fundamental question arises: who sets the laws of physics of the game? When a central
server exists, it alone enforces the board size, the maximum number of moves and the scent dissipation
rate, and both players are subject to its rulings. But in the absence of a referee, each side runs its own
copy of the game logic — and if the two copies do not agree on exactly the same values, the race
disintegrates into two contradictory realities that cannot be reconciled.

The practical solution is to turn all the agreed game conditions into a single source of truth, unique,
readable and visible, concentrated in the file `config/game.json` — the game's **signed constitution**.
This file is not merely a collection of constants; it is a **constitution** the two sides agree before the
curtain rises, and it is loaded byte-for-byte identically at both ends and locked with a cryptographic
signature. Alongside it, each peer holds a private configuration file — `config/game.toml` — with its
local settings only (network port, choice of strategy module, language-model mode for the verbal game,
mail target and group identity), which are not subject to negotiation and need not be identical between
the sides. When the board exists, the same limits, the same decay rate, so that both agents enforce
exactly the same physics: the same board, the same boundaries, the same decay rate. Thus, even though no
third entity arbitrates, both sides compute the same result out of the same rules.

An additional advantage is readability and **configurability**. Separating the parameters from the code
allows the battle conditions to be changed — a bigger grid, a harder time limit, a wider scent field —
without touching a single line of logic. The values shown here are the book's agreed default choices, and
each of them can be re-tuned per match, as long as both sides load the same JSON file. A full example of
the configuration in JSON format is attached to the book as the file `[configuration file]` (see the
variables table in Appendix F).

## B.2 When JSON, when TOML, and why

The project uses two configuration formats, each with a distinct role. **The distinction is simple:
everything the two sides must agree on is written in JSON; everything that is private and local to a
single peer is written in TOML.**

- **JSON — for shared, signed and exchanged data.** In this format are written (a) the agreed game
  conditions — `config/game.json`; (b) the four standard files — the declaration, the configuration, the
  log and the results report (Chapter 9); and (c) the rate-limiter configuration — `rate_limits.json`.
  JSON was chosen because it is an unambiguous, cross-language standard, admits **canonical**
  serialisation (sorted keys) and therefore consistent hashing (`config_sha256`), and suits
  byte-for-byte-identical cryptographic signing and exchange between teams who may have written their code
  in different languages. **Anything the opponent sees, verifies or depends on must be here.**
- **TOML — for private, local configuration only.** In this format is written only and exclusively the
  private file for each peer — `config/game.toml`: network port, the opponent's address, choice of
  strategy module, language-model mode, LLM settings, mail target and group identity. TOML was chosen
  because it is edited by hand by every team, is especially readable, and **supports comments** — a
  decisive advantage, since the `[strategy]` and `[trash_talk]` sections include code-explanatory notes
  guiding the student. This file does not go out to the network and is not signed, and therefore needs no
  canonical or hashable form. **No value relevant to the opponent is found in it;** if some value becomes
  shared — its place moves to the JSON.

From here the decisive test: ask "must the opponent agree to this value, or depend on it?" — if yes, its
place is in the shared JSON; if not, it stays in the private TOML.

## B.3 The signed shared file

Below is the shared constitution file `config/game.json` with its sections: the board and the agents
(`board_and_agents`), movement and barriers (`movement_and_barriers`), scoring (`scoring`), the pheromones
(`pheromones`), the network and the league (`network_and_league`) and the rate limiter
(`rate_limiter_gatekeeper`). The two peers load a byte-for-byte identical copy, and the signature exchange
before the game refuses to play on any mismatch. The values here are the book's binding default choices
(see the binding table in Appendix F).

```json
{
  "schema_version": "1.2",
  "agreed_between": ["group-a", "group-b"],
  "board_and_agents": {
    "grid_size": 7,
    "num_agents": 2,
    "thief_start": [3, 3],
    "cop_start": [0, 0],
    "axis_origin_corner": "top-left",
    "axis_start_index": 0
  },
  "world": {
    "map_area": "New York",
    "hint_max_words": 15
  },
  "movement_and_barriers": {
    "move_set": ["N", "S", "E", "W", "STAY"],
    "max_barriers": 14,
    "max_moves": 35,
    "survival_threshold": 35
  },
  "scoring": {
    "capture_cop": 20, "capture_thief": 5,
    "survival_cop": 5, "survival_thief": 10,
    "tie_score": 2, "technical_loss": 0
  },
  "pheromones": {
    "pheromone_center_intensity": 0.9,
    "pheromone_decay": 0.10,
    "pheromone_grid_size": 5
  },
  "network_and_league": {
    "response_timeout_sec": 30, "watchdog_timeout_sec": 60,
    "num_games": 1, "diversity_reward": 10,
    "min_games_to_pass": 2, "max_games_per_team": 10,
    "token_budget_per_series": 200000
  },
  "rate_limiter_gatekeeper": {
    "requests_per_minute": 30, "concurrent_requests": 2,
    "retry_backoff_sec": 5, "max_retries": 3, "queue_depth": 100
  }
}
```

The key fields map one-to-one to the binding parameter table: `grid_size` = `[board size]`, `max_barriers`
= `[barrier quota]`, `scoring.capture_cop` = `[capture score – cop]`, and so on. Every field's value may
change in negotiation (in the stricter direction only, for a parameter of "minimum" type) but the field
**names** are fixed and binding. The `num_games` field is sent with a default value of 1 (a single
demonstration sub-game); a full league series requires `[number of sub-games]` sub-games.

## B.4 The private per-peer file

Alongside the shared JSON, each peer holds `config/game.toml` — private, local, and not subject to
negotiation. It contains the group's identity, the network port and the opponent's address, choice of
strategy module (`[strategy]`), the language-model mode for the verbal game (`[trash_talk]`),
language-model settings (`[llm]`), the mail target and the graphical settings. Below is an abbreviated
skeleton:

```toml
version = "1.10"

[game]
group_name = "My-Team"
group_id   = "my-team"
sub_game_number = 1
members = ["id-1001", "id-1002"]
repos = { cop = "https://github.com/you/repo", thief = "https://github.com/you/repo" }

[network]
my_port      = 8802                            # MY MCP server port
opponent_url = "http://127.0.0.1:8801/mcp"     # the only thing I know about the opponent
turn_timeout_seconds = 180

# [strategy]  -- optional: point at YOUR brain subclass (else the shipped heuristic runs)
# thief_class  = "my_team.strategy:MyThiefBrain"
# police_class = "my_team.strategy:MyPoliceBrain"

# [trash_talk] -- optional: HOW the banter is produced. The MOVE is always pure Python.
# provider = "template"   # template(0 tokens, default) | ollama | claude_api | claude_cli

[llm]
model = "claude-opus-4-8[1m]"    # MY choice; the opponent may differ
step_deadline_seconds = 30       # hard cap on LLM thinking per step

[email]
recipient = "rmisegal+uoh26finalgame@gmail.com"
mode = "draft"
```

When `config/game.json` exists, its game-condition values **override** every parallel key from the TOML —
so that the private file can never "weaken" a signed condition. The full and binding dictionary of every
parameter — its name, meaning and value — is concentrated in the binding parameter table in Appendix F.

---

# Appendix C: GitHub submission requirements and academic report

This appendix defines the formal threshold conditions for submitting the project. It is important to
understand from the outset: submission is not a lone source file attached to an email, but a **complete
development artefact** — a full code repository accessible to the lecturer (public, or private and shared
with them), documented, and version-tagged — which tells the story of the system you built. The manner of
submission is measured with the same rigour as the code itself, because in the real world of distributed
AI systems, **reproducibility** and process transparency are an inseparable part of the product.

## C.1 The GitHub repository: structure, branches and tagging

The submission infrastructure is a well-organised GitHub repository, **accessible to the lecturer** —
either **public** or **shared** with the lecturer's address `[lecturer address]`. The accessibility
requirement is not a technical whim but a professional stance: good professional code is written to be
read, examined and reproduced by others. Development is managed through **branches** — every substantive
capability is developed on a dedicated branch and merged into the main branch only after it has stabilised
— in accordance with the development practices of distributed systems and microservices [5].

The final submission version is not marked in the vague "state of the last branch", but is fixed by means
of a documented **annotated Git tag**. The tag freezes a certain and unappealable point in time in the
repository's history, and lets the examiner reconstruct exactly the code that was submitted — and not a
later version that may have been written after the deadline.

```bash
# Create an annotated, documented tag for the submission commit.
# The -a flag makes it an annotated tag (stored as a full object),
# and -m attaches the mandatory documentation message.
git tag -a v1.0-submission -m "Final submission: Police-Thief P2P, group N"

# Push the tag to the remote the grader can access
# (public, or private shared with the lecturer).
git push origin v1.0-submission

# (Optional) verify the tag was created and points to the right commit.
git show v1.0-submission
```

The tag `v1.0-submission` turns the chosen commit into a stable reference point.

## C.2 The academic report: README.md

The heart of the documentary submission is the extended academic report written in the `README.md` file at
the root of the repository. This is not merely an installation-instructions file but a scientific document
explaining the planning decisions, justifying them, and presenting the empirical evidence for their
success.

> ### The README contents are defined in Chapter 9
>
> The mandatory content of the academic report — its five components, alongside the requirement for the
> **contents of the second repository** (cop and thief) and the cross-link between them — is defined in
> full in Chapter 9 ("GitHub submission: structure, contents, two repositories"). Verify that all the
> components exist in the `README.md` file of **each** of the two repositories.

The requirement for screen captures is not merely formal: the belief map proves that the agent really does
run probabilistic inference under partial observability, and the `Verified OK` indication proves that the
**integrity** of the game was preserved — that the encrypted chain of moves was checked and verified,
similarly to the cryptographic proof mechanisms that base trust with no need for a trusted central actor
[20].

> ### Never upload secrets to the repository
>
> If the repository is public, every file you upload to it is visible to the whole world; and even if it
> is private and shared with the lecturer only — there is still an absolute prohibition on uploading
> private identification and access-token details, and in particular the OAuth `credentials.json` and
> `token.json` files (see Appendix A) and any configuration key or secret (see Appendix B). It is
> **mandatory** to include at the root of the repository a `.gitignore` file explicitly excluding these
> files, so they will not be included in a commit by accident. A secret that has leaked once is considered
> permanently exposed — it remains in the Git history even if deleted in a later commit.

## C.3 Submission tagging checklist

**Table 6 — Submission tagging checklist**

| Item | Required status |
|---|---|
| Two GitHub repositories accessible to the lecturer (cop, thief) | Public **or** private and shared with the lecturer |
| Cross-link between the repositories + two links in the submission | Present |
| A documented Git tag `v1.0-submission` for the submission version | Pushed |
| The components of the report in `README.md` (Chapter 9) | Complete in both repositories |
| Screen capture of the belief map (GUI) | Attached |
| Screen capture of Replay with `Verified OK` | Attached |
| At least two games against different groups | 2 and above |
| Game-closing email — from each group separately | Both sides sent |
| No secrets uploaded to the repository (`.gitignore`) | Verified |

> ### Systems development, not just programming
>
> Remember the message running through the whole book: the project before you is not a plain programming
> assignment but an exercise in developing a complex system under real network conditions. Success is
> measured on four central metrics — **coordination** between the agents; **adaptation** to uncertainty by
> means of stigmergy-based scent trails [14]; guaranteeing **integrity** with advanced hashing mechanisms
> [20]; and adherence to correct **architecture** (the Gatekeeper and Orchestrator templates) [5]. These
> four metrics — and not the beauty of a lone algorithm — are what will decide each group's success and
> its ability to cope in the real world of distributed AI systems. A full summary of these metrics appears
> in Chapter 11.

---

# Appendix D: The example code repository — a basic simulation implementation

Alongside the rules and guidelines book, an **example code repository** is attached — a basic, public,
public implementation of the cop-and-thief game, shared with the students on the course. The repository is
available on GitHub at `[example code repository]` (the full address appears in the variables table in
Appendix F).

This appendix describes **code version 3.0.0** of the repository (the same version appears on the book's
title page). A deep version link exists, bidirectional between the code and the book: the code version is
read from a version file in the repository and is updated here automatically on every rebuild of the book,
and the book version (3.0.0) is updated in the repository's `README` on every commit.

> ### What this repository is — and, more importantly, what it is not
>
> This repository is intended **for study only**. It demonstrates the basic game flow and the simple
> graphical interface, **with no strategy at all** — the agents move in a minimal way in order to show how
> a complex system runs end-to-end. **Do not start the project from this repository**, because it does not
> meet the full project specification: it was written as a condensed example and not as a submission
> solution. You are permitted to use parts of the code or to change it, and it is recommended to draw on
> it in order to learn how a certain component is implemented or to clarify a point not understood from
> the book — but your solution must stand on its own against the full requirements (see the binding
> parameter table in the last appendix).

## D.1 What the example shows

The repository runs two independent **peers** — cop and thief — each in a separate process, with its own
configuration file and its own FastMCP server, exactly as two students playing against each other from two
machines. It demonstrates: movement on the board, barrier placement, the scent-trail mechanism and the
belief map, the **Commit-Reveal** protocol based on SHA-256 with a full audit at the end of the game, a
token-consumption meter, and a JSON report sent as a Gmail draft. The strategic logic — choosing the moves
— was deliberately left minimal, and that is the core you are meant to develop.

## D.2 Code layout

According to the repository's `README.md`, the architecture is built in layers:

- **Interface (Tkinter GUI/CLI)** — a live window and a replay application.
- **SimulationSdk** — a single business entry point.
- **PeerRuntime** — one autonomous peer: negotiation → turn loop → audit.
- **domain** — board, scent, belief, state, rules, cryptography, negotiation, protocol and the decision
  "brain".
- **infra** — language-model providers for the verbal game (a free template as the default, a local
  Ollama, or a cloud/CLI), the MCP traffic to the opponent's server, and the mail sender.
- **shared** — configuration manager, rate limiter, system information and the version.

Every Python file is short (up to about 150 lines of code), development is accompanied by tests
(`pytest`), and all the external configuration is in `config/police/` versus `config/thief/`, in full
separation. **The student's two extension points** are clearly separated in the private configuration file:
in the `[strategy]` section the keys `police_class`/`thief_class` point at your "brain" class, inheriting
from `BrainBase` and overriding `_pick_move` (and for the cop also `_decide_move` — where the barrier
choice lives); and in the `[trash_talk]` section you choose how the deception text is produced (default
`template` — zero tokens). **The move is always computed in Python**; the language model touches only and
exclusively the verbal layer.

## D.3 How to run

```bash
uv sync

# Terminal 1
uv run python -m police_thief peer --role police
# Terminal 2
uv run python -m police_thief peer --role thief

# Replay a saved match:
uv run python -m police_thief replay --log logs/police_match.json
```

> ### Tip: turn the repository into a "chat-bot" over the code with NotebookLM
>
> A convenient way to learn the code is to convert all the repository files to text format (`.txt`), load
> them into **NotebookLM**, and then ask questions about the code as if you had a dedicated conversational
> agent for the simulation: "where is the belief map computed?", "how exactly is the Commit-Reveal
> protocol enforced?" and so on. Thus you can understand a particular component quickly, without reading
> the whole repository by hand.

> ### Strongly recommended: a research and performance-analysis report — a template for your own planning
>
> In the `docs/` folder of the reference repository a **research and performance-analysis report** is
> attached (`RESEARCH-REPORT-Performance-Analysis.md`). The report analyses, on the basis of the code
> itself, the agent's resource consumption: how many language-model calls are needed in a full series, how
> they stack up against the rate limits (RPM) and the message windows of the various providers — Ollama,
> Gemini, ChatGPT, Claude and Grok — in their free and paid versions, and how the **fallback** mechanism
> guarantees that every sub-game finishes even when the provider is blocked. **Read it in order to plan
> and forecast your project:** to choose the game strategy and the **suitable language model** for your
> budget and infrastructure, and to understand in advance where a bottleneck is expected. And more
> important still — use it **as a template**: repeat the same analysis on **your** plan, architecture and
> infrastructure, so that your decisions rest on numbers and not on guesswork.

## D.4 Terms of use

You are permitted to use parts of the code, to learn from it, and to change it for the project's needs.
That said, remember two principles: **(1)** the repository is an **educational starting point**, not a
submission skeleton; your solution is measured against the full specification. **(2)** the repository's
licence is an **educational use licence** (see the `LICENSE` file). Wherever the repository deviates from
the book, **the book and the binding parameter table prevail**.

---

# Appendix E: Mapping of the mandatory rules — do, do not, and recommendations

Research into distributed artificial-intelligence systems, and particularly those operating under a model
of decentralised, partially observable Markov decisions (Dec-POMDP), demands a deep understanding of
regulatory rules. This appendix concentrates the list of the system's mandatory rules, scattered through
the book, into a single categorical checklist, divided into five topic groups and a completions group.
Non-compliance with these rules carries a clear systemic meaning — from disqualification, through a
technical loss, to loss of points. The binding quantitative values themselves are concentrated in the
**binding parameter table** in Appendix F.

Each group is presented as a three-column table — number, action (duty / prohibition / recommendation), and
instruction.

## E.1 Network architecture, decentralisation and local epistemology

**Table 7 — Network architecture, decentralisation and local epistemology**

| # | Action | Instruction |
|---|---|---|
| 1 | Duty | Run the thief's code and the cop's code in two fully separate processes. *Sanction:* total failure and breaking of the Zero-Trust model. |
| 2 | Prohibition | Do not share memory or variables between the sides at all. *Sanction:* immediate disqualification of the solution for information leakage. |
| 3 | Duty | Define the orchestrator component as the single entry point to the sub-systems. *Sanction:* instability and technical loss. |
| 4 | Duty | Manage the game states with a proper state machine. *Sanction:* technical loss resulting from a deadlock in the system. |
| 5 | Duty | Reject any attempt at an illegal state transition in the state machine. *Sanction:* a logic error leading to a loss. |
| 6 | Duty | Implement a deadline-tracking mechanism to prevent freezing while waiting for the opponent. *Sanction:* paralysis of the system and loss on time (Timeout). |
| 7 | Duty | Run a watchdog to monitor process crashes and to extract data in a controlled way. *Sanction:* game crash and loss of the official record. |
| 8 | Duty | Display local truth only in the live user interface. *Sanction:* disqualification of the game's legality on account of an information breach. |
| 9 | Prohibition | Do not display the full objective board state in the live interface. *Sanction:* project disqualification for an illegal advantage. |
| 10 | Duty | Use a tunnelling tool to expose the local server to the public internet. *Sanction:* inability to compete in the league against opponents. |

## E.2 Spatial mechanics, physics and board constraints

**Table 8 — Spatial mechanics, physics and board constraints**

| # | Action | Instruction |
|---|---|---|
| 11 | Duty | Verify that the configuration file is identical byte-for-byte on both sides. *Sanction:* match disqualification for broken symmetry. |
| 12 | Duty | Raise minimum values in the parameter table by agreement only, and never lower them. *Sanction:* deviation from the threshold conditions, leading to score disqualification. |
| 13 | Duty | Move only and exclusively in the orthogonal directions. *Sanction:* an illegal move and a technical loss. |
| 14 | Prohibition | Do not perform diagonal moves. *Sanction:* the move is rejected by the opponent, and a loss. |
| 15 | Duty | Declare openly every barrier placement. *Sanction:* board forgery and an automatic loss at the audit. |
| 16 | Prohibition | Do not lie about the location of the barrier placement. *Sanction:* grounds for severe disqualification. |

## E.3 Cryptography, record integrity and zero-knowledge

**Table 9 — Cryptography, record integrity and zero-knowledge**

| # | Action | Instruction |
|---|---|---|
| 17 | Duty | Use a commit-reveal protocol based on SHA-256. *Sanction:* absence of the mechanism makes the solution illegal. |
| 18 | Duty | Keep the number-used-once (Nonce) absolutely secret until the end of the game. *Sanction:* disqualification of the protection against a dictionary attack. |
| 19 | Duty | Void a game technically on any hash mismatch at the audit stage. *Sanction:* an iron rule dictating a score of 0 for the forging group. |
| 20 | Duty | Build a viewing application for the replay of the game log and its verification. *Sanction:* a threshold condition for review approval and for submitting the project. |
| 21 | Duty | Declare truthfully only, at the time a thief is captured. *Sanction:* immediate disqualification for denying reality. |
| 22 | Prohibition | Do not declare falsely about a capture; a false declaration causes immediate disqualification. *Sanction:* a zero score and a technical loss with no possibility of appeal. |
| 23 | Duty | Lock the scent emission and decay model cryptographically before the game begins. *Sanction:* a deviation in the decay formula voids the game. |
| 24 | Duty | Perform a cryptographic hardware declaration before the game begins. *Sanction:* forfeiture of eligibility for the computational-fairness bonus. |

## E.4 Strategy, language and the public network

**Table 10 — Strategy, language and the public network**

| # | Action | Instruction |
|---|---|---|
| 25 | **Recommendation** | Do not pass to the language model the decision on the movement step itself; use it for text processing and for producing a behavioural profile only. *Note:* there is no mandatory sanction, but blind reliance is liable to cause hallucinations, illegal moves and a technical loss. |
| 26 | Duty | Conduct communication in free natural language only. *Sanction:* preserving the psychological character of the challenge. |
| 27 | Prohibition | Do not use a protocol of direct numeric positions. *Sanction:* disqualification of the game's character as defined in the rules book. |
| 28 | Duty | Implement a token-bucket-based rate limiter for sending the reports to Gmail. *Sanction:* preventing a 429 block that would paralyse the group's reporting. |
| 29 | Duty | Define a denial-of-service (DOS) detector for hard protection of the network resources. *Sanction:* locking the interface to prevent the reporting account being blocked. |
| 30 | Duty | Use send-only permission for the Gmail interface. *Sanction:* a security deviation that would entail disqualification in the code. |

## E.5 League fairness, administrative procedures and competitive purity

**Table 11 — League fairness, administrative procedures and competitive purity**

| # | Action | Instruction |
|---|---|---|
| 31 | Duty | Play the minimum mandatory number of games against different groups in the league. *Sanction:* non-compliance with the minimum denies a passing score. |
| 32 | Duty | Report the game results automatically by means of the Gmail interface. *Sanction:* absence of reporting voids the points from that game. |
| 33 | Duty | Shape the game report as a standard data structure of type JSON. *Sanction:* code cannot process free text, and the report will be rejected. |
| 34 | Prohibition | Do not send the closing report in free text, but only as an attached JSON file. *Sanction:* a report that is not JSON will be refused in processing and will bring a zero score. |
| 35 | Duty | Agree with the opponent on the result, and every group sends a separate closing report; non-reporting by one of the groups or a contradictory report causes disqualification of the game and a score of 0 for both groups. *Sanction:* the principal enforcement mechanism preventing fraud in reporting. |
| 36 | Duty | Perform a comprehensive mutual log audit at the end of every game. *Sanction:* a necessary precondition before agreeing on the shared JSON result. |
| 37 | Duty | Declare precisely the number of games actually played, at the beginning of every game. *Sanction:* a threshold condition for computing the true competition factor. |
| 38 | Prohibition | Do not declare falsely about the number of games; a false declaration disqualifies the project. *Sanction:* absolute disqualification for a breach of discipline and integrity. |
| 39 | Prohibition | Never push secrets and credentials to the repository — even if it is private and shared with the lecturer only. *Sanction:* a severe security failure and failure of the project. |
| 40 | Duty | Add the credentials and secrets files to the `.gitignore` file. *Sanction:* mandatory protection against leakage of the Gmail API authorisation details. |
| 41 | Duty | Tag the submission version in the repository by means of a documented Git tag. *Sanction:* an administrative condition enabling the lecturer to check the final version. |
| 42 | Duty | Write and attach a comprehensive academic report as a readable file in the repository (model description, dilemmas, strategy, images and RL curves). *Sanction:* without the report the project is not academically complete. |
| 43 | Duty | Download the submission form from the model, fill it in and save it as PDF; do not change and do not move fields. *Sanction:* a bureaucratic condition for awarding a grade. |
| 44 | Duty | Submit the assignment in the model separately for every group member. *Sanction:* a project with no individual submission will not earn the student a grade. |
| 45 | Duty | Enter a unique group identification code of eight characters with no spaces. *Sanction:* an organisational failure that would prevent automatic attribution of reports to a group. |

## E.6 Completions discovered on cross-checking against the book

The rules below appear in the body of the book but were absent from the original mapping; they are brought
here to complete the picture, alongside a reference to their source.

**Table 12 — Completions discovered on cross-checking against the book**

| # | Action | Instruction |
|---|---|---|
| 46 | Duty | A barrier placed on the cell on which the thief stands at that moment counts as a capture (the cop wins). *Source:* Chapter 3. |
| 47 | Duty | A thief trapped with no legal move at all is likewise considered captured. *Source:* Chapter 3. |
| 48 | Duty | Score every end scenario according to the scoring table (capture 5/20, survival 10/5, technical loss 0/0). *Source:* Chapter 3 and the parameter table. |
| 49 | Duty | Submit **two** separate GitHub repositories — cop and thief — with a cross-link in the README, two links in the model submission, and four links in the JSON of both groups. *Source:* Chapter 9. |
| 50 | Duty | Include in every repository, at the very least: README, configuration files (`config/`), PRD files, a PLAN file and TODO files. *Source:* Chapter 9. |
| 51 | Duty | Send the automatic closing reports to the lecturer's address `[agent reporting address]`. *Source:* Chapter 9. |
| 52 | Duty | Against every opponent, **exactly one counted game** takes place (no repeats for accruing points); warm-up games, which are not counted, are permitted. *Source:* Chapter 9. |
| 53 | Duty | Record in the step-zero declaration the commit hash that was played; it is permitted to change code between games, but in every game it is mandatory to update the commit identifier. *Source:* Chapter 5. |
| 54 | Duty | Report in the closing JSON file the **total tokens** consumed in the sub-game (and in the series). *Source:* Chapter 5, Chapter 9. |
| 55 | Duty | Give a **self-grade for code quality only** — not for the league game result. *Source:* Chapter 11. |

---

# Appendix F: The binding parameter table

This appendix is the single source of truth for every quantitative value in the project. Throughout the
book, numeric values do not appear as a "hard" number in the body of the text, but as an intuitive Hebrew
**code-name** enclosed in square brackets — for example `[board size]`. The value is in practice fixed
here, and only here, in the tables below.

> ### How to read the table
>
> The values presented in the "example value" column are the **binding minimum**: it is permitted to raise
> them by mutual agreement between the two playing groups, but it is **forbidden** to lower them below this
> threshold. A parameter marked "fixed" cannot be changed; a parameter marked "negotiation" is fixed
> entirely in the negotiation stage between the sides, and the value shown is an example only.

## F.1 Board, axis system and opening positions

**Table 13 — Board parameters, axis system and opening positions**

| # | Parameter name | Meaning | Example value | Status |
|---|---|---|---|---|
| 1 | `[board size]` | The edge of the square game grid | 7×7 | minimum |
| 2 | `[number of agents]` | The number of players in the race | 2 | fixed |
| 3 | `[axis-system origin]` | The corner in which cell (0,0) sits | top-left | negotiation |
| 4 | `[axis start index]` | The number from which each axis starts counting | 0 | negotiation |
| 5 | `[opening position – thief]` | The thief's opening cell | centre (3,3) | negotiation |
| 6 | `[opening position – cop]` | The cop's opening cell | corner (0,0) | negotiation |

## F.2 Game arena and verbal hints

**Table 14 — Game-arena and verbal-hint parameters**

| # | Parameter name | Meaning | Example value | Status |
|---|---|---|---|---|
| 1 | `[game arena]` | The fictional region in which the game takes place — feeds real landmarks into the verbal hints. Empty (`""`) = generic landmarks | New York | negotiation |
| 2 | `[hint word limit]` | The maximum number of words in every verbal hint sent over the network — applies both to the template mode and to the language model (which is told it in the system prompt) | 15 | negotiation |

## F.3 Movement and barriers

**Table 15 — Movement and barrier parameters**

| # | Parameter name | Meaning | Example value | Status |
|---|---|---|---|---|
| 1 | `[move set]` | A single orthogonal move; no diagonals | 4 + stay | fixed |
| 2 | `[barrier quota]` | The maximum number of barriers the cop is entitled to place | 14 | minimum |
| 3 | `[step ceiling]` | The maximum number of moves in a sub-game | 35 | minimum |
| 4 | `[survival threshold]` | Steps the thief must survive to win | 35 | minimum |

## F.4 Dynamic pheromones

**Table 16 — Dynamic pheromone parameters**

| # | Parameter name | Meaning | Example value | Status |
|---|---|---|---|---|
| 1 | `[scent strength at focus]` | The pheromone strength in the emitting cell | 0.9 | fixed |
| 2 | `[scent decay rate]` | The decay rate every turn | 0.10 | fixed |
| 3 | `[scent field size]` | The edge of the emission window around the agent | 5×5 | fixed |

## F.5 Scoring

**Table 17 — Scoring parameters (win, survival and tie)**

| # | Parameter name | Meaning | Example value | Status |
|---|---|---|---|---|
| 1 | `[capture score – cop]` | Score to the cop for a successful capture | 20 | fixed |
| 2 | `[capture score – thief]` | Score to the thief on a capture | 5 | fixed |
| 3 | `[survival score – cop]` | Score to the cop on the thief's survival | 5 | fixed |
| 4 | `[survival score – thief]` | Score to the thief for successful survival | 10 | fixed |
| 5 | `[tie score]` | Score to each side when the accumulated score of all the sub-games against an opponent ends in a tie | 2 | fixed |

## F.6 Network and league

**Table 18 — Network and league parameters**

| # | Parameter name | Meaning | Example value | Status |
|---|---|---|---|---|
| 1 | `[number of sub-games]` | Sub-games in a series against an opponent | 6 | fixed |
| 2 | `[diversity reward]` | Score for a win against a new opponent | 10 | fixed |
| 3 | `[minimum games to pass]` | The minimum number of games for every group in order to obtain a passing score in the project | 2 | fixed |
| 4 | `[token estimate per series]` | The total language-model tokens each group is entitled to consume; the actual consumption is reported by email | ~200000 | negotiation |
| 5 | `[maximum games per group]` | The maximum number of games each group is entitled to play | 10 | fixed |

## F.7 Rate limiter and protection (the Gatekeeper template)

**Table 19 — Network, rate-limiter and protection parameters (the Gatekeeper template)**

| # | Parameter name | Meaning | Example value | Status |
|---|---|---|---|---|
| 1 | `[requests per minute]` | Maximum rate of outgoing API requests | 30 | minimum |
| 2 | `[concurrent requests]` | The maximum number of concurrent requests | 2 | minimum |
| 3 | `[delay after an error]` | Wait before a retry | 5 s | minimum |
| 4 | `[retries]` | The number of attempts before failure | 3 | minimum |
| 5 | `[queue depth]` | The size of the request queue under load | 100 | minimum |
| 6 | `[response time limit]` | A timeout for every network request | 30 s | negotiation |
| 7 | `[watchdog threshold]` | Freeze time before Watchdog intervention | 60 s | negotiation |

## F.8 Status-column definitions

The "status" column in the tables above receives one of three values, whose binding meaning is defined
thus:

- **minimum.** The sides are entitled to negotiate the value, but only and exclusively in the direction
  that makes the game harder (generally by enlarging the value) — never in the direction of an easement
  below the example value. In the absence of an express agreed definition between the sides, the code must
  guarantee that the example value is the default the group uses.
- **fixed.** A binding value that cannot be changed at all. **A deviation from this value disqualifies the
  group.**
- **negotiation.** The sides are entitled to agree on **any** value whatsoever. In the absence of an
  express agreed definition between the sides, the code must guarantee that the example value is the
  default the group uses.

## F.9 Mandatory instructions

1. Every group must define **all** the values above in the configuration file. The groups must verify that
   these values are **identical** between the two groups, and lock them cryptographically.
2. In every new game the group is entitled to change the definitions, as long as they are consistent with
   the agreement with the opposing group.
3. Every configuration file must be given a **different** name matching the game, so as to enable easy
   reconstruction of every game's configuration.
4. It is mandatory to attach the configuration file of every game to the GitHub repository.
5. Every group is permitted to change the code between games; therefore, for every game an email must be
   sent to the lecturer containing the **Commit number** in GitHub that was used in that game.

## F.10 Variables of the attached files, the repository and the addresses

Attached to this book are **four example JSON files** — pre-game declaration, the agreed configuration, the
sub-game log and the results report — which illustrate the full usage format; an explanation of each file's
contents and role appears in Chapter 9. The table below defines the variable-name for each file, and also
the example code repository and the lecturer's two email addresses, and these are the names the book uses
everywhere. This table is a reference table only — it is not part of the agreed configuration file and is
not subject to negotiation. The file names are derived from the game identifier (`game_id`) and the
sub-game number (`<NN>`), so that files from different games are never mixed.

**Table 20 — Variables of the attached files, the code repository and the lecturer's addresses**

| Variable name | Role and contents | Value |
|---|---|---|
| `[declaration file]` | Pre-game declaration: all the fixed data of the game — groups, members, repositories, hardware, model, tokens and times | `declaration_<game_id>.json` |
| `[configuration file]` | The agreed configuration: the sub-game parameters, cryptographically locked | `config_<game_id>_g<NN>.json` |
| `[log file]` | The sub-game log, for full cryptographic verification in the replay simulator | `log_<game_id>_g<NN>.json` |
| `[results file]` | The final results report, for weighting the league score by the lecturer | `result_<game_id>.json` |
| `[example code repository]` | The reference implementation of the game on GitHub | https://github.com/rmisegal/Game-P2P-Cop-Chase |
| `[lecturer address]` | General mail and sharing of GitHub repositories | rmisegal@gmail.com |
| `[agent reporting address]` | The target for the JSON reports the agent sends automatically | rmisegal+uoh26finalgame@gmail.com |

## F.11 Language-model modes for the verbal game

This table documents the language model's four operating modes, all of which touch on the deception text
**only and exclusively** — **the movement decision is always algorithmic and in Python code** (see Chapter
6). The mode is chosen in the private configuration file (`[trash_talk] provider`), and it is what
determines how much of `[token estimate per series]` the group will spend on speech. This table is a
reference table only — the choice is private to every peer; it is **not** part of the agreed configuration
file and is not subject to negotiation.

**Table 21 — Language-model modes for the verbal game (a private choice for every peer)**

| Mode | Where it runs and token cost | Rate limit | Account and installation |
|---|---|---|---|
| `template` | In process; deception sentences chosen in advance in code — **zero tokens**. The default | — | None; offline and free |
| `ollama` | A local model via Ollama at `localhost:11434` — zero API tokens | None | Installing Ollama and pulling a model |
| `claude_api` | A small cloud model (e.g. Haiku) through the API — real consumption counted against `[token estimate per series]` | By account | An Anthropic API key (paid account) |
| `claude_cli` | Running `claude -p` through the Claude Code CLI — the highest cost | By subscription | A Claude CLI subscription |

The `every_n_steps` parameter runs the model only once every so many turns and reduces consumption
further. In `template` and `ollama` mode a whole series of `[number of sub-games]` sub-games can be played
at **zero tokens**, and the entire competition then turns on the quality of the movement algorithm.

## F.12 Strategy-module selection

The movement policy — **the heart of the score** — is chosen in the private configuration file
(`[strategy]`). Leaving the section empty runs the built-in heuristic brain of the reference
implementation. To run your own strategy, point one of the keys at your "brain" class, inheriting from
`BrainBase` and overriding `_pick_move` (and for the cop also `_decide_move` — the barrier). This table is
a reference table only — the choice is private to every peer and is not subject to negotiation. Full
detail in `docs/STRATEGY.md` and in Appendix D.

**Table 22 — Keys for choosing the strategy module (a private choice for every peer)**

| Key (`[strategy]`) | Role | How to override |
|---|---|---|
| `thief_class` | Your thief's brain, written `package.module:Class` | Inherit from `ThiefBrain` and override `_pick_move` and/or `_decide_move` |
| `police_class` | Your cop's brain | As above; for the cop `_decide_move` also chooses the barrier |

---

**End of book.** You have reached the end of the rules and guidelines book of the final project. Good luck!
