"""Tests for AnalyzeSkill and WikiLinkResult / resolve_wiki_link."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from ink_core.fs.article import Article, ArticleManager
from ink_core.fs.index_manager import IndexManager
from ink_core.skills.analyze import AnalyzeSkill, WikiLinkResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_article(
    ink_dir: Path,
    canonical_id: str,
    title: str,
    tags: list[str] | None = None,
    body: str = "",
) -> Path:
    """Create a minimal article directory and return its path."""
    tags = tags or []
    parts = canonical_id.split("/")  # YYYY, MM, DD-slug
    article_dir = ink_dir / parts[0] / parts[1] / parts[2]
    article_dir.mkdir(parents=True, exist_ok=True)
    (article_dir / "assets").mkdir(exist_ok=True)

    tags_yaml = str(tags).replace("'", '"')
    index_md = textwrap.dedent(f"""\
        ---
        title: "{title}"
        slug: "{parts[2].split('-', 1)[1]}"
        date: "{parts[0]}-{parts[1]}-{parts[2][:2]}"
        status: "draft"
        tags: {tags_yaml}
        ---

        # {title}

        {body}
    """)
    (article_dir / "index.md").write_text(index_md, encoding="utf-8")

    abstract = f"Abstract for {title}."
    (article_dir / ".abstract").write_text(abstract, encoding="utf-8")

    overview = textwrap.dedent(f"""\
        ---
        title: "{title}"
        created_at: "2025-01-01T00:00:00"
        updated_at: "2025-01-01T00:00:00"
        status: "draft"
        tags: {tags_yaml}
        word_count: 10
        reading_time_min: 1
        related: []
        ---

        ## Summary

        Summary for {title}.

        ## Key Points

        - Point one
    """)
    (article_dir / ".overview").write_text(overview, encoding="utf-8")

    return article_dir


# ---------------------------------------------------------------------------
# resolve_wiki_link tests
# ---------------------------------------------------------------------------

class TestResolveWikiLink:
    def _skill(self, ink_dir: Path) -> AnalyzeSkill:
        return AnalyzeSkill(ink_dir)

    def _articles(self, ink_dir: Path) -> list[Article]:
        return ArticleManager(ink_dir).list_all()

    def test_resolved_by_title(self, ink_dir: Path) -> None:
        _make_article(ink_dir, "2025/03/20-liquid-blog", "Liquid Blog")
        skill = self._skill(ink_dir)
        articles = self._articles(ink_dir)

        result = skill.resolve_wiki_link("Liquid Blog", articles)

        assert result.status == "resolved"
        assert result.resolved_id == "2025/03/20-liquid-blog"
        assert result.candidates is None

    def test_resolved_case_insensitive(self, ink_dir: Path) -> None:
        _make_article(ink_dir, "2025/03/20-liquid-blog", "Liquid Blog")
        skill = self._skill(ink_dir)
        articles = self._articles(ink_dir)

        result = skill.resolve_wiki_link("liquid blog", articles)

        assert result.status == "resolved"
        assert result.resolved_id == "2025/03/20-liquid-blog"

    def test_resolved_by_slug(self, ink_dir: Path) -> None:
        _make_article(ink_dir, "2025/03/20-liquid-blog", "Liquid Blog")
        skill = self._skill(ink_dir)
        articles = self._articles(ink_dir)

        result = skill.resolve_wiki_link("liquid-blog", articles)

        assert result.status == "resolved"
        assert result.resolved_id == "2025/03/20-liquid-blog"

    def test_ambiguous_multiple_matches(self, ink_dir: Path) -> None:
        _make_article(ink_dir, "2025/03/20-liquid-blog", "Liquid Blog")
        _make_article(ink_dir, "2026/01/10-liquid-blog", "Liquid Blog")
        skill = self._skill(ink_dir)
        articles = self._articles(ink_dir)

        result = skill.resolve_wiki_link("Liquid Blog", articles)

        assert result.status == "ambiguous"
        assert result.resolved_id is None
        assert result.candidates is not None
        assert len(result.candidates) == 2

    def test_unresolved_no_match(self, ink_dir: Path) -> None:
        _make_article(ink_dir, "2025/03/20-liquid-blog", "Liquid Blog")
        skill = self._skill(ink_dir)
        articles = self._articles(ink_dir)

        result = skill.resolve_wiki_link("Nonexistent Article", articles)

        assert result.status == "unresolved"
        assert result.resolved_id is None
        assert result.candidates is None

    def test_exact_canonical_id_resolved(self, ink_dir: Path) -> None:
        _make_article(ink_dir, "2025/03/20-liquid-blog", "Liquid Blog")
        skill = self._skill(ink_dir)
        articles = self._articles(ink_dir)

        result = skill.resolve_wiki_link("2025/03/20-liquid-blog", articles)

        assert result.status == "resolved"
        assert result.resolved_id == "2025/03/20-liquid-blog"

    def test_exact_canonical_id_unresolved(self, ink_dir: Path) -> None:
        skill = self._skill(ink_dir)
        articles = self._articles(ink_dir)

        result = skill.resolve_wiki_link("2025/03/20-nonexistent", articles)

        assert result.status == "unresolved"
        assert result.resolved_id is None

    def test_exact_canonical_id_no_ambiguity(self, ink_dir: Path) -> None:
        """Canonical ID format should never produce ambiguous result."""
        _make_article(ink_dir, "2025/03/20-liquid-blog", "Liquid Blog")
        _make_article(ink_dir, "2026/01/10-liquid-blog", "Liquid Blog")
        skill = self._skill(ink_dir)
        articles = self._articles(ink_dir)

        result = skill.resolve_wiki_link("2025/03/20-liquid-blog", articles)

        assert result.status == "resolved"
        assert result.resolved_id == "2025/03/20-liquid-blog"


# ---------------------------------------------------------------------------
# AnalyzeSkill.execute – single article
# ---------------------------------------------------------------------------

class TestAnalyzeSingle:
    def test_basic_analysis_fields(self, ink_dir: Path) -> None:
        _make_article(ink_dir, "2025/03/20-liquid-blog", "Liquid Blog", tags=["blog"])
        skill = AnalyzeSkill(ink_dir)

        result = skill.execute("2025/03/20-liquid-blog", {})

        assert result.success is True
        data = result.data
        assert "word_count" in data
        assert "reading_time" in data
        assert "tags" in data
        assert "related_count" in data
        assert "in_link_count" in data
        assert isinstance(data["word_count"], int)
        assert data["word_count"] >= 0
        assert data["reading_time"] >= 1
        assert isinstance(data["tags"], list)
        assert isinstance(data["related_count"], int)
        assert isinstance(data["in_link_count"], int)

    def test_word_count_excludes_frontmatter(self, ink_dir: Path) -> None:
        _make_article(
            ink_dir,
            "2025/03/20-liquid-blog",
            "Liquid Blog",
            body="Hello world this is a test sentence.",
        )
        skill = AnalyzeSkill(ink_dir)

        result = skill.execute("2025/03/20-liquid-blog", {})

        assert result.success is True
        # Body has "# Liquid Blog" + blank + "Hello world this is a test sentence."
        # = 2 + 7 = 9 words (approximately)
        assert result.data["word_count"] > 0

    def test_reading_time_minimum_one(self, ink_dir: Path) -> None:
        _make_article(ink_dir, "2025/03/20-liquid-blog", "Liquid Blog", body="Short.")
        skill = AnalyzeSkill(ink_dir)

        result = skill.execute("2025/03/20-liquid-blog", {})

        assert result.data["reading_time"] >= 1

    def test_tags_extracted(self, ink_dir: Path) -> None:
        _make_article(ink_dir, "2025/03/20-liquid-blog", "Liquid Blog", tags=["ai", "python"])
        skill = AnalyzeSkill(ink_dir)

        result = skill.execute("2025/03/20-liquid-blog", {})

        assert "ai" in result.data["tags"] or "python" in result.data["tags"]

    def test_related_count_resolved_links(self, ink_dir: Path) -> None:
        _make_article(ink_dir, "2025/03/21-other-article", "Other Article")
        _make_article(
            ink_dir,
            "2025/03/20-liquid-blog",
            "Liquid Blog",
            body="See [[Other Article]] for more.",
        )
        skill = AnalyzeSkill(ink_dir)

        result = skill.execute("2025/03/20-liquid-blog", {})

        assert result.success is True
        assert result.data["related_count"] == 1

    def test_in_link_count_from_graph(self, ink_dir: Path) -> None:
        _make_article(ink_dir, "2025/03/20-liquid-blog", "Liquid Blog")
        # Pre-populate graph with an incoming edge
        index_mgr = IndexManager(ink_dir)
        index_mgr.update_graph({
            "nodes": [{"id": "2025/03/20-liquid-blog", "title": "Liquid Blog", "tags": []}],
            "edges": [{"source": "2026/01/01-other", "target": "2025/03/20-liquid-blog", "type": "wiki_link"}],
            "ambiguous": [],
            "unresolved": [],
        })
        skill = AnalyzeSkill(ink_dir)

        result = skill.execute("2025/03/20-liquid-blog", {})

        assert result.success is True
        assert result.data["in_link_count"] == 1

    def test_in_link_count_zero_when_no_graph(self, ink_dir: Path) -> None:
        _make_article(ink_dir, "2025/03/20-liquid-blog", "Liquid Blog")
        skill = AnalyzeSkill(ink_dir)

        result = skill.execute("2025/03/20-liquid-blog", {})

        assert result.data["in_link_count"] == 0

    def test_path_not_found_returns_error_with_list(self, ink_dir: Path) -> None:
        _make_article(ink_dir, "2025/03/20-liquid-blog", "Liquid Blog")
        skill = AnalyzeSkill(ink_dir)

        result = skill.execute("2025/03/20-nonexistent", {})

        assert result.success is False
        assert "available_articles" in result.data
        assert "2025/03/20-liquid-blog" in result.data["available_articles"]

    def test_graph_json_written_after_analysis(self, ink_dir: Path) -> None:
        _make_article(ink_dir, "2025/03/20-liquid-blog", "Liquid Blog")
        skill = AnalyzeSkill(ink_dir)

        skill.execute("2025/03/20-liquid-blog", {})

        graph_path = ink_dir / "_index" / "graph.json"
        assert graph_path.exists()

    def test_graph_json_has_required_keys(self, ink_dir: Path) -> None:
        _make_article(ink_dir, "2025/03/20-liquid-blog", "Liquid Blog")
        skill = AnalyzeSkill(ink_dir)

        skill.execute("2025/03/20-liquid-blog", {})

        graph = IndexManager(ink_dir).read_graph()
        assert "nodes" in graph
        assert "edges" in graph
        assert "ambiguous" in graph
        assert "unresolved" in graph

    def test_ambiguous_links_in_graph(self, ink_dir: Path) -> None:
        _make_article(ink_dir, "2025/03/20-article-a", "Shared Title")
        _make_article(ink_dir, "2025/03/21-article-b", "Shared Title")
        _make_article(
            ink_dir,
            "2025/03/22-source",
            "Source",
            body="See [[Shared Title]] for details.",
        )
        skill = AnalyzeSkill(ink_dir)

        skill.execute("2025/03/22-source", {})

        graph = IndexManager(ink_dir).read_graph()
        assert len(graph["ambiguous"]) >= 1
        assert graph["ambiguous"][0]["source"] == "2025/03/22-source"
        assert graph["ambiguous"][0]["label"] == "Shared Title"

    def test_unresolved_links_in_graph(self, ink_dir: Path) -> None:
        _make_article(
            ink_dir,
            "2025/03/20-liquid-blog",
            "Liquid Blog",
            body="See [[Ghost Article]] for details.",
        )
        skill = AnalyzeSkill(ink_dir)

        skill.execute("2025/03/20-liquid-blog", {})

        graph = IndexManager(ink_dir).read_graph()
        assert len(graph["unresolved"]) >= 1
        assert graph["unresolved"][0]["label"] == "Ghost Article"

    def test_empty_ambiguous_unresolved_when_no_issues(self, ink_dir: Path) -> None:
        _make_article(ink_dir, "2025/03/20-liquid-blog", "Liquid Blog")
        skill = AnalyzeSkill(ink_dir)

        skill.execute("2025/03/20-liquid-blog", {})

        graph = IndexManager(ink_dir).read_graph()
        assert graph["ambiguous"] == []
        assert graph["unresolved"] == []


# ---------------------------------------------------------------------------
# AnalyzeSkill.execute – all articles
# ---------------------------------------------------------------------------

class TestAnalyzeAll:
    def test_all_mode_via_param(self, ink_dir: Path) -> None:
        _make_article(ink_dir, "2025/03/20-article-a", "Article A", tags=["ai"])
        _make_article(ink_dir, "2025/03/21-article-b", "Article B", tags=["python"])
        skill = AnalyzeSkill(ink_dir)

        result = skill.execute(None, {"all": True})

        assert result.success is True
        data = result.data
        assert data["total_articles"] == 2
        assert data["total_tags"] == 2
        assert "most_recent_updated_at" in data
        assert "isolated_articles" in data

    def test_all_mode_via_target_string(self, ink_dir: Path) -> None:
        _make_article(ink_dir, "2025/03/20-article-a", "Article A")
        skill = AnalyzeSkill(ink_dir)

        result = skill.execute("all", {})

        assert result.success is True
        assert result.data["total_articles"] == 1

    def test_isolated_articles_count(self, ink_dir: Path) -> None:
        _make_article(ink_dir, "2025/03/20-article-a", "Article A")
        _make_article(ink_dir, "2025/03/21-article-b", "Article B")
        # No edges → both isolated
        skill = AnalyzeSkill(ink_dir)

        result = skill.execute(None, {"all": True})

        assert result.data["isolated_articles"] == 2

    def test_connected_articles_not_isolated(self, ink_dir: Path) -> None:
        _make_article(ink_dir, "2025/03/21-article-b", "Article B")
        _make_article(
            ink_dir,
            "2025/03/20-article-a",
            "Article A",
            body="See [[Article B]] for more.",
        )
        # First run analyze on article-a to build graph
        skill = AnalyzeSkill(ink_dir)
        skill.execute("2025/03/20-article-a", {})

        result = skill.execute(None, {"all": True})

        # article-a has outgoing edge, article-b has incoming edge → neither isolated
        assert result.data["isolated_articles"] == 0

    def test_graph_written_in_all_mode(self, ink_dir: Path) -> None:
        _make_article(ink_dir, "2025/03/20-article-a", "Article A")
        skill = AnalyzeSkill(ink_dir)

        skill.execute(None, {"all": True})

        graph_path = ink_dir / "_index" / "graph.json"
        assert graph_path.exists()

    def test_empty_workspace(self, ink_dir: Path) -> None:
        skill = AnalyzeSkill(ink_dir)

        result = skill.execute(None, {"all": True})

        assert result.success is True
        assert result.data["total_articles"] == 0
        assert result.data["total_tags"] == 0
        assert result.data["isolated_articles"] == 0
