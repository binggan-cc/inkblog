"""Skill registry: registration, discovery, and directory-based loading."""

from __future__ import annotations

import logging
from pathlib import Path

from ink_core.skills.base import Skill, SkillResult
from ink_core.skills.loader import SkillDefinition, SkillFileLoader

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# FileDefinedSkill – wraps a SkillDefinition as a Skill instance
# ---------------------------------------------------------------------------

class FileDefinedSkill(Skill):
    """A lightweight Skill wrapper around a SkillDefinition loaded from a .md file.

    File-defined skills execute through the strict DSL SkillExecutor.
    """

    def __init__(self, definition: SkillDefinition, workspace_root: Path | None = None) -> None:
        self._definition = definition
        self._workspace_root = workspace_root or Path.cwd()
        self.source = "custom"

    @property
    def name(self) -> str:
        return self._definition.skill

    @property
    def version(self) -> str:
        return self._definition.version

    @property
    def context_requirement(self) -> str:
        return self._definition.context_requirement

    @property
    def description(self) -> str:
        return self._definition.description

    def execute(self, target: str | None, params: dict) -> SkillResult:
        from ink_core.skills.executor import SkillExecutor

        return SkillExecutor(self._workspace_root).execute(self._definition, target, params)


# ---------------------------------------------------------------------------
# SkillRegistry
# ---------------------------------------------------------------------------

class SkillRegistry:
    """Skill registration and discovery.

    On initialisation the three built-in Skills (publish, analyze, search)
    are NOT auto-registered here because they require a ``workspace_root``
    argument.  Callers that want the built-ins should pass them via
    ``register()`` or use the factory helper ``create_with_builtins()``.

    File-defined Skills loaded from a directory via ``load_from_directory()``
    are wrapped as ``FileDefinedSkill`` instances and registered automatically.
    """

    def __init__(self, workspace_root: Path | None = None) -> None:
        self._workspace_root = workspace_root or Path.cwd()
        self._skills: dict[str, Skill] = {}
        self._loader = SkillFileLoader()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, skill: Skill) -> None:
        """Register a Skill instance.

        If a Skill with the same name is already registered it will be
        overwritten and a debug message will be emitted.
        """
        if skill.name in self._skills:
            logger.debug(
                "SkillRegistry: overwriting existing skill '%s'", skill.name
            )
        self._skills[skill.name] = skill
        logger.debug("SkillRegistry: registered skill '%s' v%s", skill.name, skill.version)

    def resolve(self, name: str) -> Skill | None:
        """Look up a Skill by name (exact match, case-insensitive).

        Returns the Skill instance or ``None`` if not found.
        """
        # Try exact match first
        skill = self._skills.get(name)
        if skill is not None:
            return skill
        # Fall back to case-insensitive match
        name_lower = name.lower()
        for key, skill in self._skills.items():
            if key.lower() == name_lower:
                return skill
        return None

    def list_all(self) -> list[Skill]:
        """Return all registered Skills in registration order."""
        return list(self._skills.values())

    def load_from_directory(self, path: Path) -> None:
        """Load all .md Skill definition files from *path* and register them.

        Files that are missing required frontmatter fields are skipped with a
        warning (delegated to ``SkillFileLoader``).  Files that fail to parse
        are also skipped silently (loader returns ``None``).

        Built-in Skills already registered under the same name are NOT
        overwritten by file-defined Skills; the built-in takes precedence.
        """
        if not path.exists():
            logger.debug(
                "SkillRegistry.load_from_directory: path does not exist: %s", path
            )
            return

        if not path.is_dir():
            logger.warning(
                "SkillRegistry.load_from_directory: path is not a directory: %s", path
            )
            return

        md_files = sorted(path.glob("*.md"))
        logger.debug(
            "SkillRegistry.load_from_directory: found %d .md file(s) in %s",
            len(md_files),
            path,
        )

        for md_file in md_files:
            definition = self._loader.load(md_file)
            if definition is None:
                # Loader already emitted a warning
                continue

            skill_name = definition.skill

            # Built-in skills take precedence over file-defined ones
            existing = self._skills.get(skill_name)
            if existing is not None and not isinstance(existing, FileDefinedSkill):
                logger.debug(
                    "SkillRegistry: skipping file-defined skill '%s' — "
                    "built-in already registered",
                    skill_name,
                )
                continue

            self.register(FileDefinedSkill(definition, self._workspace_root))

    # ------------------------------------------------------------------
    # Factory helper
    # ------------------------------------------------------------------

    @classmethod
    def create_with_builtins(cls, workspace_root: Path) -> "SkillRegistry":
        """Create a registry pre-populated with the three built-in Skills.

        Args:
            workspace_root: The workspace root path passed to each built-in.

        Returns:
            A new ``SkillRegistry`` with publish, analyze, and search registered.
        """
        # Import here to avoid circular imports at module level
        from ink_core.skills.publish import PublishSkill, SyndicateSkill
        from ink_core.skills.analyze import AnalyzeSkill
        from ink_core.skills.search import SearchSkill

        registry = cls(workspace_root)
        registry.register(PublishSkill(workspace_root))
        registry.register(SyndicateSkill(workspace_root))
        registry.register(AnalyzeSkill(workspace_root))
        registry.register(SearchSkill(workspace_root))
        return registry
