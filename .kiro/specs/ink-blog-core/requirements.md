# 需求文档

## 简介

Ink Blog Core（Phase 1）是一个基于 CLI+Skills+Markdown 三位一体架构的个人博客系统核心层。
系统遵循"文件系统即数据库（FS-as-DB）"哲学，以纯文本文件夹作为唯一数据存储，通过自然语言 CLI 驱动 AI 能力单元（Skills）完成内容创作、检索与发布。

Phase 1 交付四个核心能力：
1. CLI 基础框架（自然语言解析与意图路由）
2. 文件系统抽象（L0/L1/L2 三层上下文自动生成与维护）
3. 基础 Skills（publish、analyze、search）
4. Git 集成（版本控制与历史追踪）

---

## 词汇表

- **Ink**：本系统的命名，代表 Intent + Note + Knowledge，也是 CLI 入口命令
- **FS-as-DB**：文件系统即数据库，路径即关系，无需外部数据库
- **L0（摘要层）**：`.abstract` 文件，一句话总结，用于快速检索，AI 自动生成
- **L1（概览层）**：`.overview` 文件，结构化概览，包含核心信息、适用场景、关联文章
- **L2（详情层）**：`index.md` 文件，完整原始内容，按需加载
- **Skill**：可复用的 AI 能力单元，以 Markdown 文件定义，自文档化
- **Article**：一篇文章，对应一个文件夹，路径格式为 `YYYY/MM/DD-slug/`
- **CLI**：命令行接口，`ink` 命令的入口
- **Intent**：用户通过自然语言表达的操作意图
- **Global_Index**：`_index/` 目录下的全局索引，自动维护
- **Session**：`.ink/sessions/` 下的会话记忆文件，记录操作历史
- **Git_Repo**：Ink 工作目录对应的 Git 仓库

---

## 需求

### 需求 1：CLI 基础框架

**用户故事：** 作为内容创作者，我希望通过自然语言向 `ink` 命令表达意图，从而无需记忆复杂的命令语法即可完成操作。

#### 验收标准

1. THE CLI SHALL 接受 `ink "<自然语言意图>"` 格式的命令输入
2. WHEN 用户输入自然语言意图时，THE CLI SHALL 将意图解析为结构化操作（动作 + 目标 + 参数）
3. WHEN 解析结果匹配已注册的 Skill 时，THE CLI SHALL 调用对应 Skill 执行
4. WHEN 解析结果不匹配任何 Skill 时，THE CLI SHALL 返回可用 Skill 列表及使用示例
5. THE CLI SHALL 支持显式命令格式 `ink <skill-name> [目标路径] [--参数]`，作为自然语言解析的补充
6. WHEN 命令执行成功时，THE CLI SHALL 在终端输出结构化执行摘要（操作名称、目标、耗时）
7. IF 命令执行过程中发生错误，THEN THE CLI SHALL 输出错误类型、错误位置及建议修复步骤
8. THE CLI SHALL 在 `~/.ink/` 目录下维护全局配置文件 `config.yaml`

---

### 需求 2：文件系统抽象与三层上下文

**用户故事：** 作为内容创作者，我希望系统自动为每篇文章生成和维护 L0/L1/L2 三层上下文文件，从而在 AI 检索时降低 Token 消耗并提升精度。

#### 验收标准

1. THE File_System SHALL 以 `YYYY/MM/DD-slug/` 路径格式组织 Article 文件夹
2. WHEN 新 Article 文件夹被创建时，THE File_System SHALL 自动初始化 `.abstract`、`.overview`、`index.md` 三个文件
3. WHEN `index.md` 内容发生变更时，THE File_System SHALL 自动更新对应的 `.abstract`（L0）内容
4. WHEN `index.md` 内容发生变更时，THE File_System SHALL 自动更新对应的 `.overview`（L1）内容
5. THE L0_Generator SHALL 将 `.abstract` 内容限制在单行、不超过 200 个字符
6. THE L1_Generator SHALL 在 `.overview` 中包含：标题、标签、核心摘要（3-5 句）、关联文章路径列表
7. THE File_System SHALL 在 `_index/` 目录下维护全局时间线索引文件 `timeline.json`
8. WHEN Article 被创建或更新时，THE File_System SHALL 同步更新 `_index/timeline.json`
9. IF `.abstract` 或 `.overview` 文件被手动删除，THEN THE File_System SHALL 在下次 `ink` 命令执行时重新生成这两个文件
10. THE File_System SHALL 支持对 `.abstract` 和 `.overview` 文件执行解析，再格式化输出，再解析，结果与原始解析结果等价（往返属性）

---

### 需求 3：Publish Skill

**用户故事：** 作为内容创作者，我希望通过 `ink publish` 命令将文章发布到指定渠道，从而无需手动处理多平台格式转换。

#### 验收标准

1. WHEN 用户执行 `ink publish <article-path> --channels <channel-list>` 时，THE Publish_Skill SHALL 读取目标 Article 的 `index.md` 及 frontmatter
2. WHEN Article 的 frontmatter `status` 字段不为 `ready` 时，THE Publish_Skill SHALL 拒绝发布并返回当前 status 值及修改建议
3. THE Publish_Skill SHALL 支持 `blog`、`newsletter`、`mastodon` 三个发布渠道
4. WHEN 指定多个渠道时，THE Publish_Skill SHALL 并行生成各渠道对应的格式化内容
5. WHEN 发布成功时，THE Publish_Skill SHALL 将 Article frontmatter 中的 `status` 更新为 `published`，并记录发布时间戳
6. WHEN 发布成功时，THE Publish_Skill SHALL 在 `.ink/sessions/` 下创建本次操作的 Session 记录文件
7. IF 目标渠道不在支持列表中，THEN THE Publish_Skill SHALL 返回支持的渠道列表
8. IF 发布过程中网络请求失败，THEN THE Publish_Skill SHALL 保存草稿到本地并返回失败原因，不修改 Article 的 `status` 字段

---

### 需求 4：Analyze Skill

**用户故事：** 作为内容创作者，我希望通过 `ink analyze` 命令获取文章或整个知识库的结构化分析报告，从而了解内容质量和知识关联。

#### 验收标准

1. WHEN 用户执行 `ink analyze <article-path>` 时，THE Analyze_Skill SHALL 输出该 Article 的字数、阅读时长、标签、关联文章数量
2. WHEN 用户执行 `ink analyze --all` 时，THE Analyze_Skill SHALL 扫描所有 Article 并输出知识库统计摘要
3. THE Analyze_Skill SHALL 识别 `index.md` 中的 Wiki 链接（`[[文章名]]` 格式）并建立文章间关联图
4. WHEN 分析完成时，THE Analyze_Skill SHALL 将关联图数据写入 `_index/graph.json`
5. IF 目标路径不存在，THEN THE Analyze_Skill SHALL 返回路径不存在的错误信息及当前可用 Article 列表

---

### 需求 5：Search Skill

**用户故事：** 作为内容创作者，我希望通过自然语言搜索找到相关笔记，从而快速定位历史内容。

#### 验收标准

1. WHEN 用户执行 `ink search "<查询词>"` 时，THE Search_Skill SHALL 在所有 Article 的 L0（`.abstract`）层执行关键词匹配
2. WHEN L0 层匹配结果不足 3 条时，THE Search_Skill SHALL 自动扩展到 L1（`.overview`）层继续搜索
3. THE Search_Skill SHALL 按相关度排序返回搜索结果，每条结果包含：Article 路径、L0 摘要、匹配片段
4. WHEN 搜索结果为空时，THE Search_Skill SHALL 返回搜索词及建议的相近关键词
5. THE Search_Skill SHALL 支持标签过滤，格式为 `ink search "<查询词>" --tag <标签名>`
6. WHERE 全文搜索功能启用时，THE Search_Skill SHALL 支持在 L2（`index.md`）层执行全文检索

---

### 需求 6：Git 集成

**用户故事：** 作为内容创作者，我希望 Ink 自动管理 Git 版本控制，从而无需手动执行 git 命令即可保留完整的修改历史。

#### 验收标准

1. WHEN 用户在非 Git 仓库目录执行 `ink init` 时，THE Git_Integration SHALL 初始化 Git 仓库并创建初始提交
2. WHEN Article 被创建时，THE Git_Integration SHALL 自动执行 `git add` 并提交，提交信息格式为 `feat: add <article-slug>`
3. WHEN Article 的 `index.md` 被更新时，THE Git_Integration SHALL 自动执行提交，提交信息格式为 `update: <article-slug> - <变更摘要>`
4. WHEN Publish_Skill 执行成功时，THE Git_Integration SHALL 自动提交发布状态变更，提交信息格式为 `publish: <article-slug> to <channels>`
5. THE Git_Integration SHALL 在 `.gitignore` 中自动排除 `.ink/sessions/` 目录（会话记忆不纳入版本控制）
6. IF 当前目录不是 Git 仓库且用户未执行 `ink init`，THEN THE Git_Integration SHALL 在首次写操作前提示用户执行 `ink init`

---

### 需求 7：Skills 体系基础

**用户故事：** 作为开发者，我希望 Skills 以 Markdown 文件定义，从而实现自文档化、可版本控制、可扩展的能力单元体系。

#### 验收标准

1. THE Skill_Loader SHALL 从 `.ink/skills/` 目录加载所有 `.md` 格式的 Skill 定义文件
2. WHEN Skill 文件的 frontmatter 包含 `skill`、`version`、`context_requirement` 字段时，THE Skill_Loader SHALL 将其注册为可用 Skill
3. THE Skill_Loader SHALL 解析 Skill 文件中的"输入"和"执行流程"章节，提取参数定义和执行步骤
4. WHEN 解析 Skill 文件后再格式化输出再解析时，THE Skill_Loader SHALL 产生与原始解析等价的结果（往返属性）
5. IF Skill 文件 frontmatter 缺少必填字段，THEN THE Skill_Loader SHALL 跳过该文件并输出警告信息，包含文件路径和缺失字段名
6. THE Skill_Loader SHALL 支持 `ink skills list` 命令，列出所有已注册 Skill 的名称、版本和描述
