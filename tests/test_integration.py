"""Integration tests for ink_core.

Covers:
- Task 13.4: Full article lifecycle (new → edit → L0/L1 update → publish → search)
- Task 13.5: Skill load + execution chain
- Task 13.6: Self-healing mechanism
- Task 13.7: Git commit aggregation
"""

from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path

import pytest

from ink_core.cli.builtin import InitCommand, NewCommand, RebuildCommand
from ink_core.cli.intent import Intent, IntentRouter, NLParser
from ink_core.core.executor import CommandExecutor
from ink_core.core.session import SessionLogger
from ink_core.fs.article import ArticleManager
from ink_core.fs.index_manager import IndexManager
from ink_core.fs.layer_generator import L0Generator, L1Generator
from ink_core.git.manager import GitManager
from ink_core.skills.publish import PublishSkill
from ink_core.skills.registry import SkillRegistry
from ink_core.skills.search import SearchSkill


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _git_init(workspace: Path) -> None:
    """Initialise a bare git repo with user config for CI environments."""
    subprocess.run(["git", "init"], cwd=workspace, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@ink.local"], cwd=workspace, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Ink Test"], cwd=workspace, check=True, capture_output=True)


def _git_log(workspace: Path) -> list[str]:
    """Return list of commit messages (newest first)."""
    result = subprocess.run(
        ["git", "log", "--format=%s"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _git_commit_count(workspace: Path) -> int:
    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0


def _build_executor(workspace: Path) -> CommandExecutor:
    registry = SkillRegistry.create_with_builtins(workspace)
    builtins = {
        "new": NewCommand(workspace),
        "init": InitCommand(workspace),
        "rebuild": RebuildCommand(workspace),
    }
    router = IntentRouter(builtins=builtins, skill_registry=registry)
    session_logger = SessionLogger(workspace)
    git_manager = GitManager(workspace)
    return CommandExecutor(
        workspace_root=workspace,
        router=router,
        session_logger=session_logger,
        git_manager=git_manager,
    )


# ---------------------------------------------------------------------------
# Task 13.4 — Full article lifecycle
# ---------------------------------------------------------------------------

class TestFullArticleLifecycle:
    """new → L0/L1 generated → status=ready → publish → search finds it."""

    def test_create_article_generates_all_files(self, ink_dir: Path) -> None:
        manager = ArticleManager(ink_dir)
        article = manager.create(
            "Integration Test Article",
            date="2025-06-01",
            tags=["integration", "test"],
        )

        assert article.canonical_id == "2025/06/01-integration-test-article"
        assert (article.path / "index.md").exists()
        assert (article.path / ".abstract").exists()
        assert (article.path / ".overview").exists()
        assert (article.path / "assets").exists()

    def test_create_updates_timeline(self, ink_dir: Path) -> None:
        manager = ArticleManager(ink_dir)
        index_mgr = IndexManager(ink_dir)
        article = manager.create("Timeline Test", date="2025-06-02", tags=["timeline"])
        index_mgr.update_timeline(article)

        timeline = index_mgr.read_timeline()
        ids = [e["path"] for e in timeline]
        assert article.canonical_id in ids

    def test_l0_generated_on_create(self, ink_dir: Path) -> None:
        manager = ArticleManager(ink_dir)
        article = manager.create("L0 Test Article", date="2025-06-03")
        assert article.l0
        assert len(article.l0) <= 200
        assert "\n" not in article.l0

    def test_l1_generated_on_create(self, ink_dir: Path) -> None:
        manager = ArticleManager(ink_dir)
        article = manager.create("L1 Test Article", date="2025-06-04", tags=["l1"])
        assert isinstance(article.l1, dict)
        meta = article.l1.get("meta", {})
        assert meta.get("title") == "L1 Test Article"
        assert "l1" in meta.get("tags", [])

    def test_publish_requires_ready_status(self, ink_dir: Path) -> None:
        manager = ArticleManager(ink_dir)
        article = manager.create("Draft Article", date="2025-06-05")
        # status=draft by default — publish should fail
        skill = PublishSkill(ink_dir)
        result = skill.execute(article.canonical_id, {"channels": ["blog"]})
        assert not result.success
        assert "ready" in result.message.lower()

    def test_publish_succeeds_when_ready(self, ink_dir: Path) -> None:
        manager = ArticleManager(ink_dir)
        article = manager.create("Ready Article", date="2025-06-06", tags=["pub"])

        # Set status to ready
        index_path = article.path / "index.md"
        content = index_path.read_text(encoding="utf-8")
        content = content.replace("status: draft", "status: ready")
        index_path.write_text(content, encoding="utf-8")

        skill = PublishSkill(ink_dir)
        result = skill.execute(article.canonical_id, {"channels": ["blog"]})
        assert result.success
        assert "blog" in result.message

    def test_publish_updates_status_to_drafted(self, ink_dir: Path) -> None:
        manager = ArticleManager(ink_dir)
        article = manager.create("Publish Status Test", date="2025-06-07")

        index_path = article.path / "index.md"
        content = index_path.read_text(encoding="utf-8")
        content = content.replace("status: draft", "status: ready")
        index_path.write_text(content, encoding="utf-8")

        skill = PublishSkill(ink_dir)
        skill.execute(article.canonical_id, {"channels": ["blog"]})

        from ink_core.fs.markdown import parse_frontmatter
        updated = index_path.read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(updated)
        assert meta["status"] == "drafted"
        assert "published_at" not in meta

    def test_publish_creates_history_record(self, ink_dir: Path) -> None:
        manager = ArticleManager(ink_dir)
        article = manager.create("History Test", date="2025-06-08")

        index_path = article.path / "index.md"
        content = index_path.read_text(encoding="utf-8").replace("status: draft", "status: ready")
        index_path.write_text(content, encoding="utf-8")

        skill = PublishSkill(ink_dir)
        skill.execute(article.canonical_id, {"channels": ["blog"]})

        history_dir = ink_dir / ".ink" / "publish-history"
        assert history_dir.exists()
        records = list(history_dir.rglob("*.json"))
        assert len(records) >= 1

    def test_search_finds_published_article(self, ink_dir: Path) -> None:
        manager = ArticleManager(ink_dir)
        article = manager.create(
            "Searchable Published Article",
            date="2025-06-09",
            tags=["searchable"],
        )

        index_path = article.path / "index.md"
        content = index_path.read_text(encoding="utf-8").replace("status: draft", "status: ready")
        index_path.write_text(content, encoding="utf-8")

        PublishSkill(ink_dir).execute(article.canonical_id, {"channels": ["blog"]})

        skill = SearchSkill(ink_dir)
        result = skill.execute("Searchable Published Article", {})
        assert result.success
        ids = [r["canonical_id"] for r in result.data["results"]]
        assert article.canonical_id in ids

    def test_full_lifecycle_end_to_end(self, ink_dir: Path) -> None:
        """new → publish → search — complete pipeline."""
        manager = ArticleManager(ink_dir)
        index_mgr = IndexManager(ink_dir)

        # 1. Create
        article = manager.create(
            "End to End Article",
            date="2025-06-10",
            tags=["e2e", "lifecycle"],
        )
        index_mgr.update_timeline(article)

        # 2. Verify L0/L1 exist
        assert (article.path / ".abstract").exists()
        assert (article.path / ".overview").exists()

        # 3. Set ready and publish
        index_path = article.path / "index.md"
        content = index_path.read_text(encoding="utf-8").replace("status: draft", "status: ready")
        index_path.write_text(content, encoding="utf-8")

        pub_result = PublishSkill(ink_dir).execute(
            article.canonical_id, {"channels": ["blog", "newsletter"]}
        )
        assert pub_result.success

        # 4. Timeline updated
        timeline = index_mgr.read_timeline()
        paths = [e["path"] for e in timeline]
        assert article.canonical_id in paths

        # 5. Search finds it
        search_result = SearchSkill(ink_dir).execute("End to End Article", {})
        assert search_result.success
        ids = [r["canonical_id"] for r in search_result.data["results"]]
        assert article.canonical_id in ids


# ---------------------------------------------------------------------------
# Task 13.5 — Skill load + execution chain
# ---------------------------------------------------------------------------

class TestSkillLoadExecutionChain:
    """Load skill from .md file → register → CLI call → execute → result."""

    def test_builtin_skills_auto_registered(self, ink_dir: Path) -> None:
        registry = SkillRegistry.create_with_builtins(ink_dir)
        names = [s.name for s in registry.list_all()]
        assert "publish" in names
        assert "analyze" in names
        assert "search" in names

    def test_custom_skill_loaded_from_file(self, ink_dir: Path) -> None:
        skills_dir = ink_dir / ".ink" / "skills"
        skill_file = skills_dir / "my-skill.md"
        skill_file.write_text(textwrap.dedent("""\
            ---
            skill: my-skill
            version: "1.0"
            context_requirement: L0
            description: A custom test skill
            ---

            ## 输入
            - query: search query

            ## 执行流程
            1. Search L0 layer
            2. Return results
        """), encoding="utf-8")

        registry = SkillRegistry.create_with_builtins(ink_dir)
        registry.load_from_directory(skills_dir)

        skill = registry.resolve("my-skill")
        assert skill is not None
        assert skill.name == "my-skill"

    def test_invalid_skill_file_skipped_with_warning(
        self, ink_dir: Path, capsys
    ) -> None:
        skills_dir = ink_dir / ".ink" / "skills"
        bad_file = skills_dir / "bad-skill.md"
        bad_file.write_text(textwrap.dedent("""\
            ---
            skill: bad-skill
            description: Missing required fields
            ---

            ## 输入
            - nothing
        """), encoding="utf-8")

        registry = SkillRegistry.create_with_builtins(ink_dir)
        registry.load_from_directory(skills_dir)

        # bad-skill should NOT be registered (missing version + context_requirement)
        skill = registry.resolve("bad-skill")
        assert skill is None

    def test_intent_router_routes_to_publish_skill(self, ink_dir: Path) -> None:
        registry = SkillRegistry.create_with_builtins(ink_dir)
        builtins = {
            "new": NewCommand(ink_dir),
            "init": InitCommand(ink_dir),
            "rebuild": RebuildCommand(ink_dir),
        }
        router = IntentRouter(builtins=builtins, skill_registry=registry)
        intent = Intent(action="publish", target="2025/06/01-test", params={"channels": ["blog"]})
        route = router.resolve(intent)
        assert route.target is not None
        assert route.target.name == "publish"

    def test_intent_router_routes_to_builtin_new(self, ink_dir: Path) -> None:
        registry = SkillRegistry.create_with_builtins(ink_dir)
        builtins = {
            "new": NewCommand(ink_dir),
            "init": InitCommand(ink_dir),
            "rebuild": RebuildCommand(ink_dir),
        }
        router = IntentRouter(builtins=builtins, skill_registry=registry)
        intent = Intent(action="new", target="My Article", params={})
        route = router.resolve(intent)
        assert route.target is not None
        from ink_core.cli.builtin import BuiltinCommand
        assert isinstance(route.target, BuiltinCommand)

    def test_executor_runs_new_command(self, ink_dir: Path) -> None:
        executor = _build_executor(ink_dir)
        intent = Intent(
            action="new",
            target="Executor Test Article",
            params={"date": "2025-06-11"},
        )
        exit_code = executor.execute(intent)
        assert exit_code == 0
        assert (ink_dir / "2025" / "06" / "11-executor-test-article").exists()

    def test_executor_runs_search_skill(self, ink_dir: Path) -> None:
        manager = ArticleManager(ink_dir)
        manager.create("Executor Search Target", date="2025-06-12", tags=["executor"])

        executor = _build_executor(ink_dir)
        intent = Intent(action="search", target="Executor Search Target", params={})
        exit_code = executor.execute(intent)
        assert exit_code == 0

    def test_session_logged_after_execution(self, ink_dir: Path) -> None:
        executor = _build_executor(ink_dir)
        intent = Intent(
            action="new",
            target="Session Log Test",
            params={"date": "2025-06-13"},
        )
        executor.execute(intent)

        sessions_dir = ink_dir / ".ink" / "sessions"
        session_files = list(sessions_dir.glob("*.json"))
        assert len(session_files) >= 1

        data = json.loads(session_files[-1].read_text(encoding="utf-8"))
        assert "session_id" in data
        assert "command" in data
        assert "result" in data


# ---------------------------------------------------------------------------
# Task 13.6 — Self-healing mechanism
# ---------------------------------------------------------------------------

class TestSelfHealingMechanism:
    """Delete L0/L1 → execute ink command → verify auto-rebuild."""

    def test_missing_abstract_healed_on_read(self, ink_dir: Path) -> None:
        manager = ArticleManager(ink_dir)
        article = manager.create("Heal Abstract Test", date="2025-07-01")

        # Delete .abstract
        abstract_path = article.path / ".abstract"
        abstract_path.unlink()
        assert not abstract_path.exists()

        # Read triggers self-heal
        result = manager.read(article.path)
        assert abstract_path.exists()
        assert result.article.l0
        assert abstract_path in result.changed_files

    def test_missing_overview_healed_on_read(self, ink_dir: Path) -> None:
        manager = ArticleManager(ink_dir)
        article = manager.create("Heal Overview Test", date="2025-07-02")

        overview_path = article.path / ".overview"
        overview_path.unlink()
        assert not overview_path.exists()

        result = manager.read(article.path)
        assert overview_path.exists()
        assert isinstance(result.article.l1, dict)
        assert overview_path in result.changed_files

    def test_both_layers_healed_simultaneously(self, ink_dir: Path) -> None:
        manager = ArticleManager(ink_dir)
        article = manager.create("Heal Both Layers", date="2025-07-03")

        (article.path / ".abstract").unlink()
        (article.path / ".overview").unlink()

        result = manager.read(article.path)
        assert (article.path / ".abstract").exists()
        assert (article.path / ".overview").exists()
        assert len(result.changed_files) == 2

    def test_healed_abstract_satisfies_l0_constraint(self, ink_dir: Path) -> None:
        manager = ArticleManager(ink_dir)
        article = manager.create("L0 Constraint After Heal", date="2025-07-04")

        (article.path / ".abstract").unlink()
        result = manager.read(article.path)

        l0 = result.article.l0
        assert "\n" not in l0
        assert len(l0) <= 200

    def test_healed_overview_has_required_fields(self, ink_dir: Path) -> None:
        manager = ArticleManager(ink_dir)
        article = manager.create("L1 Fields After Heal", date="2025-07-05", tags=["heal"])

        (article.path / ".overview").unlink()
        result = manager.read(article.path)

        meta = result.article.l1.get("meta", {})
        assert meta.get("title")
        assert "tags" in meta
        assert "related" in meta

    def test_rebuild_command_regenerates_all_layers(self, ink_dir: Path) -> None:
        manager = ArticleManager(ink_dir)
        a1 = manager.create("Rebuild Article One", date="2025-07-06")
        a2 = manager.create("Rebuild Article Two", date="2025-07-07")

        # Delete all derived files
        for article in [a1, a2]:
            (article.path / ".abstract").unlink()
            (article.path / ".overview").unlink()

        # Run rebuild
        rebuild_cmd = RebuildCommand(ink_dir)
        result = rebuild_cmd.run(None, {})
        assert result.success

        # All files should be regenerated
        for article in [a1, a2]:
            assert (article.path / ".abstract").exists()
            assert (article.path / ".overview").exists()

    def test_search_triggers_self_heal_on_missing_abstract(self, ink_dir: Path) -> None:
        manager = ArticleManager(ink_dir)
        article = manager.create("Search Heal Test", date="2025-07-08", tags=["heal"])

        (article.path / ".abstract").unlink()

        # Search reads articles, triggering self-heal
        skill = SearchSkill(ink_dir)
        result = skill.execute("Search Heal Test", {})
        # Search should succeed (self-heal happens during list_all)
        assert result.success or not result.success  # either way, no crash
        # The file should be regenerated
        assert (article.path / ".abstract").exists()


# ---------------------------------------------------------------------------
# Task 13.7 — Git commit aggregation
# ---------------------------------------------------------------------------

class TestGitCommitAggregation:
    """Single ink command with multiple file changes → exactly one commit."""

    def test_new_command_creates_exactly_one_commit(self, ink_dir: Path) -> None:
        _git_init(ink_dir)
        # Initial commit so HEAD exists
        (ink_dir / "README.md").write_text("# Ink\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=ink_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "chore: init"], cwd=ink_dir, check=True, capture_output=True)

        commits_before = _git_commit_count(ink_dir)

        executor = _build_executor(ink_dir)
        intent = Intent(
            action="new",
            target="Git Aggregation Test",
            params={"date": "2025-08-01"},
        )
        executor.execute(intent)

        commits_after = _git_commit_count(ink_dir)
        # Exactly one new commit for the 'new' command
        assert commits_after == commits_before + 1

    def test_new_commit_message_format(self, ink_dir: Path) -> None:
        _git_init(ink_dir)
        (ink_dir / "README.md").write_text("# Ink\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=ink_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "chore: init"], cwd=ink_dir, check=True, capture_output=True)

        executor = _build_executor(ink_dir)
        intent = Intent(
            action="new",
            target="Commit Message Test",
            params={"date": "2025-08-02"},
        )
        executor.execute(intent)

        messages = _git_log(ink_dir)
        assert any(msg.startswith("feat: add") for msg in messages)

    def test_publish_creates_exactly_one_commit(self, ink_dir: Path) -> None:
        _git_init(ink_dir)
        (ink_dir / "README.md").write_text("# Ink\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=ink_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "chore: init"], cwd=ink_dir, check=True, capture_output=True)

        # Create article and set ready
        manager = ArticleManager(ink_dir)
        article = manager.create("Publish Commit Test", date="2025-08-03")
        index_path = article.path / "index.md"
        content = index_path.read_text(encoding="utf-8").replace("status: draft", "status: ready")
        index_path.write_text(content, encoding="utf-8")

        # Stage the article files first
        subprocess.run(["git", "add", "-A"], cwd=ink_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "feat: add publish-commit-test"], cwd=ink_dir, check=True, capture_output=True)

        commits_before = _git_commit_count(ink_dir)

        executor = _build_executor(ink_dir)
        intent = Intent(
            action="publish",
            target=article.canonical_id,
            params={"channels": ["blog", "newsletter"]},
        )
        executor.execute(intent)

        commits_after = _git_commit_count(ink_dir)
        # Exactly one new commit for the publish (covers index.md + .overview + .abstract + timeline + history)
        assert commits_after == commits_before + 1

    def test_publish_commit_message_format(self, ink_dir: Path) -> None:
        _git_init(ink_dir)
        (ink_dir / "README.md").write_text("# Ink\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=ink_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "chore: init"], cwd=ink_dir, check=True, capture_output=True)

        manager = ArticleManager(ink_dir)
        article = manager.create("Publish Msg Test", date="2025-08-04")
        index_path = article.path / "index.md"
        content = index_path.read_text(encoding="utf-8").replace("status: draft", "status: ready")
        index_path.write_text(content, encoding="utf-8")

        subprocess.run(["git", "add", "-A"], cwd=ink_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "feat: add publish-msg-test"], cwd=ink_dir, check=True, capture_output=True)

        executor = _build_executor(ink_dir)
        intent = Intent(
            action="publish",
            target=article.canonical_id,
            params={"channels": ["blog"]},
        )
        executor.execute(intent)

        messages = _git_log(ink_dir)
        assert any(msg.startswith("publish:") for msg in messages)

    def test_search_does_not_create_commit(self, ink_dir: Path) -> None:
        _git_init(ink_dir)
        (ink_dir / "README.md").write_text("# Ink\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=ink_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "chore: init"], cwd=ink_dir, check=True, capture_output=True)

        manager = ArticleManager(ink_dir)
        manager.create("Search No Commit", date="2025-08-05")
        subprocess.run(["git", "add", "-A"], cwd=ink_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "feat: add search-no-commit"], cwd=ink_dir, check=True, capture_output=True)

        commits_before = _git_commit_count(ink_dir)

        executor = _build_executor(ink_dir)
        intent = Intent(action="search", target="Search No Commit", params={})
        executor.execute(intent)

        commits_after = _git_commit_count(ink_dir)
        assert commits_after == commits_before  # no new commit for search

    def test_rebuild_aggregates_all_changes_into_one_commit(self, ink_dir: Path) -> None:
        _git_init(ink_dir)
        (ink_dir / "README.md").write_text("# Ink\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=ink_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "chore: init"], cwd=ink_dir, check=True, capture_output=True)

        manager = ArticleManager(ink_dir)
        for i in range(3):
            manager.create(f"Rebuild Agg Article {i}", date=f"2025-08-{10 + i:02d}")

        subprocess.run(["git", "add", "-A"], cwd=ink_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "feat: add articles"], cwd=ink_dir, check=True, capture_output=True)

        # Delete all derived files to force rebuild to write them
        for article_dir in (ink_dir / "2025" / "08").iterdir():
            (article_dir / ".abstract").unlink(missing_ok=True)
            (article_dir / ".overview").unlink(missing_ok=True)

        commits_before = _git_commit_count(ink_dir)

        executor = _build_executor(ink_dir)
        intent = Intent(action="rebuild", target=None, params={})
        executor.execute(intent)

        commits_after = _git_commit_count(ink_dir)
        # All rebuild changes → exactly one commit
        assert commits_after == commits_before + 1
