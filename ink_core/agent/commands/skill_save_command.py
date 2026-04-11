"""SkillSaveCommand — copy a custom skill .md file into .ink/skills/ in agent mode."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ink_core.agent import SkillRecord
from ink_core.cli.builtin import BuiltinCommand
from ink_core.skills.base import SkillResult

_REQUIRED_FRONTMATTER = {"skill", "version", "context_requirement"}


class SkillSaveCommand(BuiltinCommand):
    """Save a custom skill definition file to .ink/skills/ (agent mode only)."""

    def __init__(self, workspace_root: Path) -> None:
        self._root = workspace_root

    @property
    def name(self) -> str:
        return "skill-save"

    def run(self, target: str | None, params: dict) -> SkillResult:
        from ink_core.agent.journal import JournalManager
        from ink_core.agent.skill_index import SkillIndexManager
        from ink_core.core.config import InkConfig

        config = InkConfig(workspace_root=self._root)
        config.load()

        if config.get("mode") != "agent":
            return SkillResult(
                success=False,
                message="ink skill-save requires agent mode. Set mode: agent in .ink/config.yaml",
            )

        skill_name = target or params.get("name", "")
        if not skill_name:
            return SkillResult(success=False, message="Skill name is required.")

        file_path_str = params.get("file", "")
        if not file_path_str:
            return SkillResult(success=False, message="--file is required for ink skill-save.")

        source_file = Path(file_path_str)
        if not source_file.exists():
            return SkillResult(
                success=False,
                message=f"Skill file not found: {file_path_str}",
            )

        # Validate frontmatter
        content = source_file.read_text(encoding="utf-8")
        missing = self._check_frontmatter(content)
        if missing:
            return SkillResult(
                success=False,
                message=f"Invalid skill file: missing required fields: {', '.join(sorted(missing))}",
            )

        # Copy to .ink/skills/
        skills_dir = self._root / ".ink" / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        dest = skills_dir / f"{skill_name}.md"
        shutil.copy2(source_file, dest)

        install_path = f".ink/skills/{skill_name}.md"
        fm = self._parse_frontmatter(content)
        record = SkillRecord(
            name=skill_name,
            type="custom",
            source="local",
            version=fm.get("version", ""),
            install_path=install_path,
            installed_at=datetime.now(tz=timezone.utc).isoformat(),
        )

        SkillIndexManager(self._root).upsert(record)

        journal_mgr = JournalManager(self._root, config)
        from datetime import date
        today = date.today().isoformat()
        journal_mgr.append_entry(
            today,
            "skill-installed",
            f"Saved custom skill: {skill_name} (type: custom, path: {install_path})",
        )

        # Git auto-commit
        if config.get("git.auto_commit"):
            self._git_commit(dest, skill_name)

        return SkillResult(
            success=True,
            message=f"Saved custom skill: {skill_name} → {install_path}",
            data={"skill": record.__dict__},
            changed_files=[dest],
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _check_frontmatter(content: str) -> set[str]:
        """Return set of missing required frontmatter fields."""
        fm = SkillSaveCommand._parse_frontmatter(content)
        return _REQUIRED_FRONTMATTER - set(fm.keys())

    @staticmethod
    def _parse_frontmatter(content: str) -> dict:
        if not content.startswith("---"):
            return {}
        end = content.find("---", 3)
        if end == -1:
            return {}
        try:
            return yaml.safe_load(content[3:end]) or {}
        except yaml.YAMLError:
            return {}

    def _git_commit(self, dest: Path, skill_name: str) -> None:
        from ink_core.git.manager import GitManager
        git = GitManager(self._root)
        if git.is_repo():
            git.aggregate_commit([dest], f"skill: add {skill_name}")
