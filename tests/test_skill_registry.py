"""Tests for SkillRegistry (Requirements 7.1, 7.6)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from ink_core.skills.base import Skill, SkillResult
from ink_core.skills.registry import FileDefinedSkill, SkillRegistry
from ink_core.skills.loader import SkillDefinition


# ---------------------------------------------------------------------------
# Minimal stub Skill for testing
# ---------------------------------------------------------------------------

class StubSkill(Skill):
    def __init__(self, name: str, version: str = "1.0", context: str = "L0") -> None:
        self._name = name
        self._version = version
        self._context = context

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    @property
    def context_requirement(self) -> str:
        return self._context

    def execute(self, target, params) -> SkillResult:
        return SkillResult(success=True, message="stub")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_SKILL_MD = """\
---
skill: "custom"
version: "1.0"
context_requirement: "L1"
description: "A custom skill"
---
## 输入
- source: path

## 执行流程
1. do something
"""

INVALID_SKILL_MD = """\
---
description: "missing required fields"
---
## 输入

## 执行流程
"""


def _write_skill_file(directory: Path, name: str, content: str) -> Path:
    p = directory / name
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# register / resolve / list_all
# ---------------------------------------------------------------------------

class TestRegisterAndResolve:
    def test_register_and_resolve_exact(self):
        registry = SkillRegistry()
        skill = StubSkill("publish")
        registry.register(skill)
        assert registry.resolve("publish") is skill

    def test_resolve_case_insensitive(self):
        registry = SkillRegistry()
        skill = StubSkill("Publish")
        registry.register(skill)
        assert registry.resolve("publish") is skill
        assert registry.resolve("PUBLISH") is skill

    def test_resolve_unknown_returns_none(self):
        registry = SkillRegistry()
        assert registry.resolve("nonexistent") is None

    def test_list_all_empty(self):
        registry = SkillRegistry()
        assert registry.list_all() == []

    def test_list_all_returns_registered_skills(self):
        registry = SkillRegistry()
        a = StubSkill("alpha")
        b = StubSkill("beta")
        registry.register(a)
        registry.register(b)
        skills = registry.list_all()
        assert len(skills) == 2
        assert a in skills
        assert b in skills

    def test_register_overwrites_same_name(self, caplog):
        registry = SkillRegistry()
        s1 = StubSkill("publish", version="1.0")
        s2 = StubSkill("publish", version="2.0")
        registry.register(s1)
        with caplog.at_level(logging.DEBUG):
            registry.register(s2)
        assert registry.resolve("publish") is s2
        assert len(registry.list_all()) == 1


# ---------------------------------------------------------------------------
# load_from_directory
# ---------------------------------------------------------------------------

class TestLoadFromDirectory:
    def test_loads_valid_md_file(self, tmp_path):
        _write_skill_file(tmp_path, "custom.md", VALID_SKILL_MD)
        registry = SkillRegistry()
        registry.load_from_directory(tmp_path)
        skill = registry.resolve("custom")
        assert skill is not None
        assert skill.name == "custom"
        assert skill.version == "1.0"
        assert skill.context_requirement == "L1"

    def test_skips_invalid_md_file(self, tmp_path, caplog):
        _write_skill_file(tmp_path, "bad.md", INVALID_SKILL_MD)
        registry = SkillRegistry()
        with caplog.at_level(logging.WARNING):
            registry.load_from_directory(tmp_path)
        assert registry.list_all() == []

    def test_loads_multiple_md_files(self, tmp_path):
        skill_a = VALID_SKILL_MD.replace('"custom"', '"alpha"')
        skill_b = VALID_SKILL_MD.replace('"custom"', '"beta"')
        _write_skill_file(tmp_path, "alpha.md", skill_a)
        _write_skill_file(tmp_path, "beta.md", skill_b)
        registry = SkillRegistry()
        registry.load_from_directory(tmp_path)
        assert len(registry.list_all()) == 2
        assert registry.resolve("alpha") is not None
        assert registry.resolve("beta") is not None

    def test_ignores_non_md_files(self, tmp_path):
        (tmp_path / "readme.txt").write_text("ignored", encoding="utf-8")
        (tmp_path / "data.json").write_text("{}", encoding="utf-8")
        _write_skill_file(tmp_path, "custom.md", VALID_SKILL_MD)
        registry = SkillRegistry()
        registry.load_from_directory(tmp_path)
        assert len(registry.list_all()) == 1

    def test_nonexistent_directory_is_noop(self, tmp_path):
        registry = SkillRegistry()
        registry.load_from_directory(tmp_path / "does_not_exist")
        assert registry.list_all() == []

    def test_builtin_takes_precedence_over_file_defined(self, tmp_path):
        """Built-in skill registered first should not be overwritten by file-defined."""
        builtin = StubSkill("custom", version="builtin")
        registry = SkillRegistry()
        registry.register(builtin)
        _write_skill_file(tmp_path, "custom.md", VALID_SKILL_MD)
        registry.load_from_directory(tmp_path)
        # Built-in should still be there
        assert registry.resolve("custom") is builtin

    def test_file_defined_skill_can_be_overwritten_by_another_file(self, tmp_path):
        """A FileDefinedSkill can be replaced by another file-defined skill."""
        registry = SkillRegistry()
        _write_skill_file(tmp_path, "custom.md", VALID_SKILL_MD)
        registry.load_from_directory(tmp_path)
        # Register a new file-defined skill with same name (simulating re-load)
        new_def = SkillDefinition(
            skill="custom", version="2.0", context_requirement="L2",
            description="updated", inputs={}, steps=[],
        )
        registry.register(FileDefinedSkill(new_def))
        assert registry.resolve("custom").version == "2.0"


# ---------------------------------------------------------------------------
# FileDefinedSkill
# ---------------------------------------------------------------------------

class TestFileDefinedSkill:
    def test_properties_from_definition(self):
        defn = SkillDefinition(
            skill="my-skill",
            version="3.0",
            context_requirement="L2",
            description="desc",
            inputs={},
            steps=[],
        )
        skill = FileDefinedSkill(defn)
        assert skill.name == "my-skill"
        assert skill.version == "3.0"
        assert skill.context_requirement == "L2"
        assert skill.description == "desc"

    def test_execute_returns_failure(self):
        defn = SkillDefinition(
            skill="stub", version="1.0", context_requirement="L0",
            description="", inputs={}, steps=[],
        )
        skill = FileDefinedSkill(defn)
        result = skill.execute(None, {})
        assert result.success is False


# ---------------------------------------------------------------------------
# create_with_builtins factory
# ---------------------------------------------------------------------------

class TestCreateWithBuiltins:
    def test_creates_registry_with_three_builtins(self, ink_dir):
        registry = SkillRegistry.create_with_builtins(ink_dir)
        assert registry.resolve("publish") is not None
        assert registry.resolve("analyze") is not None
        assert registry.resolve("search") is not None

    def test_list_all_has_three_skills(self, ink_dir):
        registry = SkillRegistry.create_with_builtins(ink_dir)
        assert len(registry.list_all()) == 3

    def test_builtins_are_not_file_defined(self, ink_dir):
        registry = SkillRegistry.create_with_builtins(ink_dir)
        for skill in registry.list_all():
            assert not isinstance(skill, FileDefinedSkill)

    def test_load_from_directory_does_not_overwrite_builtins(self, ink_dir, tmp_path):
        """Req 7.1: file-defined skills with same name as built-ins are skipped."""
        # Write a .md file claiming to be "publish"
        publish_md = VALID_SKILL_MD.replace('"custom"', '"publish"')
        _write_skill_file(tmp_path, "publish.md", publish_md)

        registry = SkillRegistry.create_with_builtins(ink_dir)
        original_publish = registry.resolve("publish")
        registry.load_from_directory(tmp_path)

        # Built-in publish should still be there
        assert registry.resolve("publish") is original_publish
        assert not isinstance(registry.resolve("publish"), FileDefinedSkill)
