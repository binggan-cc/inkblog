# Implementation Plan: Ink Blog Core (Phase 1)

## Overview

将现有 `ink`/`ink-v2` 两个独立 CLI 脚本重构为模块化 Python 包 `ink_core`，按分层架构逐步实现：Core Services → Skills 层 → CLI 层 → 集成联调。每个阶段增量构建，确保代码始终可运行。

## Tasks

- [ ] 1. 项目结构与核心数据模型
  - [x] 1.1 创建 `ink_core` 包骨架与 pyproject.toml
    - 创建 `ink_core/__init__.py`、`ink_core/cli/`、`ink_core/fs/`、`ink_core/skills/`、`ink_core/git/`、`ink_core/core/` 目录结构
    - 创建 `pyproject.toml`，定义 `ink` 作为 console_scripts 入口点
    - 创建 `tests/conftest.py`，定义共享 fixtures（临时 ink 目录、示例文章）
    - _Requirements: 1.1, 1.5, 1.8_

  - [x] 1.2 实现核心数据模型与基础接口
    - 在 `ink_core/core/errors.py` 中定义全部领域异常：`PathNotFoundError`、`PathConflictError`、`InvalidStatusError`、`UnsupportedChannelError`、`TemplateRenderError`、`ChannelOutputError`、`AmbiguousLinkError`、`UnresolvedLinkError`、`SkillNotFoundError`、`SkillLoadError`、`GitNotInitError`、`LayerCorruptError`、`ConfigError`
    - 在 `ink_core/cli/intent.py` 中定义 `Intent` dataclass（action, target, params）、`ParseResult` dataclass（intent: Intent | None, error: str | None, candidates: list[str] | None）、`RouteResult` dataclass（target, error, candidates）
    - 在 `ink_core/cli/builtin.py` 中定义 `BuiltinCommand` ABC（name: str，run(target, params) -> SkillResult）
    - 在 `ink_core/fs/article.py` 中定义 `Article` dataclass（path, canonical_id, folder_name, slug, date, l0, l1, l2）
    - 在 `ink_core/skills/base.py` 中定义 `Skill` ABC 基类和 `SkillResult` dataclass（success, message, data, changed_files: list[Path] | None）；执行层内部统一使用 `list[Path]`，只有 `SessionLogger.log()` 写 JSON 时才转 `list[str]`
    - 在 `ink_core/skills/loader.py` 中定义 `SkillDefinition` dataclass
    - 在 `ink_core/core/executor.py` 中定义 `ExecutionContext` dataclass（session_id, command, target: str | None, params, changed_files: list[Path], warnings, started_at）
    - 在 `ink_core/core/publish_history.py` 中定义 `ChannelPublishRecord` dataclass（channel, status, attempted_at, published_at, error）
    - _Requirements: 1.2, 2.1, 6.8, 6.9, 7.2_

  - [ ]* 1.3 写单元测试：核心数据结构正确性
    - 验证 `Intent`、`ParseResult`、`RouteResult`、`ExecutionContext`、`SkillResult` 各字段类型与默认值
    - 验证 `ParseResult(intent=None, error="...", candidates=[...])` 结构合法
    - 验证 `changed_files` 在所有数据结构中均为 `list[Path]` 类型（不是 `list[str]`）
    - _Requirements: 1.2_

- [ ] 2. 配置与会话服务
  - [x] 2.1 实现 `InkConfig`（`ink_core/core/config.py`）
    - 实现 `load()`、`save()`、`get()` 方法，支持 `~/.ink/config.yaml` 读写
    - 配置文件不存在时使用默认配置
    - _Requirements: 1.8_

  - [x] 2.2 实现 `SessionLogger`（`ink_core/core/session.py`）
    - 实现 `log(context: ExecutionContext, result: str, duration_ms: int) -> Path`，将操作记录写入 `.ink/sessions/YYYYMMDD-HHMMSS-action.json`
    - `context.target` 可为 Canonical ID、保留值（workspace/all/system）或 None；写入 JSON 时 `changed_files` 从 `list[Path]` 序列化为字符串列表
    - 实现 `recent(n: int = 10) -> list[dict]`，返回最近 N 条记录
    - _Requirements: 3.11, 6.8_

  - [ ]* 2.3 写单元测试：配置加载与会话记录
    - 测试默认配置生成、配置读写、Session 文件创建格式（含 target=None 场景）
    - _Requirements: 1.8, 6.8_

- [ ] 3. 文件系统层：三层上下文
  - [x] 3.0 实现 Markdown/frontmatter 解析工具（`ink_core/fs/markdown.py`）
    - `parse_frontmatter(content: str) -> dict`：从 Markdown 文本提取 YAML frontmatter
    - `dump_frontmatter(meta: dict, body: str) -> str`：将 frontmatter dict + body 序列化回 Markdown
    - `parse_overview(content: str) -> dict`：解析 `.overview` 文件（YAML frontmatter + Markdown 章节）为结构化 dict
    - `serialize_overview(data: dict) -> str`：将结构化 dict 序列化回 `.overview` 格式
    - 这是 Publish/Analyze/Search/L1Generator 的共用基础，避免各处重复解析逻辑
    - _Requirements: 2.6, 2.12, 3.1, 6.2_

  - [x] 3.1 实现 `L0Generator` 和 `L1Generator`（`ink_core/fs/layer_generator.py`）
    - `L0Generator.generate(content)` → 单行 ≤200 字符摘要
    - `L1Generator.generate(content, existing=None)` → 包含 title、tags、summary、related 的 YAML frontmatter + Markdown 章节；`existing` 仅用于读取历史元数据（如 created_at），不保留人工修改内容
    - _Requirements: 2.5, 2.6_

  - [ ]* 3.2 写属性测试：L0 摘要约束
    - **Property 8: L0 摘要约束**
    - **Validates: Requirements 2.5**

  - [ ]* 3.3 写属性测试：L1 概览必填字段
    - **Property 9: L1 概览必填字段**
    - **Validates: Requirements 2.6**

  - [ ]* 3.4 写属性测试：L0/L1 往返属性
    - **Property 12: L0/L1 往返属性**
    - **Validates: Requirements 2.12**

  - [x] 3.5 实现 `SlugResolver`（`ink_core/fs/article.py`）
    - `generate_slug(title)` → 从标题生成 slug
    - `check_conflict(date, slug)` → 检测目标路径是否已存在
    - _Requirements: 1.11, 1.12, 1.13_

  - [x] 3.6 实现 `ArticleManager`（`ink_core/fs/article.py`）
    - 定义 `ArticleReadResult` dataclass（article: Article, changed_files: list[Path]），作为 read/read_by_id 的返回类型，将自愈产生的变更文件带回给调用方
    - `create(title, *, date, slug, tags, template)` → 创建 `YYYY/MM/DD-slug/` 目录，初始化 index.md、.abstract、.overview、assets/；slug 冲突时抛出 PathConflictError
    - `read(path: Path) -> ArticleReadResult` → 读取 Article；自愈逻辑：检测 .abstract/.overview 缺失则自动重建，重建文件列入 `ArticleReadResult.changed_files`；调用方（CommandExecutor）负责判断是否将这些文件纳入 Git commit
    - `read_by_id(canonical_id: str) -> ArticleReadResult` → 将 Canonical ID 转换为路径后调用 read()，供 Skills 和 CLI 直接使用
    - `resolve_path(canonical_id: str) -> Path` → 从 Canonical ID 解析出绝对路径
    - `update_layers(article) -> list[Path]` → 调用 L0/L1Generator 更新派生文件，返回变更文件列表
    - `list_all()` → 扫描所有年份/月份目录返回 Article 列表
    - `resolve_canonical_id(path: Path) -> str` → 从路径生成 Canonical ID（YYYY/MM/DD-slug，不含末尾斜杠）
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.9, 1.11, 1.12_

  - [ ]* 3.7 写属性测试：文章创建不变量
    - **Property 4: 文章创建不变量**
    - **Validates: Requirements 2.1, 2.2, 1.11**

  - [ ]* 3.8 写属性测试：Slug 冲突检测
    - **Property 5: Slug 冲突检测**
    - **Validates: Requirements 1.12, 1.13**

  - [ ]* 3.9 写属性测试：内容变更触发层级自动更新
    - **Property 6: 内容变更触发层级自动更新**
    - **Validates: Requirements 2.3, 2.4**

  - [ ]* 3.10 写属性测试：派生文件覆盖一致性
    - **Property 7: 派生文件覆盖一致性**
    - **Validates: Requirements 2.14, 2.15**

  - [x] 3.11 实现 `IndexManager`（`ink_core/fs/index_manager.py`）
    - `update_timeline(article)` → 更新 `_index/timeline.json`，按 date 倒序排列，date 相同按 updated_at 倒序
    - `read_timeline()` → 读取时间线索引
    - `update_graph(graph_data)` → 更新 `_index/graph.json`，ambiguous/unresolved 无数据时写空数组
    - `read_graph()` → 读取知识图谱
    - _Requirements: 2.7, 2.8_

  - [ ]* 3.12 写属性测试：时间线索引同步
    - **Property 10: 时间线索引同步**
    - **Validates: Requirements 2.7, 2.8**

  - [ ]* 3.13 写属性测试：Canonical ID 全局一致性
    - **Property 11: Canonical ID 全局一致性**
    - **Validates: Requirements 6.6**

- [x] 4. Checkpoint - 核心文件系统层验证
  - Ensure all tests pass; unresolved issues SHALL be recorded in an implementation notes file with chosen default behavior.

- [x] 5. 发布记录管理
  - [x] 5.1 实现 `PublishHistoryManager`（`ink_core/core/publish_history.py`）
    - `record(session_id, canonical_id, attempted_at, records)` → 在 `.ink/publish-history/YYYY/MM/DD-slug/` 目录下生成 `YYYYMMDD-HHMMSS-publish-<hash>.json`；Canonical ID 中的 `/` 直接映射为目录层级
    - 记录文件顶层必须包含 `session_id`、`canonical_id`、`attempted_at`、`channels` 四个字段
    - `get_history(canonical_id)` → 遍历对应目录返回所有历史记录
    - `get_latest(canonical_id)` → 返回最新一条记录
    - _Requirements: 3.13, 3.14, 6.9_

  - [ ]* 5.2 写属性测试：发布记录完整性
    - **Property 15: 发布记录完整性**
    - **Validates: Requirements 3.13, 3.14**

- [x] 6. Skills 层：Publish
  - [x] 6.1 实现 `PublisherAdapter` 及三个 Phase 1 适配器（`ink_core/skills/publish.py`）
    - `BlogFileAdapter`：生成本地 blog 格式文件
    - `NewsletterFileAdapter`：生成本地 newsletter 格式文件
    - `MastodonDraftAdapter`：生成本地 mastodon 草稿文件（不调用真实 API）
    - 每个 adapter 的 `publish()` 返回 `ChannelPublishRecord`
    - _Requirements: 3.3, 3.4, 3.9_

  - [x] 6.2 实现 `PublishSkill`（`ink_core/skills/publish.py`）
    - 状态门控：读取 `index.md` frontmatter 中的 `status`（不读 .overview），`status != ready` 时拒绝并返回当前值
    - 调用各渠道 adapter，分渠道收集 ChannelPublishRecord
    - 至少一个渠道成功时：更新 `index.md` status=published、写入发布时间戳；调用 `ArticleManager.update_layers()` 同步刷新 `.overview`；调用 `IndexManager.update_timeline()` 更新 `_index/timeline.json`
    - 所有渠道失败时：不修改 Article status，不调用 update_layers/update_timeline
    - 调用 `PublishHistoryManager.record()` 写入发布记录（无论成功或失败均记录）
    - 不支持的渠道返回支持渠道列表
    - _Requirements: 3.1, 3.2, 3.5, 3.6, 3.7, 3.8, 3.10, 3.12, 3.15_

  - [ ]* 6.3 写属性测试：发布状态门控
    - **Property 13: 发布状态门控**
    - **Validates: Requirements 3.2**

  - [ ]* 6.4 写属性测试：多渠道输出完整性
    - **Property 14: 多渠道输出完整性**
    - **Validates: Requirements 3.4, 3.12**

  - [ ]* 6.5 写属性测试：发布成功副作用
    - **Property 16: 发布成功副作用**
    - **Validates: Requirements 3.7, 3.11, 3.15**

- [~] 7. Skills 层：Analyze
  - [ ] 7.1 实现 `AnalyzeSkill`（`ink_core/skills/analyze.py`）
    - 单篇分析：输出 word_count、reading_time、tags、related_count（出链数）、in_link_count（入链数，依赖 `_index/graph.json` 或全库扫描；若图谱未建立则返回 0）
    - 全库分析（`--all`）：输出 Article 总数、标签总数、最近更新时间、孤立文章数量
    - Wiki 链接提取：识别 `[[...]]` 格式，调用 `resolve_wiki_link()` 分类为 resolved/ambiguous/unresolved
    - 分析完成后写入 `_index/graph.json`（遵循 6.7 节格式，ambiguous/unresolved 无数据时写空数组）
    - 路径不存在时返回错误 + 可用 Article 列表
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ] 7.2 实现 `WikiLinkResult` 与 `resolve_wiki_link()`（`ink_core/skills/analyze.py`）
    - `[[文章名]]` 匹配唯一 Article → resolved，返回 Canonical ID
    - `[[文章名]]` 匹配多个候选 → ambiguous，不建立确定性边
    - `[[文章名]]` 未匹配任何 Article → unresolved
    - `[[YYYY/MM/DD-slug]]` 精确格式 → 直接解析为 Canonical ID，不产生歧义
    - _Requirements: 4.7, 4.8, 4.9_

  - [ ]* 7.3 写属性测试：文章分析输出完整性
    - **Property 17: 文章分析输出完整性**
    - **Validates: Requirements 4.1**

  - [ ]* 7.4 写属性测试：Wiki Link 解析完整性
    - **Property 18: Wiki Link 解析完整性**
    - **Validates: Requirements 4.7, 4.8, 4.9**

- [~] 8. Skills 层：Search
  - [ ] 8.1 实现 `SearchSkill`（`ink_core/skills/search.py`）
    - L0 层关键词匹配，结果少于 3 条时自动扩展到 L1 层，最终结果为两层并集
    - 结果排序：标题命中 > 标签命中 > L0 命中 > L1 命中 > L2 命中；同层级按命中次数降序；仍相同按 date 倒序
    - 默认排除 `status=archived` 的 Article
    - 支持 `--tag` 标签过滤
    - L2 全文检索默认关闭，通过 `config.yaml` 中 `search.engine=fulltext` 或 CLI flag `--fulltext` 启用
    - 空结果返回原始查询词 + 无结果提示 + 至少 1 条改写建议
    - 每条结果包含：Canonical ID、title、L0 摘要、匹配片段、score、hit_layer、hit_count、date
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9_

  - [ ]* 8.2 写属性测试：分层搜索策略
    - **Property 21: 分层搜索策略**
    - **Validates: Requirements 5.1, 5.2**

  - [ ]* 8.3 写属性测试：搜索排序稳定性
    - **Property 19: 搜索排序稳定性**
    - **Validates: Requirements 5.8, 5.9**

  - [ ]* 8.4 写属性测试：搜索排除归档文章
    - **Property 20: 搜索排除归档文章**
    - **Validates: Requirements 5.10**

  - [ ]* 8.5 写属性测试：搜索标签过滤
    - **Property 22: 搜索标签过滤**
    - **Validates: Requirements 5.6**

- [~] 9. Checkpoint - Skills 层验证
  - Ensure all tests pass; unresolved issues SHALL be recorded in an implementation notes file with chosen default behavior.

- [~] 10. Git 集成
  - [ ] 10.1 实现 `GitManager`（`ink_core/git/manager.py`）
    - `init_repo()` → 初始化 Git 仓库 + 初始提交
    - `is_repo()` → 检测当前目录是否为 Git 仓库
    - `auto_commit(paths, message)` → 单路径 add + commit（供内部使用）
    - `aggregate_commit(changed_files: list[Path], message)` → 单次 ink 命令所有变更聚合为一次 commit
    - `ensure_gitignore()` → 确保 `.gitignore` 排除 `.ink/sessions/`
    - 提交信息格式：创建 `feat: add <slug>`、更新 `update: <slug> - <summary>`、发布 `publish: <slug> to <channels>`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.7, 6.8_

  - [ ]* 10.2 写属性测试：Git 提交格式
    - **Property 23: Git 提交格式**
    - **Validates: Requirements 6.2, 6.3, 6.4**

  - [ ]* 10.3 写属性测试：Git 提交聚合
    - **Property 24: Git 提交聚合**
    - **Validates: Requirements 6.8**

  - [ ]* 10.4 写单元测试：Git 初始化与非仓库提示
    - 测试 `ink init` 初始化仓库、非仓库目录提示、sessions 不纳入 Git
    - _Requirements: 6.1, 6.6, 6.9_

- [~] 11. Skill 文件加载器与注册表
  - [ ] 11.1 实现 `SkillFileLoader`（`ink_core/skills/loader.py`）
    - `load(path)` → 解析 `.md` 文件 frontmatter + 章节内容，缺少必填字段（skill、version、context_requirement）时跳过 + 警告（含文件路径和缺失字段名）
    - `parse_frontmatter(content)` → 提取 YAML frontmatter
    - `parse_sections(content)` → 提取"输入"和"执行流程"章节
    - `serialize(definition)` → 将 SkillDefinition 序列化回 Markdown
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ] 11.2 实现 `SkillRegistry`（`ink_core/skills/registry.py`）
    - `register(skill)` → 注册 Skill 实例
    - `resolve(name)` → 按名称查找 Skill
    - `list_all()` → 列出所有已注册 Skill
    - `load_from_directory(path)` → 从目录批量加载 Skill 定义
    - 内置 Skills（publish、analyze、search）自动注册
    - _Requirements: 7.1, 7.6_

  - [ ]* 11.3 写属性测试：Skill 加载正确性
    - **Property 27: Skill 加载正确性**
    - **Validates: Requirements 7.1, 7.2, 7.5**

  - [ ]* 11.4 写属性测试：Skill 定义文件往返属性
    - **Property 28: Skill 定义文件往返属性**
    - **Validates: Requirements 7.7**

  - [ ]* 11.5 实现 `Validator` stub（`ink_core/core/validator.py`）
    - 定义 `ValidationIssue` dataclass（level, path, message）和 `Validator` 类接口（validate_article、validate_indexes、validate_skills），Phase 1 返回空列表
    - 预留接口供后续 `ink validate` 和 `ink rebuild --check` 使用，Phase 1 不实现具体校验逻辑

- [~] 12. CLI 层：解析器、路由与执行事务
  - [ ] 12.1 实现 `NLParser`（`ink_core/cli/intent.py`）
    - 规则匹配优先：正则模式匹配常见意图（发布、搜索、创建等）
    - `parse(text: str) -> ParseResult`：匹配成功返回 `ParseResult(intent=Intent(...), error=None)`；无法识别返回 `ParseResult(intent=None, error="...", candidates=[...])`，不返回 None
    - _Requirements: 1.1, 1.2, 1.4_

  - [ ] 12.2 实现各内置命令（`ink_core/cli/builtin.py`）
    - `BuiltinCommand` ABC 已在 1.2 定义，此处实现四个具体命令
    - `NewCommand`：调用 ArticleManager.create，返回 SkillResult
    - `InitCommand`：调用 GitManager.init_repo，返回 SkillResult
    - `SkillsListCommand`：调用 SkillRegistry.list_all，格式化输出，返回 SkillResult；对应 `ink skills list` 子动作（顶层子命令 `skills`，Phase 1 仅支持子动作 `list`）
    - `RebuildCommand`：遍历所有 Article，调用 L0/L1Generator 全量重建 .abstract/.overview；再调用 IndexManager 重建 `_index/timeline.json`；可选重建 `_index/graph.json`（需先执行 analyze）；返回 SkillResult
    - _Requirements: 1.10, 1.11, 6.1, 7.6, 2.10_

  - [ ] 12.3 实现 `IntentRouter`（`ink_core/cli/intent.py`）
    - `resolve(intent) -> RouteResult`：先检查 BuiltinCommand 表，再查 SkillRegistry，两者不重叠
    - 匹配到 BuiltinCommand → RouteResult.target = BuiltinCommand 实例
    - 匹配到 Skill → RouteResult.target = Skill 实例
    - 未匹配 → RouteResult.target = None，error 含失败原因，candidates 含可用列表
    - _Requirements: 1.3, 1.4_

  - [ ] 12.4 实现 `CommandExecutor`（`ink_core/core/executor.py`）
    - `execute(intent) -> int`：创建 ExecutionContext（含 session_id）→ 调用 IntentRouter.resolve() → 调用 BuiltinCommand.run() 或 Skill.execute() → 累积 changed_files（含自愈产生的文件）→ 调用 SessionLogger.log() → 条件触发 GitManager.aggregate_commit() → 返回退出码
    - Git commit 触发规则：仅 `new`、`init`、`rebuild`、`publish` 及其他显式写命令触发 `aggregate_commit()`；`search`、`analyze` 即使发生自愈写入，也仅记录到 Session，不自动 commit
    - 统一格式化成功输出（操作名称、目标、耗时）和失败输出（错误类型、位置、建议修复步骤）
    - _Requirements: 1.6, 1.7, 6.8_

  - [ ] 12.5 实现 `InkCLI`（`ink_core/cli/parser.py`）
    - 统一 argparse 子命令 + NLP 自然语言入口
    - 子命令：init、new、rebuild、publish、analyze、search、skills
    - 无子命令时走 NLParser 路由
    - 所有命令最终通过 CommandExecutor.execute() 执行
    - _Requirements: 1.1, 1.5_

  - [ ]* 12.6 写属性测试：意图解析结果可解释
    - **Property 1: 意图解析结果可解释**
    - **Validates: Requirements 1.2, 1.3, 1.4, 1.5**

  - [ ]* 12.7 写属性测试：意图路由正确性
    - **Property 2: 意图路由正确性**
    - **Validates: Requirements 1.3, 1.4**

  - [ ]* 12.8 写属性测试：执行输出格式完整性
    - **Property 3: 执行输出格式完整性**
    - **Validates: Requirements 1.6, 1.7**

- [~] 13. 集成联调：端到端流程
  - [ ] 13.1 将所有组件在 `InkCLI.run()` 中串联
    - 确保 `ink` 入口点可通过 `pip install -e .` 安装后直接使用
    - ArticleManager 操作后自动调用 IndexManager 更新索引
    - 所有写操作通过 CommandExecutor 统一触发 GitManager.aggregate_commit()
    - _Requirements: 1.3, 1.5, 2.8, 6.2, 6.3, 6.4_

  - [ ]* 13.2 写属性测试：幂等性
    - **Property 25: 幂等性**
    - **Validates: Requirements NFR-2**

  - [ ]* 13.3 写属性测试：失败隔离
    - **Property 26: 失败隔离**
    - **Validates: Requirements NFR-4**

  - [ ]* 13.4 写集成测试：完整文章生命周期
    - 创建 → 编辑 → L0/L1 更新 → 发布 → 发布记录 → Git 提交 → 搜索验证
    - _Requirements: 2.1, 2.3, 3.7, 6.2_

  - [ ]* 13.5 写集成测试：Skill 加载 + 执行链路
    - 从 .md 加载 Skill 定义 → 注册 → CLI 调用 → 执行 → 结果输出
    - _Requirements: 7.1, 7.2, 7.6_

  - [ ]* 13.6 写集成测试：自愈机制
    - 删除 L0/L1 文件 → 执行 ink 命令 → 验证自动重建（全量覆盖）
    - _Requirements: 2.9_

  - [ ]* 13.7 写集成测试：Git 提交聚合
    - 单次命令多文件变更 → 验证恰好一次 commit
    - _Requirements: 6.8_

- [~] 14. Final checkpoint - 全量测试通过
  - Ensure all tests pass; unresolved issues SHALL be recorded in an implementation notes file with chosen default behavior.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (hypothesis)
- Unit tests validate specific examples and edge cases (pytest)
- 设计文档使用 Python，所有实现代码使用 Python
