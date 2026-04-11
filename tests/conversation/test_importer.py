from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ink_core.conversation.importer import ConversationImporter
from ink_core.core.errors import (
    ConversationDuplicateImportError,
    ConversationFormatDetectionError,
    ConversationSourceNotFoundError,
)


def test_import_file_success(workspace: Path, sample_json_file: Path) -> None:
    result = ConversationImporter(workspace).import_file(sample_json_file, source="openclaw")
    assert result.conversation.conversation_id.startswith("2026/04/11-openclaw-")
    assert (result.conversation_dir / "meta.json").exists()
    assert result.raw_path.exists()
    assert result.index_path.exists()


def test_import_file_errors(workspace: Path, tmp_path: Path) -> None:
    importer = ConversationImporter(workspace)
    with pytest.raises(ConversationSourceNotFoundError):
        importer.import_file(tmp_path / "missing.json")
    empty = tmp_path / "empty.txt"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ConversationFormatDetectionError):
        importer.import_file(empty)


def test_duplicate_import_rejected(workspace: Path, sample_text_file: Path) -> None:
    importer = ConversationImporter(workspace)
    importer.import_file(sample_text_file, source="test")
    with pytest.raises(ConversationDuplicateImportError):
        importer.import_file(sample_text_file, source="test")


def test_detect_and_parse_formats(workspace: Path) -> None:
    importer = ConversationImporter(workspace)
    assert importer._detect_and_parse('{"messages": []}')[0] == "json"
    assert importer._detect_and_parse('{"role":"user","content":"a"}\n{"role":"assistant","content":"b"}\n')[0] == "jsonl"
    assert importer._detect_and_parse("plain text")[0] == "text"


@given(content=st.binary(min_size=1, max_size=100).map(lambda payload: payload.hex()))
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_fingerprint_and_duplicate_property(workspace: Path, tmp_path: Path, content: str) -> None:
    # Feature: ink-node-conversation, Property 5
    path = tmp_path / "payload.txt"
    content_bytes = content.encode("utf-8")
    path.write_bytes(content_bytes)
    importer = ConversationImporter(workspace)
    result = importer.import_file(path, source="test")
    assert result.conversation.source_fingerprint == hashlib.sha256(content_bytes).hexdigest()
    with pytest.raises(ConversationDuplicateImportError):
        importer.import_file(path, source="test")


@given(value=st.text(alphabet=st.sampled_from(list("abcdef xyz")), min_size=1, max_size=50))
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_format_detection_property(workspace: Path, value: str) -> None:
    # Feature: ink-node-conversation, Property 6
    importer = ConversationImporter(workspace)
    assert importer._detect_and_parse('{"messages": []}')[0] == "json"
    assert importer._detect_and_parse('{"role":"user","content":"hello"}\n{"role":"assistant","content":"world"}')[0] == "jsonl"
    if value.strip():
        assert importer._detect_and_parse(value)[0] == "text"
