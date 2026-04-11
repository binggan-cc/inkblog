"""Conversation import pipeline."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ink_core.conversation.manager import ConversationManager
from ink_core.conversation.models import Conversation
from ink_core.conversation.normalizer import ConversationNormalizer


@dataclass
class ConversationImportResult:
    """Result of a successful conversation import."""

    conversation: Conversation
    conversation_dir: Path
    raw_path: Path
    index_path: Path


class ConversationImporter:
    """Read, detect, normalize, and persist local conversation cache files."""

    SUPPORTED_FORMATS = ("json", "jsonl", "text")

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root
        self._manager = ConversationManager(workspace_root)
        self._normalizer = ConversationNormalizer()

    def import_file(
        self,
        file_path: Path,
        *,
        source: str = "unknown",
        title: str | None = None,
    ) -> ConversationImportResult:
        """Import one source cache file."""
        from ink_core.core.errors import (
            ConversationDuplicateImportError,
            ConversationFormatDetectionError,
            ConversationSourceNotFoundError,
        )

        file_path = file_path.expanduser()
        if not file_path.exists() or not file_path.is_file():
            raise ConversationSourceNotFoundError(f"Conversation source not found: {file_path}")

        content_bytes = file_path.read_bytes()
        fingerprint = hashlib.sha256(content_bytes).hexdigest()
        existing_id = self._manager.fingerprint_exists(fingerprint)
        if existing_id:
            raise ConversationDuplicateImportError(
                f"Conversation source already imported: {existing_id}"
            )

        content = content_bytes.decode("utf-8", errors="replace")
        source_format, raw_data = self._detect_and_parse(content)
        if source_format is None:
            raise ConversationFormatDetectionError(
                "Cannot detect conversation format. Supported formats: json, jsonl, text"
            )

        self._manager.ensure_dirs()
        source = self._normalizer._normalize_source(source)
        raw_rel = Path("_node") / "conversations" / "raw" / source / file_path.name
        conversation = self._normalizer.normalize(
            raw_data=raw_data,
            source_format=source_format,
            source=source,
            source_file=raw_rel.as_posix(),
            source_fingerprint=fingerprint,
            title=title,
            imported_at=datetime.now().replace(microsecond=0).isoformat(),
        )

        raw_dest = self._unique_raw_path(self._manager.raw_root / source / file_path.name)
        if raw_dest.name != file_path.name:
            conversation.source_file = raw_dest.relative_to(self._workspace_root).as_posix()

        conv_dir: Path | None = None
        try:
            raw_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, raw_dest)
            conv_dir = self._manager.save(conversation)
            self._manager.update_index(conversation)
        except Exception:
            raw_dest.unlink(missing_ok=True)
            if conv_dir is not None:
                shutil.rmtree(conv_dir, ignore_errors=True)
            raise

        return ConversationImportResult(
            conversation=conversation,
            conversation_dir=conv_dir,
            raw_path=raw_dest,
            index_path=self._manager.index_path,
        )

    def _detect_and_parse(self, content: str) -> tuple[str | None, list | dict | str | None]:
        """Detect JSON, JSONL, then plain text."""
        try:
            data = json.loads(content)
            if isinstance(data, (dict, list)):
                return "json", data
        except (TypeError, ValueError, json.JSONDecodeError):
            pass

        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if lines:
            records = []
            for line in lines:
                try:
                    records.append(json.loads(line))
                except (TypeError, ValueError, json.JSONDecodeError):
                    records = []
                    break
            if records:
                return "jsonl", records

        if content.strip():
            return "text", content
        return None, None

    def _unique_raw_path(self, raw_path: Path) -> Path:
        if not raw_path.exists():
            return raw_path
        stem = raw_path.stem
        suffix = raw_path.suffix
        for index in range(1, 1000):
            candidate = raw_path.with_name(f"{stem}-{index}{suffix}")
            if not candidate.exists():
                return candidate
        return raw_path.with_name(f"{stem}-{hashlib.sha256(str(raw_path).encode()).hexdigest()[:8]}{suffix}")
