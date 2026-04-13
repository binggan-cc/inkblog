#!/usr/bin/env python3
"""Refresh Ink Blog derived context through the project CLI."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(args: list[str], cwd: Path) -> int:
    print("+", " ".join(args))
    return subprocess.run(args, cwd=cwd).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh Ink Blog derived context.")
    parser.add_argument(
        "--workspace",
        default=".",
        help="Ink Blog workspace root. Defaults to the current directory.",
    )
    parser.add_argument(
        "--conversations",
        action="store_true",
        help="Also rebuild conversation indexes and rendered markdown.",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Run ink analyze --all after rebuild.",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Run ink build after rebuild/analyze.",
    )
    parser.add_argument(
        "--include-drafted",
        action="store_true",
        help="Pass --include-drafted to ink build.",
    )
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    if not (workspace / ".ink").exists():
        print(f"Not an Ink Blog workspace: {workspace}", file=sys.stderr)
        return 2

    rebuild_cmd = ["ink", "rebuild"]
    if args.conversations:
        rebuild_cmd.append("--conversations")
    else:
        rebuild_cmd.append("--articles")

    code = run(rebuild_cmd, workspace)
    if code:
        return code

    if args.analyze:
        code = run(["ink", "analyze", "--all"], workspace)
        if code:
            return code

    if args.build:
        build_cmd = ["ink", "build"]
        if args.include_drafted:
            build_cmd.append("--include-drafted")
        code = run(build_cmd, workspace)
        if code:
            return code

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
