"""Session logger for ink commands."""

from __future__ import annotations

import json
from pathlib import Path

from ink_core.core.executor import ExecutionContext


class SessionLogger:
    """Records ink command sessions to .ink/sessions/."""

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root
        self._sessions_dir = workspace_root / ".ink" / "sessions"

    def log(self, context: ExecutionContext, result: str, duration_ms: int) -> Path:
        """Write a session record to .ink/sessions/YYYYMMDD-HHMMSS-<command>.json.

        Returns the path of the written file.
        """
        self._sessions_dir.mkdir(parents=True, exist_ok=True)

        ts = context.started_at.strftime("%Y%m%d-%H%M%S")
        filename = f"{ts}-{context.command}.json"
        file_path = self._sessions_dir / filename

        # Serialize changed_files: relative to workspace_root when possible
        changed_files: list[str] = []
        for p in context.changed_files:
            try:
                changed_files.append(str(p.relative_to(self._workspace_root)))
            except ValueError:
                changed_files.append(str(p))

        record = {
            "session_id": context.session_id,
            "timestamp": context.started_at.isoformat(timespec="seconds"),
            "command": context.command,
            "target": context.target,
            "params": context.params,
            "result": result,
            "changed_files": changed_files,
            "duration_ms": duration_ms,
        }

        file_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return file_path

    def recent(self, n: int = 10) -> list[dict]:
        """Return the most recent n session records, sorted by filename descending."""
        if not self._sessions_dir.exists():
            return []

        files = sorted(self._sessions_dir.glob("*.json"), key=lambda p: p.name, reverse=True)
        results: list[dict] = []
        for f in files[:n]:
            try:
                results.append(json.loads(f.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                continue
        return results
