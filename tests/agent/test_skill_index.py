"""Property tests for SkillIndexManager and SkillSaveCommand.

Property 13: Skill upsert no duplicates
Property 14: Skill frontmatter validation
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from ink_core.agent import SkillRecord
from ink_core.agent.commands.skill_save_command import SkillSaveCommand
from ink_core.agent.skill_index import SkillIndexManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(name: str, version: str = "1.0") -> SkillRecord:
    return SkillRecord(
        name=name,
        type="external",
        source="https://example.com",
        version=version,
        install_path="",
        installed_at="2026-04-10T00:00:00+00:00",
    )


def _make_agent_workspace(root: Path) -> Path:
    ws = root / "ws"
    ws.mkdir(exist_ok=True)
    (ws / ".ink").mkdir(exist_ok=True)
    cfg = {
        "mode": "agent",
        "git": {"auto_commit": False},
        "agent": {"agent_name": "TestAgent"},
    }
    (ws / ".ink" / "config.yaml").write_text(yaml.dump(cfg), encoding="utf-8")
    return ws


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_skill_name = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="-"),
    min_size=1,
    max_size=30,
)

_version = st.text(
    alphabet=st.characters(whitelist_categories=("Nd",), whitelist_characters=".-"),
    min_size=1,
    max_size=10,
)


# ---------------------------------------------------------------------------
# Property 13: Skill upsert no duplicates
# ---------------------------------------------------------------------------


@given(name=_skill_name, versions=st.lists(_version, min_size=2, max_size=5))
@settings(max_examples=100)
def test_property13_upsert_no_duplicates(name: str, versions: list[str]) -> None:
    """After multiple upserts with same name, list_all() contains exactly one record."""
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        mgr = SkillIndexManager(ws)
        for version in versions:
            mgr.upsert(_make_record(name, version))
        all_skills = mgr.list_all()

    names = [s.name for s in all_skills]
    assert names.count(name) == 1
    # Last upserted version is preserved
    record = next(s for s in all_skills if s.name == name)
    assert record.version == versions[-1]


@given(
    skills=st.lists(
        st.builds(_make_record, name=_skill_name, version=_version),
        min_size=1,
        max_size=10,
        unique_by=lambda r: r.name,
    )
)
@settings(max_examples=50)
def test_property13_distinct_skills_all_preserved(skills: list[SkillRecord]) -> None:
    """Distinct-named skills are all preserved after sequential upserts."""
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        mgr = SkillIndexManager(ws)
        for skill in skills:
            mgr.upsert(skill)
        all_skills = mgr.list_all()

    assert len(all_skills) == len(skills)
    stored_names = {s.name for s in all_skills}
    expected_names = {s.name for s in skills}
    assert stored_names == expected_names


def test_property13_empty_index_returns_empty_list(tmp_path: Path) -> None:
    """list_all() returns [] when skills.json does not exist."""
    mgr = SkillIndexManager(tmp_path)
    assert mgr.list_all() == []


def test_property13_upsert_creates_index_file(tmp_path: Path) -> None:
    """upsert() creates _index/skills.json if absent."""
    mgr = SkillIndexManager(tmp_path)
    mgr.upsert(_make_record("my-skill"))
    index_path = tmp_path / "_index" / "skills.json"
    assert index_path.exists()


@given(name=_skill_name, v1=_version, v2=_version)
@settings(max_examples=50)
def test_property13_upsert_replaces_existing(name: str, v1: str, v2: str) -> None:
    """Upserting same name twice leaves exactly one record with the latest version."""
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        mgr = SkillIndexManager(ws)
        mgr.upsert(_make_record(name, v1))
        mgr.upsert(_make_record(name, v2))
        all_skills = mgr.list_all()

    assert len(all_skills) == 1
    assert all_skills[0].version == v2


# ---------------------------------------------------------------------------
# Property 14: Skill frontmatter validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("missing_field", ["skill", "version", "context_requirement"])
def test_property14_missing_required_field_rejected(
    tmp_path: Path, missing_field: str
) -> None:
    """SkillSaveCommand rejects files missing any required frontmatter field."""
    ws = _make_agent_workspace(tmp_path)

    full_fm: dict = {
        "skill": "my-skill",
        "version": "1.0",
        "context_requirement": "low",
    }
    del full_fm[missing_field]

    skill_file = tmp_path / "test_skill.md"
    skill_file.write_text(
        f"---\n{yaml.dump(full_fm)}---\n\n# Skill content\n", encoding="utf-8"
    )

    cmd = SkillSaveCommand(ws)
    result = cmd.run("test-skill", {"file": str(skill_file)})
    assert result.success is False
    assert missing_field in result.message


def test_property14_complete_frontmatter_accepted(tmp_path: Path) -> None:
    """SkillSaveCommand accepts files with all required frontmatter fields present."""
    ws = _make_agent_workspace(tmp_path)

    fm = {"skill": "my-skill", "version": "1.0", "context_requirement": "low"}
    skill_file = tmp_path / "my_skill.md"
    skill_file.write_text(
        f"---\n{yaml.dump(fm)}---\n\n# Skill content\n", encoding="utf-8"
    )

    result = SkillSaveCommand(ws).run("my-skill", {"file": str(skill_file)})
    assert result.success is True


def test_property14_no_frontmatter_rejected(tmp_path: Path) -> None:
    """SkillSaveCommand rejects files with no YAML frontmatter (no leading ---)."""
    ws = _make_agent_workspace(tmp_path)

    skill_file = tmp_path / "no_fm.md"
    skill_file.write_text("# No frontmatter\nsome content\n", encoding="utf-8")

    result = SkillSaveCommand(ws).run("no-fm-skill", {"file": str(skill_file)})
    assert result.success is False


def test_property14_nonexistent_file_rejected(tmp_path: Path) -> None:
    """SkillSaveCommand returns failure for a file path that does not exist."""
    ws = _make_agent_workspace(tmp_path)
    result = SkillSaveCommand(ws).run(
        "ghost-skill", {"file": str(tmp_path / "nonexistent.md")}
    )
    assert result.success is False
    assert "not found" in result.message.lower()


def test_property14_skill_copied_to_ink_skills(tmp_path: Path) -> None:
    """SkillSaveCommand copies the skill file into .ink/skills/<name>.md."""
    ws = _make_agent_workspace(tmp_path)

    fm = {"skill": "copy-test", "version": "0.1", "context_requirement": "none"}
    skill_file = tmp_path / "copy_test.md"
    skill_file.write_text(
        f"---\n{yaml.dump(fm)}---\n\n# Copy test skill\n", encoding="utf-8"
    )

    result = SkillSaveCommand(ws).run("copy-test", {"file": str(skill_file)})
    assert result.success is True
    assert (ws / ".ink" / "skills" / "copy-test.md").exists()
