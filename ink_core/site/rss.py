"""RSS/Atom feed generator for ink_core static site."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ink_core.fs.article import Article

_MAX_FEED_ITEMS = 20


class RSSGenerator:
    """Generate an Atom feed (feed.xml) from a list of articles.

    Uses only Python standard library (xml.etree.ElementTree).
    """

    def generate(
        self,
        articles: list["Article"],
        output_path: Path,
        site_config: dict,
    ) -> None:
        """Write an Atom feed to output_path.

        Args:
            articles: Articles to include (already filtered/sorted by caller).
                      At most MAX_FEED_ITEMS (20) will be included.
            output_path: Destination file path (e.g. _site/feed.xml).
            site_config: Dict with optional keys: title, author, base_url.
        """
        from ink_core.fs.markdown import parse_frontmatter

        site_title = site_config.get("title", "Blog")
        site_author = site_config.get("author", "Anonymous")
        base_url = site_config.get("base_url", "").rstrip("/")

        # Take at most 20 items
        feed_articles = articles[:_MAX_FEED_ITEMS]

        # Build Atom feed
        ET.register_namespace("", "http://www.w3.org/2005/Atom")
        feed = ET.Element("{http://www.w3.org/2005/Atom}feed")

        _sub(feed, "title", site_title)
        _sub(feed, "id", base_url or "urn:ink-blog")
        _sub(feed, "updated", _now_atom())

        author_el = ET.SubElement(feed, "{http://www.w3.org/2005/Atom}author")
        _sub(author_el, "name", site_author)

        if base_url:
            link_el = ET.SubElement(feed, "{http://www.w3.org/2005/Atom}link")
            link_el.set("rel", "alternate")
            link_el.set("href", base_url)

            feed_link = ET.SubElement(feed, "{http://www.w3.org/2005/Atom}link")
            feed_link.set("rel", "self")
            feed_link.set("href", f"{base_url}/feed.xml")

        for article in feed_articles:
            meta, body = parse_frontmatter(article.l2)
            title = meta.get("title", article.slug)
            article_url = f"{base_url}/{article.canonical_id}/" if base_url else f"/{article.canonical_id}/"
            published_at = meta.get("published_at") or article.date
            updated_at = _parse_date(str(published_at))

            entry = ET.SubElement(feed, "{http://www.w3.org/2005/Atom}entry")
            _sub(entry, "title", str(title))
            _sub(entry, "id", article_url)
            _sub(entry, "updated", updated_at)
            _sub(entry, "published", updated_at)

            entry_link = ET.SubElement(entry, "{http://www.w3.org/2005/Atom}link")
            entry_link.set("rel", "alternate")
            entry_link.set("href", article_url)

            if article.l0:
                _sub(entry, "summary", article.l0)

            tags = meta.get("tags") or []
            for tag in tags:
                cat = ET.SubElement(entry, "{http://www.w3.org/2005/Atom}category")
                cat.set("term", str(tag))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        tree = ET.ElementTree(feed)
        ET.indent(tree, space="  ")
        tree.write(output_path, encoding="utf-8", xml_declaration=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sub(parent: ET.Element, tag: str, text: str) -> ET.Element:
    el = ET.SubElement(parent, f"{{http://www.w3.org/2005/Atom}}{tag}")
    el.text = text
    return el


def _now_atom() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_date(value: str) -> str:
    """Convert a date/datetime string to Atom format (RFC 3339)."""
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value[:19], fmt[:len(value[:19])])
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
    return _now_atom()
