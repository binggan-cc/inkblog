"""Property-based tests for ink_core using hypothesis.

Covers:
- Task 3.2  / Property 8:  L0 摘要约束
- Task 3.4  / Property 12: L0/L1 往返属性
- Task 6.3  / Property 13: 发布状态门控
- Task 8.3  / Property 19: 搜索排序稳定性
- Task 13.2 / Property 25: 幂等性
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ink_core.fs.layer_generator import L0Generator, L1Generator
from ink_core.fs.markdown import (
    dump_frontmatter,
    parse_frontmatter,
    parse_overview,
    serialize_overview,
)


# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------

# Printable ASCII + common CJK range, no null bytes
_safe_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd", "Zs", "Po", "Pd"),
        whitelist_characters="\n ",
    ),
    min_size=0,
    max_size=2000,
)

_nonempty_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd", "Zs"),
        whitelist_characters=" \n",
    ),
    min_size=1,
    max_size=500,
)

_tag = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="-"),
    min_size=1,
    max_size=20,
)

_tags_list = st.lists(_tag, min_size=0, max_size=5)

_status = st.sampled_from(["draft", "review", "ready", "published", "archived"])

_date = st.dates(
    min_value=__import__("datetime").date(2020, 1, 1),
    max_value=__import__("datetime").date(2030, 12, 31),
).map(lambda d: d.isoformat())


def _make_index_md(title: str, body: str, status: str = "draft", tags=None) -> str:
    """Build a minimal index.md string."""
    import yaml
    if tags is None:
        tags = []
    meta = {
        "title": title or "Untitled",
        "slug": "test-slug",
        "date": "2025-01-01",
        "status": status,
        "tags": tags,
    }
    yaml_str = yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return f"---\n{yaml_str}---\n\n{body}"


# ---------------------------------------------------------------------------
# Property 8: L0 摘要约束
# Feature: ink-blog-core, Property 8: L0 summary constraint
# ---------------------------------------------------------------------------

class TestP8L0SummaryConstraint:
    """For any Markdown content, L0Generator must produce a single-line
    string of at most 200 characters."""

    @given(content=_safe_text)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_l0_never_exceeds_200_chars(self, content: str) -> None:
        gen = L0Generator()
        result = gen.generate(content)
        assert len(result) <= 200, f"L0 too long ({len(result)}): {result!r}"

    @given(content=_safe_text)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_l0_is_single_line(self, content: str) -> None:
        gen = L0Generator()
        result = gen.generate(content)
        assert "\n" not in result, f"L0 contains newline: {result!r}"

    @given(title=_nonempty_text, body=_safe_text)
    @settings(max_examples=150, suppress_health_check=[HealthCheck.too_slow])
    def test_l0_single_line_from_full_document(self, title: str, body: str) -> None:
        content = _make_index_md(title, body)
        gen = L0Generator()
        result = gen.generate(content)
        assert "\n" not in result
        assert len(result) <= 200

    @given(body=st.text(min_size=201, max_size=5000))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_l0_truncates_long_body(self, body: str) -> None:
        """Even very long body text must produce ≤200 char L0."""
        content = _make_index_md("Long Article", body)
        gen = L0Generator()
        result = gen.generate(content)
        assert len(result) <= 200


# ---------------------------------------------------------------------------
# Property 12: L0/L1 往返属性
# Feature: ink-blog-core, Property 12: L0/L1 round-trip
# ---------------------------------------------------------------------------

class TestP12RoundTrip:
    """parse(serialize(parse(content))) == parse(content) for .overview files."""

    @given(
        title=_nonempty_text,
        tags=_tags_list,
        status=_status,
        summary=_nonempty_text,
    )
    @settings(max_examples=150, suppress_health_check=[HealthCheck.too_slow])
    def test_overview_roundtrip(
        self, title: str, tags: list[str], status: str, summary: str
    ) -> None:
        """serialize_overview(parse_overview(content)) round-trips correctly."""
        # Build a valid .overview string
        import yaml
        meta = {
            "title": title,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
            "status": status,
            "tags": tags,
            "word_count": 100,
            "reading_time_min": 1,
            "related": [],
        }
        yaml_str = yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False)
        key_points = ["Point one", "Point two"]
        kp_items = "\n".join(f"- {p}" for p in key_points)
        overview_content = (
            f"---\n{yaml_str}---\n\n"
            f"## Summary\n\n{summary.strip()}\n\n"
            f"## Key Points\n\n{kp_items}\n"
        )

        # First parse
        parsed1 = parse_overview(overview_content)
        # Serialize back
        serialized = serialize_overview(parsed1)
        # Second parse
        parsed2 = parse_overview(serialized)

        # Semantic equivalence: meta fields, summary, key_points
        assert parsed1["meta"].get("title") == parsed2["meta"].get("title")
        assert parsed1["meta"].get("status") == parsed2["meta"].get("status")
        assert parsed1["meta"].get("tags") == parsed2["meta"].get("tags")
        assert parsed1["summary"].strip() == parsed2["summary"].strip()
        assert parsed1["key_points"] == parsed2["key_points"]

    @given(
        meta_dict=st.fixed_dictionaries({
            "title": _nonempty_text,
            "status": _status,
            "tags": _tags_list,
        }),
        body=_nonempty_text,
    )
    @settings(max_examples=150, suppress_health_check=[HealthCheck.too_slow])
    def test_frontmatter_roundtrip(self, meta_dict: dict, body: str) -> None:
        """dump_frontmatter(parse_frontmatter(content)) round-trips correctly."""
        content = dump_frontmatter(meta_dict, body)
        parsed_meta, parsed_body = parse_frontmatter(content)

        # Re-serialize and re-parse
        content2 = dump_frontmatter(parsed_meta, parsed_body)
        parsed_meta2, parsed_body2 = parse_frontmatter(content2)

        assert parsed_meta.get("title") == parsed_meta2.get("title")
        assert parsed_meta.get("status") == parsed_meta2.get("status")
        assert parsed_meta.get("tags") == parsed_meta2.get("tags")
        assert parsed_body.strip() == parsed_body2.strip()

    @given(content=_nonempty_text)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_l0_generate_is_deterministic(self, content: str) -> None:
        """L0Generator produces the same output for the same input."""
        gen = L0Generator()
        r1 = gen.generate(content)
        r2 = gen.generate(content)
        assert r1 == r2


# ---------------------------------------------------------------------------
# Workspace factory helper (avoids function-scoped fixture + @given conflict)
# ---------------------------------------------------------------------------

def _make_workspace(base: Path, name: str = "ws") -> Path:
    """Create a minimal ink workspace under base/name."""
    ws = base / name
    ws.mkdir(parents=True, exist_ok=True)
    (ws / ".ink" / "sessions").mkdir(parents=True, exist_ok=True)
    (ws / ".ink" / "skills").mkdir(parents=True, exist_ok=True)
    (ws / "_index").mkdir(exist_ok=True)
    return ws


# ---------------------------------------------------------------------------
# Property 13: 发布状态门控
# Feature: ink-blog-core, Property 13: Publish status gate
# ---------------------------------------------------------------------------

class TestP13PublishStatusGate:
    """For any Article with status != 'ready', PublishSkill must reject publish."""

    @given(status=st.sampled_from(["draft", "review", "published", "archived"]))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_non_ready_status_rejected(self, tmp_path: Path, status: str) -> None:
        """Any status other than 'ready' must be rejected by PublishSkill."""
        import tempfile
        from ink_core.fs.article import ArticleManager
        from ink_core.skills.publish import PublishSkill

        with tempfile.TemporaryDirectory() as td:
            workspace = _make_workspace(Path(td))
            manager = ArticleManager(workspace)
            article = manager.create(f"Gate Test {status}", date="2025-09-01")

            index_path = article.path / "index.md"
            content = index_path.read_text(encoding="utf-8")
            content = content.replace("status: draft", f"status: {status}")
            index_path.write_text(content, encoding="utf-8")

            skill = PublishSkill(workspace)
            result = skill.execute(article.canonical_id, {"channels": ["blog"]})

            assert not result.success
            assert status in result.message or "ready" in result.message.lower()

    @given(status=st.sampled_from(["draft", "review", "published", "archived"]))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_non_ready_does_not_modify_index_md(self, tmp_path: Path, status: str) -> None:
        """Rejected publish must not modify index.md."""
        import tempfile
        from ink_core.fs.article import ArticleManager
        from ink_core.skills.publish import PublishSkill

        with tempfile.TemporaryDirectory() as td:
            workspace = _make_workspace(Path(td))
            manager = ArticleManager(workspace)
            article = manager.create(f"No Modify {status}", date="2025-09-02")

            index_path = article.path / "index.md"
            content = index_path.read_text(encoding="utf-8")
            content = content.replace("status: draft", f"status: {status}")
            index_path.write_text(content, encoding="utf-8")

            original_content = index_path.read_text(encoding="utf-8")

            skill = PublishSkill(workspace)
            skill.execute(article.canonical_id, {"channels": ["blog"]})

            after_content = index_path.read_text(encoding="utf-8")
            assert original_content == after_content

    def test_ready_status_is_accepted(self, tmp_path: Path) -> None:
        """status='ready' must be accepted by PublishSkill."""
        from ink_core.fs.article import ArticleManager
        from ink_core.skills.publish import PublishSkill

        workspace = _make_workspace(tmp_path)
        manager = ArticleManager(workspace)
        article = manager.create("Ready Gate Test", date="2025-09-03")

        index_path = article.path / "index.md"
        content = index_path.read_text(encoding="utf-8").replace("status: draft", "status: ready")
        index_path.write_text(content, encoding="utf-8")

        skill = PublishSkill(workspace)
        result = skill.execute(article.canonical_id, {"channels": ["blog"]})
        assert result.success


# ---------------------------------------------------------------------------
# Property 19: 搜索排序稳定性
# Feature: ink-blog-core, Property 19: Search sort stability
# ---------------------------------------------------------------------------

class TestP19SearchSortStability:
    """Search results must satisfy the multi-level sort invariant:
    score desc → hit_count desc → date desc."""

    @given(
        n_articles=st.integers(min_value=2, max_value=8),
        query=st.sampled_from(["python", "blog", "test", "article", "ink"]),
    )
    @settings(max_examples=80, suppress_health_check=[HealthCheck.too_slow])
    def test_results_sorted_by_score_then_hit_count_then_date(
        self, n_articles: int, query: str
    ) -> None:
        """Results must be sorted: score desc, hit_count desc, date desc."""
        import tempfile
        from ink_core.fs.article import ArticleManager
        from ink_core.skills.search import SearchSkill

        with tempfile.TemporaryDirectory() as td:
            workspace = _make_workspace(Path(td))
            manager = ArticleManager(workspace)
            for i in range(n_articles):
                manager.create(
                    f"{query} article number {i}",
                    date=f"2025-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
                    tags=[query] if i % 2 == 0 else [],
                )

            skill = SearchSkill(workspace)
            result = skill.execute(query, {})

            if not result.success or not result.data.get("results"):
                return  # No results is valid; skip sort check

            results = result.data["results"]
            for i in range(len(results) - 1):
                a, b = results[i], results[i + 1]
                assert a["score"] >= b["score"], (
                    f"Sort violation at [{i}]: score {a['score']} < {b['score']}"
                )
                if a["score"] == b["score"]:
                    assert a["hit_count"] >= b["hit_count"], (
                        f"Sort violation at [{i}]: hit_count {a['hit_count']} < {b['hit_count']}"
                    )
                    if a["hit_count"] == b["hit_count"]:
                        assert a["date"] >= b["date"], (
                            f"Sort violation at [{i}]: date {a['date']} < {b['date']}"
                        )

    @given(query=st.sampled_from(["python", "blog", "test"]))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_sort_is_deterministic(self, query: str) -> None:
        """Same query on same data must produce identical ordering."""
        import tempfile
        from ink_core.fs.article import ArticleManager
        from ink_core.skills.search import SearchSkill

        with tempfile.TemporaryDirectory() as td:
            workspace = _make_workspace(Path(td))
            manager = ArticleManager(workspace)
            for i in range(3):
                manager.create(
                    f"{query} determinism test {i}",
                    date=f"2025-10-{i + 1:02d}",
                    tags=[query],
                )

            skill = SearchSkill(workspace)
            r1 = skill.execute(query, {})
            r2 = skill.execute(query, {})

            ids1 = [r["canonical_id"] for r in r1.data.get("results", [])]
            ids2 = [r["canonical_id"] for r in r2.data.get("results", [])]
            assert ids1 == ids2

    def test_title_hit_ranks_above_l0_hit(self, tmp_path: Path) -> None:
        """Title match must rank higher than L0-only match."""
        from ink_core.fs.article import ArticleManager
        from ink_core.skills.search import SearchSkill

        workspace = _make_workspace(tmp_path)
        manager = ArticleManager(workspace)

        a_title = manager.create("Python Programming Guide", date="2025-10-10", tags=[])
        a_l0 = manager.create("General Programming Notes", date="2025-10-11", tags=[])
        (a_l0.path / ".abstract").write_text(
            "This article discusses python scripting techniques.", encoding="utf-8"
        )

        skill = SearchSkill(workspace)
        result = skill.execute("python", {})
        assert result.success

        results = result.data["results"]
        ids = [r["canonical_id"] for r in results]

        if a_title.canonical_id in ids and a_l0.canonical_id in ids:
            idx_title = ids.index(a_title.canonical_id)
            idx_l0 = ids.index(a_l0.canonical_id)
            assert idx_title < idx_l0, "Title hit should rank above L0-only hit"


# ---------------------------------------------------------------------------
# Property 25: 幂等性
# Feature: ink-blog-core, Property 25: Idempotency
# ---------------------------------------------------------------------------

class TestP25Idempotency:
    """rebuild / analyze / search on same input twice must produce consistent results."""

    @given(
        title=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Zs")),
            min_size=3,
            max_size=40,
        ).filter(lambda t: t.strip()),
    )
    @settings(max_examples=60, suppress_health_check=[HealthCheck.too_slow])
    def test_rebuild_is_idempotent(self, title: str) -> None:
        """Running rebuild twice produces identical .abstract and key structural content."""
        import tempfile
        from ink_core.cli.builtin import RebuildCommand
        from ink_core.fs.article import ArticleManager

        with tempfile.TemporaryDirectory() as td:
            workspace = _make_workspace(Path(td))
            manager = ArticleManager(workspace)
            article = manager.create(title.strip(), date="2025-11-01")

            rebuild = RebuildCommand(workspace)
            rebuild.run(None, {})

            abstract1 = (article.path / ".abstract").read_text(encoding="utf-8")
            overview1 = (article.path / ".overview").read_text(encoding="utf-8")

            rebuild.run(None, {})

            abstract2 = (article.path / ".abstract").read_text(encoding="utf-8")
            parsed1 = parse_overview(overview1)
            parsed2 = parse_overview((article.path / ".overview").read_text(encoding="utf-8"))

            assert abstract1 == abstract2
            assert parsed1["meta"].get("title") == parsed2["meta"].get("title")
            assert parsed1["meta"].get("tags") == parsed2["meta"].get("tags")
            assert parsed1["summary"] == parsed2["summary"]
            assert parsed1["key_points"] == parsed2["key_points"]

    @given(query=st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Zs")),
        min_size=2,
        max_size=20,
    ).filter(lambda q: q.strip()))
    @settings(max_examples=60, suppress_health_check=[HealthCheck.too_slow])
    def test_search_is_idempotent(self, query: str) -> None:
        """Running search twice on same data returns same canonical_id ordering."""
        import tempfile
        from ink_core.fs.article import ArticleManager
        from ink_core.skills.search import SearchSkill

        with tempfile.TemporaryDirectory() as td:
            workspace = _make_workspace(Path(td))
            manager = ArticleManager(workspace)
            q = query.strip()
            manager.create(f"{q} idempotent article one", date="2025-11-02", tags=[])
            manager.create(f"{q} idempotent article two", date="2025-11-03", tags=[])

            skill = SearchSkill(workspace)
            r1 = skill.execute(q, {})
            r2 = skill.execute(q, {})

            ids1 = [r["canonical_id"] for r in r1.data.get("results", [])]
            ids2 = [r["canonical_id"] for r in r2.data.get("results", [])]
            assert ids1 == ids2

    @given(
        title=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Zs")),
            min_size=3,
            max_size=30,
        ).filter(lambda t: t.strip()),
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_analyze_word_count_is_idempotent(self, title: str) -> None:
        """Running analyze twice returns the same word_count."""
        import tempfile
        from ink_core.fs.article import ArticleManager
        from ink_core.skills.analyze import AnalyzeSkill

        with tempfile.TemporaryDirectory() as td:
            workspace = _make_workspace(Path(td))
            manager = ArticleManager(workspace)
            article = manager.create(title.strip(), date="2025-11-04")

            skill = AnalyzeSkill(workspace)
            r1 = skill.execute(article.canonical_id, {})
            r2 = skill.execute(article.canonical_id, {})

            if r1.success and r2.success:
                assert r1.data["word_count"] == r2.data["word_count"]
                assert r1.data["tags"] == r2.data["tags"]
