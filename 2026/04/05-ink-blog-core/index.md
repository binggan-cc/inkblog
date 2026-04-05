---
title: Ink Blog Core 使用指南
slug: ink-blog-core
date: '2026-04-05'
status: published
tags:
- ink
- blog
- tutorial
published_at: '2026-04-05T02:19:21'
---


# Ink Blog Core 使用指南

Ink Blog Core 是一个基于 CLI + Skills + Markdown 的个人博客系统，遵循 FS-as-DB 哲学，以本地文件系统作为唯一数据存储。

## 核心理念

### FS-as-DB

不依赖数据库，目录结构即关系，Markdown 文件即数据。所有内容都是人类可读的纯文本，天然适合 Git 版本控制。

### 三层上下文

每篇文章维护三个层级的内容：

| 层级 | 文件 | 内容 |
|------|------|------|
| L0 | `.abstract` | 单行摘要，≤200 字符 |
| L1 | `.overview` | YAML frontmatter + 结构化概览 |
| L2 | `index.md` | 完整正文（Source of Truth） |

L0 和 L1 由系统自动生成，删除后可通过 `ink rebuild` 重建。

## 快速上手

### 初始化

```bash
ink init
```

执行后会创建 `.ink/` 目录结构、默认配置文件，并初始化 Git 仓库。

### 创建文章

```bash
ink new "我的第一篇文章" --tags ai,python
```

系统自动生成 `YYYY/MM/DD-slug/` 目录，包含 `index.md`、`.abstract`、`.overview`、`assets/`。

### 发布流程

1. 编辑 `index.md` 写入内容
2. 将 `status` 改为 `ready`
3. 执行 `ink publish <canonical-id> --channels blog`
4. 执行 `ink build` 生成静态站

## 搜索功能

Ink 支持分层搜索，默认先搜 L0（摘要），不足 3 条时自动扩展到 L1（概览）：

```bash
ink search "关键词"
ink search "关键词" --tag ai
ink search "关键词" --fulltext  # 全文搜索
```

## 知识图谱

通过 Wiki 链接语法建立文章间的关联：

```markdown
参见 [[另一篇文章]] 或精确引用 [[2026/04/05-ink-blog-core]]
```

执行 `ink analyze --all` 后生成 `_index/graph.json`，记录所有文章的链接关系。

## 静态站生成

```bash
ink build
```

生成 `_site/` 目录，包含首页、所有文章页面和 RSS feed，可直接部署到 GitHub Pages 或 Netlify。
