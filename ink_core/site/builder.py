"""Static site builder for ink_core."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ink_core.core.config import InkConfig
    from ink_core.fs.article import Article
    from ink_core.fs.article import ArticleManager
    from ink_core.fs.index_manager import IndexManager


@dataclass
class BuildResult:
    """Result of a static site build."""
    page_count: int
    duration_ms: int
    output_dir: Path


class SiteBuilder:
    """Build a static HTML site from the ink workspace.

    Reads _index/timeline.json, filters articles, renders HTML pages
    via TemplateRenderer, and generates an RSS feed via RSSGenerator.
    """

    DEFAULT_OUTPUT_DIR = "_site"

    def __init__(
        self,
        workspace_root: Path,
        config: "InkConfig",
        article_manager: "ArticleManager",
        index_manager: "IndexManager",
    ) -> None:
        self._workspace_root = workspace_root
        self._config = config
        self._article_manager = article_manager
        self._index_manager = index_manager

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, *, include_all: bool = False, include_drafted: bool = False) -> BuildResult:
        """Build the static site.

        Args:
            include_all: If True, include articles of all statuses.
            include_drafted: If True, include drafted articles for preview.
                         If False (default), only include status=published.

        Returns:
            BuildResult with page_count, duration_ms, output_dir.
        """
        from ink_core.fs.markdown import parse_frontmatter
        from ink_core.core.status import ArticleStatus
        from ink_core.site.renderer import TemplateRenderer
        from ink_core.site.rss import RSSGenerator

        start = time.monotonic()

        output_dir = self._output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)

        renderer = TemplateRenderer(self._workspace_root)
        rss_gen = RSSGenerator()

        # Read timeline for ordered article list
        timeline = self._index_manager.read_timeline()

        # Load articles in timeline order
        articles: list[Article] = []
        for entry in timeline:
            canonical_id = entry.get("path", "")
            if not canonical_id:
                continue
            status = str(entry.get("status", ArticleStatus.DRAFT.value))
            if not include_all and status != ArticleStatus.PUBLISHED.value:
                if not (include_drafted and status == ArticleStatus.DRAFTED.value):
                    continue
            try:
                result = self._article_manager.read_by_id(canonical_id)
                articles.append(result.article)
            except Exception:
                continue

        page_count = 0

        site_title = self._config.get("site.title", "Blog")

        # Render individual article pages
        for article in articles:
            out_path = output_dir / Path(article.canonical_id) / "index.html"
            renderer.render_article(article, out_path, site_title=site_title)
            page_count += 1

        # Render index page
        index_path = output_dir / "index.html"
        renderer.render_index(articles, index_path, site_title=site_title, site_config={
            "subtitle": self._config.get("site.subtitle", ""),
            "author": self._config.get("site.author", "Anonymous"),
        })
        page_count += 1  # count index page

        # Generate RSS feed (published articles only, max 20)
        published_articles = [
            a for a in articles
            if _get_status(a) == ArticleStatus.PUBLISHED.value
        ] if (include_all or include_drafted) else articles

        feed_path = output_dir / "feed.xml"
        site_config = {
            "title": site_title,
            "author": self._config.get("site.author", "Anonymous"),
            "base_url": self._config.get("site.base_url", ""),
        }
        rss_gen.generate(published_articles, feed_path, site_config)

        duration_ms = int((time.monotonic() - start) * 1000)
        return BuildResult(
            page_count=page_count,
            duration_ms=duration_ms,
            output_dir=output_dir,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _output_dir(self) -> Path:
        """Resolve output directory from config or default."""
        configured = self._config.get("channels.blog.output", "")
        if configured:
            p = Path(configured)
            if not p.is_absolute():
                p = self._workspace_root / p
            return p
        return self._workspace_root / self.DEFAULT_OUTPUT_DIR


def _get_status(article: "Article") -> str:
    from ink_core.core.status import ArticleStatus
    from ink_core.fs.markdown import parse_frontmatter
    if isinstance(article.l1, dict):
        meta = article.l1.get("meta", {})
        if isinstance(meta, dict):
            s = meta.get("status")
            if s:
                return str(s)
    meta, _ = parse_frontmatter(article.l2)
    return str(meta.get("status", ArticleStatus.DRAFT.value))
