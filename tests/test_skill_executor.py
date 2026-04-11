"""Tests for strict DSL SkillExecutor."""

from __future__ import annotations

from pathlib import Path

from ink_core.fs.article import ArticleManager
from ink_core.skills.executor import SkillExecutor
from ink_core.skills.loader import SkillDefinition


def _definition(*steps: str) -> SkillDefinition:
    return SkillDefinition(
        skill="test-skill",
        version="1.0",
        description="",
        context_requirement="L2",
        inputs={},
        steps=list(steps),
    )


def test_read_content_then_write_file(tmp_path: Path) -> None:
    article = ArticleManager(tmp_path).create("Executor Test", date="2025-02-01")
    result = SkillExecutor(tmp_path).execute(
        _definition("read_content L0", "write_file summaries/out.txt"),
        article.canonical_id,
        {},
    )

    out = tmp_path / ".ink" / "skill-output" / "summaries" / "out.txt"
    assert result.success
    assert out.exists()
    assert "Executor Test" in out.read_text(encoding="utf-8")


def test_unsupported_step_stops_execution(tmp_path: Path) -> None:
    article = ArticleManager(tmp_path).create("Unsupported Step", date="2025-02-02")
    result = SkillExecutor(tmp_path).execute(
        _definition("do anything", "write_file should-not-exist.txt"),
        article.canonical_id,
        {},
    )

    assert not result.success
    assert not (tmp_path / ".ink" / "skill-output" / "should-not-exist.txt").exists()


def test_missing_target_fails(tmp_path: Path) -> None:
    result = SkillExecutor(tmp_path).execute(_definition("read_content L2"), None, {})
    assert not result.success


def test_write_file_requires_path(tmp_path: Path) -> None:
    result = SkillExecutor(tmp_path).execute(_definition("write_file"), None, {})
    assert not result.success


def test_write_file_rejects_path_traversal(tmp_path: Path) -> None:
    result = SkillExecutor(tmp_path).execute(_definition("write_file ../../etc/passwd"), None, {})
    assert not result.success
    assert "escapes" in result.message


def test_write_file_rejects_absolute_path(tmp_path: Path) -> None:
    result = SkillExecutor(tmp_path).execute(_definition("write_file /tmp/foo"), None, {})
    assert not result.success
    assert "absolute" in result.message
