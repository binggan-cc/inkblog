# Liquid Blog - 基于 Skills + Markdown 的个人博客系统

> 🌊 **Liquid CLI 理念**：像水一样适应容器，意图驱动的交互界面

## 核心概念

| 概念 | 定义 | 类比 |
|------|------|------|
| **Liquid CLI** | 根据上下文动态生成的交互界面 | 水适应容器 |
| **Skills** | 可复用的 AI 能力单元，自文档化的 Markdown 文件 | 数字乐高 |
| **Ink** | Intent + Note + Knowledge 三位一体 | 数字墨水 |
| **FS-as-DB** | 文件系统即数据库，路径即关系 | Unix 哲学 |
| **Semantic Retrieval** | 语义检索，超越关键词的向量化匹配 | 思维导图 |

## 三层上下文架构

```
L0 (摘要)  →  一句话总结，用于快速检索
     ↓
L1 (概览)  →  核心信息、适用场景、关联文章
     ↓
L2 (详情)  →  完整原始数据，按需加载
```

**优势**：Token 成本降低 90%，检索精度提升

## 快速开始

```bash
# 1. 创建新文章
ink new "我的第一篇博客"

# 2. 智能编辑（AI 辅助）
ink edit 2025/03/20-my-first-post/

# 3. 发布到多平台
ink publish 2025/03/20-my-first-post/ --channels blog,mastodon

# 4. 语义搜索
ink search "关于 AI 开发的最佳实践"

# 5. 分析博客数据
ink analyze --type stats --period month
```

## 目录结构

```
~/ink/                          # Blog 宇宙，只是一个文件夹
├── .ink/                       # 系统目录
│   ├── skills/                 # 能力定义（可执行 Markdown）
│   │   ├── publish.md
│   │   ├── analyze.md
│   │   └── search.md
│   ├── workflows/              # 编排剧本
│   │   └── morning-routine.md
│   ├── sessions/               # 会话记忆（自动迭代）
│   └── config.yaml             # 全局配置
│
├── 2025/                       # 年份
│   └── 03/                     # 月份
│       └── 20-liquid-blog/     # 文章即文件夹
│           ├── .abstract       # L0：一句话摘要
│           ├── .overview       # L1：结构化概览
│           ├── index.md        # L2：完整内容
│           ├── assets/         # 资源文件
│           │   └── cover.png
│           └── comments/       # 评论数据
│
├── _index/                     # 全局索引（自动维护）
│   ├── timeline.json           # 时间线索引
│   ├── tags.json               # 标签索引
│   ├── graph.json              # 知识图谱
│   └── stats.json              # 统计数据
│
└── _templates/                 # 文章模板
    ├── default/
    ├── tech-review/
    └── weekly-summary/
```

## Skills 详解

### 1. Publish Skill

```yaml
---
skill: publish
version: 2.0
context_requirement: L1  # 执行只需概览层
---

## 输入
- source: 文章路径
- channels: [blog|newsletter|mastodon|x|wechat]

## 执行流程
1. **预处理**：读取 frontmatter，验证 status: ready
2. **渠道适配**：并行生成多平台格式
3. **会话记忆**：记录本次操作到 .ink/sessions/
4. **索引更新**：更新全局 timeline 和知识图谱

## 渠道适配规则

| 渠道 | 格式处理 | 图片处理 | 特殊规则 |
|------|----------|----------|----------|
| Blog | Markdown → HTML | 本地引用 | 生成 RSS |
| Mastodon | 截断 500 字 | 上传图床 | 添加标签 |
| X/Twitter | 截断 280 字 | 上传图床 | 添加话题 |
| Newsletter | 邮件格式 | 嵌入 Base64 | 生成 TOC |
| WeChat | 微信排版 | 上传 CDN | 添加版权 |
```

### 2. Analyze Skill

```yaml
---
skill: analyze
version: 1.0
context_requirement: L2
---

## 分析维度

### 内容分析
- 阅读难度 (Flesch-Kincaid)
- 情感倾向
- 关键词提取
- 主题分类

### 数据分析
- 阅读量趋势
- 来源分布
- 互动率
- 转化漏斗

### 知识图谱
- 实体识别
- 关系抽取
- 关联文章推荐
```

### 3. Search Skill

```yaml
---
skill: search
version: 1.5
context_requirement: L0
---

## 搜索模式

### 1. 语义搜索（默认）
```bash
ink search "关于 AI 开发的最佳实践"
```
使用向量相似度，返回语义相关结果

### 2. 关键词搜索
```bash
ink search "TODO" --mode keyword
```
传统关键词匹配

### 3. 结构化搜索
```bash
ink search "tag:ai AND date>2025-01-01"
```
支持类 SQL 的查询语法

### 4. 混合搜索
```bash
ink search "部署技巧" --context "Kubernetes Docker"
```
语义 + 上下文增强
```

## 文章生命周期

```
草稿 (draft)
    ↓ (edit)
审核中 (review)
    ↓ (ready)
待发布 (ready)
    ↓ (publish)
已发布 (published)
    ↓ (archive)
已归档 (archived)
```

## 安装

```bash
# 克隆仓库
git clone https://github.com/yourname/liquid-blog.git ~/ink
cd ~/ink

# 安装依赖
pip install -r requirements.txt

# 初始化
ink init

# 配置
vim .ink/config.yaml
```

## 配置文件

```yaml
# .ink/config.yaml
site:
  title: "My Liquid Blog"
  description: "A blog powered by Skills"
  url: "https://yourblog.com"
  author: "Your Name"

channels:
  blog:
    type: static
    output: "./_site"
    theme: "minimal"
  
  mastodon:
    instance: "mastodon.social"
    token: "${MASTODON_TOKEN}"
  
  x:
    api_key: "${X_API_KEY}"
    api_secret: "${X_API_SECRET}"

ai:
  provider: "openai"
  model: "gpt-4"
  embedding_model: "text-embedding-3-small"

search:
  engine: "semantic"  # semantic | keyword | hybrid
  top_k: 10
```

## 贡献

欢迎提交 Skills！一个 Skill 就是一个 Markdown 文件，包含：
- Frontmatter 元数据
- 使用文档
- 执行逻辑（代码块）

---

*Built with 💧 Liquid Philosophy*
