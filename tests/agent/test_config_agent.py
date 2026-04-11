"""Property tests for InkConfig agent mode extension.

Property 11: Invalid mode config rejected
Property 12: Agent init config write+preserve
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from ink_core.core.config import InkConfig
from ink_core.core.errors import ConfigError

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_invalid_mode = st.text(min_size=1, max_size=20).filter(
    lambda s: s not in {"human", "agent"}
)

_agent_name = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),
        whitelist_characters="-_ ",
    ),
    min_size=1,
    max_size=30,
)


# ---------------------------------------------------------------------------
# Property 11: Invalid mode config rejected
# ---------------------------------------------------------------------------


@given(invalid_mode=_invalid_mode)
@settings(max_examples=100)
def test_property11_invalid_mode_rejected(invalid_mode: str) -> None:
    """Any mode value other than 'human' or 'agent' raises ConfigError on load."""
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "ws"
        ws.mkdir()
        ink_dir = ws / ".ink"
        ink_dir.mkdir()
        (ink_dir / "config.yaml").write_text(
            yaml.dump({"mode": invalid_mode}), encoding="utf-8"
        )
        config = InkConfig(workspace_root=ws)
        with pytest.raises(ConfigError, match="Invalid mode"):
            config.load()


@pytest.mark.parametrize("valid_mode", ["human", "agent"])
def test_property11_valid_modes_accepted(tmp_path: Path, valid_mode: str) -> None:
    """'human' and 'agent' are the only accepted mode values."""
    (tmp_path / ".ink").mkdir()
    (tmp_path / ".ink" / "config.yaml").write_text(
        yaml.dump({"mode": valid_mode}), encoding="utf-8"
    )
    config = InkConfig(workspace_root=tmp_path)
    config.load()
    assert config.get("mode") == valid_mode


def test_property11_default_mode_is_human(tmp_path: Path) -> None:
    """Default mode (no config) is 'human'."""
    (tmp_path / ".ink").mkdir()
    config = InkConfig(workspace_root=tmp_path)
    config.load()
    assert config.get("mode") == "human"


# ---------------------------------------------------------------------------
# Property 12: Agent init config write+preserve
# ---------------------------------------------------------------------------


@given(agent_name=_agent_name)
@settings(max_examples=50)
def test_property12_agent_config_write_preserve(agent_name: str) -> None:
    """After writing agent config, re-loading preserves mode and agent_name."""
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "ws"
        ws.mkdir()
        (ws / ".ink").mkdir()

        cfg_data = {
            "mode": "agent",
            "agent": {
                "agent_name": agent_name,
                "disable_human_commands": True,
            },
        }
        (ws / ".ink" / "config.yaml").write_text(yaml.dump(cfg_data), encoding="utf-8")

        config = InkConfig(workspace_root=ws)
        config.load()

        assert config.get("mode") == "agent"
        assert config.get("agent.agent_name") == agent_name
        assert config.get("agent.disable_human_commands") is True
        # DEFAULT_CONFIG defaults are preserved for unset keys
        assert config.get("agent.default_category") == "note"
        assert config.get("agent.auto_create_daily") is True


def test_property12_agent_config_http_api_defaults(tmp_path: Path) -> None:
    """Agent config http_api defaults are correctly inherited."""
    (tmp_path / ".ink").mkdir()
    (tmp_path / ".ink" / "config.yaml").write_text(
        yaml.dump({"mode": "agent"}), encoding="utf-8"
    )
    config = InkConfig(workspace_root=tmp_path)
    config.load()
    assert config.get("agent.http_api.enabled") is False
    assert config.get("agent.http_api.port") == 4242


def test_property12_agent_name_override(tmp_path: Path) -> None:
    """Custom agent_name overrides the default 'OpenClaw'."""
    (tmp_path / ".ink").mkdir()
    (tmp_path / ".ink" / "config.yaml").write_text(
        yaml.dump({"mode": "agent", "agent": {"agent_name": "MyBot"}}),
        encoding="utf-8",
    )
    config = InkConfig(workspace_root=tmp_path)
    config.load()
    assert config.get("agent.agent_name") == "MyBot"
