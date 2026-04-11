from __future__ import annotations

from hypothesis import given, settings

from ink_core.conversation.models import Conversation, ConversationStatus, Message

from .conftest import conversation_strategy


def test_conversation_status_validation() -> None:
    assert ConversationStatus.is_valid("imported")
    assert ConversationStatus.is_valid("archived")
    assert not ConversationStatus.is_valid("published")


def test_message_and_conversation_creation() -> None:
    message = Message(role="user", content="hello")
    conversation = Conversation(
        conversation_id="2026/04/11-openclaw-hello",
        source="openclaw",
        source_file="_node/conversations/raw/openclaw/hello.json",
        source_fingerprint="a" * 64,
        title="hello",
        created_at="2026-04-11T10:30:00",
        updated_at="2026-04-11T10:30:00",
        participants=["user"],
        messages=[message],
    )
    assert conversation.messages[0].content == "hello"


@given(conversation=conversation_strategy)
@settings(max_examples=100)
def test_conversation_serialization_round_trip(conversation: Conversation) -> None:
    # Feature: ink-node-conversation, Property 1
    assert Conversation.from_dict(conversation.to_dict()) == conversation
