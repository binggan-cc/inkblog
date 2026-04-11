"""SkillIndexManager — manages _index/skills.json for OpenClaw Agent Mode."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from ink_core.agent import SkillRecord


class SkillIndexManager:
    """Reads and writes _index/skills.json with upsert semantics."""

    def __init__(self, workspace_root: Path) -> None:
        self._index_path = workspace_root / "_index" / "skills.json"

    def upsert(self, skill: SkillRecord) -> None:
        """Insert or update a skill record (matched by name)."""
        records = self.list_all()
        updated = False
        for i, r in enumerate(records):
            if r.name == skill.name:
                records[i] = skill
                updated = True
                break
        if not updated:
            records.append(skill)
        self._write(records)

    def list_all(self) -> list[SkillRecord]:
        """Return all skill records; empty list if file absent."""
        if not self._index_path.exists():
            return []
        try:
            data = json.loads(self._index_path.read_text(encoding="utf-8"))
            return [SkillRecord(**item) for item in data]
        except (json.JSONDecodeError, TypeError, KeyError):
            return []

    def _write(self, records: list[SkillRecord]) -> None:
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        self._index_path.write_text(
            json.dumps([asdict(r) for r in records], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
