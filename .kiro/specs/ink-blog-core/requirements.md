# Ink Blog Core（Phase 1）需求文档

## 1. 文档信息

- 项目名称：Ink Blog Core
- 阶段：Phase 1
- 文档类型：Requirement Specification
- 版本：v1.4
- 状态：Draft

---

## 2. 简介

Ink Blog Core（Phase 1）是一个基于 **CLI + Skills + Markdown** 三位一体架构的个人博客系统核心层。

系统遵循 **FS-as-DB（File System as Database）** 哲学，以本地文件系统作为唯一数据存储载体，以目录结构表达关系，以 Markdown 作为内容源，以自然语言或显式命令驱动 Skills 执行内容创作、检索、分析与发布操作。

Phase 1 的目标是交付一个 **单机、本地优先、可版本控制、可扩展** 的博客核心系统，为后续更复杂的发布编排、知识图谱和插件生态提供稳定基础。

---

## 3. Phase 1 范围

### 3.1 In Scope

Phase 1 SHALL 包含以下能力：

1. CLI 基础框架
2. 文件系统抽象与 Article 生命周期管理
3. L0 / L1 / L2 三层上下文生成与维护
4. 基础 Skills：
   - publish
   - analyze
   - search
5. Git 集成
6. Skills 加载与注册机制
7. 本地索引维护（timeline / graph）

### 3.2 Out of Scope

Phase 1 SHALL NOT 包含以下能力：

1. 多用户协作
2. 云端同步与远程存储
3. 外部数据库依赖
4. 向量数据库或语义检索服务
5. 文件系统实时监听守护进程
6. 复杂权限管理
7. 完整的多平台远程发布中心
8. 图形化管理界面

---

## 4. 设计原则

1. **本地优先**：所有核心数据 SHALL 可在本地目录中直接查看和编辑
2. **文本优先**：所有核心内容 SHALL 使用纯文本格式存储
3. **可重建**：所有派生数据（如 `.abstract`、`.overview`、`timeline.json`、`graph.json`）SHALL 可从源文件重新生成
4. **最小依赖**：系统核心 SHALL 不依赖外部数据库
5. **显式可回退**：自然语言输入失败时 SHALL 可回退到显式命令模式
6. **Git 友好**：所有核心数据结构 SHALL 适合版本控制与差异追踪

---

## 5. 词汇表

- **Ink**：系统命名，代表 Intent + Note + Knowledge，同时是 CLI 入口命令
- **FS-as-DB**：文件系统即数据库，路径表达关系，无需外部数据库
- **Article**：一篇文章，对应一个独立文件夹
- **Article Path**：文章目录路径，格式为 `YYYY/MM/DD-slug/`
- **Canonical ID**：Article 的规范唯一标识，格式为 `YYYY/MM/DD-slug`（不含末尾斜杠）
- **L0**：摘要层，对应 `.abstract`
- **L1**：概览层，对应 `.overview`
- **L2**：详情层，对应 `index.md`
- **Skill**：可复用 AI 能力单元，以 Markdown 文件定义
- **Intent**：用户通过自然语言表达的操作意图
- **Global Index**：`_index/` 目录下的全局索引数据
- **Session**：`.ink/sessions/` 下的操作记录
- **Workspace**：当前执行 `ink` 命令的项目根目录
- **Git Repo**：Workspace 对应的 Git 仓库

---

## 6. 数据结构约定

### 6.1 Article 目录结构

每个 Article SHALL 使用如下目录结构：

```text
YYYY/
  MM/
    DD-slug/
      index.md
      .abstract
      .overview
      assets/
```

### 6.2 index.md

`index.md` SHALL 作为 Article 的唯一源内容文件（Source of Truth）。

对于通过 `ink new` 创建的 Article，`index.md` frontmatter SHALL 至少包含以下字段：

- `title`
- `slug`
- `date`
- `status`
- `tags`

对于外部导入或手工创建的 Article，系统 MAY 在首次解析时补全缺失字段，或返回校验错误。

### 6.3 .abstract

`.abstract` SHALL 为单行纯文本摘要，作为 L0 层输入源。

### 6.4 .overview

`.overview` SHALL 使用 YAML frontmatter + Markdown 章节的固定格式：

```markdown
---
title: "文章标题"
created_at: "2025-03-20T10:30:00"
updated_at: "2025-03-20T15:00:00"
status: "draft"
tags: ["ai", "python"]
category: "tech"
word_count: 1500
reading_time_min: 8
related:
  - "2025/03/15-other-article"
---

## Summary

3-5 句核心摘要内容。

## Key Points

- 要点一
- 要点二
```

frontmatter 必填字段：`title`、`created_at`、`updated_at`、`status`、`tags`、`word_count`、`reading_time_min`、`related`

可选字段：`category`（Phase 1 不作为核心索引字段，仅用于展示）

### 6.5 派生文件覆盖规则

- `.abstract` 与 `.overview` SHALL 视为系统派生文件
- 用户 MAY 手工编辑 `.abstract` 或 `.overview`，但 THE System SHALL NOT 保证在后续 `regenerate` / `rebuild` 后保留人工修改内容
- Phase 1 不区分系统托管区与人工补充区；rebuild 时全量覆盖

### 6.6 Article 唯一标识约定

每个 Article 的规范唯一标识（Canonical ID）SHALL 为其相对路径，不包含末尾斜杠，格式为：

`YYYY/MM/DD-slug`

约束规则：

- `title` 用于展示，不保证唯一
- `slug` 用于路径生成，不单独作为全局唯一键
- Canonical ID SHALL 作为以下场景的统一引用键：
  - `_index/timeline.json`
  - `_index/graph.json`
  - `.overview` 中的 `related` 列表
  - Session 记录中的 `target`
  - 发布记录

### 6.7 _index/ 索引文件格式

`_index/` SHALL 至少包含：

- `timeline.json`
- `graph.json`

#### timeline.json 最小结构

```json
[
  {
    "path": "2025/03/20-liquid-blog",
    "title": "Liquid Blog",
    "date": "2025-03-20",
    "status": "published",
    "tags": ["blog", "skills"],
    "updated_at": "2025-03-20T15:00:00"
  }
]
```

必填字段：`path`、`title`、`date`、`status`、`tags`、`updated_at`

其中 `path` SHALL 使用 Canonical ID。

`timeline.json` 中的记录 SHOULD 默认按 `date` 倒序排列；若 `date` 相同，则按 `updated_at` 倒序排列。

#### graph.json 最小结构

```json
{
  "nodes": [
    {
      "id": "2025/03/20-liquid-blog",
      "title": "Liquid Blog",
      "tags": ["blog"]
    }
  ],
  "edges": [
    {
      "source": "2025/03/20-liquid-blog",
      "target": "2025/03/15-other-article",
      "type": "wiki_link"
    }
  ],
  "ambiguous": [
    {
      "source": "2025/03/20-liquid-blog",
      "label": "Liquid Blog",
      "candidates": ["2025/03/15-a", "2025/03/16-b"]
    }
  ],
  "unresolved": [
    {
      "source": "2025/03/20-liquid-blog",
      "label": "某不存在的文章"
    }
  ]
}
```

nodes 必填字段：`id`、`title`、`tags`

edges 必填字段：`source`、`target`、`type`

其中 `id` / `source` / `target` SHALL 使用 Canonical ID。`type` 在 Phase 1 中至少支持 `wiki_link`。

当 Wiki Link 无法解析为唯一 Canonical ID 时，`graph.json` MAY 额外包含以下字段：

- `ambiguous`：歧义链接列表，每条 SHALL 至少包含 `source`（Canonical ID）、`label`（原始链接文本）、`candidates`（候选 Canonical ID 列表）
- `unresolved`：未解析链接列表，每条 SHALL 至少包含 `source`（Canonical ID）、`label`（原始链接文本）

### 6.8 Session 记录格式

Session 记录文件（`.ink/sessions/YYYYMMDD-HHMMSS-action.json`）SHALL 至少包含以下字段：

- `session_id`：唯一标识
- `timestamp`：操作时间
- `command`：执行的命令或 Skill 名称
- `target`：操作目标；当目标为单篇 Article 时 SHALL 使用 Canonical ID；当目标为全局操作时 MAY 使用保留值（如 `workspace`、`all`、`system`）
- `params`：命令参数
- `result`：执行结果（`success` / `failed` / `partial`）
- `changed_files`：本次操作变更的文件列表
- `duration_ms`：执行耗时（毫秒）

### 6.9 发布记录格式

WHEN 任一渠道执行过发布尝试时，THE System SHALL 记录分渠道发布结果。

Phase 1 MAY 将详细发布记录存储于 `.ink/publish-history/` 独立文件，而非全部写入 Article frontmatter。

每条渠道记录 SHALL 至少包含：

- `target`：目标 Article 的 Canonical ID
- `session_id`：本次发布尝试对应的 Session 标识
- `channel`：渠道标识
- `status`：`success` / `draft_saved` / `failed`
- `attempted_at`：尝试时间
- `published_at`：发布成功时间（若成功）
- `error`：错误信息（若失败）

---

## 7. 状态模型

Article frontmatter 中的 `status` 字段 SHALL 支持以下枚举值：

- `draft`
- `review`
- `ready`
- `published`
- `archived`

状态迁移规则：

- 新建 Article 的默认状态 SHALL 为 `draft`
- 仅当 `status=ready` 时，Publish Skill 才允许执行发布
- 发布成功后，状态 SHALL 更新为 `published`
- `archived` 状态的 Article SHALL 不出现在默认搜索和列表结果中（除非显式指定）

---

## 8. 需求

### 需求 1：CLI 基础框架

**用户故事：** 作为内容创作者，我希望通过自然语言或显式命令向 `ink` 表达操作意图，从而无需记忆复杂命令语法即可完成核心操作。

#### 验收标准

1. THE CLI SHALL 接受 `ink "<自然语言意图>"` 格式输入
2. THE CLI SHALL 接受显式命令格式 `ink <skill-name> [target] [--flags]`
3. WHEN 用户输入自然语言意图时，THE CLI SHALL 将输入解析为结构化操作：
   - `action`
   - `target`
   - `arguments`
4. THE CLI SHALL 仅支持受控自然语言意图集合，超出支持范围时 SHALL 返回：
   - 未识别原因
   - 可用 Skill 列表
   - 至少 1 条可执行示例
5. WHEN 解析结果匹配已注册 Skill 时，THE CLI SHALL 调用对应 Skill
6. WHEN 命令执行成功时，THE CLI SHALL 输出结构化执行摘要，至少包含：
   - 操作名称
   - 目标
   - 执行结果
   - 耗时
7. IF 命令执行失败，THEN THE CLI SHALL 输出：
   - 错误类型
   - 出错位置
   - 建议修复步骤
8. THE CLI SHALL 在 `~/.ink/config.yaml` 维护全局配置
9. THE CLI SHALL 在 Workspace 根目录支持 `.ink/` 本地配置与元数据目录
10. THE CLI SHALL 支持 `ink new "<title>"` 命令用于创建新 Article
11. WHEN 用户执行 `ink new "<title>"` 时，THE CLI SHALL：
    - 默认以命令执行时间生成 Article 路径（`YYYY/MM/DD-slug/`）
    - WHEN 用户显式传入 `--date YYYY-MM-DD` 时，THE CLI SHALL 以该日期生成 Article 路径与 frontmatter 中的 `date`
    - 自动从 title 生成 slug（除非显式传入 `--slug`）
    - 初始化 `index.md`、`.abstract`、`.overview`、`assets/`
    - 为 `index.md` 写入默认 frontmatter（title、slug、date、status=draft、tags）
    - 支持可选参数：`--date YYYY-MM-DD`、`--slug xxx`、`--tags a,b`、`--template xxx`
12. IF 用户显式提供 `--slug` 且目标路径已存在，THEN THE CLI SHALL 返回路径冲突错误
13. IF 自动生成的 slug 对应路径已存在，THEN THE CLI SHALL 返回路径冲突错误，不自动追加后缀

---

### 需求 2：文件系统抽象与三层上下文

**用户故事：** 作为内容创作者，我希望系统为每篇文章自动维护 L0/L1/L2 三层上下文，从而降低 AI 检索成本并提升定位效率。

#### 验收标准

1. THE File Workspace SHALL 以 `YYYY/MM/DD-slug/` 路径组织 Article
2. WHEN 新 Article 通过 `ink` 创建时，THE System SHALL 自动初始化：
   - `index.md`
   - `.abstract`
   - `.overview`
3. `index.md` SHALL 作为三层上下文的唯一源文件
4. WHEN `index.md` 通过 `ink` 命令被创建或更新时，THE System SHALL 自动重新生成：
   - `.abstract`
   - `.overview`
5. THE `.abstract` 内容 SHALL 为单行文本，长度 SHALL NOT 超过 200 个字符
6. THE `.overview` 内容 SHALL 遵循 6.4 节定义的固定格式，至少包含：
   - 标题
   - 标签
   - 3-5 句核心摘要
   - 关联文章路径列表（使用 Canonical ID）
7. THE System SHALL 在 `_index/timeline.json` 中维护时间线索引（遵循 6.7 节格式）
8. WHEN Article 被创建或更新时，THE System SHALL 同步更新 `_index/timeline.json`
9. IF `.abstract` 或 `.overview` 缺失，THEN THE System SHALL 在下次相关 `ink` 写操作或显式 `rebuild` 操作时重新生成
10. THE System SHALL 提供 `ink rebuild` 或等价机制，用于重建所有派生文件
11. 所有派生文件 SHALL 满足可重建原则，即删除后可由源文件重新生成
12. THE System SHALL 支持对 `.abstract` 和 `.overview` 文件执行解析→格式化输出→再解析，结果与原始解析结果等价（往返属性）
13. Phase 1 SHALL NOT 要求通过文件系统监听自动感知手动编辑行为；手动编辑后的同步更新可由后续 `ink` 命令或 `rebuild` 触发
14. `.abstract` 与 `.overview` SHALL 视为系统派生文件（遵循 6.5 节覆盖规则）
15. 用户 MAY 手工编辑 `.abstract` 或 `.overview`，但 THE System SHALL NOT 保证在后续 `regenerate` / `rebuild` 后保留人工修改内容

---

### 需求 3：Publish Skill

**用户故事：** 作为内容创作者，我希望通过 `ink publish` 将文章转换为目标渠道格式，并在可用时完成渠道发布，从而减少手工处理工作。

#### 验收标准

1. WHEN 用户执行 `ink publish <article-path> --channels <channel-list>` 时，THE Publish Skill SHALL 读取目标 Article 的 `index.md` 与 frontmatter
2. IF Article 的 `status` 不等于 `ready`，THEN THE Publish Skill SHALL 拒绝发布，并返回：
   - 当前状态值
   - 可执行的修改建议
3. THE Publish Skill SHALL 支持以下渠道标识：
   - `blog`
   - `newsletter`
   - `mastodon`
4. THE Publish Skill SHALL 为每个目标渠道生成对应格式内容
5. WHEN 指定多个渠道时，THE Publish Skill MAY 并行执行格式化与适配流程，但最终结果 SHALL 分渠道返回
6. THE Publish Skill SHALL 将每个渠道的执行结果明确标记为：
   - `success`
   - `draft_saved`
   - `failed`
7. IF 至少一个目标渠道发布成功，THEN THE Publish Skill SHALL：
   - 更新 Article `status=published`
   - 写入发布时间戳
   - 记录成功渠道列表
8. WHEN 仅部分渠道成功时，THE Publish Skill SHALL：
   - 返回分渠道结果
   - 仅在至少 1 个渠道成功时允许写入发布记录
9. IF 发布过程中网络请求失败，THEN THE Publish Skill SHALL：
   - 将目标渠道内容保存为本地草稿
   - 返回失败原因
   - 不得将失败渠道标记为成功
10. IF 所有渠道均失败，THEN THE Publish Skill SHALL NOT 修改 Article 的 `status`
11. WHEN Publish Skill 执行后，THE System SHALL 在 `.ink/sessions/` 下记录本次操作（遵循 6.8 节格式）
12. IF 用户指定不支持的渠道，THEN THE Publish Skill SHALL 返回支持渠道列表
13. WHEN 任一渠道执行过发布尝试时，THE Publish Skill SHALL 记录分渠道发布结果（遵循 6.9 节格式），至少包含：
    - `channel`
    - `status`
    - `attempted_at`
    - `published_at`（若成功）
    - `error`（若失败）
14. Phase 1 MAY 将详细发布记录存储于独立文件（`.ink/publish-history/`），而非全部写入 Article frontmatter
15. Phase 1 中，`published` 表示"至少一个目标渠道已成功发布"，而非"所有目标渠道均成功发布"

---

### 需求 4：Analyze Skill

**用户故事：** 作为内容创作者，我希望通过 `ink analyze` 获取文章或知识库的结构化分析结果，从而了解内容质量与知识关联。

#### 验收标准

1. WHEN 用户执行 `ink analyze <article-path>` 时，THE Analyze Skill SHALL 输出至少以下信息：
   - 字数
   - 预估阅读时长
   - 标签
   - 出链数量
   - 入链数量（若可计算）
2. WHEN 用户执行 `ink analyze --all` 时，THE Analyze Skill SHALL 输出知识库级统计摘要，至少包含：
   - Article 总数
   - 标签总数
   - 最近更新时间
   - 孤立文章数量
3. THE Analyze Skill SHALL 识别 `index.md` 中的 Wiki 链接格式 `[[文章名]]`
4. THE Analyze Skill SHALL 根据 Wiki 链接关系生成文章关联图（遵循 6.7 节 graph.json 格式）
5. WHEN 分析完成时，THE Analyze Skill SHALL 写入 `_index/graph.json`
6. IF 目标路径不存在，THEN THE Analyze Skill SHALL 返回：
   - 路径不存在提示
   - 当前可用 Article 列表或候选项
7. IF `[[文章名]]` 匹配多个候选 Article，THEN THE Analyze Skill SHALL 将该链接标记为 `ambiguous`，且 SHALL NOT 自动建立确定性边
8. IF `[[文章名]]` 未匹配任何 Article，THEN THE Analyze Skill SHALL 将该链接标记为 `unresolved`
9. THE Analyze Skill SHALL 支持 `[[YYYY/MM/DD-slug]]` 格式作为精确链接，直接解析为 Canonical ID

---

### 需求 5：Search Skill

**用户故事：** 作为内容创作者，我希望通过自然语言或关键词搜索快速找到历史文章。

#### 验收标准

1. WHEN 用户执行 `ink search "<query>"` 时，THE Search Skill SHALL 默认先在 L0（`.abstract`）层执行搜索
2. WHEN L0 层结果少于 3 条时，THE Search Skill SHALL 自动扩展到 L1（`.overview`）层
3. WHERE 全文搜索功能被启用时，THE Search Skill SHALL 支持在 L2（`index.md`）层执行全文检索
4. THE Search Skill SHALL 返回按相关度排序的结果列表
5. 每条搜索结果 SHALL 至少包含：
   - Article 路径（Canonical ID）
   - 标题
   - L0 摘要
   - 匹配片段
6. THE Search Skill SHALL 支持标签过滤：`ink search "<query>" --tag <tag-name>`
7. WHEN 搜索结果为空时，THE Search Skill SHALL 返回：
   - 原始查询词
   - 无结果提示
   - 至少 1 条改写建议或相近关键词提示
8. Phase 1 的搜索结果排序 SHALL 同时满足以下规则：
   - 标题命中权重 > 标签命中权重 > L0 命中 > L1 命中 > L2 命中
   - 同层级下按关键词命中次数排序
   - 若仍相同，则按 Article `date` 倒序排序
9. 默认搜索结果 SHALL 排除 `archived` 状态 Article，除非用户显式指定包含归档内容

---

### 需求 6：Git 集成

**用户故事：** 作为内容创作者，我希望 Ink 自动维护 Git 历史，从而保留完整修改记录并降低手工操作成本。

#### 验收标准

1. WHEN 用户执行 `ink init` 且当前目录不是 Git 仓库时，THE System SHALL：
   - 初始化 Git 仓库
   - 生成必要目录
   - 创建初始提交
2. WHEN Article 被创建时，THE System SHALL 自动执行提交，提交信息格式为：`feat: add <article-slug>`
3. WHEN Article 的 `index.md` 通过 `ink` 被更新时，THE System SHALL 自动执行提交，提交信息格式为：`update: <article-slug> - <summary>`
4. WHEN Publish Skill 成功执行时，THE System SHALL 自动提交发布状态变更，提交信息格式为：`publish: <article-slug> to <channels>`
5. THE System SHALL 在 `.gitignore` 中自动排除：`.ink/sessions/`
6. IF 当前目录不是 Git 仓库且用户未执行 `ink init`，THEN THE System SHALL 在首次写操作前提示用户初始化
7. IF 自动提交失败，THEN THE System SHALL：
   - 保留业务写入结果
   - 输出 Git 错误信息
   - 提示用户手动修复
8. 单次 `ink` 命令触发的业务写入 SHALL 默认聚合为一次 Git 提交
9. `.ink/sessions/` 目录下的记录 SHALL NOT 纳入 Git 版本控制

---

### 需求 7：Skills 体系基础

**用户故事：** 作为开发者，我希望 Skills 以 Markdown 文件定义，从而具备自文档化、可版本控制、可扩展的能力组织方式。

#### 验收标准

1. THE Skill Loader SHALL 从 `.ink/skills/` 目录加载所有 `.md` Skill 定义文件
2. Skill frontmatter SHALL 至少支持以下字段：
   - `skill`
   - `version`
   - `description`
   - `context_requirement`
3. WHEN Skill 文件缺少必填字段时，THE Skill Loader SHALL：
   - 跳过该文件
   - 输出警告标明文件路径与缺失字段
4. THE Skill Loader SHALL 解析 Skill 文件中的至少以下章节：
   - 输入
   - 执行流程
5. THE Skill Loader SHALL 将解析结果注册为可调用 Skill
6. THE System SHALL 支持 `ink skills list`，列出：
   - 名称
   - 版本
   - 描述
7. Skill 定义文件 SHALL 支持往返解析一致性，即：解析→格式化输出→再解析 结果在语义上等价

---

## 9. 非功能需求

1. **可恢复性**：所有派生文件 SHALL 可重建，删除后不得导致源内容丢失
2. **幂等性**：对同一输入重复执行 `rebuild`、`analyze`、`search` SHALL 不产生不一致结果
3. **可读性**：系统生成的文本文件 SHALL 保持人类可读，便于手工编辑与 Git diff
4. **失败隔离**：单个 Skill 执行失败 SHALL NOT 破坏已有 Article 源文件
5. **最小性能要求**：在 1000 篇以内 Article 规模下，常规 search / analyze / rebuild 操作 SHOULD 保持可接受的本地交互速度

---

## 10. 建议的后续扩展（非 Phase 1）

- 文件监听与自动派生更新
- 向量检索与混合搜索
- 远程发布适配器插件化
- Session Memory 与上下文管理增强
- 图形化管理后台
- 多仓库 / 多站点支持
- `ink rename` 命令（含引用自动更新）
- Agent 系统（自主执行、团队协作、去中心化 Orchestrator）
- 记忆机制（working / episodic / semantic 三层）
- 多维度审计与真相文件

---

## 11. 风险与开放问题

1. 自然语言意图解析在 Phase 1 中采用受控意图集合，复杂自由表达不保证识别
2. `[[文章名]]` 形式的 Wiki Link 存在重名歧义风险，Phase 1 通过 `ambiguous` / `unresolved` 标记处理，后续可能需要演进为显式路径引用
3. 多渠道发布的远程适配能力在不同平台之间存在接口差异，Phase 1 以本地格式化与有限适配为主
4. `.overview` 与 `.abstract` 的人工修改在 Phase 1 中不保证被保留
5. Git 自动提交失败时，业务写入与版本历史可能暂时不一致，需要用户手动修复
6. Canonical ID 依赖路径，Article 重命名或移动会导致所有引用漂移，Phase 1 不提供自动引用更新机制
7. `published` 状态在 Phase 1 中表示"至少一个渠道成功"，若后续需要区分主渠道与辅助渠道，需要引入更细粒度的状态模型
8. 自动生成 slug 冲突时 Phase 1 直接报错（不追加后缀），用户需手动指定 `--slug` 或 `--date` 规避
