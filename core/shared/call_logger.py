"""Every external call, recorded (TODO 7.1.1, PRD 7 §3.1 req. 7.5).

The cost analysis the report carries is only as good as this list. It is also
the only evidence available after the fact about *why* a Gatekeeper refusal
happened — a locked pipe with no record of what led to it tells whoever is
debugging at 2 a.m. nothing they can act on.

So refusals are logged as carefully as successes. A call the quota rejected
never reached the provider, but it is exactly the entry that explains the
report that did not arrive.

**Naming discipline (PRD 7 §3.1).** ``llm_tokens`` here means model tokens and
nothing else. Rate-limiter currency is ``rate_tokens`` in
:mod:`core.shared.rate_limiter`; OAuth material is ``oauth_token``. The three
never share an identifier.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

__all__ = ["CallRecord", "CallLogger", "OK", "REFUSED", "FAILED"]

OK = "ok"
REFUSED = "refused"
FAILED = "failed"


@dataclass(frozen=True)
class CallRecord:
    """One attempt to reach an external service.

    Attributes:
        target: What was being called, e.g. ``gmail.send`` or ``groq.generate``.
        started_at: Clock reading when the attempt began.
        duration_sec: Wall time spent. Zero for a call refused before it ran.
        outcome: ``ok``, ``refused`` (a gate said no) or ``failed`` (it ran and
            errored). Three values rather than a boolean, because "did not
            happen" and "happened and broke" call for different fixes.
        detail: The error or the refusing gate. Empty on success.
        attempts: Including the first. Above 1 means a 429 was backed off.
        llm_tokens: Model tokens spent, when the call was to a model.
    """

    target: str
    started_at: float
    duration_sec: float = 0.0
    outcome: str = OK
    detail: str = ""
    attempts: int = 1
    llm_tokens: int = 0


@dataclass
class CallLogger:
    """The append-only record of everything that left this process.

    Attributes:
        records: Every call, in order.
    """

    records: list[CallRecord] = field(default_factory=list)

    def record(self, entry: CallRecord) -> CallRecord:
        """Append *entry* and return it."""
        self.records.append(entry)
        return entry

    @property
    def total_llm_tokens(self) -> int:
        """Model tokens across every call, for `result_<game_id>.json` (M#54)."""
        return sum(entry.llm_tokens for entry in self.records)

    def count(self, outcome: str) -> int:
        """How many calls ended in *outcome*."""
        return sum(1 for entry in self.records if entry.outcome == outcome)

    @property
    def retried(self) -> int:
        """How many calls needed more than one attempt."""
        return sum(1 for entry in self.records if entry.attempts > 1)

    def to_json(self) -> list[dict]:
        """Return the log as plain dicts, ready for the report artefact."""
        return [asdict(entry) for entry in self.records]

    def describe(self) -> str:
        """One line for the post-match report."""
        if not self.records:
            return "no external calls"
        parts = [f"{len(self.records)} calls", f"{self.count(OK)} ok"]
        for outcome in (REFUSED, FAILED):
            if found := self.count(outcome):
                parts.append(f"{found} {outcome}")
        if self.retried:
            parts.append(f"{self.retried} retried")
        if self.total_llm_tokens:
            parts.append(f"{self.total_llm_tokens} llm_tokens")
        return ", ".join(parts)
