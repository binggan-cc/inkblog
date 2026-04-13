# Content Workflow

Use this when converting learning material, product notes, or technical research into an Ink Blog article.

## Article Creation

1. Use `ink new`, not manual `mkdir`, unless the user explicitly requests a manual migration.
2. Edit the generated `index.md`.
3. Keep `index.md` as the source of truth.
4. Run `ink rebuild --articles`.
5. Run `ink analyze --all` if wiki links changed.
6. Run `ink build --include-drafted` for local preview or `ink build` for published-only output.

## Suggested Article Structure

Use [../templates/article-template.md](../templates/article-template.md) as a reference for learning notes and technical summaries.

Do not force every article into the template. Preserve user-provided style and only add structure that helps the content.

## Quality Checks

Before publishing:

- `index.md` frontmatter has `title`, `date`, `status`, and `tags`.
- `.abstract` is concise and <=200 characters.
- `.overview` has a useful Summary and Key Points.
- Links are valid enough for the current task.
- Sensitive wording has been checked with [sensitive-words.md](sensitive-words.md) when content is public-facing.
- Status is `ready` before `ink publish`.

For a full checklist, use [../templates/review-report.md](../templates/review-report.md).

## Publish Sequence

```bash
ink publish YYYY/MM/DD-slug --channels blog
ink syndicate YYYY/MM/DD-slug
ink build
```

Use `ink publish --push` only when the user wants the combined operation and the configured channels support it.

## Conversation Source Linking

When an article is derived from an agent/chat session:

```bash
ink import-conversation ./session.json --source openclaw
ink render-conversation YYYY/MM/DD-source-slug --preview
ink link-source YYYY/MM/DD-article-slug --conversation YYYY/MM/DD-source-slug
```

Then rebuild conversation pages if needed:

```bash
ink build-conversations
```
