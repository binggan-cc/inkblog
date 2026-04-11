"""Property tests for RecallCommand.

Property 1: Log round-trip
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
from ink_core.agent.commands.recall_command import RecallCommand

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

# Content safe for round-trip: no leading/trailing whitespace (stripped by parse_entries),
# no '## ' pattern which would confuse the journal parser, non-empty
_safe_content = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd", "Zs"),
        whitelist_characters=" -_",
    ),
    min_size=3,
    max_size=80,
).map(str.strip).filter(lambda s: len(s) >= 3)

_category = st.sampled_from(VALID_CATEGORIES)


# ---------------------------------------------------------------------------
# Property 1: Log round-trip
# ---------------------------------------------------------------------------


@given(content=_safe_content, category=_category)
@settings(max_examples=50)
def test_property1_log_recall_round_trip(content: str, category: str) -> None:
    """Content logged with `ink log` is retrievable with `ink recall`."""
    with tempfile.TemporaryDirectory() as tmp:
        ws = _make_agent_workspace(Path(tmp))

        # Log the entry
        log_cmd = LogCommand(ws)
        log_result = log_cmd.run(content, {"category": category})
        assert log_result.success is True, f"Log failed: {log_result.message}"

        # Recall all entries (empty query = return all)
        recall_cmd = RecallCommand(ws)
        recall_result = recall_cmd.run("", {"limit": 100})
        assert recall_result.success is True, f"Recall failed: {recall_result.message}"

    entries = recall_result.data["entries"]
    assert len(entries) >= 1
    found = any(e["content"] == content for e in entries)
    assert found, f"Logged content '{content}' not found in recall results"


@given(content=_safe_content, category=_category)
@settings(max_examples=30)
def test_property1_recall_category_matches(content: str, category: str) -> None:
    """Recalled entry for logged content has the correct (normalised) category."""
    with tempfile.TemporaryDirectory() as tmp:
        ws = _make_agent_workspace(Path(tmp))

        log_cmd = LogCommand(ws)
        log_cmd.run(content, {"category": category})

        recall_cmd = RecallCommand(ws)
        recall_result = recall_cmd.run("", {"limit": 100})

    entries = recall_result.data["entries"]
    matching = [e for e in entries if e["content"] == content]
    assert len(matching) >= 1
    assert matching[-1]["category"] == category.lower()


# ---------------------------------------------------------------------------
# Edge cases and guard tests
# ---------------------------------------------------------------------------


def test_property1_recall_human_mode_rejected(tmp_path: Path) -> None:
    """RecallCommand returns failure when mode is not 'agent'."""
    (tmp_path / ".ink").mkdir()
    (tmp_path / ".ink" / "config.yaml").write_text(
        yaml.dump({"mode": "human"}), encoding="utf-8"
    )
    cmd = RecallCommand(tmp_path)
    result = cmd.run("", {})
    assert result.success is False
    assert "agent mode" in result.message.lower()


def test_property1_recall_limit_zero_rejected(tmp_path: Path) -> None:
    """RecallCommand returns failure for limit=0."""
    ws = _make_agent_workspace(tmp_path)
    result = RecallCommand(ws).run("", {"limit": 0})
    assert result.success is False
    assert "limit" in result.message.lower()


def test_property1_recall_limit_overflow_rejected(tmp_path: Path) -> None:
    """RecallCommand returns failure for limit=501."""
    ws = _make_agent_workspace(tmp_path)
    result = RecallCommand(ws).run("", {"limit": 501})
    assert result.success is False


def test_property1_recall_limit_negative_rejected(tmp_path: Path) -> None:
    """RecallCommand returns failure for limit=-1."""
    ws = _make_agent_workspace(tmp_path)
    result = RecallCommand(ws).run("", {"limit": -1})
    assert result.success is False


def test_property1_recall_empty_workspace(tmp_path: Path) -> None:
    """RecallCommand on empty workspace returns success with empty entries list."""
    ws = _make_agent_workspace(tmp_path)
    result = RecallCommand(ws).run("", {"limit": 20})
    assert result.success is True
    assert result.data["total"] == 0
    assert result.data["entries"] == []


def test_property1_recall_data_structure(tmp_path: Path) -> None:
    """RecallCommand result.data has expected keys: query, total, entries."""
    ws = _make_agent_workspace(tmp_path)
    LogCommand(ws).run("hello world", {"category": "note"})
    result = RecallCommand(ws).run("hello", {"limit": 10})
    assert result.success is True
    assert "query" in result.data
    assert "total" in result.data
    assert "entries" in result.data
    assert isinstance(result.data["entries"], list)
