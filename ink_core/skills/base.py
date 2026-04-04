"""Base classes and result types for the Skills layer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SkillResult:
    success: bool
    message: str
    data: dict | None = None
    changed_files: list[Path] | None = None


class Skill(ABC):
    """Abstract base class for all skills."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def version(self) -> str: ...

    @property
    @abstractmethod
    def context_requirement(self) -> str:
        """One of: "L0" | "L1" | "L2"."""
        ...

    @abstractmethod
    def execute(self, target: str | None, params: dict) -> SkillResult: ...
