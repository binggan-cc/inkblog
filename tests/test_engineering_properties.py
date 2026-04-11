"""Property tests for engineering hardening tasks."""

from __future__ import annotations

import hashlib
from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ink_core.core.status import ArticleStatus
from ink_core.fs.article import ArticleManager, SlugResolver
from ink_core.fs.markdown_renderer import render_markdown
from ink_core.skills.executor import SkillExecutor
from ink_core.skills.loader import SkillDefinition
from ink_core.skills.publish import PublishSkill


_titles = st.text(min_size=1, max_size=80)
_cjk_titles = st.text(
    alphabet=st.characters(min_codepoint=0x4E00, max_codepoint=0x9FFF),
    min_size=1,
    max_size=20,
)


def _definition(*steps: str) -> SkillDefinition:
    return SkillDefinition(
        skill="prop-skill",
        version="1.0",
        description="",
        context_requirement="L2",
        inputs={},
        steps=list(steps),
    )


@given(title=_titles)
@settings(max_examples=100)
def test_property_1_slug_non_empty(title: str) -> None:
    slug = SlugResolver(Path("/tmp")).generate_slug(title)
    assert slug
    assert "/" not in slug


@given(title=_cjk_titles)
@settings(max_examples=100)
def test_property_2_cjk_slug_usable(title: str) -> None:
    slug = SlugResolver(Path("/tmp")).generate_slug(title)
    assert slug
    assert not any("\u4e00" <= ch <= "\u9fff" for ch in slug)


@given(title=_titles)
@settings(max_examples=100)
def test_property_3_slug_deterministic(title: str) -> None:
    resolver = SlugResolver(Path("/tmp"))
    assert resolver.generate_slug(title) == resolver.generate_slug(title)


def test_property_4_mixed_slug_combines_ascii_and_pinyin() -> None:
    slug = SlugResolver(Path("/tmp")).generate_slug("Python 深度学习")
    assert slug.startswith("python-")
    assert slug != SlugResolver(Path("/tmp")).generate_slug("Python 机器学习")


def test_property_5_status_enum_complete() -> None:
    assert {s.value for s in ArticleStatus} == {
        "draft",
        "review",
        "ready",
        "drafted",
        "published",
        "archived",
    }


def test_property_6_status_transition_closure() -> None:
    values = {s.value for s in ArticleStatus}
    transitions = ArticleStatus.valid_transitions()
    assert set(transitions) == values
    for targets in transitions.values():
        assert set(targets) <= values


def test_property_7_draft_saved_does_not_publish(tmp_path: Path) -> None:
    article = ArticleManager(tmp_path).create("Draft Saved", date="2025-03-01")
    index_path = article.path / "index.md"
    index_path.write_text(
        index_path.read_text(encoding="utf-8").replace("status: draft", "status: ready"),
        encoding="utf-8",
    )

    result = PublishSkill(tmp_path).execute(article.canonical_id, {"channels": ["mastodon"]})
    assert result.success
    assert "status: drafted" in index_path.read_text(encoding="utf-8")


@given(payload=st.text(min_size=0, max_size=80))
@settings(max_examples=100)
def test_property_8_rendering_escapes_scripts(payload: str) -> None:
    rendered = render_markdown(f"<script>{payload}</script>", safe=True)
    assert "<script>" not in rendered


@given(md=st.text(min_size=0, max_size=200))
@settings(max_examples=100)
def test_property_9_rendering_deterministic(md: str) -> None:
    assert render_markdown(md, safe=True) == render_markdown(md, safe=True)


def test_property_10_skill_steps_execute_in_order(tmp_path: Path) -> None:
    article = ArticleManager(tmp_path).create("Step Order", date="2025-03-02")
    result = SkillExecutor(tmp_path).execute(
        _definition("read_content L0", "write_file order.txt"),
        article.canonical_id,
        {},
    )
    assert result.success
    assert (tmp_path / ".ink" / "skill-output" / "order.txt").exists()


def test_property_11_skill_failure_isolates_later_steps(tmp_path: Path) -> None:
    result = SkillExecutor(tmp_path).execute(
        _definition("write_file ../../escape.txt", "write_file after.txt"),
        None,
        {},
    )
    assert not result.success
    assert not (tmp_path / ".ink" / "skill-output" / "after.txt").exists()


def test_property_12_unsupported_steps_are_skipped(tmp_path: Path) -> None:
    result = SkillExecutor(tmp_path).execute(_definition("summarize L2"), None, {})
    assert result.success
    assert "skipped" in result.data["outputs"][0]


@given(title=st.text(min_size=1, max_size=40))
@settings(
    max_examples=100,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
def test_property_13_template_variables_escape(tmp_path: Path, title: str) -> None:
    from ink_core.site.renderer import TemplateRenderer

    slug = hashlib.sha256(title.encode("utf-8")).hexdigest()[:12]
    article = ArticleManager(tmp_path).create(
        f"<script>{title}</script>",
        date="2025-03-03",
        slug=slug,
    )
    out = tmp_path / "_site" / "x.html"
    TemplateRenderer(tmp_path).render_article(article, out)
    assert "<h1><script>" not in out.read_text(encoding="utf-8")


def test_property_14_body_html_not_double_escaped(tmp_path: Path) -> None:
    from ink_core.site.renderer import TemplateRenderer

    article = ArticleManager(tmp_path).create("Body", date="2025-03-04")
    article.l2 += "\n\n**bold**"
    out = tmp_path / "_site" / "body.html"
    TemplateRenderer(tmp_path).render_article(article, out)
    assert "<strong>bold</strong>" in out.read_text(encoding="utf-8")
