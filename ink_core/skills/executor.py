"""Strict DSL executor for file-defined skills."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ink_core.fs.article import Article
from ink_core.skills.base import SkillResult
from ink_core.skills.loader import SkillDefinition


@dataclass
class StepContext:
    """Execution state shared across strict DSL steps."""

    target: str | None
    params: dict[str, Any]
    article: Article | None = None
    content: str = ""
    changed_files: list[Path] = field(default_factory=list)


class SkillExecutor:
    """Execute the minimal file-defined Skill DSL.

    Supported steps:
    - read_content <L0|L1|L2>
    - write_file <relative-path-under-.ink/skill-output>
    """

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root
        self._output_root = (workspace_root / ".ink" / "skill-output").resolve()

    def execute(
        self,
        definition: SkillDefinition,
        target: str | None,
        params: dict[str, Any] | None = None,
    ) -> SkillResult:
        ctx = StepContext(target=target, params=params or {})

        for step in definition.steps:
            result = self._execute_step(step, ctx)
            if result is not None:
                return result

        return SkillResult(
            success=True,
            message=f"Skill '{definition.skill}' executed.",
            data={"steps": len(definition.steps)},
            changed_files=ctx.changed_files,
        )

    def _execute_step(self, step: str, ctx: StepContext) -> SkillResult | None:
        parts = step.split(maxsplit=1)
        command = parts[0] if parts else ""
        arg = parts[1].strip() if len(parts) > 1 else ""

        if command == "read_content":
            return self._read_content(arg, ctx)
        if command == "write_file":
            return self._write_file(arg, ctx)

        return SkillResult(
            success=False,
            message=f"Unsupported skill step: {step}",
            changed_files=ctx.changed_files,
        )

    def _read_content(self, layer: str, ctx: StepContext) -> SkillResult | None:
        if layer not in {"L0", "L1", "L2"}:
            return SkillResult(success=False, message=f"Unsupported content layer: {layer}")
        if not ctx.target:
            return SkillResult(success=False, message="read_content requires a target article.")

        from ink_core.fs.article import ArticleManager

        try:
            result = ArticleManager(self._workspace_root).read_by_id(ctx.target)
        except Exception as exc:
            return SkillResult(success=False, message=str(exc), changed_files=ctx.changed_files)

        ctx.article = result.article
        if layer == "L0":
            ctx.content = result.article.l0
        elif layer == "L1":
            ctx.content = str(result.article.l1)
        else:
            ctx.content = result.article.l2
        return None

    def _write_file(self, rel_path: str, ctx: StepContext) -> SkillResult | None:
        if not rel_path:
            return SkillResult(success=False, message="write_file requires a relative path.")

        path = Path(rel_path)
        if path.is_absolute():
            return SkillResult(success=False, message="write_file rejects absolute paths.")

        target_path = (self._output_root / path).resolve()
        try:
            target_path.relative_to(self._output_root)
        except ValueError:
            return SkillResult(success=False, message="write_file path escapes .ink/skill-output.")

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(ctx.content, encoding="utf-8")
        ctx.changed_files.append(target_path)
        return None
