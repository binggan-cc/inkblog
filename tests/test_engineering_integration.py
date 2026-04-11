"""Integration tests for engineering hardening tasks."""

from __future__ import annotations

from pathlib import Path

from ink_core.core.config import InkConfig
from ink_core.fs.article import ArticleManager
from ink_core.fs.index_manager import IndexManager
from ink_core.fs.markdown import parse_frontmatter
from ink_core.site.builder import SiteBuilder
from ink_core.skills.registry import SkillRegistry
from ink_core.skills.publish import PublishSkill


def test_chinese_mixed_titles_create_distinct_slugs(tmp_path: Path) -> None:
    manager = ArticleManager(tmp_path)
    a = manager.create("Python 深度学习", date="2025-04-01")
    b = manager.create("Python 机器学习", date="2025-04-02")
    assert a.slug != b.slug
    assert a.slug.startswith("python-")
    assert b.slug.startswith("python-")


def test_xss_article_build_is_safe(tmp_path: Path) -> None:
    manager = ArticleManager(tmp_path)
    index_mgr = IndexManager(tmp_path)
    article = manager.create("<script>alert(1)</script>", date="2025-04-03", slug="xss")
    index_path = article.path / "index.md"
    content = index_path.read_text(encoding="utf-8").replace(
        "# <script>alert(1)</script>",
        "# <script>alert(1)</script>\n\n<script>alert(2)</script>",
    )
    content = content.replace("status: draft", "status: published")
    index_path.write_text(content, encoding="utf-8")
    article.l2 = content
    manager.update_layers(article)
    updated = manager.read(article.path).article
    index_mgr.update_timeline(updated)

    builder = SiteBuilder(tmp_path, InkConfig(), ArticleManager(tmp_path), index_mgr)
    builder.build()

    html = (tmp_path / "_site" / article.canonical_id / "index.html").read_text(encoding="utf-8")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_custom_skill_execution_and_path_traversal(tmp_path: Path) -> None:
    article = ArticleManager(tmp_path).create("Skill Chain", date="2025-04-04")
    skills_dir = tmp_path / ".ink" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "ok.md").write_text(
        """---
skill: ok
version: "1.0"
context_requirement: L0
---
## 执行流程
1. read_content L0
2. write_file ok/out.txt
""",
        encoding="utf-8",
    )
    (skills_dir / "bad.md").write_text(
        """---
skill: bad
version: "1.0"
context_requirement: L0
---
## 执行流程
1. write_file ../../escape.txt
""",
        encoding="utf-8",
    )

    registry = SkillRegistry.create_with_builtins(tmp_path)
    registry.load_from_directory(skills_dir)

    ok_result = registry.resolve("ok").execute(article.canonical_id, {})
    bad_result = registry.resolve("bad").execute(article.canonical_id, {})

    assert ok_result.success
    assert (tmp_path / ".ink" / "skill-output" / "ok" / "out.txt").exists()
    assert not bad_result.success
    assert not (tmp_path / "escape.txt").exists()


def test_publish_mastodon_draft_saved_advances_to_drafted(tmp_path: Path) -> None:
    article = ArticleManager(tmp_path).create("Mastodon Draft", date="2025-04-05")
    index_path = article.path / "index.md"
    index_path.write_text(
        index_path.read_text(encoding="utf-8").replace("status: draft", "status: ready"),
        encoding="utf-8",
    )

    result = PublishSkill(tmp_path).execute(
        article.canonical_id,
        {"channels": ["mastodon"], "session_id": "draft-only"},
    )

    meta, _ = parse_frontmatter(index_path.read_text(encoding="utf-8"))
    assert result.success
    assert meta["status"] == "drafted"
    assert (tmp_path / ".ink" / "publish-history" / "2025" / "04" / "05-mastodon-draft").exists()
    assert (tmp_path / "_index" / "timeline.json").exists()
