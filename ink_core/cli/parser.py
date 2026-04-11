"""CLI entry point for the `ink` command."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _workspace_root() -> Path:
    """Return the workspace root (current working directory)."""
    return Path.cwd()


def _build_executor(workspace_root: Path):
    """Wire up all components and return a CommandExecutor."""
    from ink_core.agent.commands.log_command import LogCommand
    from ink_core.agent.commands.recall_command import RecallCommand
    from ink_core.agent.commands.serve_command import ServeCommand
    from ink_core.agent.commands.skill_list_command import SkillListCommand
    from ink_core.agent.commands.skill_record_command import SkillRecordCommand
    from ink_core.agent.commands.skill_save_command import SkillSaveCommand
    from ink_core.cli.builtin import BuildCommand, DoctorCommand, InitCommand, NewCommand, RebuildCommand, SkillsListCommand
    from ink_core.cli.intent import IntentRouter
    from ink_core.conversation.commands import (
        BuildConversationsCommand,
        ImportConversationCommand,
        LinkSourceCommand,
        RenderConversationCommand,
    )
    from ink_core.core.executor import CommandExecutor
    from ink_core.core.session import SessionLogger
    from ink_core.git.manager import GitManager
    from ink_core.skills.registry import SkillRegistry

    # Registry with built-in skills
    registry = SkillRegistry.create_with_builtins(workspace_root)

    # Load user-defined skills from .ink/skills/
    skills_dir = workspace_root / ".ink" / "skills"
    registry.load_from_directory(skills_dir)

    # Built-in commands
    builtins = {
        "new": NewCommand(workspace_root),
        "init": InitCommand(workspace_root),
        "rebuild": RebuildCommand(workspace_root),
        "skills": SkillsListCommand(registry),
        "build": BuildCommand(workspace_root),
        "doctor": DoctorCommand(workspace_root),
        "import-conversation": ImportConversationCommand(workspace_root),
        "render-conversation": RenderConversationCommand(workspace_root),
        "build-conversations": BuildConversationsCommand(workspace_root),
        "link-source": LinkSourceCommand(workspace_root),
        # Agent commands
        "log": LogCommand(workspace_root),
        "recall": RecallCommand(workspace_root),
        "serve": ServeCommand(workspace_root),
        "skill-record": SkillRecordCommand(workspace_root),
        "skill-save": SkillSaveCommand(workspace_root),
        "skill-list": SkillListCommand(workspace_root),
    }

    router = IntentRouter(builtins=builtins, skill_registry=registry, workspace_root=workspace_root)
    session_logger = SessionLogger(workspace_root)
    git_manager = GitManager(workspace_root)

    return CommandExecutor(
        workspace_root=workspace_root,
        router=router,
        session_logger=session_logger,
        git_manager=git_manager,
    )


def _intent_from_namespace(ns: argparse.Namespace):
    """Convert a parsed argparse Namespace to an Intent."""
    from ink_core.cli.intent import Intent

    cmd = ns.command
    params: dict = {}

    if cmd == "new":
        target = ns.title
        if ns.date:
            params["date"] = ns.date
        if ns.slug:
            params["slug"] = ns.slug
        if ns.tags:
            params["tags"] = [t.strip() for t in ns.tags.split(",")]
        if ns.template:
            params["template"] = ns.template

    elif cmd == "init":
        target = None
        if getattr(ns, "mode", None):
            params["mode"] = ns.mode
        if getattr(ns, "agent_name", None):
            params["agent_name"] = ns.agent_name

    elif cmd == "log":
        target = getattr(ns, "content", None)
        if getattr(ns, "category", None):
            params["category"] = ns.category

    elif cmd == "recall":
        target = getattr(ns, "query", None) or ""
        if getattr(ns, "category", None):
            params["category"] = ns.category
        if getattr(ns, "since", None):
            params["since"] = ns.since
        if getattr(ns, "limit", None) is not None:
            params["limit"] = ns.limit

    elif cmd == "serve":
        target = None

    elif cmd == "skill-record":
        target = getattr(ns, "skill_name", None)
        if getattr(ns, "source", None):
            params["source"] = ns.source
        if getattr(ns, "version", None):
            params["version"] = ns.version
        if getattr(ns, "path", None):
            params["path"] = ns.path

    elif cmd == "skill-save":
        target = getattr(ns, "skill_name", None)
        if getattr(ns, "file", None):
            params["file"] = ns.file

    elif cmd == "skill-list":
        target = None

    elif cmd == "rebuild":
        target = None
        if getattr(ns, "conversations", False):
            params["scope"] = "conversations"
        elif getattr(ns, "articles", False):
            params["scope"] = "articles"

    elif cmd == "publish":
        target = getattr(ns, "target", None)
        if ns.channels:
            params["channels"] = [c.strip() for c in ns.channels.split(",")]
        if getattr(ns, "push", False):
            params["push"] = True
        if getattr(ns, "all", False):
            params["all"] = True
            target = None

    elif cmd == "syndicate":
        target = getattr(ns, "target", None)

    elif cmd == "analyze":
        target = getattr(ns, "target", None)
        if getattr(ns, "all", False):
            params["all"] = True
            target = None

    elif cmd == "search":
        target = ns.query
        if getattr(ns, "tag", None):
            params["tag"] = ns.tag
        if getattr(ns, "fulltext", False):
            params["fulltext"] = True
        if getattr(ns, "type", None):
            params["type"] = ns.type

    elif cmd == "skills":
        target = None
        params["subcommand"] = ns.subcommand if hasattr(ns, "subcommand") else "list"

    elif cmd == "build":
        target = None
        if getattr(ns, "all", False):
            params["all"] = True
        if getattr(ns, "include_drafted", False):
            params["include_drafted"] = True

    elif cmd == "doctor":
        target = None
        if getattr(ns, "migrate_status", False):
            params["migrate_status"] = True

    elif cmd == "import-conversation":
        target = getattr(ns, "file", None)
        if getattr(ns, "source", None):
            params["source"] = ns.source
        if getattr(ns, "title", None):
            params["title"] = ns.title

    elif cmd == "render-conversation":
        target = getattr(ns, "conversation_id", None)
        if getattr(ns, "preview", False):
            params["preview"] = True

    elif cmd == "build-conversations":
        target = None

    elif cmd == "link-source":
        target = getattr(ns, "article_id", None)
        if getattr(ns, "conversation", None):
            params["conversation"] = ns.conversation

    else:
        target = None

    return Intent(action=cmd, target=target, params=params)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ink",
        description="Ink Blog Core — CLI + Skills + Markdown",
    )
    sub = parser.add_subparsers(dest="command")

    # init
    p_init = sub.add_parser("init", help="[核心] Initialise a Git repository in the workspace")
    p_init.add_argument("--mode", choices=["human", "agent"], help="Workspace mode")
    p_init.add_argument("--agent-name", dest="agent_name", help="Agent name (agent mode, default: OpenClaw)")

    # new
    p_new = sub.add_parser("new", help="[核心] Create a new article")
    p_new.add_argument("title", help="Article title")
    p_new.add_argument("--date", help="Date in YYYY-MM-DD format")
    p_new.add_argument("--slug", help="Explicit slug")
    p_new.add_argument("--tags", help="Comma-separated tags")
    p_new.add_argument("--template", help="Template name", default="default")

    # rebuild
    p_rebuild = sub.add_parser("rebuild", help="[核心] Rebuild all derived files and indexes")
    p_rebuild_scope = p_rebuild.add_mutually_exclusive_group()
    p_rebuild_scope.add_argument("--conversations", action="store_true", help="Rebuild conversation index and Markdown only")
    p_rebuild_scope.add_argument("--articles", action="store_true", help="Rebuild article layers and timeline only")

    # publish
    p_pub = sub.add_parser("publish", help="[技能] Publish an article to one or more channels")
    p_pub_group = p_pub.add_mutually_exclusive_group()
    p_pub_group.add_argument("target", nargs="?", help="Canonical ID of the article")
    p_pub_group.add_argument("--all", action="store_true", help="Publish all ready articles")
    p_pub.add_argument("--channels", help="Comma-separated channel list (blog,newsletter,mastodon)")
    p_pub.add_argument("--push", action="store_true", help="Push to published in one step")

    # syndicate
    p_syn = sub.add_parser("syndicate", help="[技能] Promote a drafted article to published")
    p_syn.add_argument("target", help="Canonical ID of the drafted article")

    # analyze
    p_ana = sub.add_parser("analyze", help="[技能] Analyse an article or the whole workspace")
    p_ana_group = p_ana.add_mutually_exclusive_group()
    p_ana_group.add_argument("target", nargs="?", help="Canonical ID of the article")
    p_ana_group.add_argument("--all", action="store_true", help="Analyse all articles")

    # search
    p_srch = sub.add_parser("search", help="[技能] Search articles and conversations")
    p_srch.add_argument("query", help="Search query")
    p_srch.add_argument("--tag", help="Filter by tag")
    p_srch.add_argument("--fulltext", action="store_true", help="Enable L2 full-text search")
    p_srch.add_argument("--type", choices=["conversation", "all"], help="Search scope")

    # skills
    p_skills = sub.add_parser("skills", help="[核心] Manage skills")
    skills_sub = p_skills.add_subparsers(dest="subcommand")
    skills_sub.add_parser("list", help="List all registered skills")

    # build
    p_build = sub.add_parser("build", help="[核心] Generate static HTML site")
    p_build.add_argument("--all", action="store_true", help="Include all articles (not just published)")
    p_build.add_argument("--include-drafted", action="store_true", help="Include drafted articles for preview")

    # doctor
    p_doctor = sub.add_parser("doctor", help="[核心] Run workspace maintenance checks")
    p_doctor.add_argument("--migrate-status", action="store_true", help="Migrate old local published records to drafted")

    # conversation
    p_import = sub.add_parser("import-conversation", help="[对话] Import a local conversation cache file")
    p_import.add_argument("file", help="Conversation cache file path")
    p_import.add_argument("--source", default="unknown", help="Conversation source name")
    p_import.add_argument("--title", help="Conversation title")

    p_render = sub.add_parser("render-conversation", help="[对话] Render a conversation archive")
    p_render.add_argument("conversation_id", help="Conversation ID")
    p_render.add_argument("--preview", action="store_true", help="Also generate preview.html")

    sub.add_parser("build-conversations", help="[对话] Build static conversation HTML pages")

    p_link = sub.add_parser("link-source", help="[对话] Link an article to a source conversation")
    p_link.add_argument("article_id", help="Article canonical ID")
    p_link.add_argument("--conversation", required=True, help="Conversation ID")

    from ink_core.agent import VALID_CATEGORIES

    # log (agent mode)
    p_log = sub.add_parser("log", help="[Agent] Append a log entry to today's journal")
    p_log.add_argument("content", help="Entry content")
    p_log.add_argument(
        "--category",
        choices=VALID_CATEGORIES,
        help=f"Entry category ({', '.join(VALID_CATEGORIES)}). Default: from config",
    )

    # recall (agent mode)
    p_recall = sub.add_parser("recall", help="[Agent] Search past journal entries")
    p_recall.add_argument("query", nargs="?", default="", help="Search query (empty = latest entries)")
    p_recall.add_argument("--category", choices=VALID_CATEGORIES, help="Filter by category")
    p_recall.add_argument("--since", metavar="YYYY-MM-DD", help="Only entries on or after this date")
    p_recall.add_argument("--limit", type=int, default=20, help="Max results (1–500, default 20)")

    # serve (agent mode)
    sub.add_parser("serve", help="[Agent] Start HTTP API server (requires http_api.enabled: true)")

    # skill-record (agent mode)
    p_srec = sub.add_parser("skill-record", help="[Agent] Record an external skill")
    p_srec.add_argument("skill_name", help="Skill name")
    p_srec.add_argument("--source", required=False, help="Source URL (required)")
    p_srec.add_argument("--version", default="", help="Skill version")
    p_srec.add_argument("--path", default="", help="Install path")

    # skill-save (agent mode)
    p_ssave = sub.add_parser("skill-save", help="[Agent] Save a custom skill .md file")
    p_ssave.add_argument("skill_name", help="Skill name")
    p_ssave.add_argument("--file", required=False, help="Path to the .md skill file")

    # skill-list (agent mode)
    sub.add_parser("skill-list", help="[Agent] List all recorded skills")

    # Add _index/skills.json to .gitignore note (handled in code, documented here)

    return parser


class InkCLI:
    """Unified argparse subcommands + NLP natural-language entry point."""

    def run(self, argv: list[str] | None = None) -> int:
        if argv is None:
            argv = sys.argv[1:]

        workspace_root = _workspace_root()
        executor = _build_executor(workspace_root)

        # If a single free-form string is passed (no recognised subcommand),
        # route through NLParser.
        parser = _build_arg_parser()
        ns, remainder = parser.parse_known_args(argv)

        if ns.command is None:
            # No subcommand — treat entire argv as natural language
            from ink_core.cli.intent import NLParser

            nl_input = " ".join(argv).strip()
            if not nl_input:
                parser.print_help()
                return 0

            nl_parser = NLParser()
            parse_result = nl_parser.parse(nl_input)

            if parse_result.intent is None:
                candidates = parse_result.candidates or []
                print(
                    f"❌ {parse_result.error}\n"
                    f"   Available: {', '.join(candidates)}",
                    file=sys.stderr,
                )
                return 1

            return executor.execute(parse_result.intent)

        # Subcommand path
        intent = _intent_from_namespace(ns)
        return executor.execute(intent)


def main() -> int:
    """Main entry point for the `ink` CLI command."""
    return InkCLI().run()


if __name__ == "__main__":
    sys.exit(main())
