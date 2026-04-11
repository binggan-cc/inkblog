"""Tests for the self-contained Markdown renderer."""

from __future__ import annotations

import sys

from ink_core.fs.markdown_renderer import render_markdown


def test_render_markdown_escapes_raw_html() -> None:
    html = render_markdown("hello <script>alert(1)</script>", safe=True)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_code_block_escapes_script_as_text() -> None:
    html = render_markdown("```html\n<script>alert(1)</script>\n```", safe=True)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<pre" in html


def test_render_markdown_is_deterministic() -> None:
    md = "# Title\n\n**bold** and `code`"
    assert render_markdown(md, safe=True) == render_markdown(md, safe=True)


def test_module_has_no_site_renderer_dependency() -> None:
    sys.modules.pop("ink_core.site.renderer", None)
    import ink_core.fs.markdown_renderer  # noqa: F401

    assert "ink_core.site.renderer" not in sys.modules
