# Ink Blog Core

基于 **CLI + Skills + Markdown** 的个人博客系统核心层。

遵循 **FS-as-DB** 哲学：本地文件系统作为唯一数据存储，目录结构表达关系，Markdown 作为内容源，自然语言或显式命令驱动 Skills 执行。

## 安装

```bash
pip install -e .
```

## 快速开始

```bash
# 初始化 Git 仓库
ink init

# 创建文章
ink new "我的第一篇文章" --tags ai,python

# 重建所有派生文件（.abstract / .overview / timeline.json）
ink rebuild

# 分析文章
ink analyze 2025/03/20-my-first-post

# 搜索
ink search "关键词"

# 发布
ink publish 2025/03/20-my-first-post --channels blog,newsletter,mastodon

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
├── sessions/       # 操作记录（不纳入 Git）
├── publish-history/ # 发布记录
└── skills/         # 自定义 Skill 定义文件（.md）

_index/
├── timeline.json   # 时间线索引
└── graph.json      # 知识图谱（由 analyze 生成）
```

## Article 状态流转

```
draft → review → ready → published → archived
```

只有 `status=ready` 的文章才能发布。

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

## 开发

```bash
# 运行测试
pytest tests/

# 查看测试覆盖
pytest tests/ -v
```

## 配置

全局配置位于 `~/.ink/config.yaml`：

```yaml
site:
  title: "My Blog"
  author: "Anonymous"
channels:
  blog:
    type: static
    output: "./_site"
ai:
  provider: "none"   # none | ollama | openai | anthropic
search:
  engine: "keyword"  # keyword | fulltext
git:
  auto_commit: true
```
