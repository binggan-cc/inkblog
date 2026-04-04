"""Tests for PublishHistoryManager."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ink_core.core.publish_history import ChannelPublishRecord, PublishHistoryManager


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def manager(workspace: Path) -> PublishHistoryManager:
    return PublishHistoryManager(workspace)


def make_record(channel: str = "blog", status: str = "success") -> ChannelPublishRecord:
    return ChannelPublishRecord(
        channel=channel,
        status=status,
        attempted_at="2025-03-20T10:30:00",
        published_at="2025-03-20T10:30:05" if status == "success" else None,
        error=None if status != "failed" else "Something went wrong",
    )


class TestRecord:
    def test_creates_file_under_correct_directory(self, manager: PublishHistoryManager, workspace: Path):
        canonical_id = "2025/03/20-liquid-blog"
        path = manager.record(
            session_id="20250320-103000-publish-a1b2c3",
            canonical_id=canonical_id,
            attempted_at="2025-03-20T10:30:00",
            records=[make_record()],
        )
        expected_dir = workspace / ".ink" / "publish-history" / "2025" / "03" / "20-liquid-blog"
        assert path.parent == expected_dir
        assert path.exists()

    def test_filename_format(self, manager: PublishHistoryManager):
        path = manager.record(
            session_id="20250320-103000-publish-a1b2c3",
            canonical_id="2025/03/20-liquid-blog",
            attempted_at="2025-03-20T10:30:00",
            records=[make_record()],
        )
        # Should match YYYYMMDD-HHMMSS-publish-<hash>.json
        name = path.name
        assert name.endswith(".json")
        parts = name[:-5].split("-")
        assert parts[2] == "publish"
        assert len(parts[3]) == 6  # short hash

    def test_file_contains_required_top_level_fields(self, manager: PublishHistoryManager):
        path = manager.record(
            session_id="sess-001",
            canonical_id="2025/03/20-liquid-blog",
            attempted_at="2025-03-20T10:30:00",
            records=[make_record()],
        )
        data = json.loads(path.read_text())
        assert "session_id" in data
        assert "canonical_id" in data
        assert "attempted_at" in data
        assert "channels" in data

    def test_file_content_matches_input(self, manager: PublishHistoryManager):
        records = [make_record("blog", "success"), make_record("newsletter", "failed")]
        path = manager.record(
            session_id="sess-abc",
            canonical_id="2025/03/20-liquid-blog",
            attempted_at="2025-03-20T10:30:00",
            records=records,
        )
        data = json.loads(path.read_text())
        assert data["session_id"] == "sess-abc"
        assert data["canonical_id"] == "2025/03/20-liquid-blog"
        assert data["attempted_at"] == "2025-03-20T10:30:00"
        assert len(data["channels"]) == 2
        assert data["channels"][0]["channel"] == "blog"
        assert data["channels"][1]["channel"] == "newsletter"

    def test_canonical_id_slash_maps_to_directory_levels(self, manager: PublishHistoryManager, workspace: Path):
        canonical_id = "2026/04/02-agenthub"
        path = manager.record(
            session_id="s1",
            canonical_id=canonical_id,
            attempted_at="2026-04-02T09:00:00",
            records=[make_record()],
        )
        expected_dir = workspace / ".ink" / "publish-history" / "2026" / "04" / "02-agenthub"
        assert path.parent == expected_dir

    def test_returns_path_object(self, manager: PublishHistoryManager):
        result = manager.record(
            session_id="s1",
            canonical_id="2025/03/20-liquid-blog",
            attempted_at="2025-03-20T10:30:00",
            records=[make_record()],
        )
        assert isinstance(result, Path)


class TestGetHistory:
    def test_returns_empty_list_when_no_records(self, manager: PublishHistoryManager):
        assert manager.get_history("2025/03/20-nonexistent") == []

    def test_returns_all_records_sorted_by_filename(self, manager: PublishHistoryManager):
        canonical_id = "2025/03/20-liquid-blog"
        manager.record("s1", canonical_id, "2025-03-20T10:00:00", [make_record()])
        manager.record("s2", canonical_id, "2025-03-20T11:00:00", [make_record()])
        manager.record("s3", canonical_id, "2025-03-20T12:00:00", [make_record()])

        history = manager.get_history(canonical_id)
        assert len(history) == 3
        # Should be sorted chronologically (by filename)
        timestamps = [h["attempted_at"] for h in history]
        assert timestamps == sorted(timestamps)

    def test_each_record_has_required_fields(self, manager: PublishHistoryManager):
        canonical_id = "2025/03/20-liquid-blog"
        manager.record("s1", canonical_id, "2025-03-20T10:00:00", [make_record()])
        history = manager.get_history(canonical_id)
        assert len(history) == 1
        record = history[0]
        for field in ("session_id", "canonical_id", "attempted_at", "channels"):
            assert field in record


class TestGetLatest:
    def test_returns_none_when_no_records(self, manager: PublishHistoryManager):
        assert manager.get_latest("2025/03/20-nonexistent") is None

    def test_returns_latest_record(self, manager: PublishHistoryManager):
        canonical_id = "2025/03/20-liquid-blog"
        manager.record("s1", canonical_id, "2025-03-20T10:00:00", [make_record()])
        manager.record("s2", canonical_id, "2025-03-20T11:00:00", [make_record()])
        manager.record("s3", canonical_id, "2025-03-20T12:00:00", [make_record()])

        latest = manager.get_latest(canonical_id)
        assert latest is not None
        assert latest["attempted_at"] == "2025-03-20T12:00:00"

    def test_returns_single_record_when_only_one(self, manager: PublishHistoryManager):
        canonical_id = "2025/03/20-liquid-blog"
        manager.record("s1", canonical_id, "2025-03-20T10:00:00", [make_record()])
        latest = manager.get_latest(canonical_id)
        assert latest is not None
        assert latest["session_id"] == "s1"
