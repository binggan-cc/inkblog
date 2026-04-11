"""ink_core.agent — OpenClaw Agent Mode data models and constants."""

from __future__ import annotations

from dataclasses import dataclass

VALID_CATEGORIES: list[str] = ["work", "learning", "skill-installed", "memory", "note"]


@dataclass
class LogEntry:
    date: str       # YYYY-MM-DD
    time: str       # HH:MM (local time)
    category: str   # one of VALID_CATEGORIES
    content: str    # raw entry text
    source: str     # Daily Journal canonical_id, e.g. "2026/04/10-journal"


@dataclass
class SkillRecord:
    name: str
    type: str           # "external" | "custom"
    source: str         # URL (external) or "local" (custom)
    version: str        # may be empty string
    install_path: str   # absolute path or relative ".ink/skills/<name>.md"
    installed_at: str   # ISO 8601 timestamp
