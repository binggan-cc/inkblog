"""Tests for SlugResolver in ink_core/fs/article.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from ink_core.fs.article import SlugResolver


@pytest.fixture
def resolver(tmp_path: Path) -> SlugResolver:
    return SlugResolver(workspace_root=tmp_path)


class TestGenerateSlug:
    def test_simple_english_title(self, resolver):
        assert resolver.generate_slug("Hello World") == "hello-world"

    def test_lowercase(self, resolver):
        assert resolver.generate_slug("My Blog Post") == "my-blog-post"

    def test_cjk_replaced_with_hyphens(self, resolver):
        slug = resolver.generate_slug("人工智能")
        assert slug == "untitled" or (slug.replace("-", "") == "" or slug == "untitled")
        # CJK chars become hyphens, then stripped → empty → "untitled"
        assert slug == "untitled"

    def test_mixed_cjk_and_english(self, resolver):
        slug = resolver.generate_slug("AI人工智能Guide")
        assert "ai" in slug
        assert "guide" in slug
        assert "人" not in slug

    def test_special_chars_replaced(self, resolver):
        slug = resolver.generate_slug("Hello, World! (2024)")
        assert slug == "hello-world-2024"

    def test_multiple_hyphens_collapsed(self, resolver):
        slug = resolver.generate_slug("Hello   World")
        assert "--" not in slug
        assert slug == "hello-world"

    def test_leading_trailing_hyphens_stripped(self, resolver):
        slug = resolver.generate_slug("  Hello World  ")
        assert not slug.startswith("-")
        assert not slug.endswith("-")

    def test_empty_title_returns_untitled(self, resolver):
        assert resolver.generate_slug("") == "untitled"

    def test_only_special_chars_returns_untitled(self, resolver):
        assert resolver.generate_slug("!!!") == "untitled"

    def test_only_cjk_returns_untitled(self, resolver):
        assert resolver.generate_slug("中文标题") == "untitled"

    def test_max_length_60(self, resolver):
        long_title = "a" * 100
        slug = resolver.generate_slug(long_title)
        assert len(slug) <= 60

    def test_truncate_at_word_boundary(self, resolver):
        # Create a title that produces a slug longer than 60 chars with hyphens
        title = "word " * 20  # "word-word-word-..." well over 60 chars
        slug = resolver.generate_slug(title)
        assert len(slug) <= 60
        assert not slug.endswith("-")

    def test_numbers_preserved(self, resolver):
        assert resolver.generate_slug("Top 10 Tips") == "top-10-tips"

    def test_underscores_treated_as_word_chars(self, resolver):
        # \w includes underscores, so they stay
        slug = resolver.generate_slug("hello_world")
        assert "hello" in slug
        assert "world" in slug


class TestCheckConflict:
    def test_no_conflict_when_path_absent(self, resolver, tmp_path):
        result = resolver.check_conflict("2025-03-20", "my-article")
        assert result is False

    def test_conflict_when_path_exists(self, resolver, tmp_path):
        article_dir = tmp_path / "2025" / "03" / "20-my-article"
        article_dir.mkdir(parents=True)
        result = resolver.check_conflict("2025-03-20", "my-article")
        assert result is True

    def test_different_date_no_conflict(self, resolver, tmp_path):
        article_dir = tmp_path / "2025" / "03" / "20-my-article"
        article_dir.mkdir(parents=True)
        # Different day
        result = resolver.check_conflict("2025-03-21", "my-article")
        assert result is False

    def test_different_slug_no_conflict(self, resolver, tmp_path):
        article_dir = tmp_path / "2025" / "03" / "20-my-article"
        article_dir.mkdir(parents=True)
        result = resolver.check_conflict("2025-03-20", "other-article")
        assert result is False

    def test_path_construction(self, resolver, tmp_path):
        """Verify path is constructed as workspace/YYYY/MM/DD-slug."""
        article_dir = tmp_path / "2026" / "04" / "15-test-slug"
        article_dir.mkdir(parents=True)
        assert resolver.check_conflict("2026-04-15", "test-slug") is True
        assert resolver.check_conflict("2026-04-16", "test-slug") is False
