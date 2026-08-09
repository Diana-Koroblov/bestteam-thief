"""Writing the four artefacts a match must leave behind (TODO 9.5, 7.2.1-7.2.4).

`core/report/artefacts.py` knows how to *build* a declaration, a config snapshot
and a result; `core/report/match_log.py` knows how to build a log. Until now
nothing called any of them, so the project could play a match and file nothing —
and the four files are what a grader actually reads (Ch. 9.2).

This is the join, and it lives in the runtime for the reason M#3 gives: it needs
the driver, the config and the report builders at once, and no two of those may
reach each other directly.

**Everything is written under one `game_id`.** Both of our processes — the Cop
repository for its sub-games and the Thief repository for the others — file into
the same directory under the same identifier, which is what makes six logs from
two processes one match rather than two halves nobody can join up (7.2.5).

**A log is written even when the sub-game was lost on a timeout.** It is at its
most useful precisely then: an empty directory says nothing about whose peer
went quiet, and the log with its steps and its verdict says exactly that.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.report.artefacts import build_config_snapshot, build_declaration, build_result, write
from core.report.identifiers import artefact_name
from core.report.match_log import build_log
from core.report.merge import load_rows, merge_rows, series_block

__all__ = ["MatchFiling"]


@dataclass
class MatchFiling:
    """Files this peer's artefacts for one match.

    Attributes:
        game_id: The shared identifier both peers derive (7.2.5). Shared, so the
            two teams' reports describe one match.
        directory: Where the files land. Both of our role processes point here.
        config: What we played under. Only its `shared` half is snapshotted.
        role_split: The negotiated plan, recorded so a reader can tell a 3-3
            series from an uneven one without counting the logs (C-011).
        agreed_digest: The `config_sha256` actually exchanged at the handshake.
            Checked against the config in the snapshot, and a mismatch refuses
            to write — see `build_config_snapshot`.
        github_commit: From Step-0, naming the code that played (M#53).
        written: Every path filed, in order, for the caller to report and for
            the email to attach.
    """

    game_id: str
    directory: Path
    config: Any
    role_split: str = "3-3"
    agreed_digest: str = ""
    scent_model_digest: str = ""
    readings: dict[str, str] = field(default_factory=dict)
    github_commit: str = ""
    repos: dict[str, str] = field(default_factory=dict)
    written: list[Path] = field(default_factory=list)

    def declaration(
        self,
        teams: dict[str, list[str]],
        mcp_urls: dict[str, str],
        llm_model: str,
        token_cap: int,
    ) -> Path:
        """File `declaration_<game_id>.json`, once per match (7.2.1)."""
        return self._write(
            build_declaration(
                game_identifier=self.game_id,
                teams=teams,
                repos=self.repos,
                mcp_urls=mcp_urls,
                llm_model=llm_model,
                token_cap=token_cap,
            ),
            "declaration",
        )

    def sub_game(self, report: Any, driver: Any) -> list[Path]:
        """File the config snapshot and the log for one sub-game (7.2.2, 7.2.3).

        Both, together, and in that order. A log names a `config_sha256` it
        cannot itself explain, so filing one without the snapshot beside it
        produces a record whose physics nobody can reconstruct — *"a log without
        its config is a list of moves nobody can score"*.
        """
        snapshot = self._write(
            build_config_snapshot(
                game_identifier=self.game_id,
                sub_game=report.sub_game,
                shared_config=self.config.shared,
                role=report.role.value,
                agreed_digest=self.agreed_digest,
                role_split=self.role_split,
                scent_model_digest=self.scent_model_digest,
                readings=self.readings,
            ),
            "config",
            report.sub_game,
        )
        log = self._write(
            build_log(
                game_identifier=self.game_id,
                sub_game=report.sub_game,
                role=report.role.value,
                steps=[record.entry for record in driver.records],
                # Ours, released now that the sub-game is over (M#18). Held any
                # longer and the log we file is one nobody — including us — can
                # verify.
                nonces=driver.nonces,
                outcome=report.outcome.reason,
                config_sha256=self.config.shared_digest(),
            ),
            "log",
            report.sub_game,
        )
        return [snapshot, log]

    @property
    def result_path(self) -> Path:
        """Where `result_<game_id>.json` lives.

        The one artefact named for the whole match rather than for a sub-game,
        and therefore the one both of our role processes have to share.
        """
        return self.directory / artefact_name("result", self.game_id)

    def result(self, series: Any, table: Any) -> Path:
        """File `result_<game_id>.json` for the whole series (7.2.4, M#49).

        **Merged with whatever is already there, never overwritten.** Our two
        role processes each finish a half of a 3-3 split and each file this, so
        the second to run used to replace a report covering the first three
        sub-games with one covering the three it had played itself — a file
        that was internally consistent and contradicted both the opponent's
        report and our own logs sitting beside it (M#35).

        Totals and league credit are recomputed over the **merged** rows rather
        than carried from *series*, which knows only this process's half. See
        `core/report/merge.py`.
        """
        rows = merge_rows(load_rows(self.result_path), series.rows(table))
        return self._write(
            build_result(
                game_identifier=self.game_id,
                sub_games=rows,
                github_commit=self.github_commit,
                # M#54 wants the series total. Zero is the honest number on the
                # `template` provider, which spends no model tokens at all —
                # and it stops being honest the moment a provider is switched
                # on, which is what TODO 9.6 wires up.
                total_llm_tokens=0,
                repos=self.repos,
                series=series_block(rows, table),
            ),
            "result",
        )

    def _write(self, payload: dict[str, Any], kind: str, sub_game: int | None = None) -> Path:
        """Write one artefact, remember it, and return where it went."""
        path = write(payload, self.directory, artefact_name(kind, self.game_id, sub_game))
        self.written.append(path)
        return path
