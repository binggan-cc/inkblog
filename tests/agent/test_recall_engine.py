"""Property tests for RecallEngine.

Property 4: Recall result schema compliance
Property 5: Recall category filter correctness
Property 6: Recall date filter correctness
Property 7: Recall limit constraint
Property 8: Scoring behaviour (exact > partial, empty query)
"""
from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from ink_core.agent import VALID_CATEGORIES, LogEntry
from ink_core.agent.recall import RecallEngine

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_date = st.builds(
    lambda y, m, d: f"{y:04d}-{m:02d}-{d:02d}",
    y=st.integers(min_value=2024, max_value=2026),
    m=st.integers(min_value=1, max_value=12),
    d=st.integers(min_value=1, max_value=28),
)

_time = st.builds(
    lambda h, m: f"{h:02d}:{m:02d}",
    h=st.integers(min_value=0, max_value=23),
    m=st.integers(min_value=0, max_value=59),
)

_category = st.sampled_from(VALID_CATEGORIES)

_content = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd", "Zs"),
        whitelist_characters=" ",
    ),
    min_size=0,
    max_size=200,
)

_log_entry = st.builds(
    LogEntry,
    date=_date,
    time=_time,
    category=_category,
    content=_content,
    source=st.just("2026/04/10-journal"),
)

_entries = st.lists(_log_entry, min_size=0, max_size=50)
_limit = st.integers(min_value=1, max_value=500)
_query = st.text(min_size=0, max_size=50)


# ---------------------------------------------------------------------------
# Property 4: Recall result schema compliance
# ---------------------------------------------------------------------------


@given(entries=_entries, query=_query, limit=_limit)
@settings(max_examples=100)
def test_property4_result_schema(
    entries: list[LogEntry], query: str, limit: int
) -> None:
    """search() always returns a list[LogEntry]; count never exceeds limit."""
    engine = RecallEngine()
    results = engine.search(entries, query, limit=limit)

    assert isinstance(results, list)
    assert len(results) <= limit
    for entry in results:
        assert isinstance(entry, LogEntry)
        assert hasattr(entry, "date")
        assert hasattr(entry, "time")
        assert hasattr(entry, "category")
        assert hasattr(entry, "content")
        assert hasattr(entry, "source")


@given(entries=_entries, limit=_limit)
@settings(max_examples=50)
def test_property4_result_is_subset_of_input(
    entries: list[LogEntry], limit: int
) -> None:
    """All returned entries come from the original input list."""
    engine = RecallEngine()
    results = engine.search(entries, "", limit=limit)
    for entry in results:
        assert entry in entries


# ---------------------------------------------------------------------------
# Property 5: Recall category filter correctness
# ---------------------------------------------------------------------------


@given(entries=_entries, category=_category, limit=_limit)
@settings(max_examples=100)
def test_property5_category_filter(
    entries: list[LogEntry], category: str, limit: int
) -> None:
    """All returned entries match the requested category (case-insensitive)."""
    engine = RecallEngine()
    results = engine.search(entries, "", category=category, limit=limit)
    for entry in results:
        assert entry.category.lower() == category.lower()


@given(entries=_entries, limit=_limit)
@settings(max_examples=50)
def test_property5_no_filter_returns_from_all(
    entries: list[LogEntry], limit: int
) -> None:
    """Without category filter, results may include entries from any category."""
    engine = RecallEngine()
    results = engine.search(entries, "", limit=limit)
    assert len(results) <= min(limit, len(entries))


# ---------------------------------------------------------------------------
# Property 6: Recall date filter correctness
# ---------------------------------------------------------------------------


@given(entries=_entries, since=_date, limit=_limit)
@settings(max_examples=100)
def test_property6_date_filter(
    entries: list[LogEntry], since: str, limit: int
) -> None:
    """All returned entries have date >= since."""
    engine = RecallEngine()
    results = engine.search(entries, "", since=since, limit=limit)
    for entry in results:
        assert entry.date >= since


@given(entries=_entries, limit=_limit)
@settings(max_examples=50)
def test_property6_no_date_filter_returns_all_dates(
    entries: list[LogEntry], limit: int
) -> None:
    """Without date filter, entries from any date may be returned."""
    engine = RecallEngine()
    results = engine.search(entries, "", limit=limit)
    assert len(results) <= limit


# ---------------------------------------------------------------------------
# Property 7: Recall limit constraint
# ---------------------------------------------------------------------------


@given(entries=_entries, limit=_limit)
@settings(max_examples=100)
def test_property7_limit_respected(
    entries: list[LogEntry], limit: int
) -> None:
    """Result count never exceeds limit, regardless of input size or query."""
    engine = RecallEngine()
    results = engine.search(entries, "", limit=limit)
    assert len(results) <= limit


@given(
    entries=st.lists(_log_entry, min_size=10, max_size=50),
    limit=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=50)
def test_property7_limit_truncates_large_input(
    entries: list[LogEntry], limit: int
) -> None:
    """When input exceeds limit, result is truncated to at most limit entries."""
    engine = RecallEngine()
    results = engine.search(entries, "", limit=limit)
    assert len(results) <= limit


# ---------------------------------------------------------------------------
# Property 8: Scoring behaviour
# ---------------------------------------------------------------------------


def test_property8_exact_match_scores_higher_than_partial() -> None:
    """Exact whole-word match scores 2; partial (substring) match scores 1."""
    engine = RecallEngine()
    exact = LogEntry("2026-01-01", "10:00", "note", "python is great", "s")
    partial = LogEntry("2026-01-01", "10:00", "note", "pythonic approach", "s")

    exact_score = engine.score_entry(exact, "python")
    partial_score = engine.score_entry(partial, "python")

    assert exact_score == 2
    assert partial_score == 1
    assert exact_score > partial_score


def test_property8_empty_query_returns_zero_score() -> None:
    """Empty query always returns score 0."""
    engine = RecallEngine()
    entry = LogEntry("2026-01-01", "10:00", "note", "some content", "s")
    assert engine.score_entry(entry, "") == 0


def test_property8_empty_query_returns_all_sorted_by_date_desc() -> None:
    """Empty query returns all entries sorted by date descending."""
    engine = RecallEngine()
    entries = [
        LogEntry("2026-01-03", "09:00", "note", "c", "s"),
        LogEntry("2026-01-01", "09:00", "note", "a", "s"),
        LogEntry("2026-01-02", "09:00", "note", "b", "s"),
    ]
    results = engine.search(entries, "", limit=10)
    dates = [e.date for e in results]
    assert dates == sorted(dates, reverse=True)


def test_property8_non_matching_query_returns_empty() -> None:
    """Query with no matches returns empty list."""
    engine = RecallEngine()
    entries = [
        LogEntry("2026-01-01", "10:00", "note", "hello world", "s"),
        LogEntry("2026-01-01", "11:00", "work", "doing tasks", "s"),
    ]
    results = engine.search(entries, "zzznomatch", limit=10)
    assert results == []


@given(entries=_entries)
@settings(max_examples=50)
def test_property8_empty_query_returns_entries_count(entries: list[LogEntry]) -> None:
    """Empty query without filters returns all entries (up to default limit)."""
    engine = RecallEngine()
    limit = 20
    results = engine.search(entries, "", limit=limit)
    assert len(results) == min(len(entries), limit)
