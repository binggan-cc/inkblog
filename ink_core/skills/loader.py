"""Skill definition data model and file loader."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SkillDefinition:
    skill: str
    version: str
    description: str
    context_requirement: str
    inputs: dict = field(default_factory=dict)
    steps: list[str] = field(default_factory=list)
