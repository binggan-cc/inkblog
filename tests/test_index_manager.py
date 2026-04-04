"""Tests for IndexManager (ink_core/fs/index_manager.py).

Covers Requirements 2.7, 2.8 (timeline index) and graph index management.
"""

from __future__ import annotations

import json
import textwrap
from dataclasses import dataclass
from pathlib import Path

import pytest

from ink_core.fs.article import Article
from ink_core.fs.index_manager import IndexManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_article(
    ink_dir: Path,
    canonical_id: str = "2025/03/20-liquid-blog",
    date: str = "2025-03-20",
    title: str = "Liquid Blog",
    status: str = "published",
    tags: list[str] | None = None,
    updated_at: str = "2025-03-20T15:00:00",
) -> Article:
    """Build a minimal Article with l1 populated from given fields."""
    if tags is None:
        tags = ["blog", "skills"]

    parts = canonical_id.split("/")
    folder_name = parts[-1]
    slug = folder_name[3:]  # strip DD-

    article_dir = ink_dir / "/".join(parts)
    article_dir.mkdir(parents=True, exist_ok=True)

    l1 = {
        "title": title,
        "status": status,
        "tags": tags,
        "updated_at": updated_at,
        "created_at": updated_at,
        "word_count": 100,
        "reading_time_min": 1,
        "related": [],
    }

    return Article(
        path=article_dir,
        canonical_id=canonical_id,
        folder_name=folder_name,
        slug=slug,
        date=date,
        l0="A short abstract.",
        l1=l1,
        l2="# Title\n\nContent.",
    )


# ---------------------------------------------------------------------------
# Timeline tests
# ---------------------------------------------------------------------------

class TestReadTimeline:
    def test_returns_empty_list_when_file_missing(self, ink_dir: Path) -> None:
        mgr = IndexManager(ink_dir)
        assert mgr.read_timeline() == []

    def test_returns_empty_list_when_file_is_empty(self, ink_dir: Path) -> None:
        (ink_dir / "_index" / "timeline.json").write_text("", encoding="utf-8")
        mgr = IndexManager(ink_dir)
        assert mgr.read_timeline() == []

    def test_returns_existing_entries(self, ink_dir: Path) -> None:
        entries = [
            {
                "path": "2025/03/20-liquid-blog",
                "title": "Liquid Blog",
                "date": "2025-03-20",
                "status": "published",
                "tags": ["blog"],
                "updated_at": "2025-03-20T15:00:00",
            }
        ]
        (ink_dir / "_index" / "timeline.json").write_text(
            json.dumps(entries), encoding="utf-8"
        )
        mgr = IndexManager(ink_dir)
        result = mgr.read_timeline()
        assert result == entries


class TestUpdateTimeline:
    def test_creates_timeline_file_if_missing(self, ink_dir: Path) -> None:
        mgr = IndexManager(ink_dir)
        article = _make_article(ink_dir)
        mgr.update_timeline(article)
        assert (ink_dir / "_index" / "timeline.json").exists()

    def test_entry_contains_required_fields(self, ink_dir: Path) -> None:
        mgr = IndexManager(ink_dir)
        article = _make_article(ink_dir)
        mgr.update_timeline(article)

        entries = mgr.read_timeline()
        assert len(entries) == 1
        entry = entries[0]
        assert entry["path"] == "2025/03/20-liquid-blog"
        assert entry["title"] == "Liquid Blog"
        assert entry["date"] == "2025-03-20"
        assert entry["status"] == "published"
        assert entry["tags"] == ["blog", "skills"]
        assert entry["updated_at"] == "2025-03-20T15:00:00"

    def test_upsert_replaces_existing_entry(self, ink_dir: Path) -> None:
        mgr = IndexManager(ink_dir)
        article = _make_article(ink_dir, status="draft")
        mgr.update_timeline(article)

        # Update with new status
        updated = _make_article(ink_dir, status="published", updated_at="2025-03-20T16:00:00")
        mgr.update_timeline(updated)

        entries = mgr.read_timeline()
        assert len(entries) == 1
        assert entries[0]["status"] == "published"
        assert entries[0]["updated_at"] == "2025-03-20T16:00:00"

    def test_multiple_articles_appended(self, ink_dir: Path) -> None:
        mgr = IndexManager(ink_dir)
        a1 = _make_article(ink_dir, canonical_id="2025/03/20-article-a", date="2025-03-20")
        a2 = _make_article(ink_dir, canonical_id="2025/03/21-article-b", date="2025-03-21")
        mgr.update_timeline(a1)
        mgr.update_timeline(a2)

        entries = mgr.read_timeline()
        assert len(entries) == 2

    def test_sorted_by_date_descending(self, ink_dir: Path) -> None:
        mgr = IndexManager(ink_dir)
        older = _make_article(
            ink_dir,
            canonical_id="2025/03/15-older",
            date="2025-03-15",
            updated_at="2025-03-15T10:00:00",
        )
        newer = _make_article(
            ink_dir,
            canonical_id="2025/03/20-newer",
            date="2025-03-20",
            updated_at="2025-03-20T10:00:00",
        )
        mgr.update_timeline(older)
        mgr.update_timeline(newer)

        entries = mgr.read_timeline()
        assert entries[0]["path"] == "2025/03/20-newer"
        assert entries[1]["path"] == "2025/03/15-older"

    def test_same_date_sorted_by_updated_at_descending(self, ink_dir: Path) -> None:
        mgr = IndexManager(ink_dir)
        early = _make_article(
            ink_dir,
            canonical_id="2025/03/20-early",
            date="2025-03-20",
            updated_at="2025-03-20T09:00:00",
        )
        late = _make_article(
            ink_dir,
            canonical_id="2025/03/20-late",
            date="2025-03-20",
            updated_at="2025-03-20T18:00:00",
        )
        mgr.update_timeline(early)
        mgr.update_timeline(late)

        entries = mgr.read_timeline()
        assert entries[0]["path"] == "2025/03/20-late"
        assert entries[1]["path"] == "2025/03/20-early"

    def test_creates_index_dir_if_missing(self, tmp_path: Path) -> None:
        workspace = tmp_path / "new_workspace"
        workspace.mkdir()
        # No _index/ directory
        mgr = IndexManager(workspace)
        article = _make_article(workspace)
        mgr.update_timeline(article)
        assert (workspace / "_index" / "timeline.json").exists()


# ---------------------------------------------------------------------------
# Graph tests
# ---------------------------------------------------------------------------

class TestReadGraph:
    def test_returns_empty_structure_when_file_missing(self, ink_dir: Path) -> None:
        mgr = IndexManager(ink_dir)
        result = mgr.read_graph()
        assert result == {"nodes": [], "edges": [], "ambiguous": [], "unresolved": []}

    def test_returns_empty_structure_when_file_is_empty(self, ink_dir: Path) -> None:
        (ink_dir / "_index" / "graph.json").write_text("", encoding="utf-8")
        mgr = IndexManager(ink_dir)
        result = mgr.read_graph()
        assert result == {"nodes": [], "edges": [], "ambiguous": [], "unresolved": []}

    def test_returns_existing_graph(self, ink_dir: Path) -> None:
        graph = {
            "nodes": [{"id": "2025/03/20-liquid-blog", "title": "Liquid Blog", "tags": ["blog"]}],
            "edges": [],
            "ambiguous": [],
            "unresolved": [],
        }
        (ink_dir / "_index" / "graph.json").write_text(
            json.dumps(graph), encoding="utf-8"
        )
        mgr = IndexManager(ink_dir)
        assert mgr.read_graph() == graph


class TestUpdateGraph:
    def test_writes_graph_file(self, ink_dir: Path) -> None:
        mgr = IndexManager(ink_dir)
        graph = {
            "nodes": [{"id": "2025/03/20-liquid-blog", "title": "Liquid Blog", "tags": []}],
            "edges": [],
            "ambiguous": [],
            "unresolved": [],
        }
        mgr.update_graph(graph)
        assert (ink_dir / "_index" / "graph.json").exists()
        assert mgr.read_graph() == graph

    def test_ensures_ambiguous_key_when_missing(self, ink_dir: Path) -> None:
        mgr = IndexManager(ink_dir)
        graph = {"nodes": [], "edges": []}
        mgr.update_graph(graph)
        result = mgr.read_graph()
        assert "ambiguous" in result
        assert result["ambiguous"] == []

    def test_ensures_unresolved_key_when_missing(self, ink_dir: Path) -> None:
        mgr = IndexManager(ink_dir)
        graph = {"nodes": [], "edges": []}
        mgr.update_graph(graph)
        result = mgr.read_graph()
        assert "unresolved" in result
        assert result["unresolved"] == []

    def test_ensures_ambiguous_empty_array_when_none(self, ink_dir: Path) -> None:
        mgr = IndexManager(ink_dir)
        graph = {"nodes": [], "edges": [], "ambiguous": None, "unresolved": None}
        mgr.update_graph(graph)
        result = mgr.read_graph()
        assert result["ambiguous"] == []
        assert result["unresolved"] == []

    def test_preserves_existing_ambiguous_data(self, ink_dir: Path) -> None:
        mgr = IndexManager(ink_dir)
        ambiguous_entry = {
            "source": "2025/03/20-liquid-blog",
            "label": "Some Article",
            "candidates": ["2025/03/15-a", "2025/03/16-b"],
        }
        graph = {
            "nodes": [],
            "edges": [],
            "ambiguous": [ambiguous_entry],
            "unresolved": [],
        }
        mgr.update_graph(graph)
        result = mgr.read_graph()
        assert result["ambiguous"] == [ambiguous_entry]

    def test_creates_index_dir_if_missing(self, tmp_path: Path) -> None:
        workspace = tmp_path / "new_workspace"
        workspace.mkdir()
        mgr = IndexManager(workspace)
        mgr.update_graph({"nodes": [], "edges": []})
        assert (workspace / "_index" / "graph.json").exists()

    def test_does_not_mutate_input_dict(self, ink_dir: Path) -> None:
        mgr = IndexManager(ink_dir)
        graph = {"nodes": [], "edges": []}
        original_keys = set(graph.keys())
        mgr.update_graph(graph)
        # Original dict should not be mutated
        assert set(graph.keys()) == original_keys


# ---------------------------------------------------------------------------
# Export test
# ---------------------------------------------------------------------------

def test_index_manager_exported_from_fs_package() -> None:
    from ink_core.fs import IndexManager as IM
    assert IM is IndexManager
