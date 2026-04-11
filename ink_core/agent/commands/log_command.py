"""LogCommand — append a log entry to today's Daily Journal."""

from __future__ import annotations

from pathlib import Path

from ink_core.agent import VALID_CATEGORIES
from ink_core.cli.builtin import BuiltinCommand
from ink_core.skills.base import SkillResult


class LogCommand(BuiltinCommand):
    """Append a Log_Entry to the Daily Journal (agent mode only)."""

    def __init__(self, workspace_root: Path) -> None:
        self._root = workspace_root

    @property
    def name(self) -> str:
        return "log"

    def run(self, target: str | None, params: dict) -> SkillResult:
        from datetime import date, datetime

        from ink_core.agent.journal import JournalManager
        from ink_core.core.config import InkConfig

        config = InkConfig(workspace_root=self._root)
        config.load()

        # Guard: agent mode only
        if config.get("mode") != "agent":
            return SkillResult(
                success=False,
                message="ink log requires agent mode. Set mode: agent in .ink/config.yaml",
            )

        content = target or params.get("content", "")
        if not content:
            return SkillResult(success=False, message="Content is required for `ink log`.")

        # Validate category
        raw_category = params.get("category", "")
        if raw_category:
            category = raw_category.lower()
            if category not in VALID_CATEGORIES:
                return SkillResult(
                    success=False,
                    message=(
                        f"Invalid category '{raw_category}'. "
                        f"Valid values: {', '.join(VALID_CATEGORIES)}"
                    ),
                )
        else:
            category = config.get("agent.default_category", "note")

        today = date.today().isoformat()
        journal_mgr = JournalManager(self._root, config)

        # Req 1.4: auto_create_daily controls whether journal is created on demand
        if not config.get("agent.auto_create_daily", True):
            journal_dir = self._root / today.replace("-", "/", 1).replace("-", "/", 1)
            # Derive path: YYYY/MM/DD-journal/index.md
            year, month, day = today.split("-")
            index_path = self._root / year / month / f"{day}-journal" / "index.md"
            if not index_path.exists():
                return SkillResult(
                    success=False,
                    message=(
                        f"No journal exists for {today} and auto_create_daily is disabled. "
                        "Create the journal manually or set agent.auto_create_daily: true in config."
                    ),
                )

        entry = journal_mgr.append_entry(today, category, content)

        journal_path = journal_mgr.get_or_create_journal(today)[0]
        entry_text = f"## {entry.time} [{entry.category}]\n\n{content}"

        # Git auto-commit
        if config.get("git.auto_commit"):
            self._git_commit(journal_path, entry)

        return SkillResult(
            success=True,
            message=entry_text,
            changed_files=[journal_path],
        )

    def _git_commit(self, journal_path: Path, entry) -> None:
        from ink_core.git.manager import GitManager

        git = GitManager(self._root)
        if not git.is_repo():
            return
        short_content = entry.content[:60].replace("\n", " ")
        message = f"log: {entry.time} [{entry.category}] {short_content}"
        git.aggregate_commit([journal_path], message)
