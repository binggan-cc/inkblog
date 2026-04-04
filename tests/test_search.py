"""Tests for SearchSkill (ink_core/skills/search.py)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from ink_core.skills.search import SearchSkill, _tokenize, _count_hits, _extract_snippet


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_article(
    ink_dir: Path,
    year: str,
    month: str,
    day_slug: str,
    title: str,
    tags: list[str],
    abstract: str,
    summary: str,
    body: str = "",
    status: str = "published",
) -> Path:
    """Create a minimal article directory for testing."""
    import yaml

    article_path = ink_dir / year / month / day_slug
    article_path.mkdir(parents=True, exist_ok=True)
    (article_path / "assets").mkdir(exist_ok=True)

    date = f"{year}-{month}-{day_slug[:2]}"
    slug = day_slug[3:]  # strip "DD-"

    frontmatter = {
        "title": title,
        "slug": slug,
        "date": date,
        "status": status,
        "tags": tags,
    }
    fm_str = yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False, sort_keys=False)
    index_content = f"---\n{fm_str}---\n\n# {title}\n\n{body}\n"
    (article_path / "index.md").write_text(index_content, encoding="utf-8")

    (article_path / ".abstract").write_text(abstract, encoding="utf-8")

    overview_fm = {
        "title": title,
        "created_at": f"{date}T10:00:00",
        "updated_at": f"{date}T10:00:00",
        "status": status,
        "tags": tags,
        "word_count": len(body.split()),
        "reading_time_min": 1,
        "related": [],
    }
    ov_fm_str = yaml.dump(overview_fm, allow_unicode=True, default_flow_style=False, sort_keys=False)
    overview_content = f"---\n{ov_fm_str}---\n\n## Summary\n\n{summary}\n\n## Key Points\n\n- key point\n"
    (article_path / ".overview").write_text(overview_content, encoding="utf-8")

    return article_path


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------

class TestTokenize:
    def test_basic_ascii(self):
        assert _tokenize("hello world") == ["hello", "world"]

    def test_lowercase(self):
        assert _tokenize("Hello World") == ["hello", "world"]

    def test_cjk(self):
        tokens = _tokenize("人工智能 AI")
        assert "ai" in tokens

    def test_empty(self):
        assert _tokenize("") == []

    def test_punctuation_stripped(self):
        tokens = _tokenize("hello, world!")
        assert tokens == ["hello", "world"]


class TestCountHits:
    def test_single_keyword(self):
        assert _count_hits("hello world hello", ["hello"]) == 2

    def test_multiple_keywords(self):
        assert _count_hits("foo bar foo baz", ["foo", "baz"]) == 3

    def test_case_insensitive(self):
        assert _count_hits("Hello HELLO hello", ["hello"]) == 3

    def test_no_match(self):
        assert _count_hits("nothing here", ["xyz"]) == 0


class TestExtractSnippet:
    def test_returns_at_most_150_chars(self):
        long_text = "word " * 100
        snippet = _extract_snippet(long_text, ["word"])
        assert len(snippet) <= 155  # allow for ellipsis

    def test_contains_keyword_context(self):
        text = "The quick brown fox jumps over the lazy dog"
        snippet = _extract_snippet(text, ["fox"])
        assert "fox" in snippet

    def test_empty_text(self):
        assert _extract_snippet("", ["foo"]) == ""


# ---------------------------------------------------------------------------
# SearchSkill integration tests
# ---------------------------------------------------------------------------

class TestSearchSkillBasic:
    def test_empty_query_returns_failure(self, ink_dir):
        skill = SearchSkill(ink_dir)
        result = skill.execute(None, {"query": ""})
        assert result.success is False

    def test_no_articles_returns_empty_results(self, ink_dir):
        skill = SearchSkill(ink_dir)
        result = skill.execute("python", {})
        assert result.success is True
        assert result.data["results"] == []
        assert len(result.data["suggestions"]) >= 1

    def test_basic_l0_hit(self, ink_dir):
        _make_article(
            ink_dir, "2025", "03", "20-python-guide",
            title="Python Guide",
            tags=["python"],
            abstract="A comprehensive guide to Python programming.",
            summary="Learn Python from scratch.",
        )
        skill = SearchSkill(ink_dir)
        result = skill.execute("python", {})
        assert result.success is True
        assert len(result.data["results"]) >= 1
        ids = [r["canonical_id"] for r in result.data["results"]]
        assert "2025/03/20-python-guide" in ids

    def test_result_fields_present(self, ink_dir):
        _make_article(
            ink_dir, "2025", "03", "20-python-guide",
            title="Python Guide",
            tags=["python"],
            abstract="A comprehensive guide to Python programming.",
            summary="Learn Python from scratch.",
        )
        skill = SearchSkill(ink_dir)
        result = skill.execute("python", {})
        assert result.success is True
        hit = result.data["results"][0]
        for field in ("canonical_id", "title", "abstract", "snippet", "score",
                      "hit_layer", "hit_count", "date"):
            assert field in hit, f"Missing field: {field}"


class TestSearchSkillArchived:
    def test_archived_excluded_by_default(self, ink_dir):
        _make_article(
            ink_dir, "2025", "03", "20-archived-post",
            title="Archived Post",
            tags=["old"],
            abstract="This is an archived article about Python.",
            summary="Old content.",
            status="archived",
        )
        skill = SearchSkill(ink_dir)
        result = skill.execute("python", {})
        assert result.success is True
        ids = [r["canonical_id"] for r in result.data["results"]]
        assert "2025/03/20-archived-post" not in ids

    def test_archived_included_when_flag_set(self, ink_dir):
        _make_article(
            ink_dir, "2025", "03", "20-archived-post",
            title="Archived Post",
            tags=["old"],
            abstract="This is an archived article about Python.",
            summary="Old content.",
            status="archived",
        )
        skill = SearchSkill(ink_dir)
        result = skill.execute("python", {"include_archived": True})
        assert result.success is True
        ids = [r["canonical_id"] for r in result.data["results"]]
        assert "2025/03/20-archived-post" in ids


class TestSearchSkillTagFilter:
    def test_tag_filter_includes_matching(self, ink_dir):
        _make_article(
            ink_dir, "2025", "03", "20-ml-article",
            title="Machine Learning",
            tags=["ml", "python"],
            abstract="An article about machine learning.",
            summary="ML overview.",
        )
        _make_article(
            ink_dir, "2025", "03", "21-web-article",
            title="Web Development",
            tags=["web"],
            abstract="An article about web development.",
            summary="Web overview.",
        )
        skill = SearchSkill(ink_dir)
        result = skill.execute("article", {"tag": "ml"})
        assert result.success is True
        ids = [r["canonical_id"] for r in result.data["results"]]
        assert "2025/03/20-ml-article" in ids
        assert "2025/03/21-web-article" not in ids

    def test_tag_filter_excludes_non_matching(self, ink_dir):
        _make_article(
            ink_dir, "2025", "03", "20-ml-article",
            title="Machine Learning",
            tags=["ml"],
            abstract="An article about machine learning.",
            summary="ML overview.",
        )
        skill = SearchSkill(ink_dir)
        result = skill.execute("article", {"tag": "web"})
        assert result.success is True
        assert result.data["results"] == []


class TestSearchSkillLayerExpansion:
    def test_l1_expansion_when_l0_results_less_than_3(self, ink_dir):
        """When L0 hits < 3, L1 should be searched automatically."""
        # Create 1 article with keyword only in L0
        _make_article(
            ink_dir, "2025", "03", "20-l0-article",
            title="Some Article",
            tags=["misc"],
            abstract="This article mentions uniquekeyword123.",
            summary="No match here.",
        )
        # Create 2 articles with keyword only in L1 summary
        _make_article(
            ink_dir, "2025", "03", "21-l1-article-a",
            title="Another Article A",
            tags=["misc"],
            abstract="No match here.",
            summary="This summary mentions uniquekeyword123.",
        )
        _make_article(
            ink_dir, "2025", "03", "22-l1-article-b",
            title="Another Article B",
            tags=["misc"],
            abstract="No match here.",
            summary="This summary also mentions uniquekeyword123.",
        )

        skill = SearchSkill(ink_dir)
        result = skill.execute("uniquekeyword123", {})
        assert result.success is True
        ids = [r["canonical_id"] for r in result.data["results"]]
        # L0 hit
        assert "2025/03/20-l0-article" in ids
        # L1 hits (expanded because L0 < 3)
        assert "2025/03/21-l1-article-a" in ids
        assert "2025/03/22-l1-article-b" in ids

    def test_no_l1_expansion_when_l0_has_3_or_more(self, ink_dir):
        """When L0 hits >= 3, L1 should NOT be searched."""
        kw = "searchterm999"
        for i in range(3):
            _make_article(
                ink_dir, "2025", "03", f"2{i}-l0-article-{i}",
                title=f"Article {i}",
                tags=["misc"],
                abstract=f"This abstract contains {kw}.",
                summary="No match here.",
            )
        # One article with keyword only in L1
        _make_article(
            ink_dir, "2025", "03", "25-l1-only",
            title="L1 Only Article",
            tags=["misc"],
            abstract="No match here.",
            summary=f"This summary contains {kw}.",
        )

        skill = SearchSkill(ink_dir)
        result = skill.execute(kw, {})
        assert result.success is True
        ids = [r["canonical_id"] for r in result.data["results"]]
        # L1-only article should NOT appear
        assert "2025/03/25-l1-only" not in ids


class TestSearchSkillFulltext:
    def test_l2_not_searched_by_default(self, ink_dir):
        kw = "fulltextonlykeyword"
        _make_article(
            ink_dir, "2025", "03", "20-l2-article",
            title="L2 Article",
            tags=["misc"],
            abstract="No match.",
            summary="No match.",
            body=f"This body contains {kw}.",
        )
        skill = SearchSkill(ink_dir)
        result = skill.execute(kw, {})
        assert result.success is True
        ids = [r["canonical_id"] for r in result.data["results"]]
        assert "2025/03/20-l2-article" not in ids

    def test_l2_searched_with_fulltext_flag(self, ink_dir):
        kw = "fulltextonlykeyword"
        _make_article(
            ink_dir, "2025", "03", "20-l2-article",
            title="L2 Article",
            tags=["misc"],
            abstract="No match.",
            summary="No match.",
            body=f"This body contains {kw}.",
        )
        skill = SearchSkill(ink_dir)
        result = skill.execute(kw, {"fulltext": True})
        assert result.success is True
        ids = [r["canonical_id"] for r in result.data["results"]]
        assert "2025/03/20-l2-article" in ids

    def test_l2_searched_with_config_engine_fulltext(self, ink_dir):
        kw = "configfulltextkeyword"
        _make_article(
            ink_dir, "2025", "03", "20-l2-config-article",
            title="L2 Config Article",
            tags=["misc"],
            abstract="No match.",
            summary="No match.",
            body=f"This body contains {kw}.",
        )

        class FakeConfig:
            def get(self, key, default=None):
                if key == "search.engine":
                    return "fulltext"
                return default

        skill = SearchSkill(ink_dir, config=FakeConfig())
        result = skill.execute(kw, {})
        assert result.success is True
        ids = [r["canonical_id"] for r in result.data["results"]]
        assert "2025/03/20-l2-config-article" in ids


class TestSearchSkillSorting:
    def test_title_hit_ranks_above_l0_hit(self, ink_dir):
        kw = "rankingtest"
        # Article with keyword in title
        _make_article(
            ink_dir, "2025", "03", "20-title-hit",
            title=f"Article about {kw}",
            tags=["misc"],
            abstract="No match.",
            summary="No match.",
        )
        # Article with keyword in L0 only
        _make_article(
            ink_dir, "2025", "03", "21-l0-hit",
            title="Unrelated Title",
            tags=["misc"],
            abstract=f"This abstract mentions {kw}.",
            summary="No match.",
        )
        skill = SearchSkill(ink_dir)
        result = skill.execute(kw, {})
        assert result.success is True
        results = result.data["results"]
        assert len(results) >= 2
        ids = [r["canonical_id"] for r in results]
        title_idx = ids.index("2025/03/20-title-hit")
        l0_idx = ids.index("2025/03/21-l0-hit")
        assert title_idx < l0_idx, "Title hit should rank above L0 hit"

    def test_tag_hit_ranks_above_l0_hit(self, ink_dir):
        kw = "tagranking"
        _make_article(
            ink_dir, "2025", "03", "20-tag-hit",
            title="Unrelated",
            tags=[kw],
            abstract="No match.",
            summary="No match.",
        )
        _make_article(
            ink_dir, "2025", "03", "21-l0-hit",
            title="Unrelated",
            tags=["misc"],
            abstract=f"This abstract mentions {kw}.",
            summary="No match.",
        )
        skill = SearchSkill(ink_dir)
        result = skill.execute(kw, {})
        assert result.success is True
        results = result.data["results"]
        ids = [r["canonical_id"] for r in results]
        tag_idx = ids.index("2025/03/20-tag-hit")
        l0_idx = ids.index("2025/03/21-l0-hit")
        assert tag_idx < l0_idx, "Tag hit should rank above L0 hit"

    def test_same_layer_sorted_by_hit_count_desc(self, ink_dir):
        kw = "counttest"
        # Article with 3 hits in L0
        _make_article(
            ink_dir, "2025", "03", "20-high-count",
            title="Unrelated",
            tags=["misc"],
            abstract=f"{kw} {kw} {kw} three times.",
            summary="No match.",
        )
        # Article with 1 hit in L0
        _make_article(
            ink_dir, "2025", "03", "21-low-count",
            title="Unrelated",
            tags=["misc"],
            abstract=f"{kw} once.",
            summary="No match.",
        )
        skill = SearchSkill(ink_dir)
        result = skill.execute(kw, {})
        assert result.success is True
        results = result.data["results"]
        ids = [r["canonical_id"] for r in results]
        high_idx = ids.index("2025/03/20-high-count")
        low_idx = ids.index("2025/03/21-low-count")
        assert high_idx < low_idx, "Higher hit count should rank first"

    def test_same_layer_same_count_sorted_by_date_desc(self, ink_dir):
        kw = "datetest"
        # Newer article
        _make_article(
            ink_dir, "2026", "01", "15-newer",
            title="Unrelated",
            tags=["misc"],
            abstract=f"{kw} once.",
            summary="No match.",
        )
        # Older article
        _make_article(
            ink_dir, "2025", "01", "15-older",
            title="Unrelated",
            tags=["misc"],
            abstract=f"{kw} once.",
            summary="No match.",
        )
        skill = SearchSkill(ink_dir)
        result = skill.execute(kw, {})
        assert result.success is True
        results = result.data["results"]
        ids = [r["canonical_id"] for r in results]
        newer_idx = ids.index("2026/01/15-newer")
        older_idx = ids.index("2025/01/15-older")
        assert newer_idx < older_idx, "Newer date should rank first when tied"


class TestSearchSkillEmptyResults:
    def test_empty_results_include_query(self, ink_dir):
        skill = SearchSkill(ink_dir)
        result = skill.execute("xyznonexistent", {})
        assert result.success is True
        assert result.data["query"] == "xyznonexistent"

    def test_empty_results_include_suggestions(self, ink_dir):
        skill = SearchSkill(ink_dir)
        result = skill.execute("xyznonexistent", {})
        assert result.success is True
        assert "suggestions" in result.data
        assert len(result.data["suggestions"]) >= 1

    def test_empty_results_list_is_empty(self, ink_dir):
        skill = SearchSkill(ink_dir)
        result = skill.execute("xyznonexistent", {})
        assert result.success is True
        assert result.data["results"] == []
