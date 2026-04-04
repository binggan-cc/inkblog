"""Tests for ink_core/fs/markdown.py."""

from __future__ import annotations

import textwrap

import pytest

from ink_core.fs.markdown import (
    dump_frontmatter,
    parse_frontmatter,
    parse_overview,
    serialize_overview,
)


# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------

class TestParseFrontmatter:
    def test_basic_frontmatter(self):
        content = textwrap.dedent("""\
            ---
            title: "Hello"
            status: draft
            ---

            Body text here.
        """)
        meta, body = parse_frontmatter(content)
        assert meta["title"] == "Hello"
        assert meta["status"] == "draft"
        assert "Body text here." in body

    def test_no_frontmatter_returns_empty_dict(self):
        content = "Just plain text, no frontmatter."
        meta, body = parse_frontmatter(content)
        assert meta == {}
        assert body == content

    def test_empty_frontmatter(self):
        content = "---\n---\n\nBody."
        meta, body = parse_frontmatter(content)
        assert meta == {}
        assert "Body." in body

    def test_frontmatter_with_list(self):
        content = textwrap.dedent("""\
            ---
            tags:
              - python
              - blog
            ---

            Content.
        """)
        meta, body = parse_frontmatter(content)
        assert meta["tags"] == ["python", "blog"]

    def test_body_preserved(self):
        content = "---\ntitle: T\n---\n\n# Heading\n\nParagraph.\n"
        _, body = parse_frontmatter(content)
        assert "# Heading" in body
        assert "Paragraph." in body


# ---------------------------------------------------------------------------
# dump_frontmatter
# ---------------------------------------------------------------------------

class TestDumpFrontmatter:
    def test_roundtrip(self):
        meta = {"title": "Test", "status": "draft", "tags": ["a", "b"]}
        body = "Some body content.\n"
        result = dump_frontmatter(meta, body)
        assert result.startswith("---\n")
        assert "---\n\n" in result
        assert "Some body content." in result

    def test_meta_fields_present(self):
        meta = {"title": "My Post", "status": "ready"}
        result = dump_frontmatter(meta, "")
        assert "title:" in result
        assert "My Post" in result
        assert "status:" in result

    def test_empty_meta(self):
        result = dump_frontmatter({}, "body")
        assert result.startswith("---\n")
        assert "body" in result

    def test_unicode_preserved(self):
        meta = {"title": "中文标题"}
        result = dump_frontmatter(meta, "内容")
        assert "中文标题" in result
        assert "内容" in result


# ---------------------------------------------------------------------------
# parse_overview
# ---------------------------------------------------------------------------

SAMPLE_OVERVIEW = textwrap.dedent("""\
    ---
    title: "文章标题"
    created_at: "2025-03-20T10:30:00"
    updated_at: "2025-03-20T15:00:00"
    status: "draft"
    tags: ["ai", "python"]
    word_count: 1500
    reading_time_min: 8
    related: []
    ---

    ## Summary

    3-5 sentence summary content.

    ## Key Points

    - Point one
    - Point two
""")


class TestParseOverview:
    def test_meta_extracted(self):
        data = parse_overview(SAMPLE_OVERVIEW)
        assert data["meta"]["title"] == "文章标题"
        assert data["meta"]["status"] == "draft"
        assert data["meta"]["tags"] == ["ai", "python"]

    def test_summary_extracted(self):
        data = parse_overview(SAMPLE_OVERVIEW)
        assert data["summary"] == "3-5 sentence summary content."

    def test_key_points_extracted(self):
        data = parse_overview(SAMPLE_OVERVIEW)
        assert data["key_points"] == ["Point one", "Point two"]

    def test_missing_sections_return_defaults(self):
        content = "---\ntitle: T\n---\n\nNo sections here.\n"
        data = parse_overview(content)
        assert data["summary"] == ""
        assert data["key_points"] == []

    def test_no_frontmatter(self):
        content = "## Summary\n\nSome summary.\n\n## Key Points\n\n- Item\n"
        data = parse_overview(content)
        assert data["meta"] == {}
        assert data["summary"] == "Some summary."
        assert data["key_points"] == ["Item"]


# ---------------------------------------------------------------------------
# serialize_overview
# ---------------------------------------------------------------------------

class TestSerializeOverview:
    def test_produces_frontmatter(self):
        data = {
            "meta": {"title": "Test", "status": "draft"},
            "summary": "A short summary.",
            "key_points": ["Point A", "Point B"],
        }
        result = serialize_overview(data)
        assert result.startswith("---\n")
        assert "title:" in result
        assert "## Summary" in result
        assert "A short summary." in result
        assert "## Key Points" in result
        assert "- Point A" in result
        assert "- Point B" in result

    def test_empty_key_points_omitted(self):
        data = {"meta": {}, "summary": "Summary text.", "key_points": []}
        result = serialize_overview(data)
        assert "## Key Points" not in result

    def test_empty_summary_omitted(self):
        data = {"meta": {}, "summary": "", "key_points": ["Item"]}
        result = serialize_overview(data)
        assert "## Summary" not in result
        assert "## Key Points" in result


# ---------------------------------------------------------------------------
# Round-trip property
# ---------------------------------------------------------------------------

class TestRoundTrip:
    def test_parse_serialize_parse_roundtrip(self):
        """parse_overview(serialize_overview(parse_overview(content))) == parse_overview(content)"""
        original = parse_overview(SAMPLE_OVERVIEW)
        serialized = serialize_overview(original)
        reparsed = parse_overview(serialized)
        assert reparsed["meta"] == original["meta"]
        assert reparsed["summary"] == original["summary"]
        assert reparsed["key_points"] == original["key_points"]

    def test_dump_parse_frontmatter_roundtrip(self):
        meta = {"title": "Hello", "tags": ["x", "y"], "count": 42}
        body = "Some body.\n"
        dumped = dump_frontmatter(meta, body)
        parsed_meta, parsed_body = parse_frontmatter(dumped)
        assert parsed_meta == meta
        assert parsed_body.strip() == body.strip()

    def test_real_overview_file_roundtrip(self, sample_article_dir):
        """Round-trip using the fixture .overview file."""
        overview_path = sample_article_dir / ".overview"
        content = overview_path.read_text(encoding="utf-8")
        original = parse_overview(content)
        serialized = serialize_overview(original)
        reparsed = parse_overview(serialized)
        assert reparsed["meta"] == original["meta"]
        assert reparsed["summary"] == original["summary"]
        assert reparsed["key_points"] == original["key_points"]
