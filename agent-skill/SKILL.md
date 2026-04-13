---
name: agent-skill
description: "Use for managing an Ink Blog Core workspace: create and edit articles, maintain L0/L1/L2 context files, publish or syndicate posts, build the static site, import/render/search conversation archives, and use agent-mode journal/recall/skill commands. Prefer the ink CLI over manual file creation."
---

# Ink Blog

Ink Blog Core is an FS-as-DB personal knowledge/blog system. The filesystem is the source of truth, Markdown is the content format, and the `ink` CLI owns most mutations.

## Operating Rule

Prefer existing project commands over hand-written filesystem operations:

```bash
ink new "Title" --tags ai,python
ink rebuild
ink analyze --all
ink build
```

Only edit files directly when the user asks for content changes or when the CLI does not expose the needed operation.

## Core Model

Articles live at `YYYY/MM/DD-slug/`:

```text
index.md    # L2: full Markdown, source of truth
.abstract   # L0: <=200 character single-line summary
.overview   # L1: YAML + structured overview
assets/     # article-local assets
```

Read order for agent context:

1. Read `.abstract` to decide whether the item is relevant.
2. Read `.overview` for structured summary and tags.
3. Read `index.md` only when the full article is needed.

## Article Lifecycle

Current status flow:

```text
draft -> review -> ready -> drafted -> published -> archived
```

`ink publish` writes local publishing artifacts and moves `ready` articles to `drafted`. `ink syndicate` moves `drafted` articles to `published`. `ink publish --push` combines both steps when configured.

## Common Workflows

Create an article:

```bash
ink new "Article title" --tags ai,python
```

After editing `index.md`, refresh derived files and indexes:

```bash
ink rebuild --articles
ink analyze --all
```

Publish locally and then syndicate:

```bash
ink publish YYYY/MM/DD-slug --channels blog
ink syndicate YYYY/MM/DD-slug
ink build
```

Preview drafted articles locally:

```bash
ink build --include-drafted
```

Conversation archive flow:

```bash
ink import-conversation ./session.json --source openclaw
ink render-conversation YYYY/MM/DD-source-slug --preview
ink build-conversations
ink link-source YYYY/MM/DD-article-slug --conversation YYYY/MM/DD-source-slug
ink search "query" --type all
```

Agent mode flow:

```bash
ink init --mode agent --agent-name OpenClaw
ink log "Finished search refactor" --category work
ink recall "search" --limit 5
ink skill-list
```

## References

- Command details: [references/ink-commands.md](references/ink-commands.md)
- Three-layer context details: [references/three-layer-context.md](references/three-layer-context.md)
- Content workflow and quality checks: [references/content-workflow.md](references/content-workflow.md)
- Sensitive wording replacements: [references/sensitive-words.md](references/sensitive-words.md)

## Templates And Scripts

- Article structure template: [templates/article-template.md](templates/article-template.md)
- Review checklist: [templates/review-report.md](templates/review-report.md)
- Safe context refresh wrapper: [scripts/refresh_context.py](scripts/refresh_context.py)

Use the templates as writing/checking aids. Do not copy them verbatim into a post unless the user asks for a template scaffold.
