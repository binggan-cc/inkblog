"""Property tests for LogCommand.

Property 9: Category case normalisation
Property 10: Invalid category rejected
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from ink_core.agent import VALID_CATEGORIES
from ink_core.agent.commands.log_command import LogCommand

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent_workspace(root: Path) -> Path:
    ws = root / "ws"
    ws.mkdir(exist_ok=True)
    (ws / ".ink").mkdir(exist_ok=True)
    cfg = {
        "mode": "agent",
        "git": {"auto_commit": False},
        "agent": {"agent_name": "TestAgent", "default_category": "note"},
    }
    (ws / ".ink" / "config.yaml").write_text(yaml.dump(cfg), encoding="utf-8")
    return ws


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Mixed-case variants of each valid category
_cat_variants = [
    variant
    for cat in VALID_CATEGORIES
    for variant in [cat, cat.upper(), cat.title(), cat.capitalize()]
]

_mixed_case_category = st.sampled_from(_cat_variants)

_invalid_category = st.text(min_size=1, max_size=20).filter(
    lambda s: s.lower() not in VALID_CATEGORIES
)


# ---------------------------------------------------------------------------
# Property 9: Category case normalisation
# ---------------------------------------------------------------------------


@given(category=_mixed_case_category)
@settings(max_examples=50)
def test_property9_category_normalised_to_lowercase(category: str) -> None:
    """LogCommand stores entries with lowercase category regardless of input case."""
    with tempfile.TemporaryDirectory() as tmp:
        ws = _make_agent_workspace(Path(tmp))
        cmd = LogCommand(ws)
        result = cmd.run("test content for category normalisation", {"category": category})

    assert result.success is True
    # The message contains the formatted entry; category should appear in lowercase
    assert category.lower() in result.message


# ---------------------------------------------------------------------------
# Property 10: Invalid category rejected
# ---------------------------------------------------------------------------


@given(category=_invalid_category)
@settings(max_examples=100)
def test_property10_invalid_category_rejected(category: str) -> None:
    """LogCommand returns SkillResult(success=False) for any category not in VALID_CATEGORIES."""
    with tempfile.TemporaryDirectory() as tmp:
        ws = _make_agent_workspace(Path(tmp))
        cmd = LogCommand(ws)
        result = cmd.run("test content", {"category": category})

    assert result.success is False
    assert "category" in result.message.lower()


@pytest.mark.parametrize("valid_cat", VALID_CATEGORIES)
def test_property10_valid_categories_accepted(tmp_path: Path, valid_cat: str) -> None:
    """All VALID_CATEGORIES are accepted by LogCommand."""
    ws = _make_agent_workspace(tmp_path)
    cmd = LogCommand(ws)
    result = cmd.run("test content", {"category": valid_cat})
    assert result.success is True


def test_property10_human_mode_rejected(tmp_path: Path) -> None:
    """LogCommand returns failure when mode is not 'agent'."""
    (tmp_path / ".ink").mkdir()
    (tmp_path / ".ink" / "config.yaml").write_text(
        yaml.dump({"mode": "human"}), encoding="utf-8"
    )
    cmd = LogCommand(tmp_path)
    result = cmd.run("test content", {"category": "note"})
    assert result.success is False
    assert "agent mode" in result.message.lower()


def test_property10_missing_content_rejected(tmp_path: Path) -> None:
    """LogCommand returns failure when content is empty."""
    ws = _make_agent_workspace(tmp_path)
    cmd = LogCommand(ws)
    result = cmd.run(None, {})
    assert result.success is False


def test_property10_default_category_used_when_none_given(tmp_path: Path) -> None:
    """When no category is given, the default_category from config is used."""
    ws = _make_agent_workspace(tmp_path)
    cmd = LogCommand(ws)
    result = cmd.run("test default category", {})
    assert result.success is True
    # Default is "note" as set in _make_agent_workspace
    assert "[note]" in result.message
