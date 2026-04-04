"""InkConfig: reads/writes ~/.ink/config.yaml with dot-notation access."""

import logging
from pathlib import Path
from typing import Any

import yaml

from ink_core.core.errors import ConfigError

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".ink"
CONFIG_PATH = CONFIG_DIR / "config.yaml"

DEFAULT_CONFIG: dict = {
    "site": {
        "title": "My Liquid Blog",
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


class InkConfig:
    """Manages ~/.ink/config.yaml with dot-notation key access."""

    def __init__(self, config_path: Path = CONFIG_PATH) -> None:
        self._path = config_path
        self._data: dict = {}

    def load(self) -> dict:
        """Read config file; create default if missing. Returns config dict."""
        if not self._path.exists():
            self._data = _deep_copy(DEFAULT_CONFIG)
            self._ensure_dir()
            self.save(self._data)
            return self._data

        try:
            text = self._path.read_text(encoding="utf-8")
            parsed = yaml.safe_load(text)
            if not isinstance(parsed, dict):
                raise ConfigError(f"Expected a YAML mapping, got {type(parsed).__name__}")
            self._data = parsed
        except yaml.YAMLError as exc:
            logger.warning("config.yaml parse error (%s); using default config.", exc)
            self._data = _deep_copy(DEFAULT_CONFIG)

        return self._data

    def save(self, config: dict) -> None:
        """Write config dict to file."""
        self._ensure_dir()
        self._path.write_text(
            yaml.dump(config, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
        self._data = config

    def get(self, key: str, default: Any = None) -> Any:
        """Dot-notation key access, e.g. 'search.engine'."""
        parts = key.split(".")
        node: Any = self._data
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def _ensure_dir(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)


def _deep_copy(obj: Any) -> Any:
    """Simple deep copy for plain dicts/lists/scalars (avoids importing copy)."""
    if isinstance(obj, dict):
        return {k: _deep_copy(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_copy(v) for v in obj]
    return obj
