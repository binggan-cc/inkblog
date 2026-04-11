"""Tests for TemplateRenderer autoescape behavior."""

from __future__ import annotations

from pathlib import Path

from ink_core.fs.article import ArticleManager
from ink_core.site.renderer import TemplateRenderer


def test_title_is_autoescaped(tmp_path: Path) -> None:
    manager = ArticleManager(tmp_path)
    article = manager.create("<script>alert(1)</script>", date="2025-01-01")

    out = tmp_path / "_site" / "article.html"
    TemplateRenderer(tmp_path).render_article(article, out)

    html = out.read_text(encoding="utf-8")
    assert "<h1><script>" not in html
    assert "&lt;script&gt;" in html


def test_body_html_is_not_double_escaped(tmp_path: Path) -> None:
    manager = ArticleManager(tmp_path)
    article = manager.create("Body Test", date="2025-01-02")
    index_path = article.path / "index.md"
    content = index_path.read_text(encoding="utf-8") + "\n\n**bold** <script>x</script>"
    index_path.write_text(content, encoding="utf-8")
    article.l2 = content

    out = tmp_path / "_site" / "article.html"
    TemplateRenderer(tmp_path).render_article(article, out)

    html = out.read_text(encoding="utf-8")
    assert "<strong>bold</strong>" in html
    assert "&lt;strong&gt;bold&lt;/strong&gt;" not in html
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
