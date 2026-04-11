"""Conversation CRUD, path resolution, and index management."""

from __future__ import annotations

import json
from pathlib import Path

from ink_core.conversation.models import Conversation


class ConversationManager:
    """Manage conversations stored under _node/conversations."""

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root
        self._normalized_root = workspace_root / "_node" / "conversations" / "normalized"
        self._raw_root = workspace_root / "_node" / "conversations" / "raw"
        self._index_path = workspace_root / "_index" / "conversations.json"

    @property
    def normalized_root(self) -> Path:
        return self._normalized_root

    @property
    def raw_root(self) -> Path:
        return self._raw_root

    @property
    def index_path(self) -> Path:
        return self._index_path

    def ensure_dirs(self) -> None:
        """Create the conversation directory skeleton."""
        self._raw_root.mkdir(parents=True, exist_ok=True)
        self._normalized_root.mkdir(parents=True, exist_ok=True)

    def resolve_path(self, conversation_id: str) -> Path:
        """Resolve a Conversation_ID to its normalized conversation directory."""
        return self._normalized_root / Path(conversation_id)

    def save(self, conversation: Conversation) -> Path:
        """Persist *conversation* to meta.json and return its directory."""
        self.ensure_dirs()
        conv_dir = self.resolve_path(conversation.conversation_id)
        conv_dir.mkdir(parents=True, exist_ok=True)
        (conv_dir / "assets").mkdir(exist_ok=True)
        (conv_dir / "meta.json").write_text(
            json.dumps(conversation.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return conv_dir

    def read(self, conversation_id: str) -> Conversation:
        """Read a conversation by ID."""
        from ink_core.core.errors import ConversationNotFoundError

        meta_path = self.resolve_path(conversation_id) / "meta.json"
        if not meta_path.exists():
            available = [entry.get("conversation_id") for entry in self.list_all() if entry.get("conversation_id")]
            raise ConversationNotFoundError(
                f"Conversation not found: {conversation_id}. Available: {', '.join(available) or 'none'}"
            )
        return Conversation.from_dict(json.loads(meta_path.read_text(encoding="utf-8")))

    def list_all(self, *, source: str | None = None) -> list[dict]:
        """Return indexed conversation summaries, optionally filtered by source."""
        entries = self._read_index()
        if not entries and self._normalized_root.exists():
            entries = self._rebuild_index()
        if source is not None:
            entries = [entry for entry in entries if entry.get("source") == source]
        return entries

    def update_index(self, conversation: Conversation) -> None:
        """Upsert one conversation summary into _index/conversations.json."""
        entries = self._read_index()
        linked_articles: list[str] = []
        for entry in entries:
            if entry.get("conversation_id") == conversation.conversation_id:
                linked_articles = list(entry.get("linked_articles", []))
                break

        new_entry = self._summary_entry(conversation)
        new_entry["linked_articles"] = linked_articles
        entries = [
            entry for entry in entries
            if entry.get("conversation_id") != conversation.conversation_id
        ]
        entries.append(new_entry)
        entries.sort(key=lambda entry: entry.get("created_at", ""), reverse=True)
        self._write_index(entries)

    def fingerprint_exists(self, fingerprint: str) -> str | None:
        """Return the existing conversation ID for *fingerprint*, if present."""
        if not self._normalized_root.exists():
            return None
        for meta_path in sorted(self._normalized_root.glob("*/*/*/meta.json")):
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if data.get("source_fingerprint") == fingerprint:
                return str(data.get("conversation_id", ""))
        return None

    def update_linked_articles(self, conversation_id: str, article_id: str) -> None:
        """Add *article_id* to the indexed linked_articles for *conversation_id*."""
        conversation = self.read(conversation_id)
        entries = self._read_index()
        if not any(entry.get("conversation_id") == conversation_id for entry in entries):
            self.update_index(conversation)
            entries = self._read_index()

        for entry in entries:
            if entry.get("conversation_id") != conversation_id:
                continue
            linked = list(entry.get("linked_articles", []))
            if article_id not in linked:
                linked.append(article_id)
            entry["linked_articles"] = linked
            break
        self._write_index(entries)

    def _read_index(self) -> list[dict]:
        if not self._index_path.exists():
            return []
        raw = self._index_path.read_text(encoding="utf-8").strip()
        if not raw:
            return []
        data = json.loads(raw)
        return data if isinstance(data, list) else []

    def _write_index(self, entries: list[dict]) -> None:
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        self._index_path.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _rebuild_index(self) -> list[dict]:
        entries: list[dict] = []
        if self._normalized_root.exists():
            for meta_path in sorted(self._normalized_root.glob("*/*/*/meta.json")):
                try:
                    conversation = Conversation.from_dict(
                        json.loads(meta_path.read_text(encoding="utf-8"))
                    )
                except Exception:
                    continue
                entries.append(self._summary_entry(conversation))

        links = self._scan_article_source_links()
        for entry in entries:
            entry["linked_articles"] = links.get(entry["conversation_id"], [])
        entries.sort(key=lambda entry: entry.get("created_at", ""), reverse=True)
        self._write_index(entries)
        return entries

    def _scan_article_source_links(self) -> dict[str, list[str]]:
        """Return conversation_id -> article_id mappings from article frontmatter."""
        from ink_core.fs.article import ArticleManager
        from ink_core.fs.markdown import parse_frontmatter

        links: dict[str, list[str]] = {}
        try:
            articles = ArticleManager(self._workspace_root).list_all()
        except Exception:
            return links

        for article in articles:
            try:
                meta, _ = parse_frontmatter((article.path / "index.md").read_text(encoding="utf-8"))
            except Exception:
                continue
            values = meta.get("source_conversations", [])
            if isinstance(values, str):
                values = [values]
            if not isinstance(values, list):
                continue
            for conversation_id in values:
                if not isinstance(conversation_id, str):
                    continue
                linked = links.setdefault(conversation_id, [])
                if article.canonical_id not in linked:
                    linked.append(article.canonical_id)
        return links

    @staticmethod
    def _summary_entry(conversation: Conversation) -> dict:
        return {
            "conversation_id": conversation.conversation_id,
            "source": conversation.source,
            "title": conversation.title,
            "created_at": conversation.created_at,
            "message_count": len(conversation.messages),
            "status": conversation.status,
            "linked_articles": [],
        }
