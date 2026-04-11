from __future__ import annotations

from pathlib import Path

from hypothesis import HealthCheck, given, settings

from ink_core.conversation.html_renderer import ConversationHtmlRenderer
from ink_core.conversation.models import Conversation, Message

from .conftest import conversation_strategy


def test_html_renderer_uses_custom_template(workspace: Path) -> None:
    template_dir = workspace / "_templates" / "site"
    template_dir.mkdir(parents=True)
    (template_dir / "conversation.html").write_text("custom {{ title }} {{ messages[0].content_html }}", encoding="utf-8")
    conversation = Conversation(
        conversation_id="2026/04/11-openclaw-template",
        source="openclaw",
        source_file="_node/conversations/raw/openclaw/a.json",
        source_fingerprint="a" * 64,
        title="Template",
        created_at="2026-04-11T10:30:00",
        updated_at="2026-04-11T10:30:00",
        participants=["user"],
        messages=[Message(role="user", content="hello")],
    )
    assert "custom Template" in ConversationHtmlRenderer(workspace).render(conversation)


def test_html_renderer_escapes_html_and_renders_code(workspace: Path) -> None:
    conversation = Conversation(
        conversation_id="2026/04/11-openclaw-xss",
        source="openclaw",
        source_file="_node/conversations/raw/openclaw/a.json",
        source_fingerprint="a" * 64,
        title="XSS",
        created_at="2026-04-11T10:30:00",
        updated_at="2026-04-11T10:30:00",
        participants=["user"],
        messages=[Message(role="user", content="<script>alert(1)</script>\n\n```python\nprint(1)\n```")],
    )
    html = ConversationHtmlRenderer(workspace).render(conversation)
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html
    assert "<pre><code" in html


@given(conversation=conversation_strategy)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_html_render_is_idempotent(workspace: Path, conversation: Conversation) -> None:
    # Feature: ink-node-conversation, Property 8
    renderer = ConversationHtmlRenderer(workspace)
    assert renderer.render(conversation) == renderer.render(conversation)


@given(payload=conversation_strategy)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_html_render_escapes_special_characters(workspace: Path, payload: Conversation) -> None:
    # Feature: ink-node-conversation, Property 9
    payload.messages = [Message(role="user", content="<img src=x onerror=alert(1)>")]
    html = ConversationHtmlRenderer(workspace).render(payload)
    assert "<img src=x" not in html
    assert "&lt;img" in html
