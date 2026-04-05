"""Publish skill and channel adapters for ink_core."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from ink_core.core.errors import InvalidStatusError, UnsupportedChannelError
from ink_core.core.publish_history import ChannelPublishRecord, PublishHistoryManager
from ink_core.fs.article import Article, ArticleManager
from ink_core.fs.index_manager import IndexManager
from ink_core.fs.markdown import dump_frontmatter, parse_frontmatter
from ink_core.skills.base import Skill, SkillResult


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string (no microseconds)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------------------
# PublisherAdapter ABC
# ---------------------------------------------------------------------------

class PublisherAdapter(ABC):
    """Abstract interface for a publish channel adapter."""

    channel: str

    @abstractmethod
    def publish(self, article: Article, payload: dict) -> ChannelPublishRecord:
        """Publish the article to this channel and return a record."""
        ...


# ---------------------------------------------------------------------------
# Phase 1 adapters – write local files, no real API calls
# ---------------------------------------------------------------------------

class BlogFileAdapter(PublisherAdapter):
    """Phase 1: write a local blog-format Markdown file."""

    channel = "blog"

    def __init__(self, workspace_root: Path) -> None:
        self._output_dir = workspace_root / ".ink" / "publish-output" / "blog"

    def publish(self, article: Article, payload: dict) -> ChannelPublishRecord:
        attempted_at = _now_iso()
        try:
            self._output_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{article.date}-{article.slug}.md"
            output_path = self._output_dir / filename

            meta, body = parse_frontmatter(article.l2)
            # Ensure published_at is recorded in the output file meta
            meta["published_at"] = attempted_at
            content = dump_frontmatter(meta, body)
            output_path.write_text(content, encoding="utf-8")

            published_at = _now_iso()
            return ChannelPublishRecord(
                channel=self.channel,
                status="success",
                attempted_at=attempted_at,
                published_at=published_at,
                error=None,
            )
        except Exception as exc:
            return ChannelPublishRecord(
                channel=self.channel,
                status="failed",
                attempted_at=attempted_at,
                published_at=None,
                error=str(exc),
            )


class NewsletterFileAdapter(PublisherAdapter):
    """Phase 1: write a local newsletter-format Markdown file."""

    channel = "newsletter"

    def __init__(self, workspace_root: Path) -> None:
        self._output_dir = workspace_root / ".ink" / "publish-output" / "newsletter"

    def publish(self, article: Article, payload: dict) -> ChannelPublishRecord:
        attempted_at = _now_iso()
        try:
            self._output_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{article.date}-{article.slug}.md"
            output_path = self._output_dir / filename

            meta, body = parse_frontmatter(article.l2)
            # Newsletter format: include abstract as intro
            newsletter_body = f"> {article.l0}\n\n{body}" if article.l0 else body
            meta["newsletter_published_at"] = attempted_at
            content = dump_frontmatter(meta, newsletter_body)
            output_path.write_text(content, encoding="utf-8")

            published_at = _now_iso()
            return ChannelPublishRecord(
                channel=self.channel,
                status="success",
                attempted_at=attempted_at,
                published_at=published_at,
                error=None,
            )
        except Exception as exc:
            return ChannelPublishRecord(
                channel=self.channel,
                status="failed",
                attempted_at=attempted_at,
                published_at=None,
                error=str(exc),
            )


class MastodonDraftAdapter(PublisherAdapter):
    """Phase 1: write a local Mastodon draft text file (no real API call)."""

    channel = "mastodon"
    MAX_CHARS = 500

    def __init__(self, workspace_root: Path) -> None:
        self._output_dir = workspace_root / ".ink" / "publish-output" / "mastodon"

    def publish(self, article: Article, payload: dict) -> ChannelPublishRecord:
        attempted_at = _now_iso()
        try:
            self._output_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{article.date}-{article.slug}.txt"
            output_path = self._output_dir / filename

            meta, _ = parse_frontmatter(article.l2)
            title = meta.get("title", article.slug)
            tags = meta.get("tags", [])
            hashtags = " ".join(f"#{t}" for t in tags) if tags else ""

            # Build toot text: title + abstract + hashtags, truncated to 500 chars
            abstract = article.l0 or ""
            toot = f"{title}\n\n{abstract}"
            if hashtags:
                toot = f"{toot}\n\n{hashtags}"
            if len(toot) > self.MAX_CHARS:
                toot = toot[: self.MAX_CHARS - 1] + "…"

            output_path.write_text(toot, encoding="utf-8")

            return ChannelPublishRecord(
                channel=self.channel,
                status="draft_saved",
                attempted_at=attempted_at,
                published_at=None,
                error=None,
            )
        except Exception as exc:
            return ChannelPublishRecord(
                channel=self.channel,
                status="failed",
                attempted_at=attempted_at,
                published_at=None,
                error=str(exc),
            )


# ---------------------------------------------------------------------------
# PublishSkill
# ---------------------------------------------------------------------------

class PublishSkill(Skill):
    """Publish an article to one or more channels (Phase 1: local file output)."""

    SUPPORTED_CHANNELS = ["blog", "newsletter", "mastodon"]

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root
        self._article_manager = ArticleManager(workspace_root)
        self._index_manager = IndexManager(workspace_root)
        self._history_manager = PublishHistoryManager(workspace_root)
        self._adapters: dict[str, PublisherAdapter] = {
            "blog": BlogFileAdapter(workspace_root),
            "newsletter": NewsletterFileAdapter(workspace_root),
            "mastodon": MastodonDraftAdapter(workspace_root),
        }

    # ------------------------------------------------------------------
    # Skill ABC
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "publish"

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def context_requirement(self) -> str:
        return "L2"

    # ------------------------------------------------------------------
    # execute
    # ------------------------------------------------------------------

    def execute(self, target: str | None, params: dict) -> SkillResult:
        """Execute the publish skill.

        Args:
            target: Canonical ID of the article to publish, or None when --all.
            params: Must contain 'channels' (list[str]) and optionally
                    'session_id' (str) and 'all' (bool).

        Returns:
            SkillResult with success/failure details.
        """
        # --all: publish every article with status=ready
        if params.get("all"):
            return self._execute_all(params)

        if not target:
            return SkillResult(
                success=False,
                message="No target article specified. Usage: ink publish <canonical-id> --channels <channel-list>",
            )

        channels: list[str] = params.get("channels", self.SUPPORTED_CHANNELS)
        session_id: str = params.get("session_id", _now_iso())

        # --- Validate channels ---
        unsupported = [c for c in channels if c not in self.SUPPORTED_CHANNELS]
        if unsupported:
            return SkillResult(
                success=False,
                message=(
                    f"Unsupported channel(s): {unsupported}. "
                    f"Supported channels: {self.SUPPORTED_CHANNELS}"
                ),
                data={"supported_channels": self.SUPPORTED_CHANNELS},
            )

        # --- Read article ---
        try:
            read_result = self._article_manager.read_by_id(target)
        except Exception as exc:
            return SkillResult(success=False, message=str(exc))

        article = read_result.article

        # --- Status gate: read from index.md frontmatter directly ---
        index_path = article.path / "index.md"
        raw_index = index_path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(raw_index)
        current_status = meta.get("status", "draft")

        if current_status != "ready":
            return SkillResult(
                success=False,
                message=(
                    f"Article status is '{current_status}', not 'ready'. "
                    f"Update status to 'ready' before publishing."
                ),
                data={"current_status": current_status},
            )

        # --- Run adapters ---
        attempted_at = _now_iso()
        records: list[ChannelPublishRecord] = []
        changed_files: list[Path] = []

        for channel in channels:
            adapter = self._adapters[channel]
            record = adapter.publish(article, params)
            records.append(record)

        # --- Determine overall success ---
        successful = [r for r in records if r.status in ("success", "draft_saved")]
        any_success = len(successful) > 0

        if any_success:
            # Update index.md: status=published + published_at timestamp
            published_at = _now_iso()
            meta["status"] = "published"
            meta["published_at"] = published_at
            new_index_content = dump_frontmatter(meta, body)
            index_path.write_text(new_index_content, encoding="utf-8")
            changed_files.append(index_path)

            # Refresh article.l2 so update_layers uses the new content
            article.l2 = new_index_content

            # Regenerate .abstract and .overview
            layer_files = self._article_manager.update_layers(article)
            changed_files.extend(layer_files)

            # Re-read the article to get updated l1 for timeline
            updated_result = self._article_manager.read_by_id(target)
            updated_article = updated_result.article

            # Update timeline index
            self._index_manager.update_timeline(updated_article)
            timeline_path = self._workspace_root / "_index" / "timeline.json"
            changed_files.append(timeline_path)

        # --- Always record publish history ---
        history_path = self._history_manager.record(
            session_id=session_id,
            canonical_id=target,
            attempted_at=attempted_at,
            records=records,
        )
        changed_files.append(history_path)

        # --- Build result ---
        channel_summaries = [
            {"channel": r.channel, "status": r.status, "error": r.error}
            for r in records
        ]

        if any_success:
            success_channels = [r.channel for r in successful]
            return SkillResult(
                success=True,
                message=f"Published '{target}' to: {success_channels}",
                data={
                    "canonical_id": target,
                    "channels": channel_summaries,
                    "published_at": meta.get("published_at"),
                },
                changed_files=changed_files,
            )
        else:
            failed_details = [
                f"{r.channel}: {r.error}" for r in records if r.error
            ]
            return SkillResult(
                success=False,
                message=f"All channels failed for '{target}'. Errors: {failed_details}",
                data={
                    "canonical_id": target,
                    "channels": channel_summaries,
                },
                changed_files=changed_files,
            )

    # ------------------------------------------------------------------
    # Batch publish
    # ------------------------------------------------------------------

    def _execute_all(self, params: dict) -> SkillResult:
        """Publish all articles with status=ready."""
        articles = self._article_manager.list_all()
        ready = []
        for a in articles:
            index_path = a.path / "index.md"
            try:
                raw = index_path.read_text(encoding="utf-8")
                meta, _ = parse_frontmatter(raw)
                if meta.get("status") == "ready":
                    ready.append(a.canonical_id)
            except Exception:
                continue

        if not ready:
            return SkillResult(
                success=True,
                message="No articles with status=ready found.",
                data={"published": [], "failed": []},
            )

        published, failed = [], []
        all_changed: list[Path] = []

        for canonical_id in ready:
            result = self.execute(canonical_id, {k: v for k, v in params.items() if k != "all"})
            if result.success:
                published.append(canonical_id)
            else:
                failed.append({"canonical_id": canonical_id, "error": result.message})
            if result.changed_files:
                all_changed.extend(result.changed_files)

        msg = f"Batch publish: {len(published)} published, {len(failed)} failed."
        return SkillResult(
            success=len(published) > 0,
            message=msg,
            data={"published": published, "failed": failed},
            changed_files=all_changed,
        )
