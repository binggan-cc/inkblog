"""Tests for ArticleStatus."""

from __future__ import annotations

from ink_core.core.status import ArticleStatus


def test_article_status_values() -> None:
    assert {s.value for s in ArticleStatus} == {
        "draft",
        "review",
        "ready",
        "drafted",
        "published",
        "archived",
    }


def test_article_status_helpers() -> None:
    assert ArticleStatus.is_valid("ready")
    assert not ArticleStatus.is_valid("unknown")
    assert ArticleStatus.is_publishable("ready")
    assert not ArticleStatus.is_publishable("drafted")
    assert ArticleStatus.is_syndicatable("drafted")
    assert not ArticleStatus.is_syndicatable("ready")
    assert ArticleStatus.is_visible_in_search("published")
    assert not ArticleStatus.is_visible_in_search("archived")


def test_article_status_transitions_are_closed() -> None:
    values = {s.value for s in ArticleStatus}
    transitions = ArticleStatus.valid_transitions()
    assert set(transitions) == values
    for targets in transitions.values():
        assert set(targets) <= values
