"""Analyze skill and Wiki link resolution for ink_core."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from ink_core.fs.article import Article, ArticleManager
from ink_core.fs.index_manager import IndexManager
from ink_core.fs.markdown import parse_frontmatter
from ink_core.skills.base import Skill, SkillResult


# ---------------------------------------------------------------------------
# WikiLinkResult
# ---------------------------------------------------------------------------

@dataclass
class WikiLinkResult:
    """Wiki Link resolution result."""

    raw: str                        # Original link text (without [[ ]])
    resolved_id: str | None         # Resolved Canonical ID, or None
    status: str                     # "resolved" | "ambiguous" | "unresolved"
    candidates: list[str] | None    # Candidate list when ambiguous


# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

# Matches [[...]] wiki links; captures the inner text
_WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

# Matches the exact Canonical ID format: YYYY/MM/DD-slug
_CANONICAL_ID_RE = re.compile(r"^\d{4}/\d{2}/\d{2}-[a-zA-Z0-9_-]+$")


# ---------------------------------------------------------------------------
# AnalyzeSkill
# ---------------------------------------------------------------------------

class AnalyzeSkill(Skill):
    """Article analysis and knowledge graph generation."""

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root
        self._article_manager = ArticleManager(workspace_root)
        self._index_manager = IndexManager(workspace_root)

    # ------------------------------------------------------------------
    # Skill ABC
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "analyze"

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def context_requirement(self) -> str:
        return "L2"

    # ------------------------------------------------------------------
    # execute
    # ------------------------------------------------------------------

    def execute(self, target: str | None, params: dict) -> SkillResult:
        """Execute the analyze skill.

        Two modes:
        - Single article: target is a Canonical ID
        - All articles:   params.get("all") == True  OR  target == "all"

        Args:
            target: Canonical ID or "all".
            params: May contain {"all": True}.

        Returns:
            SkillResult with analysis data.
        """
        all_mode = params.get("all", False) or target == "all"

        if all_mode:
            return self._analyze_all()
        else:
            return self._analyze_single(target)

    # ------------------------------------------------------------------
    # Single-article analysis
    # ------------------------------------------------------------------

    def _analyze_single(self, target: str | None) -> SkillResult:
        if not target:
            all_articles = self._article_manager.list_all()
            available = [a.canonical_id for a in all_articles]
            return SkillResult(
                success=False,
                message="No target article specified.",
                data={"available_articles": available},
            )

        # Resolve path and check existence
        article_path = self._article_manager.resolve_path(target)
        if not article_path.exists():
            all_articles = self._article_manager.list_all()
            available = [a.canonical_id for a in all_articles]
            return SkillResult(
                success=False,
                message=f"Article not found: '{target}'",
                data={"available_articles": available},
            )

        try:
            read_result = self._article_manager.read_by_id(target)
        except Exception as exc:
            all_articles = self._article_manager.list_all()
            available = [a.canonical_id for a in all_articles]
            return SkillResult(
                success=False,
                message=str(exc),
                data={"available_articles": available},
            )

        article = read_result.article
        all_articles = self._article_manager.list_all()

        # --- Word count (from l2, excluding frontmatter) ---
        _, body = parse_frontmatter(article.l2)
        word_count = _count_words(body)

        # --- Reading time (ceil of word_count / 200) ---
        reading_time = max(1, math.ceil(word_count / 200))

        # --- Tags (from l1 meta or l2 frontmatter) ---
        tags = _extract_tags(article)

        # --- Wiki link extraction and resolution ---
        wiki_links = self._extract_wiki_links(article.l2, article, all_articles)

        resolved_links = [wl for wl in wiki_links if wl.status == "resolved"]
        ambiguous_links = [wl for wl in wiki_links if wl.status == "ambiguous"]
        unresolved_links = [wl for wl in wiki_links if wl.status == "unresolved"]

        # related_count = number of resolved outgoing links
        related_count = len(resolved_links)

        # --- In-link count from graph.json ---
        graph = self._index_manager.read_graph()
        in_link_count = sum(
            1 for edge in graph.get("edges", [])
            if edge.get("target") == target
        )

        # --- Update graph.json ---
        changed_files = self._update_graph(
            source_article=article,
            all_articles=all_articles,
            resolved_links=resolved_links,
            ambiguous_links=ambiguous_links,
            unresolved_links=unresolved_links,
        )

        graph_path = self._workspace_root / "_index" / "graph.json"

        return SkillResult(
            success=True,
            message=f"Analysis complete for '{target}'",
            data={
                "canonical_id": target,
                "word_count": word_count,
                "reading_time": reading_time,
                "tags": tags,
                "related_count": related_count,
                "in_link_count": in_link_count,
                "wiki_links": {
                    "resolved": [wl.resolved_id for wl in resolved_links],
                    "ambiguous": [
                        {"raw": wl.raw, "candidates": wl.candidates}
                        for wl in ambiguous_links
                    ],
                    "unresolved": [wl.raw for wl in unresolved_links],
                },
            },
            changed_files=[graph_path] + changed_files,
        )

    # ------------------------------------------------------------------
    # All-articles analysis
    # ------------------------------------------------------------------

    def _analyze_all(self) -> SkillResult:
        all_articles = self._article_manager.list_all()

        total_articles = len(all_articles)

        # Collect all unique tags
        all_tags: set[str] = set()
        for article in all_articles:
            for tag in _extract_tags(article):
                all_tags.add(tag)
        total_tags = len(all_tags)

        # Most recent updated_at
        most_recent_updated_at: str | None = None
        for article in all_articles:
            l1_meta = article.l1.get("meta", {}) if isinstance(article.l1, dict) else {}
            updated_at = l1_meta.get("updated_at", "")
            if updated_at:
                if most_recent_updated_at is None or updated_at > most_recent_updated_at:
                    most_recent_updated_at = updated_at

        # Isolated articles: no edges in graph.json (neither source nor target)
        graph = self._index_manager.read_graph()
        edges = graph.get("edges", [])
        connected_ids: set[str] = set()
        for edge in edges:
            connected_ids.add(edge.get("source", ""))
            connected_ids.add(edge.get("target", ""))
        connected_ids.discard("")

        isolated_count = sum(
            1 for a in all_articles if a.canonical_id not in connected_ids
        )

        # Update graph with all articles as nodes (rebuild full graph)
        self._rebuild_full_graph(all_articles)
        graph_path = self._workspace_root / "_index" / "graph.json"

        return SkillResult(
            success=True,
            message=f"Knowledge base analysis complete: {total_articles} articles",
            data={
                "total_articles": total_articles,
                "total_tags": total_tags,
                "most_recent_updated_at": most_recent_updated_at,
                "isolated_articles": isolated_count,
            },
            changed_files=[graph_path],
        )

    # ------------------------------------------------------------------
    # Wiki link extraction
    # ------------------------------------------------------------------

    def _extract_wiki_links(
        self,
        content: str,
        source_article: Article,
        all_articles: list[Article],
    ) -> list[WikiLinkResult]:
        """Extract and resolve all [[...]] wiki links from content."""
        raw_links = _WIKI_LINK_RE.findall(content)
        results: list[WikiLinkResult] = []
        seen: set[str] = set()

        for raw in raw_links:
            raw = raw.strip()
            if raw in seen:
                continue
            seen.add(raw)
            # Skip self-links
            if raw == source_article.canonical_id:
                continue
            result = self.resolve_wiki_link(raw, all_articles)
            results.append(result)

        return results

    # ------------------------------------------------------------------
    # resolve_wiki_link
    # ------------------------------------------------------------------

    def resolve_wiki_link(self, link_text: str, all_articles: list[Article]) -> WikiLinkResult:
        """Resolve a wiki link text against the article collection.

        Resolution rules:
        1. If link_text matches YYYY/MM/DD-slug exactly → direct canonical lookup
        2. Otherwise: case-insensitive title or slug match
           - 1 match → resolved
           - >1 matches → ambiguous
           - 0 matches → unresolved

        Args:
            link_text: The raw text inside [[ ]], e.g. "Liquid Blog" or "2025/03/20-liquid-blog"
            all_articles: Full list of articles to search against.

        Returns:
            WikiLinkResult with status and resolved_id / candidates.
        """
        # Rule 1: exact canonical ID format
        if _CANONICAL_ID_RE.match(link_text):
            # Direct lookup by canonical_id
            match = next(
                (a for a in all_articles if a.canonical_id == link_text), None
            )
            if match:
                return WikiLinkResult(
                    raw=link_text,
                    resolved_id=match.canonical_id,
                    status="resolved",
                    candidates=None,
                )
            else:
                return WikiLinkResult(
                    raw=link_text,
                    resolved_id=None,
                    status="unresolved",
                    candidates=None,
                )

        # Rule 2: title / slug match (case-insensitive)
        link_lower = link_text.lower()
        matches: list[Article] = []

        for article in all_articles:
            # Match against title from l1 meta or l2 frontmatter
            title = _get_title(article).lower()
            slug = article.slug.lower()

            if title == link_lower or slug == link_lower:
                matches.append(article)

        if len(matches) == 1:
            return WikiLinkResult(
                raw=link_text,
                resolved_id=matches[0].canonical_id,
                status="resolved",
                candidates=None,
            )
        elif len(matches) > 1:
            return WikiLinkResult(
                raw=link_text,
                resolved_id=None,
                status="ambiguous",
                candidates=[a.canonical_id for a in matches],
            )
        else:
            return WikiLinkResult(
                raw=link_text,
                resolved_id=None,
                status="unresolved",
                candidates=None,
            )

    # ------------------------------------------------------------------
    # Graph update helpers
    # ------------------------------------------------------------------

    def _update_graph(
        self,
        source_article: Article,
        all_articles: list[Article],
        resolved_links: list[WikiLinkResult],
        ambiguous_links: list[WikiLinkResult],
        unresolved_links: list[WikiLinkResult],
    ) -> list[Path]:
        """Update graph.json with analysis results for source_article.

        Merges new edges/ambiguous/unresolved into the existing graph,
        replacing any previous entries for this source article.
        """
        graph = self._index_manager.read_graph()
        source_id = source_article.canonical_id

        # Rebuild nodes: ensure all articles are present
        existing_node_ids = {n["id"] for n in graph.get("nodes", [])}
        nodes = list(graph.get("nodes", []))

        for article in all_articles:
            if article.canonical_id not in existing_node_ids:
                nodes.append(_article_to_node(article))
                existing_node_ids.add(article.canonical_id)

        # Ensure source article node is up-to-date
        nodes = [n for n in nodes if n["id"] != source_id]
        nodes.append(_article_to_node(source_article))

        # Remove old edges/ambiguous/unresolved from this source
        edges = [e for e in graph.get("edges", []) if e.get("source") != source_id]
        ambiguous = [a for a in graph.get("ambiguous", []) if a.get("source") != source_id]
        unresolved = [u for u in graph.get("unresolved", []) if u.get("source") != source_id]

        # Add new edges
        for wl in resolved_links:
            edges.append({
                "source": source_id,
                "target": wl.resolved_id,
                "type": "wiki_link",
            })

        # Add new ambiguous
        for wl in ambiguous_links:
            ambiguous.append({
                "source": source_id,
                "label": wl.raw,
                "candidates": wl.candidates or [],
            })

        # Add new unresolved
        for wl in unresolved_links:
            unresolved.append({
                "source": source_id,
                "label": wl.raw,
            })

        new_graph = {
            "nodes": nodes,
            "edges": edges,
            "ambiguous": ambiguous,
            "unresolved": unresolved,
        }
        self._index_manager.update_graph(new_graph)
        return []

    def _rebuild_full_graph(self, all_articles: list[Article]) -> None:
        """Rebuild the full graph for all articles (used in --all mode)."""
        nodes = [_article_to_node(a) for a in all_articles]
        edges: list[dict] = []
        ambiguous: list[dict] = []
        unresolved: list[dict] = []

        for article in all_articles:
            wiki_links = self._extract_wiki_links(article.l2, article, all_articles)
            for wl in wiki_links:
                if wl.status == "resolved":
                    edges.append({
                        "source": article.canonical_id,
                        "target": wl.resolved_id,
                        "type": "wiki_link",
                    })
                elif wl.status == "ambiguous":
                    ambiguous.append({
                        "source": article.canonical_id,
                        "label": wl.raw,
                        "candidates": wl.candidates or [],
                    })
                else:
                    unresolved.append({
                        "source": article.canonical_id,
                        "label": wl.raw,
                    })

        self._index_manager.update_graph({
            "nodes": nodes,
            "edges": edges,
            "ambiguous": ambiguous,
            "unresolved": unresolved,
        })


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _count_words(text: str) -> int:
    """Count words in text (split on whitespace)."""
    words = text.split()
    return len(words)


def _extract_tags(article: Article) -> list[str]:
    """Extract tags from article l1 meta or l2 frontmatter."""
    # Try l1 meta first
    if isinstance(article.l1, dict):
        meta = article.l1.get("meta", {})
        if isinstance(meta, dict):
            tags = meta.get("tags")
            if tags is not None:
                return list(tags)

    # Fall back to l2 frontmatter
    meta, _ = parse_frontmatter(article.l2)
    tags = meta.get("tags", [])
    return list(tags) if tags else []


def _get_title(article: Article) -> str:
    """Get article title from l1 meta or l2 frontmatter."""
    if isinstance(article.l1, dict):
        meta = article.l1.get("meta", {})
        if isinstance(meta, dict):
            title = meta.get("title")
            if title:
                return str(title)

    meta, _ = parse_frontmatter(article.l2)
    return str(meta.get("title", article.slug))


def _article_to_node(article: Article) -> dict:
    """Convert an Article to a graph node dict."""
    return {
        "id": article.canonical_id,
        "title": _get_title(article),
        "tags": _extract_tags(article),
    }
