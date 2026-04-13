# Ink Blog Command Reference

This reference matches Ink Blog Core v0.5.1.

## Core Commands

### `ink init`

```bash
ink init
ink init --mode agent
ink init --mode agent --agent-name OpenClaw
```

Initializes `.ink/`, `_index/`, templates, and Git support.

### `ink new`

```bash
ink new "Article title"
ink new "Article title" --tags ai,python
ink new "Article title" --slug custom-slug
ink new "Article title" --date 2026-04-13
ink new "Article title" --template tech-review
```

Creates `YYYY/MM/DD-slug/index.md`, `.abstract`, `.overview`, and `assets/`.

### `ink rebuild`

```bash
ink rebuild
ink rebuild --articles
ink rebuild --conversations
```

Rebuilds derived article context and/or conversation indexes/rendered markdown.

### `ink build`

```bash
ink build
ink build --include-drafted
```

Generates `_site/`. By default it includes `published` articles. `--include-drafted` is for local preview of drafted posts.

### `ink doctor`

```bash
ink doctor
ink doctor --migrate-status
```

Runs maintenance checks. `--migrate-status` converts legacy `published` posts without `published_at` to `drafted`.

## Skill Commands

### `ink publish`

```bash
ink publish YYYY/MM/DD-slug --channels blog
ink publish YYYY/MM/DD-slug --channels blog,newsletter,mastodon
ink publish YYYY/MM/DD-slug --channels blog --push
ink publish --all --channels blog
```

Precondition: `index.md` frontmatter must have `status: ready`.

Default behavior: writes local output and moves the article to `drafted`.

With `--push`: performs publish + syndicate when supported.

### `ink syndicate`

```bash
ink syndicate YYYY/MM/DD-slug
```

Moves a `drafted` article to `published` and writes `published_at`.

### `ink analyze`

```bash
ink analyze YYYY/MM/DD-slug
ink analyze --all
```

Builds `_index/graph.json` from wiki links and reports article/workspace stats.

### `ink search`

```bash
ink search "query"
ink search "query" --tag ai
ink search "query" --fulltext
ink search "query" --type conversation
ink search "query" --type all
```

Default type is article search only. `--type all` returns articles and conversations with `content_type`.

### `ink skills`

```bash
ink skills list
```

Lists built-in and custom skills known to the workspace.

## Conversation Commands

### `ink import-conversation`

```bash
ink import-conversation ./session.json --source openclaw
ink import-conversation ./session.txt --source other --title "Architecture Discussion"
```

Imports JSON, JSONL, or plain text. Raw copies are stored under `_node/conversations/raw/`; normalized archives are stored under `_node/conversations/normalized/`.

### `ink render-conversation`

```bash
ink render-conversation YYYY/MM/DD-source-slug
ink render-conversation YYYY/MM/DD-source-slug --preview
```

Always generates conversation `index.md`; `--preview` also generates local-only `preview.html`.

### `ink build-conversations`

```bash
ink build-conversations
```

Builds `_site/conversations/.../index.html`. It must not modify the site homepage or RSS feed.

### `ink link-source`

```bash
ink link-source YYYY/MM/DD-article-slug --conversation YYYY/MM/DD-source-slug
```

Adds the conversation to the article frontmatter `source_conversations` and updates `_index/conversations.json`.

## Agent Commands

Agent commands require `mode: agent` in `.ink/config.yaml`.

```bash
ink log "entry" --category work
ink recall "query" --category work --since 2026-04-01 --limit 5
ink serve
ink skill-record name --source https://example.com/skill.md --version 1.0
ink skill-save name --file ./skill.md
ink skill-list
```

Valid log categories are defined by the current implementation; use `ink log --help` if uncertain.

## Template Variables

Article template variables include `title`, `site_title`, `date`, `tags`, `abstract`, `body_html`, and `canonical_id`.

Conversation template variables include `title`, `site_title`, `source`, `created_at`, `participants`, `message_count`, `conversation_id`, and `messages`.
