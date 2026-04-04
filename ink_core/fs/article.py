"""Article data model."""

from __future__ import annotations

import re
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


class SlugResolver:
    """Generates slugs from titles and checks for path conflicts."""

    MAX_SLUG_LENGTH = 60

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root

    def generate_slug(self, title: str) -> str:
        """Generate a URL-friendly slug from a title.

        - Converts to lowercase
        - Replaces CJK/non-alphanumeric chars with hyphens
        - Collapses multiple hyphens into one
        - Strips leading/trailing hyphens
        - Returns "untitled" if result is empty
        - Truncates to 60 chars at word boundary if possible
        """
        slug = title.lower()
        # Replace CJK characters and non-ASCII-alphanumeric chars with hyphens.
        # Keep only ASCII letters (a-z) and digits (0-9).
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        # Collapse multiple hyphens
        slug = re.sub(r'-+', '-', slug)
        # Strip leading/trailing hyphens
        slug = slug.strip('-')

        if not slug:
            return 'untitled'

        if len(slug) <= self.MAX_SLUG_LENGTH:
            return slug

        # Truncate at word boundary (hyphen) if possible
        truncated = slug[:self.MAX_SLUG_LENGTH]
        last_hyphen = truncated.rfind('-')
        if last_hyphen > 0:
            truncated = truncated[:last_hyphen]
        return truncated.strip('-')

    def check_conflict(self, date: str, slug: str) -> bool:
        """Check if the target article path already exists.

        Args:
            date: Date string in "YYYY-MM-DD" format
            slug: Article slug

        Returns:
            True if the path exists, False otherwise
        """
        year, month, day = date.split('-')
        folder_name = f"{day}-{slug}"
        target_path = self.workspace_root / year / month / folder_name
        return target_path.exists()
