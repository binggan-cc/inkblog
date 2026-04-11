"""Self-contained Markdown to safe HTML renderer."""

from __future__ import annotations

import html
import re


def render_markdown(md: str, *, safe: bool = True) -> str:
    """Render Markdown to HTML.

    When *safe* is True, raw HTML is escaped before it reaches templates.
    mistune is used when available; otherwise a small built-in renderer covers
    the subset already supported by Ink.
    """
    if _mistune_available():
        return _render_with_mistune(md, safe=safe)
    return _md_to_html_builtin(md, safe=safe)


def _mistune_available() -> bool:
    try:
        import mistune  # noqa: F401
    except ImportError:
        return False
    return True


def _render_with_mistune(md: str, *, safe: bool = True) -> str:
    import mistune

    renderer = mistune.HTMLRenderer(escape=safe)
    markdown = mistune.create_markdown(renderer=renderer, plugins=["table"])
    return markdown(md)


def _md_to_html_builtin(md: str, *, safe: bool = True) -> str:
    """Convert Markdown to HTML with id anchors on headings."""
    lines = md.split("\n")
    html_lines: list[str] = []
    in_code_block = False
    in_list = False
    in_ordered_list = False
    in_table = False
    table_rows: list[str] = []

    def flush_table() -> None:
        nonlocal in_table, table_rows
        if not table_rows:
            return
        out = ["<table>"]
        for i, row in enumerate(table_rows):
            cells = [c.strip() for c in row.strip("|").split("|")]
            if i == 0:
                out.append(
                    "<thead><tr>"
                    + "".join(f"<th>{_inline_safe(c, safe=safe)}</th>" for c in cells)
                    + "</tr></thead><tbody>"
                )
            elif i == 1 and all(re.match(r"^[-:]+$", c.strip()) for c in cells):
                continue
            else:
                out.append(
                    "<tr>"
                    + "".join(f"<td>{_inline_safe(c, safe=safe)}</td>" for c in cells)
                    + "</tr>"
                )
        out.append("</tbody></table>")
        html_lines.extend(out)
        table_rows = []
        in_table = False

    for line in lines:
        if line.startswith("```"):
            if in_code_block:
                html_lines.append("</code></pre>")
                in_code_block = False
            else:
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                if in_ordered_list:
                    html_lines.append("</ol>")
                    in_ordered_list = False
                lang = _escape(line[3:].strip()) if safe else line[3:].strip()
                cls = f' class="language-{lang}"' if lang else ""
                html_lines.append(f"<pre><code{cls}>")
                in_code_block = True
            continue

        if in_code_block:
            html_lines.append(_escape(line) if safe else line)
            continue

        if "|" in line and line.strip().startswith("|"):
            if not in_table:
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                if in_ordered_list:
                    html_lines.append("</ol>")
                    in_ordered_list = False
                in_table = True
            table_rows.append(line)
            continue
        if in_table:
            flush_table()

        if in_list and not (line.startswith("- ") or line.startswith("* ")):
            html_lines.append("</ul>")
            in_list = False
        if in_ordered_list and not re.match(r"^\d+\.\s", line):
            html_lines.append("</ol>")
            in_ordered_list = False

        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            slug = re.sub(r"[^\w\u4e00-\u9fff-]", "-", text.lower()).strip("-")
            html_lines.append(f'<h{level} id="{_escape(slug)}">{_inline_safe(text, safe=safe)}</h{level}>')
            continue

        if re.match(r"^[-*_]{3,}\s*$", line):
            html_lines.append("<hr>")
            continue

        if line.startswith("> "):
            html_lines.append(f"<blockquote><p>{_inline_safe(line[2:], safe=safe)}</p></blockquote>")
            continue

        m = re.match(r"^(\d+)\.\s+(.*)", line)
        if m:
            if not in_ordered_list:
                html_lines.append("<ol>")
                in_ordered_list = True
            html_lines.append(f"<li>{_inline_safe(m.group(2), safe=safe)}</li>")
            continue

        if line.startswith("- ") or line.startswith("* "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{_inline_safe(line[2:], safe=safe)}</li>")
            continue

        if not line.strip():
            html_lines.append("")
            continue

        html_lines.append(f"<p>{_inline_safe(line, safe=safe)}</p>")

    if in_list:
        html_lines.append("</ul>")
    if in_ordered_list:
        html_lines.append("</ol>")
    if in_code_block:
        html_lines.append("</code></pre>")
    if in_table:
        flush_table()

    return "\n".join(html_lines)


def _escape(text: str) -> str:
    return html.escape(text, quote=True)


def _sanitize_url(url: str) -> str:
    url = url.strip()
    if re.match(r"(?i)^\s*(javascript|data):", url):
        return "#"
    return _escape(url)


def _inline_safe(text: str, *, safe: bool = True) -> str:
    """Render inline Markdown after escaping raw HTML-sensitive characters."""
    if not safe:
        escaped = text
    else:
        escaped = _escape(text)

    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"__(.+?)__", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*(.+?)\*", r"<em>\1</em>", escaped)
    escaped = re.sub(r"_(.+?)_", r"<em>\1</em>", escaped)

    def image(match: re.Match[str]) -> str:
        alt = match.group(1)
        src = _sanitize_url(html.unescape(match.group(2))) if safe else match.group(2)
        return f'<img src="{src}" alt="{alt}">'

    def link(match: re.Match[str]) -> str:
        label = match.group(1)
        href = _sanitize_url(html.unescape(match.group(2))) if safe else match.group(2)
        return f'<a href="{href}">{label}</a>'

    escaped = re.sub(r"!\[([^\]]*)\]\(([^\)]+)\)", image, escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", link, escaped)
    escaped = re.sub(r"\[\[([^\]]+)\]\]", r"\1", escaped)
    return escaped
