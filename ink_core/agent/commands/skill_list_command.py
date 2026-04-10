"""SkillListCommand — list all recorded skills in agent mode."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from ink_core.cli.builtin import BuiltinCommand
from ink_core.skills.base import SkillResult


class SkillListCommand(BuiltinCommand):
    """List all skills in _index/skills.json (agent mode only)."""

    def __init__(self, workspace_root: Path) -> None:
        self._root = workspace_root

    @property
    def name(self) -> str:
        return "skill-list"

    def run(self, target: str | None, params: dict) -> SkillResult:
        from ink_core.agent.skill_index import SkillIndexManager
        from ink_core.core.config import InkConfig

        config = InkConfig(workspace_root=self._root)
        config.load()

        if config.get("mode") != "agent":
            return SkillResult(
                success=False,
                message="ink skill-list requires agent mode. Set mode: agent in .ink/config.yaml",
            )

        records = SkillIndexManager(self._root).list_all()

        if not records:
            return SkillResult(
                success=True,
                message="No skills recorded.",
                data={"skills": []},
            )

        lines = []
        for r in records:
            ver = f" v{r.version}" if r.version else ""
            lines.append(f"  {r.name}{ver} [{r.type}] installed_at={r.installed_at}")
        message = "Recorded skills:\n" + "\n".join(lines)

        return SkillResult(
            success=True,
            message=message,
            data={"skills": [asdict(r) for r in records]},
        )
