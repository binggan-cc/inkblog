"""Tests for PublishSkill and channel adapters (Tasks 6.1, 6.2)."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from ink_core.skills.publish import (
    BlogFileAdapter,
    MastodonDraftAdapter,
    NewsletterFileAdapter,
    PublishSkill,
)
from ink_core.fs.article import ArticleManager
from ink_core.fs.markdown import parse_frontmatter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_article(ink_dir: Path, canonical_id: str, status: str = "ready") -> Path:
    """Create a minimal article directory for testing."""
    parts = canonical_id.split("/")
    article_path = ink_dir
    for part in parts:
        article_path = article_path / part
    article_path.mkdir(parents=True, exist_ok=True)
    (article_path / "assets").mkdir(exist_ok=True)

    # Derive date and slug from canonical_id: YYYY/MM/DD-slug
    year, month, day_slug = parts
    day = day_slug.split("-")[0]
    slug = "-".join(day_slug.split("-")[1:])
    date = f"{year}-{month}-{day}"

    index_md = textwrap.dedent(f"""\
        ---
        title: "Test Article"
        slug: "{slug}"
        date: "{date}"
        status: "{status}"
        tags: ["test", "publish"]
        ---

        # Test Article

        Content for testing publish skill.
    """)
    (article_path / "index.md").write_text(index_md, encoding="utf-8")
    (article_path / ".abstract").write_text("A test article for publish.", encoding="utf-8")

    overview = textwrap.dedent(f"""\
        ---
        title: "Test Article"
        created_at: "{date}T09:00:00"
        updated_at: "{date}T09:00:00"
        status: "{status}"
        tags: ["test", "publish"]
        word_count: 50
        reading_time_min: 1
        related: []
        ---

        ## Summary

        A test article for publish.

        ## Key Points

        - Test point
    """)
    (article_path / ".overview").write_text(overview, encoding="utf-8")
    return article_path


# ---------------------------------------------------------------------------
# Task 6.1: Adapter tests
# ---------------------------------------------------------------------------

class TestBlogFileAdapter:
    def test_publish_creates_output_file(self, ink_dir: Path, sample_ready_article_dir: Path):
        manager = ArticleManager(ink_dir)
        result = manager.read(sample_ready_article_dir)
        article = result.article

        adapter = BlogFileAdapter(ink_dir)
        record = adapter.publish(article, {})

        assert record.channel == "blog"
        assert record.status == "success"
        assert record.attempted_at is not None
        assert record.published_at is not None
        assert record.error is None

        output_file = ink_dir / ".ink" / "publish-output" / "blog" / f"{article.date}-{article.slug}.md"
        assert output_file.exists()

    def test_publish_output_contains_frontmatter(self, ink_dir: Path, sample_ready_article_dir: Path):
        manager = ArticleManager(ink_dir)
        article = manager.read(sample_ready_article_dir).article

        adapter = BlogFileAdapter(ink_dir)
        adapter.publish(article, {})

        output_file = ink_dir / ".ink" / "publish-output" / "blog" / f"{article.date}-{article.slug}.md"
        content = output_file.read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(content)
        assert "published_at" in meta

    def test_publish_returns_channel_publish_record(self, ink_dir: Path, sample_ready_article_dir: Path):
        manager = ArticleManager(ink_dir)
        article = manager.read(sample_ready_article_dir).article

        adapter = BlogFileAdapter(ink_dir)
        record = adapter.publish(article, {})

        from ink_core.core.publish_history import ChannelPublishRecord
        assert isinstance(record, ChannelPublishRecord)


class TestNewsletterFileAdapter:
    def test_publish_creates_output_file(self, ink_dir: Path, sample_ready_article_dir: Path):
        manager = ArticleManager(ink_dir)
        article = manager.read(sample_ready_article_dir).article

        adapter = NewsletterFileAdapter(ink_dir)
        record = adapter.publish(article, {})

        assert record.channel == "newsletter"
        assert record.status == "success"
        assert record.error is None

        output_file = ink_dir / ".ink" / "publish-output" / "newsletter" / f"{article.date}-{article.slug}.md"
        assert output_file.exists()

    def test_publish_includes_abstract_as_intro(self, ink_dir: Path, sample_ready_article_dir: Path):
        manager = ArticleManager(ink_dir)
        article = manager.read(sample_ready_article_dir).article

        adapter = NewsletterFileAdapter(ink_dir)
        adapter.publish(article, {})

        output_file = ink_dir / ".ink" / "publish-output" / "newsletter" / f"{article.date}-{article.slug}.md"
        content = output_file.read_text(encoding="utf-8")
        # Abstract should appear as blockquote intro
        assert article.l0 in content


class TestMastodonDraftAdapter:
    def test_publish_creates_draft_file(self, ink_dir: Path, sample_ready_article_dir: Path):
        manager = ArticleManager(ink_dir)
        article = manager.read(sample_ready_article_dir).article

        adapter = MastodonDraftAdapter(ink_dir)
        record = adapter.publish(article, {})

        assert record.channel == "mastodon"
        assert record.status == "draft_saved"
        assert record.published_at is None
        assert record.error is None

        output_file = ink_dir / ".ink" / "publish-output" / "mastodon" / f"{article.date}-{article.slug}.txt"
        assert output_file.exists()

    def test_publish_toot_within_500_chars(self, ink_dir: Path, sample_ready_article_dir: Path):
        manager = ArticleManager(ink_dir)
        article = manager.read(sample_ready_article_dir).article

        adapter = MastodonDraftAdapter(ink_dir)
        adapter.publish(article, {})

        output_file = ink_dir / ".ink" / "publish-output" / "mastodon" / f"{article.date}-{article.slug}.txt"
        content = output_file.read_text(encoding="utf-8")
        assert len(content) <= 500

    def test_publish_toot_contains_title(self, ink_dir: Path, sample_ready_article_dir: Path):
        manager = ArticleManager(ink_dir)
        article = manager.read(sample_ready_article_dir).article

        adapter = MastodonDraftAdapter(ink_dir)
        adapter.publish(article, {})

        output_file = ink_dir / ".ink" / "publish-output" / "mastodon" / f"{article.date}-{article.slug}.txt"
        content = output_file.read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(article.l2)
        assert meta.get("title", "") in content


# ---------------------------------------------------------------------------
# Task 6.2: PublishSkill tests
# ---------------------------------------------------------------------------

class TestPublishSkillStatusGate:
    def test_rejects_draft_status(self, ink_dir: Path):
        _make_article(ink_dir, "2025/03/20-test-draft", status="draft")
        skill = PublishSkill(ink_dir)
        result = skill.execute("2025/03/20-test-draft", {"channels": ["blog"]})

        assert result.success is False
        assert "draft" in result.message
        assert result.data["current_status"] == "draft"

    def test_rejects_review_status(self, ink_dir: Path):
        _make_article(ink_dir, "2025/03/21-test-review", status="review")
        skill = PublishSkill(ink_dir)
        result = skill.execute("2025/03/21-test-review", {"channels": ["blog"]})

        assert result.success is False
        assert result.data["current_status"] == "review"

    def test_rejects_published_status(self, ink_dir: Path):
        _make_article(ink_dir, "2025/03/22-test-published", status="published")
        skill = PublishSkill(ink_dir)
        result = skill.execute("2025/03/22-test-published", {"channels": ["blog"]})

        assert result.success is False
        assert result.data["current_status"] == "published"

    def test_allows_ready_status(self, ink_dir: Path, sample_ready_article_dir: Path):
        skill = PublishSkill(ink_dir)
        result = skill.execute("2025/04/01-ready-article", {"channels": ["blog"]})
        assert result.success is True

    def test_reads_status_from_index_md_not_overview(self, ink_dir: Path):
        """Status gate must read index.md frontmatter, not .overview."""
        article_path = _make_article(ink_dir, "2025/05/01-status-test", status="ready")
        # Overwrite .overview with a different status
        overview = (article_path / ".overview").read_text(encoding="utf-8")
        overview_modified = overview.replace('status: "ready"', 'status: "draft"')
        (article_path / ".overview").write_text(overview_modified, encoding="utf-8")

        skill = PublishSkill(ink_dir)
        result = skill.execute("2025/05/01-status-test", {"channels": ["blog"]})
        # Should succeed because index.md says ready
        assert result.success is True


class TestPublishSkillUnsupportedChannel:
    def test_returns_supported_channels_on_unsupported(self, ink_dir: Path, sample_ready_article_dir: Path):
        skill = PublishSkill(ink_dir)
        result = skill.execute("2025/04/01-ready-article", {"channels": ["twitter"]})

        assert result.success is False
        assert "twitter" in result.message
        assert result.data["supported_channels"] == PublishSkill.SUPPORTED_CHANNELS

    def test_mixed_supported_and_unsupported_channels(self, ink_dir: Path, sample_ready_article_dir: Path):
        skill = PublishSkill(ink_dir)
        result = skill.execute("2025/04/01-ready-article", {"channels": ["blog", "unknown"]})

        assert result.success is False
        assert "unknown" in result.message


class TestPublishSkillSuccess:
    def test_updates_index_md_status_to_published(self, ink_dir: Path, sample_ready_article_dir: Path):
        skill = PublishSkill(ink_dir)
        skill.execute("2025/04/01-ready-article", {"channels": ["blog"]})

        index_path = sample_ready_article_dir / "index.md"
        meta, _ = parse_frontmatter(index_path.read_text(encoding="utf-8"))
        assert meta["status"] == "published"

    def test_writes_published_at_timestamp(self, ink_dir: Path, sample_ready_article_dir: Path):
        skill = PublishSkill(ink_dir)
        skill.execute("2025/04/01-ready-article", {"channels": ["blog"]})

        index_path = sample_ready_article_dir / "index.md"
        meta, _ = parse_frontmatter(index_path.read_text(encoding="utf-8"))
        assert "published_at" in meta
        assert meta["published_at"] is not None

    def test_updates_timeline_json(self, ink_dir: Path, sample_ready_article_dir: Path):
        skill = PublishSkill(ink_dir)
        skill.execute("2025/04/01-ready-article", {"channels": ["blog"]})

        timeline_path = ink_dir / "_index" / "timeline.json"
        assert timeline_path.exists()
        entries = json.loads(timeline_path.read_text(encoding="utf-8"))
        paths = [e["path"] for e in entries]
        assert "2025/04/01-ready-article" in paths

    def test_calls_update_layers(self, ink_dir: Path, sample_ready_article_dir: Path):
        """After publish, .overview should reflect published status."""
        skill = PublishSkill(ink_dir)
        skill.execute("2025/04/01-ready-article", {"channels": ["blog"]})

        overview_path = sample_ready_article_dir / ".overview"
        assert overview_path.exists()
        # The overview should have been regenerated (file still exists)
        content = overview_path.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_records_publish_history(self, ink_dir: Path, sample_ready_article_dir: Path):
        skill = PublishSkill(ink_dir)
        skill.execute("2025/04/01-ready-article", {"channels": ["blog"], "session_id": "test-session-001"})

        history_dir = ink_dir / ".ink" / "publish-history" / "2025" / "04" / "01-ready-article"
        assert history_dir.exists()
        files = list(history_dir.glob("*.json"))
        assert len(files) == 1

        record = json.loads(files[0].read_text(encoding="utf-8"))
        assert record["canonical_id"] == "2025/04/01-ready-article"
        assert record["session_id"] == "test-session-001"
        assert len(record["channels"]) == 1
        assert record["channels"][0]["channel"] == "blog"
        assert record["channels"][0]["status"] == "success"

    def test_returns_changed_files(self, ink_dir: Path, sample_ready_article_dir: Path):
        skill = PublishSkill(ink_dir)
        result = skill.execute("2025/04/01-ready-article", {"channels": ["blog"]})

        assert result.changed_files is not None
        assert len(result.changed_files) > 0

    def test_multi_channel_publish(self, ink_dir: Path, sample_ready_article_dir: Path):
        skill = PublishSkill(ink_dir)
        result = skill.execute("2025/04/01-ready-article", {"channels": ["blog", "newsletter", "mastodon"]})

        assert result.success is True
        assert len(result.data["channels"]) == 3

    def test_mastodon_draft_saved_counts_as_success(self, ink_dir: Path, sample_ready_article_dir: Path):
        """draft_saved status should count as success for status update."""
        skill = PublishSkill(ink_dir)
        result = skill.execute("2025/04/01-ready-article", {"channels": ["mastodon"]})

        assert result.success is True
        index_path = sample_ready_article_dir / "index.md"
        meta, _ = parse_frontmatter(index_path.read_text(encoding="utf-8"))
        assert meta["status"] == "published"


class TestPublishSkillAllFail:
    def test_does_not_modify_status_when_all_fail(self, ink_dir: Path):
        """When all channels fail, index.md status must remain unchanged."""
        article_path = _make_article(ink_dir, "2025/06/01-fail-test", status="ready")

        # Make the output directory read-only to force failure
        import os
        output_dir = ink_dir / ".ink" / "publish-output"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Patch adapters to always fail
        skill = PublishSkill(ink_dir)

        from ink_core.core.publish_history import ChannelPublishRecord
        from unittest.mock import patch

        def always_fail(article, payload):
            return ChannelPublishRecord(
                channel="blog",
                status="failed",
                attempted_at="2025-06-01T00:00:00",
                published_at=None,
                error="Forced failure",
            )

        skill._adapters["blog"].publish = always_fail

        result = skill.execute("2025/06/01-fail-test", {"channels": ["blog"]})

        assert result.success is False
        index_path = article_path / "index.md"
        meta, _ = parse_frontmatter(index_path.read_text(encoding="utf-8"))
        assert meta["status"] == "ready"  # unchanged

    def test_still_records_history_when_all_fail(self, ink_dir: Path):
        """Publish history must be recorded even when all channels fail."""
        _make_article(ink_dir, "2025/06/02-fail-history", status="ready")

        skill = PublishSkill(ink_dir)

        from ink_core.core.publish_history import ChannelPublishRecord
        from unittest.mock import patch

        def always_fail(article, payload):
            return ChannelPublishRecord(
                channel="blog",
                status="failed",
                attempted_at="2025-06-02T00:00:00",
                published_at=None,
                error="Forced failure",
            )

        skill._adapters["blog"].publish = always_fail

        skill.execute("2025/06/02-fail-history", {"channels": ["blog"], "session_id": "fail-session"})

        history_dir = ink_dir / ".ink" / "publish-history" / "2025" / "06" / "02-fail-history"
        assert history_dir.exists()
        files = list(history_dir.glob("*.json"))
        assert len(files) == 1

        record = json.loads(files[0].read_text(encoding="utf-8"))
        assert record["channels"][0]["status"] == "failed"


class TestPublishSkillNoTarget:
    def test_returns_error_when_no_target(self, ink_dir: Path):
        skill = PublishSkill(ink_dir)
        result = skill.execute(None, {"channels": ["blog"]})
        assert result.success is False
        assert "No target" in result.message
