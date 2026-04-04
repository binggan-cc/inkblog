"""Unit tests for GitManager (ink_core/git/manager.py).

Covers: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.7, 6.8
"""

import subprocess
from pathlib import Path

import pytest

from ink_core.git.manager import GitManager
from ink_core.core.errors import GitNotInitError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_git(path: Path) -> None:
    """Initialise a bare git repo (no commits) in *path*."""
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=path, check=True, capture_output=True,
    )


# ---------------------------------------------------------------------------
# is_repo
# ---------------------------------------------------------------------------


def test_is_repo_returns_false_when_no_git_dir(tmp_path):
    gm = GitManager(tmp_path)
    assert gm.is_repo() is False


def test_is_repo_returns_true_after_git_init(tmp_path):
    _init_git(tmp_path)
    gm = GitManager(tmp_path)
    assert gm.is_repo() is True


# ---------------------------------------------------------------------------
# ensure_gitignore
# ---------------------------------------------------------------------------


def test_ensure_gitignore_creates_file_when_missing(tmp_path):
    gm = GitManager(tmp_path)
    gm.ensure_gitignore()
    gitignore = tmp_path / ".gitignore"
    assert gitignore.exists()
    assert ".ink/sessions/" in gitignore.read_text()


def test_ensure_gitignore_appends_to_existing_file(tmp_path):
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.pyc\n__pycache__/\n")
    gm = GitManager(tmp_path)
    gm.ensure_gitignore()
    content = gitignore.read_text()
    assert ".ink/sessions/" in content
    assert "*.pyc" in content  # original content preserved


def test_ensure_gitignore_idempotent(tmp_path):
    gm = GitManager(tmp_path)
    gm.ensure_gitignore()
    gm.ensure_gitignore()  # second call should not duplicate the entry
    content = (tmp_path / ".gitignore").read_text()
    assert content.count(".ink/sessions/") == 1


# ---------------------------------------------------------------------------
# init_repo
# ---------------------------------------------------------------------------


def test_init_repo_creates_git_directory(tmp_path):
    # Provide git user config so commit works in CI
    subprocess.run(
        ["git", "config", "--global", "user.email", "test@example.com"],
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "--global", "user.name", "Test User"],
        capture_output=True,
    )
    gm = GitManager(tmp_path)
    result = gm.init_repo()
    assert result is True
    assert (tmp_path / ".git").exists()


def test_init_repo_adds_gitignore_entry(tmp_path):
    subprocess.run(
        ["git", "config", "--global", "user.email", "test@example.com"],
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "--global", "user.name", "Test User"],
        capture_output=True,
    )
    gm = GitManager(tmp_path)
    gm.init_repo()
    assert ".ink/sessions/" in (tmp_path / ".gitignore").read_text()


# ---------------------------------------------------------------------------
# auto_commit
# ---------------------------------------------------------------------------


def test_auto_commit_raises_when_not_a_repo(tmp_path):
    gm = GitManager(tmp_path)
    with pytest.raises(GitNotInitError):
        gm.auto_commit([tmp_path / "file.txt"], "test commit")


def test_auto_commit_commits_file(tmp_path):
    _init_git(tmp_path)
    gm = GitManager(tmp_path)
    test_file = tmp_path / "hello.txt"
    test_file.write_text("hello")
    result = gm.auto_commit([test_file], "feat: add hello")
    assert result is True
    log = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    assert "feat: add hello" in log.stdout


# ---------------------------------------------------------------------------
# aggregate_commit
# ---------------------------------------------------------------------------


def test_aggregate_commit_raises_when_not_a_repo(tmp_path):
    gm = GitManager(tmp_path)
    with pytest.raises(GitNotInitError):
        gm.aggregate_commit([tmp_path / "a.txt"], "update: slug - summary")


def test_aggregate_commit_creates_single_commit_for_multiple_files(tmp_path):
    _init_git(tmp_path)
    gm = GitManager(tmp_path)
    files = []
    for name in ("a.txt", "b.txt", "c.txt"):
        f = tmp_path / name
        f.write_text(name)
        files.append(f)
    result = gm.aggregate_commit(files, "feat: add multiple files")
    assert result is True
    log = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    lines = [l for l in log.stdout.strip().splitlines() if l]
    assert len(lines) == 1, "Expected exactly one commit"
    assert "feat: add multiple files" in lines[0]


def test_aggregate_commit_returns_true_for_empty_list(tmp_path):
    _init_git(tmp_path)
    gm = GitManager(tmp_path)
    assert gm.aggregate_commit([], "no-op") is True


# ---------------------------------------------------------------------------
# Commit message format helpers (Requirements 6.2, 6.3, 6.4)
# ---------------------------------------------------------------------------


def test_commit_message_create():
    assert GitManager.commit_message_create("my-slug") == "feat: add my-slug"


def test_commit_message_update():
    msg = GitManager.commit_message_update("my-slug", "fixed typos")
    assert msg == "update: my-slug - fixed typos"


def test_commit_message_publish_single_channel():
    msg = GitManager.commit_message_publish("my-slug", ["blog"])
    assert msg == "publish: my-slug to blog"


def test_commit_message_publish_multiple_channels():
    msg = GitManager.commit_message_publish("my-slug", ["blog", "newsletter"])
    assert msg == "publish: my-slug to blog, newsletter"
