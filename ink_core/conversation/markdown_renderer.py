"""Render Conversation objects to Markdown archives."""

from __future__ import annotations

import yaml

from ink_core.conversation.models import Conversation


class ConversationMarkdownRenderer:
    """Conversation -> index.md renderer."""

    def render(self, conversation: Conversation) -> str:
        """Render a conversation archive as Markdown."""
        frontmatter = {
            "title": conversation.title,
            "conversation_id": conversation.conversation_id,
            "source": conversation.source,
            "created_at": conversation.created_at,
            "participants": conversation.participants,
            "message_count": len(conversation.messages),
            "status": conversation.status,
        }
        yaml_text = yaml.dump(
            frontmatter,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )
        parts = [f"---\n{yaml_text}---\n", f"# {conversation.title}\n"]
        for message in conversation.messages:
            heading = self._role_display(message.role)
            if message.timestamp:
                heading = f"{heading} - {message.timestamp}"
            parts.append(f"### {heading}\n")
            parts.append(f"{message.content}\n")
        return "\n".join(parts)

    def _role_display(self, role: str) -> str:
        """Return a human-readable role label."""
        return {
            "user": "User",
            "assistant": "Assistant",
            "system": "System",
        }.get(role, role.capitalize() if role else "Unknown")
