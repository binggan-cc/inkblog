"""Publish history data models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChannelPublishRecord:
    channel: str
    status: str              # "success" | "draft_saved" | "failed"
    attempted_at: str        # ISO timestamp
    published_at: str | None = None
    error: str | None = None
