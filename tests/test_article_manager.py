"""Unit tests for ArticleManager in ink_core/fs/article.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from ink_core.core.errors import PathConflictError, PathNotFoundError
from ink_core.fs.article import Article, ArticleManager, ArticleReadResult


@pytest.fixture
def manager(tmp_path: Path) -> ArticleManager:
    return ArticleManager(workspace_root=tmp_path)


@pytest.fixture
def manager_with_templates(tmp_path: Path) -> ArticleManager:
    """ArticleManager with a default template available."""
    templates_dir = tmp_path / "_templates" / "default"
    templates_dir.mkdir(parents=True)
    (templates_dir / "index.md").write_text(
        "# {{title}}\n\n## 正文\n\n{{content}}\n", encoding="utf-8"
    )
    return ArticleManager(workspace_root=tmp_path)


# ---------------------------------------------------------------------------
# create()
# ---------------------------------------------------------------------------

class TestCreate:
    def test_creates_directory_structure(self, manager, tmp_path):
        article = manager.create("Hello World", date="2025-03-20")
        article_dir = tmp_path / "2025" / "03" / "20-hello-world"
        assert article_dir.exists()
        assert (article_dir / "index.md").exists()
        assert (article_dir / ".abstract").exists()
        assert (article_dir / ".overview").exists()
        assert (article_dir / "assets").is_dir()

    def test_returns_article_with_correct_fields(self, manager, tmp_path):
        article = manager.create("My Post", date="2026-04-15", slug="my-post", tags=["a", "b"])
        assert article.slug == "my-post"
        assert article.date == "2026-04-15"
        assert article.folder_name == "15-my-post"
        assert article.canonical_id == "2026/04/15-my-post"
        assert article.path == tmp_path / "2026" / "04" / "15-my-post"

    def test_index_md_frontmatter_fields(self, manager, tmp_path):
        from ink_core.fs.markdown import parse_frontmatter
        article = manager.create("Test Article", date="2025-01-01", tags=["x"])
        index_content = (article.path / "index.md").read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(index_content)
        assert meta["title"] == "Test Article"
        assert meta["status"] == "draft"
        assert meta["date"] == "2025-01-01"
        assert "x" in meta["tags"]
        assert "slug" in meta

    def test_auto_generates_slug_from_title(self, manager):
        article = manager.create("Hello World", date="2025-03-20")
        assert article.slug == "hello-world"

    def test_explicit_slug_used(self, manager):
        article = manager.create("Some Title", date="2025-03-20", slug="custom-slug")
        assert article.slug == "custom-slug"
        assert article.folder_name == "20-custom-slug"

    def test_raises_path_conflict_error_on_duplicate(self, manager, tmp_path):
        manager.create("First", date="2025-03-20", slug="my-slug")
        with pytest.raises(PathConflictError):
            manager.create("Second", date="2025-03-20", slug="my-slug")

    def test_no_files_created_on_conflict(self, manager, tmp_path):
        manager.create("First", date="2025-03-20", slug="my-slug")
        article_dir = tmp_path / "2025" / "03" / "20-my-slug"
        files_before = set(article_dir.iterdir())
        with pytest.raises(PathConflictError):
            manager.create("Second", date="2025-03-20", slug="my-slug")
        files_after = set(article_dir.iterdir())
        assert files_before == files_after

    def test_default_tags_empty(self, manager):
        article = manager.create("No Tags", date="2025-03-20")
        from ink_core.fs.markdown import parse_frontmatter
        meta, _ = parse_frontmatter(article.l2)
        assert meta["tags"] == []

    def test_l0_is_single_line(self, manager):
        article = manager.create("Test", date="2025-03-20")
        assert "\n" not in article.l0.strip()

    def test_l1_has_required_keys(self, manager):
        article = manager.create("Test", date="2025-03-20")
        assert "meta" in article.l1
        assert "summary" in article.l1
        assert "key_points" in article.l1

    def test_uses_default_template_when_available(self, manager_with_templates):
        article = manager_with_templates.create("Template Test", date="2025-03-20")
        assert "Template Test" in article.l2

    def test_falls_back_to_minimal_template(self, manager):
        # No _templates/ directory exists in tmp_path
        article = manager.create("Minimal", date="2025-03-20")
        assert "Minimal" in article.l2


# ---------------------------------------------------------------------------
# read()
# ---------------------------------------------------------------------------

class TestRead:
    def test_reads_existing_article(self, manager, tmp_path):
        created = manager.create("Read Test", date="2025-05-10", slug="read-test")
        result = manager.read(created.path)
        assert isinstance(result, ArticleReadResult)
        assert result.article.canonical_id == "2025/05/10-read-test"
        assert result.article.slug == "read-test"
        assert result.article.date == "2025-05-10"

    def test_no_changed_files_when_all_present(self, manager):
        created = manager.create("Full Article", date="2025-05-10", slug="full-article")
        result = manager.read(created.path)
        assert result.changed_files == []

    def test_self_heals_missing_abstract(self, manager):
        created = manager.create("Heal Abstract", date="2025-05-10", slug="heal-abstract")
        (created.path / ".abstract").unlink()
        result = manager.read(created.path)
        assert (created.path / ".abstract").exists()
        assert created.path / ".abstract" in result.changed_files

    def test_self_heals_missing_overview(self, manager):
        created = manager.create("Heal Overview", date="2025-05-10", slug="heal-overview")
        (created.path / ".overview").unlink()
        result = manager.read(created.path)
        assert (created.path / ".overview").exists()
        assert created.path / ".overview" in result.changed_files

    def test_self_heals_both_missing(self, manager):
        created = manager.create("Heal Both", date="2025-05-10", slug="heal-both")
        (created.path / ".abstract").unlink()
        (created.path / ".overview").unlink()
        result = manager.read(created.path)
        assert len(result.changed_files) == 2

    def test_raises_path_not_found_for_missing_dir(self, manager, tmp_path):
        with pytest.raises(PathNotFoundError):
            manager.read(tmp_path / "nonexistent" / "path")

    def test_raises_path_not_found_for_missing_index(self, manager, tmp_path):
        article_dir = tmp_path / "2025" / "03" / "20-no-index"
        article_dir.mkdir(parents=True)
        with pytest.raises(PathNotFoundError):
            manager.read(article_dir)

    def test_article_l2_matches_index_md(self, manager):
        created = manager.create("L2 Test", date="2025-05-10", slug="l2-test")
        result = manager.read(created.path)
        expected = (created.path / "index.md").read_text(encoding="utf-8")
        assert result.article.l2 == expected


# ---------------------------------------------------------------------------
# read_by_id()
# ---------------------------------------------------------------------------

class TestReadById:
    def test_reads_by_canonical_id(self, manager):
        manager.create("By ID", date="2025-06-01", slug="by-id")
        result = manager.read_by_id("2025/06/01-by-id")
        assert result.article.canonical_id == "2025/06/01-by-id"

    def test_raises_for_nonexistent_id(self, manager):
        with pytest.raises(PathNotFoundError):
            manager.read_by_id("2025/01/01-nonexistent")


# ---------------------------------------------------------------------------
# resolve_path() and resolve_canonical_id()
# ---------------------------------------------------------------------------

class TestResolve:
    def test_resolve_path_from_canonical_id(self, manager, tmp_path):
        path = manager.resolve_path("2025/03/20-my-article")
        assert path == tmp_path / "2025" / "03" / "20-my-article"

    def test_resolve_canonical_id_from_path(self, manager, tmp_path):
        path = tmp_path / "2025" / "03" / "20-my-article"
        cid = manager.resolve_canonical_id(path)
        assert cid == "2025/03/20-my-article"

    def test_canonical_id_no_trailing_slash(self, manager, tmp_path):
        path = tmp_path / "2026" / "04" / "15-test"
        cid = manager.resolve_canonical_id(path)
        assert not cid.endswith("/")

    def test_roundtrip_path_canonical_id(self, manager, tmp_path):
        original_path = tmp_path / "2025" / "03" / "20-roundtrip"
        cid = manager.resolve_canonical_id(original_path)
        recovered_path = manager.resolve_path(cid)
        assert recovered_path == original_path


# ---------------------------------------------------------------------------
# update_layers()
# ---------------------------------------------------------------------------

class TestUpdateLayers:
    def test_returns_two_changed_files(self, manager):
        created = manager.create("Update Test", date="2025-07-01", slug="update-test")
        changed = manager.update_layers(created)
        assert len(changed) == 2
        paths = {p.name for p in changed}
        assert ".abstract" in paths
        assert ".overview" in paths

    def test_overwrites_existing_layers(self, manager):
        created = manager.create("Overwrite Test", date="2025-07-01", slug="overwrite-test")
        # Manually corrupt the .abstract
        (created.path / ".abstract").write_text("CORRUPTED", encoding="utf-8")
        manager.update_layers(created)
        new_abstract = (created.path / ".abstract").read_text(encoding="utf-8")
        assert new_abstract != "CORRUPTED"

    def test_preserves_created_at_in_overview(self, manager):
        from ink_core.fs.markdown import parse_overview
        created = manager.create("Preserve CreatedAt", date="2025-07-01", slug="preserve-created-at")
        # Read original created_at
        original_overview = parse_overview(
            (created.path / ".overview").read_text(encoding="utf-8")
        )
        original_created_at = original_overview["meta"].get("created_at")
        # Update layers
        manager.update_layers(created)
        updated_overview = parse_overview(
            (created.path / ".overview").read_text(encoding="utf-8")
        )
        assert updated_overview["meta"].get("created_at") == original_created_at


# ---------------------------------------------------------------------------
# list_all()
# ---------------------------------------------------------------------------

class TestListAll:
    def test_returns_empty_for_empty_workspace(self, manager):
        assert manager.list_all() == []

    def test_lists_single_article(self, manager):
        manager.create("Article One", date="2025-03-20", slug="article-one")
        articles = manager.list_all()
        assert len(articles) == 1
        assert articles[0].slug == "article-one"

    def test_lists_multiple_articles(self, manager):
        manager.create("Article A", date="2025-03-20", slug="article-a")
        manager.create("Article B", date="2025-03-21", slug="article-b")
        manager.create("Article C", date="2026-01-01", slug="article-c")
        articles = manager.list_all()
        assert len(articles) == 3

    def test_skips_non_article_dirs(self, manager, tmp_path):
        # Create a year dir with a non-article subdirectory
        (tmp_path / "2025" / "03" / "not-an-article").mkdir(parents=True)
        manager.create("Real Article", date="2025-03-20", slug="real-article")
        articles = manager.list_all()
        assert len(articles) == 1

    def test_skips_non_year_dirs(self, manager, tmp_path):
        # _templates, _index, etc. should be ignored
        (tmp_path / "_templates").mkdir()
        (tmp_path / "_index").mkdir()
        manager.create("Only Article", date="2025-03-20", slug="only-article")
        articles = manager.list_all()
        assert len(articles) == 1

    def test_all_articles_have_valid_canonical_ids(self, manager):
        manager.create("Post One", date="2025-03-20", slug="post-one")
        manager.create("Post Two", date="2025-04-01", slug="post-two")
        articles = manager.list_all()
        for article in articles:
            parts = article.canonical_id.split("/")
            assert len(parts) == 3
            assert parts[0].isdigit() and len(parts[0]) == 4
            assert parts[1].isdigit() and len(parts[1]) == 2
