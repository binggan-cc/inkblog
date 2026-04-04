"""Article data model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Article:
    path: Path           # Absolute path to the article directory
    canonical_id: str    # YYYY/MM/DD-slug (no trailing slash)
    folder_name: str     # DD-slug (date-prefixed directory name)
    slug: str            # Pure slug without date prefix
    date: str            # YYYY-MM-DD
    l0: str              # .abstract content
    l1: dict             # Parsed .overview dict
    l2: str              # Raw index.md content
