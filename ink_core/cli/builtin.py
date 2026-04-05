"""Built-in CLI commands: New, Init, SkillsList, Rebuild."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ink_core.skills.base import SkillResult


class BuiltinCommand(ABC):
    """Built-in command interface, shares SkillResult with skills for uniform handling."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def run(self, target: str | None, params: dict) -> SkillResult: ...


# ---------------------------------------------------------------------------
# NewCommand
# ---------------------------------------------------------------------------

class NewCommand(BuiltinCommand):
    """Create a new article via ArticleManager."""

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root

    @property
    def name(self) -> str:
        return "new"

    def run(self, target: str | None, params: dict) -> SkillResult:
        from ink_core.fs.article import ArticleManager
        from ink_core.fs.index_manager import IndexManager
        from ink_core.core.errors import PathConflictError

        title = target or params.get("title", "")
        if not title:
            return SkillResult(success=False, message="Title is required for `ink new`.")

        manager = ArticleManager(self._workspace_root)
        try:
            article = manager.create(
                title,
                date=params.get("date"),
                slug=params.get("slug"),
                tags=params.get("tags"),
                template=params.get("template", "default"),
            )
        except PathConflictError as exc:
            return SkillResult(
                success=False,
                message=str(exc),
                data={"error_type": "PathConflictError"},
            )

        # Update timeline index after article creation (Requirement 2.8)
        index_mgr = IndexManager(self._workspace_root)
        index_mgr.update_timeline(article)
        timeline_path = self._workspace_root / "_index" / "timeline.json"

        changed = [
            article.path / "index.md",
            article.path / ".abstract",
            article.path / ".overview",
            article.path / "assets",
            timeline_path,
        ]
        return SkillResult(
            success=True,
            message=f"Created article: {article.canonical_id}",
            data={"canonical_id": article.canonical_id, "path": str(article.path), "slug": article.slug},
            changed_files=[p for p in changed if p.exists()],
        )


# ---------------------------------------------------------------------------
# InitCommand
# ---------------------------------------------------------------------------

class InitCommand(BuiltinCommand):
    """Initialise a Git repository in the workspace."""

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root

    @property
    def name(self) -> str:
        return "init"

    def run(self, target: str | None, params: dict) -> SkillResult:
        from ink_core.git.manager import GitManager

        git = GitManager(self._workspace_root)
        if git.is_repo():
            return SkillResult(
                success=True,
                message="Git repository already initialised.",
                changed_files=[],
            )

        ok = git.init_repo()
        if ok:
            return SkillResult(
                success=True,
                message="Git repository initialised.",
                changed_files=[self._workspace_root / ".gitignore"],
            )
        return SkillResult(
            success=False,
            message="Failed to initialise Git repository. Check stderr for details.",
        )


# ---------------------------------------------------------------------------
# SkillsListCommand
# ---------------------------------------------------------------------------

class SkillsListCommand(BuiltinCommand):
    """List all registered skills (ink skills list)."""

    def __init__(self, skill_registry: object) -> None:
        self._registry = skill_registry

    @property
    def name(self) -> str:
        return "skills"

    def run(self, target: str | None, params: dict) -> SkillResult:
        subcommand = params.get("subcommand", "list")
        if subcommand != "list":
            return SkillResult(
                success=False,
                message=f"Unknown skills subcommand: '{subcommand}'. Supported: list",
            )

        skills = self._registry.list_all()
        if not skills:
            return SkillResult(success=True, message="No skills registered.", data={"skills": []})

        lines = []
        skill_data = []
        for skill in skills:
            desc = getattr(skill, "description", "")
            lines.append(f"  {skill.name} (v{skill.version}) — {desc}")
            skill_data.append({"name": skill.name, "version": skill.version, "description": desc})

        message = "Registered skills:\n" + "\n".join(lines)
        return SkillResult(success=True, message=message, data={"skills": skill_data})


# ---------------------------------------------------------------------------
# RebuildCommand
# ---------------------------------------------------------------------------

class RebuildCommand(BuiltinCommand):
    """Rebuild all derived files (.abstract, .overview) and timeline index."""

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root

    @property
    def name(self) -> str:
        return "rebuild"

    def run(self, target: str | None, params: dict) -> SkillResult:
        from ink_core.fs.article import ArticleManager
        from ink_core.fs.index_manager import IndexManager

        manager = ArticleManager(self._workspace_root)
        index_mgr = IndexManager(self._workspace_root)

        articles = manager.list_all()
        all_changed: list[Path] = []
        errors: list[str] = []

        for article in articles:
            try:
                changed = manager.update_layers(article)
                all_changed.extend(changed)
                # Re-read to get updated l1 for timeline
                result = manager.read(article.path)
                index_mgr.update_timeline(result.article)
                timeline_path = self._workspace_root / "_index" / "timeline.json"
                if timeline_path.exists() and timeline_path not in all_changed:
                    all_changed.append(timeline_path)
            except Exception as exc:
                errors.append(f"{article.canonical_id}: {exc}")

        if errors:
            return SkillResult(
                success=False,
                message=f"Rebuild completed with {len(errors)} error(s):\n" + "\n".join(errors),
                data={"rebuilt": len(articles) - len(errors), "errors": errors},
                changed_files=all_changed,
            )

        return SkillResult(
            success=True,
            message=f"Rebuilt {len(articles)} article(s).",
            data={"rebuilt": len(articles)},
            changed_files=all_changed,
        )


# ---------------------------------------------------------------------------
# BuildCommand
# ---------------------------------------------------------------------------

class BuildCommand(BuiltinCommand):
    """Generate a static HTML site from the ink workspace (ink build)."""

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root

    @property
    def name(self) -> str:
        return "build"

    def run(self, target: str | None, params: dict) -> SkillResult:
        from ink_core.core.config import InkConfig
        from ink_core.fs.article import ArticleManager
        from ink_core.fs.index_manager import IndexManager
        from ink_core.site.builder import SiteBuilder

        include_all = bool(params.get("all", False))

        config = InkConfig()
        article_manager = ArticleManager(self._workspace_root)
        index_manager = IndexManager(self._workspace_root)

        builder = SiteBuilder(
            workspace_root=self._workspace_root,
            config=config,
            article_manager=article_manager,
            index_manager=index_manager,
        )

        try:
            result = builder.build(include_all=include_all)
        except Exception as exc:
            return SkillResult(
                success=False,
                message=f"Build failed: {exc}",
            )

        # Collect generated files for Git commit
        output_dir = result.output_dir
        changed_files = list(output_dir.rglob("*")) if output_dir.exists() else []
        changed_files = [f for f in changed_files if f.is_file()]

        return SkillResult(
            success=True,
            message=(
                f"Built {result.page_count} page(s) in {result.duration_ms}ms "
                f"→ {result.output_dir}"
            ),
            data={
                "page_count": result.page_count,
                "duration_ms": result.duration_ms,
                "output_dir": str(result.output_dir),
            },
            changed_files=changed_files,
        )
