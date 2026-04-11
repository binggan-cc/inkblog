from __future__ import annotations

from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ink_core.conversation.manager import ConversationManager
from ink_core.conversation.markdown_renderer import ConversationMarkdownRenderer
from ink_core.conversation.models import Conversation, Message
from ink_core.fs.article import ArticleManager
from ink_core.skills.search import SearchSkill


def _save_conversation(workspace: Path, conversation_id: str, content: str, created_at: str = "2026-04-11T10:30:00") -> None:
    conversation = Conversation(
        conversation_id=conversation_id,
        source="openclaw",
        source_file="_node/conversations/raw/openclaw/source.json",
        source_fingerprint=conversation_id.encode("utf-8").hex()[:64].ljust(64, "a"),
        title=conversation_id.rsplit("-", 1)[-1],
        created_at=created_at,
        updated_at=created_at,
        participants=["user"],
        messages=[Message(role="user", content=content)],
    )
    manager = ConversationManager(workspace)
    conv_dir = manager.save(conversation)
    manager.update_index(conversation)
    (conv_dir / "index.md").write_text(ConversationMarkdownRenderer().render(conversation), encoding="utf-8")


def test_search_type_conversation_all_and_default_isolation(workspace: Path) -> None:
    ArticleManager(workspace).create("Needle Article", date="2026-04-12", slug="needle", tags=["needle"])
    _save_conversation(workspace, "2026/04/11-openclaw-needle", "needle in conversation")
    skill = SearchSkill(workspace)

    default = skill.execute("needle", {})
    assert default.success
    assert default.data["results"]
    assert all("conversation_id" not in hit for hit in default.data["results"])

    conversations = skill.execute("needle", {"type": "conversation"})
    assert conversations.success
    assert conversations.data["results"]
    assert all(hit["content_type"] == "conversation" for hit in conversations.data["results"])

    all_results = skill.execute("needle", {"type": "all"})
    assert all_results.success
    assert {hit["content_type"] for hit in all_results.data["results"]} == {"article", "conversation"}

    empty = skill.execute("missing", {"type": "conversation"})
    assert empty.success
    assert empty.data["suggestions"]


@given(query=st.sampled_from(["alpha", "beta", "gamma"]))
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_search_type_isolation_property(workspace: Path, query: str) -> None:
    # Feature: ink-node-conversation, Property 13
    ArticleManager(workspace).create(f"{query} Article", date="2026-04-12", slug=f"{query}-article")
    _save_conversation(workspace, f"2026/04/11-openclaw-{query}", f"{query} conversation")
    skill = SearchSkill(workspace)
    assert all("conversation_id" not in hit for hit in skill.execute(query, {}).data["results"])
    assert all(hit["content_type"] == "conversation" for hit in skill.execute(query, {"type": "conversation"}).data["results"])
    assert all("content_type" in hit for hit in skill.execute(query, {"type": "all"}).data["results"])


def test_conversation_search_sorting() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        workspace = Path(td)
        _save_conversation(workspace, "2026/04/10-openclaw-old", "needle needle", "2026-04-10T10:00:00")
        _save_conversation(workspace, "2026/04/11-openclaw-new", "needle needle", "2026-04-11T10:00:00")
        _save_conversation(workspace, "2026/04/12-openclaw-many", "needle needle needle", "2026-04-12T10:00:00")
        results = SearchSkill(workspace).execute("needle", {"type": "conversation"}).data["results"]
        assert [hit["conversation_id"] for hit in results] == [
            "2026/04/12-openclaw-many",
            "2026/04/11-openclaw-new",
            "2026/04/10-openclaw-old",
        ]


@given(extra=st.integers(min_value=0, max_value=3))
@settings(max_examples=100)
def test_conversation_search_sorting_property(extra: int) -> None:
    # Feature: ink-node-conversation, Property 14
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        workspace = Path(td)
        _save_conversation(workspace, "2026/04/10-openclaw-a", "needle " * (1 + extra), "2026-04-10T10:00:00")
        _save_conversation(workspace, "2026/04/11-openclaw-b", "needle " * (1 + extra), "2026-04-11T10:00:00")
        results = SearchSkill(workspace).execute("needle", {"type": "conversation"}).data["results"]
        keys = [(hit["hit_count"], hit["created_at"]) for hit in results]
        assert keys == sorted(keys, reverse=True)
