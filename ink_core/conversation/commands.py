"""Built-in CLI commands for conversation processing."""

from __future__ import annotations

import time
from pathlib import Path

from ink_core.cli.builtin import BuiltinCommand
from ink_core.skills.base import SkillResult


class ImportConversationCommand(BuiltinCommand):
    """Import a local conversation cache file."""

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root

    @property
    def name(self) -> str:
        return "import-conversation"

    def run(self, target: str | None, params: dict) -> SkillResult:
        from ink_core.conversation.importer import ConversationImporter
        from ink_core.core.errors import (
            ConversationDuplicateImportError,
            ConversationFormatDetectionError,
            ConversationSourceNotFoundError,
        )

        if not target:
            return SkillResult(success=False, message="Conversation source file is required.")
        file_path = Path(target)
        if not file_path.is_absolute():
            file_path = self._workspace_root / file_path

        try:
            result = ConversationImporter(self._workspace_root).import_file(
                file_path,
                source=params.get("source", "unknown"),
                title=params.get("title"),
            )
        except (
            ConversationSourceNotFoundError,
            ConversationFormatDetectionError,
            ConversationDuplicateImportError,
        ) as exc:
            return SkillResult(
                success=False,
                message=str(exc),
                data={"error_type": type(exc).__name__},
            )

        conversation = result.conversation
        return SkillResult(
            success=True,
            message=(
                f"Imported conversation: {conversation.conversation_id} "
                f"({len(conversation.messages)} messages)"
            ),
            data={
                "conversation_id": conversation.conversation_id,
                "message_count": len(conversation.messages),
                "source": conversation.source,
                "path": str(result.conversation_dir),
            },
            changed_files=[
                result.conversation_dir / "meta.json",
                result.raw_path,
                result.index_path,
            ],
        )


class RenderConversationCommand(BuiltinCommand):
    """Render one conversation to index.md and optional preview.html."""

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root

    @property
    def name(self) -> str:
        return "render-conversation"

    def run(self, target: str | None, params: dict) -> SkillResult:
        from ink_core.conversation.html_renderer import ConversationHtmlRenderer
        from ink_core.conversation.manager import ConversationManager
        from ink_core.conversation.markdown_renderer import ConversationMarkdownRenderer
        from ink_core.core.errors import ConversationNotFoundError

        if not target:
            return SkillResult(success=False, message="Conversation ID is required.")
        manager = ConversationManager(self._workspace_root)
        try:
            conversation = manager.read(target)
        except ConversationNotFoundError as exc:
            return SkillResult(success=False, message=str(exc), data={"error_type": type(exc).__name__})

        conv_dir = manager.resolve_path(target)
        md_path = conv_dir / "index.md"
        md_path.write_text(ConversationMarkdownRenderer().render(conversation), encoding="utf-8")
        changed = [md_path]

        if params.get("preview"):
            preview_path = conv_dir / "preview.html"
            ConversationHtmlRenderer(self._workspace_root).render_to_file(conversation, preview_path)
            changed.append(preview_path)

        return SkillResult(
            success=True,
            message=f"Rendered conversation: {target}",
            data={"conversation_id": target, "preview": bool(params.get("preview"))},
            changed_files=changed,
        )


class BuildConversationsCommand(BuiltinCommand):
    """Build static HTML pages for all conversations."""

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root

    @property
    def name(self) -> str:
        return "build-conversations"

    def run(self, target: str | None, params: dict) -> SkillResult:
        from ink_core.conversation.html_renderer import ConversationHtmlRenderer
        from ink_core.conversation.manager import ConversationManager
        from ink_core.core.config import InkConfig

        start = time.monotonic()
        manager = ConversationManager(self._workspace_root)
        entries = manager.list_all()
        if not entries:
            return SkillResult(
                success=True,
                message="No conversations to build.",
                data={"page_count": 0, "duration_ms": 0, "errors": []},
                changed_files=[],
            )

        config = InkConfig(workspace_root=self._workspace_root)
        site_title = config.get("site.title", "Blog")
        renderer = ConversationHtmlRenderer(self._workspace_root)
        changed: list[Path] = []
        errors: list[str] = []
        page_count = 0

        for entry in entries:
            conversation_id = str(entry.get("conversation_id", ""))
            try:
                conversation = manager.read(conversation_id)
                output_path = self._output_path(conversation_id)
                renderer.render_to_file(conversation, output_path, site_title=site_title)
                changed.append(output_path)
                page_count += 1
            except Exception as exc:
                errors.append(f"{conversation_id}: {exc}")

        duration_ms = int((time.monotonic() - start) * 1000)
        message = f"Built {page_count} conversation page(s) in {duration_ms}ms"
        if errors:
            message += f" with {len(errors)} error(s)"

        return SkillResult(
            success=not errors,
            message=message,
            data={"page_count": page_count, "duration_ms": duration_ms, "errors": errors},
            changed_files=changed,
        )

    def _output_path(self, conversation_id: str) -> Path:
        parts = conversation_id.split("/")
        if len(parts) == 3:
            year, month, leaf = parts
            return self._workspace_root / "_site" / "conversations" / year / month / f"{year}-{month}-{leaf}" / "index.html"
        return self._workspace_root / "_site" / "conversations" / conversation_id / "index.html"


class LinkSourceCommand(BuiltinCommand):
    """Link an article to a source conversation."""

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root

    @property
    def name(self) -> str:
        return "link-source"

    def run(self, target: str | None, params: dict) -> SkillResult:
        from ink_core.conversation.manager import ConversationManager
        from ink_core.core.errors import ConversationNotFoundError, PathNotFoundError
        from ink_core.fs.article import ArticleManager
        from ink_core.fs.markdown import dump_frontmatter, parse_frontmatter

        article_id = target
        conversation_id = params.get("conversation")
        if not article_id:
            return SkillResult(success=False, message="Article ID is required.")
        if not conversation_id:
            return SkillResult(success=False, message="--conversation is required.")

        article_manager = ArticleManager(self._workspace_root)
        try:
            article = article_manager.read_by_id(article_id).article
        except PathNotFoundError as exc:
            return SkillResult(success=False, message=str(exc), data={"error_type": type(exc).__name__})

        conversation_manager = ConversationManager(self._workspace_root)
        try:
            conversation_manager.read(conversation_id)
        except ConversationNotFoundError as exc:
            return SkillResult(success=False, message=str(exc), data={"error_type": type(exc).__name__})

        index_path = article.path / "index.md"
        meta, body = parse_frontmatter(index_path.read_text(encoding="utf-8"))
        source_conversations = meta.get("source_conversations", [])
        if isinstance(source_conversations, str):
            source_conversations = [source_conversations]
        if not isinstance(source_conversations, list):
            source_conversations = []

        if conversation_id in source_conversations:
            return SkillResult(
                success=True,
                message=f"Already linked: {article_id} <- {conversation_id}",
                data={"article_id": article_id, "conversation_id": conversation_id, "already_linked": True},
                changed_files=[],
            )

        source_conversations.append(conversation_id)
        meta["source_conversations"] = source_conversations
        index_path.write_text(dump_frontmatter(meta, body), encoding="utf-8")
        conversation_manager.update_linked_articles(conversation_id, article_id)

        return SkillResult(
            success=True,
            message=f"Linked: {article_id} <- {conversation_id}",
            data={"article_id": article_id, "conversation_id": conversation_id},
            changed_files=[index_path, conversation_manager.index_path],
        )
