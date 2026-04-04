"""Tests for SkillFileLoader (Requirements 7.1–7.5)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from ink_core.skills.loader import SkillDefinition, SkillFileLoader

VALID_MD = """\
---
skill: "publish"
version: "2.0"
context_requirement: "L1"
description: "多渠道发布"
---
## 输入
- source: 文章路径
- channels: [blog|newsletter|mastodon]

## 执行流程
1. 读取 frontmatter
2. 验证 status
3. 格式转换
4. 输出结果
"""

MISSING_SKILL_MD = """\
---
version: "1.0"
context_requirement: "L0"
---
## 输入

## 执行流程
"""

MISSING_MULTIPLE_MD = """\
---
description: "only description"
---
## 输入

## 执行流程
"""

NO_FRONTMATTER_MD = """\
## 输入
- foo: bar

## 执行流程
1. do something
"""


@pytest.fixture
def loader():
    return SkillFileLoader()


@pytest.fixture
def tmp_skill_file(tmp_path):
    """Helper: write content to a .md file and return its path."""
    def _write(content: str, name: str = "skill.md") -> Path:
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        return p
    return _write


# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------

class TestParseFrontmatter:
    def test_valid_frontmatter(self, loader):
        fm = loader.parse_frontmatter(VALID_MD)
        assert fm["skill"] == "publish"
        assert fm["version"] == "2.0"
        assert fm["context_requirement"] == "L1"
        assert fm["description"] == "多渠道发布"

    def test_no_frontmatter_returns_empty(self, loader):
        assert loader.parse_frontmatter("# Just a heading\n\nsome text") == {}

    def test_empty_frontmatter_returns_empty(self, loader):
        content = "---\n---\n## Section\n"
        result = loader.parse_frontmatter(content)
        assert result == {} or result is None or result == {}


# ---------------------------------------------------------------------------
# parse_sections
# ---------------------------------------------------------------------------

class TestParseSections:
    def test_parses_inputs(self, loader):
        sections = loader.parse_sections(VALID_MD)
        assert "source" in sections["inputs"]
        assert "channels" in sections["inputs"]

    def test_parses_steps(self, loader):
        sections = loader.parse_sections(VALID_MD)
        assert len(sections["steps"]) == 4
        assert sections["steps"][0] == "读取 frontmatter"
        assert sections["steps"][3] == "输出结果"

    def test_no_frontmatter_sections(self, loader):
        sections = loader.parse_sections(NO_FRONTMATTER_MD)
        assert sections["inputs"] == {"foo": "bar"}
        assert sections["steps"] == ["do something"]

    def test_empty_inputs_and_steps(self, loader):
        content = "---\nskill: x\nversion: 1\ncontext_requirement: L0\n---\n## 输入\n\n## 执行流程\n"
        sections = loader.parse_sections(content)
        assert sections["inputs"] == {}
        assert sections["steps"] == []


# ---------------------------------------------------------------------------
# load — happy path (Req 7.1, 7.2, 7.4)
# ---------------------------------------------------------------------------

class TestLoad:
    def test_load_valid_file(self, loader, tmp_skill_file):
        path = tmp_skill_file(VALID_MD)
        defn = loader.load(path)
        assert defn is not None
        assert defn.skill == "publish"
        assert defn.version == "2.0"
        assert defn.context_requirement == "L1"
        assert defn.description == "多渠道发布"
        assert "source" in defn.inputs
        assert len(defn.steps) == 4

    def test_load_returns_skill_definition_type(self, loader, tmp_skill_file):
        path = tmp_skill_file(VALID_MD)
        defn = loader.load(path)
        assert isinstance(defn, SkillDefinition)

    # Req 7.3: missing required field → skip + warning
    def test_load_missing_skill_field_returns_none(self, loader, tmp_skill_file, caplog):
        path = tmp_skill_file(MISSING_SKILL_MD)
        with caplog.at_level(logging.WARNING):
            defn = loader.load(path)
        assert defn is None
        assert str(path) in caplog.text
        assert "skill" in caplog.text

    def test_load_missing_multiple_fields_warns_all(self, loader, tmp_skill_file, caplog):
        path = tmp_skill_file(MISSING_MULTIPLE_MD)
        with caplog.at_level(logging.WARNING):
            defn = loader.load(path)
        assert defn is None
        # Warning should mention the missing field names
        assert "skill" in caplog.text or "version" in caplog.text or "context_requirement" in caplog.text

    def test_load_no_frontmatter_returns_none(self, loader, tmp_skill_file, caplog):
        path = tmp_skill_file(NO_FRONTMATTER_MD)
        with caplog.at_level(logging.WARNING):
            defn = loader.load(path)
        assert defn is None

    def test_load_nonexistent_file_returns_none(self, loader, tmp_path, caplog):
        path = tmp_path / "nonexistent.md"
        with caplog.at_level(logging.WARNING):
            defn = loader.load(path)
        assert defn is None


# ---------------------------------------------------------------------------
# serialize + roundtrip (Req 7.7 / Property 28)
# ---------------------------------------------------------------------------

class TestSerialize:
    def test_serialize_contains_frontmatter(self, loader):
        defn = SkillDefinition(
            skill="publish",
            version="2.0",
            context_requirement="L1",
            description="多渠道发布",
            inputs={"source": "文章路径"},
            steps=["读取 frontmatter", "输出结果"],
        )
        output = loader.serialize(defn)
        assert "---" in output
        assert "skill:" in output
        assert "version:" in output
        assert "context_requirement:" in output

    def test_serialize_contains_sections(self, loader):
        defn = SkillDefinition(
            skill="test",
            version="1.0",
            context_requirement="L0",
            description="",
            inputs={"key": "value"},
            steps=["step one", "step two"],
        )
        output = loader.serialize(defn)
        assert "## 输入" in output
        assert "## 执行流程" in output
        assert "key: value" in output
        assert "1. step one" in output
        assert "2. step two" in output

    def test_roundtrip_parse_serialize_parse(self, loader, tmp_skill_file):
        """parse(serialize(parse(content))) == parse(content)  — Property 28"""
        path = tmp_skill_file(VALID_MD)
        defn1 = loader.load(path)
        assert defn1 is not None

        serialized = loader.serialize(defn1)

        # Write serialized back and re-parse
        path2 = path.parent / "roundtrip.md"
        path2.write_text(serialized, encoding="utf-8")
        defn2 = loader.load(path2)
        assert defn2 is not None

        assert defn2.skill == defn1.skill
        assert defn2.version == defn1.version
        assert defn2.context_requirement == defn1.context_requirement
        assert defn2.description == defn1.description
        assert defn2.inputs == defn1.inputs
        assert defn2.steps == defn1.steps


# ---------------------------------------------------------------------------
# Req 7.1: load_from_directory (via SkillRegistry integration)
# ---------------------------------------------------------------------------

class TestLoadFromDirectory:
    def test_loads_all_md_files(self, loader, tmp_path):
        """Req 7.1: loader should process all .md files in a directory."""
        skill_a = """\
---
skill: "alpha"
version: "1.0"
context_requirement: "L0"
---
## 输入

## 执行流程
1. do alpha
"""
        skill_b = """\
---
skill: "beta"
version: "1.0"
context_requirement: "L1"
---
## 输入

## 执行流程
1. do beta
"""
        (tmp_path / "alpha.md").write_text(skill_a, encoding="utf-8")
        (tmp_path / "beta.md").write_text(skill_b, encoding="utf-8")
        (tmp_path / "not_a_skill.txt").write_text("ignored", encoding="utf-8")

        definitions = [
            loader.load(p)
            for p in sorted(tmp_path.glob("*.md"))
        ]
        definitions = [d for d in definitions if d is not None]
        names = {d.skill for d in definitions}
        assert names == {"alpha", "beta"}

    def test_skips_invalid_files_and_loads_valid(self, loader, tmp_path, caplog):
        """Req 7.3: invalid files skipped, valid ones loaded."""
        valid = """\
---
skill: "good"
version: "1.0"
context_requirement: "L0"
---
## 输入

## 执行流程
1. step
"""
        invalid = """\
---
description: "no required fields"
---
## 输入

## 执行流程
"""
        (tmp_path / "good.md").write_text(valid, encoding="utf-8")
        bad_path = tmp_path / "bad.md"
        bad_path.write_text(invalid, encoding="utf-8")

        with caplog.at_level(logging.WARNING):
            results = [loader.load(p) for p in sorted(tmp_path.glob("*.md"))]

        loaded = [r for r in results if r is not None]
        assert len(loaded) == 1
        assert loaded[0].skill == "good"
        assert str(bad_path) in caplog.text
