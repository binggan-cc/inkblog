from __future__ import annotations

from hypothesis import given, settings

from ink_core.conversation.markdown_renderer import ConversationMarkdownRenderer
from ink_core.conversation.models import Conversation, Message
from ink_core.fs.markdown import parse_frontmatter

from .conftest import conversation_strategy


def test_markdown_renderer_frontmatter_and_code_blocks() -> None:
    conversation = Conversation(
        conversation_id="2026/04/11-openclaw-code",
        source="openclaw",
        source_file="_node/conversations/raw/openclaw/code.json",
        source_fingerprint="a" * 64,
        title="Code",
        created_at="2026-04-11T10:30:00",
        updated_at="2026-04-11T10:31:00",
        participants=["user", "assistant"],
        messages=[Message(role="assistant", content="```python\nprint('x')\n```", timestamp="2026-04-11T10:31:00")],
    )
    rendered = ConversationMarkdownRenderer().render(conversation)
    meta, body = parse_frontmatter(rendered)
    assert meta["conversation_id"] == conversation.conversation_id
    assert meta["message_count"] == 1
    assert "```python" in body
    assert "Assistant - 2026-04-11T10:31:00" in body


@given(conversation=conversation_strategy)
@settings(max_examples=100)
def test_markdown_frontmatter_matches_conversation(conversation: Conversation) -> None:
    # Feature: ink-node-conversation, Property 7
    meta, _ = parse_frontmatter(ConversationMarkdownRenderer().render(conversation))
    assert meta["conversation_id"] == conversation.conversation_id
    assert meta["title"] == conversation.title
    assert meta["source"] == conversation.source
    assert meta["message_count"] == len(conversation.messages)


@given(conversation=conversation_strategy)
@settings(max_examples=100)
def test_markdown_render_is_idempotent(conversation: Conversation) -> None:
    # Feature: ink-node-conversation, Property 8
    renderer = ConversationMarkdownRenderer()
    assert renderer.render(conversation) == renderer.render(conversation)
