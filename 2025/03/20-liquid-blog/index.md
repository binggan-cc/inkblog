---
title: Ink Blog Core：FS-as-DB 博客系统的设计与实现
slug: liquid-blog
date: '2025-03-20'
status: published
tags:
- ink
- blog
- cli
- markdown
- fs-as-db
published_at: '2026-04-05T01:30:00'
---

# Ink Blog Core：FS-as-DB 博客系统的设计与实现

> 🌊 文件系统即数据库，意图驱动的内容创作体验

这篇文章记录了 Ink Blog Core 的设计理念和实现过程。从一个想法出发：**如果把文件系统当作数据库，博客系统可以有多简单？**

---

## 核心理念

### FS-as-DB

不依赖任何外部数据库。目录结构表达关系，Markdown 文件即数据，Git 提供版本控制。所有内容都是人类可读的纯文本，可以用任何编辑器打开，可以直接 `grep`，可以随时迁移。

```
2025/03/20-liquid-blog/   ← 路径即 ID（Canonical ID）
├── index.md              ← L2: 完整内容（Source of Truth）
├── .abstract             ← L0: 单行摘要，≤200 字符
├── .overview             ← L1: YAML frontmatter + 结构化概览
└── assets/
```

### 三层上下文

每篇文章维护三个层级，按需加载，大幅降低 AI 检索的 Token 成本：

| 层级 | 文件 | 内容 | 典型用途 |
|------|------|------|----------|
| L0 | `.abstract` | 单行纯文本，≤200 字符 | 搜索摘要、列表展示、RSS 描述 |
| L1 | `.overview` | YAML frontmatter + Summary + Key Points | 搜索扩展、分析、关联推荐 |
| L2 | `index.md` | 完整 Markdown 正文 | 阅读、发布、深度处理 |

L0 和 L1 是系统派生文件，由 `ink new` 和 `ink rebuild` 自动生成，删除后可重建。

### Skills 体系

能力以 Markdown 文件定义，自文档化、可版本控制、可扩展：

```yaml
---
skill: publish
version: "1.0"
context_requirement: L2
description: 发布文章到多个渠道
---

## 输入
- source: 文章 Canonical ID
- channels: [blog|newsletter|mastodon]

## 执行流程
1. 读取 index.md frontmatter，验证 status=ready
2. 为每个渠道生成对应格式
3. 更新 status=published，写入 published_at
4. 更新 _index/timeline.json
5. 记录发布历史到 .ink/publish-history/
```

---

## 实现架构

```
┌─────────────────────────────────────────────────────────┐
│                      ink CLI                            │
│         argparse 子命令 + NLP 自然语言路由               │
├─────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ publish  │  │ analyze  │  │  search  │   Skills     │
│  │  Skill   │  │  Skill   │  │  Skill   │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │   new    │  │  init    │  │  build   │  Builtins    │
│  └──────────┘  └──────────┘  └──────────┘              │
├─────────────────────────────────────────────────────────┤
│              Core Services                              │
│   ArticleManager · IndexManager · GitManager            │
│   SessionLogger · PublishHistoryManager · InkConfig     │
├─────────────────────────────────────────────────────────┤
│                    FS-as-DB                             │
│         YYYY/MM/DD-slug/ · _index/ · .ink/              │
└─────────────────────────────────────────────────────────┘
```

---

## 完整工作流

### 初始化

```bash
ink init
# ✅ 创建 .ink/ 目录结构
# ✅ 生成 .ink/config.yaml
# ✅ 初始化 Git 仓库
```

### 创建文章

```bash
ink new "我的第一篇文章" --tags ai,python
# 生成 2025/03/20-my-first-article/
# ├── index.md      ← 自动填充 frontmatter
# ├── .abstract     ← 自动生成 L0 摘要
# ├── .overview     ← 自动生成 L1 概览
# └── assets/
```

### 发布

```bash
# 将 index.md 中 status 改为 ready，然后：
ink publish 2025/03/20-my-first-article --channels blog,newsletter,mastodon
# ✅ status 更新为 published
# ✅ 写入 published_at 时间戳
# ✅ 更新 _index/timeline.json
# ✅ 记录发布历史
```

### 搜索

```bash
ink search "关键词"           # 分层搜索：L0 → L1 → L2
ink search "关键词" --tag ai  # 标签过滤
ink search "关键词" --fulltext # 全文搜索
```

### 知识图谱

```bash
ink analyze --all
# 提取所有文章中的 [[Wiki 链接]]
# 生成 _index/graph.json
# 标记 resolved / ambiguous / unresolved 链接
```

### 生成静态站

```bash
ink build
# 生成 _site/index.html        ← 首页（文章列表 + 统计）
# 生成 _site/YYYY/MM/DD-slug/  ← 每篇文章页面
# 生成 _site/feed.xml          ← RSS/Atom 订阅源
```

---

## 设计决策

### 为什么不用数据库？

- 纯文本文件天然支持 Git diff，每次修改都有完整历史
- 可以用任何工具直接操作：`grep`、`sed`、编辑器、脚本
- 零迁移成本，文件就是数据
- 离线可用，无网络依赖

### 为什么三层上下文？

搜索时不需要加载完整正文。L0 只有一行，L1 有结构化摘要，只有真正需要时才读 L2。在 1000 篇文章规模下，搜索仍然保持毫秒级响应。

### 为什么 Skills 用 Markdown 定义？

Skills 本身就是文档。定义文件即说明书，可以用 `ink skills list` 查看，可以提交到 Git，可以在团队间共享。

---

## 配置

站点信息在 `.ink/config.yaml` 中配置，优先级高于全局配置：

```yaml
site:
  title: "🌱 程老师的数字花园"
  subtitle: "技术、产品与思考的沉淀"
  author: "程老师"
  base_url: "https://blog.example.com"

channels:
  blog:
    output: "./_site"

git:
  auto_commit: true
```

---

## 参考

- [Unix Philosophy](https://en.wikipedia.org/wiki/Unix_philosophy) — 做一件事，做好它
- [Zettelkasten Method](https://zettelkasten.de) — 卡片盒笔记法，知识网络的灵感来源
- [FS-as-DB Pattern](https://martinfowler.com/bliki/TwoHardThings.html) — 文件系统作为数据库的设计模式

---

*用 Ink 的方式书写，让内容在文件系统中自由流动。*
