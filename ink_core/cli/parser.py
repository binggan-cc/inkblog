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
    from ink_core.cli.builtin import BuildCommand, InitCommand, NewCommand, RebuildCommand, SkillsListCommand
    from ink_core.cli.intent import IntentRouter
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

    elif cmd == "publish":
        target = getattr(ns, "target", None)
        if ns.channels:
            params["channels"] = [c.strip() for c in ns.channels.split(",")]
        if getattr(ns, "all", False):
            params["all"] = True
            target = None

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

    elif cmd == "skills":
        target = None
        params["subcommand"] = ns.subcommand if hasattr(ns, "subcommand") else "list"

    elif cmd == "build":
        target = None
        if getattr(ns, "all", False):
            params["all"] = True

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
    p_init = sub.add_parser("init", help="Initialise a Git repository in the workspace")
    p_init.add_argument("--mode", choices=["human", "agent"], help="Workspace mode")
    p_init.add_argument("--agent-name", dest="agent_name", help="Agent name (agent mode, default: OpenClaw)")

    # new
    p_new = sub.add_parser("new", help="Create a new article")
    p_new.add_argument("title", help="Article title")
    p_new.add_argument("--date", help="Date in YYYY-MM-DD format")
    p_new.add_argument("--slug", help="Explicit slug")
    p_new.add_argument("--tags", help="Comma-separated tags")
    p_new.add_argument("--template", help="Template name", default="default")

    # rebuild
    sub.add_parser("rebuild", help="Rebuild all derived files and indexes")

    # publish
    p_pub = sub.add_parser("publish", help="Publish an article to one or more channels")
    p_pub_group = p_pub.add_mutually_exclusive_group()
    p_pub_group.add_argument("target", nargs="?", help="Canonical ID of the article")
    p_pub_group.add_argument("--all", action="store_true", help="Publish all ready articles")
    p_pub.add_argument("--channels", help="Comma-separated channel list (blog,newsletter,mastodon)")

    # analyze
    p_ana = sub.add_parser("analyze", help="Analyse an article or the whole workspace")
    p_ana_group = p_ana.add_mutually_exclusive_group()
    p_ana_group.add_argument("target", nargs="?", help="Canonical ID of the article")
    p_ana_group.add_argument("--all", action="store_true", help="Analyse all articles")

    # search
    p_srch = sub.add_parser("search", help="Search articles")
    p_srch.add_argument("query", help="Search query")
    p_srch.add_argument("--tag", help="Filter by tag")
    p_srch.add_argument("--fulltext", action="store_true", help="Enable L2 full-text search")

    # skills
    p_skills = sub.add_parser("skills", help="Manage skills")
    skills_sub = p_skills.add_subparsers(dest="subcommand")
    skills_sub.add_parser("list", help="List all registered skills")

    # build
    p_build = sub.add_parser("build", help="Generate static HTML site")
    p_build.add_argument("--all", action="store_true", help="Include all articles (not just published)")

    from ink_core.agent import VALID_CATEGORIES

    # log (agent mode)
    p_log = sub.add_parser("log", help="Append a log entry to today's journal (agent mode)")
    p_log.add_argument("content", help="Entry content")
    p_log.add_argument(
        "--category",
        choices=VALID_CATEGORIES,
        help=f"Entry category ({', '.join(VALID_CATEGORIES)}). Default: from config",
    )

    # recall (agent mode)
    p_recall = sub.add_parser("recall", help="Search past journal entries (agent mode)")
    p_recall.add_argument("query", nargs="?", default="", help="Search query (empty = latest entries)")
    p_recall.add_argument("--category", choices=VALID_CATEGORIES, help="Filter by category")
    p_recall.add_argument("--since", metavar="YYYY-MM-DD", help="Only entries on or after this date")
    p_recall.add_argument("--limit", type=int, default=20, help="Max results (1–500, default 20)")

    # serve (agent mode)
    sub.add_parser("serve", help="Start HTTP API server (agent mode, requires http_api.enabled: true)")

    # skill-record (agent mode)
    p_srec = sub.add_parser("skill-record", help="Record an external skill (agent mode)")
    p_srec.add_argument("skill_name", help="Skill name")
    p_srec.add_argument("--source", required=False, help="Source URL (required)")
    p_srec.add_argument("--version", default="", help="Skill version")
    p_srec.add_argument("--path", default="", help="Install path")

    # skill-save (agent mode)
    p_ssave = sub.add_parser("skill-save", help="Save a custom skill .md file (agent mode)")
    p_ssave.add_argument("skill_name", help="Skill name")
    p_ssave.add_argument("--file", required=False, help="Path to the .md skill file")

    # skill-list (agent mode)
    sub.add_parser("skill-list", help="List all recorded skills (agent mode)")

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
