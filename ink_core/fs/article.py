"""Article data model and manager."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class Article:
    path: Path           # Absolute path to the article directory
    canonical_id: str    # YYYY/MM/DD-slug (no trailing slash)
    folder_name: str     # DD-slug (date-prefixed directory name)
    slug: str            # Pure slug without date prefix
    date: str            # YYYY-MM-DD
    l0: str              # .abstract content
    l1: dict             # Parsed .overview dict
    l2: str              # Raw index.md content


@dataclass
class ArticleReadResult:
    """Result of reading an article, including any self-healed files."""
    article: Article
    changed_files: list[Path] = field(default_factory=list)


class SlugResolver:
    """Generates slugs from titles and checks for path conflicts."""

    MAX_SLUG_LENGTH = 60

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root

    def generate_slug(self, title: str) -> str:
        """Generate a URL-friendly slug from a title.

        - Converts to lowercase
        - Replaces CJK/non-alphanumeric chars with hyphens
        - Collapses multiple hyphens into one
        - Strips leading/trailing hyphens
        - Returns "untitled" if result is empty
        - Truncates to 60 chars at word boundary if possible
        """
        slug = title.lower()
        # Replace CJK characters and non-ASCII-alphanumeric chars with hyphens.
        # Keep only ASCII letters (a-z) and digits (0-9).
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        # Collapse multiple hyphens
        slug = re.sub(r'-+', '-', slug)
        # Strip leading/trailing hyphens
        slug = slug.strip('-')

        if not slug:
            return 'untitled'

        if len(slug) <= self.MAX_SLUG_LENGTH:
            return slug

        # Truncate at word boundary (hyphen) if possible
        truncated = slug[:self.MAX_SLUG_LENGTH]
        last_hyphen = truncated.rfind('-')
        if last_hyphen > 0:
            truncated = truncated[:last_hyphen]
        return truncated.strip('-')

    def check_conflict(self, date: str, slug: str) -> bool:
        """Check if the target article path already exists.

        Args:
            date: Date string in "YYYY-MM-DD" format
            slug: Article slug

        Returns:
            True if the path exists, False otherwise
        """
        year, month, day = date.split('-')
        folder_name = f"{day}-{slug}"
        target_path = self.workspace_root / year / month / folder_name
        return target_path.exists()


class ArticleManager:
    """Article CRUD + three-layer context management."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root
        self._slug_resolver = SlugResolver(workspace_root)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create(
        self,
        title: str,
        *,
        date: str | None = None,
        slug: str | None = None,
        tags: list[str] | None = None,
        template: str = "default",
    ) -> Article:
        """Create a new article directory with all required files.

        Args:
            title: Article title.
            date: Date string in "YYYY-MM-DD" format. Defaults to today.
            slug: Explicit slug. Auto-generated from title if not provided.
            tags: List of tags. Defaults to empty list.
            template: Template name under _templates/. Defaults to "default".

        Returns:
            The created Article.

        Raises:
            PathConflictError: If the target path already exists.
        """
        from datetime import date as date_cls
        from ink_core.core.errors import PathConflictError
        from ink_core.fs.layer_generator import L0Generator, L1Generator
        from ink_core.fs.markdown import parse_frontmatter

        if date is None:
            date = date_cls.today().isoformat()

        if slug is None:
            slug = self._slug_resolver.generate_slug(title)

        if self._slug_resolver.check_conflict(date, slug):
            raise PathConflictError(
                f"Article path already exists: {self._article_path(date, slug)}"
            )

        if tags is None:
            tags = []

        year, month, day = date.split("-")
        folder_name = f"{day}-{slug}"
        article_dir = self.workspace_root / year / month / folder_name
        article_dir.mkdir(parents=True, exist_ok=False)

        # Create assets/ directory
        (article_dir / "assets").mkdir()

        # Build index.md content from template
        index_content = self._render_index_template(
            template=template,
            title=title,
            slug=slug,
            date=date,
            tags=tags,
        )
        (article_dir / "index.md").write_text(index_content, encoding="utf-8")

        # Generate L0 (.abstract) and L1 (.overview)
        l0_gen = L0Generator()
        l1_gen = L1Generator()

        l0_content = l0_gen.generate(index_content)
        l1_content = l1_gen.generate(index_content)

        (article_dir / ".abstract").write_text(l0_content, encoding="utf-8")
        (article_dir / ".overview").write_text(l1_content, encoding="utf-8")

        # Parse L1 for the Article dataclass
        from ink_core.fs.markdown import parse_overview
        l1_dict = parse_overview(l1_content)

        canonical_id = f"{year}/{month}/{folder_name}"

        return Article(
            path=article_dir,
            canonical_id=canonical_id,
            folder_name=folder_name,
            slug=slug,
            date=date,
            l0=l0_content,
            l1=l1_dict,
            l2=index_content,
        )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def read(self, path: Path) -> ArticleReadResult:
        """Read an article from disk, self-healing missing .abstract/.overview.

        Args:
            path: Absolute path to the article directory.

        Returns:
            ArticleReadResult with the Article and any self-healed files.

        Raises:
            PathNotFoundError: If the article directory does not exist.
        """
        from ink_core.core.errors import PathNotFoundError
        from ink_core.fs.layer_generator import L0Generator, L1Generator
        from ink_core.fs.markdown import parse_overview

        if not path.exists() or not path.is_dir():
            raise PathNotFoundError(f"Article directory not found: {path}")

        index_path = path / "index.md"
        if not index_path.exists():
            raise PathNotFoundError(f"index.md not found in: {path}")

        l2 = index_path.read_text(encoding="utf-8")
        changed_files: list[Path] = []

        # Self-heal .abstract if missing
        abstract_path = path / ".abstract"
        if abstract_path.exists():
            l0 = abstract_path.read_text(encoding="utf-8").strip()
        else:
            l0_gen = L0Generator()
            l0 = l0_gen.generate(l2)
            abstract_path.write_text(l0, encoding="utf-8")
            changed_files.append(abstract_path)

        # Self-heal .overview if missing
        overview_path = path / ".overview"
        if overview_path.exists():
            overview_raw = overview_path.read_text(encoding="utf-8")
            l1 = parse_overview(overview_raw)
        else:
            l1_gen = L1Generator()
            overview_raw = l1_gen.generate(l2)
            overview_path.write_text(overview_raw, encoding="utf-8")
            changed_files.append(overview_path)
            l1 = parse_overview(overview_raw)

        canonical_id = self.resolve_canonical_id(path)
        # folder_name is the last component of the path (DD-slug)
        folder_name = path.name
        # slug is folder_name without the DD- prefix
        slug = re.sub(r"^\d{2}-", "", folder_name)
        # date from canonical_id: YYYY/MM/DD-slug → YYYY-MM-DD
        parts = canonical_id.split("/")
        date = f"{parts[0]}-{parts[1]}-{folder_name[:2]}"

        article = Article(
            path=path,
            canonical_id=canonical_id,
            folder_name=folder_name,
            slug=slug,
            date=date,
            l0=l0,
            l1=l1,
            l2=l2,
        )
        return ArticleReadResult(article=article, changed_files=changed_files)

    def read_by_id(self, canonical_id: str) -> ArticleReadResult:
        """Read an article by its Canonical ID.

        Args:
            canonical_id: Canonical ID in "YYYY/MM/DD-slug" format.

        Returns:
            ArticleReadResult with the Article and any self-healed files.

        Raises:
            PathNotFoundError: If the article directory does not exist.
        """
        path = self.resolve_path(canonical_id)
        return self.read(path)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update_layers(self, article: Article) -> list[Path]:
        """Regenerate .abstract and .overview from index.md.

        Args:
            article: The Article whose layers should be updated.

        Returns:
            List of changed file paths (.abstract and/or .overview).
        """
        from ink_core.fs.layer_generator import L0Generator, L1Generator
        from ink_core.fs.markdown import parse_overview

        l2 = article.l2
        changed: list[Path] = []

        # Read existing .overview for created_at preservation
        overview_path = article.path / ".overview"
        existing_l1: dict | None = None
        if overview_path.exists():
            existing_raw = overview_path.read_text(encoding="utf-8")
            existing_l1 = parse_overview(existing_raw)

        l0_gen = L0Generator()
        l1_gen = L1Generator()

        new_l0 = l0_gen.generate(l2)
        new_l1_raw = l1_gen.generate(l2, existing=existing_l1)

        abstract_path = article.path / ".abstract"
        abstract_path.write_text(new_l0, encoding="utf-8")
        changed.append(abstract_path)

        overview_path.write_text(new_l1_raw, encoding="utf-8")
        changed.append(overview_path)

        return changed

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    def list_all(self) -> list[Article]:
        """Scan all YYYY/MM/ directories and return all Articles.

        Returns:
            List of Article objects for all found articles.
        """
        articles: list[Article] = []
        year_pattern = re.compile(r"^\d{4}$")
        month_pattern = re.compile(r"^\d{2}$")

        for year_dir in sorted(self.workspace_root.iterdir()):
            if not year_dir.is_dir() or not year_pattern.match(year_dir.name):
                continue
            for month_dir in sorted(year_dir.iterdir()):
                if not month_dir.is_dir() or not month_pattern.match(month_dir.name):
                    continue
                for article_dir in sorted(month_dir.iterdir()):
                    if not article_dir.is_dir():
                        continue
                    # Must have index.md to be a valid article
                    if not (article_dir / "index.md").exists():
                        continue
                    try:
                        result = self.read(article_dir)
                        articles.append(result.article)
                    except Exception:
                        # Skip unreadable articles
                        continue

        return articles

    # ------------------------------------------------------------------
    # Resolve helpers
    # ------------------------------------------------------------------

    def resolve_canonical_id(self, path: Path) -> str:
        """Derive Canonical ID from an absolute article directory path.

        Args:
            path: Absolute path to the article directory.

        Returns:
            Canonical ID in "YYYY/MM/DD-slug" format (no trailing slash).
        """
        rel = path.relative_to(self.workspace_root)
        # rel is YYYY/MM/DD-slug — join with forward slashes
        return "/".join(rel.parts)

    def resolve_path(self, canonical_id: str) -> Path:
        """Resolve a Canonical ID to an absolute path.

        Args:
            canonical_id: Canonical ID in "YYYY/MM/DD-slug" format.

        Returns:
            Absolute path to the article directory.
        """
        return self.workspace_root / Path(canonical_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _article_path(self, date: str, slug: str) -> Path:
        year, month, day = date.split("-")
        return self.workspace_root / year / month / f"{day}-{slug}"

    def _render_index_template(
        self,
        template: str,
        title: str,
        slug: str,
        date: str,
        tags: list[str],
    ) -> str:
        """Build index.md content using the specified template.

        Falls back to a minimal default if the template file is not found.
        """
        import yaml as _yaml

        template_dir = self.workspace_root / "_templates" / template
        template_index = template_dir / "index.md"

        if template_index.exists():
            raw = template_index.read_text(encoding="utf-8")
            # Simple placeholder substitution
            raw = raw.replace("{{title}}", title)
            raw = raw.replace("{{date}}", date)
            raw = raw.replace("{{slug}}", slug)
            raw = raw.replace("{{abstract}}", "")
            raw = raw.replace("{{content}}", "")
            raw = raw.replace("{{author}}", "")
            # Prepend proper frontmatter
            frontmatter = {
                "title": title,
                "slug": slug,
                "date": date,
                "status": "draft",
                "tags": tags,
            }
            yaml_str = _yaml.dump(
                frontmatter,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )
            return f"---\n{yaml_str}---\n\n{raw}"
        else:
            # Minimal default template
            import yaml as _yaml
            frontmatter = {
                "title": title,
                "slug": slug,
                "date": date,
                "status": "draft",
                "tags": tags,
            }
            yaml_str = _yaml.dump(
                frontmatter,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )
            body = f"# {title}\n\n"
            return f"---\n{yaml_str}---\n\n{body}"
