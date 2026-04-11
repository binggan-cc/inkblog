# 需求文档：Conversation Processing MVP（ink-node-conversation）

## 1. 文档信息

- 项目名称：InkBlog Node — Conversation Processing MVP
- 阶段：v0.5.0
- 文档类型：Requirement Specification
- 版本：v1.1
- 状态：Draft

---

## 2. 简介

InkBlog Node v0.5.0 引入 **Conversation Processing MVP**，让 Node 能够吃进本地 AI/Agent 对话缓存文件，将其转化为：

1. **可归档的 Markdown 文件**（用于 Git 追踪、本地搜索、人工审阅、AI 再加工）
2. **可浏览的静态 HTML 页面**（用于回看完整对话、阅读长会话）
3. **可被博客文章引用的来源素材**（文章 ↔ 对话双向溯源）

Conversation 是 Node 的第二内容类型（第一类型为 Article），遵循与 Article 相同的 FS-as-DB 哲学和最小依赖原则。Conversation 不替代 Article，而是作为 Article 的上游素材来源。

### Sprint 划分

v0.5.0 按四个 Sprint 递进交付：

| Sprint | 主题 | 关键交付 |
|--------|------|---------|
| Sprint 1 | 定义 Node 边界 | 明确单工作区 + 单节点 + blog 为核心对象的边界，引入 `_node/` 目录结构，定义 Conversation 标准对象 |
| Sprint 2 | Conversation Pipeline | 本地 JSON/JSONL/纯文本缓存文件 → 规范化 → Markdown 归档 + 静态 HTML 渲染 |
| Sprint 3 | Article ↔ Conversation 来源链 | Article frontmatter 增加 `source_conversations` / `derived_from` / `source_notes` 字段，`ink link-source` 命令 |
| Sprint 4 | Node 内搜索扩展 | SearchSkill 扩展到 article + conversation，不做全类型 Artifact 统一模型 |

---

## 3. 范围

### 3.1 In Scope

v0.5.0 SHALL 包含以下能力：

1. `_node/` 目录结构定义与初始化
2. 标准 Conversation 对象定义（`meta.json`）
3. 本地对话缓存文件导入（JSON、JSONL、纯文本）
4. 多格式对话规范化为标准 Conversation 对象
5. 规范化对话的 Markdown 归档渲染（`index.md`）
6. 规范化对话的静态 HTML 页面渲染（`index.html`）
7. ConversationManager：对话 CRUD、路径解析、列表查询
8. Article ↔ Conversation 双向来源链接
9. 对话相关 CLI 命令（导入、渲染、批量构建、来源绑定）
10. SearchSkill 扩展：支持对话内容搜索
11. SiteBuilder 扩展：对话页面构建入口
12. `_index/conversations.json` 对话清单索引

### 3.2 Out of Scope

v0.5.0 SHALL NOT 包含以下能力：

1. 平台特定格式解析器（如 ChatGPT 导出格式、Claude 导出格式等专有格式）
2. 对话的 AI 自动摘要生成
3. 对话标签体系与分类索引
4. AnalyzeSkill 对话分析扩展
5. 对话搜索的倒排索引
6. 对话内容的向量检索
7. 多节点对话同步
8. Hub 层对话汇聚
9. 对话内嵌图片/视频/附件的一等对象管理
10. 复杂全局目录结构（artifacts/、images/、graph-assets/ 等）
11. 全类型 Artifact 统一模型（ContentItem 等）
12. 多工作区 / 多节点协同

---

## 4. 设计原则

1. **FS-as-DB**：对话数据 SHALL 以文件系统为唯一存储，目录结构表达关系
2. **最小依赖**：对话处理 SHALL NOT 引入新的必选运行时依赖
3. **Blog-first**：博客仍为核心对象，对话为辅助内容类型，不改变博客主链路
4. **单工作区 + 单节点**：v0.5.0 仅面向单个工作区内的单个 Node 运行
5. **可重建**：对话的 Markdown 归档和 HTML 页面 SHALL 可从 `meta.json` + 原始缓存重新生成
6. **Hub-ready**：Conversation 的 canonical ID 和目录结构 SHALL 为未来 Hub 汇聚预留边界

---

## 5. 词汇表

- **Node**：InkBlog Node，面向单个 Agent / 单个知识域的本地知识整理与 blog 产出节点
- **Conversation**：一次完整的 AI/Agent 对话，包含多条消息，对应一个独立目录
- **Conversation_ID**：对话的规范唯一标识（canonical identifier），格式为 `YYYY/MM/DD-<source>-<session-slug>`，同时作为 `_node/conversations/normalized/` 下的相对路径标识
- **Message**：对话中的单条消息，包含角色、内容、时间戳等字段
- **ConversationImporter**：读取本地缓存文件、识别源格式的模块
- **ConversationNormalizer**：将不同源格式转换为标准 Conversation 对象的模块
- **ConversationMarkdownRenderer**：将标准 Conversation 对象输出为 Markdown 归档的模块
- **ConversationHtmlRenderer**：将标准 Conversation 对象输出为静态 HTML 页面的模块
- **ConversationManager**：对话 CRUD、路径解析、列表查询的管理模块
- **Source_Conversations**：Article frontmatter 中记录来源对话的字段
- **Raw Cache**：原始对话缓存文件，存放于 `_node/conversations/raw/` 下
- **Normalized Conversation**：经规范化处理后的对话，存放于 `_node/conversations/normalized/` 下

---

## 6. 数据结构约定

### 6.1 标准 Conversation 对象（最小字段集）

```json
{
  "conversation_id": "2026/04/11-openclaw-session-001",
  "source": "openclaw",
  "source_file": "_node/conversations/raw/openclaw/session-001.json",
  "source_fingerprint": "a1b2c3d4e5f6...sha256...",
  "title": "讨论 InkBlog Node 架构",
  "created_at": "2026-04-11T10:30:00",
  "updated_at": "2026-04-11T12:00:00",
  "participants": ["user", "assistant"],
  "messages": [
    {
      "role": "user",
      "content": "消息内容",
      "timestamp": "2026-04-11T10:30:00",
      "metadata": {}
    }
  ],
  "assets": [],
  "status": "archived"
}
```

必填字段：`conversation_id`、`source`、`source_file`、`source_fingerprint`、`title`、`created_at`、`updated_at`、`participants`、`messages`、`status`

- `source_fingerprint`：原始文件内容的 SHA256 哈希值，用于重复导入检测

每条 Message 必填字段：`role`、`content`

每条 Message 可选字段：`timestamp`、`metadata`

`assets` 为可选字段，默认空数组。

`status` 枚举值：`imported`（已导入未审阅）、`archived`（已归档）

### 6.2 对话目录结构

normalized 目录的叶目录名严格等于 `conversation_id` 的最后一段（即 `DD-<source>-<session-slug>`），完整路径为 `_node/conversations/normalized/YYYY/MM/DD-<source>-<session-slug>/`。

```
_node/
  conversations/
    raw/                              # 原始缓存文件（按来源分目录）
      openclaw/
        session-001.json
      other/
        export-2026-04.jsonl
    normalized/                       # 规范化后的对话（按日期组织）
      2026/
        04/
          11-openclaw-session-001/     # 叶目录 = conversation_id 最后一段
            index.md                  # Markdown 归档
            meta.json                 # 标准 Conversation 对象
            assets/                   # 对话关联资源
```

### 6.3 对话静态输出目录

`_site` 输出目录使用完整日期叶目录名（`YYYY-MM-DD-<source>-<session-slug>`），用于展示友好的 URL 路径。这与 normalized 目录的路径语义分离：normalized 路径是源数据路径，`_site` 路径是展示路径。

```
_site/
  conversations/
    2026/
      04/
        2026-04-11-openclaw-session-001/
          index.html
```

### 6.4 Article frontmatter 来源字段（Sprint 3）

Article 的 `index.md` frontmatter MAY 包含以下可选字段：

```yaml
source_conversations:
  - "2026/04/11-openclaw-session-001"
derived_from: "2026/04/11-openclaw-session-001"
source_notes: "基于与 OpenClaw 的架构讨论整理"
```

- `source_conversations`：来源对话 Conversation_ID 列表
- `derived_from`：主要来源对话 Conversation_ID（单个）
- `source_notes`：来源说明文本

### 6.5 `_index/conversations.json` 索引格式

```json
[
  {
    "conversation_id": "2026/04/11-openclaw-session-001",
    "source": "openclaw",
    "title": "讨论 InkBlog Node 架构",
    "created_at": "2026-04-11T10:30:00",
    "message_count": 42,
    "status": "archived",
    "linked_articles": ["2026/04/12-inkblog-architecture"]
  }
]
```

必填字段：`conversation_id`、`source`、`title`、`created_at`、`message_count`、`status`

可选字段：`linked_articles`（默认空数组）

索引 SHOULD 按 `created_at` 倒序排列。

---


## 7. 需求

---

### Sprint 1：定义 Node 边界

> 明确单工作区 + 单节点 + blog 为核心对象的边界，引入 `_node/` 目录结构，定义 Conversation 标准对象。

---

### 需求 1：Node 边界与 `_node/` 目录结构

**用户故事：** 作为 Node 运维者，我希望系统明确定义单工作区、单节点的运行边界，并引入 `_node/` 目录作为非 blog 内容的存放区域，从而在不破坏现有 blog 结构的前提下承载新的内容类型。

#### 验收标准

1. THE System SHALL 在工作区根目录下支持 `_node/` 顶层目录，用于存放非 Article 类型的内容数据
2. THE System SHALL 在 `_node/` 下创建 `conversations/raw/` 和 `conversations/normalized/` 子目录结构
3. WHEN 用户首次执行对话相关命令时，THE System SHALL 自动创建 `_node/conversations/` 目录结构（若不存在）
4. THE System SHALL 保持 `YYYY/MM/DD-slug/` 目录结构专用于 Article（blog 内容），不在该结构下存放对话数据
5. THE System SHALL 保持 `YYYY/MM/DD-journal/` 目录结构专用于 Agent 日记，不在该结构下存放对话数据
6. THE `_node/conversations/raw/` 目录 SHALL 按来源名称组织子目录（如 `openclaw/`、`other/`）
7. THE `_node/conversations/normalized/` 目录 SHALL 按 `YYYY/MM/` 日期组织子目录，每个对话一个独立目录
8. THE System SHALL 在 `.gitignore` 中默认排除 `_node/conversations/raw/`（原始缓存可选忽略），但 SHALL NOT 排除 `_node/conversations/normalized/`（规范化数据建议纳入版本控制）

### 需求 2：标准 Conversation 对象定义

**用户故事：** 作为系统开发者，我希望有一个明确的标准 Conversation 数据模型，从而所有对话处理模块共享统一的数据契约。

#### 验收标准

1. THE Conversation 对象 SHALL 包含以下必填字段：`conversation_id`、`source`、`source_file`、`source_fingerprint`、`title`、`created_at`、`updated_at`、`participants`、`messages`、`status`
2. THE Conversation 对象中每条 Message SHALL 至少包含 `role` 和 `content` 两个必填字段
3. THE Conversation 对象的 `conversation_id` SHALL 遵循 `YYYY/MM/DD-<source>-<session-slug>` 格式
4. THE `conversation_id` SHALL 同时作为 Conversation 的 canonical identifier 和相对路径标识，可直接映射到 `_node/conversations/normalized/<conversation_id>/` 目录
5. THE Conversation 对象的 `status` SHALL 仅接受 `imported` 和 `archived` 两个枚举值
6. THE Conversation 对象 SHALL 以 `meta.json` 文件形式持久化存储于对话目录中
7. THE Conversation 对象 SHALL 支持序列化为 JSON 后再反序列化回 Conversation 对象，结果与原始对象语义等价（往返属性）
8. THE Conversation 对象的 `participants` SHALL 为非空字符串数组
9. THE Conversation 对象的 `messages` SHALL 为数组，允许为空数组（表示无消息的占位对话）
10. THE Conversation 对象的 `source_fingerprint` SHALL 为原始文件内容的 SHA256 哈希值，用于跨路径的重复导入检测

---

### Sprint 2：Conversation Pipeline

> 本地 JSON/JSONL/纯文本缓存文件 → 规范化 → Markdown 归档 + 静态 HTML 渲染。

---

### 需求 3：对话导入

**用户故事：** 作为知识整理者，我希望通过 `ink import-conversation` 将本地 AI 对话缓存文件导入 Node，从而将散落的对话记录集中管理。

#### 验收标准

1. THE CLI SHALL 支持 `ink import-conversation <file>` 命令，接受本地文件路径作为参数
2. WHEN 用户执行 `ink import-conversation <file>` 时，THE ConversationImporter SHALL 读取指定文件并自动识别文件格式（JSON、JSONL、纯文本）
3. WHEN 文件格式为 JSON 时，THE ConversationImporter SHALL 将文件解析为 JSON 对象或 JSON 数组
4. WHEN 文件格式为 JSONL 时，THE ConversationImporter SHALL 逐行解析，每行作为一条独立 JSON 记录
5. WHEN 文件格式为纯文本时，THE ConversationImporter SHALL 按对话分隔符（空行或角色标记如 `User:` / `Assistant:`）解析为消息序列
6. WHEN 导入成功时，THE ConversationImporter SHALL 将原始文件复制到 `_node/conversations/raw/<source>/` 目录下保留原始副本
7. WHEN 导入成功时，THE ConversationImporter SHALL 计算原始文件内容的 SHA256 哈希值作为 `source_fingerprint`，写入标准 Conversation 对象
8. WHEN 导入成功时，THE ConversationImporter SHALL 调用 ConversationNormalizer 将解析结果转换为标准 Conversation 对象
9. WHEN 导入成功时，THE ConversationManager SHALL 在 `_node/conversations/normalized/YYYY/MM/` 下创建对话目录，写入 `meta.json`
10. WHEN 导入成功时，THE System SHALL 更新 `_index/conversations.json` 索引
11. THE CLI SHALL 支持 `--source <source-name>` 可选参数，用于指定对话来源标识；WHEN 未指定时，THE System SHALL 使用 `unknown` 作为默认来源
12. THE CLI SHALL 支持 `--title <title>` 可选参数，用于指定对话标题；WHEN 未指定时，THE System SHALL 从对话内容中提取首条消息的前 50 个字符作为标题
13. IF 指定文件不存在，THEN THE ConversationImporter SHALL 返回文件不存在错误及文件路径
14. IF 文件内容无法解析为任何支持的格式，THEN THE ConversationImporter SHALL 返回格式识别失败错误，并列出支持的格式列表
15. IF 同一源文件内容已被导入过（通过 `source_fingerprint` SHA256 匹配），THEN THE ConversationImporter SHALL 返回重复导入警告，不创建新的对话记录
16. WHEN 导入完成时，THE CLI SHALL 输出结构化执行摘要，至少包含：对话 ID、消息数量、来源标识、存储路径

### 需求 4：对话规范化

**用户故事：** 作为知识整理者，我希望不同来源的对话缓存都能被转换为统一的标准格式，从而后续处理流程无需关心原始格式差异。

#### 验收标准

1. THE ConversationNormalizer SHALL 接受解析后的原始数据和源格式标识，输出标准 Conversation 对象
2. THE ConversationNormalizer SHALL 为每个 Conversation 生成唯一的 `conversation_id`，格式为 `YYYY/MM/DD-<source>-<session-slug>`
3. WHEN 原始数据包含时间戳信息时，THE ConversationNormalizer SHALL 使用原始时间戳填充 `created_at` 和 `updated_at`
4. WHEN 原始数据不包含时间戳信息时，THE ConversationNormalizer SHALL 使用导入时间作为 `created_at` 和 `updated_at`
5. THE ConversationNormalizer SHALL 从原始数据中提取 `participants` 列表；WHEN 无法提取时，SHALL 使用 `["user", "assistant"]` 作为默认值
6. THE ConversationNormalizer SHALL 确保每条 Message 至少包含 `role` 和 `content` 两个必填字段
7. WHEN 原始数据来自纯文本或无法识别角色的简单序列时，THE ConversationNormalizer MAY 根据消息顺序交替分配 `user` 和 `assistant` 角色；WHEN 原始数据为结构化输入（JSON/JSONL）时，THE ConversationNormalizer SHALL 优先保留原始角色字段，无法识别时使用 `unknown`
8. WHEN Message 的 `content` 为空字符串时，THE ConversationNormalizer SHALL 保留该消息但将 `content` 设为空字符串，不丢弃消息
9. THE ConversationNormalizer SHALL 对同一输入的多次调用返回语义等价的 Conversation 对象（确定性）
10. THE ConversationNormalizer SHALL 将新导入对话的 `status` 设为 `imported`

### 需求 5：对话 Markdown 渲染

**用户故事：** 作为知识整理者，我希望每个对话都能生成可读的 Markdown 归档文件，从而方便 Git 追踪、本地搜索和人工审阅。

#### 验收标准

1. THE ConversationMarkdownRenderer SHALL 接受标准 Conversation 对象，输出 Markdown 格式的 `index.md` 文件内容
2. THE 输出的 `index.md` SHALL 包含 YAML frontmatter，至少包含以下字段：`title`、`conversation_id`、`source`、`created_at`、`participants`、`message_count`、`status`
3. THE 输出的 `index.md` 正文 SHALL 按时间顺序渲染每条消息，每条消息至少包含角色标识和内容
4. WHEN Message 包含 `timestamp` 时，THE ConversationMarkdownRenderer SHALL 在消息渲染中包含时间戳信息
5. THE ConversationMarkdownRenderer SHALL 使用 Markdown 标题或分隔符区分不同角色的消息，确保人类可读性
6. THE ConversationMarkdownRenderer SHALL 对消息内容中已有的 Markdown 格式进行适当处理，保留代码块的原始格式
7. WHEN 用户执行 `ink render-conversation <conversation-id>` 时，THE System SHALL 读取对应的 `meta.json`，调用 ConversationMarkdownRenderer 生成 `index.md`，写入对话目录
8. THE ConversationMarkdownRenderer SHALL 对同一 Conversation 对象的多次调用返回完全相同的结果（幂等性）
9. FOR ALL 有效的 Conversation 对象，将其渲染为 `index.md` 后解析 frontmatter，提取的 `conversation_id`、`title`、`source`、`message_count` SHALL 与原始 Conversation 对象一致（渲染→解析一致性）

### 需求 6：对话 HTML 渲染

**用户故事：** 作为知识整理者，我希望每个对话都能生成可浏览的静态 HTML 页面，从而获得比纯 Markdown 更好的阅读体验。

#### 验收标准

1. THE ConversationHtmlRenderer SHALL 接受标准 Conversation 对象，输出 HTML 格式的 `index.html` 文件内容
2. THE 输出的 HTML 页面 SHALL 包含对话标题、来源、创建时间、参与者信息
3. THE 输出的 HTML 页面 SHALL 按时间顺序渲染每条消息，使用视觉样式区分不同角色（如不同背景色或对齐方式）
4. THE ConversationHtmlRenderer SHALL 使用 Jinja2 模板引擎渲染 HTML 页面
5. WHEN `_templates/site/conversation.html` 存在时，THE ConversationHtmlRenderer SHALL 优先使用用户自定义模板
6. IF `_templates/site/conversation.html` 不存在，THEN THE ConversationHtmlRenderer SHALL 使用内置默认模板
7. THE 输出的 HTML 页面 SHALL 对消息内容中的 HTML 特殊字符进行转义，防止 XSS 注入
8. WHEN 消息内容包含 Markdown 代码块时，THE ConversationHtmlRenderer SHALL 将代码块渲染为可读的 `<pre><code>` 结构，并附带语言 class 或基础样式，以支持后续样式增强
9. THE ConversationHtmlRenderer SHALL 对同一 Conversation 对象的多次调用返回完全相同的结果（幂等性）
10. WHEN 用户执行 `ink render-conversation <conversation-id>` 时，THE System SHALL 生成 Markdown 归档（`index.md`）；HTML 预览（`preview.html`）为可选输出，不生成 `index.html`（`index.html` 由 `build-conversations` 统一生成到 `_site/`）

### 需求 7：对话管理

**用户故事：** 作为知识整理者，我希望能够列出、查看和管理已导入的对话，从而掌握 Node 中的对话资产全貌。

#### 验收标准

1. THE ConversationManager SHALL 提供 `list_all()` 方法，返回所有已规范化对话的摘要列表
2. THE ConversationManager SHALL 提供 `read(conversation_id)` 方法，根据 Conversation_ID 读取完整的 Conversation 对象
3. THE ConversationManager SHALL 提供 `resolve_path(conversation_id)` 方法，将 Conversation_ID 解析为对话目录的绝对路径
4. WHEN `_index/conversations.json` 不存在时，THE ConversationManager SHALL 通过扫描 `_node/conversations/normalized/` 目录重建索引；重建过程还 SHALL 扫描所有 Article frontmatter 的 `source_conversations` 字段，反向恢复每个对话的 `linked_articles` 关系
5. THE ConversationManager SHALL 提供 `update_index(conversation)` 方法，在对话创建或更新时同步更新 `_index/conversations.json`
6. IF 指定的 Conversation_ID 对应的目录不存在，THEN THE ConversationManager SHALL 返回路径不存在错误及当前可用对话列表
7. THE ConversationManager SHALL 支持按来源（`source`）过滤对话列表

### 需求 8：对话批量构建

**用户故事：** 作为知识整理者，我希望通过一条命令批量生成所有对话的静态页面，从而与博客站点一起部署。

#### 验收标准

1. THE CLI SHALL 支持 `ink build-conversations` 命令，批量生成所有对话的静态 HTML 页面
2. WHEN 执行 `ink build-conversations` 时，THE System SHALL 读取 `_index/conversations.json` 获取对话列表
3. WHEN 处理每个对话时，THE System SHALL 在 `_site/conversations/YYYY/MM/YYYY-MM-DD-<source>-<session-slug>/index.html` 路径生成对应 HTML 页面
4. WHEN `ink build-conversations` 执行完成时，THE CLI SHALL 输出构建统计信息，至少包含：生成的 HTML 页面数量、构建耗时
5. THE SiteBuilder SHALL 新增对话页面构建入口，不改变博客主线构建逻辑
6. WHEN 执行 `ink build` 时，THE SiteBuilder SHALL NOT 自动构建对话页面；对话页面 SHALL 通过 `ink build-conversations` 独立构建
7. THE `build-conversations` 命令 SHALL NOT 修改博客首页文章列表或 RSS feed 生成结果；对话内容 SHALL NOT 出现在 `_site/index.html` 或 `_site/feed.xml` 中
8. IF `_index/conversations.json` 不存在或为空，THEN THE System SHALL 输出无对话可构建的提示信息

---

### Sprint 3：Article ↔ Conversation 来源链

> 给 Article 增加 `source_conversations` / `derived_from` / `source_notes` 来源链字段，实现双向溯源。

---

### 需求 9：Article ↔ Conversation 来源链接

**用户故事：** 作为知识整理者，我希望将博客文章与来源对话建立关联，从而实现文章可追溯来源、对话可反查产出。

#### 验收标准

1. THE CLI SHALL 支持 `ink link-source <article-id> --conversation <conversation-id>` 命令
2. WHEN 用户执行 `ink link-source` 时，THE System SHALL 将指定的 Conversation_ID 添加到 Article 的 `index.md` frontmatter 的 `source_conversations` 列表中
3. WHEN `source_conversations` 字段不存在时，THE System SHALL 创建该字段并写入指定的 Conversation_ID
4. WHEN 指定的 Conversation_ID 已存在于 `source_conversations` 列表中时，THE System SHALL 返回已关联提示，不重复添加
5. IF 指定的 Article_ID 不存在，THEN THE System SHALL 返回文章不存在错误
6. IF 指定的 Conversation_ID 不存在，THEN THE System SHALL 返回对话不存在错误
7. WHEN 来源链接建立成功时，THE System SHALL 同步更新 `_index/conversations.json` 中对应对话的 `linked_articles` 字段
8. WHEN 来源链接建立成功时，THE CLI SHALL 输出关联结果摘要，包含文章 ID 和对话 ID
9. THE System SHALL 支持通过 Article frontmatter 的 `source_conversations` 字段正向查询文章的来源对话列表
10. THE System SHALL 支持通过 `_index/conversations.json` 的 `linked_articles` 字段反向查询对话产出的文章列表
11. THE Article frontmatter 的 `source_conversations`、`derived_from`、`source_notes` 字段 SHALL 为可选字段，不影响现有文章的解析和处理

---

### Sprint 4：Node 内搜索扩展

> SearchSkill 扩展到 article + conversation，但仍不做全类型 Artifact 统一模型。

---

### 需求 10：对话搜索扩展

**用户故事：** 作为知识整理者，我希望通过现有的搜索功能也能检索到对话内容，从而在 Node 内统一查找信息。

#### 验收标准

1. THE SearchSkill SHALL 支持 `--type conversation` 参数，用于限定搜索范围为对话内容
2. WHEN 用户执行 `ink search "<query>" --type conversation` 时，THE SearchSkill SHALL 在对话的 `index.md` 中执行关键词搜索
3. WHEN 搜索类型为 conversation 时，每条搜索结果 SHALL 至少包含：Conversation_ID、标题、匹配片段、来源标识
4. WHEN 用户执行 `ink search "<query>"` 且未指定 `--type` 时，THE SearchSkill SHALL 保持现有行为，仅搜索 Article 内容（不自动包含对话）
5. THE SearchSkill SHALL 对对话搜索结果按关键词命中次数降序排列；WHEN 命中次数相同时，按 `created_at` 倒序排列
6. WHEN 对话搜索结果为空时，THE SearchSkill SHALL 返回原始查询词、无结果提示和至少 1 条改写建议
7. THE SearchSkill SHALL 支持 `--type all` 参数，同时搜索 Article 和 Conversation 内容，结果按统一评分排序
8. WHEN 使用 `--type all` 时，每条搜索结果 SHALL 包含 `content_type` 字段（`article` 或 `conversation`），用于区分结果来源
9. IN v0.5.0，`--type all` SHALL 仅在响应层统一输出字段格式，SHALL NOT 要求内部引入统一的内容领域模型（如 ContentItem / SearchResultItem）；Article 和 Conversation 的搜索逻辑 SHALL 保持独立实现

---

## 8. 非功能需求

1. **可重建性**：对话的 `index.md` 和 HTML 页面 SHALL 可从 `meta.json` 重新生成，删除后不导致源数据丢失
2. **幂等性**：对同一对话重复执行 `render-conversation` 或 `build-conversations` SHALL 产生完全相同的输出
3. **可读性**：对话的 Markdown 归档 SHALL 保持人类可读，便于手工编辑和 Git diff
4. **失败隔离**：单个对话的导入或渲染失败 SHALL NOT 影响其他对话或已有 Article 数据
5. **性能**：在 500 个对话以内的规模下，`build-conversations` SHOULD 保持可接受的本地交互速度
6. **向后兼容**：v0.5.0 的对话功能 SHALL NOT 改变现有 Article 的目录结构、CLI 命令行为或索引格式

---

## 9. 风险与开放问题

1. 纯文本对话格式的解析规则（角色标记、消息分隔符）在不同来源间差异较大，v0.5.0 以最简规则为主，复杂格式留待后续扩展
2. `conversation_id` 依赖日期 + source + session-slug 组合，同一天同一来源的多个会话需要通过 session-slug 区分，可能存在冲突风险
3. 对话的 `index.md` 在消息量较大时（如 200+ 条消息）文件体积可能较大，v0.5.0 不做分页处理
4. Article frontmatter 新增的 `source_conversations`、`derived_from`、`source_notes` 字段为可选字段，不影响现有文章的解析
5. `_node/` 目录是新引入的顶层目录，需要在 `.gitignore` 中合理配置（`raw/` 建议忽略，`normalized/` 建议纳入版本控制）
6. 对话搜索在 v0.5.0 中仅支持基于 `index.md` 的关键词搜索，不支持对 `meta.json` 结构化字段的精确查询
7. `ink build-conversations` 与 `ink build` 独立运行，部署时需要用户分别执行两条命令；后续版本可考虑统一构建入口
8. 对话 HTML 模板的默认样式需要与博客站点的默认样式保持视觉一致性，但 v0.5.0 不强制要求完全统一
9. Sprint 4 的搜索扩展不引入全类型 Artifact 统一模型，SearchSkill 内部通过 `content_type` 参数分流，Article 和 Conversation 保持独立搜索逻辑，仅在响应层统一输出字段格式