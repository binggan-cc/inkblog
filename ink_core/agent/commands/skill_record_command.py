"""SkillRecordCommand — record an externally-installed skill in agent mode."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ink_core.agent import SkillRecord
from ink_core.cli.builtin import BuiltinCommand
from ink_core.skills.base import SkillResult


class SkillRecordCommand(BuiltinCommand):
    """Record metadata of an externally-installed skill (agent mode only)."""

    def __init__(self, workspace_root: Path) -> None:
        self._root = workspace_root

    @property
    def name(self) -> str:
        return "skill-record"

    def run(self, target: str | None, params: dict) -> SkillResult:
        from ink_core.agent.journal import JournalManager
        from ink_core.agent.skill_index import SkillIndexManager
        from ink_core.core.config import InkConfig

        config = InkConfig(workspace_root=self._root)
        config.load()

        if config.get("mode") != "agent":
            return SkillResult(
                success=False,
                message="ink skill-record requires agent mode. Set mode: agent in .ink/config.yaml",
            )

        skill_name = target or params.get("name", "")
        if not skill_name:
            return SkillResult(success=False, message="Skill name is required.")

        source = params.get("source", "")
        if not source:
            return SkillResult(
                success=False,
                message="--source is required for external skill recording",
            )

        record = SkillRecord(
            name=skill_name,
            type="external",
            source=source,
            version=params.get("version", ""),
            install_path=params.get("path", ""),
            installed_at=datetime.now(tz=timezone.utc).isoformat(),
        )

        SkillIndexManager(self._root).upsert(record)

        journal_mgr = JournalManager(self._root, config)
        from datetime import date
        today = date.today().isoformat()
        journal_mgr.append_entry(
            today,
            "skill-installed",
            f"Recorded external skill: {skill_name} (source: {source}, version: {record.version})",
        )

        return SkillResult(
            success=True,
            message=f"Recorded external skill: {skill_name}",
            data={"skill": record.__dict__},
        )
