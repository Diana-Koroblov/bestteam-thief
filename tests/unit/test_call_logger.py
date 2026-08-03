"""The record of everything that left this process (TODO 7.1.1, PRD 7 req. 7.5).

The cost analysis in `result_<game_id>.json` is only as good as this list, and
after a match it is the only account of *why* a Gatekeeper refusal happened. So
the summarising helpers are tested rather than assumed: a `describe()` that
quietly dropped the refusals would make a locked pipe look like a quiet match.
"""

from __future__ import annotations

from core.shared.call_logger import FAILED, OK, REFUSED, CallLogger, CallRecord


def build(*entries: CallRecord) -> CallLogger:
    """Return a logger holding *entries*."""
    logger = CallLogger()
    for entry in entries:
        logger.record(entry)
    return logger


def test_an_empty_log_says_so_rather_than_rendering_nothing() -> None:
    """A match that made no external call is a finding, not a blank line."""
    assert CallLogger().describe() == "no external calls"
    assert CallLogger().to_json() == []


def test_llm_tokens_are_summed_for_the_result_artefact() -> None:
    """**M#54.** The total the report carries is computed here, never passed in."""
    logger = build(
        CallRecord("groq.generate", started_at=0.0, llm_tokens=120),
        CallRecord("groq.generate", started_at=1.0, llm_tokens=80),
        CallRecord("gmail.send", started_at=2.0),
    )
    assert logger.total_llm_tokens == 200


def test_the_three_outcomes_are_counted_separately() -> None:
    """"Did not happen" and "happened and broke" call for different fixes."""
    logger = build(
        CallRecord("a", started_at=0.0, outcome=OK),
        CallRecord("b", started_at=1.0, outcome=REFUSED, detail="quota"),
        CallRecord("c", started_at=2.0, outcome=FAILED, detail="boom"),
    )
    assert (logger.count(OK), logger.count(REFUSED), logger.count(FAILED)) == (1, 1, 1)


def test_retried_calls_are_visible_without_reading_every_row() -> None:
    """A retry means a 429 was backed off, which is worth seeing at a glance."""
    logger = build(
        CallRecord("a", started_at=0.0, attempts=3),
        CallRecord("b", started_at=1.0),
    )
    assert logger.retried == 1


def test_the_summary_carries_every_outcome_that_occurred() -> None:
    logger = build(
        CallRecord("a", started_at=0.0),
        CallRecord("b", started_at=1.0, outcome=REFUSED, detail="locked"),
        CallRecord("c", started_at=2.0, outcome=FAILED, attempts=2, llm_tokens=40),
    )
    line = logger.describe()
    for expected in ("3 calls", "1 ok", "1 refused", "1 failed", "1 retried", "40 llm_tokens"):
        assert expected in line


def test_the_summary_omits_what_did_not_happen() -> None:
    """A clean match should not read as though it had failures worth reporting."""
    line = build(CallRecord("a", started_at=0.0)).describe()
    assert "refused" not in line and "failed" not in line and "retried" not in line


def test_the_log_serialises_to_plain_json_types() -> None:
    """It goes into an artefact a grader reads; no dataclass may leak into it."""
    rows = build(CallRecord("gmail.send", started_at=1.5, attempts=2)).to_json()
    assert rows == [
        {
            "target": "gmail.send",
            "started_at": 1.5,
            "duration_sec": 0.0,
            "outcome": OK,
            "detail": "",
            "attempts": 2,
            "llm_tokens": 0,
        }
    ]
