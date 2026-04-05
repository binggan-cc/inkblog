"""Jinja2 template renderer for static site generation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import jinja2

if TYPE_CHECKING:
    from ink_core.fs.article import Article

# ---------------------------------------------------------------------------
# Built-in default templates
# ---------------------------------------------------------------------------

_DEFAULT_ARTICLE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - {{ site_title }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.8;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem 1rem;
            background: #fafafa;
        }
        nav { margin-bottom: 2rem; }
        nav a { color: #3498db; text-decoration: none; font-size: 0.9rem; }
        nav a:hover { text-decoration: underline; }
        .article-header {
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid #e0e0e0;
        }
        .article-header h1 {
            font-size: 2rem;
            color: #2c3e50;
            margin-bottom: 0.5rem;
            line-height: 1.3;
        }
        .article-meta {
            display: flex;
            gap: 1rem;
            align-items: center;
            flex-wrap: wrap;
            font-size: 0.85rem;
            color: #999;
        }
        .tag {
            background: #f0f4f8;
            color: #5a6c7d;
            padding: 0.2rem 0.6rem;
            border-radius: 12px;
            font-size: 0.8rem;
        }
        .content h1 { font-size: 1.8rem; margin: 2rem 0 1rem; color: #2c3e50; }
        .content h2 { font-size: 1.4rem; margin: 2rem 0 0.8rem; color: #2c3e50; padding-bottom: 0.3rem; border-bottom: 1px solid #eee; }
        .content h3 { font-size: 1.2rem; margin: 1.5rem 0 0.6rem; color: #34495e; }
        .content h4 { font-size: 1.05rem; margin: 1.2rem 0 0.5rem; color: #34495e; }
        .content p { margin-bottom: 1rem; }
        .content ul, .content ol { margin: 0.5rem 0 1rem 1.5rem; }
        .content li { margin-bottom: 0.3rem; }
        .content blockquote {
            border-left: 4px solid #3498db;
            padding: 0.5rem 1rem;
            margin: 1rem 0;
            background: #f8f9fa;
            color: #555;
            border-radius: 0 4px 4px 0;
        }
        .content pre {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 1rem;
            border-radius: 6px;
            overflow-x: auto;
            margin: 1rem 0;
            font-size: 0.9rem;
        }
        .content code {
            background: #f0f0f0;
            padding: 0.1rem 0.3rem;
            border-radius: 3px;
            font-size: 0.9em;
            font-family: "SF Mono", Monaco, Consolas, monospace;
        }
        .content pre code { background: none; padding: 0; color: inherit; }
        .content table { width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.9rem; }
        .content th, .content td { border: 1px solid #ddd; padding: 0.5rem 0.75rem; text-align: left; }
        .content th { background: #f5f5f5; font-weight: 600; }
        .content tr:nth-child(even) { background: #fafafa; }
        .content hr { border: none; border-top: 1px solid #e0e0e0; margin: 2rem 0; }
        .content a { color: #3498db; text-decoration: none; }
        .content a:hover { text-decoration: underline; }
        .content strong { font-weight: 600; }
        .content img { max-width: 100%; border-radius: 6px; margin: 0.5rem 0; }
        footer {
            text-align: center;
            padding: 3rem 0;
            color: #999;
            font-size: 0.9rem;
            border-top: 1px solid #e0e0e0;
            margin-top: 3rem;
        }
    </style>
</head>
<body>
    <nav><a href="../../../index.html">← 返回首页</a></nav>
    <div class="article-header">
        <h1>{{ title }}</h1>
        <div class="article-meta">
            <span>📅 {{ date }}</span>
            {% for t in tags %}<span class="tag">{{ t }}</span>{% endfor %}
        </div>
    </div>
    <div class="content">
        {{ body_html }}
    </div>
    <footer>
        <p>🍪 使用 Ink Blog Core 构建</p>
    </footer>
</body>
</html>
"""

_DEFAULT_INDEX_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ site_title }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.8;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem 1rem;
            background: #fafafa;
        }
        header {
            text-align: center;
            padding: 3rem 0;
            border-bottom: 2px solid #e0e0e0;
            margin-bottom: 2rem;
        }
        header h1 { font-size: 2.5rem; color: #2c3e50; margin-bottom: 0.5rem; }
        .subtitle { color: #666; font-size: 1.1rem; }
        .stats {
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin-top: 1rem;
            font-size: 0.9rem;
            color: #888;
        }
        .section-title {
            font-size: 1.5rem;
            color: #2c3e50;
            margin: 2rem 0 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #3498db;
        }
        article {
            background: white;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        article:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .article-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 0.5rem;
        }
        .article-title {
            font-size: 1.3rem;
            color: #2c3e50;
            text-decoration: none;
            font-weight: 600;
        }
        .article-title:hover { color: #3498db; }
        .article-date { font-size: 0.85rem; color: #999; white-space: nowrap; margin-left: 1rem; }
        .article-summary { color: #666; font-size: 0.95rem; margin-bottom: 0.75rem; line-height: 1.6; }
        .article-meta { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; font-size: 0.85rem; }
        .tag {
            background: #f0f4f8;
            color: #5a6c7d;
            padding: 0.2rem 0.6rem;
            border-radius: 12px;
            font-size: 0.8rem;
        }
        .word-count { color: #999; }
        .rss-link {
            display: inline-block;
            margin-top: 0.5rem;
            font-size: 0.85rem;
            color: #999;
            text-decoration: none;
            border: 1px solid #ddd;
            padding: 2px 10px;
            border-radius: 4px;
        }
        .rss-link:hover { border-color: #aaa; color: #555; }
        footer {
            text-align: center;
            padding: 3rem 0;
            color: #999;
            font-size: 0.9rem;
            border-top: 1px solid #e0e0e0;
            margin-top: 2rem;
        }
    </style>
</head>
<body>
    <header>
        <h1>{{ site_title }}</h1>
        <p class="subtitle">{{ site_subtitle }}</p>
        <div class="stats">
            <span>📚 {{ total_articles }} 篇文章</span>
            <span>📝 ~{{ total_words }} 字</span>
            {% if date_range %}<span>📅 {{ date_range }}</span>{% endif %}
        </div>
        <div style="margin-top:1rem"><a class="rss-link" href="./feed.xml">RSS 订阅</a></div>
    </header>

    <h2 class="section-title">最新文章</h2>

    {% for article in articles %}
    <article>
        <div class="article-header">
            <a href="./{{ article.canonical_id }}/index.html" class="article-title">{{ article.title }}</a>
            <span class="article-date">{{ article.date }}</span>
        </div>
        {% if article.abstract %}<p class="article-summary">{{ article.abstract }}</p>{% endif %}
        <div class="article-meta">
            {% for t in article.tags %}<span class="tag">{{ t }}</span>{% endfor %}
            {% if article.word_count %}<span class="word-count">~{{ article.word_count }} 字</span>{% endif %}
        </div>
    </article>
    {% endfor %}

    <footer>
        <p>🍪 使用 Ink Blog Core 构建</p>
        <p>© {{ year }} {{ site_author }}</p>
    </footer>
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

    def render_article(self, article: "Article", output_path: Path, site_title: str = "Blog") -> None:
        from ink_core.fs.markdown import parse_frontmatter

        meta, body = parse_frontmatter(article.l2)
        title = meta.get("title", article.slug)
        date = article.date
        tags = meta.get("tags") or []
        abstract = article.l0 or ""
        body_html = _md_to_html(body)
        toc = _extract_toc(body)

        ctx = {
            "title": title,
            "site_title": site_title,
            "date": date,
            "tags": tags,
            "abstract": abstract,
            "body_html": body_html,
            "toc": toc,
            "canonical_id": article.canonical_id,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Use autoescape=False so body_html renders as HTML, not escaped text
        html = self._render(self.ARTICLE_TEMPLATE_NAME, _DEFAULT_ARTICLE_TEMPLATE, ctx, autoescape=False)
        output_path.write_text(html, encoding="utf-8")

    def render_index(self, articles: list["Article"], output_path: Path, site_title: str = "Blog",
                     site_config: dict | None = None) -> None:
        from ink_core.fs.markdown import parse_frontmatter
        import datetime

        site_config = site_config or {}
        site_subtitle = site_config.get("subtitle", "")
        site_author = site_config.get("author", "")
        year = str(datetime.date.today().year)

        article_ctx = []
        total_words = 0
        dates = []

        for a in articles:
            meta, body = parse_frontmatter(a.l2)
            # word count estimate
            wc = len(body.split())
            total_words += wc
            if a.date:
                dates.append(a.date)
            item = {
                "canonical_id": a.canonical_id,
                "title": meta.get("title", a.slug),
                "date": a.date,
                "tags": meta.get("tags") or [],
                "abstract": a.l0 or "",
                "word_count": f"{round(wc / 100) * 100:,}" if wc > 100 else str(wc),
            }
            article_ctx.append(item)

        date_range = ""
        if dates:
            date_range = f"{min(dates)} 至 {max(dates)}"

        total_words_str = f"~{round(total_words / 1000)}k" if total_words >= 1000 else str(total_words)

        ctx = {
            "site_title": site_title,
            "site_subtitle": site_subtitle,
            "site_author": site_author,
            "year": year,
            "articles": article_ctx,
            "total_articles": len(article_ctx),
            "total_words": total_words_str,
            "date_range": date_range,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        html = self._render(self.INDEX_TEMPLATE_NAME, _DEFAULT_INDEX_TEMPLATE, ctx, autoescape=False)
        output_path.write_text(html, encoding="utf-8")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _render(self, template_name: str, default_src: str, ctx: dict, autoescape: bool = False) -> str:
        user_template_path = self._workspace_root / self.TEMPLATE_DIR / template_name
        if user_template_path.exists():
            env = self._get_fs_env(autoescape=autoescape)
            tmpl = env.get_template(template_name)
        else:
            env = jinja2.Environment(loader=jinja2.BaseLoader(), autoescape=autoescape)
            tmpl = env.from_string(default_src)
        return tmpl.render(**ctx)

    def _get_fs_env(self, autoescape: bool = False) -> jinja2.Environment:
        if self._env is None:
            template_dir = str(self._workspace_root / self.TEMPLATE_DIR)
            self._env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(template_dir),
                autoescape=autoescape,
            )
        return self._env


# ---------------------------------------------------------------------------
# Markdown → HTML
# ---------------------------------------------------------------------------

def _extract_toc(md: str) -> list[dict]:
    """Extract h2/h3 headings for table of contents."""
    import re
    toc = []
    for m in re.finditer(r"^(#{2,3})\s+(.+)", md, re.MULTILINE):
        text = m.group(2).strip()
        slug = re.sub(r"[^\w\u4e00-\u9fff-]", "-", text.lower()).strip("-")
        toc.append({"id": slug, "text": text, "level": len(m.group(1))})
    return toc


def _md_to_html(md: str) -> str:
    """Convert Markdown to HTML with id anchors on headings."""
    import re

    lines = md.split("\n")
    html_lines: list[str] = []
    in_code_block = False
    in_list = False
    in_ordered_list = False
    in_blockquote = False
    in_table = False
    table_rows: list[str] = []

    def flush_table():
        nonlocal in_table, table_rows
        if not table_rows:
            return
        out = ["<table>"]
        for i, row in enumerate(table_rows):
            cells = [c.strip() for c in row.strip("|").split("|")]
            if i == 0:
                out.append("<thead><tr>" + "".join(f"<th>{_inline(c)}</th>" for c in cells) + "</tr></thead><tbody>")
            elif i == 1 and all(re.match(r"^[-:]+$", c.strip()) for c in cells):
                continue  # separator row
            else:
                out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in cells) + "</tr>")
        out.append("</tbody></table>")
        html_lines.extend(out)
        table_rows = []
        in_table = False

    for line in lines:
        # Fenced code blocks
        if line.startswith("```"):
            if in_code_block:
                html_lines.append("</code></pre>")
                in_code_block = False
            else:
                if in_list: html_lines.append("</ul>"); in_list = False
                if in_ordered_list: html_lines.append("</ol>"); in_ordered_list = False
                lang = line[3:].strip()
                cls = f' class="language-{lang}"' if lang else ""
                html_lines.append(f"<pre><code{cls}>")
                in_code_block = True
            continue

        if in_code_block:
            html_lines.append(_escape(line))
            continue

        # Table
        if "|" in line and line.strip().startswith("|"):
            if not in_table:
                if in_list: html_lines.append("</ul>"); in_list = False
                if in_ordered_list: html_lines.append("</ol>"); in_ordered_list = False
                in_table = True
            table_rows.append(line)
            continue
        elif in_table:
            flush_table()

        # Close lists if needed
        if in_list and not (line.startswith("- ") or line.startswith("* ")):
            html_lines.append("</ul>"); in_list = False
        if in_ordered_list and not re.match(r"^\d+\.\s", line):
            html_lines.append("</ol>"); in_ordered_list = False

        # Headings
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            slug = re.sub(r"[^\w\u4e00-\u9fff-]", "-", text.lower()).strip("-")
            html_lines.append(f"<h{level} id=\"{slug}\">{_inline(text)}</h{level}>")
            continue

        # Horizontal rule
        if re.match(r"^[-*_]{3,}\s*$", line):
            html_lines.append("<hr>"); continue

        # Blockquote
        if line.startswith("> "):
            html_lines.append(f"<blockquote><p>{_inline(line[2:])}</p></blockquote>")
            continue

        # Ordered list
        m = re.match(r"^(\d+)\.\s+(.*)", line)
        if m:
            if not in_ordered_list:
                html_lines.append("<ol>"); in_ordered_list = True
            html_lines.append(f"<li>{_inline(m.group(2))}</li>")
            continue

        # Unordered list
        if line.startswith("- ") or line.startswith("* "):
            if not in_list:
                html_lines.append("<ul>"); in_list = True
            html_lines.append(f"<li>{_inline(line[2:])}</li>")
            continue

        # Blank line
        if not line.strip():
            html_lines.append(""); continue

        # Paragraph
        html_lines.append(f"<p>{_inline(line)}</p>")

    if in_list: html_lines.append("</ul>")
    if in_ordered_list: html_lines.append("</ol>")
    if in_code_block: html_lines.append("</code></pre>")
    if in_table: flush_table()

    return "\n".join(html_lines)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline(text: str) -> str:
    import re
    text = re.sub(r"`([^`]+)`", lambda m: f"<code>{_escape(m.group(1))}</code>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"_(.+?)_", r"<em>\1</em>", text)
    text = re.sub(r"!\[([^\]]*)\]\(([^\)]+)\)", r'<img src="\2" alt="\1">', text)
    text = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    return text
