"""JournalManager — Daily Journal CRUD for OpenClaw Agent Mode."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from ink_core.agent import VALID_CATEGORIES, LogEntry
from ink_core.core.config import InkConfig


class JournalManager:
    """Manages Daily Journal files under YYYY/MM/DD-journal/."""

    _ENTRY_PATTERN = re.compile(
        r"^## (\d{2}:\d{2}) \[([^\]]+)\]\s*\n\n(.*?)(?=\n^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )

    def __init__(self, workspace_root: Path, config: InkConfig) -> None:
        self._root = workspace_root
        self._config = config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_or_create_journal(self, date: str) -> tuple[Path, bool]:
        """Get or create the Daily Journal index.md for the given date.

        Returns:
            (journal_index_path, was_created)
        """
        journal_dir = self._journal_dir(date)
        index_path = journal_dir / "index.md"

        if index_path.exists():
            return index_path, False

        journal_dir.mkdir(parents=True, exist_ok=True)

        agent_name = self._config.get("agent.agent_name", "OpenClaw")
        year, month, day = date.split("-")

        frontmatter = (
            f"---\n"
            f"title: \"{date} Journal\"\n"
            f"date: {date}\n"
            f"status: draft\n"
            f"tags:\n"
            f"  - journal\n"
            f"  - agent\n"
            f"agent: {agent_name}\n"
            f"---\n"
            f"\n"
            f"## Entries\n"
        )
        index_path.write_text(frontmatter, encoding="utf-8")

        # Generate L0 and L1 layer files (consistent with ArticleManager)
        self._generate_layers(index_path, date)

        return index_path, True

    def append_entry(self, date: str, category: str, content: str) -> LogEntry:
        """Append a Log_Entry to the Daily Journal for the given date.

        Normalises category to lowercase. Creates journal if absent.
        Returns the appended LogEntry.
        """
        category = category.lower()
        index_path, _ = self.get_or_create_journal(date)

        now = datetime.now()
        time_str = now.strftime("%H:%M")

        entry_text = f"\n## {time_str} [{category}]\n\n{content}\n"
        with open(index_path, "a", encoding="utf-8") as f:
            f.write(entry_text)

        year, month, day = date.split("-")
        folder_name = f"{day}-journal"
        canonical_id = f"{year}/{month}/{folder_name}"

        return LogEntry(
            date=date,
            time=time_str,
            category=category,
            content=content,
            source=canonical_id,
        )

    def parse_entries(self, journal_path: Path) -> list[LogEntry]:
        """Parse all Log_Entry blocks from a Daily Journal index.md."""
        if not journal_path.exists():
            return []

        text = journal_path.read_text(encoding="utf-8")

        # Derive date and canonical_id from path: YYYY/MM/DD-journal/index.md
        parts = journal_path.parts
        # parts[-3] = YYYY, parts[-2] = MM (unused individually), parts[-1] = "index.md"
        # path structure: <root>/YYYY/MM/DD-journal/index.md
        folder_name = journal_path.parent.name          # "DD-journal"
        month_dir = journal_path.parent.parent.name     # "MM"
        year_dir = journal_path.parent.parent.parent.name  # "YYYY"
        day = folder_name.split("-")[0]
        date_str = f"{year_dir}-{month_dir}-{day}"
        canonical_id = f"{year_dir}/{month_dir}/{folder_name}"

        entries: list[LogEntry] = []
        for m in self._ENTRY_PATTERN.finditer(text):
            time_str = m.group(1)
            category = m.group(2).strip()
            content = m.group(3).strip()
            entries.append(LogEntry(
                date=date_str,
                time=time_str,
                category=category,
                content=content,
                source=canonical_id,
            ))
        return entries

    def list_journal_paths(self, since: str | None = None) -> list[Path]:
        """Return all Daily Journal index.md paths, optionally filtered by date.

        Args:
            since: If provided, only return journals on or after this YYYY-MM-DD date.
        """
        paths: list[Path] = []
        for p in sorted(self._root.glob("*/*/?*-journal/index.md")):
            if since is not None:
                folder = p.parent.name       # DD-journal
                month = p.parent.parent.name  # MM
                year = p.parent.parent.parent.name  # YYYY
                day = folder.split("-")[0]
                journal_date = f"{year}-{month}-{day}"
                if journal_date < since:
                    continue
            paths.append(p)
        return paths

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _journal_dir(self, date: str) -> Path:
        year, month, day = date.split("-")
        return self._root / year / month / f"{day}-journal"

    def _generate_layers(self, index_path: Path, date: str) -> None:
        """Generate .abstract and .overview alongside the journal index.md."""
        from ink_core.fs.layer_generator import L0Generator, L1Generator

        content = index_path.read_text(encoding="utf-8")
        l0 = L0Generator().generate(content)
        l1 = L1Generator().generate(content)

        (index_path.parent / ".abstract").write_text(l0, encoding="utf-8")
        (index_path.parent / ".overview").write_text(l1, encoding="utf-8")
