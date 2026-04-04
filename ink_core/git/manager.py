"""Git operations wrapper for ink_core."""

import subprocess
import sys
from pathlib import Path

from ink_core.core.errors import GitNotInitError


class GitManager:
    """Git 操作封装"""

    GITIGNORE_ENTRY = ".ink/sessions/"

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_repo(self) -> bool:
        """检测当前目录是否为 Git 仓库（检查 .git 目录是否存在）。"""
        return (self.workspace_root / ".git").exists()

    def init_repo(self) -> bool:
        """初始化 Git 仓库并创建初始提交。

        Steps:
        1. git init
        2. ensure_gitignore()
        3. git add -A && git commit -m "chore: init ink workspace"

        Returns True on success, False on failure.
        """
        try:
            self._run(["git", "init"])
            self.ensure_gitignore()
            self._run(["git", "add", "-A"])
            self._run(["git", "commit", "-m", "chore: init ink workspace"])
            return True
        except subprocess.CalledProcessError as exc:
            self._print_git_error(exc)
            return False

    def ensure_gitignore(self) -> None:
        """确保 .gitignore 中包含 .ink/sessions/ 排除规则。"""
        gitignore_path = self.workspace_root / ".gitignore"

        if gitignore_path.exists():
            content = gitignore_path.read_text(encoding="utf-8")
            # Check if the entry is already present (exact line match)
            lines = content.splitlines()
            if self.GITIGNORE_ENTRY in lines:
                return
            # Append with a trailing newline
            separator = "\n" if content and not content.endswith("\n") else ""
            gitignore_path.write_text(
                content + separator + self.GITIGNORE_ENTRY + "\n",
                encoding="utf-8",
            )
        else:
            gitignore_path.write_text(self.GITIGNORE_ENTRY + "\n", encoding="utf-8")

    def auto_commit(self, paths: list[Path], message: str) -> bool:
        """单路径 add + commit（供内部使用）。

        Stages the given paths individually and creates a commit.
        Returns True on success, False on failure (business writes are preserved).
        """
        if not self.is_repo():
            raise GitNotInitError(
                "Not a git repository. Run `ink init` to initialise."
            )
        try:
            for p in paths:
                self._run(["git", "add", str(p)])
            self._run(["git", "commit", "-m", message])
            return True
        except subprocess.CalledProcessError as exc:
            self._print_git_error(exc)
            return False

    def aggregate_commit(self, changed_files: list[Path], message: str) -> bool:
        """单次 ink 命令的所有变更聚合为一次 commit（Requirement 6.8）。

        Stages all changed_files in a single batch and creates exactly one commit.
        Returns True on success, False on failure (business writes are preserved).
        """
        if not self.is_repo():
            raise GitNotInitError(
                "Not a git repository. Run `ink init` to initialise."
            )
        if not changed_files:
            return True  # Nothing to commit – not an error

        try:
            for p in changed_files:
                self._run(["git", "add", str(p)])
            self._run(["git", "commit", "-m", message])
            return True
        except subprocess.CalledProcessError as exc:
            self._print_git_error(exc)
            return False

    # ------------------------------------------------------------------
    # Commit message helpers (Requirement 6.2 / 6.3 / 6.4)
    # ------------------------------------------------------------------

    @staticmethod
    def commit_message_create(slug: str) -> str:
        """创建文章提交信息：feat: add <slug>"""
        return f"feat: add {slug}"

    @staticmethod
    def commit_message_update(slug: str, summary: str) -> str:
        """更新文章提交信息：update: <slug> - <summary>"""
        return f"update: {slug} - {summary}"

    @staticmethod
    def commit_message_publish(slug: str, channels: list[str]) -> str:
        """发布文章提交信息：publish: <slug> to <channels>"""
        channels_str = ", ".join(channels)
        return f"publish: {slug} to {channels_str}"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run(self, cmd: list[str]) -> subprocess.CompletedProcess:
        """Run a git command in workspace_root, raising on non-zero exit."""
        return subprocess.run(
            cmd,
            cwd=self.workspace_root,
            check=True,
            capture_output=True,
            text=True,
        )

    @staticmethod
    def _print_git_error(exc: subprocess.CalledProcessError) -> None:
        """Print a user-friendly git error message per Requirement 6.7."""
        stderr = exc.stderr.strip() if exc.stderr else ""
        stdout = exc.stdout.strip() if exc.stdout else ""
        detail = stderr or stdout or str(exc)
        print(
            f"❌ [GitError] Git command failed: {' '.join(exc.cmd)}\n"
            f"   📍 Detail: {detail}\n"
            f"   💡 建议: 请检查 Git 配置后手动执行提交（git add / git commit）",
            file=sys.stderr,
        )
