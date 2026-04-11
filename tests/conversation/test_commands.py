from __future__ import annotations

import json
from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ink_core.conversation.commands import (
    BuildConversationsCommand,
    ImportConversationCommand,
    LinkSourceCommand,
    RenderConversationCommand,
)
from ink_core.conversation.manager import ConversationManager
from ink_core.conversation.markdown_renderer import ConversationMarkdownRenderer
from ink_core.conversation.models import Conversation, Message
from ink_core.fs.article import ArticleManager
from ink_core.fs.markdown import parse_frontmatter


def _conversation(conversation_id: str = "2026/04/11-openclaw-source") -> Conversation:
    return Conversation(
        conversation_id=conversation_id,
        source="openclaw",
        source_file="_node/conversations/raw/openclaw/source.json",
        source_fingerprint="a" * 64,
        title="Source",
        created_at="2026-04-11T10:30:00",
        updated_at="2026-04-11T10:30:00",
        participants=["user", "assistant"],
        messages=[Message(role="user", content="source keyword")],
    )


def _save_conversation(workspace: Path, conversation: Conversation) -> None:
    manager = ConversationManager(workspace)
    conv_dir = manager.save(conversation)
    manager.update_index(conversation)
    (conv_dir / "index.md").write_text(ConversationMarkdownRenderer().render(conversation), encoding="utf-8")


def test_import_render_build_commands(workspace: Path, sample_json_file: Path) -> None:
    imported = ImportConversationCommand(workspace).run(str(sample_json_file), {"source": "openclaw"})
    assert imported.success
    conversation_id = imported.data["conversation_id"]

    rendered = RenderConversationCommand(workspace).run(conversation_id, {"preview": True})
    assert rendered.success
    conv_dir = ConversationManager(workspace).resolve_path(conversation_id)
    assert (conv_dir / "index.md").exists()
    assert (conv_dir / "preview.html").exists()
    assert not (conv_dir / "index.html").exists()

    built = BuildConversationsCommand(workspace).run(None, {})
    assert built.success
    assert built.data["page_count"] == 1
    assert list((workspace / "_site/conversations").rglob("index.html"))


def test_link_source_success_duplicate_and_missing(workspace: Path) -> None:
    conversation = _conversation()
    _save_conversation(workspace, conversation)
    article = ArticleManager(workspace).create("Article", date="2026-04-12", slug="article")
    command = LinkSourceCommand(workspace)

    result = command.run(article.canonical_id, {"conversation": conversation.conversation_id})
    assert result.success
    meta, _ = parse_frontmatter((article.path / "index.md").read_text(encoding="utf-8"))
    assert meta["source_conversations"] == [conversation.conversation_id]
    assert ConversationManager(workspace).list_all()[0]["linked_articles"] == [article.canonical_id]

    duplicate = command.run(article.canonical_id, {"conversation": conversation.conversation_id})
    assert duplicate.success
    meta, _ = parse_frontmatter((article.path / "index.md").read_text(encoding="utf-8"))
    assert meta["source_conversations"] == [conversation.conversation_id]

    missing_article = command.run("2026/04/12-missing", {"conversation": conversation.conversation_id})
    missing_conversation = command.run(article.canonical_id, {"conversation": "2026/04/11-openclaw-missing"})
    assert not missing_article.success
    assert not missing_conversation.success


@given(slug=st.from_regex(r"[a-z][a-z0-9-]{1,20}", fullmatch=True))
@settings(max_examples=100)
def test_link_source_property(slug: str) -> None:
    # Feature: ink-node-conversation, Property 12
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        workspace = Path(td)
        conversation = _conversation(f"2026/04/11-openclaw-{slug}")
        _save_conversation(workspace, conversation)
        article = ArticleManager(workspace).create(f"Article {slug}", date="2026-04-12", slug=f"article-{slug}")
        command = LinkSourceCommand(workspace)
        assert command.run(article.canonical_id, {"conversation": conversation.conversation_id}).success
        assert command.run(article.canonical_id, {"conversation": conversation.conversation_id}).success
        meta, _ = parse_frontmatter((article.path / "index.md").read_text(encoding="utf-8"))
        assert meta["source_conversations"].count(conversation.conversation_id) == 1
        entry = ConversationManager(workspace).list_all()[0]
        assert entry["linked_articles"].count(article.canonical_id) == 1


def test_build_conversations_does_not_modify_blog_outputs(workspace: Path) -> None:
    # Build isolation integration check.
    (workspace / "_site").mkdir()
    index = workspace / "_site" / "index.html"
    feed = workspace / "_site" / "feed.xml"
    index.write_text("home", encoding="utf-8")
    feed.write_text("feed", encoding="utf-8")
    conversation = _conversation()
    _save_conversation(workspace, conversation)

    result = BuildConversationsCommand(workspace).run(None, {})
    assert result.success
    assert index.read_text(encoding="utf-8") == "home"
    assert feed.read_text(encoding="utf-8") == "feed"


def test_build_failure_isolated(workspace: Path) -> None:
    good = _conversation("2026/04/11-openclaw-good")
    bad = _conversation("2026/04/11-openclaw-bad")
    _save_conversation(workspace, good)
    manager = ConversationManager(workspace)
    manager.save(bad)
    manager.update_index(bad)
    (manager.resolve_path(bad.conversation_id) / "meta.json").write_text("{bad json", encoding="utf-8")
    result = BuildConversationsCommand(workspace).run(None, {})
    assert not result.success
    assert result.data["page_count"] == 1
    assert result.data["errors"]
