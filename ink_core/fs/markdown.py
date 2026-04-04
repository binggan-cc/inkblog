"""Markdown/frontmatter parsing utilities for ink_core."""

from __future__ import annotations

import re
import yaml


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter from Markdown content.

    Returns (meta_dict, body_str). If no frontmatter is found,
    returns ({}, original content).
    """
    if not content.startswith("---"):
        return {}, content

    # Find the closing ---
    rest = content[3:]
    end = rest.find("\n---")
    if end == -1:
        return {}, content

    yaml_str = rest[:end]
    body = rest[end + 4:]  # skip '\n---'
    # Strip leading newline from body
    if body.startswith("\n"):
        body = body[1:]

    meta = yaml.safe_load(yaml_str) or {}
    return meta, body


def dump_frontmatter(meta: dict, body: str) -> str:
    """Serialize meta dict + body back to Markdown with YAML frontmatter.

    Format:
        ---
        <yaml>
        ---

        <body>
    """
    yaml_str = yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return f"---\n{yaml_str}---\n\n{body}"


def parse_overview(content: str) -> dict:
    """Parse a .overview file into a structured dict.

    Returns:
        {
            "meta": {...},
            "summary": "...",
            "key_points": [...],
        }
    """
    meta, body = parse_frontmatter(content)

    summary = _extract_section(body, "Summary")
    key_points_raw = _extract_section(body, "Key Points")
    key_points = _parse_list(key_points_raw)

    return {
        "meta": meta,
        "summary": summary,
        "key_points": key_points,
    }


def serialize_overview(data: dict) -> str:
    """Serialize a structured overview dict back to .overview format.

    Expects data with keys: meta, summary, key_points.
    """
    meta = data.get("meta", {})
    summary = data.get("summary", "")
    key_points = data.get("key_points", [])

    body_parts: list[str] = []

    if summary:
        body_parts.append(f"## Summary\n\n{summary.strip()}\n")

    if key_points:
        items = "\n".join(f"- {p}" for p in key_points)
        body_parts.append(f"## Key Points\n\n{items}\n")

    body = "\n".join(body_parts)
    return dump_frontmatter(meta, body)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_section(body: str, heading: str) -> str:
    """Extract the text content under a ## heading, up to the next ## heading."""
    pattern = rf"^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s|\Z)"
    match = re.search(pattern, body, re.MULTILINE | re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


def _parse_list(text: str) -> list[str]:
    """Parse a Markdown bullet list into a Python list of strings."""
    if not text:
        return []
    items = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- "):
            items.append(line[2:].strip())
        elif line.startswith("* "):
            items.append(line[2:].strip())
    return items
