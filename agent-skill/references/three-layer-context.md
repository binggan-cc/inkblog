# Three-Layer Context

Ink Blog uses three files per article so agents can load only the context they need.

## L0: `.abstract`

- Plain text, single line, at most 200 characters.
- Used in search previews, RSS descriptions, article lists, and quick agent triage.
- Regenerable from `index.md`.

## L1: `.overview`

- YAML frontmatter plus Markdown sections such as Summary and Key Points.
- Used for structured search, navigation, and agent analysis.
- Regenerable from `index.md`.

## L2: `index.md`

- Full Markdown article.
- Source of truth for title, date, status, tags, and body content.
- Static site generation reads from this layer.

## Agent Reading Strategy

Use this order:

1. Read `.abstract`.
2. Read `.overview` when the abstract is relevant or ambiguous.
3. Read `index.md` only when full details are needed.

When editing an article, edit `index.md` first, then run:

```bash
ink rebuild --articles
```

Run `ink analyze --all` when wiki links or graph relationships may have changed.
