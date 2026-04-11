# Ink Blog Core — 内核架构、改进路线与可扩展方向

> 版本：v0.3.0-draft
> 日期：2026-04-11
> 状态：设计讨论稿
> 合并自：improvements.md (2026-04-10) + design.md (2026-04-11)

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

## 六、测试覆盖（最高优先级）

`hypothesis` 已在 `pyproject.toml` 的 `dev` 依赖中，实现成本低，收益高。以下 13 个属性测试尚未实现：

| 文件 | 覆盖的 Property |
|------|----------------|
| `tests/agent/test_config_agent.py` | P11 无效 mode 被拒绝、P12 agent init 配置写入与保留 |
| `tests/agent/test_journal_manager.py` | P2 LogEntry 格式正确性、P3 Daily Journal 创建完整性 |
| `tests/agent/test_recall_engine.py` | P4 Recall schema 合规性、P5 分类过滤、P6 日期过滤、P7 limit 约束、P8 无效 limit 被拒绝 |
| `tests/agent/test_log_command.py` | P9 分类大小写规范化、P10 无效分类被拒绝 |
| `tests/agent/test_recall_command.py` | P1 日记写入 round-trip 一致性 |
| `tests/agent/test_skill_index.py` | P13 技能 upsert 无重复、P14 技能 frontmatter 验证 |
| `tests/agent/test_human_compat.py` | P15 disable_human_commands 拦截 |
| `tests/integration/test_http_api.py` | HTTP API 端到端测试（`/log`、`/recall`、`/health`、400 错误） |

---

## 七、版本路线图与功能规划

### 版本总览

| 版本 | 主题 | 关键交付 |
|------|------|---------|
| v0.2.1 | 质量加固 | 13 个属性测试 + HTTP API 集成测试 + L0/L1 同步更新修复 |
| v0.3.0 | 内核增强 | `ink doctor` + `ink stats` + `ink archive` |
| v0.4.0 | 用户价值 | `ink digest` + `ink promote` + Shell 补全 + `ink export` + 最小 Skill 执行引擎 |
| v0.5.0 | 生态扩展 | MCP Server 接入 + 可选语义检索 |
| v0.6.0 | 内核重构 | 统一内容模型（ContentItem）+ 统一检索引擎 |
| v1.0.0 | 稳定版 | 完整 Skill 执行引擎 + Skill 市场 |

> 注：v0.6.0 的内核重构放在生态扩展之后，是因为当前架构足以支撑 v0.3–v0.5 的功能。
> 过早重构会增加风险，等积累了更多内容类型的实际需求后再做统一抽象更稳妥。
> 但建议在 v0.3.0 引入 `ContentItem` 的接口定义（不做完整重构），让新功能面向接口编程。


### v0.2.1 — 质量加固

#### L0/L1 同步更新

当前 `ink log` 追加内容后不更新 `.abstract` 和 `.overview`，导致三层上下文不一致。

修复：在 `JournalManager.append_entry()` 末尾调用 `_generate_layers()`。
同理，任何修改 `index.md` 的操作都应触发 L0/L1 重建。

### v0.3.0 — 内核增强

这些改进直接强化现有能力，不引入新概念。

#### `ink doctor` — 工作区健康诊断

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
- HTTP API 端口可用性检测

实现：新增 `DoctorCommand(BuiltinCommand)`，调用各 Manager 的校验方法。
各项检查均有现成基础设施可复用：`InkConfig.validate_mode()`、`GitManager`、`JournalManager.list_journal_paths()`、`L0Generator` / `L1Generator`。

#### `ink stats` — 内容统计

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

实现：新增 `StatsCommand(BuiltinCommand)`，复用 `JournalManager.list_journal_paths()` + `parse_entries()` 做聚合。

#### `ink archive` — 文章归档命令

```bash
ink archive YYYY/MM/DD-slug
```

将 `status` 改为 `archived`，更新 L0/L1，从 timeline 中标记。
填补生命周期中缺失的最后一环。

### v0.4.0 — 用户价值

这些功能面向终端用户（人类或 Agent），提供新的使用场景。

#### `ink digest` — 周期摘要生成

```bash
ink digest --week
ink digest --since 2026-04-01 --until 2026-04-10
```

- 聚合指定时间范围内的 journal 条目
- 按 category 分组，生成结构化摘要
- 可选写入当天 journal 作为 `[note]` 条目

实现：复用 `RecallEngine.search()` + 模板格式化。

#### `ink promote` — Journal 提升为文章

```bash
ink promote 2026-04-10 --title "本周学习总结" --tags learning,weekly
```

- 从指定日期的 journal 提取内容
- 创建新文章目录（通过 `ArticleManager.create()`）
- 转换 frontmatter（移除 `agent` 字段，更新 `tags`/`status`）
- 保留原 journal 不变，在新文章中添加 `source: YYYY/MM/DD-journal` 引用

> ⚠️ journal 的 frontmatter 结构与正式文章不同，"提升" 需要 frontmatter 转换、slug 重命名、timeline 更新等操作，比表面看起来复杂。建议先明确需求边界再评估。

#### Shell 补全

```bash
ink completion zsh >> ~/.zshrc
ink completion bash >> ~/.bashrc
ink completion fish > ~/.config/fish/completions/ink.fish
```

- 基于 argparse 子命令和 flag 生成补全脚本（可用 `argcomplete` 或手写）
- `--category` 从 `VALID_CATEGORIES` 动态补全
- canonical ID 从 `_index/timeline.json` 补全

#### `ink export` — 数据导出

```bash
ink export --format csv --since 2026-01-01 --type journal
ink export --format json --type article
```

- JSON 格式：直接序列化 `ContentItem` 列表
- CSV 格式：扁平化 frontmatter + 内容摘要

#### 最小 Skill 执行引擎

当前 `FileDefinedSkill.execute()` 是空壳，建议在 v0.4.0 实现最小可用版本（支持 `read_content` + `write_file` 两种步骤类型），避免 Skill 系统长期空壳到 v1.0.0。

### v0.5.0 — 生态扩展

以下方向需要独立的设计文档，这里只描述方向和约束。

#### MCP Server 接入

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

> 注：当前 AI Agent 生态发展很快，MCP 已成为事实标准。实现成本不高（仅参数转换），可考虑提前到 v0.4.x。

#### 语义检索（可选依赖）

```toml
[project.optional-dependencies]
semantic = ["sqlite-vec>=0.1"]
```

- 在 `ink log` / `ink new` 时自动生成 embedding，存入 `_index/embeddings.db`
- `SearchEngine` 接口的 `VectorSearchEngine` 实现
- 配置切换：`search.engine: keyword | vector`

**约束**：核心路径（keyword search）不依赖此模块。`sqlite-vec` 缺失时优雅降级。

> 引入任何 embedding 方案都会新增外部依赖，需评估对 "零外部依赖" 哲学的影响。

#### Skill 市场与远程安装

```bash
ink skill-install summarize --from https://registry.example.com
```

- 定义 `skills.registry.yaml` 格式（name, url, version, sha256）
- 下载 → SHA256 校验 → 写入 `.ink/skills/` → 注册到 `_index/skills.json`
- 全局技能目录：`~/.ink/global-skills/`

**约束**：需要完整的安全模型设计（签名验证、沙箱执行）。复杂度高，建议单独编写设计文档。


---

## 八、Developer Experience 改进

### Watch Mode

文件变化时自动 rebuild L0/L1。

```bash
ink serve --watch
```

实现方式：基于定时 `os.scandir` 轮询，或引入 `watchdog` 做 fsevents/inotify 监听。

> 建议 watch 功能作为独立 flag 而非与 HTTP server 强耦合，
> 也可考虑作为独立命令 `ink watch`，避免职责混淆。

### RAG 问答（长期调研）

```bash
ink ask "上周学了什么"   # 调用本地 LLM（如 ollama）做 RAG 问答
```

这是独立于 recall 升级的功能，涉及 LLM 调用链、prompt 模板、上下文窗口管理等，
建议作为单独提案设计，不与语义检索混在一起。

---

## 九、接入层演进路线

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

## 十、暂不纳入（需进一步论证）

以下方向在当前阶段不建议实施，记录于此供未来参考。

### 跨 Workspace 检索

```bash
ink recall "关键词" --workspace /other/path
```

**暂缓原因**：允许一个 agent 读取任意路径的 journal 数据，违反 FS-as-DB 的 workspace 隔离原则。
如果未来要做，至少需要设计白名单/授权机制。

### 多 Agent 协作与通信

```
Agent-A (port 4001) → POST /log → Agent-B (port 4002)
```

**暂缓原因**：范围远超当前项目边界。当前单 agent 的 HTTP API 尚无集成测试，
不应在此阶段讨论多 agent 协作。建议在单 agent 模式稳定后，作为独立 RFC 提出。

### Config Profile 切换

```bash
ink --profile work serve
ink --profile personal log "今天的笔记"
```

**暂缓原因**：当前 agent 场景下，一个 workspace 对应一个 agent 是最自然的映射。
多 profile 切换更适合人类用户多身份场景，对 agent 价值有限。
如有需求，可通过多 workspace 目录实现同等效果。

### Skill 依赖图（`ink skill-graph`）

- `_index/skills.json` 增加 `depends_on` 字段
- 打印 ASCII 依赖树，检测循环依赖和版本冲突

当前 `SkillRecord` 没有 `depends_on` 字段，需扩展 schema。
且现有技能数量较少，依赖图的实际价值有待验证。优先级较低。

---

## 十一、优先级矩阵

| 方向 | 用户价值 | 实现难度 | 建议优先级 |
|------|---------|---------|-----------|
| Property Tests（六） | 质量保障 | 低 | ⭐⭐⭐ 立即 |
| L0/L1 同步更新（七 v0.2.1） | 数据一致性 | 低 | ⭐⭐⭐ 立即 |
| `ink doctor` 诊断（七 v0.3.0） | 运维友好 | 中 | ⭐⭐⭐ 近期 |
| `ink stats` 统计（七 v0.3.0） | 高 | 中 | ⭐⭐⭐ 近期 |
| `ink archive`（七 v0.3.0） | 生命周期完整 | 低 | ⭐⭐⭐ 近期 |
| `ink digest` 周报（七 v0.4.0） | 中 | 低 | ⭐⭐ 近期 |
| `ink promote`（七 v0.4.0） | 中 | 中 | ⭐⭐ 中期 |
| Shell 补全（七 v0.4.0） | DX 提升 | 低 | ⭐⭐ 中期 |
| 最小 Skill 执行引擎（七 v0.4.0） | 功能完整 | 中 | ⭐⭐ 中期 |
| `ink export`（七 v0.4.0） | 低 | 低 | ⭐ 中期 |
| MCP Server（七 v0.5.0） | 生态接入 | 中 | ⭐⭐ 中期（可提前） |
| Watch Mode（八） | DX 提升 | 中 | ⭐ 中期 |
| 语义检索 / RAG（七 v0.5.0 / 八） | 差异化 | 高 | ⭐ 长期调研 |
| Skill 市场（七 v0.5.0） | 生态 | 高 | ⭐ 长期，需独立设计文档 |
| 统一内容模型（五 / 七 v0.6.0） | 架构优化 | 高 | ⭐ 长期（建议 v0.3.0 先定义接口） |
| 统一检索引擎（五 / 七 v0.6.0） | 架构优化 | 高 | ⭐ 长期 |
| 跨 Workspace / 多 Agent / Profile（十） | — | — | 暂不纳入 |

---

## 十二、设计约束与决策记录

| 决策 | 理由 |
|------|------|
| 不引入数据库 | FS-as-DB 是核心哲学，所有状态可用 `git diff` 追踪 |
| 运行时仅 pyyaml + jinja2 | 最小依赖降低安装门槛，新依赖必须作为 optional |
| 不做多租户 | 一个 workspace = 一个用户/agent，隔离通过文件系统权限保证 |
| Skill 定义用 Markdown | 与内容格式统一，降低学习成本，Git 友好 |
| 索引文件放 `_index/` 且 gitignore | 索引是派生数据，可随时 `rebuild` 重建 |
| Agent 命令复用 BuiltinCommand 接口 | 统一 SkillResult 返回类型，编排层无需区分 |
| HTTP API 用标准库实现 | 避免引入 flask/fastapi 依赖，serve 是可选功能 |
| MCP 接入时的依赖策略 | 待定：MCP SDK 可能引入新依赖，需评估是否作为 optional extras |

---

## 十三、版本命名与发版规则

### 版本号规范

遵循 [Semantic Versioning 2.0.0](https://semver.org/)，格式为 `MAJOR.MINOR.PATCH`：

| 位 | 含义 | 何时递增 | 示例 |
|---|---|---|---|
| MAJOR | 不兼容的 API 变更 | CLI 命令签名变更、配置格式不兼容、数据模型破坏性变更 | `1.0.0` |
| MINOR | 向后兼容的新功能 | 新增命令、新增配置项、新增扩展点 | `0.3.0` |
| PATCH | 向后兼容的缺陷修复 | Bug 修复、文档修正、测试补充、性能优化 | `0.3.1` |

**1.0.0 之前**（当前阶段）：MINOR 版本可包含小范围的不兼容变更，但需在 release note 中明确标注 `BREAKING`。

### 版本号存放位置

版本号在以下两处维护，发版时必须同步更新：

1. `pyproject.toml` → `[project].version`（唯一真相源）
2. `README.md` → 顶部版本标注

### Git Tag 规范

- 格式：`v{MAJOR}.{MINOR}.{PATCH}`，如 `v0.3.0`
- 使用 annotated tag（`git tag -a`），包含 release note
- Tag message 格式：

```
v0.3.0 - 简短主题描述

Features:
- 功能点 1
- 功能点 2

Fixes:
- 修复点 1

Breaking Changes:（如有）
- 变更说明
```

### 发版流程

```bash
# 1. 确保在 main 分支，工作区干净
git checkout main
git status

# 2. 运行全量测试
pytest tests/ -v

# 3. 更新版本号
#    - pyproject.toml: version = "X.Y.Z"
#    - README.md: > vX.Y.Z

# 4. 提交 release commit
git add pyproject.toml README.md
git commit -m "release: vX.Y.Z - 简短描述"

# 5. 打 annotated tag
git tag -a vX.Y.Z -m "vX.Y.Z - 简短描述

Features:
- ...

Fixes:
- ..."

# 6. 推送（含 tag）
git push origin main --tags
```

### 分支策略

| 分支 | 用途 | 合并方式 |
|------|------|---------|
| `main` | 稳定版本，所有 release tag 打在此分支 | — |
| `feature/*` | 功能开发分支，从 main 创建 | `--no-ff` merge 到 main |
| `fix/*` | 缺陷修复分支（可选，小修复可直接在 main 提交） | fast-forward 或 `--no-ff` |

- feature 分支合并后不删除（保留历史），但不再继续开发
- 不使用 develop 分支，main 即开发主线（项目规模不需要 gitflow）

### 版本历史

| 版本 | 日期 | 主题 |
|------|------|------|
| v0.2.0 | 2026-04-05 | 静态站生成、分层配置、改进 init |
| v0.3.0 | 2026-04-11 | Agent 模式（log/recall/serve/skill-*）、属性测试、文档整合 |
