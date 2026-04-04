"""Intent and routing data models for the CLI layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Intent:
    action: str
    target: str | None
    params: dict = field(default_factory=dict)


@dataclass
class ParseResult:
    intent: Intent | None
    error: str | None = None
    candidates: list[str] | None = None


@dataclass
class RouteResult:
    target: Any
    error: str | None = None
    candidates: list[str] | None = None
