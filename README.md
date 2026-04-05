# Ink Blog Core

基于 **CLI + Skills + Markdown** 的个人博客系统核心层。

遵循 **FS-as-DB** 哲学：本地文件系统作为唯一数据存储，目录结构表达关系，Markdown 作为内容源，自然语言或显式命令驱动 Skills 执行。

## 安装

```bash
pip install -e .
```

## 快速开始

```bash
# 初始化工作区（创建 .ink/ 目录结构、config.yaml、Git 仓库）
ink init

# 创建文章
ink new "我的第一篇文章" --tags ai,python

# 重建所有派生文件（.abstract / .overview / timeline.json）
ink rebuild

# 分析文章（生成 graph.json）
ink analyze 2025/03/20-my-first-post

# 全库分析
ink analyze --all

# 搜索
ink search "关键词"
ink search "关键词" --tag ai
ink search "关键词" --fulltext

# 发布（status 需为 ready）
ink publish 2025/03/20-my-first-post --channels blog,newsletter,mastodon

# 生成静态站（输出到 _site/）
ink build

# 生成静态站（包含所有状态的文章）
ink build --all

# 列出已注册 Skills
ink skills list
```

## 目录结构

```
YYYY/MM/DD-slug/
├── index.md        # L2: 完整内容（Source of Truth）
├── .abstract       # L0: 单行摘要，≤200 字符（系统派生）
├── .overview       # L1: YAML frontmatter + Markdown 章节（系统派生）
└── assets/

.ink/
├── config.yaml         # 项目配置（站点标题、作者等）
├── sessions/           # 操作记录（不纳入 Git）
├── publish-history/    # 发布记录（不纳入 Git）
└── skills/             # 自定义 Skill 定义文件（.md）

_index/
├── timeline.json   # 时间线索引（由 rebuild/new 维护）
└── graph.json      # 知识图谱（由 analyze 生成）

_site/              # 静态站输出（由 build 生成，不纳入 Git）
├── index.html
├── feed.xml
└── YYYY/MM/DD-slug/index.html
```

## Article 状态流转

```
draft → review → ready → published → archived
```

只有 `status=ready` 的文章才能发布（`ink publish`）。`ink build` 默认只生成 `status=published` 的文章页面。

## 配置

`ink init` 会在项目目录自动生成 `.ink/config.yaml`，编辑后重新 `ink build` 即可生效。

**配置优先级（高 → 低）：**
1. `.ink/config.yaml`（项目级，随代码提交 Git）
2. `~/.ink/config.yaml`（全局用户配置）
3. 内置默认值

```yaml
# .ink/config.yaml
site:
  title: "My Blog"
  subtitle: ""
  author: ""
  base_url: ""        # 部署后的域名，用于 RSS feed 链接

channels:
  blog:
    type: static
    output: "./_site"  # 静态站输出目录

search:
  engine: keyword      # keyword | fulltext
  top_k: 10

git:
  auto_commit: true
```

## 自定义 Skills

在 `.ink/skills/` 下创建 `.md` 文件即可注册新 Skill：

```yaml
---
skill: my-skill
version: 1.0
description: 我的自定义能力
context_requirement: L1
---

## 输入
- source: 文章路径

## 执行流程
1. 读取文章
2. 执行操作
```

## 自定义站点模板

在 `_templates/site/` 下放置 Jinja2 模板文件，优先于内置默认模板：

- `article.html` — 文章页面模板
- `index.html` — 首页模板

模板变量：
- 文章页：`title`, `date`, `tags`, `abstract`, `body_html`, `site_title`
- 首页：`site_title`, `site_subtitle`, `site_author`, `articles`, `total_articles`, `total_words`, `date_range`

## 开发

```bash
# 安装（含开发依赖）
pip install -e ".[dev]"

# 运行测试
pytest tests/

# 详细输出
pytest tests/ -v
```

## 依赖

- Python ≥ 3.11
- `pyyaml` — YAML 解析
- `jinja2` — 静态站模板渲染
