"""RecallCommand — search past journal entries and return structured JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ink_core.cli.builtin import BuiltinCommand
from ink_core.skills.base import SkillResult


class RecallCommand(BuiltinCommand):
    """Search Daily Journal entries and return Recall_Result JSON (agent mode only)."""

    def __init__(self, workspace_root: Path) -> None:
        self._root = workspace_root

    @property
    def name(self) -> str:
        return "recall"

    def run(self, target: str | None, params: dict) -> SkillResult:
        from ink_core.agent.journal import JournalManager
        from ink_core.agent.recall import RecallEngine
        from ink_core.core.config import InkConfig

        config = InkConfig(workspace_root=self._root)
        config.load()

        # Guard: agent mode only
        if config.get("mode") != "agent":
            return SkillResult(
                success=False,
                message="ink recall requires agent mode. Set mode: agent in .ink/config.yaml",
            )

        query = target or params.get("query", "")
        category = params.get("category") or None
        since = params.get("since") or None

        # Validate limit
        raw_limit = params.get("limit", 20)
        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            limit = -1
        if not (1 <= limit <= 500):
            return SkillResult(
                success=False,
                message=f"Invalid --limit '{raw_limit}'. Must be an integer between 1 and 500.",
            )

        # Collect all journal entries
        journal_mgr = JournalManager(self._root, config)
        all_entries = []
        for path in journal_mgr.list_journal_paths(since=since):
            all_entries.extend(journal_mgr.parse_entries(path))

        # Search
        engine = RecallEngine()
        results = engine.search(
            all_entries,
            query,
            category=category,
            since=since,
            limit=limit,
        )

        recall_result = {
            "query": query,
            "total": len(results),
            "entries": [
                {
                    "date": e.date,
                    "time": e.time,
                    "category": e.category,
                    "content": e.content,
                    "source": e.source,
                }
                for e in results
            ],
        }

        # Print to stdout for CLI/machine consumers
        print(json.dumps(recall_result, ensure_ascii=False, indent=2))

        return SkillResult(
            success=True,
            message=f"Found {len(results)} entries.",
            data=recall_result,
        )
