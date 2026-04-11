"""Render Conversation objects to static HTML."""

from __future__ import annotations

from pathlib import Path

import jinja2
from markupsafe import Markup

from ink_core.conversation.models import Conversation
from ink_core.fs.markdown_renderer import render_markdown


_DEFAULT_TEMPLATE = """\
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }} - {{ site_title }}</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.7; max-width: 900px; margin: 0 auto; padding: 32px 18px; color: #222; background: #f7f7f7; }
    a { color: #1f6feb; }
    header { border-bottom: 1px solid #ddd; margin-bottom: 24px; padding-bottom: 16px; }
    h1 { font-size: 32px; margin: 0 0 8px; }
    .meta { color: #666; display: flex; flex-wrap: wrap; gap: 12px; font-size: 14px; }
    .message { border-radius: 8px; margin: 18px 0; padding: 16px; background: #fff; border-left: 4px solid #777; }
    .message-user { border-left-color: #1f6feb; }
    .message-assistant { border-left-color: #238636; }
    .message-system { border-left-color: #9a6700; }
    .role { color: #444; font-weight: 700; margin-bottom: 8px; }
    .time { color: #777; font-weight: 400; margin-left: 8px; }
    pre { background: #1f2328; color: #f6f8fa; overflow-x: auto; padding: 12px; border-radius: 8px; }
    code { background: #eaeef2; padding: 1px 4px; border-radius: 4px; }
    pre code { background: transparent; padding: 0; }
  </style>
</head>
<body>
  <nav><a href="../../../../index.html">Back to home</a></nav>
  <header>
    <h1>{{ title }}</h1>
    <div class="meta">
      <span>{{ created_at }}</span>
      <span>{{ source }}</span>
      <span>{{ message_count }} messages</span>
      <span>{{ participants | join(", ") }}</span>
    </div>
  </header>
  <main>
  {% for msg in messages %}
    <article class="message message-{{ msg.role }}">
      <div class="role">{{ msg.role_display }}{% if msg.timestamp %}<span class="time">{{ msg.timestamp }}</span>{% endif %}</div>
      <div class="content">{{ msg.content_html }}</div>
    </article>
  {% endfor %}
  </main>
</body>
</html>
"""


class ConversationHtmlRenderer:
    """Conversation -> HTML renderer."""

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root

    def render(self, conversation: Conversation, site_title: str = "Blog") -> str:
        """Render a conversation to an HTML string."""
        messages = []
        for message in conversation.messages:
            messages.append({
                "role": message.role or "unknown",
                "role_display": self._role_display(message.role),
                "timestamp": message.timestamp or "",
                "content_html": Markup(render_markdown(message.content, safe=True)),
            })
        return self._render_template({
            "title": conversation.title,
            "site_title": site_title,
            "source": conversation.source,
            "created_at": conversation.created_at,
            "participants": conversation.participants,
            "message_count": len(conversation.messages),
            "conversation_id": conversation.conversation_id,
            "messages": messages,
        })

    def render_to_file(self, conversation: Conversation, output_path: Path, site_title: str = "Blog") -> None:
        """Render and write a conversation HTML file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.render(conversation, site_title=site_title), encoding="utf-8")

    def _render_template(self, context: dict) -> str:
        template_dir = self._workspace_root / "_templates" / "site"
        template_path = template_dir / "conversation.html"
        if template_path.exists():
            env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(template_dir)),
                autoescape=True,
            )
            template = env.get_template("conversation.html")
        else:
            env = jinja2.Environment(loader=jinja2.BaseLoader(), autoescape=True)
            template = env.from_string(_DEFAULT_TEMPLATE)
        return template.render(**context)

    def _role_display(self, role: str) -> str:
        return {
            "user": "User",
            "assistant": "Assistant",
            "system": "System",
        }.get(role, role.capitalize() if role else "Unknown")
