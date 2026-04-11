from __future__ import annotations

from pathlib import Path

from hypothesis import HealthCheck, given, settings

from ink_core.conversation.manager import ConversationManager
from ink_core.conversation.models import Conversation, Message
from ink_core.core.errors import ConversationNotFoundError
from ink_core.fs.article import ArticleManager
from ink_core.fs.markdown import dump_frontmatter, parse_frontmatter

from .conftest import conversation_id_strategy, conversation_strategy


def _conversation(conversation_id: str = "2026/04/11-openclaw-architecture") -> Conversation:
    return Conversation(
        conversation_id=conversation_id,
        source="openclaw",
        source_file="_node/conversations/raw/openclaw/source.json",
        source_fingerprint="b" * 64,
        title="Architecture",
        created_at="2026-04-11T10:30:00",
        updated_at="2026-04-11T10:31:00",
        participants=["user", "assistant"],
        messages=[Message(role="user", content="hello")],
    )


def test_ensure_dirs_save_read_and_list_all(workspace: Path) -> None:
    manager = ConversationManager(workspace)
    manager.ensure_dirs()
    assert (workspace / "_node/conversations/raw").exists()
    assert (workspace / "_node/conversations/normalized").exists()

    conversation = _conversation()
    manager.save(conversation)
    manager.update_index(conversation)
    assert manager.read(conversation.conversation_id) == conversation
    assert manager.list_all()[0]["conversation_id"] == conversation.conversation_id
    assert manager.list_all(source="openclaw")[0]["source"] == "openclaw"
    assert manager.fingerprint_exists("b" * 64) == conversation.conversation_id


def test_read_missing_raises_conversation_error(workspace: Path) -> None:
    manager = ConversationManager(workspace)
    try:
        manager.read("2026/04/11-openclaw-missing")
    except ConversationNotFoundError as exc:
        assert "Conversation not found" in str(exc)
    else:
        raise AssertionError("ConversationNotFoundError was not raised")


def test_rebuild_index_restores_article_links(workspace: Path) -> None:
    manager = ConversationManager(workspace)
    conversation = _conversation()
    manager.save(conversation)
    article = ArticleManager(workspace).create("Linked Article", date="2026-04-12", slug="linked")
    index_path = article.path / "index.md"
    meta, body = parse_frontmatter(index_path.read_text(encoding="utf-8"))
    meta["source_conversations"] = [conversation.conversation_id]
    index_path.write_text(dump_frontmatter(meta, body), encoding="utf-8")

    entries = manager._rebuild_index()
    assert entries[0]["linked_articles"] == [article.canonical_id]


@given(conversation_id=conversation_id_strategy)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_resolve_path_maps_conversation_id(workspace: Path, conversation_id: str) -> None:
    # Feature: ink-node-conversation, Property 4
    path = ConversationManager(workspace).resolve_path(conversation_id)
    assert path == workspace / "_node" / "conversations" / "normalized" / Path(conversation_id)


@given(conversation=conversation_strategy)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_save_read_round_trip(workspace: Path, conversation: Conversation) -> None:
    # Feature: ink-node-conversation, Property 10
    manager = ConversationManager(workspace)
    manager.save(conversation)
    assert manager.read(conversation.conversation_id) == conversation


@given(conversation=conversation_strategy)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_source_filter_only_returns_matching_source(workspace: Path, conversation: Conversation) -> None:
    # Feature: ink-node-conversation, Property 11
    manager = ConversationManager(workspace)
    manager.save(conversation)
    manager.update_index(conversation)
    assert all(entry["source"] == conversation.source for entry in manager.list_all(source=conversation.source))
