"""Skill definition data model and file loader."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ("skill", "version", "context_requirement")


@dataclass
class SkillDefinition:
    skill: str
    version: str
    description: str
    context_requirement: str
    inputs: dict = field(default_factory=dict)
    steps: list[str] = field(default_factory=list)


class SkillFileLoader:
    """从 .ink/skills/*.md 加载 Skill 定义"""

    def load(self, path: Path) -> SkillDefinition | None:
        """解析 .md 文件 frontmatter + 章节内容。

        缺少必填字段（skill、version、context_requirement）时跳过并输出警告。
        """
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning("SkillFileLoader: cannot read %s: %s", path, e)
            return None

        frontmatter = self.parse_frontmatter(content)

        missing = [f for f in REQUIRED_FIELDS if not frontmatter.get(f)]
        if missing:
            logger.warning(
                "SkillFileLoader: skipping %s — missing required fields: %s",
                path,
                ", ".join(missing),
            )
            return None

        sections = self.parse_sections(content)

        return SkillDefinition(
            skill=frontmatter["skill"],
            version=str(frontmatter["version"]),
            description=frontmatter.get("description", ""),
            context_requirement=frontmatter["context_requirement"],
            inputs=sections.get("inputs", {}),
            steps=sections.get("steps", []),
        )

    def parse_frontmatter(self, content: str) -> dict:
        """提取 YAML frontmatter（--- ... --- 块）。"""
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if not match:
            return {}
        try:
            data = yaml.safe_load(match.group(1))
            return data if isinstance(data, dict) else {}
        except yaml.YAMLError:
            return {}

    def parse_sections(self, content: str) -> dict:
        """提取"输入"和"执行流程"章节内容。

        Returns a dict with keys:
          - "inputs": dict parsed from bullet list under ## 输入
          - "steps": list[str] parsed from numbered list under ## 执行流程
        """
        # Strip frontmatter first
        body = re.sub(r"^---\s*\n.*?\n---\s*\n", "", content, count=1, flags=re.DOTALL)

        result: dict = {"inputs": {}, "steps": []}

        # Split into sections by ## headings
        sections = re.split(r"^##\s+", body, flags=re.MULTILINE)
        for section in sections:
            if not section.strip():
                continue
            lines = section.splitlines()
            heading = lines[0].strip()
            body_lines = lines[1:]

            if heading == "输入":
                result["inputs"] = _parse_bullet_dict(body_lines)
            elif heading == "执行流程":
                result["steps"] = _parse_numbered_list(body_lines)

        return result

    def serialize(self, definition: SkillDefinition) -> str:
        """将 SkillDefinition 序列化回 Markdown 格式。"""
        fm_data: dict = {
            "skill": definition.skill,
            "version": definition.version,
            "context_requirement": definition.context_requirement,
        }
        if definition.description:
            fm_data["description"] = definition.description

        frontmatter = yaml.dump(fm_data, allow_unicode=True, default_flow_style=False).rstrip()
        lines = [f"---\n{frontmatter}\n---\n"]

        # 输入 section
        lines.append("\n## 输入\n")
        if definition.inputs:
            for key, value in definition.inputs.items():
                lines.append(f"- {key}: {value}\n")
        else:
            lines.append("\n")

        # 执行流程 section
        lines.append("\n## 执行流程\n")
        if definition.steps:
            for i, step in enumerate(definition.steps, 1):
                lines.append(f"{i}. {step}\n")
        else:
            lines.append("\n")

        return "".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_bullet_dict(lines: list[str]) -> dict:
    """Parse lines like '- key: value' into a dict."""
    result = {}
    for line in lines:
        m = re.match(r"^\s*-\s+(\S+?):\s*(.*)", line)
        if m:
            result[m.group(1)] = m.group(2).strip()
    return result


def _parse_numbered_list(lines: list[str]) -> list[str]:
    """Parse lines like '1. step text' into a list of strings."""
    result = []
    for line in lines:
        m = re.match(r"^\s*\d+\.\s+(.*)", line)
        if m:
            result.append(m.group(1).strip())
    return result
