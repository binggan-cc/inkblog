"""InkConfig: reads/writes ~/.ink/config.yaml with dot-notation access.

Config resolution order (later overrides earlier):
1. Built-in defaults
2. ~/.ink/config.yaml  (global user config)
3. .ink/config.yaml    (workspace/project config, relative to cwd)
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from ink_core.core.errors import ConfigError

logger = logging.getLogger(__name__)

GLOBAL_CONFIG_PATH = Path.home() / ".ink" / "config.yaml"

DEFAULT_CONFIG: dict = {
    "mode": "human",   # "human" | "agent"
    "agent": {
        "agent_name": "OpenClaw",
        "auto_create_daily": True,
        "default_category": "note",
        "disable_human_commands": False,
        "http_api": {
            "enabled": False,
            "port": 4242,
        },
    },
    "site": {
        "title": "My Blog",
        "author": "Anonymous",
    },
    "channels": {
        "blog": {
            "type": "static",
            "output": "./_site",
        }
    },
    "ai": {
        "provider": "none",
        "model": "",
        "api_key": "",
    },
    "search": {
        "engine": "keyword",
        "top_k": 10,
    },
    "git": {
        "auto_commit": True,
    },
    "editor": "vim",
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, returning a new dict."""
    result = _deep_copy(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


class InkConfig:
    """Manages ink configuration with layered resolution.

    Priority (highest wins):
      workspace .ink/config.yaml > ~/.ink/config.yaml > built-in defaults
    """

    def __init__(self, workspace_root: Path | None = None) -> None:
        self._workspace_root = workspace_root or Path.cwd()
        self._data: dict = {}

    @property
    def _workspace_config_path(self) -> Path:
        return self._workspace_root / ".ink" / "config.yaml"

    def load(self) -> dict:
        """Load and merge configs: defaults → global → workspace."""
        data = _deep_copy(DEFAULT_CONFIG)

        # Layer 2: global user config
        if GLOBAL_CONFIG_PATH.exists():
            data = _deep_merge(data, _load_yaml(GLOBAL_CONFIG_PATH))

        # Layer 3: workspace config (highest priority)
        ws_path = self._workspace_config_path
        if ws_path.exists():
            data = _deep_merge(data, _load_yaml(ws_path))

        self._data = data
        self.validate_mode()
        return self._data

    def validate_mode(self) -> None:
        """Raise ConfigError if 'mode' is not 'human' or 'agent'."""
        mode = self._data.get("mode", "human")
        if mode not in {"human", "agent"}:
            raise ConfigError(
                f"Invalid mode '{mode}' in config. Valid values are: human, agent."
            )

    def save(self, config: dict, *, workspace: bool = True) -> None:
        """Write config to workspace config file (default) or global."""
        path = self._workspace_config_path if workspace else GLOBAL_CONFIG_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.dump(config, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
        self._data = config

    def get(self, key: str, default: Any = None) -> Any:
        """Dot-notation key access, e.g. 'site.title'. Auto-loads if needed."""
        if not self._data:
            self.load()
        parts = key.split(".")
        node: Any = self._data
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def _ensure_dir(self) -> None:
        self._workspace_config_path.parent.mkdir(parents=True, exist_ok=True)


def _load_yaml(path: Path) -> dict:
    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(parsed, dict):
            return parsed
        logger.warning("Config file %s is not a YAML mapping, skipping.", path)
    except yaml.YAMLError as exc:
        logger.warning("Config parse error in %s: %s", path, exc)
    return {}


def _deep_copy(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _deep_copy(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_copy(v) for v in obj]
    return obj
