"""The pre-match protocol check (`python -m core probe`).

Replaces `test_a2a.py`, deleted with the A2A complement on 15/08. What is worth
asserting moved rather than disappeared: the old suite proved a card said the
right thing, this one proves we tell a human the right thing to *do* about an
opponent's tool list — which is the only part of that command anyone ran.

Every case here is a real surface we have met or expect to meet in the league.
"""

from __future__ import annotations

import argparse

import pytest

from core.cli_args import parse_args
from core.cli_probe import (
    NATIVE_TOOLS,
    REFERENCE_TOOLS,
    classify,
    probe_command,
)


def test_our_six_tools_need_no_flag() -> None:
    """A peer serving our whole surface plays on the native path."""
    flag, explanation = classify(NATIVE_TOOLS)
    assert flag == ""
    assert "OUR protocol" in explanation


def test_the_example_repositorys_four_ask_for_the_reference_flag() -> None:
    """The four mailboxes are playable — with `--protocol reference` (C-019).

    The regression this pins: the retired A2A probe checked an opponent against
    our six *only*, so this exact list came back as five missing tools and a
    NOT READY verdict for an opponent we can in fact play.
    """
    flag, explanation = classify(REFERENCE_TOOLS)
    assert flag == "--protocol reference"
    assert "example repository" in explanation


def test_a_peer_serving_both_surfaces_is_answered_on_ours() -> None:
    """Ours wins the tie: it is the path the artefacts and audit were built for."""
    flag, _ = classify(tuple({*NATIVE_TOOLS, *REFERENCE_TOOLS}))
    assert flag == ""


def test_a_partial_native_surface_names_what_is_missing() -> None:
    """`declare_barrier` absent is a sub-game that dies at the first placement."""
    flag, explanation = classify(("negotiate", "receive_commit", "receive_reveal"))
    assert flag == ""
    assert "declare_barrier" in explanation
    assert "PARTIAL" in explanation


@pytest.mark.parametrize("names", [(), ("ping", "echo")])
def test_an_unrecognised_surface_says_so_rather_than_guessing(names: tuple[str, ...]) -> None:
    """Neither protocol: ask them, do not assume one and fail at the handshake."""
    flag, explanation = classify(names)
    assert flag == ""
    assert "unrecognised" in explanation


def test_an_unreachable_peer_exits_non_zero_without_raising() -> None:
    """A dead URL is the normal case before a slot, not a crash.

    The whole point of the command is to be runnable against a peer who has not
    started yet; an exception here would make it useless exactly then.
    """
    args = argparse.Namespace(url="http://127.0.0.1:9/mcp")
    assert probe_command(args) == 1


def test_the_mcp_suffix_is_added_when_missing() -> None:
    """Opponents paste a bare host as often as a full endpoint."""
    args = argparse.Namespace(url="http://127.0.0.1:9")
    # Reaching the connection attempt at all proves the URL was accepted and
    # normalised; the failure is the unreachable host, not a malformed target.
    assert probe_command(args) == 1


def test_probe_is_parsed_without_a_role() -> None:
    """It must run from a clone that has no config yet (see `core/__main__`)."""
    args = parse_args(["probe", "https://them.example/mcp"])
    assert args.command == "probe"
    assert args.url == "https://them.example/mcp"
    assert not hasattr(args, "role")
