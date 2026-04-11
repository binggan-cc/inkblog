from __future__ import annotations

import re

from hypothesis import given, settings
from hypothesis import strategies as st

from ink_core.conversation.normalizer import ConversationNormalizer


def test_normalizes_json_dict_and_role_mapping() -> None:
    normalizer = ConversationNormalizer()
    conversation = normalizer.normalize(
        {
            "created_at": "2026-04-11T10:30:00",
            "messages": [{"author": "human", "text": "hello"}, {"sender": "AI", "body": ""}],
        },
        "json",
        "OpenClaw",
        "_node/conversations/raw/openclaw/a.json",
        "c" * 64,
    )
    assert conversation.conversation_id.startswith("2026/04/11-openclaw-")
    assert [m.role for m in conversation.messages] == ["user", "assistant"]
    assert conversation.messages[1].content == ""


def test_normalizes_jsonl_and_text() -> None:
    normalizer = ConversationNormalizer()
    jsonl = normalizer.normalize(
        [{"role": "system", "content": "setup"}],
        "jsonl",
        "test",
        "_node/conversations/raw/test/a.jsonl",
        "d" * 64,
    )
    text = normalizer.normalize(
        "User: hello\nAssistant: world",
        "text",
        "test",
        "_node/conversations/raw/test/a.txt",
        "e" * 64,
    )
    assert jsonl.messages[0].role == "system"
    assert [m.role for m in text.messages] == ["user", "assistant"]


@given(content=st.text(min_size=1, max_size=80))
@settings(max_examples=100)
def test_normalize_output_is_valid(content: str) -> None:
    # Feature: ink-node-conversation, Property 2
    conversation = ConversationNormalizer().normalize(
        content,
        "text",
        "source",
        "_node/conversations/raw/source/a.txt",
        "f" * 64,
    )
    assert re.match(r"^\d{4}/\d{2}/\d{2}-.+-.+$", conversation.conversation_id)
    assert conversation.participants
    assert all(message.role is not None and message.content is not None for message in conversation.messages)
    assert conversation.status in {"imported", "archived"}


@given(content=st.text(min_size=1, max_size=80))
@settings(max_examples=100)
def test_normalize_is_deterministic(content: str) -> None:
    # Feature: ink-node-conversation, Property 3
    normalizer = ConversationNormalizer()
    kwargs = {
        "raw_data": content,
        "source_format": "text",
        "source": "source",
        "source_file": "_node/conversations/raw/source/a.txt",
        "source_fingerprint": "a" * 64,
        "imported_at": "2026-04-11T00:00:00",
    }
    assert normalizer.normalize(**kwargs).to_dict() == normalizer.normalize(**kwargs).to_dict()
