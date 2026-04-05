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
    }

    router = IntentRouter(builtins=builtins, skill_registry=registry)
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
    sub.add_parser("init", help="Initialise a Git repository in the workspace")

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
