"""Execution context for a single ink command."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class ExecutionContext:
    session_id: str          # Format: YYYYMMDD-HHMMSS-<action>-<hash>
    command: str
    target: str | None       # Canonical ID, reserved value, or None
    params: dict
    changed_files: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
