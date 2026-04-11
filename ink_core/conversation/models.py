"""Conversation data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ConversationStatus(str, Enum):
    """Conversation lifecycle status."""

    IMPORTED = "imported"
    ARCHIVED = "archived"

    @classmethod
    def is_valid(cls, status: str) -> bool:
        """Return True when *status* is a known conversation status."""
        return status in {item.value for item in cls}


@dataclass
class Message:
    """A single conversation message."""

    role: str
    content: str
    timestamp: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Conversation:
    """Canonical conversation object persisted in meta.json."""

    conversation_id: str
    source: str
    source_file: str
    source_fingerprint: str
    title: str
    created_at: str
    updated_at: str
    participants: list[str]
    messages: list[Message]
    status: str = ConversationStatus.IMPORTED.value
    assets: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Lightweight field validation."""
        if not self.participants:
            raise ValueError("participants must be a non-empty list")
        if not ConversationStatus.is_valid(self.status):
            raise ValueError(f"invalid status: {self.status!r} (expected 'imported' or 'archived')")

    def to_dict(self) -> dict:
        """Serialize the conversation to a JSON-compatible dictionary."""
        return {
            "conversation_id": self.conversation_id,
            "source": self.source,
            "source_file": self.source_file,
            "source_fingerprint": self.source_fingerprint,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "participants": list(self.participants),
            "messages": [
                {
                    "role": message.role,
                    "content": message.content,
                    **({"timestamp": message.timestamp} if message.timestamp else {}),
                    **({"metadata": message.metadata} if message.metadata else {}),
                }
                for message in self.messages
            ],
            "status": self.status,
            "assets": list(self.assets),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Conversation":
        """Deserialize a conversation from a dictionary."""
        messages = [
            Message(
                role=str(message["role"]),
                content=str(message["content"]),
                timestamp=(
                    str(message["timestamp"])
                    if message.get("timestamp") is not None
                    else None
                ),
                metadata=dict(message.get("metadata", {})),
            )
            for message in data.get("messages", [])
        ]
        return cls(
            conversation_id=str(data["conversation_id"]),
            source=str(data["source"]),
            source_file=str(data["source_file"]),
            source_fingerprint=str(data["source_fingerprint"]),
            title=str(data["title"]),
            created_at=str(data["created_at"]),
            updated_at=str(data["updated_at"]),
            participants=[str(p) for p in data["participants"]],
            messages=messages,
            status=str(data.get("status", ConversationStatus.IMPORTED.value)),
            assets=[str(asset) for asset in data.get("assets", [])],
        )
