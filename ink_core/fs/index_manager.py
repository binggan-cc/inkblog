"""Index manager for maintaining _index/ global indexes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ink_core.fs.article import Article


class IndexManager:
    """维护 _index/ 下的全局索引。

    Args:
        workspace_root: The root of the ink workspace. _index/ is stored under
                        workspace_root/_index/.
    """

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root
        self._index_dir = workspace_root / "_index"

    # ------------------------------------------------------------------
    # Timeline
    # ------------------------------------------------------------------

    def update_timeline(self, article: "Article") -> None:
        """Upsert an article entry in _index/timeline.json.

        Reads the existing timeline (or starts with []), upserts the entry
        matched by canonical_id == path, then sorts by date descending;
        if date is equal, by updated_at descending, and writes back.

        Args:
            article: The Article whose timeline entry should be updated.
        """
        entries = self.read_timeline()

        # Build the new entry from article.l1 (parsed .overview frontmatter)
        l1 = article.l1 or {}
        new_entry = {
            "path": article.canonical_id,
            "title": l1.get("title", ""),
            "date": article.date,
            "status": l1.get("status", "draft"),
            "tags": l1.get("tags", []),
            "updated_at": l1.get("updated_at", ""),
        }

        # Upsert: replace existing entry with same canonical_id, or append
        updated = False
        for i, entry in enumerate(entries):
            if entry.get("path") == article.canonical_id:
                entries[i] = new_entry
                updated = True
                break
        if not updated:
            entries.append(new_entry)

        # Sort: date descending, then updated_at descending
        entries.sort(
            key=lambda e: (e.get("date", ""), e.get("updated_at", "")),
            reverse=True,
        )

        self._ensure_index_dir()
        timeline_path = self._index_dir / "timeline.json"
        timeline_path.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def read_timeline(self) -> list[dict]:
        """Read _index/timeline.json.

        Returns:
            List of timeline entry dicts, or [] if the file doesn't exist.
        """
        timeline_path = self._index_dir / "timeline.json"
        if not timeline_path.exists():
            return []
        content = timeline_path.read_text(encoding="utf-8").strip()
        if not content:
            return []
        return json.loads(content)

    # ------------------------------------------------------------------
    # Graph
    # ------------------------------------------------------------------

    def update_graph(self, graph_data: dict) -> None:
        """Write graph_data to _index/graph.json.

        Ensures that 'ambiguous' and 'unresolved' keys exist as arrays even
        if not provided in graph_data.

        Args:
            graph_data: Dict containing nodes, edges, and optionally
                        ambiguous/unresolved lists.
        """
        data = dict(graph_data)
        if "ambiguous" not in data or data["ambiguous"] is None:
            data["ambiguous"] = []
        if "unresolved" not in data or data["unresolved"] is None:
            data["unresolved"] = []

        self._ensure_index_dir()
        graph_path = self._index_dir / "graph.json"
        graph_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def read_graph(self) -> dict:
        """Read _index/graph.json.

        Returns:
            Graph dict, or an empty structure with nodes/edges/ambiguous/unresolved
            as empty arrays if the file doesn't exist.
        """
        graph_path = self._index_dir / "graph.json"
        if not graph_path.exists():
            return {"nodes": [], "edges": [], "ambiguous": [], "unresolved": []}
        content = graph_path.read_text(encoding="utf-8").strip()
        if not content:
            return {"nodes": [], "edges": [], "ambiguous": [], "unresolved": []}
        return json.loads(content)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_index_dir(self) -> None:
        """Create _index/ directory if it doesn't exist."""
        self._index_dir.mkdir(parents=True, exist_ok=True)
