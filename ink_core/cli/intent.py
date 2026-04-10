"""Intent, routing data models, NLParser, and IntentRouter for the CLI layer."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ink_core.cli.builtin import BuiltinCommand
    from ink_core.skills.base import Skill


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
    target: Any  # Skill | BuiltinCommand | None
    error: str | None = None
    candidates: list[str] | None = None


# ---------------------------------------------------------------------------
# NLParser – rule-based natural language → Intent
# ---------------------------------------------------------------------------

# Each rule: (compiled_regex, action, target_group_index_or_None, params_fn)
# params_fn receives the match object and returns a dict of extra params.

def _no_params(_m: re.Match) -> dict:
    return {}


_NL_RULES: list[tuple[re.Pattern, str, int | None, Any]] = [
    # publish <target> [--channels / to <channels>]
    (
        re.compile(
            r"(?:publish|发布)\s+([^\s]+)(?:\s+(?:--channels?|to)\s+(.+))?",
            re.IGNORECASE,
        ),
        "publish",
        1,
        lambda m: {"channels": [c.strip() for c in m.group(2).split(",")] if m.group(2) else []},
    ),
    # analyze --all / 分析全库
    (
        re.compile(r"(?:analyze|分析)\s+--all", re.IGNORECASE),
        "analyze",
        None,
        lambda _m: {"all": True},
    ),
    # analyze <target>
    (
        re.compile(r"(?:analyze|分析)\s+([^\s]+)", re.IGNORECASE),
        "analyze",
        1,
        _no_params,
    ),
    # search "<query>" / search <query>
    (
        re.compile(r'(?:search|搜索)\s+"([^"]+)"', re.IGNORECASE),
        "search",
        1,
        _no_params,
    ),
    (
        re.compile(r"(?:search|搜索)\s+(.+)", re.IGNORECASE),
        "search",
        1,
        _no_params,
    ),
    # new "<title>" / create "<title>"
    (
        re.compile(r'(?:new|create|创建|新建)\s+"([^"]+)"', re.IGNORECASE),
        "new",
        1,
        _no_params,
    ),
    (
        re.compile(r"(?:new|create|创建|新建)\s+(.+)", re.IGNORECASE),
        "new",
        1,
        _no_params,
    ),
    # rebuild
    (
        re.compile(r"(?:rebuild|重建)", re.IGNORECASE),
        "rebuild",
        None,
        _no_params,
    ),
    # init
    (
        re.compile(r"(?:init|初始化)", re.IGNORECASE),
        "init",
        None,
        _no_params,
    ),
    # skills list
    (
        re.compile(r"skills\s+list", re.IGNORECASE),
        "skills",
        None,
        lambda _m: {"subcommand": "list"},
    ),
]

_AVAILABLE_ACTIONS = ["publish", "analyze", "search", "new", "rebuild", "init", "skills"]


class NLParser:
    """Natural language → Intent parser (rule-based, regex-first).

    ``parse()`` always returns a ``ParseResult``; it never returns ``None``.
    """

    def parse(self, text: str) -> ParseResult:
        """Parse a natural-language or explicit command string into a ParseResult.

        Returns:
            ParseResult with a valid Intent on success, or error + candidates on failure.
        """
        text = text.strip()
        if not text:
            return ParseResult(
                intent=None,
                error="Empty input.",
                candidates=_AVAILABLE_ACTIONS,
            )

        for pattern, action, target_group, params_fn in _NL_RULES:
            m = pattern.search(text)
            if m:
                target = m.group(target_group).strip() if target_group else None
                params = params_fn(m)
                return ParseResult(intent=Intent(action=action, target=target, params=params))

        return ParseResult(
            intent=None,
            error=f"Unrecognised input: '{text}'",
            candidates=_AVAILABLE_ACTIONS,
        )


# ---------------------------------------------------------------------------
# IntentRouter – maps Intent → Skill or BuiltinCommand
# ---------------------------------------------------------------------------

class IntentRouter:
    """Routes an Intent to the appropriate Skill or BuiltinCommand.

    Resolution order:
    1. BuiltinCommand table (checked first, no overlap with SkillRegistry)
    2. SkillRegistry

    Does not execute anything; does not return exit codes.
    """

    def __init__(
        self,
        builtins: dict[str, "BuiltinCommand"],
        skill_registry: Any,  # SkillRegistry
        workspace_root: Any = None,  # Path | None
    ) -> None:
        self._builtins = builtins
        self._registry = skill_registry
        self._workspace_root = workspace_root

    _HUMAN_COMMANDS = {"publish", "build", "search", "analyze", "rebuild"}

    def resolve(self, intent: Intent) -> RouteResult:
        """Resolve an Intent to a RouteResult.

        Returns:
            RouteResult whose ``target`` is a BuiltinCommand, Skill, or None.
        """
        action = intent.action.lower()

        # 0. Human-command guard for agent mode with disable_human_commands=true
        if action in self._HUMAN_COMMANDS and self._workspace_root is not None:
            guard = self._human_command_guard(action)
            if guard is not None:
                return guard

        # 1. Check built-in commands first
        builtin = self._builtins.get(action)
        if builtin is not None:
            return RouteResult(target=builtin)

        # 2. Check skill registry
        skill = self._registry.resolve(action)
        if skill is not None:
            return RouteResult(target=skill)

        # 3. Not found
        available = list(self._builtins.keys()) + [s.name for s in self._registry.list_all()]
        return RouteResult(
            target=None,
            error=f"Unknown command or skill: '{intent.action}'",
            candidates=available,
        )

    def _human_command_guard(self, action: str) -> "RouteResult | None":
        """Return a failing RouteResult if agent mode disables human commands, else None."""
        try:
            from ink_core.core.config import InkConfig
            from ink_core.skills.base import SkillResult
            from ink_core.cli.builtin import BuiltinCommand

            config = InkConfig(workspace_root=self._workspace_root)
            config.load()
            if (
                config.get("mode") == "agent"
                and config.get("agent.disable_human_commands") is True
            ):
                class _BlockedCommand(BuiltinCommand):
                    @property
                    def name(self) -> str:
                        return action

                    def run(self, target, params) -> SkillResult:
                        return SkillResult(
                            success=False,
                            message=f"Command '{action}' is disabled in agent mode",
                        )

                return RouteResult(target=_BlockedCommand())
        except Exception:
            pass
        return None
