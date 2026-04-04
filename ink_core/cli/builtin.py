"""Abstract base class for built-in CLI commands."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ink_core.skills.base import SkillResult


class BuiltinCommand(ABC):
    """Built-in command interface, shares SkillResult with skills for uniform handling."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def run(self, target: str | None, params: dict) -> SkillResult: ...
