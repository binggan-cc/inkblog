"""Publish history data models."""

from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ChannelPublishRecord:
    channel: str
    status: str              # "success" | "draft_saved" | "failed"
    attempted_at: str        # ISO timestamp
    published_at: str | None = None
    error: str | None = None


class PublishHistoryManager:
    """Manages publish history records under .ink/publish-history/."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root
        self._base_dir = workspace_root / ".ink" / "publish-history"

    def _history_dir(self, canonical_id: str) -> Path:
        """Return the directory for a given canonical_id."""
        return self._base_dir / canonical_id

    def _filename(self, session_id: str, attempted_at: str) -> str:
        """Generate YYYYMMDD-HHMMSS-publish-<hash>.json filename."""
        # Derive timestamp portion from attempted_at (ISO format)
        # attempted_at: "2025-03-20T10:30:00" → "20250320-103000"
        ts = attempted_at.replace("-", "").replace("T", "-").replace(":", "")[:15]
        # ts is now "20250320-103000"
        short_hash = hashlib.sha1(session_id.encode()).hexdigest()[:6]
        return f"{ts}-publish-{short_hash}.json"

    def record(
        self,
        session_id: str,
        canonical_id: str,
        attempted_at: str,
        records: list[ChannelPublishRecord],
    ) -> Path:
        """Write a publish history record and return the file path."""
        history_dir = self._history_dir(canonical_id)
        history_dir.mkdir(parents=True, exist_ok=True)

        filename = self._filename(session_id, attempted_at)
        file_path = history_dir / filename

        data = {
            "session_id": session_id,
            "canonical_id": canonical_id,
            "attempted_at": attempted_at,
            "channels": [dataclasses.asdict(r) for r in records],
        }

        file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return file_path

    def get_history(self, canonical_id: str) -> list[dict]:
        """Return all history records for a canonical_id, sorted by filename."""
        history_dir = self._history_dir(canonical_id)
        if not history_dir.exists():
            return []

        files = sorted(history_dir.glob("*.json"))
        result = []
        for f in files:
            try:
                result.append(json.loads(f.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                pass
        return result

    def get_latest(self, canonical_id: str) -> dict | None:
        """Return the most recent history record, or None if none exist."""
        history_dir = self._history_dir(canonical_id)
        if not history_dir.exists():
            return None

        files = sorted(history_dir.glob("*.json"))
        if not files:
            return None

        try:
            return json.loads(files[-1].read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
