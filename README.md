# Ink Blog Core

[中文](#中文) | [English](#english)

---

<a id="中文"></a>

## 中文

基于 **CLI + Skills + Markdown** 的个人博客系统核心层。

遵循 **FS-as-DB** 哲学：本地文件系统作为唯一数据存储，目录结构表达关系，Markdown 作为内容源，自然语言或显式命令驱动操作执行。

---

### 目录

- [安装](#安装)
- [快速开始](#快速开始)
- [命令参考](#命令参考)
- [目录结构](#目录结构-1)
- [文章生命周期](#文章生命周期)
- [配置](#配置)
- [静态站生成](#静态站生成)
- [自定义模板](#自定义模板)
- [自定义 Skills](#自定义-skills)
- [部署](#部署)
- [开发](#开发)

---

### 安装

**环境要求：** Python ≥ 3.11、Git

```bash
# 克隆项目
git clone <repo-url>
cd inkblog

# 安装
pip install -e .

# 验证安装
ink --help
```

---

### 快速开始

```bash
# 1. 在当前目录初始化工作区
ink init

# 2. 编辑站点配置
#    修改 .ink/config.yaml 中的 title、subtitle、author

# 3. 创建第一篇文章
ink new "我的第一篇文章" --tags ai,python

# 4. 编辑文章内容
#    打开 YYYY/MM/DD-slug/index.md 写作

# 5. 将文章标记为可发布
#    在 index.md frontmatter 中将 status 改为 ready

# 6. 发布文章
ink publish YYYY/MM/DD-slug --channels blog

# 7. 生成静态站
ink build

# 8. 打开 _site/index.html 预览
```

---

### 命令参考

#### `ink init`

初始化工作区。在当前目录创建完整的 `.ink/` 目录结构、默认配置文件，并初始化 Git 仓库。

```bash
ink init
```

**执行内容：**
- 创建 `.ink/sessions/`、`.ink/skills/`、`.ink/publish-history/`、`_index/`
- 生成 `.ink/config.yaml`（如不存在）
- 执行 `git init` 并创建初始提交
- 在 `.gitignore` 中排除 `.ink/sessions/`

---

#### `ink new`

创建新文章，自动生成目录结构和三层上下文文件。

```bash
ink new "文章标题"
ink new "文章标题" --date 2025-06-01
ink new "文章标题" --slug my-custom-slug
ink new "文章标题" --tags ai,python,blog
ink new "文章标题" --template tech-review
```

**参数：**

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `title` | 文章标题（必填） | — |
| `--date` | 文章日期，格式 `YYYY-MM-DD` | 当天日期 |
| `--slug` | 自定义 slug（URL 路径片段） | 从标题自动生成 |
| `--tags` | 逗号分隔的标签列表 | 空 |
| `--template` | 模板名称，对应 `_templates/` 下的目录 | `default` |

**生成文件：**
```
YYYY/MM/DD-slug/
├── index.md      # 文章正文（需手动编辑）
├── .abstract     # L0 摘要（自动生成，≤200 字符）
├── .overview     # L1 概览（自动生成，YAML + Markdown）
└── assets/       # 资源目录
```

---

#### `ink rebuild`

重建所有文章的派生文件（`.abstract`、`.overview`）和时间线索引（`_index/timeline.json`）。

```bash
ink rebuild
```

适用场景：批量修改文章内容后、`.abstract`/`.overview` 文件损坏或丢失时。

---

#### `ink analyze`

分析文章内容，提取 Wiki 链接关系，生成知识图谱（`_index/graph.json`）。

```bash
# 分析单篇文章
ink analyze 2025/03/20-my-post

# 分析全库
ink analyze --all
```

**单篇输出：** 字数、预估阅读时长、标签、出链数、入链数

**全库输出：** 文章总数、标签总数、最近更新时间、孤立文章数

Wiki 链接格式：`[[文章名]]` 或 `[[YYYY/MM/DD-slug]]`（精确格式）

---

#### `ink search`

在文章库中搜索，默认先搜 L0（摘要），不足 3 条时自动扩展到 L1（概览）。

```bash
ink search "关键词"
ink search "关键词" --tag ai          # 按标签过滤
ink search "关键词" --fulltext        # 启用全文搜索（L2）
```

**排序规则（优先级从高到低）：** 标题命中 → 标签命中 → L0 命中 → L1 命中 → L2 命中，同层级按命中次数降序，再按日期降序。

---

#### `ink publish`

将文章发布到指定渠道。**文章 `status` 必须为 `ready` 才能发布。**

```bash
ink publish 2025/03/20-my-post --channels blog
ink publish 2025/03/20-my-post --channels blog,newsletter,mastodon
ink publish --all --channels blog
```

**支持的渠道（Phase 1 均为本地文件输出）：**

| 渠道 | 输出位置 | 说明 |
|------|----------|------|
| `blog` | `.ink/publish-output/blog/` | Markdown 格式，含 `published_at` |
| `newsletter` | `.ink/publish-output/newsletter/` | Markdown 格式，含摘要引言 |
| `mastodon` | `.ink/publish-output/mastodon/` | 纯文本，≤500 字符 |

发布成功后：
- `index.md` 中 `status` 更新为 `published`
- 写入 `published_at` 时间戳
- 更新 `_index/timeline.json`
- 在 `.ink/publish-history/` 下记录发布历史

---

#### `ink build`

生成静态 HTML 站点，输出到 `_site/`（可通过配置修改）。

```bash
ink build
ink build --all
```

**生成内容：**
- `_site/index.html` — 首页（文章列表 + 统计信息）
- `_site/YYYY/MM/DD-slug/index.html` — 每篇文章页面
- `_site/feed.xml` — RSS/Atom 订阅源（最近 20 篇已发布文章）

---

#### `ink skills list`

列出所有已注册的 Skills（内置 + 自定义）。

```bash
ink skills list
```

---

### 目录结构

```
项目根目录/
├── YYYY/MM/DD-slug/          # 文章目录（按日期组织）
│   ├── index.md              # L2: 文章正文（Source of Truth）
│   ├── .abstract             # L0: 单行摘要，≤200 字符
│   ├── .overview             # L1: YAML frontmatter + Markdown 章节
│   └── assets/               # 图片等资源文件
├── .ink/                     # 工作区元数据
│   ├── config.yaml           # 项目配置
│   ├── sessions/             # 操作记录
│   ├── publish-history/      # 发布历史
│   ├── publish-output/       # 发布输出文件
│   └── skills/               # 自定义 Skill 定义文件
├── _index/                   # 全局索引（可重建）
│   ├── timeline.json
│   └── graph.json
├── _site/                    # 静态站输出
├── _templates/               # 文章模板
├── .gitignore
├── pyproject.toml
└── README.md
```

---

### 文章生命周期

**状态流转：**

```
draft → review → ready → published → archived
```

| 状态 | 说明 |
|------|------|
| `draft` | 草稿，新建文章的默认状态 |
| `review` | 审阅中 |
| `ready` | 准备发布，`ink publish` 的前置条件 |
| `published` | 已发布 |
| `archived` | 已归档 |

**index.md frontmatter 格式：**

```yaml
---
title: "文章标题"
slug: "article-slug"
date: "2025-03-20"
status: "draft"
tags: ["ai", "python"]
---
```

**三层上下文：**

| 层级 | 文件 | 内容 | 用途 |
|------|------|------|------|
| L0 | `.abstract` | 单行纯文本，≤200 字符 | 搜索摘要、RSS 描述 |
| L1 | `.overview` | YAML frontmatter + Summary + Key Points | 搜索扩展、分析 |
| L2 | `index.md` | 完整 Markdown 正文 | Source of Truth |

---

### 配置

**配置优先级（高 → 低）：**

1. `.ink/config.yaml` — 项目级配置
2. `~/.ink/config.yaml` — 全局用户配置
3. 内置默认值

```yaml
# .ink/config.yaml
site:
  title: "My Blog"
  subtitle: ""
  author: ""
  base_url: ""

channels:
  blog:
    type: static
    output: "./_site"

search:
  engine: keyword
  top_k: 10

git:
  auto_commit: true
```

---

### 静态站生成

```
ink build → 读取 timeline.json → 过滤 published → 生成 HTML → 生成 RSS → Git commit
```

**本地预览：**

```bash
ink build
open _site/index.html      # macOS
xdg-open _site/index.html  # Linux
```

---

### 自定义模板

在 `_templates/site/` 下放置 Jinja2 模板文件，优先于内置默认模板。

```
_templates/site/
├── article.html    # 文章页面模板
└── index.html      # 首页模板
```

**文章页模板变量：** `title`、`site_title`、`date`、`tags`、`abstract`、`body_html`、`canonical_id`

**首页模板变量：** `site_title`、`site_subtitle`、`site_author`、`year`、`articles`、`total_articles`、`total_words`、`date_range`

---

### 自定义 Skills

在 `.ink/skills/` 下创建 `.md` 文件即可注册新 Skill。

```yaml
---
skill: summarize
version: "1.0"
description: 生成文章摘要
context_requirement: L2
---
```

**必填 frontmatter 字段：** `skill`、`version`、`context_requirement`

---

### 部署

`ink build` 生成的 `_site/` 是纯静态文件，可部署到任何静态托管服务。

```bash
# GitHub Pages
git subtree push --prefix _site origin gh-pages

# Netlify / Vercel
# 构建命令: pip install -e . && ink build
# 发布目录: _site

# 本地预览
cd _site && python -m http.server 8000
```

在 `.ink/config.yaml` 中设置 `site.base_url` 以生成正确的 RSS 链接。

---

### 开发

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

**依赖：** `pyyaml>=6.0`、`jinja2>=3.1`

**开发依赖：** `pytest>=7.0`、`hypothesis>=6.0`


---

<a id="english"></a>

## English

A personal blog system core layer built on **CLI + Skills + Markdown**.

Follows the **FS-as-DB** philosophy: the local filesystem is the sole data store, directory structure expresses relationships, Markdown serves as the content source, and operations are driven by natural language or explicit commands.

---

### Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Command Reference](#command-reference)
- [Directory Structure](#directory-structure)
- [Article Lifecycle](#article-lifecycle)
- [Configuration](#configuration)
- [Static Site Generation](#static-site-generation)
- [Custom Templates](#custom-templates)
- [Custom Skills](#custom-skills)
- [Deployment](#deployment)
- [Development](#development)

---

### Installation

**Requirements:** Python ≥ 3.11, Git

```bash
git clone <repo-url>
cd inkblog
pip install -e .
ink --help
```

---

### Quick Start

```bash
# 1. Initialize workspace
ink init

# 2. Edit site config
#    Update title, subtitle, author in .ink/config.yaml

# 3. Create your first article
ink new "My First Post" --tags ai,python

# 4. Edit article content
#    Open YYYY/MM/DD-slug/index.md and write

# 5. Mark article as ready
#    Set status to "ready" in index.md frontmatter

# 6. Publish
ink publish YYYY/MM/DD-slug --channels blog

# 7. Build static site
ink build

# 8. Preview
open _site/index.html
```

---

### Command Reference

#### `ink init`

Initialize workspace. Creates the `.ink/` directory structure, default config, and initializes a Git repository.

```bash
ink init
```

---

#### `ink new`

Create a new article with auto-generated directory structure and three-layer context files.

```bash
ink new "Article Title"
ink new "Article Title" --date 2025-06-01
ink new "Article Title" --slug my-custom-slug
ink new "Article Title" --tags ai,python,blog
ink new "Article Title" --template tech-review
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| `title` | Article title (required) | — |
| `--date` | Article date (`YYYY-MM-DD`) | Today |
| `--slug` | Custom URL slug | Auto-generated from title |
| `--tags` | Comma-separated tag list | Empty |
| `--template` | Template name from `_templates/` | `default` |

**Generated files:**
```
YYYY/MM/DD-slug/
├── index.md      # Article body (edit manually)
├── .abstract     # L0 summary (auto-generated, ≤200 chars)
├── .overview     # L1 overview (auto-generated, YAML + Markdown)
└── assets/       # Resource directory
```

---

#### `ink rebuild`

Rebuild all derived files (`.abstract`, `.overview`) and timeline index (`_index/timeline.json`).

```bash
ink rebuild
```

---

#### `ink analyze`

Analyze article content, extract wiki-link relationships, and generate a knowledge graph (`_index/graph.json`).

```bash
ink analyze 2025/03/20-my-post    # Single article
ink analyze --all                  # Entire library
```

Wiki link format: `[[Article Name]]` or `[[YYYY/MM/DD-slug]]`

---

#### `ink search`

Search the article library. Searches L0 (abstracts) first, auto-expands to L1 (overviews) if fewer than 3 results.

```bash
ink search "keyword"
ink search "keyword" --tag ai          # Filter by tag
ink search "keyword" --fulltext        # Full-text search (L2)
```

**Ranking (highest to lowest):** Title match → Tag match → L0 match → L1 match → L2 match. Within the same level, sorted by hit count descending, then by date descending.

---

#### `ink publish`

Publish articles to specified channels. **Article `status` must be `ready`.**

```bash
ink publish 2025/03/20-my-post --channels blog
ink publish 2025/03/20-my-post --channels blog,newsletter,mastodon
ink publish --all --channels blog
```

| Channel | Output Location | Format |
|---------|----------------|--------|
| `blog` | `.ink/publish-output/blog/` | Markdown with `published_at` |
| `newsletter` | `.ink/publish-output/newsletter/` | Markdown with summary intro |
| `mastodon` | `.ink/publish-output/mastodon/` | Plain text, ≤500 chars |

After publishing: status updates to `published`, `published_at` timestamp is written, `_index/timeline.json` is updated, and publish history is recorded.

---

#### `ink build`

Generate a static HTML site to `_site/`.

```bash
ink build          # Published articles only (default)
ink build --all    # All articles
```

**Output:**
- `_site/index.html` — Homepage (article list + stats)
- `_site/YYYY/MM/DD-slug/index.html` — Article pages
- `_site/feed.xml` — RSS/Atom feed (latest 20 published articles)

---

#### `ink skills list`

List all registered skills (built-in + custom).

```bash
ink skills list
```

---

### Directory Structure

```
project-root/
├── YYYY/MM/DD-slug/          # Article directories (organized by date)
│   ├── index.md              # L2: Full article (Source of Truth)
│   ├── .abstract             # L0: One-line summary, ≤200 chars
│   ├── .overview             # L1: YAML frontmatter + Markdown sections
│   └── assets/               # Images and resources
├── .ink/                     # Workspace metadata
│   ├── config.yaml           # Project config
│   ├── sessions/             # Operation logs
│   ├── publish-history/      # Publish history
│   ├── publish-output/       # Publish output files
│   └── skills/               # Custom skill definitions
├── _index/                   # Global indexes (rebuildable)
│   ├── timeline.json
│   └── graph.json
├── _site/                    # Static site output
├── _templates/               # Article templates
├── .gitignore
├── pyproject.toml
└── README.md
```

---

### Article Lifecycle

**Status flow:**

```
draft → review → ready → published → archived
```

| Status | Description |
|--------|-------------|
| `draft` | Draft, default for new articles |
| `review` | Under review |
| `ready` | Ready to publish, prerequisite for `ink publish` |
| `published` | Published |
| `archived` | Archived |

**index.md frontmatter format:**

```yaml
---
title: "Article Title"
slug: "article-slug"
date: "2025-03-20"
status: "draft"
tags: ["ai", "python"]
---
```

**Three-layer context:**

| Layer | File | Content | Purpose |
|-------|------|---------|---------|
| L0 | `.abstract` | Plain text, ≤200 chars | Search summary, RSS description |
| L1 | `.overview` | YAML frontmatter + Summary + Key Points | Extended search, analysis |
| L2 | `index.md` | Full Markdown body | Source of Truth |

---

### Configuration

**Priority (high → low):**

1. `.ink/config.yaml` — Project-level config
2. `~/.ink/config.yaml` — Global user config
3. Built-in defaults

```yaml
# .ink/config.yaml
site:
  title: "My Blog"
  subtitle: ""
  author: ""
  base_url: ""

channels:
  blog:
    type: static
    output: "./_site"

search:
  engine: keyword
  top_k: 10

git:
  auto_commit: true
```

---

### Static Site Generation

```
ink build → Read timeline.json → Filter published → Generate HTML → Generate RSS → Git commit
```

**Local preview:**

```bash
ink build
open _site/index.html      # macOS
xdg-open _site/index.html  # Linux
```

---

### Custom Templates

Place Jinja2 template files in `_templates/site/` to override built-in defaults.

```
_templates/site/
├── article.html    # Article page template
└── index.html      # Homepage template
```

**Article template variables:** `title`, `site_title`, `date`, `tags`, `abstract`, `body_html`, `canonical_id`

**Homepage template variables:** `site_title`, `site_subtitle`, `site_author`, `year`, `articles`, `total_articles`, `total_words`, `date_range`

---

### Custom Skills

Create `.md` files in `.ink/skills/` to register new skills.

```yaml
---
skill: summarize
version: "1.0"
description: Generate article summary
context_requirement: L2
---
```

**Required frontmatter fields:** `skill`, `version`, `context_requirement`

---

### Deployment

The `_site/` directory generated by `ink build` contains pure static files, deployable to any static hosting service.

```bash
# GitHub Pages
git subtree push --prefix _site origin gh-pages

# Netlify / Vercel
# Build command: pip install -e . && ink build
# Publish directory: _site

# Local preview
cd _site && python -m http.server 8000
```

Set `site.base_url` in `.ink/config.yaml` for correct RSS links.

---

### Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

**Dependencies:** `pyyaml>=6.0`, `jinja2>=3.1`

**Dev dependencies:** `pytest>=7.0`, `hypothesis>=6.0`
