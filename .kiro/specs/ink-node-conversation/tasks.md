# 实施计划：Conversation Processing MVP（ink-node-conversation）

## Sprint 1：定义 Node 边界

### Task 1: 创建 Conversation 数据模型
- [x] 1.1 创建 `ink_core/conversation/__init__.py`
- [x] 1.2 创建 `ink_core/conversation/models.py`，实现 `ConversationStatus` 枚举（`imported`、`archived`）、`Message` dataclass（`role`、`content`、`timestamp`、`metadata`）、`Conversation` dataclass（含所有必填字段）
- [x] 1.3 实现 `Conversation.to_dict()` 序列化方法，处理 `timestamp`/`metadata` 的可选字段省略
- [x] 1.4 实现 `Conversation.from_dict()` 反序列化类方法
- [x] 1.5 编写 `tests/conversation/test_models.py`：单元测试覆盖 `ConversationStatus.is_valid()`、`Message` 创建、`Conversation` 创建
- [x] 1.6 编写 `tests/conversation/test_properties.py`（P1）：属性测试 — Conversation 序列化往返（`to_dict()` → `from_dict()` 字段等价），最少 100 次迭代
  > Requirements: 2.1, 2.2, 2.7, 2.8, 2.9

### Task 2: 新增对话领域异常类
- [x] 2.1 在 `ink_core/core/errors.py` 中新增 `ConversationSourceNotFoundError`、`ConversationFormatDetectionError`、`ConversationDuplicateImportError`、`ConversationNotFoundError` 四个异常类
- [x] 2.2 贯穿使用约束：`ConversationManager.read()` 抛 `ConversationNotFoundError`；`ConversationImporter` 使用 `ConversationSourceNotFoundError` / `ConversationFormatDetectionError` / `ConversationDuplicateImportError`；命令层统一 catch 对话领域异常并转为 `SkillResult`，不回退到字符串错误或 `PathNotFoundError`
  > Requirements: 3.13, 3.14, 3.15, 7.6, 9.6

### Task 3: 创建 ConversationManager 基础
- [x] 3.1 创建 `ink_core/conversation/manager.py`，实现 `ConversationManager.__init__()`（设置 `_normalized_root`、`_raw_root`、`_index_path`）
- [x] 3.2 实现 `ensure_dirs()` — 创建 `_node/conversations/raw/` 和 `_node/conversations/normalized/` 目录
- [x] 3.3 实现 `resolve_path(conversation_id)` — 将 `YYYY/MM/DD-source-slug` 映射到 `_node/conversations/normalized/YYYY/MM/DD-source-slug/`
- [x] 3.4 实现 `save(conversation)` — 创建对话目录 + `assets/` 子目录，写入 `meta.json`
- [x] 3.5 实现 `read(conversation_id)` — 读取 `meta.json` 并反序列化为 `Conversation`，不存在时抛出 `ConversationNotFoundError`（Article 相关继续用 `PathNotFoundError`，对话领域用独立异常）
- [x] 3.6 实现 `_read_index()` / `_write_index()` — 读写 `_index/conversations.json`
- [x] 3.7 实现 `update_index(conversation)` — Upsert 对话条目到索引，保留已有 `linked_articles`，按 `created_at` 倒序
- [x] 3.8 实现 `list_all(source=None)` — 优先从索引读取，索引不存在时调用 `_rebuild_index()`，支持 `source` 过滤
- [x] 3.9 实现 `fingerprint_exists(fingerprint)` — 扫描 `normalized/` 下所有 `meta.json` 检查 SHA256 匹配
- [x] 3.10 实现 `update_linked_articles(conversation_id, article_id)` — 向索引条目的 `linked_articles` 添加文章 ID
- [x] 3.11 实现 `_rebuild_index()` — 扫描 `normalized/` 目录重建索引，并调用 `_scan_article_source_links()` 恢复 `linked_articles`
- [x] 3.12 实现 `_scan_article_source_links()` — 扫描所有 Article 的 `index.md` frontmatter 的 `source_conversations` 字段，构建 `conv_id → [article_id]` 反向映射
- [x] 3.13 编写 `tests/conversation/test_manager.py`：单元测试覆盖 `ensure_dirs`、`save`/`read`、`list_all`、`update_index`、索引重建（含 Article frontmatter 扫描）
- [x] 3.14 编写属性测试 P4（路径映射）：随机 `conversation_id` → `resolve_path()` 路径格式正确
- [x] 3.15 编写属性测试 P10（持久化往返）：随机 Conversation → `save()` → `read()` → 字段等价
- [x] 3.16 编写属性测试 P11（来源过滤）：随机对话集 + 随机 `source` → `list_all(source=X)` 结果全部匹配
  > Requirements: 1.1-1.3, 1.6-1.7, 2.4, 2.6, 7.1-7.7

---

## Sprint 2：Conversation Pipeline

### Task 4: 创建 ConversationNormalizer
- [x] 4.1 创建 `ink_core/conversation/normalizer.py`，实现 `ConversationNormalizer.normalize()` 入口方法
- [x] 4.2 实现 `_normalize_json(data)` — 处理 JSON dict（单对话）和 list（消息数组）
- [x] 4.3 实现 `_normalize_jsonl(records)` — 逐条记录规范化为 Message
- [x] 4.4 实现 `_normalize_text(text)` — 按角色标记（`User:`/`Assistant:`/`System:`/`Human:`/`AI:`/`Bot:`）分割，无标记时交替分配 `user`/`assistant`
- [x] 4.5 实现 `_normalize_message(data)` — 单条消息字典 → Message，处理 `role`/`author`/`sender` 和 `content`/`text`/`body` 字段映射
- [x] 4.6 实现 `_map_role(role)` — 角色名标准化映射（`human`→`user`、`ai`/`bot`→`assistant` 等）
- [x] 4.7 实现 `_extract_title(messages)` — 从首条非空消息提取前 50 字符作为标题
- [x] 4.8 实现 `_generate_session_slug(title)` — 提取或复用 `SlugResolver.generate_slug()` 的无状态 slug 生成逻辑（仅"标题→slug"部分，不引入 workspace 路径冲突检测语义），`post-` 前缀替换为 `session-`，截断到 40 字符
- [x] 4.9 实现 `conversation_id` 生成逻辑：`YYYY/MM/DD-<source>-<session-slug>`
- [x] 4.10 编写 `tests/conversation/test_normalizer.py`：单元测试覆盖 JSON/JSONL/纯文本解析、角色映射、空消息保留、时间戳处理、标题提取
- [x] 4.11 编写属性测试 P2（规范化有效性）：随机输入 → `normalize()` → 验证字段约束（`conversation_id` 格式、`participants` 非空、Message 字段存在、`status` 合法）
- [x] 4.12 编写属性测试 P3（规范化确定性）：相同输入两次 `normalize()` → 结果等价
  > Requirements: 4.1-4.10

### Task 5: 创建 ConversationImporter
- [x] 5.1 创建 `ink_core/conversation/importer.py`，实现 `ConversationImporter.__init__()`
- [x] 5.2 实现 `import_file()` 主流程：文件存在检查 → SHA256 计算 → 重复检测 → 格式检测 → 规范化（先于 raw 复制）→ 复制 raw → 持久化 → 更新索引；当 raw 复制后持久化或索引更新失败时，SHALL 清理本次导入产生的 raw 副本与半成品目录
- [x] 5.3 实现 `_detect_and_parse(content)` — 格式自动检测：JSON → JSONL → 纯文本 → None
- [x] 5.4 编写 `tests/conversation/test_importer.py`：单元测试覆盖成功导入、文件不存在、格式识别失败、重复导入拒绝
- [x] 5.5 编写属性测试 P5（Fingerprint + 去重）：随机文件内容 → SHA256 正确 + 二次导入被拒
- [x] 5.6 编写属性测试 P6（格式检测）：随机 JSON/JSONL/text → 正确识别格式
  > Requirements: 3.1-3.16

### Task 6: 创建 ConversationMarkdownRenderer
- [x] 6.1 创建 `ink_core/conversation/markdown_renderer.py`，实现 `ConversationMarkdownRenderer.render()`
- [x] 6.2 生成 YAML frontmatter（`title`、`conversation_id`、`source`、`created_at`、`participants`、`message_count`、`status`）
- [x] 6.3 按时间顺序渲染消息，含角色 emoji 标识和可选时间戳
- [x] 6.4 实现 `_role_display(role)` — 角色 → 显示名称映射（`user`→`👤 User` 等）
- [x] 6.5 编写 `tests/conversation/test_markdown_renderer.py`：单元测试覆盖 frontmatter 字段、消息渲染顺序、代码块保留
- [x] 6.6 编写属性测试 P7（Markdown 渲染→解析一致性）：随机 Conversation → `render()` → 解析 frontmatter → 字段匹配
- [x] 6.7 编写属性测试 P8（渲染幂等性 — Markdown 部分）：随机 Conversation → `render()` 两次 → 字符串相等
  > Requirements: 5.1-5.9

### Task 7: 创建 ConversationHtmlRenderer
- [x] 7.1 创建 `ink_core/conversation/html_renderer.py`，实现 `ConversationHtmlRenderer.__init__()` 和 `render()`
- [x] 7.2 实现内置默认 HTML 模板（Jinja2 + autoescape），含对话标题、来源、时间、参与者、消息列表
- [x] 7.3 实现 `render_to_file()` — 渲染并写入文件
- [x] 7.4 实现 `_render_template()` — 优先加载 `_templates/site/conversation.html` 用户模板，不存在时使用内置模板
- [x] 7.5 消息内容通过 `render_markdown()` 处理 Markdown → HTML（代码块 → `<pre><code>`）
- [x] 7.6 编写 `tests/conversation/test_html_renderer.py`：单元测试覆盖模板优先级、消息渲染、代码块处理
- [x] 7.7 编写属性测试 P8（渲染幂等性 — HTML 部分）：随机 Conversation → `render()` 两次 → 字符串相等
- [x] 7.8 编写属性测试 P9（XSS 转义）：随机含 HTML 特殊字符的消息 → `render()` → 无未转义标签
  > Requirements: 6.1-6.9

### Task 8: 创建 CLI 命令 — import-conversation
- [x] 8.1 创建 `ink_core/conversation/commands.py`，实现 `ImportConversationCommand(BuiltinCommand)`
- [x] 8.2 `run()` 方法：解析 `file_path`（支持相对/绝对路径）、`source`、`title` 参数，调用 `ConversationImporter.import_file()`
- [x] 8.3 在 `ink_core/cli/parser.py` 的 `_build_executor()` 中注册 `import-conversation` 命令
- [x] 8.4 在 `_build_arg_parser()` 中添加 `import-conversation` 子命令（`file` 位置参数、`--source`、`--title` 可选参数）
- [x] 8.5 在 `_intent_from_namespace()` 中添加 `import-conversation` 分支
- [x] 8.6 在 `ink_core/core/executor.py` 的 `_WRITE_COMMANDS` 集合中添加 `import-conversation`
  > Requirements: 3.1, 3.11, 3.12, 3.16

### Task 9: 创建 CLI 命令 — render-conversation
- [x] 9.1 在 `commands.py` 中实现 `RenderConversationCommand(BuiltinCommand)`
- [x] 9.2 `run()` 方法：读取 Conversation → 始终生成 `index.md` → 可选 `--preview` 生成 `preview.html`（不生成 `index.html`）
- [x] 9.3 在 `parser.py` 中注册 `render-conversation` 子命令（`conversation_id` 位置参数、`--preview` 可选标志）
- [x] 9.4 在 `_intent_from_namespace()` 和 `_WRITE_COMMANDS` 中添加对应分支
  > Requirements: 5.7, 6.10

### Task 10: 创建 CLI 命令 — build-conversations
- [x] 10.1 在 `commands.py` 中实现 `BuildConversationsCommand(BuiltinCommand)`
- [x] 10.2 `run()` 方法：读取索引 → 遍历对话 → 生成 `_site/conversations/YYYY/MM/YYYY-MM-DD-<source>-<slug>/index.html` → 输出统计
- [x] 10.3 实现失败隔离：单个对话渲染失败跳过，继续处理其余，汇总错误
- [x] 10.4 `build-conversations` SHALL NOT 读取或复制 normalized 目录下的 `preview.html`；`preview.html` 仅作为本地预览辅助产物，不纳入 `_index/conversations.json` 索引，不出现在 `_site/` 输出中
- [x] 10.5 在 `parser.py` 中注册 `build-conversations` 子命令
- [x] 10.6 在 `_intent_from_namespace()` 和 `_WRITE_COMMANDS` 中添加对应分支
  > Requirements: 8.1-8.8

### Task 11: 编写 Sprint 2 集成测试
- [x] 11.1 创建 `tests/conversation/conftest.py`：共享 fixtures（临时工作区目录、示例 JSON/JSONL/纯文本对话文件）
- [x] 11.2 编写 `tests/conversation/test_integration.py`：完整导入链路（`import_file` → `meta.json` + raw 副本 + `conversations.json`）
- [x] 11.3 编写渲染链路集成测试（`render-conversation` → `index.md`，可选 `preview.html`）
- [x] 11.4 编写批量构建集成测试（`build-conversations` → `_site/conversations/` 下 HTML 文件）
- [x] 11.5 编写构建隔离硬断言测试：先记录 `_site/index.html` 和 `_site/feed.xml` 的内容哈希，运行 `build-conversations`，再断言二者内容未变化（不只是概念性隔离，而是哈希级断言）
- [x] 11.6 编写重复导入拒绝测试
- [x] 11.7 编写失败隔离测试（单个对话渲染失败不影响批量构建）
  > Requirements: NFR-1 至 NFR-6

---

## Sprint 3：Article ↔ Conversation 来源链

### Task 12: 创建 CLI 命令 — link-source
- [x] 12.1 在 `commands.py` 中实现 `LinkSourceCommand(BuiltinCommand)`
- [x] 12.2 `run()` 方法：验证 Article 存在 → 验证 Conversation 存在 → 更新 Article frontmatter `source_conversations` → 更新 `conversations.json` 的 `linked_articles`
- [x] 12.3 处理重复关联（已存在时返回提示，不重复添加）
- [x] 12.4 在 `parser.py` 中注册 `link-source` 子命令（`article_id` 位置参数、`--conversation` 必选参数）
- [x] 12.5 在 `_intent_from_namespace()` 和 `_WRITE_COMMANDS` 中添加对应分支
- [x] 12.6 编写 `tests/conversation/test_commands.py`：单元测试覆盖 link-source 的成功/重复/不存在场景
- [x] 12.7 编写属性测试 P12（来源链接完整性）：随机 Article + Conversation → `link-source` → 双向验证 + 重复执行不产生重复条目
- [x] 12.8 编写来源链接集成测试（Article frontmatter + `conversations.json` 双向更新）
  > Requirements: 9.1-9.11

---

## Sprint 4：Node 内搜索扩展

### Task 13: SearchSkill 重构 — 提取 `_search_articles()`
- [x] 13.1 将 `SearchSkill.execute()` 中现有的 Article 搜索逻辑提取为 `_search_articles(query, params)` 方法（返回 `SkillResult`）
- [x] 13.2 `execute()` 方法改为调用 `_search_articles()`，保持现有行为不变
- [x] 13.3 运行现有搜索测试确保重构无回归
  > 前置步骤：当前 `execute()` 内联了 Article 搜索逻辑，需先提取才能添加 `--type` 分流

### Task 14: SearchSkill 扩展 — 对话搜索
- [x] 14.1 在 `SearchSkill.execute()` 中添加 `content_type = params.get("type")` 分流逻辑
- [x] 14.2 实现 `_search_conversations(query, params)` — 在对话 `index.md` 中执行关键词搜索，结果含 `conversation_id`、`title`、`snippet`、`source`、`content_type`
- [x] 14.3 实现 `_merge_results(query, article_result, conv_result)` — 合并 Article 和 Conversation 结果，添加 `content_type` 字段
- [x] 14.4 在 `parser.py` 的 `search` 子命令中添加 `--type` 参数（`conversation`/`all`）
- [x] 14.5 在 `_intent_from_namespace()` 的 `search` 分支中传递 `type` 参数
- [x] 14.6 编写 `tests/conversation/test_search_extension.py`：单元测试覆盖 `--type conversation`、`--type all`、默认行为、空结果建议；其中默认行为回归测试须单独断言：未指定 `--type` 时，结果中不得出现任何 conversation 命中
- [x] 14.7 编写属性测试 P13（搜索类型隔离）：随机查询 + 混合内容 → 按 type 过滤正确
- [x] 14.8 编写属性测试 P14（对话搜索排序）：随机对话集 + 查询 → 结果按 `hit_count` 降序 + `created_at` 降序
  > Requirements: 10.1-10.9

---

## 收尾

### Task 15: .gitignore 配置
- [x] 15.1 在仓库根 `.gitignore` 中添加 `_node/conversations/raw/` 排除规则（原始缓存可选忽略），确保 `_node/conversations/normalized/` 不被排除
- [x] 15.2 同步更新 `ink init` 生成的默认 `.gitignore` 模板内容，使新工作区与老工作区行为一致
  > Requirements: 1.8

### Task 16: 自定义 Hypothesis 生成器
- [x] 16.1 在 `tests/conversation/conftest.py` 中创建共享的 `message_strategy`、`conversation_strategy` Hypothesis 生成器，供所有属性测试复用
  > 支撑所有 Property-Based Tests（P1-P14）

### Task 17: 文档同步
- [x] 17.1 README 增加 `_node/conversations/` 目录结构说明（`raw/` vs `normalized/` 语义）
- [x] 17.2 README 增加 `import-conversation`、`render-conversation`、`build-conversations`、`link-source` 四个命令的用法说明
- [x] 17.3 CLI help 文案同步：确保 `[对话]` 命令分组清晰
- [x] 17.4 文档中说明 `preview.html`（本地预览）与 `_site/.../index.html`（正式站点输出）的区别
  > 避免后续遗忘约束，保持文档与实现同步
