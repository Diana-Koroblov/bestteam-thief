"""The reference path's log, and the round trip that proves it replays (M#20).

`build → write → read → verify` is the DoD, not inspection: a log that cannot
be re-audited off disk is not sufficient whatever fields it carries. These tests
run that circuit against records sealed by the real `core/compat/sealing.py`,
so a change to either end fails here rather than in a match.
"""

from __future__ import annotations

import json

from core.compat import sealing
from core.compat.match_log import build_sub_game_log, verify_sub_game_log
from core.report.artefacts import write

OURS, THEIRS = "bestteam", "yanell11"


def _record(step: int, who: str) -> dict:
    """Return one genuinely sealed `{payload, nonce, commit}`."""
    payload = {"step": step, "state": f"grid=7x7;self=[{step},0];barriers=[]",
               "move": "S", "intent": "truth", "hint": f"{who} moved", "verdict": "truth"}
    return {"payload": payload, **sealing.seal(payload)}


def _log(our_records=None, their_records=None, live=None) -> dict:
    ours = our_records if our_records is not None else [_record(n, OURS) for n in (1, 2)]
    theirs = their_records if their_records is not None else [_record(n, THEIRS) for n in (1, 2)]
    return build_sub_game_log(
        game_identifier=f"{OURS}-vs-{THEIRS}", sub_game=1, our_group=OURS,
        their_group=THEIRS, our_role="police", our_records=ours, their_records=theirs,
        live_commits=live if live is not None
        else {int(r["payload"]["step"]): r["commit"] for r in theirs},
        outcome="survival", config_sha256="abc123",
    )


class TestRoundTrip:
    def test_a_written_log_re_verifies_off_disk(self, tmp_path) -> None:
        """The whole point: what we file can be audited again without the match."""
        path = write(_log(), tmp_path, "log_g01.json")
        reloaded = json.loads(path.read_text(encoding="utf-8"))
        verdict = verify_sub_game_log(reloaded)
        assert verdict["passed"]
        assert verdict["sides"][OURS]["verified_steps"] == 2
        assert verdict["sides"][THEIRS]["verified_steps"] == 2

    def test_both_sides_records_are_filed(self) -> None:
        """An audit verdict names who failed; only the records show what was claimed."""
        log = _log()
        assert set(log["records"]) == {OURS, THEIRS}
        assert log["step_count"] == {OURS: 2, THEIRS: 2}


class TestItActuallyChecks:
    def test_a_tampered_payload_fails(self) -> None:
        """A rewritten payload no longer hashes to the commit filed beside it."""
        log = _log()
        log["records"][THEIRS][0]["payload"]["move"] = "N"
        verdict = verify_sub_game_log(log)
        assert not verdict["passed"]
        assert verdict["sides"][THEIRS]["failed_steps"] == [1]

    def test_a_resealed_record_fails_against_the_live_commit(self) -> None:
        """Self-consistency is not enough — this is the attack `live_commits` exists for.

        The record is re-sealed properly, so `commit_of(payload, nonce) == commit`
        holds and it passes on its own terms. It is still a different commit from
        the one that crossed the wire, which is what makes it a forgery.
        """
        theirs = [_record(1, THEIRS)]
        live = {1: theirs[0]["commit"]}
        forged = {"payload": {**theirs[0]["payload"], "move": "N"}}
        forged.update(sealing.seal(forged["payload"]))
        assert sealing.verify(forged["payload"], forged["nonce"], forged["commit"])

        verdict = verify_sub_game_log(_log(their_records=[forged], live=live))
        assert not verdict["passed"]
        assert verdict["sides"][THEIRS]["failed_steps"] == [1]

    def test_our_own_side_is_checked_for_self_consistency(self) -> None:
        """We never saw our own commits arrive, so ours is re-hashed and no more."""
        broken = _record(1, OURS)
        broken["commit"] = "0" * 64
        verdict = verify_sub_game_log(_log(our_records=[broken]))
        assert not verdict["passed"]
        assert verdict["sides"][OURS]["failed_steps"] == [1]


class TestShape:
    def test_live_commits_survive_a_json_round_trip(self, tmp_path) -> None:
        """JSON has no integer keys; the reader must get back what the writer wrote."""
        path = write(_log(), tmp_path, "log_g01.json")
        reloaded = json.loads(path.read_text(encoding="utf-8"))
        assert set(reloaded["live_commits"][THEIRS]) == {"1", "2"}
        assert verify_sub_game_log(reloaded)["passed"]

    def test_roles_name_both_sides_in_wire_vocabulary(self) -> None:
        assert _log()["roles"] == {OURS: "police", THEIRS: "thief"}
