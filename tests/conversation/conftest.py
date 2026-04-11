from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import strategies as st

from ink_core.conversation.models import Conversation, Message


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "_index").mkdir()
    return tmp_path


@pytest.fixture
def sample_json_file(tmp_path: Path) -> Path:
    path = tmp_path / "conversation.json"
    path.write_text(
        json.dumps({
            "title": "Architecture chat",
            "created_at": "2026-04-11T10:30:00",
            "updated_at": "2026-04-11T10:31:00",
            "participants": ["user", "assistant"],
            "messages": [
                {"role": "user", "content": "Discuss InkBlog Node", "timestamp": "2026-04-11T10:30:00"},
                {"role": "assistant", "content": "Conversation pipeline details", "timestamp": "2026-04-11T10:31:00"},
            ],
        }),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def sample_jsonl_file(tmp_path: Path) -> Path:
    path = tmp_path / "conversation.jsonl"
    path.write_text(
        '{"role":"user","content":"hello"}\n{"role":"assistant","content":"world"}\n',
        encoding="utf-8",
    )
    return path


@pytest.fixture
def sample_text_file(tmp_path: Path) -> Path:
    path = tmp_path / "conversation.txt"
    path.write_text("User: hello\n\nAssistant: world\n", encoding="utf-8")
    return path


safe_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("Ll", "Lu", "Nd", "Lo", "Pc", "Pd", "Po", "Zs"),
        blacklist_characters="\x00",
    ),
    min_size=0,
    max_size=120,
)

safe_nonempty_text = safe_text.filter(lambda value: value.strip() != "")

message_strategy = st.builds(
    Message,
    role=st.sampled_from(["user", "assistant", "system", "unknown"]),
    content=safe_text,
    timestamp=st.one_of(st.none(), st.just("2026-04-11T10:30:00")),
    metadata=st.dictionaries(st.text(min_size=1, max_size=10), safe_text, max_size=3),
)

conversation_id_strategy = st.builds(
    lambda day, source, slug: f"2026/04/{day:02d}-{source}-{slug}",
    day=st.integers(min_value=1, max_value=28),
    source=st.from_regex(r"[a-z][a-z0-9-]{1,10}", fullmatch=True),
    slug=st.from_regex(r"[a-z0-9][a-z0-9-]{1,20}", fullmatch=True),
)

conversation_strategy = st.builds(
    Conversation,
    conversation_id=conversation_id_strategy,
    source=st.from_regex(r"[a-z][a-z0-9-]{1,10}", fullmatch=True),
    source_file=st.just("_node/conversations/raw/test/source.json"),
    source_fingerprint=st.from_regex(r"[0-9a-f]{64}", fullmatch=True),
    title=safe_nonempty_text,
    created_at=st.just("2026-04-11T10:30:00"),
    updated_at=st.just("2026-04-11T10:31:00"),
    participants=st.lists(st.sampled_from(["user", "assistant", "system"]), min_size=1, max_size=3, unique=True),
    messages=st.lists(message_strategy, min_size=0, max_size=10),
    status=st.sampled_from(["imported", "archived"]),
    assets=st.lists(st.text(min_size=1, max_size=20), max_size=3),
)


def write_conversation(workspace: Path, conversation: Conversation) -> None:
    from ink_core.conversation.manager import ConversationManager
    from ink_core.conversation.markdown_renderer import ConversationMarkdownRenderer

    manager = ConversationManager(workspace)
    conv_dir = manager.save(conversation)
    manager.update_index(conversation)
    (conv_dir / "index.md").write_text(
        ConversationMarkdownRenderer().render(conversation),
        encoding="utf-8",
    )
