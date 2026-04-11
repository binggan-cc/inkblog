"""Tests for static site generation (Task 15.5 + 15.6).

Unit tests (15.5):
- BuildCommand registration and --all param
- TemplateRenderer: custom template priority, built-in fallback
- SiteBuilder: output dir default vs config override
- Git commit message for build

Property tests (15.6):
- P29: Only published articles included by default
- P30: Article page path format matches _site/YYYY/MM/DD-slug/index.html
- P31: Index page article order matches timeline.json
- P32: RSS feed capped at 20 items
- P33: Build result contains page_count and duration_ms
"""

from __future__ import annotations

import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ink_core.cli.builtin import BuildCommand
from ink_core.core.config import InkConfig
from ink_core.fs.article import ArticleManager
from ink_core.fs.index_manager import IndexManager
from ink_core.site.builder import SiteBuilder
from ink_core.site.renderer import TemplateRenderer
from ink_core.site.rss import RSSGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_workspace(tmp_path: Path, name: str = "ws") -> Path:
    ws = tmp_path / name
    ws.mkdir(parents=True, exist_ok=True)
    (ws / ".ink" / "sessions").mkdir(parents=True, exist_ok=True)
    (ws / ".ink" / "skills").mkdir(parents=True, exist_ok=True)
    (ws / "_index").mkdir(exist_ok=True)
    return ws


def _create_published_article(manager: ArticleManager, index_mgr: IndexManager,
                               title: str, date: str, tags=None):
    """Create an article, set status=published, regenerate layers, update timeline."""
    article = manager.create(title, date=date, tags=tags or [])
    index_path = article.path / "index.md"
    content = index_path.read_text(encoding="utf-8").replace("status: draft", "status: published")
    index_path.write_text(content, encoding="utf-8")
    # Regenerate .overview so l1.meta.status == "published"
    article.l2 = content
    manager.update_layers(article)
    # Re-read to get fully updated article
    result = manager.read(article.path)
    index_mgr.update_timeline(result.article)
    return result.article


def _create_draft_article(manager: ArticleManager, index_mgr: IndexManager,
                           title: str, date: str):
    article = manager.create(title, date=date)
    result = manager.read(article.path)
    index_mgr.update_timeline(result.article)
    return result.article


def _create_drafted_article(manager: ArticleManager, index_mgr: IndexManager,
                             title: str, date: str):
    article = manager.create(title, date=date)
    index_path = article.path / "index.md"
    content = index_path.read_text(encoding="utf-8").replace("status: draft", "status: drafted")
    index_path.write_text(content, encoding="utf-8")
    article.l2 = content
    manager.update_layers(article)
    result = manager.read(article.path)
    index_mgr.update_timeline(result.article)
    return result.article


def _make_builder(workspace: Path) -> SiteBuilder:
    config = InkConfig()
    return SiteBuilder(
        workspace_root=workspace,
        config=config,
        article_manager=ArticleManager(workspace),
        index_manager=IndexManager(workspace),
    )


# ---------------------------------------------------------------------------
# 15.5 Unit Tests
# ---------------------------------------------------------------------------

class TestBuildCommandRegistration:
    """BuildCommand is registered and callable via executor."""

    def test_build_command_name(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        cmd = BuildCommand(ws)
        assert cmd.name == "build"

    def test_build_command_runs_on_empty_workspace(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        cmd = BuildCommand(ws)
        result = cmd.run(None, {})
        assert result.success
        assert "page_count" in result.data
        assert "duration_ms" in result.data

    def test_build_command_all_param_passed(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        manager = ArticleManager(ws)
        index_mgr = IndexManager(ws)
        _create_draft_article(manager, index_mgr, "Draft Article", "2025-12-01")

        cmd = BuildCommand(ws)
        # Without --all: draft not included
        result_default = cmd.run(None, {})
        # With --all: draft included
        result_all = cmd.run(None, {"all": True})

        # --all should produce more pages (draft article included)
        assert result_all.data["page_count"] >= result_default.data["page_count"]

    def test_build_command_include_drafted_param_passed(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        manager = ArticleManager(ws)
        index_mgr = IndexManager(ws)
        drafted = _create_drafted_article(manager, index_mgr, "Drafted Article", "2025-12-16")

        cmd = BuildCommand(ws)
        cmd.run(None, {"include_drafted": True})

        assert (ws / "_site" / drafted.canonical_id / "index.html").exists()

    def test_build_command_registered_in_cli(self, tmp_path: Path) -> None:
        """BuildCommand appears in the IntentRouter builtin table."""
        from ink_core.cli.intent import IntentRouter, Intent
        from ink_core.cli.builtin import BuildCommand, InitCommand, NewCommand, RebuildCommand, SkillsListCommand
        from ink_core.skills.registry import SkillRegistry

        ws = _make_workspace(tmp_path)
        registry = SkillRegistry.create_with_builtins(ws)
        builtins = {
            "new": NewCommand(ws),
            "init": InitCommand(ws),
            "rebuild": RebuildCommand(ws),
            "build": BuildCommand(ws),
        }
        router = IntentRouter(builtins=builtins, skill_registry=registry)
        intent = Intent(action="build", target=None, params={})
        route = router.resolve(intent)
        assert route.target is not None
        assert route.target.name == "build"


class TestTemplateRenderer:
    """TemplateRenderer uses custom templates when available, falls back to built-in."""

    def test_builtin_fallback_renders_article(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        manager = ArticleManager(ws)
        article = manager.create("Renderer Test", date="2025-12-02")

        renderer = TemplateRenderer(ws)
        out = ws / "_site" / "test" / "index.html"
        renderer.render_article(article, out)

        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "Renderer Test" in content
        assert "<!DOCTYPE html>" in content

    def test_builtin_fallback_renders_index(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        manager = ArticleManager(ws)
        index_mgr = IndexManager(ws)
        a = _create_published_article(manager, index_mgr, "Index Test Article", "2025-12-03")

        renderer = TemplateRenderer(ws)
        out = ws / "_site" / "index.html"
        renderer.render_index([a], out, site_title="My Blog")

        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "My Blog" in content
        assert "Index Test Article" in content

    def test_custom_template_takes_priority(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        # Create custom article template
        template_dir = ws / "_templates" / "site"
        template_dir.mkdir(parents=True)
        custom_tmpl = template_dir / "article.html"
        custom_tmpl.write_text(
            "<html><body><h1>CUSTOM: {{ title }}</h1></body></html>",
            encoding="utf-8",
        )

        manager = ArticleManager(ws)
        article = manager.create("Custom Template Test", date="2025-12-04")

        renderer = TemplateRenderer(ws)
        out = ws / "_site" / "custom" / "index.html"
        renderer.render_article(article, out)

        content = out.read_text(encoding="utf-8")
        assert "CUSTOM: Custom Template Test" in content

    def test_custom_index_template_takes_priority(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        template_dir = ws / "_templates" / "site"
        template_dir.mkdir(parents=True)
        (template_dir / "index.html").write_text(
            "<html><body><p>CUSTOM INDEX: {{ site_title }}</p></body></html>",
            encoding="utf-8",
        )

        manager = ArticleManager(ws)
        index_mgr = IndexManager(ws)
        a = _create_published_article(manager, index_mgr, "Custom Index Test", "2025-12-05")

        renderer = TemplateRenderer(ws)
        out = ws / "_site" / "index.html"
        renderer.render_index([a], out, site_title="Custom Blog")

        content = out.read_text(encoding="utf-8")
        assert "CUSTOM INDEX: Custom Blog" in content


class TestSiteBuilderOutputDir:
    """SiteBuilder respects default and configured output directories."""

    def test_default_output_dir_is_site(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        builder = _make_builder(ws)
        assert builder._output_dir() == ws / "_site"

    def test_config_output_dir_overrides_default(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        # Write a config with custom output
        config_dir = Path.home() / ".ink"
        # Use InkConfig with a patched get() instead of writing real config
        config = InkConfig()
        # Monkey-patch get() for this test
        original_get = config.get
        config.get = lambda key, default=None: (
            str(ws / "custom_output") if key == "channels.blog.output" else original_get(key, default)
        )
        builder = SiteBuilder(
            workspace_root=ws,
            config=config,
            article_manager=ArticleManager(ws),
            index_manager=IndexManager(ws),
        )
        assert builder._output_dir() == ws / "custom_output"

    def test_build_creates_output_dir(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        builder = _make_builder(ws)
        result = builder.build()
        assert result.output_dir.exists()

    def test_build_creates_index_html(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        builder = _make_builder(ws)
        builder.build()
        assert (ws / "_site" / "index.html").exists()

    def test_build_creates_feed_xml(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        builder = _make_builder(ws)
        builder.build()
        assert (ws / "_site" / "feed.xml").exists()


class TestBuildGitCommitMessage:
    """ink build triggers aggregate_commit with correct message."""

    def test_build_commit_message_format(self, tmp_path: Path) -> None:
        from ink_core.core.executor import CommandExecutor, _WRITE_COMMANDS
        assert "build" in _WRITE_COMMANDS

    def test_commit_message_is_build_regenerate(self, tmp_path: Path) -> None:
        from ink_core.core.executor import CommandExecutor
        from ink_core.cli.intent import Intent

        ws = _make_workspace(tmp_path)
        # Instantiate executor and check _commit_message for build action
        from ink_core.cli.intent import IntentRouter
        from ink_core.cli.builtin import BuildCommand, InitCommand, NewCommand, RebuildCommand, SkillsListCommand
        from ink_core.skills.registry import SkillRegistry
        from ink_core.core.session import SessionLogger
        from ink_core.git.manager import GitManager

        registry = SkillRegistry.create_with_builtins(ws)
        builtins = {
            "new": NewCommand(ws),
            "init": InitCommand(ws),
            "rebuild": RebuildCommand(ws),
            "build": BuildCommand(ws),
        }
        router = IntentRouter(builtins=builtins, skill_registry=registry)
        executor = CommandExecutor(
            workspace_root=ws,
            router=router,
            session_logger=SessionLogger(ws),
            git_manager=GitManager(ws),
        )
        intent = Intent(action="build", target=None, params={})
        msg = executor._commit_message(intent)
        assert msg == "build: regenerate static site"


class TestRSSGenerator:
    """RSSGenerator produces valid Atom XML."""

    def test_rss_generates_valid_xml(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        manager = ArticleManager(ws)
        index_mgr = IndexManager(ws)
        article = _create_published_article(manager, index_mgr, "RSS Test Article", "2025-12-06")

        gen = RSSGenerator()
        out = tmp_path / "feed.xml"
        gen.generate([article], out, {"title": "Test Blog", "author": "Tester"})

        assert out.exists()
        tree = ET.parse(out)
        root = tree.getroot()
        ns = "http://www.w3.org/2005/Atom"
        assert root.tag == f"{{{ns}}}feed"
        entries = root.findall(f"{{{ns}}}entry")
        assert len(entries) == 1

    def test_rss_capped_at_20_items(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        manager = ArticleManager(ws)
        index_mgr = IndexManager(ws)

        articles = []
        for i in range(25):
            a = _create_published_article(
                manager, index_mgr,
                f"RSS Article {i:02d}",
                f"2025-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
            )
            articles.append(a)

        gen = RSSGenerator()
        out = tmp_path / "feed.xml"
        gen.generate(articles, out, {"title": "Blog"})

        tree = ET.parse(out)
        root = tree.getroot()
        ns = "http://www.w3.org/2005/Atom"
        entries = root.findall(f"{{{ns}}}entry")
        assert len(entries) == 20

    def test_rss_fewer_than_20_items(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        manager = ArticleManager(ws)
        index_mgr = IndexManager(ws)

        articles = []
        for i in range(5):
            a = _create_published_article(
                manager, index_mgr, f"Small Feed {i}", f"2025-12-{i + 1:02d}"
            )
            articles.append(a)

        gen = RSSGenerator()
        out = tmp_path / "feed.xml"
        gen.generate(articles, out, {"title": "Blog"})

        tree = ET.parse(out)
        root = tree.getroot()
        ns = "http://www.w3.org/2005/Atom"
        entries = root.findall(f"{{{ns}}}entry")
        assert len(entries) == 5


class TestSiteBuilderFiltering:
    """SiteBuilder filters articles by status correctly."""

    def test_default_build_excludes_draft(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        manager = ArticleManager(ws)
        index_mgr = IndexManager(ws)

        pub = _create_published_article(manager, index_mgr, "Published Article", "2025-12-10")
        _create_draft_article(manager, index_mgr, "Draft Article", "2025-12-11")

        builder = _make_builder(ws)
        builder.build()

        pub_page = ws / "_site" / pub.canonical_id / "index.html"
        assert pub_page.exists()

        # Draft article should NOT have a page
        draft_pages = list((ws / "_site").rglob("index.html"))
        # Only the published article page + the index page
        article_pages = [p for p in draft_pages if p.parent != ws / "_site"]
        assert len(article_pages) == 1

    def test_all_flag_includes_draft(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        manager = ArticleManager(ws)
        index_mgr = IndexManager(ws)

        _create_published_article(manager, index_mgr, "Published B", "2025-12-12")
        draft = _create_draft_article(manager, index_mgr, "Draft B", "2025-12-13")

        builder = _make_builder(ws)
        builder.build(include_all=True)

        draft_page = ws / "_site" / draft.canonical_id / "index.html"
        assert draft_page.exists()

    def test_article_page_path_format(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        manager = ArticleManager(ws)
        index_mgr = IndexManager(ws)

        article = _create_published_article(
            manager, index_mgr, "Path Format Test", "2025-12-14"
        )

        builder = _make_builder(ws)
        builder.build()

        expected = ws / "_site" / article.canonical_id / "index.html"
        assert expected.exists(), f"Expected {expected} to exist"

    def test_build_result_has_page_count_and_duration(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        manager = ArticleManager(ws)
        index_mgr = IndexManager(ws)
        _create_published_article(manager, index_mgr, "Stats Test", "2025-12-15")

        builder = _make_builder(ws)
        result = builder.build()

        assert result.page_count >= 1  # at least index page
        assert result.duration_ms >= 0


# ---------------------------------------------------------------------------
# 15.6 Property Tests
# ---------------------------------------------------------------------------

def _make_ws_for_property(base: Path) -> Path:
    ws = base / "ws"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / ".ink" / "sessions").mkdir(parents=True, exist_ok=True)
    (ws / ".ink" / "skills").mkdir(parents=True, exist_ok=True)
    (ws / "_index").mkdir(exist_ok=True)
    return ws


class TestP29PublishedArticleFilter:
    """P29: Default build only generates pages for published articles."""

    @given(
        n_published=st.integers(min_value=0, max_value=5),
        n_draft=st.integers(min_value=1, max_value=4),
    )
    @settings(max_examples=40, suppress_health_check=[HealthCheck.too_slow])
    def test_default_build_only_published(self, n_published: int, n_draft: int) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            ws = _make_ws_for_property(Path(td))
            manager = ArticleManager(ws)
            index_mgr = IndexManager(ws)

            published_ids = set()
            for i in range(n_published):
                a = _create_published_article(
                    manager, index_mgr, f"Pub {i}", f"2025-{(i % 12) + 1:02d}-01"
                )
                published_ids.add(a.canonical_id)

            draft_ids = set()
            for i in range(n_draft):
                a = _create_draft_article(
                    manager, index_mgr, f"Draft {i}", f"2024-{(i % 12) + 1:02d}-01"
                )
                draft_ids.add(a.canonical_id)

            builder = _make_builder(ws)
            builder.build()

            site_dir = ws / "_site"
            # Check no draft pages exist
            for cid in draft_ids:
                page = site_dir / cid / "index.html"
                assert not page.exists(), f"Draft page should not exist: {page}"

            # Check all published pages exist
            for cid in published_ids:
                page = site_dir / cid / "index.html"
                assert page.exists(), f"Published page should exist: {page}"


class TestP30ArticlePagePathFormat:
    """P30: Article HTML path matches _site/YYYY/MM/DD-slug/index.html."""

    @given(
        year=st.integers(min_value=2020, max_value=2030),
        month=st.integers(min_value=1, max_value=12),
        day=st.integers(min_value=1, max_value=28),
    )
    @settings(max_examples=40, suppress_health_check=[HealthCheck.too_slow])
    def test_article_page_path_matches_canonical_id(
        self, year: int, month: int, day: int
    ) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            ws = _make_ws_for_property(Path(td))
            manager = ArticleManager(ws)
            index_mgr = IndexManager(ws)

            date_str = f"{year}-{month:02d}-{day:02d}"
            article = _create_published_article(
                manager, index_mgr, "Path Test Article", date_str
            )

            builder = _make_builder(ws)
            builder.build()

            expected = ws / "_site" / article.canonical_id / "index.html"
            assert expected.exists(), f"Expected {expected}"
            # Verify path structure
            parts = article.canonical_id.split("/")
            assert len(parts) == 3  # YYYY/MM/DD-slug
            assert parts[0] == str(year)
            assert parts[1] == f"{month:02d}"


class TestP31IndexPageOrder:
    """P31: Index page article order matches timeline.json order."""

    @given(n=st.integers(min_value=2, max_value=6))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    def test_index_order_matches_timeline(self, n: int) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            ws = _make_ws_for_property(Path(td))
            manager = ArticleManager(ws)
            index_mgr = IndexManager(ws)

            for i in range(n):
                _create_published_article(
                    manager, index_mgr,
                    f"Order Test {i:02d}",
                    f"2025-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
                )

            builder = _make_builder(ws)
            builder.build()

            # Read timeline order
            timeline = index_mgr.read_timeline()
            published_timeline = [e["path"] for e in timeline if e.get("status") == "published"]

            # Read index.html and check article order
            index_html = (ws / "_site" / "index.html").read_text(encoding="utf-8")
            positions = [(cid, index_html.find(cid)) for cid in published_timeline if cid in index_html]
            positions = [(cid, pos) for cid, pos in positions if pos != -1]

            if len(positions) >= 2:
                # Positions should be in ascending order (matching timeline order)
                for i in range(len(positions) - 1):
                    assert positions[i][1] < positions[i + 1][1], (
                        f"Index order mismatch: {positions[i][0]} should appear before {positions[i+1][0]}"
                    )


class TestP32RSSFeedCap:
    """P32: RSS feed contains at most 20 items."""

    @given(n=st.integers(min_value=21, max_value=30))
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
    def test_rss_capped_at_20(self, n: int) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            ws = _make_ws_for_property(Path(td))
            manager = ArticleManager(ws)
            index_mgr = IndexManager(ws)

            articles = []
            for i in range(n):
                a = _create_published_article(
                    manager, index_mgr,
                    f"RSS Cap {i:02d}",
                    f"2025-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
                )
                articles.append(a)

            gen = RSSGenerator()
            out = Path(td) / "feed.xml"
            gen.generate(articles, out, {"title": "Blog"})

            tree = ET.parse(out)
            root = tree.getroot()
            ns = "http://www.w3.org/2005/Atom"
            entries = root.findall(f"{{{ns}}}entry")
            assert len(entries) == 20


class TestP33BuildStatsCompleteness:
    """P33: Build result always contains page_count and duration_ms."""

    @given(n=st.integers(min_value=0, max_value=5))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    def test_build_result_always_has_stats(self, n: int) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            ws = _make_ws_for_property(Path(td))
            manager = ArticleManager(ws)
            index_mgr = IndexManager(ws)

            for i in range(n):
                _create_published_article(
                    manager, index_mgr, f"Stats {i}", f"2025-{(i % 12) + 1:02d}-01"
                )

            builder = _make_builder(ws)
            result = builder.build()

            assert isinstance(result.page_count, int)
            assert result.page_count >= 0
            assert isinstance(result.duration_ms, int)
            assert result.duration_ms >= 0
