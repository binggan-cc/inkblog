"""Execution context and CommandExecutor for a single ink command."""

from __future__ import annotations

import hashlib
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ink_core.cli.intent import Intent, IntentRouter


# Commands that trigger an aggregate Git commit after execution
_WRITE_COMMANDS = {"new", "init", "rebuild", "publish", "build"}


@dataclass
class ExecutionContext:
    session_id: str          # Format: YYYYMMDD-HHMMSS-<action>-<hash>
    command: str
    target: str | None       # Canonical ID, reserved value, or None
    params: dict
    changed_files: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)


def _make_session_id(action: str, started_at: datetime) -> str:
    ts = started_at.strftime("%Y%m%d-%H%M%S")
    short_hash = hashlib.md5(f"{ts}-{action}".encode()).hexdigest()[:6]
    return f"{ts}-{action}-{short_hash}"


class CommandExecutor:
    """Transaction coordinator for a single ink command.

    Responsibilities:
    1. Create ExecutionContext (with session_id)
    2. Route via IntentRouter → BuiltinCommand or Skill
    3. Execute and accumulate changed_files
    4. Write Session record via SessionLogger
    5. Trigger aggregate Git commit for write commands
    6. Format and print success/failure output; return exit code
    """

    def __init__(
        self,
        workspace_root: Path,
        router: "IntentRouter",
        session_logger: Any,   # SessionLogger
        git_manager: Any,      # GitManager | None
    ) -> None:
        self._workspace_root = workspace_root
        self._router = router
        self._session_logger = session_logger
        self._git = git_manager

    def execute(self, intent: "Intent") -> int:
        """Execute an intent and return an exit code (0 = success, 1 = failure)."""
        started_at = datetime.now()
        session_id = _make_session_id(intent.action, started_at)

        ctx = ExecutionContext(
            session_id=session_id,
            command=intent.action,
            target=intent.target,
            params=intent.params,
            started_at=started_at,
        )

        # --- Route ---
        route = self._router.resolve(intent)
        if route.target is None:
            candidates = route.candidates or []
            self._print_failure(
                error_type="UnknownCommand",
                location=f"command '{intent.action}'",
                suggestion=(
                    "Available commands: " + ", ".join(candidates)
                    if candidates
                    else "Run `ink skills list` to see available skills."
                ),
            )
            self._log_session(ctx, "failed", started_at)
            return 1

        # --- Execute ---
        try:
            from ink_core.cli.builtin import BuiltinCommand
            from ink_core.skills.base import Skill

            if isinstance(route.target, BuiltinCommand):
                result = route.target.run(intent.target, intent.params)
            elif isinstance(route.target, Skill):
                result = route.target.execute(intent.target, intent.params)
            else:
                self._print_failure(
                    error_type="InternalError",
                    location=f"router returned unexpected target type: {type(route.target)}",
                    suggestion="This is a bug — please report it.",
                )
                self._log_session(ctx, "failed", started_at)
                return 1
        except Exception as exc:
            self._print_failure(
                error_type=type(exc).__name__,
                location=f"command '{intent.action}'",
                suggestion=str(exc),
            )
            self._log_session(ctx, "failed", started_at)
            return 1

        # --- Accumulate changed_files ---
        if result.changed_files:
            ctx.changed_files.extend(result.changed_files)

        duration_ms = int((datetime.now() - started_at).total_seconds() * 1000)

        # --- Session log ---
        outcome = "success" if result.success else "failed"
        self._log_session(ctx, outcome, started_at, duration_ms)

        # --- Git commit (write commands only) ---
        if result.success and intent.action.lower() in _WRITE_COMMANDS:
            self._maybe_commit(ctx, intent, result)

        # --- Output ---
        if result.success:
            self._print_success(
                action=intent.action,
                target=intent.target,
                message=result.message,
                duration_ms=duration_ms,
            )
            return 0
        else:
            self._print_failure(
                error_type="ExecutionError",
                location=f"command '{intent.action}'" + (f" on '{intent.target}'" if intent.target else ""),
                suggestion=result.message,
            )
            return 1

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log_session(
        self,
        ctx: ExecutionContext,
        result: str,
        started_at: datetime,
        duration_ms: int | None = None,
    ) -> None:
        if self._session_logger is None:
            return
        if duration_ms is None:
            duration_ms = int((datetime.now() - started_at).total_seconds() * 1000)
        try:
            self._session_logger.log(ctx, result, duration_ms)
        except Exception:
            pass  # Session logging failure must not break the command

    def _maybe_commit(self, ctx: ExecutionContext, intent: "Intent", result: Any = None) -> None:
        if self._git is None:
            return
        try:
            if not self._git.is_repo():
                return
            if not ctx.changed_files:
                return
            message = self._commit_message(intent, result)
            ok = self._git.aggregate_commit(ctx.changed_files, message)
            if not ok:
                print(
                    "⚠️  Git commit failed — business writes preserved. "
                    "Run `git add / git commit` manually.",
                    file=sys.stderr,
                )
        except Exception as exc:
            print(f"⚠️  Git error: {exc}", file=sys.stderr)

    def _commit_message(self, intent: "Intent", result: Any = None) -> str:
        from ink_core.git.manager import GitManager

        action = intent.action.lower()
        target = intent.target or ""

        # For 'new' command, use the actual slug from result.data if available
        if action == "new" and result is not None and result.data:
            slug = result.data.get("slug") or result.data.get("canonical_id", "").split("/")[-1] or target
        else:
            # Extract slug from canonical_id (last path component after last /)
            slug = target.split("/")[-1] if target else "workspace"

        if action == "new":
            return GitManager.commit_message_create(slug)
        if action == "publish":
            channels = intent.params.get("channels", [])
            return GitManager.commit_message_publish(slug, channels)
        if action in ("rebuild", "init"):
            return f"chore: {action}"
        if action == "build":
            return "build: regenerate static site"
        return f"update: {slug}"

    @staticmethod
    def _print_success(action: str, target: str | None, message: str, duration_ms: int) -> None:
        target_str = f" → {target}" if target else ""
        print(f"✅ [{action}{target_str}] {message} ({duration_ms}ms)")

    @staticmethod
    def _print_failure(error_type: str, location: str, suggestion: str) -> None:
        print(
            f"❌ [{error_type}] {location}\n"
            f"   💡 建议: {suggestion}",
            file=sys.stderr,
        )
