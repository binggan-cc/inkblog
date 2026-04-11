"""RecallEngine — search and rank LogEntry items for OpenClaw Agent Mode."""

from __future__ import annotations

import re

from ink_core.agent import LogEntry


class RecallEngine:
    """Pure-function search engine over LogEntry lists.

    No side effects; all state passed in as arguments.
    """

    def score_entry(self, entry: LogEntry, query: str) -> int:
        """Score a single entry against a query string.

        Scoring rules:
        - Each exact whole-word match in content: +2
        - Each partial (substring) match in content: +1
        - Matches in category also contribute (whole-word: +2, partial: +1)
        - Empty query returns 0 (caller handles "return all" logic)
        """
        if not query:
            return 0

        score = 0
        text = entry.content.lower()
        cat = entry.category.lower()
        q = query.lower()

        # Whole-word matches (boundaries: start/end or non-alphanumeric)
        word_pattern = re.compile(r"(?<![a-z0-9])" + re.escape(q) + r"(?![a-z0-9])")

        whole_in_content = len(word_pattern.findall(text))
        whole_in_cat = len(word_pattern.findall(cat))

        score += whole_in_content * 2
        score += whole_in_cat * 2

        # Partial matches (substring, not already counted as whole-word)
        partial_in_content = text.count(q) - whole_in_content
        partial_in_cat = cat.count(q) - whole_in_cat

        score += max(partial_in_content, 0)
        score += max(partial_in_cat, 0)

        return score

    def search(
        self,
        entries: list[LogEntry],
        query: str,
        *,
        category: str | None = None,
        since: str | None = None,
        limit: int = 20,
    ) -> list[LogEntry]:
        """Filter, score, and rank entries.

        Args:
            entries: Full list of LogEntry to search across.
            query:   Search string. Empty string returns top-limit by date.
            category: If provided, restrict to this category (case-insensitive).
            since:   If provided (YYYY-MM-DD), only entries on or after this date.
            limit:   Maximum number of results to return.

        Returns:
            Up to `limit` entries sorted by relevance desc, then date desc, then time desc.
        """
        # 1. Category filter
        if category is not None:
            cat_lower = category.lower()
            entries = [e for e in entries if e.category.lower() == cat_lower]

        # 2. Date filter
        if since is not None:
            entries = [e for e in entries if e.date >= since]

        # 3. Score and sort
        if query:
            scored = [(self.score_entry(e, query), e) for e in entries]
            # Keep only entries with score > 0 when a query is provided
            scored = [(s, e) for s, e in scored if s > 0]
            scored.sort(key=lambda x: (x[0], x[1].date, x[1].time), reverse=True)
            results = [e for _, e in scored]
        else:
            # Empty query: return all filtered entries sorted by date/time desc
            results = sorted(entries, key=lambda e: (e.date, e.time), reverse=True)

        return results[:limit]
