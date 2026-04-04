"""Shared fixtures for ink_core tests."""

import textwrap
from pathlib import Path

import pytest


@pytest.fixture
def ink_dir(tmp_path: Path) -> Path:
    """Temporary workspace root that mimics an ink project directory.

    Creates the minimal directory structure expected by ink_core:
      <tmp>/
        .ink/
          sessions/
          skills/
        _index/
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    (workspace / ".ink" / "sessions").mkdir(parents=True)
    (workspace / ".ink" / "skills").mkdir(parents=True)
    (workspace / "_index").mkdir()

    return workspace


@pytest.fixture
def sample_article_dir(ink_dir: Path) -> Path:
    """Create a sample article directory with all three layers populated.

    Returns the article directory path:
      <ink_dir>/2025/03/20-liquid-blog/
    """
    article_path = ink_dir / "2025" / "03" / "20-liquid-blog"
    article_path.mkdir(parents=True)
    (article_path / "assets").mkdir()

    # L2: index.md (Source of Truth)
    index_md = textwrap.dedent("""\
        ---
        title: "Liquid Blog"
        slug: "liquid-blog"
        date: "2025-03-20"
        status: "draft"
        tags: ["blog", "skills"]
        ---

        # Liquid Blog

        This is a sample article about the liquid blog system.

        It demonstrates the three-layer context architecture used by ink.
    """)
    (article_path / "index.md").write_text(index_md, encoding="utf-8")

    # L0: .abstract (single-line summary ≤200 chars)
    abstract = "A sample article about the liquid blog system and its three-layer context architecture."
    (article_path / ".abstract").write_text(abstract, encoding="utf-8")

    # L1: .overview (YAML frontmatter + Markdown sections)
    overview = textwrap.dedent("""\
        ---
        title: "Liquid Blog"
        created_at: "2025-03-20T10:30:00"
        updated_at: "2025-03-20T15:00:00"
        status: "draft"
        tags: ["blog", "skills"]
        word_count: 150
        reading_time_min: 1
        related: []
        ---

        ## Summary

        A sample article about the liquid blog system. It demonstrates the
        three-layer context architecture used by ink. The system uses L0, L1,
        and L2 layers for efficient content retrieval.

        ## Key Points

        - Three-layer context architecture
        - L0: single-line abstract
        - L1: structured overview
        - L2: full Markdown content
    """)
    (article_path / ".overview").write_text(overview, encoding="utf-8")

    return article_path


@pytest.fixture
def sample_ready_article_dir(ink_dir: Path) -> Path:
    """Create a sample article with status=ready, suitable for publish tests."""
    article_path = ink_dir / "2025" / "04" / "01-ready-article"
    article_path.mkdir(parents=True)
    (article_path / "assets").mkdir()

    index_md = textwrap.dedent("""\
        ---
        title: "Ready Article"
        slug: "ready-article"
        date: "2025-04-01"
        status: "ready"
        tags: ["test"]
        ---

        # Ready Article

        This article is ready for publishing.
    """)
    (article_path / "index.md").write_text(index_md, encoding="utf-8")

    abstract = "An article ready for publishing."
    (article_path / ".abstract").write_text(abstract, encoding="utf-8")

    overview = textwrap.dedent("""\
        ---
        title: "Ready Article"
        created_at: "2025-04-01T09:00:00"
        updated_at: "2025-04-01T09:00:00"
        status: "ready"
        tags: ["test"]
        word_count: 50
        reading_time_min: 1
        related: []
        ---

        ## Summary

        An article ready for publishing.

        ## Key Points

        - Ready for publish
    """)
    (article_path / ".overview").write_text(overview, encoding="utf-8")

    return article_path
