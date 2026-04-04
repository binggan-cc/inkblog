"""Search skill: layered keyword search (L0 → L1 → L2)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ink_core.fs.article import Article, ArticleManager
from ink_core.fs.markdown import parse_frontmatter, parse_overview
from ink_core.skills.base import Skill, SkillResult


# ---------------------------------------------------------------------------
# SearchHit
# ---------------------------------------------------------------------------

@dataclass
class SearchHit:
    """A single search result."""

    canonical_id: str
    title: str
    abstract: str
    snippet: str
    score: float
    hit_layer: str   # "title" | "tag" | "L0" | "L1" | "L2"
    hit_count: int   # number of keyword occurrences
    date: str        # YYYY-MM-DD, used for tie-breaking


# ---------------------------------------------------------------------------
# Layer priority scores (higher = better rank)
# ---------------------------------------------------------------------------

_LAYER_SCORE: dict[str, float] = {
    "title": 5.0,
    "tag":   4.0,
    "L0":    3.0,
    "L1":    2.0,
    "L2":    1.0,
}

_SNIPPET_MAX = 150


# ---------------------------------------------------------------------------
# SearchSkill
# ---------------------------------------------------------------------------

class SearchSkill(Skill):
    """Layered keyword search (L0 → L1 → L2)."""

    def __init__(self, workspace_root: Path, config=None) -> None:
        self._workspace_root = workspace_root
        self._config = config
        self._article_manager = ArticleManager(workspace_root)

    # ------------------------------------------------------------------
    # Skill ABC
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "search"

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def context_requirement(self) -> str:
        return "L0"

    # ------------------------------------------------------------------
    # execute
    # ------------------------------------------------------------------

    def execute(self, target: str | None, params: dict) -> SkillResult:
        """Execute the search skill.

        Args:
            target: The search query string (may also be in params["query"]).
            params: May contain:
                - "query": search query string (overrides target)
                - "tag": optional tag filter
                - "fulltext": bool, enable L2 search
                - "include_archived": bool, include archived articles

        Returns:
            SkillResult with data containing "query", "results", and optionally
            "suggestions" when no results are found.
        """
        query: str = params.get("query") or target or ""
        tag_filter: str | None = params.get("tag")
        fulltext: bool = bool(params.get("fulltext", False))
        include_archived: bool = bool(params.get("include_archived", False))

        # Check config for fulltext engine
        if not fulltext and self._config is not None:
            engine = self._config.get("search.engine", "keyword")
            if engine == "fulltext":
                fulltext = True

        query = query.strip()
        if not query:
            return SkillResult(
                success=False,
                message="Search query is empty.",
                data={"query": query, "results": [], "suggestions": [
                    "Provide a non-empty search query.",
                ]},
            )

        # Load all articles
        all_articles = self._article_manager.list_all()

        # Filter archived unless explicitly included
        if not include_archived:
            all_articles = [a for a in all_articles if _get_status(a) != "archived"]

        # Apply tag filter
        if tag_filter:
            all_articles = [a for a in all_articles if tag_filter in _get_tags(a)]

        # Tokenise query into keywords
        keywords = _tokenize(query)
        if not keywords:
            return SkillResult(
                success=False,
                message="No valid keywords in query.",
                data={"query": query, "results": [], "suggestions": [
                    "Try using shorter or simpler keywords.",
                ]},
            )

        # --- L0 search (always) ---
        hits: dict[str, SearchHit] = {}
        _search_layer(articles=all_articles, keywords=keywords, layer="title", hits=hits)
        _search_layer(articles=all_articles, keywords=keywords, layer="tag", hits=hits)
        _search_layer(articles=all_articles, keywords=keywords, layer="L0", hits=hits)

        # --- L1 expansion: if fewer than 3 L0/title/tag hits, expand to L1 ---
        if len(hits) < 3:
            _search_layer(articles=all_articles, keywords=keywords, layer="L1", hits=hits)

        # --- L2 full-text (optional) ---
        if fulltext:
            _search_layer(articles=all_articles, keywords=keywords, layer="L2", hits=hits)

        # Sort results
        results = sorted(hits.values(), key=_sort_key, reverse=True)

        if not results:
            suggestions = _generate_suggestions(query, keywords)
            return SkillResult(
                success=True,
                message=f"No results found for '{query}'.",
                data={
                    "query": query,
                    "results": [],
                    "suggestions": suggestions,
                },
            )

        return SkillResult(
            success=True,
            message=f"Found {len(results)} result(s) for '{query}'.",
            data={
                "query": query,
                "results": [_hit_to_dict(h) for h in results],
            },
        )


# ---------------------------------------------------------------------------
# Layer search
# ---------------------------------------------------------------------------

def _search_layer(
    articles: list[Article],
    keywords: list[str],
    layer: str,
    hits: dict[str, SearchHit],
) -> None:
    """Search articles in the given layer and update the hits dict.

    For each article, if any keyword matches in the target layer, we either
    create a new SearchHit or upgrade an existing one if the new layer has
    higher priority.
    """
    for article in articles:
        text, snippet_source = _get_layer_text(article, layer)
        if not text:
            continue

        count = _count_hits(text, keywords)
        if count == 0:
            continue

        snippet = _extract_snippet(snippet_source, keywords)
        title = _get_title(article)
        layer_score = _LAYER_SCORE[layer]

        existing = hits.get(article.canonical_id)
        if existing is None:
            hits[article.canonical_id] = SearchHit(
                canonical_id=article.canonical_id,
                title=title,
                abstract=article.l0,
                snippet=snippet,
                score=layer_score,
                hit_layer=layer,
                hit_count=count,
                date=article.date,
            )
        else:
            # Keep the highest-priority layer hit
            if layer_score > existing.score:
                hits[article.canonical_id] = SearchHit(
                    canonical_id=article.canonical_id,
                    title=title,
                    abstract=article.l0,
                    snippet=snippet,
                    score=layer_score,
                    hit_layer=layer,
                    hit_count=count,
                    date=article.date,
                )
            elif layer_score == existing.score and count > existing.hit_count:
                # Same layer, more hits
                hits[article.canonical_id] = SearchHit(
                    canonical_id=article.canonical_id,
                    title=title,
                    abstract=article.l0,
                    snippet=snippet,
                    score=layer_score,
                    hit_layer=layer,
                    hit_count=count,
                    date=article.date,
                )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tokenize(query: str) -> list[str]:
    """Split query into lowercase keyword tokens."""
    tokens = re.findall(r"[a-zA-Z0-9\u4e00-\u9fff\u3040-\u30ff]+", query)
    return [t.lower() for t in tokens if t]


def _count_hits(text: str, keywords: list[str]) -> int:
    """Count total keyword occurrences in text (case-insensitive)."""
    text_lower = text.lower()
    total = 0
    for kw in keywords:
        total += text_lower.count(kw)
    return total


def _get_layer_text(article: Article, layer: str) -> tuple[str, str]:
    """Return (searchable_text, snippet_source) for the given layer."""
    if layer == "title":
        title = _get_title(article)
        return title, title
    elif layer == "tag":
        tags = _get_tags(article)
        tag_text = " ".join(tags)
        return tag_text, tag_text
    elif layer == "L0":
        return article.l0, article.l0
    elif layer == "L1":
        # Search in summary + key_points from parsed l1
        if isinstance(article.l1, dict):
            summary = article.l1.get("summary", "")
            key_points = article.l1.get("key_points", [])
            kp_text = " ".join(key_points) if key_points else ""
            combined = f"{summary} {kp_text}".strip()
            return combined, combined
        return "", ""
    elif layer == "L2":
        _, body = parse_frontmatter(article.l2)
        return body, body
    return "", ""


def _extract_snippet(text: str, keywords: list[str]) -> str:
    """Extract a ≤150-char snippet showing the first keyword match context."""
    if not text:
        return ""

    text_lower = text.lower()
    best_pos = len(text)

    for kw in keywords:
        pos = text_lower.find(kw)
        if pos != -1 and pos < best_pos:
            best_pos = pos

    if best_pos == len(text):
        # No match found; return start of text
        return text[:_SNIPPET_MAX].strip()

    # Centre the snippet around the match
    start = max(0, best_pos - 40)
    end = min(len(text), start + _SNIPPET_MAX)
    snippet = text[start:end].strip()

    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet = snippet + "…"

    return snippet[:_SNIPPET_MAX + 2]  # allow for ellipsis chars


def _sort_key(hit: SearchHit):
    """Sort key: (score desc, hit_count desc, date desc)."""
    return (hit.score, hit.hit_count, hit.date)


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


def _get_tags(article: Article) -> list[str]:
    """Get article tags from l1 meta or l2 frontmatter."""
    if isinstance(article.l1, dict):
        meta = article.l1.get("meta", {})
        if isinstance(meta, dict):
            tags = meta.get("tags")
            if tags is not None:
                return list(tags)
    meta, _ = parse_frontmatter(article.l2)
    tags = meta.get("tags", [])
    return list(tags) if tags else []


def _get_status(article: Article) -> str:
    """Get article status from l1 meta or l2 frontmatter."""
    if isinstance(article.l1, dict):
        meta = article.l1.get("meta", {})
        if isinstance(meta, dict):
            status = meta.get("status")
            if status is not None:
                return str(status)
    meta, _ = parse_frontmatter(article.l2)
    return str(meta.get("status", "draft"))


def _generate_suggestions(query: str, keywords: list[str]) -> list[str]:
    """Generate at least 1 rewrite suggestion for an empty result set."""
    suggestions: list[str] = []

    if len(keywords) > 1:
        suggestions.append(
            f"Try searching with fewer keywords, e.g. '{keywords[0]}'."
        )
    else:
        suggestions.append(
            f"Try a different keyword or check the spelling of '{query}'."
        )

    if len(query) > 10:
        suggestions.append("Try using shorter or more general keywords.")

    return suggestions if suggestions else ["Try different keywords or check spelling."]


def _hit_to_dict(hit: SearchHit) -> dict:
    """Serialise a SearchHit to a plain dict."""
    return {
        "canonical_id": hit.canonical_id,
        "title": hit.title,
        "abstract": hit.abstract,
        "snippet": hit.snippet,
        "score": hit.score,
        "hit_layer": hit.hit_layer,
        "hit_count": hit.hit_count,
        "date": hit.date,
    }
