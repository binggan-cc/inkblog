"""Domain exceptions for ink_core."""


class PathNotFoundError(Exception):
    """Target article path does not exist."""


class PathConflictError(Exception):
    """Target path already exists (ink new conflict)."""


class InvalidStatusError(Exception):
    """Article status is not valid for the requested operation."""


class UnsupportedChannelError(Exception):
    """Channel name is not in the supported list."""


class TemplateRenderError(Exception):
    """Channel format template rendering failed."""


class ChannelOutputError(Exception):
    """Local output directory write failed."""


class AmbiguousLinkError(Exception):
    """[[wiki-link]] matches multiple candidate articles."""


class UnresolvedLinkError(Exception):
    """[[wiki-link]] did not match any article."""


class SkillNotFoundError(Exception):
    """Intent could not be matched to any skill."""


class SkillLoadError(Exception):
    """Skill file frontmatter is missing required fields."""


class GitNotInitError(Exception):
    """Write operation attempted on a non-Git repository."""


class LayerCorruptError(Exception):
    """L0/L1 file is corrupted or missing."""


class ConfigError(Exception):
    """config.yaml format error."""


class AgentModeError(Exception):
    """Command requires agent mode but current mode is different."""
