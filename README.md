# Ink Blog Core

> v0.5.0

[中文](#中文) | [English](#english)

---

<a id="中文"></a>

## 中文

基于 **CLI + Skills + Markdown** 的个人博客系统核心层，支持 Human 模式和 Agent 模式双模运行。

遵循 **FS-as-DB** 哲学：本地文件系统作为唯一数据存储，目录结构表达关系，Markdown 作为内容源，自然语言或显式命令驱动操作执行。

---

### 目录

- [安装](#安装)
- [快速开始](#快速开始)
- [命令参考](#命令参考)
  - [通用命令](#通用命令)
  - [Agent 模式命令](#agent-模式命令)
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

# 安装可选增强依赖（中文 slug 拼音、mistune Markdown 渲染）
pip install -e ".[all]"

# 验证安装
ink --help
```

---

### 快速开始

```bash
# 1. 在当前目录初始化工作区（默认 human 模式）
ink init

# 1b. 或以 agent 模式初始化
ink init --mode agent --agent-name MyAgent

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

#### 通用命令

##### `ink init`

初始化工作区。在当前目录创建完整的 `.ink/` 目录结构、默认配置文件，并初始化 Git 仓库。

```bash
ink init
ink init --mode agent
ink init --mode agent --agent-name MyAgent
```

**参数：**

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--mode` | 工作区模式：`human` 或 `agent` | `human` |
| `--agent-name` | Agent 名称（仅 agent 模式） | `OpenClaw` |

**执行内容：**
- 创建 `.ink/sessions/`、`.ink/skills/`、`.ink/publish-history/`、`_index/`
- 生成 `.ink/config.yaml`（如不存在）
- 执行 `git init` 并创建初始提交
- 在 `.gitignore` 中排除 `.ink/sessions/`
- 在 `.gitignore` 中排除 `_node/conversations/raw/`，保留 normalized 对话归档纳入版本控制

---

##### `ink new`

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

**内置模板：** `default`、`tech-review`、`weekly-report`

**生成文件：**
```
YYYY/MM/DD-slug/
├── index.md      # 文章正文（需手动编辑）
├── .abstract     # L0 摘要（自动生成，≤200 字符）
├── .overview     # L1 概览（自动生成，YAML + Markdown）
└── assets/       # 资源目录
```

---

##### `ink rebuild`

重建所有文章的派生文件（`.abstract`、`.overview`）和时间线索引（`_index/timeline.json`）。

```bash
ink rebuild
```

适用场景：批量修改文章内容后、`.abstract`/`.overview` 文件损坏或丢失时。

---

##### `ink analyze`

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

##### `ink search`

在文章库中搜索，默认先搜 L0（摘要），不足 3 条时自动扩展到 L1（概览）。

```bash
ink search "关键词"
ink search "关键词" --tag ai          # 按标签过滤
ink search "关键词" --fulltext        # 启用全文搜索（L2）
ink search "关键词" --type conversation
ink search "关键词" --type all
```

**排序规则（优先级从高到低）：** 标题命中 → 标签命中 → L0 命中 → L1 命中 → L2 命中，同层级按命中次数降序，再按日期降序。

默认只搜索 Article；`--type conversation` 搜索 `_node/conversations/normalized/` 下的对话 `index.md`；`--type all` 同时返回 Article 和 Conversation，并用 `content_type` 区分来源。

---

##### `ink publish`

将文章发布到指定渠道。**文章 `status` 必须为 `ready` 才能发布。**

```bash
ink publish 2025/03/20-my-post --channels blog
ink publish 2025/03/20-my-post --channels blog,newsletter,mastodon
ink publish 2025/03/20-my-post --channels blog --push
ink publish --all --channels blog
ink syndicate 2025/03/20-my-post
```

**支持的渠道（Phase 1 均为本地文件输出）：**

| 渠道 | 输出位置 | 说明 |
|------|----------|------|
| `blog` | `.ink/publish-output/blog/` | Markdown 格式，含 `published_at` |
| `newsletter` | `.ink/publish-output/newsletter/` | Markdown 格式，含摘要引言 |
| `mastodon` | `.ink/publish-output/mastodon/` | 纯文本，≤500 字符 |

发布成功后：
- `ink publish` 生成本地发布产物并将 `status` 更新为 `drafted`
- `ink syndicate` 将 `drafted` 文章推进为 `published`，并写入 `published_at`
- `ink publish --push` 一步将 `ready` 文章推进为 `published`
- 每次发布尝试都会在 `.ink/publish-history/` 下记录历史

---

##### `ink build`

生成静态 HTML 站点，输出到 `_site/`（可通过配置修改）。

```bash
ink build
ink build --include-drafted
ink build --all
```

**生成内容：**
- `_site/index.html` — 首页（文章列表 + 统计信息）
- `_site/YYYY/MM/DD-slug/index.html` — 每篇文章页面
- `_site/feed.xml` — RSS/Atom 订阅源（最近 20 篇已发布文章）

默认只构建 `published` 文章；`--include-drafted` 用于本地预览 drafted 文章。

---

##### `ink doctor`

工作区维护命令。

```bash
ink doctor --migrate-status
```

`--migrate-status` 会将没有 `published_at` 的旧 `published` 文章迁移为 `drafted`，带有 `published_at` 的文章保持 `published`。

---

##### `ink import-conversation`

导入本地 AI/Agent 对话缓存文件，支持 JSON、JSONL、纯文本。原始副本写入 `_node/conversations/raw/<source>/`，规范化对象写入 `_node/conversations/normalized/YYYY/MM/DD-source-slug/meta.json`。

```bash
ink import-conversation ./session.json --source openclaw
ink import-conversation ./session.txt --source other --title "架构讨论"
```

##### `ink render-conversation`

从 `meta.json` 重新生成对话 Markdown 归档。`--preview` 额外生成本地预览文件 `preview.html`；正式站点页面不在这里生成。

```bash
ink render-conversation 2026/04/11-openclaw-session-001
ink render-conversation 2026/04/11-openclaw-session-001 --preview
```

##### `ink build-conversations`

批量生成正式对话静态页面到 `_site/conversations/YYYY/MM/YYYY-MM-DD-source-slug/index.html`。该命令独立于 `ink build`，不会修改博客首页或 RSS。

```bash
ink build-conversations
```

##### `ink link-source`

将文章与来源对话双向关联：Article frontmatter 写入 `source_conversations`，`_index/conversations.json` 写入 `linked_articles`。

```bash
ink link-source 2026/04/12-inkblog-node --conversation 2026/04/11-openclaw-session-001
```

---

##### `ink skills list`

列出所有已注册的 Skills（内置 + 自定义），并标注来源。

```bash
ink skills list
```

---

#### Agent 模式命令

以下命令在 `mode: agent` 配置下可用，用于 AI Agent 的日记记录、记忆检索和技能管理。

##### `ink log`

向当天日记追加一条带时间戳和分类的条目。

```bash
ink log "今天学习了 Rust 的所有权机制"
ink log "完成了搜索模块重构" --category work
```

**参数：**

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `content` | 条目内容（必填） | — |
| `--category` | 分类：`work`、`learning`、`skill-installed`、`memory`、`note` | 配置中的 `agent.default_category`（默认 `note`） |

日记文件存储在 `YYYY/MM/DD-journal/index.md`，复用文章的三层上下文结构。

---

##### `ink recall`

检索过往日记条目，返回结构化 JSON。

```bash
ink recall                              # 返回最近条目
ink recall "Rust"                       # 关键词搜索
ink recall --category learning          # 按分类过滤
ink recall --since 2026-04-01           # 按日期过滤
ink recall "搜索" --limit 5             # 限制结果数量
```

**参数：**

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `query` | 搜索关键词（可选） | 空（返回最近条目） |
| `--category` | 按分类过滤 | 不过滤 |
| `--since` | 仅返回此日期之后的条目，格式 `YYYY-MM-DD` | 不过滤 |
| `--limit` | 最大结果数（1–500） | `20` |

---

##### `ink serve`

启动 HTTP API 服务器，暴露 `/log`、`/recall`、`/health` 端点。

```bash
ink serve
```

需要在配置中启用：`agent.http_api.enabled: true`，默认端口 `4242`。

---

##### `ink skill-record`

记录一个外部技能到 `_index/skills.json`。

```bash
ink skill-record my-skill --source https://example.com/skill.md --version 1.0
```

---

##### `ink skill-save`

保存一个自定义技能 `.md` 文件到 `.ink/skills/`。

```bash
ink skill-save summarize --file ./my-summarize-skill.md
```

---

##### `ink skill-list`

列出所有已记录的技能（外部 + 自定义）。

```bash
ink skill-list
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
├── YYYY/MM/DD-journal/       # Agent 日记目录（agent 模式）
│   ├── index.md              # 日记正文（带时间戳条目）
│   ├── .abstract             # L0 摘要
│   └── .overview             # L1 概览
├── .ink/                     # 工作区元数据
│   ├── config.yaml           # 项目配置
│   ├── sessions/             # 操作记录（gitignore）
│   ├── publish-history/      # 发布历史（gitignore）
│   ├── publish-output/       # 发布输出文件（gitignore）
│   └── skills/               # 自定义 Skill 定义文件
├── _node/                    # Node 级非 Article 内容
│   └── conversations/
│       ├── raw/              # 原始对话缓存副本（gitignore）
│       └── normalized/       # 规范化对话；含 meta.json、index.md、assets/
├── _index/                   # 全局索引（派生数据，可通过 rebuild 重建）
│   ├── timeline.json         # 时间线索引
│   ├── graph.json            # 知识图谱
│   ├── conversations.json    # 对话索引
│   └── skills.json           # 技能注册表（agent 模式）
├── _site/                    # 静态站输出（gitignore）
├── _templates/               # 文章模板
│   ├── default/              # 默认模板
│   ├── tech-review/          # 技术评测模板
│   └── weekly-report/        # 周报模板
├── ink_core/                 # 源码
├── tests/                    # 测试
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
mode: human   # "human" | "agent"

site:
  title: "My Blog"
  subtitle: ""
  author: ""
  base_url: ""

# Agent 模式配置（仅 mode: agent 时生效）
agent:
  agent_name: "OpenClaw"
  auto_create_daily: true
  default_category: "note"
  disable_human_commands: false
  http_api:
    enabled: false
    port: 4242

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
ink build-conversations → 读取 conversations.json → 生成 _site/conversations/ → 不修改首页/RSS
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

v0.4.0 的文件定义 Skill 使用严格 DSL 执行器，仅支持：

```text
read_content <L0|L1|L2>
write_file <path>
```

`write_file` 的目标路径必须是相对路径，最终写入位置限制在 `.ink/skill-output/` 下。

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

**开发依赖：** `pytest>=7.0`、`hypothesis>=6.0`、`pypinyin>=0.50`、`mistune>=3.0`

**版本管理：** 遵循 [Semantic Versioning](https://semver.org/)（`MAJOR.MINOR.PATCH`）。版本号维护在 `pyproject.toml` 和 `README.md` 顶部。发版时打 annotated tag（`git tag -a vX.Y.Z`）。详细的发版流程和分支策略见 `.kiro/specs/ink-kernel-architecture/design.md` 第十三章。

**版本历史：**

| 版本 | 日期 | 主题 |
|------|------|------|
| v0.5.0 | 2026-04-11 | Conversation Processing MVP：本地对话导入、归档渲染、静态对话页、来源链接、对话搜索 |
| v0.4.1 | 2026-04-11 | 发布状态机扩展：drafted/syndicate/publish --push/build --include-drafted、CLI 标注 |
| v0.4.0 | 2026-04-11 | 工程硬化：中文 slug、Markdown/XSS 安全、模板 autoescape、严格 SkillExecutor、发布状态修复 |
| v0.3.0 | 2026-04-11 | Agent 模式（log/recall/serve/skill-*）、属性测试、文档整合 |
| v0.2.0 | 2026-04-05 | 静态站生成、分层配置、改进 init |


---

<a id="english"></a>

## English

A personal blog system core layer built on **CLI + Skills + Markdown**, supporting both Human mode and Agent mode.

Follows the **FS-as-DB** philosophy: the local filesystem is the sole data store, directory structure expresses relationships, Markdown serves as the content source, and operations are driven by natural language or explicit commands.

---

### Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Command Reference](#command-reference)
  - [General Commands](#general-commands)
  - [Agent Mode Commands](#agent-mode-commands)
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
# Optional enhancements: pinyin slug generation and mistune Markdown rendering
pip install -e ".[all]"
ink --help
```

---

### Quick Start

```bash
# 1. Initialize workspace (default: human mode)
ink init

# 1b. Or initialize in agent mode
ink init --mode agent --agent-name MyAgent

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

#### General Commands

##### `ink init`

Initialize workspace. Creates the `.ink/` directory structure, default config, and initializes a Git repository.

```bash
ink init
ink init --mode agent
ink init --mode agent --agent-name MyAgent
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--mode` | Workspace mode: `human` or `agent` | `human` |
| `--agent-name` | Agent name (agent mode only) | `OpenClaw` |

---

##### `ink new`

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

**Built-in templates:** `default`, `tech-review`, `weekly-report`

**Generated files:**
```
YYYY/MM/DD-slug/
├── index.md      # Article body (edit manually)
├── .abstract     # L0 summary (auto-generated, ≤200 chars)
├── .overview     # L1 overview (auto-generated, YAML + Markdown)
└── assets/       # Resource directory
```

---

##### `ink rebuild`

Rebuild all derived files (`.abstract`, `.overview`) and timeline index (`_index/timeline.json`).

```bash
ink rebuild
```

---

##### `ink analyze`

Analyze article content, extract wiki-link relationships, and generate a knowledge graph (`_index/graph.json`).

```bash
ink analyze 2025/03/20-my-post    # Single article
ink analyze --all                  # Entire library
```

Wiki link format: `[[Article Name]]` or `[[YYYY/MM/DD-slug]]`

---

##### `ink search`

Search the article library. Searches L0 (abstracts) first, auto-expands to L1 (overviews) if fewer than 3 results.

```bash
ink search "keyword"
ink search "keyword" --tag ai          # Filter by tag
ink search "keyword" --fulltext        # Full-text search (L2)
```

**Ranking (highest to lowest):** Title match → Tag match → L0 match → L1 match → L2 match. Within the same level, sorted by hit count descending, then by date descending.

---

##### `ink publish`

Publish articles to specified channels. **Article `status` must be `ready`.**

```bash
ink publish 2025/03/20-my-post --channels blog
ink publish 2025/03/20-my-post --channels blog,newsletter,mastodon
ink publish 2025/03/20-my-post --channels blog --push
ink publish --all --channels blog
ink syndicate 2025/03/20-my-post
```

| Channel | Output Location | Format |
|---------|----------------|--------|
| `blog` | `.ink/publish-output/blog/` | Markdown with `published_at` |
| `newsletter` | `.ink/publish-output/newsletter/` | Markdown with summary intro |
| `mastodon` | `.ink/publish-output/mastodon/` | Plain text, ≤500 chars |

After publishing:
- `ink publish` writes local publishing artifacts and updates `status` to `drafted`
- `ink syndicate` promotes a `drafted` article to `published` and writes `published_at`
- `ink publish --push` promotes a `ready` article to `published` in one step
- Each publish attempt is recorded under `.ink/publish-history/`

---

##### `ink build`

Generate a static HTML site to `_site/`.

```bash
ink build          # Published articles only (default)
ink build --include-drafted  # Include drafted articles for local preview
ink build --all    # All articles
```

**Output:**
- `_site/index.html` — Homepage (article list + stats)
- `_site/YYYY/MM/DD-slug/index.html` — Article pages
- `_site/feed.xml` — RSS/Atom feed (latest 20 published articles)

By default only `published` articles are built. Use `--include-drafted` for local drafted previews.

---

##### `ink doctor`

Workspace maintenance.

```bash
ink doctor --migrate-status
```

`--migrate-status` migrates legacy `published` articles without `published_at` to `drafted`; articles with `published_at` remain `published`.

---

##### `ink skills list`

List all registered skills (built-in + custom), including source labels.

```bash
ink skills list
```

---

#### Agent Mode Commands

The following commands are available when `mode: agent` is configured, providing journal logging, memory recall, and skill management for AI Agents.

##### `ink log`

Append a timestamped, categorized entry to today's journal.

```bash
ink log "Learned about Rust ownership today"
ink log "Finished search module refactor" --category work
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| `content` | Entry content (required) | — |
| `--category` | Category: `work`, `learning`, `skill-installed`, `memory`, `note` | `agent.default_category` (default `note`) |

Journal files are stored at `YYYY/MM/DD-journal/index.md`, reusing the article three-layer context structure.

---

##### `ink recall`

Search past journal entries, returns structured JSON.

```bash
ink recall                              # Latest entries
ink recall "Rust"                       # Keyword search
ink recall --category learning          # Filter by category
ink recall --since 2026-04-01           # Filter by date
ink recall "search" --limit 5           # Limit results
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| `query` | Search keyword (optional) | Empty (latest entries) |
| `--category` | Filter by category | No filter |
| `--since` | Only entries on or after this date (`YYYY-MM-DD`) | No filter |
| `--limit` | Max results (1–500) | `20` |

---

##### `ink serve`

Start HTTP API server exposing `/log`, `/recall`, `/health` endpoints.

```bash
ink serve
```

Requires `agent.http_api.enabled: true` in config. Default port: `4242`.

---

##### `ink skill-record`

Record an external skill to `_index/skills.json`.

```bash
ink skill-record my-skill --source https://example.com/skill.md --version 1.0
```

---

##### `ink skill-save`

Save a custom skill `.md` file to `.ink/skills/`.

```bash
ink skill-save summarize --file ./my-summarize-skill.md
```

---

##### `ink skill-list`

List all recorded skills (external + custom).

```bash
ink skill-list
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
├── YYYY/MM/DD-journal/       # Agent journal directories (agent mode)
│   ├── index.md              # Journal body (timestamped entries)
│   ├── .abstract             # L0 summary
│   └── .overview             # L1 overview
├── .ink/                     # Workspace metadata
│   ├── config.yaml           # Project config
│   ├── sessions/             # Operation logs (gitignore)
│   ├── publish-history/      # Publish history (gitignore)
│   ├── publish-output/       # Publish output files (gitignore)
│   └── skills/               # Custom skill definitions
├── _index/                   # Global indexes (derived data, rebuildable)
│   ├── timeline.json         # Timeline index
│   ├── graph.json            # Knowledge graph
│   └── skills.json           # Skill registry (agent mode)
├── _site/                    # Static site output (gitignore)
├── _templates/               # Article templates
│   ├── default/              # Default template
│   ├── tech-review/          # Tech review template
│   └── weekly-report/        # Weekly report template
├── ink_core/                 # Source code
├── tests/                    # Tests
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
mode: human   # "human" | "agent"

site:
  title: "My Blog"
  subtitle: ""
  author: ""
  base_url: ""

# Agent mode config (only effective when mode: agent)
agent:
  agent_name: "OpenClaw"
  auto_create_daily: true
  default_category: "note"
  disable_human_commands: false
  http_api:
    enabled: false
    port: 4242

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

In v0.4.0, file-defined skills use a strict DSL executor with only these commands:

```text
read_content <L0|L1|L2>
write_file <path>
```

`write_file` requires a relative path and writes only under `.ink/skill-output/`.

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

**Dev dependencies:** `pytest>=7.0`, `hypothesis>=6.0`, `pypinyin>=0.50`, `mistune>=3.0`

**Versioning:** Follows [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`). Version is maintained in `pyproject.toml` and the top of `README.md`. Releases use annotated tags (`git tag -a vX.Y.Z`). See `.kiro/specs/ink-kernel-architecture/design.md` Chapter 13 for the full release process and branching strategy.

**Version History:**

| Version | Date | Summary |
|---------|------|---------|
| v0.4.1 | 2026-04-11 | Publish state machine: drafted/syndicate/publish --push/build --include-drafted, CLI labels |
| v0.4.0 | 2026-04-11 | Engineering hardening: Chinese slugs, Markdown/XSS safety, template autoescape, strict SkillExecutor, publish status fix |
| v0.3.0 | 2026-04-11 | Agent mode (log/recall/serve/skill-*), property tests, docs consolidation |
| v0.2.0 | 2026-04-05 | Static site generation, layered config, improved init |
