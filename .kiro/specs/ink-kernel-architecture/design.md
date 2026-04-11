# Ink Blog Core — 内核架构与可扩展方向

> 版本：v0.3.0-draft
> 日期：2026-04-11
> 状态：设计讨论稿

---

## 一、设计哲学

Ink 的核心身份是一个 **文件系统原生的内容操作系统**（Content OS on Filesystem）。

三条不可违背的原则：

1. **FS-as-DB**：本地文件系统是唯一存储。没有数据库，没有远程服务依赖。目录结构即数据模型，Markdown 即内容源，JSON 即索引。所有状态都可以用 `ls` 和 `cat` 观察。
2. **最小依赖**：运行时仅依赖 `pyyaml` + `jinja2`。任何新功能如果需要引入新依赖，必须作为可选依赖（`extras_require`），核心路径不受影响。
3. **双模对称**：human 模式和 agent 模式共享同一套基础设施（ArticleManager、InkConfig、GitManager、IndexManager），区别仅在上层命令和交互协议。

---

## 二、当前内核分层

```
┌─────────────────────────────────────────────────────────────┐
│                     接入层 (Interface)                       │
│  CLI argparse │ NLParser │ HTTP API (serve) │ 未来: MCP/SDK  │
├─────────────────────────────────────────────────────────────┤
│                     编排层 (Orchestration)                   │
│  CommandExecutor │ IntentRouter │ SessionLogger              │
├─────────────────────────────────────────────────────────────┤
│                     能力层 (Capabilities)                    │
│  BuiltinCommand (new/init/rebuild/build)                    │
│  Skill (publish/analyze/search)                             │
│  AgentCommand (log/recall/serve/skill-*)                    │
├─────────────────────────────────────────────────────────────┤
│                     领域层 (Domain)                          │
│  ArticleManager │ JournalManager │ RecallEngine              │
│  SkillIndexManager │ PublishHistoryManager                   │
├─────────────────────────────────────────────────────────────┤
│                     基础设施层 (Infrastructure)              │
│  InkConfig │ GitManager │ IndexManager │ L0/L1 Generator     │
│  Markdown Parser │ TemplateRenderer │ RSSGenerator           │
└─────────────────────────────────────────────────────────────┘
```

### 各层职责边界

| 层 | 职责 | 不应做的事 |
|---|---|---|
| 接入层 | 解析用户输入，转换为 Intent | 不含业务逻辑 |
| 编排层 | 路由、执行、会话记录、Git 提交 | 不直接操作文件系统 |
| 能力层 | 实现具体命令/技能的业务逻辑 | 不直接解析 CLI 参数 |
| 领域层 | 内容 CRUD、检索、索引管理 | 不关心输入来源 |
| 基础设施层 | 配置、Git、模板、Markdown 解析 | 不含业务语义 |

---

## 三、内核的七个核心能力

从当前实现中提炼出 Ink 的七个不可再分的核心能力：

### 3.1 内容生命周期管理

```
创建 → 编辑 → 分析 → 发布 → 归档
(new)  (手动)  (analyze) (publish) (手动)
```

- `ArticleManager`：CRUD + 三层上下文自动生成 + 自愈
- 文章状态机：`draft → review → ready → published → archived`
- 路径即身份：`YYYY/MM/DD-slug` 是 canonical ID，不可变

**当前缺失**：没有 `ink archive` 命令，归档靠手动改 frontmatter。

### 3.2 三层上下文体系

```
L0 (.abstract)  ← 单行 ≤200 字符摘要，用于搜索/RSS/列表
L1 (.overview)  ← YAML meta + Summary + Key Points，用于分析/扩展搜索
L2 (index.md)   ← 完整 Markdown，唯一真相源
```

- L0/L1 从 L2 自动派生（`L0Generator` / `L1Generator`）
- 读取时自愈：缺失的 L0/L1 自动重建
- `rebuild` 命令批量重建所有 L0/L1 + timeline

**设计洞察**：三层上下文是 Ink 最独特的抽象。它不仅服务于搜索分层，更是 AI Agent 高效消费内容的关键——Agent 可以先读 L0 决定是否深入，再读 L1 获取结构化摘要，最后按需读 L2。这个模式可以推广到所有内容类型。

### 3.3 分层检索

```
SearchSkill: title(5.0) → tag(4.0) → L0(3.0) → L1(2.0) → L2(1.0)
RecallEngine: 关键词精确匹配(+2) → 部分匹配(+1)，按相关性/日期排序
```

- 搜索自动扩展：L0 命中不足时扩展到 L1，可选 fulltext 扩展到 L2
- Recall 支持 category/since/limit 过滤

**当前局限**：两套检索引擎（SearchSkill 面向文章，RecallEngine 面向 journal）逻辑重复，评分模型不统一。

### 3.4 知识图谱

```
AnalyzeSkill → _index/graph.json
  nodes: 文章列表
  edges: [[wiki-link]] 引用关系
  ambiguous: 歧义链接
  unresolved: 未解析链接
```

- Wiki link 解析：精确 canonical ID → 标题/slug 模糊匹配 → 歧义/未解析
- 单篇分析：字数、阅读时间、标签、关联文章、入链数
- 全库分析：总数、标签分布、最近更新、孤立文章

### 3.5 多渠道发布

```
PublishSkill → PublisherAdapter (blog / newsletter / mastodon)
  状态门控：仅 status=ready 可发布
  发布后：更新 status=published，重建 L0/L1，记录历史
```

- 适配器模式：每个渠道一个 `PublisherAdapter` 子类
- 发布历史：`.ink/publish-history/YYYY/MM/DD-slug/` 下 JSON 记录

### 3.6 静态站生成

```
SiteBuilder → TemplateRenderer (Jinja2) + RSSGenerator (Atom)
  输入：_index/timeline.json + 文章内容
  输出：_site/ (HTML + feed.xml)
```

- 模板覆盖：`_templates/site/article.html` 和 `index.html`
- 内置 Markdown → HTML 转换（无外部依赖）
- 响应式默认样式

### 3.7 Agent 日记系统

```
JournalManager → YYYY/MM/DD-journal/index.md
  ink log → 追加带时间戳和分类的条目
  ink recall → 跨日记检索，返回结构化 JSON
  ink serve → HTTP API 暴露 log/recall/health
```

- 日记复用 ArticleManager 的目录结构和三层上下文
- 技能管理：`SkillIndexManager` 管理 `_index/skills.json`

---

## 四、扩展点分析

当前系统有五个明确的扩展点和三个潜在的扩展点：

### 已有扩展点

| 扩展点 | 机制 | 当前状态 |
|--------|------|---------|
| **Skill 插件** | `.ink/skills/*.md` → `SkillFileLoader` → `FileDefinedSkill` | Phase 1 仅加载定义，无执行引擎 |
| **发布渠道** | `PublisherAdapter` 子类 | 3 个内置适配器（blog/newsletter/mastodon） |
| **模板覆盖** | `_templates/site/` 下的 Jinja2 模板 | 支持 article.html 和 index.html |
| **配置分层** | defaults → global → workspace | 完整实现 |
| **接入协议** | CLI argparse + NLParser + HTTP API | 三种接入方式 |

### 潜在扩展点（当前未开放但架构允许）

| 扩展点 | 可行性 | 说明 |
|--------|--------|------|
| **内容类型** | 高 | ArticleManager 的目录结构可承载非文章内容（journal 已证明） |
| **索引类型** | 高 | IndexManager 可扩展新的 `_index/*.json` 文件 |
| **检索引擎** | 中 | SearchSkill 和 RecallEngine 可抽象为统一接口 |

---

## 五、内核重构方向

基于以上分析，提出三个内核级的重构方向。这些不是新功能，而是对现有架构的结构性改进，为后续扩展打下基础。

### 5.1 统一内容模型（ContentItem）

**问题**：当前 `Article` 和 `LogEntry` 是两个独立的数据模型，`ArticleManager` 和 `JournalManager` 各自管理，搜索/索引逻辑重复。

**方案**：引入 `ContentItem` 作为统一的内容抽象：

```python
@dataclass
class ContentItem:
    canonical_id: str       # YYYY/MM/DD-slug 或 YYYY/MM/DD-journal
    content_type: str       # "article" | "journal" | 未来可扩展
    path: Path              # 目录绝对路径
    date: str               # YYYY-MM-DD
    l0: str                 # .abstract
    l1: dict                # .overview 解析结果
    l2: str                 # index.md 原始内容
    metadata: dict          # frontmatter 中的额外字段
```

- `Article` 和 journal 都是 `ContentItem` 的特化
- `ArticleManager` 重构为 `ContentManager`，按 `content_type` 区分行为
- 搜索和索引统一操作 `ContentItem`

**影响范围**：领域层重构，能力层适配，接入层不变。

**收益**：
- 消除 ArticleManager / JournalManager 的代码重复
- 为未来新内容类型（笔记、书签、代码片段）提供统一基础
- 搜索和索引天然覆盖所有内容类型

### 5.2 统一检索引擎

**问题**：`SearchSkill`（面向文章，分层评分）和 `RecallEngine`（面向 journal，关键词评分）是两套独立实现，评分模型不一致，无法跨内容类型检索。

**方案**：抽象 `SearchEngine` 接口，统一检索路径：

```python
class SearchEngine(ABC):
    @abstractmethod
    def search(self, query: str, *, filters: SearchFilters) -> SearchResult: ...

@dataclass
class SearchFilters:
    content_type: str | None = None   # "article" | "journal" | None (all)
    category: str | None = None       # journal 专用
    tags: list[str] | None = None     # article 专用
    since: str | None = None
    limit: int = 20

@dataclass
class SearchResult:
    query: str
    total: int
    hits: list[SearchHit]
```

- `KeywordSearchEngine`：合并现有 SearchSkill 和 RecallEngine 的逻辑
- 未来 `VectorSearchEngine`：可选依赖，实现语义检索
- `ink search` 和 `ink recall` 都路由到同一个引擎，通过 `content_type` 过滤区分

### 5.3 Skill 执行引擎

**问题**：当前 `FileDefinedSkill.execute()` 是空壳（Phase 1 stub），`.ink/skills/*.md` 中定义的技能无法真正执行。

**方案**：实现基于步骤定义的执行引擎：

```python
class SkillExecutor:
    """解释执行 SkillDefinition 中的步骤。"""

    def execute(self, definition: SkillDefinition, target: str | None, params: dict) -> SkillResult:
        # 1. 根据 context_requirement 加载对应层级的内容
        # 2. 按 steps 列表顺序执行每个步骤
        # 3. 步骤类型：read_content / transform / write_file / call_command
        # 4. 返回聚合的 SkillResult
```

这使得用户可以通过编写 `.md` 文件定义新技能，无需写 Python 代码。

---

## 六、可扩展方向

以下方向按 "内核增强 → 用户价值 → 生态扩展" 的顺序排列。

### 第一圈：内核增强（v0.3.x）

这些改进直接强化现有能力，不引入新概念。

#### 6.1 `ink doctor` — 工作区健康诊断

```bash
ink doctor
```

检查项：
- Config 合法性（`validate_mode()` + schema 校验）
- Git 状态（未提交变更、分支信息）
- 内容完整性（L0/L1 与 L2 一致性、frontmatter 必填字段）
- 索引一致性（timeline.json 与实际文章目录对比）
- Skill 文件完整性（`_index/skills.json` 引用的文件是否存在）
- Journal 连续性（检测日期缺口）

实现：新增 `DoctorCommand(BuiltinCommand)`，调用各 Manager 的校验方法。

#### 6.2 `ink stats` — 内容统计

```bash
ink stats                    # 全局统计
ink stats --type journal     # 仅 journal 统计
```

输出：
- 文章/journal 总数、字数分布
- 按 category 频次统计（journal）
- 按 tag 频次统计（article）
- 按月活跃度 heatmap（ASCII）
- 连续活跃天数

实现：新增 `StatsCommand(BuiltinCommand)`，遍历 `ContentManager`（或现有 ArticleManager + JournalManager）聚合数据。

#### 6.3 L0/L1 同步更新

当前 `ink log` 追加内容后不更新 `.abstract` 和 `.overview`，导致三层上下文不一致。

修复：在 `JournalManager.append_entry()` 末尾调用 `_generate_layers()`。
同理，任何修改 `index.md` 的操作都应触发 L0/L1 重建。

#### 6.4 `ink archive` — 文章归档命令

```bash
ink archive YYYY/MM/DD-slug
```

将 `status` 改为 `archived`，更新 L0/L1，从 timeline 中标记。
填补生命周期中缺失的最后一环。

### 第二圈：用户价值（v0.4.x）

这些功能面向终端用户（人类或 Agent），提供新的使用场景。

#### 6.5 `ink digest` — 周期摘要生成

```bash
ink digest --week
ink digest --since 2026-04-01 --until 2026-04-10
```

- 聚合指定时间范围内的 journal 条目
- 按 category 分组，生成结构化摘要
- 可选写入当天 journal 作为 `[note]` 条目

实现：复用 `RecallEngine.search()` + 模板格式化。

#### 6.6 `ink promote` — Journal 提升为文章

```bash
ink promote 2026-04-10 --title "本周学习总结" --tags learning,weekly
```

- 从指定日期的 journal 提取内容
- 创建新文章目录（通过 `ArticleManager.create()`）
- 转换 frontmatter（移除 `agent` 字段，更新 `tags`/`status`）
- 保留原 journal 不变，在新文章中添加 `source: YYYY/MM/DD-journal` 引用

#### 6.7 Shell 补全

```bash
ink completion zsh >> ~/.zshrc
```

- 基于 argparse 子命令和 flag 生成补全脚本
- `--category` 从 `VALID_CATEGORIES` 动态补全
- canonical ID 从 `_index/timeline.json` 补全

#### 6.8 `ink export` — 数据导出

```bash
ink export --format csv --since 2026-01-01 --type journal
ink export --format json --type article
```

- JSON 格式：直接序列化 `ContentItem` 列表
- CSV 格式：扁平化 frontmatter + 内容摘要

### 第三圈：生态扩展（v0.5.x+）

这些方向需要独立的设计文档，这里只描述方向和约束。

#### 6.9 MCP Server 接入

将 Ink 暴露为 MCP（Model Context Protocol）Server，使任何支持 MCP 的 AI Agent 都能直接调用 Ink 的能力。

```json
{
  "mcpServers": {
    "ink": {
      "command": "ink",
      "args": ["mcp-serve"],
      "env": {}
    }
  }
}
```

暴露的 tools：
- `ink_log`：写入 journal
- `ink_recall`：检索记忆
- `ink_search`：搜索文章
- `ink_new`：创建文章
- `ink_read`：读取指定层级的内容（L0/L1/L2）
- `ink_stats`：获取统计数据

**约束**：MCP Server 层不含业务逻辑，仅做参数转换，复用现有 Command/Skill。

#### 6.10 语义检索（可选依赖）

```toml
[project.optional-dependencies]
semantic = ["sqlite-vec>=0.1"]
```

- 在 `ink log` / `ink new` 时自动生成 embedding，存入 `_index/embeddings.db`
- `SearchEngine` 接口的 `VectorSearchEngine` 实现
- 配置切换：`search.engine: keyword | vector`

**约束**：核心路径（keyword search）不依赖此模块。`sqlite-vec` 缺失时优雅降级。

#### 6.11 Skill 市场与远程安装

```bash
ink skill-install summarize --from https://registry.example.com
```

- 定义 `skills.registry.yaml` 格式（name, url, version, sha256）
- 下载 → SHA256 校验 → 写入 `.ink/skills/` → 注册到 `_index/skills.json`
- 全局技能目录：`~/.ink/global-skills/`

**约束**：需要完整的安全模型设计（签名验证、沙箱执行）。

#### 6.12 多 Workspace 联邦

```bash
ink recall "关键词" --workspace /other/path
```

**约束**：需要授权机制（白名单）。当前不建议实施，记录为长期方向。

---

## 七、接入层演进路线

当前 Ink 有三种接入方式，未来可扩展为五种：

```
                    ┌─────────────┐
                    │   Intent    │
                    └──────▲──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────┴────┐      ┌─────┴─────┐     ┌──────┴──────┐
   │  CLI    │      │  HTTP API │     │  MCP Server │
   │argparse │      │  (serve)  │     │  (未来)     │
   └────┬────┘      └─────┬─────┘     └──────┬──────┘
        │                  │                  │
   ┌────┴────┐      ┌─────┴─────┐     ┌──────┴──────┐
   │NLParser │      │           │     │  Python SDK │
   │(自然语言)│      │           │     │  (未来)     │
   └─────────┘      └───────────┘     └─────────────┘
```

所有接入方式最终都转换为 `Intent`，由 `IntentRouter` → `CommandExecutor` 统一处理。
这个架构保证了新增接入方式不需要修改业务逻辑。

---

## 八、版本路线图

| 版本 | 主题 | 关键交付 |
|------|------|---------|
| v0.2.1 | 质量加固 | 13 个属性测试 + HTTP API 集成测试 + L0/L1 同步更新修复 |
| v0.3.0 | 内核增强 | `ink doctor` + `ink stats` + `ink archive` |
| v0.4.0 | 用户价值 | `ink digest` + `ink promote` + Shell 补全 + `ink export` |
| v0.5.0 | 生态扩展 | MCP Server 接入 + 可选语义检索 |
| v0.6.0 | 内核重构 | 统一内容模型（ContentItem）+ 统一检索引擎 |
| v1.0.0 | 稳定版 | Skill 执行引擎 + Skill 市场 |

> 注：v0.6.0 的内核重构放在生态扩展之后，是因为当前架构足以支撑 v0.3–v0.5 的功能。
> 过早重构会增加风险，等积累了更多内容类型的实际需求后再做统一抽象更稳妥。

---

## 九、设计约束与决策记录

| 决策 | 理由 |
|------|------|
| 不引入数据库 | FS-as-DB 是核心哲学，所有状态可用 `git diff` 追踪 |
| 运行时仅 pyyaml + jinja2 | 最小依赖降低安装门槛，新依赖必须作为 optional |
| 不做多租户 | 一个 workspace = 一个用户/agent，隔离通过文件系统权限保证 |
| Skill 定义用 Markdown | 与内容格式统一，降低学习成本，Git 友好 |
| 索引文件放 `_index/` 且 gitignore | 索引是派生数据，可随时 `rebuild` 重建 |
| Agent 命令复用 BuiltinCommand 接口 | 统一 SkillResult 返回类型，编排层无需区分 |
| HTTP API 用标准库实现 | 避免引入 flask/fastapi 依赖，serve 是可选功能 |
