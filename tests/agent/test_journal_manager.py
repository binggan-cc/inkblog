"""Property tests for JournalManager.

Property 2: Log_Entry format correctness
Property 3: Daily Journal creation completeness
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from ink_core.agent import VALID_CATEGORIES, LogEntry
from ink_core.agent.journal import JournalManager
from ink_core.core.config import InkConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent_workspace(root: Path) -> tuple[Path, InkConfig]:
    ws = root / "ws"
    ws.mkdir(exist_ok=True)
    (ws / ".ink").mkdir(exist_ok=True)
    (ws / ".ink" / "config.yaml").write_text(
        yaml.dump({"mode": "agent", "agent": {"agent_name": "TestAgent"}}),
        encoding="utf-8",
    )
    config = InkConfig(workspace_root=ws)
    config.load()
    return ws, config


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_date = st.builds(
    lambda y, m, d: f"{y:04d}-{m:02d}-{d:02d}",
    y=st.integers(min_value=2020, max_value=2030),
    m=st.integers(min_value=1, max_value=12),
    d=st.integers(min_value=1, max_value=28),
)

_category = st.sampled_from(VALID_CATEGORIES)

_content = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd", "Zs", "Po"),
        whitelist_characters=" -_./",
    ),
    min_size=1,
    max_size=200,
)

# Mixed-case variants of VALID_CATEGORIES
_cat_variants = [
    variant
    for cat in VALID_CATEGORIES
    for variant in [cat, cat.upper(), cat.title(), cat.capitalize()]
]


# ---------------------------------------------------------------------------
# Property 2: Log_Entry format correctness
# ---------------------------------------------------------------------------


@given(date=_date, category=_category, content=_content)
@settings(max_examples=100)
def test_property2_log_entry_format(date: str, category: str, content: str) -> None:
    """append_entry returns a LogEntry with matching fields; time format is HH:MM."""
    with tempfile.TemporaryDirectory() as tmp:
        ws, config = _make_agent_workspace(Path(tmp))
        mgr = JournalManager(ws, config)
        entry = mgr.append_entry(date, category, content)

    # Returned LogEntry fields
    assert isinstance(entry, LogEntry)
    assert entry.date == date
    assert entry.category == category.lower()
    assert entry.content == content
    assert re.match(r"^\d{2}:\d{2}$", entry.time)

    # Source canonical_id format: YYYY/MM/DD-journal
    year, month, day = date.split("-")
    assert entry.source == f"{year}/{month}/{day}-journal"


@given(category=st.sampled_from(_cat_variants))
@settings(max_examples=50)
def test_property2_category_normalised_to_lowercase(category: str) -> None:
    """Category is always stored in lowercase regardless of input case."""
    with tempfile.TemporaryDirectory() as tmp:
        ws, config = _make_agent_workspace(Path(tmp))
        mgr = JournalManager(ws, config)
        entry = mgr.append_entry("2026-04-10", category, "test content")

    assert entry.category == category.lower()


@given(date=_date, category=_category, content=_content)
@settings(max_examples=50)
def test_property2_parse_entries_round_trip(
    date: str, category: str, content: str
) -> None:
    """parse_entries round-trips appended entries: category and content are preserved."""
    with tempfile.TemporaryDirectory() as tmp:
        ws, config = _make_agent_workspace(Path(tmp))
        mgr = JournalManager(ws, config)
        appended = mgr.append_entry(date, category, content)
        journal_path, _ = mgr.get_or_create_journal(date)
        entries = mgr.parse_entries(journal_path)

    assert len(entries) >= 1
    last = entries[-1]
    assert last.date == date
    assert last.category == category.lower()
    # parse_entries strips leading/trailing whitespace from content
    assert last.content == content.strip()
    assert last.time == appended.time


# ---------------------------------------------------------------------------
# Property 3: Daily Journal creation completeness
# ---------------------------------------------------------------------------


@given(date=_date)
@settings(max_examples=50)
def test_property3_journal_created_at_expected_path(date: str) -> None:
    """get_or_create_journal creates the file at YYYY/MM/DD-journal/index.md."""
    with tempfile.TemporaryDirectory() as tmp:
        ws, config = _make_agent_workspace(Path(tmp))
        mgr = JournalManager(ws, config)
        journal_path, was_created = mgr.get_or_create_journal(date)

        year, month, day = date.split("-")
        assert journal_path.name == "index.md"
        assert journal_path.parent.name == f"{day}-journal"
        assert journal_path.parent.parent.name == month
        assert journal_path.parent.parent.parent.name == year
        assert journal_path.exists()
        assert was_created is True


@given(date=_date)
@settings(max_examples=50)
def test_property3_journal_frontmatter_complete(date: str) -> None:
    """Created journal has required frontmatter: status=draft, tags=[journal, agent], date."""
    with tempfile.TemporaryDirectory() as tmp:
        ws, config = _make_agent_workspace(Path(tmp))
        mgr = JournalManager(ws, config)
        journal_path, _ = mgr.get_or_create_journal(date)
        content = journal_path.read_text(encoding="utf-8")

        assert content.startswith("---")
        end = content.find("---", 3)
        assert end != -1, "No closing --- in frontmatter"
        fm = yaml.safe_load(content[3:end])

        assert fm["status"] == "draft"
        assert "journal" in fm["tags"]
        assert "agent" in fm["tags"]
        # YAML parses YYYY-MM-DD as datetime.date; normalise to string for comparison
        assert str(fm["date"]) == date
        assert "title" in fm
        assert "agent" in fm


@given(date=_date)
@settings(max_examples=50)
def test_property3_journal_idempotent(date: str) -> None:
    """Calling get_or_create_journal twice returns was_created=False the second time."""
    with tempfile.TemporaryDirectory() as tmp:
        ws, config = _make_agent_workspace(Path(tmp))
        mgr = JournalManager(ws, config)
        _, was_created_1 = mgr.get_or_create_journal(date)
        _, was_created_2 = mgr.get_or_create_journal(date)

    assert was_created_1 is True
    assert was_created_2 is False


def test_property3_layer_files_created(tmp_path: Path) -> None:
    """Creating a journal also generates .abstract and .overview layer files."""
    ws, config = _make_agent_workspace(tmp_path)
    mgr = JournalManager(ws, config)
    journal_path, _ = mgr.get_or_create_journal("2026-04-10")

    assert (journal_path.parent / ".abstract").exists()
    assert (journal_path.parent / ".overview").exists()
