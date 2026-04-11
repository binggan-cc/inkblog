"""Tests for v0.4.1 status and CLI hardening."""

from __future__ import annotations

from pathlib import Path

from ink_core.cli.builtin import DoctorCommand, SkillsListCommand
from ink_core.cli.parser import _build_arg_parser, _intent_from_namespace
from ink_core.fs.article import ArticleManager
from ink_core.fs.index_manager import IndexManager
from ink_core.fs.markdown import parse_frontmatter
from ink_core.skills.registry import SkillRegistry


def test_parser_help_labels_command_sources() -> None:
    help_text = _build_arg_parser().format_help()
    assert "[核心]" in help_text
    assert "[技能]" in help_text
    assert "[Agent]" in help_text


def test_parser_accepts_publish_push() -> None:
    parser = _build_arg_parser()
    ns = parser.parse_args(["publish", "2025/01/01-post", "--push"])
    intent = _intent_from_namespace(ns)
    assert intent.action == "publish"
    assert intent.params["push"] is True


def test_parser_accepts_build_include_drafted() -> None:
    parser = _build_arg_parser()
    ns = parser.parse_args(["build", "--include-drafted"])
    intent = _intent_from_namespace(ns)
    assert intent.action == "build"
    assert intent.params["include_drafted"] is True


def test_parser_accepts_doctor_migrate_status() -> None:
    parser = _build_arg_parser()
    ns = parser.parse_args(["doctor", "--migrate-status"])
    intent = _intent_from_namespace(ns)
    assert intent.action == "doctor"
    assert intent.params["migrate_status"] is True


def test_skills_list_marks_builtin_and_custom(tmp_path: Path) -> None:
    skills_dir = tmp_path / ".ink" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "custom.md").write_text(
        """---
skill: custom
version: "1.0"
context_requirement: L1
description: Custom skill
---
## 执行流程
1. read_content L1
""",
        encoding="utf-8",
    )
    registry = SkillRegistry.create_with_builtins(tmp_path)
    registry.load_from_directory(skills_dir)

    result = SkillsListCommand(registry).run(None, {"subcommand": "list"})

    assert result.success
    assert "Built-in:" in result.message
    assert "Custom:" in result.message
    sources = {item["name"]: item["source"] for item in result.data["skills"]}
    assert sources["publish"] == "built-in"
    assert sources["custom"] == "custom"


def test_doctor_migrate_status_changes_unstamped_published_to_drafted(tmp_path: Path) -> None:
    manager = ArticleManager(tmp_path)
    index_mgr = IndexManager(tmp_path)
    article = manager.create("Legacy Published", date="2025-08-01")
    index_path = article.path / "index.md"
    content = index_path.read_text(encoding="utf-8").replace("status: draft", "status: published")
    index_path.write_text(content, encoding="utf-8")
    article.l2 = content
    manager.update_layers(article)
    index_mgr.update_timeline(manager.read(article.path).article)

    result = DoctorCommand(tmp_path).run(None, {"migrate_status": True})

    assert result.success
    meta, _ = parse_frontmatter(index_path.read_text(encoding="utf-8"))
    assert meta["status"] == "drafted"


def test_doctor_migrate_status_keeps_stamped_published(tmp_path: Path) -> None:
    manager = ArticleManager(tmp_path)
    article = manager.create("Real Published", date="2025-08-02")
    index_path = article.path / "index.md"
    content = index_path.read_text(encoding="utf-8").replace(
        "status: draft",
        'status: published\npublished_at: "2025-08-02T00:00:00"',
    )
    index_path.write_text(content, encoding="utf-8")

    result = DoctorCommand(tmp_path).run(None, {"migrate_status": True})

    assert result.success
    meta, _ = parse_frontmatter(index_path.read_text(encoding="utf-8"))
    assert meta["status"] == "published"
