"""Unit tests for A2A coordination (Ch. 2.3).

Two things are worth a test here and the rest is decoration. First: **no game
message leaves or enters through this channel** — an A2A endpoint that quietly
accepted a commit would produce a move with no seal and no log entry, which is
the one failure the whole commit-reveal design exists to prevent. Second: the
card advertises the URL the request actually arrived on, because the same
process answers on localhost during a rehearsal and on an ngrok domain during a
match, and a card that hardcoded either is wrong half the time.

Nothing here opens a port. That is the point of keeping `core/a2a` free of
Starlette: the content of a card is decidable at a desk.
"""

from __future__ import annotations

import pytest

from core.a2a import CARD_PATHS, MESSAGE_PATHS, Coordination, Readiness
from core.infra.mcp_server import Route, base_url, build_server_spec

BASE = "https://denotatively-sciuroid-florine.ngrok-free.dev"


def _desk() -> Coordination:
    """A coordination desk with the values our config actually carries."""
    return Coordination(
        Readiness(
            team_name="bestteam",
            contact_label="bestteam-cop",
            role="cop",
            members=("Itay Malich", "Diana Koroblov"),
            repos={"cop": "https://example.test/cop", "thief": "https://example.test/thief"},
            mcp_tools=("negotiate", "receive_commit", "receive_reveal"),
            config_sha256="a58adb10",
        )
    )


def _ask(text: str) -> dict:
    """One inbound A2A message in the REST envelope their note documents."""
    return {"message": {"messageId": "1", "role": "ROLE_USER", "parts": [{"text": text}]}}


# --- the channel is coordination only ---------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "here is my receive_commit for step 0",
        "digest 9fbe1c and the nonce follows",
        "sending receive_reveal early to save time",
    ],
)
def test_a_game_message_over_a2a_is_refused_not_absorbed(text: str) -> None:
    """A move that never touched MCP was never sealed and cannot be replayed (M#18)."""
    _, body = _desk().answer(BASE, _ask(text))
    facts = body["parts"][1]["data"]
    assert facts["accepted"] is False
    assert "refused" in facts
    assert "REFUSED" in body["parts"][0]["text"]


def test_a_readiness_question_is_answered() -> None:
    _, body = _desk().answer(BASE, _ask("Confirm your MCP endpoint and timeout settings."))
    assert body["parts"][1]["data"]["accepted"] is True


def test_the_answer_states_the_five_things_they_asked_for() -> None:
    """The reply is the deliverable; a friendly answer that omits one is a re-ask."""
    _, body = _desk().answer(BASE, _ask("ready?"))
    facts = body["parts"][1]["data"]
    assert facts["agentCardUrl"] == f"{BASE}{CARD_PATHS[0]}"
    assert facts["a2aMessageUrl"] == f"{BASE}{MESSAGE_PATHS[0]}"
    assert facts["mcpUrl"] == f"{BASE}/mcp"
    assert facts["sendsFirstCommitAfterNegotiation"] is True
    assert facts["timeouts"]["sameAtEveryStep"] is True


def test_the_answer_does_not_promise_a_timeout_we_do_not_implement() -> None:
    """They proposed 60s then 10s. We wait one window at every step (M#6)."""
    facts = _desk().match_facts(BASE)
    assert facts["timeouts"]["responseTimeoutSec"] == 30.0
    assert facts["timeouts"]["patienceBeforeTechnicalLossSec"] == 60.0
    assert "10s" not in str(facts["timeouts"]["responseTimeoutSec"])


# --- envelopes --------------------------------------------------------------


def test_the_jsonrpc_envelope_is_answered_in_kind() -> None:
    """Their card says JSONRPC; their server accepts REST. We answer both."""
    payload = {
        "jsonrpc": "2.0",
        "id": 7,
        "method": "message/send",
        "params": {"message": {"parts": [{"text": "ready?"}]}},
    }
    status, body = _desk().answer(BASE, payload)
    assert (status, body["id"], body["jsonrpc"]) == (200, 7, "2.0")
    assert body["result"]["role"] == "ROLE_AGENT"


@pytest.mark.parametrize("payload", [None, [], {}, {"message": "hello"}, {"parts": "no"}])
def test_a_malformed_body_is_a_named_400_not_a_traceback(payload: object) -> None:
    """The sender is on another machine; our stack trace tells them nothing."""
    status, body = _desk().answer(BASE, payload)  # type: ignore[arg-type]
    assert status == 400
    assert body["error"]["code"] == "invalid_request"


# --- the card ---------------------------------------------------------------


def test_the_card_advertises_the_url_the_request_arrived_on() -> None:
    """Localhost in a rehearsal, ngrok in a match — one process, both correct."""
    card = _desk().card("http://127.0.0.1:8081")
    assert card["url"] == "http://127.0.0.1:8081/a2a/message:send"
    assert _desk().card(BASE)["url"] == f"{BASE}/a2a/message:send"


def test_the_card_keeps_the_private_half_private() -> None:
    """Appendix F Table 21 keeps the provider per peer; strategy is ours alone."""
    text = str(_desk().card(BASE))
    for secret in ("ollama", "groq", "template", "tie_epsilon", "bluff", "weight_separation"):
        assert secret not in text.lower()


def test_the_card_declares_the_tools_the_server_registers() -> None:
    """Advertising a tool we do not serve is a 404 discovered mid-match."""
    facts = _desk().match_facts(BASE)
    assert facts["mcpTools"] == ["negotiate", "receive_commit", "receive_reveal"]


# --- the transport seam -----------------------------------------------------


class _Request:
    """The two attributes `base_url` reads. Enough to test it without a server."""

    def __init__(self, headers: dict, scheme: str = "http", netloc: str = "0.0.0.0:8081"):
        self.headers = headers
        self.url = type("Url", (), {"scheme": scheme, "netloc": netloc})()


def test_a_tunnelled_request_is_reported_as_https_not_as_the_local_bind() -> None:
    """Uvicorn sees http://0.0.0.0:8081; the peer must be given the public name."""
    request = _Request({"x-forwarded-proto": "https", "x-forwarded-host": "them.ngrok.dev"})
    assert base_url(request) == "https://them.ngrok.dev"


def test_a_direct_request_falls_back_to_the_host_header() -> None:
    assert base_url(_Request({"host": "127.0.0.1:8081"})) == "http://127.0.0.1:8081"


def test_the_forwarded_chain_takes_the_first_hop() -> None:
    """Two proxies append; the client-facing one is first (RFC 7239 ordering)."""
    request = _Request({"x-forwarded-proto": "https, http", "x-forwarded-host": "a.dev, b.dev"})
    assert base_url(request) == "https://a.dev"


def test_routes_ride_the_match_server_and_do_not_disturb_the_tools() -> None:
    """One tunnel, one port: a second server would need a second public URL."""
    desk = _desk()
    routes = tuple(Route(path, ("POST",), desk.answer) for path in MESSAGE_PATHS)
    spec = build_server_spec({"negotiate": lambda payload: payload}, "cop", 8081, routes)
    assert spec.tool_names == ("negotiate",)
    assert spec.route_paths == tuple(sorted(MESSAGE_PATHS))
