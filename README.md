# Ink Blog Core

基于 **CLI + Skills + Markdown** 的个人博客系统核心层。

遵循 **FS-as-DB** 哲学：本地文件系统作为唯一数据存储，目录结构表达关系，Markdown 作为内容源，自然语言或显式命令驱动操作执行。

---

## 目录

- [安装](#安装)
- [快速开始](#快速开始)
- [命令参考](#命令参考)
- [目录结构](#目录结构)
- [文章生命周期](#文章生命周期)
- [配置](#配置)
- [静态站生成](#静态站生成)
- [自定义模板](#自定义模板)
- [自定义 Skills](#自定义-skills)
- [部署](#部署)
- [开发](#开发)

---

## 安装

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

## 快速开始

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

## 命令参考

### `ink init`

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

### `ink new`

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

### `ink rebuild`

重建所有文章的派生文件（`.abstract`、`.overview`）和时间线索引（`_index/timeline.json`）。

```bash
ink rebuild
```

适用场景：批量修改文章内容后、`.abstract`/`.overview` 文件损坏或丢失时。

---

### `ink analyze`

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

### `ink search`

在文章库中搜索，默认先搜 L0（摘要），不足 3 条时自动扩展到 L1（概览）。

```bash
ink search "关键词"
ink search "关键词" --tag ai          # 按标签过滤
ink search "关键词" --fulltext        # 启用全文搜索（L2）
```

**排序规则（优先级从高到低）：** 标题命中 → 标签命中 → L0 命中 → L1 命中 → L2 命中，同层级按命中次数降序，再按日期降序。

---

### `ink publish`

将文章发布到指定渠道。**文章 `status` 必须为 `ready` 才能发布。**

```bash
# 发布到单个渠道
ink publish 2025/03/20-my-post --channels blog

# 发布到多个渠道
ink publish 2025/03/20-my-post --channels blog,newsletter,mastodon

# 发布所有 ready 状态的文章
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

### `ink build`

生成静态 HTML 站点，输出到 `_site/`（可通过配置修改）。

```bash
# 只生成 status=published 的文章（默认）
ink build

# 生成所有状态的文章
ink build --all
```

**生成内容：**
- `_site/index.html` — 首页（文章列表 + 统计信息）
- `_site/YYYY/MM/DD-slug/index.html` — 每篇文章页面
- `_site/feed.xml` — RSS/Atom 订阅源（最近 20 篇已发布文章）

---

### `ink skills list`

列出所有已注册的 Skills（内置 + 自定义）。

```bash
ink skills list
```

---

## 目录结构

```
项目根目录/
├── YYYY/MM/DD-slug/          # 文章目录（按日期组织）
│   ├── index.md              # L2: 文章正文（Source of Truth）
│   ├── .abstract             # L0: 单行摘要，≤200 字符（系统派生，可重建）
│   ├── .overview             # L1: YAML frontmatter + Markdown 章节（系统派生，可重建）
│   └── assets/               # 图片等资源文件
│
├── .ink/                     # 工作区元数据
│   ├── config.yaml           # 项目配置（提交到 Git）
│   ├── sessions/             # 操作记录（不提交到 Git）
│   ├── publish-history/      # 发布历史（不提交到 Git）
│   ├── publish-output/       # 发布输出文件（不提交到 Git）
│   └── skills/               # 自定义 Skill 定义文件（.md）
│
├── _index/                   # 全局索引（可重建，不提交到 Git）
│   ├── timeline.json         # 时间线索引（由 new/rebuild 维护）
│   └── graph.json            # 知识图谱（由 analyze 生成）
│
├── _site/                    # 静态站输出（由 build 生成，不提交到 Git）
│   ├── index.html
│   ├── feed.xml
│   └── YYYY/MM/DD-slug/index.html
│
├── _templates/               # 文章模板
│   ├── default/              # 默认模板
│   ├── tech-review/          # 技术评测模板
│   └── site/                 # 静态站 HTML 模板（可选，覆盖内置样式）
│
├── .ink/config.yaml          # 项目配置
├── .gitignore
├── pyproject.toml
└── README.md
```

---

## 文章生命周期

### 状态流转

```
draft → review → ready → published → archived
```

| 状态 | 说明 |
|------|------|
| `draft` | 草稿，新建文章的默认状态 |
| `review` | 审阅中 |
| `ready` | 准备发布，`ink publish` 的前置条件 |
| `published` | 已发布，`ink build` 默认只生成此状态的页面 |
| `archived` | 已归档，不出现在搜索和列表中 |

### index.md frontmatter 格式

```yaml
---
title: "文章标题"
slug: "article-slug"
date: "2025-03-20"
status: "draft"
tags: ["ai", "python"]
---

# 文章标题

正文内容...
```

### 三层上下文

| 层级 | 文件 | 内容 | 用途 |
|------|------|------|------|
| L0 | `.abstract` | 单行纯文本，≤200 字符 | 搜索摘要、RSS 描述 |
| L1 | `.overview` | YAML frontmatter + Summary + Key Points | 搜索扩展、分析 |
| L2 | `index.md` | 完整 Markdown 正文 | Source of Truth |

L0 和 L1 是系统派生文件，由 `ink new` 和 `ink rebuild` 自动生成，删除后可重建。

---

## 配置

### 配置优先级（高 → 低）

1. `.ink/config.yaml` — **项目级配置**，随代码提交 Git，优先级最高
2. `~/.ink/config.yaml` — 全局用户配置，跨项目共享
3. 内置默认值

### 完整配置项

```yaml
# .ink/config.yaml

site:
  title: "My Blog"          # 站点标题，显示在首页和文章页
  subtitle: ""              # 站点副标题，显示在首页 header
  author: ""                # 作者名，显示在 footer 和 RSS
  base_url: ""              # 部署后的完整域名，用于 RSS 链接
                            # 例：https://blog.example.com

channels:
  blog:
    type: static
    output: "./_site"       # 静态站输出目录（相对路径或绝对路径）

search:
  engine: keyword           # keyword（默认）| fulltext（全文搜索）
  top_k: 10                 # 搜索返回最大条数

git:
  auto_commit: true         # 写操作后自动 Git commit
```

---

## 静态站生成

### 工作流程

```
ink build
  ↓
读取 _index/timeline.json（文章顺序）
  ↓
过滤 status=published 的文章
  ↓
为每篇文章生成 _site/YYYY/MM/DD-slug/index.html
  ↓
生成 _site/index.html（首页）
  ↓
生成 _site/feed.xml（RSS/Atom）
  ↓
触发 Git commit: "build: regenerate static site"
```

### 本地预览

生成后直接用浏览器打开 `_site/index.html`，所有链接均为相对路径，无需 web server。

```bash
ink build
open _site/index.html      # macOS
# 或
xdg-open _site/index.html  # Linux
```

---

## 自定义模板

在 `_templates/site/` 下放置 Jinja2 模板文件，优先于内置默认模板。

```
_templates/site/
├── article.html    # 文章页面模板
└── index.html      # 首页模板
```

### 文章页模板变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `title` | str | 文章标题 |
| `site_title` | str | 站点标题 |
| `date` | str | 文章日期，格式 `YYYY-MM-DD` |
| `tags` | list[str] | 标签列表 |
| `abstract` | str | L0 摘要文本 |
| `body_html` | str | 正文 HTML（已转换，直接输出） |
| `canonical_id` | str | 文章唯一标识，格式 `YYYY/MM/DD-slug` |

### 首页模板变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `site_title` | str | 站点标题 |
| `site_subtitle` | str | 站点副标题 |
| `site_author` | str | 作者名 |
| `year` | str | 当前年份 |
| `articles` | list[dict] | 文章列表（见下） |
| `total_articles` | int | 文章总数 |
| `total_words` | str | 总字数估算，如 `~48k` |
| `date_range` | str | 日期范围，如 `2025-03-15 至 2026-04-04` |

每篇文章 dict 包含：`canonical_id`、`title`、`date`、`tags`、`abstract`、`word_count`

### 模板示例

```html
<!-- _templates/site/article.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <title>{{ title }} - {{ site_title }}</title>
</head>
<body>
  <nav><a href="../../../index.html">← 返回</a></nav>
  <h1>{{ title }}</h1>
  <p>{{ date }} · {% for t in tags %}#{{ t }} {% endfor %}</p>
  <div>{{ body_html }}</div>
</body>
</html>
```

---

## 自定义 Skills

在 `.ink/skills/` 下创建 `.md` 文件即可注册新 Skill，`ink init` 后自动加载。

```yaml
---
skill: summarize
version: "1.0"
description: 生成文章摘要
context_requirement: L2
---

## 输入
- source: 文章 Canonical ID

## 执行流程
1. 读取 index.md 内容
2. 生成摘要
3. 更新 .abstract
```

**必填 frontmatter 字段：** `skill`、`version`、`context_requirement`

缺少任一字段时，该文件会被跳过并输出警告。

---

## 部署

`ink build` 生成的 `_site/` 是纯静态文件，可部署到任何静态托管服务。

### GitHub Pages

```bash
# 方式一：直接推送 _site/ 到 gh-pages 分支
git subtree push --prefix _site origin gh-pages

# 方式二：使用 GitHub Actions（推荐）
# 在 .github/workflows/deploy.yml 中配置：
# 1. 安装依赖：pip install -e .
# 2. 执行构建：ink build
# 3. 部署 _site/ 到 GitHub Pages
```

在 `.ink/config.yaml` 中设置 `site.base_url` 为 GitHub Pages 地址，RSS 链接会自动使用完整 URL：

```yaml
site:
  base_url: "https://username.github.io/repo-name"
```

### Netlify / Vercel

```bash
# 构建命令
pip install -e . && ink build

# 发布目录
_site
```

### 本地 HTTP 服务器

```bash
cd _site
python -m http.server 8000
# 访问 http://localhost:8000
```

---

## 开发

```bash
# 安装（含开发依赖）
pip install -e ".[dev]"

# 运行全量测试
pytest tests/

# 详细输出
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_site.py -v
```

### 项目结构

```
ink_core/
├── cli/
│   ├── builtin.py    # 内置命令：new, init, rebuild, build, skills
│   ├── intent.py     # NLParser, IntentRouter
│   └── parser.py     # CLI 入口（argparse + NLP）
├── core/
│   ├── config.py     # 分层配置管理
│   ├── executor.py   # 命令执行事务协调器
│   ├── session.py    # 操作记录
│   ├── publish_history.py
│   └── errors.py     # 领域异常
├── fs/
│   ├── article.py    # Article 数据模型 + ArticleManager
│   ├── layer_generator.py  # L0/L1 生成器
│   ├── index_manager.py    # timeline.json / graph.json
│   └── markdown.py   # frontmatter 解析工具
├── git/
│   └── manager.py    # Git 操作封装
├── site/
│   ├── builder.py    # SiteBuilder
│   ├── renderer.py   # Jinja2 模板渲染器
│   └── rss.py        # RSS/Atom feed 生成器
└── skills/
    ├── publish.py    # PublishSkill + 渠道适配器
    ├── analyze.py    # AnalyzeSkill + Wiki 链接解析
    ├── search.py     # SearchSkill（分层搜索）
    ├── registry.py   # Skill 注册表
    └── loader.py     # Skill 文件加载器
```

### 依赖

| 包 | 用途 |
|----|------|
| `pyyaml>=6.0` | YAML 解析（frontmatter、配置文件） |
| `jinja2>=3.1` | 静态站 HTML 模板渲染 |

开发依赖：`pytest>=7.0`、`hypothesis>=6.0`（属性测试）
