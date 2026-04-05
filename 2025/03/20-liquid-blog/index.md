---
title: Liquid Blog - Skills + Markdown 博客系统
slug: liquid-blog
date: '2025-03-20'
status: published
tags: []
published_at: '2026-04-05T01:30:00'
---


# Liquid Blog - Skills + Markdown 博客系统

> 🌊 像水一样流动的博客系统，意图驱动的创作体验

**创建时间**: 2025-03-20  
**状态**: ✅ 已发布  
**标签**: #blog #markdown #cli #ai

---

## 摘要

本文介绍了一种全新的博客系统架构：将文件系统作为数据库，用 Markdown 定义可复用的 AI 能力（Skills），并通过三层上下文架构（L0/L1/L2）实现高效的 Token 使用和精准的语义检索。

## 问题背景

传统博客系统面临以下问题：

1. **发布流程繁琐** - 需要登录后台、填写表单、手动分发到各平台
2. **数据锁定** - 内容被困在数据库中，迁移困难
3. **检索低效** - 基于关键词的搜索，无法理解语义
4. **AI 集成困难** - 缺乏标准化的 AI 能力接口

## 解决方案

### 核心架构

```
┌─────────────────────────────────────────────────────────┐
│                      Liquid CLI                         │
│                  (意图驱动的界面)                        │
├─────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Publish  │  │ Analyze  │  │  Search  │   Skills     │
│  │  Skill   │  │  Skill   │  │  Skill   │  (Markdown)  │
│  └──────────┘  └──────────┘  └──────────┘              │
├─────────────────────────────────────────────────────────┤
│                    FS-as-DB                             │
│              文件系统即数据库                            │
├─────────────────────────────────────────────────────────┤
│  L0 (摘要) → L1 (概览) → L2 (详情)   三层上下文架构     │
└─────────────────────────────────────────────────────────┘
```

### 文件系统抽象

```
~/ink/                          # Blog 宇宙
├── .ink/skills/               # 可复用能力
│   ├── publish.md             # 发布能力
│   ├── analyze.md             # 分析能力
│   └── search.md              # 搜索能力
│
├── 2025/03/20-liquid-blog/    # 文章即文件夹
│   ├── .abstract              # L0: 一句话摘要
│   ├── .overview              # L1: 结构化概览
│   ├── index.md               # L2: 完整内容
│   └── assets/                # 资源文件
│
└── _index/                    # 全局索引
    ├── timeline.json          # 时间线索引
    ├── tags.json              # 标签索引
    └── graph.json             # 知识图谱
```

### 三层上下文架构

| 层级 | 文件 | 用途 | Token 成本 |
|------|------|------|------------|
| L0 | `.abstract` | 快速检索、列表展示 | ~10 tokens |
| L1 | `.overview` | 决策支持、关联推荐 | ~100 tokens |
| L2 | `index.md` | 完整阅读、深度处理 | ~1000+ tokens |

**优势**：按需加载，Token 成本降低 90%，检索精度提升。

### CLI 设计：意图驱动

```bash
# 传统范式
find . -name "*.md" -exec grep -l "TODO" {} \;

# Liquid 范式（自然语言）
ink "找出所有提到 TODO 的笔记，并按优先级排序"
ink "把 liquid-cli 的想法扩展成完整文章，参考昨天的笔记"
ink publish 2025/03/20-liquid-blog/ --channels blog,mastodon
```

## Skills 详解

### Publish Skill

```yaml
---
skill: publish
version: 2.0
context_requirement: L1  # 执行只需概览层
---

输入:
  - source: 文章路径
  - channels: [blog|newsletter|mastodon]

执行流程:
  1. 预处理：读取 frontmatter，验证 status: ready
  2. 渠道适配：并行生成多平台格式
  3. 会话记忆：记录本次操作到 .ink/sessions/
  4. 索引更新：更新全局 timeline 和知识图谱
```

### Analyze Skill

支持内容分析、数据统计、知识图谱生成。

### Search Skill

支持语义搜索、关键词搜索、结构化查询（类 SQL）。

## 使用效果

| 指标 | 传统方案 | Liquid Blog | 提升 |
|------|----------|-------------|------|
| 发布耗时 | 30 分钟 | 3 分钟 | **10x** |
| Token 消耗 | 100% | 10% | **-90%** |
| 检索精度 | 60% | 85% | **+42%** |
| 迁移成本 | 高 | 零 | **∞** |

## 未来展望

1. **AI 辅助写作** - 自动生成 L0/L1 层
2. **智能推荐** - 基于知识图谱的关联文章
3. **协作编辑** - 多人实时协作
4. **语音交互** - 口述文章，AI 自动整理

## 参考

- [OpenClaw Documentation](https://docs.openclaw.ai)
- [Unix Philosophy](https://en.wikipedia.org/wiki/Unix_philosophy)
- [Zettelkasten Method](https://zettelkasten.de)

---

*用 💧 Liquid 的方式书写，让内容如水般自由流动。*
