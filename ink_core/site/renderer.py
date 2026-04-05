"""Jinja2 template renderer for static site generation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import jinja2

if TYPE_CHECKING:
    from ink_core.fs.article import Article

# ---------------------------------------------------------------------------
# Built-in default templates (fallback when _templates/site/ is absent)
# ---------------------------------------------------------------------------

_DEFAULT_ARTICLE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ title }}</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; color: #222; }
    header { border-bottom: 1px solid #eee; padding-bottom: 1rem; margin-bottom: 2rem; }
    .meta { color: #666; font-size: 0.9rem; }
    .tags span { background: #f0f0f0; border-radius: 3px; padding: 2px 8px; margin-right: 4px; font-size: 0.85rem; }
    .abstract { background: #f9f9f9; border-left: 3px solid #ccc; padding: 0.75rem 1rem; margin: 1.5rem 0; font-style: italic; }
    article { margin-top: 2rem; }
    a { color: #0066cc; }
    nav { margin-top: 3rem; border-top: 1px solid #eee; padding-top: 1rem; }
  </style>
</head>
<body>
  <header>
    <h1>{{ title }}</h1>
    <p class="meta">
      {{ date }}
      {% if tags %} &middot; <span class="tags">{% for t in tags %}<span>{{ t }}</span>{% endfor %}</span>{% endif %}
    </p>
    {% if abstract %}<div class="abstract">{{ abstract }}</div>{% endif %}
  </header>
  <article>
    {{ body_html }}
  </article>
  <nav><a href="/">← Back to index</a></nav>
</body>
</html>
"""

_DEFAULT_INDEX_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ site_title }}</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; color: #222; }
    h1 { border-bottom: 1px solid #eee; padding-bottom: 0.5rem; }
    ul { list-style: none; padding: 0; }
    li { margin: 1.2rem 0; }
    .date { color: #666; font-size: 0.85rem; margin-right: 0.5rem; }
    .abstract { color: #555; font-size: 0.9rem; margin-top: 0.25rem; }
    .tags span { background: #f0f0f0; border-radius: 3px; padding: 1px 6px; margin-right: 3px; font-size: 0.8rem; }
    a { color: #0066cc; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .feed-link { float: right; font-size: 0.85rem; color: #888; }
  </style>
</head>
<body>
  <h1>{{ site_title }} <a class="feed-link" href="/feed.xml">RSS</a></h1>
  <ul>
    {% for article in articles %}
    <li>
      <span class="date">{{ article.date }}</span>
      <a href="/{{ article.canonical_id }}/">{{ article.title }}</a>
      {% if article.tags %}<span class="tags">{% for t in article.tags %}<span>{{ t }}</span>{% endfor %}</span>{% endif %}
      {% if article.abstract %}<div class="abstract">{{ article.abstract }}</div>{% endif %}
    </li>
    {% endfor %}
  </ul>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# TemplateRenderer
# ---------------------------------------------------------------------------

class TemplateRenderer:
    """Jinja2 template renderer.

    Priority:
    1. User templates in ``_templates/site/`` (article.html, index.html)
    2. Built-in default templates (Python string constants above)
    """

    TEMPLATE_DIR = "_templates/site"
    ARTICLE_TEMPLATE_NAME = "article.html"
    INDEX_TEMPLATE_NAME = "index.html"

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root
        self._env: jinja2.Environment | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render_article(self, article: "Article", output_path: Path) -> None:
        """Render a single article page to output_path."""
        from ink_core.fs.markdown import parse_frontmatter

        meta, body = parse_frontmatter(article.l2)
        title = meta.get("title", article.slug)
        date = article.date
        tags = meta.get("tags") or []
        abstract = article.l0 or ""

        # Convert Markdown body to simple HTML (no external dep — basic conversion)
        body_html = _md_to_html(body)

        ctx = {
            "title": title,
            "date": date,
            "tags": tags,
            "abstract": abstract,
            "body_html": body_html,
            "canonical_id": article.canonical_id,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        html = self._render(self.ARTICLE_TEMPLATE_NAME, _DEFAULT_ARTICLE_TEMPLATE, ctx)
        output_path.write_text(html, encoding="utf-8")

    def render_index(self, articles: list["Article"], output_path: Path, site_title: str = "Blog") -> None:
        """Render the site index page to output_path."""
        from ink_core.fs.markdown import parse_frontmatter

        article_ctx = []
        for a in articles:
            meta, _ = parse_frontmatter(a.l2)
            article_ctx.append({
                "canonical_id": a.canonical_id,
                "title": meta.get("title", a.slug),
                "date": a.date,
                "tags": meta.get("tags") or [],
                "abstract": a.l0 or "",
            })

        ctx = {"site_title": site_title, "articles": article_ctx}
        output_path.parent.mkdir(parents=True, exist_ok=True)
        html = self._render(self.INDEX_TEMPLATE_NAME, _DEFAULT_INDEX_TEMPLATE, ctx)
        output_path.write_text(html, encoding="utf-8")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _render(self, template_name: str, default_src: str, ctx: dict) -> str:
        """Render using user template if available, else fall back to default."""
        user_template_path = self._workspace_root / self.TEMPLATE_DIR / template_name
        if user_template_path.exists():
            env = self._get_fs_env()
            tmpl = env.get_template(template_name)
        else:
            env = jinja2.Environment(loader=jinja2.BaseLoader(), autoescape=True)
            tmpl = env.from_string(default_src)
        return tmpl.render(**ctx)

    def _get_fs_env(self) -> jinja2.Environment:
        """Return a Jinja2 Environment backed by the user template directory."""
        if self._env is None:
            template_dir = str(self._workspace_root / self.TEMPLATE_DIR)
            self._env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(template_dir),
                autoescape=True,
            )
        return self._env


# ---------------------------------------------------------------------------
# Minimal Markdown → HTML converter (no external deps)
# ---------------------------------------------------------------------------

def _md_to_html(md: str) -> str:
    """Convert a subset of Markdown to HTML.

    Handles: headings, bold, italic, code blocks, inline code,
    unordered lists, paragraphs, horizontal rules, links, images.
    This is intentionally minimal — users can override with Jinja2 templates
    that call a proper Markdown library if needed.
    """
    import re

    lines = md.split("\n")
    html_lines: list[str] = []
    in_code_block = False
    in_list = False

    for line in lines:
        # Fenced code blocks
        if line.startswith("```"):
            if in_code_block:
                html_lines.append("</code></pre>")
                in_code_block = False
            else:
                lang = line[3:].strip()
                cls = f' class="language-{lang}"' if lang else ""
                html_lines.append(f"<pre><code{cls}>")
                in_code_block = True
            continue

        if in_code_block:
            html_lines.append(_escape(line))
            continue

        # Close list if needed
        if in_list and not line.startswith("- ") and not line.startswith("* "):
            html_lines.append("</ul>")
            in_list = False

        # Headings
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            level = len(m.group(1))
            text = _inline(m.group(2))
            html_lines.append(f"<h{level}>{text}</h{level}>")
            continue

        # Horizontal rule
        if re.match(r"^[-*_]{3,}\s*$", line):
            html_lines.append("<hr>")
            continue

        # Unordered list
        if line.startswith("- ") or line.startswith("* "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{_inline(line[2:])}</li>")
            continue

        # Blank line → paragraph break
        if not line.strip():
            html_lines.append("")
            continue

        # Regular paragraph line
        html_lines.append(f"<p>{_inline(line)}</p>")

    if in_list:
        html_lines.append("</ul>")
    if in_code_block:
        html_lines.append("</code></pre>")

    return "\n".join(html_lines)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline(text: str) -> str:
    """Apply inline Markdown formatting."""
    import re

    # Inline code
    text = re.sub(r"`([^`]+)`", lambda m: f"<code>{_escape(m.group(1))}</code>", text)
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
    # Italic
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"_(.+?)_", r"<em>\1</em>", text)
    # Images (before links)
    text = re.sub(r"!\[([^\]]*)\]\(([^\)]+)\)", r'<img src="\2" alt="\1">', text)
    # Links
    text = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", r'<a href="\2">\1</a>', text)
    # Wiki links — render as plain text
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    return text
