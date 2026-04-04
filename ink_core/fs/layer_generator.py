"""L0 and L1 layer generators for ink_core.

L0Generator → .abstract (single-line ≤200 char summary)
L1Generator → .overview (YAML frontmatter + Markdown sections)
"""

from __future__ import annotations

import re
from datetime import datetime

from ink_core.fs.markdown import parse_frontmatter, serialize_overview


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_markdown(text: str) -> str:
    """Remove common Markdown syntax from a string, returning plain text."""
    # Remove fenced code blocks
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`[^`]*`", " ", text)
    # Remove images
    text = re.sub(r"!\[.*?\]\(.*?\)", " ", text)
    # Remove links — keep link text
    text = re.sub(r"\[([^\]]*)\]\([^\)]*\)", r"\1", text)
    # Remove wiki links — keep inner text
    text = re.sub(r"\[\[([^\]]*)\]\]", r"\1", text)
    # Remove headings markers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic
    text = re.sub(r"\*{1,3}([^*]*)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}([^_]*)_{1,3}", r"\1", text)
    # Remove blockquotes
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
    # Remove horizontal rules
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_body_paragraphs(body: str) -> list[str]:
    """Return non-empty, non-heading paragraphs from Markdown body text."""
    paragraphs = []
    for para in re.split(r"\n{2,}", body):
        stripped = para.strip()
        if not stripped:
            continue
        # Skip headings
        if re.match(r"^#{1,6}\s", stripped):
            continue
        # Skip pure list items / code blocks / tables
        if stripped.startswith("```") or stripped.startswith("|"):
            continue
        paragraphs.append(stripped)
    return paragraphs


def _split_sentences(text: str) -> list[str]:
    """Split plain text into sentences (simple heuristic)."""
    # Split on . ! ? followed by whitespace or end-of-string
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def _count_words(text: str) -> int:
    """Count words in plain text."""
    return len(text.split())


# ---------------------------------------------------------------------------
# L0Generator
# ---------------------------------------------------------------------------

class L0Generator:
    """Generate .abstract content: single-line ≤200 char summary."""

    MAX_LEN = 200

    def generate(self, content: str) -> str:
        """Return a single-line summary of at most 200 characters.

        Strategy (Phase 1, no AI):
        1. Strip frontmatter.
        2. Find first non-empty, non-heading paragraph.
        3. Strip Markdown syntax.
        4. Truncate to 200 chars with "..." if needed.
        5. Fall back to title from frontmatter if no body text found.
        """
        meta, body = parse_frontmatter(content)

        paragraphs = _extract_body_paragraphs(body)
        for para in paragraphs:
            plain = _strip_markdown(para)
            if plain:
                return self._truncate(plain)

        # Fallback: use title from frontmatter
        title = meta.get("title", "")
        if title:
            return self._truncate(str(title))

        return ""

    def _truncate(self, text: str) -> str:
        text = text.replace("\n", " ").strip()
        if len(text) <= self.MAX_LEN:
            return text
        return text[: self.MAX_LEN - 3] + "..."


# ---------------------------------------------------------------------------
# L1Generator
# ---------------------------------------------------------------------------

class L1Generator:
    """Generate .overview content: YAML frontmatter + Markdown sections."""

    def generate(self, content: str, existing: dict | None = None) -> str:
        """Return full .overview file content.

        Args:
            content: Raw Markdown content of index.md.
            existing: Parsed .overview dict (from parse_overview). Used ONLY
                      to read historical metadata such as created_at. Human
                      edits are NOT preserved — rebuild always overwrites.
        """
        meta, body = parse_frontmatter(content)
        now_iso = datetime.now().replace(microsecond=0).isoformat()

        # --- meta fields ---
        title = meta.get("title", "")
        tags = meta.get("tags") or []
        status = meta.get("status", "draft")

        # created_at: preserve from existing if available
        created_at = now_iso
        if existing and isinstance(existing, dict):
            existing_meta = existing.get("meta", {})
            if existing_meta.get("created_at"):
                created_at = existing_meta["created_at"]

        updated_at = now_iso

        # word_count / reading_time
        plain_body = _strip_markdown(body)
        word_count = _count_words(plain_body) if plain_body else 0
        reading_time_min = max(1, word_count // 200)

        # related: empty in Phase 1 (populated by AnalyzeSkill later)
        related: list[str] = []

        # --- summary: first 3 sentences from body ---
        sentences = _split_sentences(plain_body)
        summary = " ".join(sentences[:3]).strip()

        # --- key_points: first 3-5 bullet points, or first 3 sentences ---
        key_points = self._extract_key_points(body, sentences)

        overview_meta = {
            "title": title,
            "created_at": created_at,
            "updated_at": updated_at,
            "status": status,
            "tags": tags,
            "word_count": word_count,
            "reading_time_min": reading_time_min,
            "related": related,
        }

        return serialize_overview({
            "meta": overview_meta,
            "summary": summary,
            "key_points": key_points,
        })

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_key_points(self, body: str, sentences: list[str]) -> list[str]:
        """Extract 3-5 bullet points from body, or fall back to sentences."""
        bullets: list[str] = []
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("- ") or stripped.startswith("* "):
                point = _strip_markdown(stripped[2:].strip())
                if point:
                    bullets.append(point)
                if len(bullets) >= 5:
                    break

        if len(bullets) >= 3:
            return bullets[:5]

        # Fallback: first 3 sentences as bullets
        return sentences[:3]
