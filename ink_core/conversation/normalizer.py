"""Normalize JSON, JSONL, and plain text caches into Conversation objects."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from ink_core.conversation.models import Conversation, ConversationStatus, Message
from ink_core.fs.article import SlugResolver


class ConversationNormalizer:
    """Convert parsed source data to canonical Conversation objects."""

    def normalize(
        self,
        raw_data: list | dict | str,
        source_format: str,
        source: str,
        source_file: str,
        source_fingerprint: str,
        title: str | None = None,
        imported_at: str | None = None,
    ) -> Conversation:
        """Normalize parsed source data."""
        if source_format == "json":
            messages, meta = self._normalize_json(raw_data)
        elif source_format == "jsonl":
            messages, meta = self._normalize_jsonl(raw_data)
        elif source_format == "text":
            messages, meta = self._normalize_text(str(raw_data))
        else:
            messages, meta = [], {}

        fallback_time = imported_at or datetime.now().replace(microsecond=0).isoformat()
        created_at = str(meta.get("created_at") or self._first_timestamp(messages) or fallback_time)
        updated_at = str(meta.get("updated_at") or self._last_timestamp(messages) or created_at)
        participants = self._participants(messages, meta.get("participants"))
        title = title or str(meta.get("title") or self._extract_title(messages))
        source = self._normalize_source(source)
        session_slug = self._generate_session_slug(title)
        year, month, day = self._date_parts(created_at)
        conversation_id = f"{year}/{month}/{day}-{source}-{session_slug}"

        return Conversation(
            conversation_id=conversation_id,
            source=source,
            source_file=source_file,
            source_fingerprint=source_fingerprint,
            title=title,
            created_at=created_at,
            updated_at=updated_at,
            participants=participants,
            messages=messages,
            status=ConversationStatus.IMPORTED.value,
        )

    def _normalize_json(self, data: dict | list) -> tuple[list[Message], dict]:
        """Normalize JSON dict or list input."""
        meta: dict = {}
        if isinstance(data, dict):
            raw_messages = (
                data.get("messages")
                or data.get("conversation")
                or data.get("items")
                or []
            )
            meta = {
                "created_at": data.get("created_at") or data.get("create_time") or data.get("timestamp"),
                "updated_at": data.get("updated_at") or data.get("update_time") or data.get("modified_at"),
                "participants": data.get("participants"),
                "title": data.get("title"),
            }
            if isinstance(raw_messages, dict):
                raw_messages = [raw_messages]
            return self._messages_from_records(raw_messages), meta
        if isinstance(data, list):
            return self._messages_from_records(data), meta
        return [], meta

    def _normalize_jsonl(self, records: list) -> tuple[list[Message], dict]:
        """Normalize JSONL records."""
        return self._messages_from_records(records), {}

    def _normalize_text(self, text: str) -> tuple[list[Message], dict]:
        """Normalize plain text using role labels or blank-line blocks."""
        messages: list[Message] = []
        marker = re.compile(r"^(User|Assistant|System|Human|AI|Bot)\s*:\s*", re.IGNORECASE | re.MULTILINE)
        matches = list(marker.finditer(text))
        if matches:
            for index, match in enumerate(matches):
                start = match.end()
                end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
                messages.append(
                    Message(
                        role=self._map_role(match.group(1)),
                        content=text[start:end].strip(),
                    )
                )
            return messages, {}

        roles = ["user", "assistant"]
        blocks = [block.strip() for block in re.split(r"\n\s*\n", text.strip()) if block.strip()]
        for index, block in enumerate(blocks):
            messages.append(Message(role=roles[index % 2], content=block))
        return messages, {}

    def _normalize_message(self, data: dict) -> Message:
        """Normalize one message dictionary."""
        role = data.get("role") or data.get("author") or data.get("sender") or "unknown"
        content = data.get("content", data.get("text", data.get("body", "")))
        timestamp = data.get("timestamp") or data.get("created_at") or data.get("time")
        known = {"role", "author", "sender", "content", "text", "body", "timestamp", "created_at", "time"}
        metadata = {key: value for key, value in data.items() if key not in known}
        return Message(
            role=self._map_role(str(role)),
            content="" if content is None else str(content),
            timestamp=str(timestamp) if timestamp is not None else None,
            metadata=metadata,
        )

    def _map_role(self, role: str) -> str:
        """Map source role names to canonical role names."""
        normalized = role.strip().lower()
        mapping = {
            "user": "user",
            "human": "user",
            "assistant": "assistant",
            "ai": "assistant",
            "bot": "assistant",
            "system": "system",
        }
        return mapping.get(normalized, normalized or "unknown")

    def _extract_title(self, messages: list[Message]) -> str:
        """Use the first non-empty message as a short title."""
        for message in messages:
            content = " ".join(message.content.split())
            if content:
                return content[:50]
        return "Untitled Conversation"

    def _generate_session_slug(self, title: str) -> str:
        """Generate a stable session slug without checking article path conflicts."""
        slug = SlugResolver(Path(".")).generate_slug(title)
        if slug.startswith("post-"):
            slug = "session-" + slug.removeprefix("post-")
        if not slug:
            slug = "session-untitled"
        return slug[:40].strip("-") or "session-untitled"

    def _messages_from_records(self, records: object) -> list[Message]:
        if not isinstance(records, list):
            return []
        messages: list[Message] = []
        for record in records:
            if isinstance(record, dict):
                messages.append(self._normalize_message(record))
            else:
                messages.append(Message(role="unknown", content="" if record is None else str(record)))
        return messages

    def _participants(self, messages: list[Message], raw_participants: object) -> list[str]:
        if isinstance(raw_participants, list):
            participants = [str(item) for item in raw_participants if str(item)]
            if participants:
                return participants
        roles = list(dict.fromkeys(message.role for message in messages if message.role))
        return roles or ["user", "assistant"]

    def _first_timestamp(self, messages: list[Message]) -> str | None:
        for message in messages:
            if message.timestamp:
                return message.timestamp
        return None

    def _last_timestamp(self, messages: list[Message]) -> str | None:
        for message in reversed(messages):
            if message.timestamp:
                return message.timestamp
        return None

    def _date_parts(self, value: str) -> tuple[str, str, str]:
        match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", value)
        if match:
            return match.group(1), match.group(2), match.group(3)
        today = datetime.now().date().isoformat()
        year, month, day = today.split("-")
        return year, month, day

    def _normalize_source(self, source: str) -> str:
        source = re.sub(r"[^a-zA-Z0-9_-]+", "-", source.strip().lower()).strip("-")
        return source or "unknown"
