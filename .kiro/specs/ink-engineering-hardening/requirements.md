# 需求文档：补工程硬伤（ink-engineering-hardening）

## 1. 文档信息

- 项目名称：Ink Blog Core — 工程硬伤修复
- 阶段：v0.4.0 / v0.4.1
- 文档类型：Requirement Specification
- 版本：v2.0
- 状态：定稿

---

## 2. 简介

本需求文档覆盖 Ink Blog Core v0.4.0 / v0.4.1 的六项工程硬伤修复。

**v0.4.0 必做**（底层硬伤）：
1. 中文 slug 分类 Fallback（纯英文 → ASCII；含 CJK → 组合拼音；兜底 → 哈希）
2. Markdown 渲染器替换（mistune 可选依赖 + 内置 fallback 安全修复）
3. Jinja2 autoescape 默认开启（`body_html` 用 `markupsafe.Markup` 标记）
4. 最小 SkillExecutor（严格 DSL：`read_content` + `write_file`）
5. PublishSkill 修 bug：`draft_saved` 不再推进到 `published`

**v0.4.1 再做**（语义与产品层清晰化）：
6. 发布状态机完整扩展（`drafted` 落地使用、`syndicate`、`publish --push`、迁移脚本）
7. CLI 命令/Skill 边界清晰化（帮助文本标注）

---

## 3. 范围

### 3.1 In Scope — v0.4.0

1. `SlugResolver` 重构：分类 Fallback slug 生成策略（中英混合优先组合）
2. `ArticleStatus` 枚举引入 + PublishSkill `draft_saved` bug 修复
3. Markdown 渲染器替换：引入 `mistune` 可选依赖，内置渲染器完全自包含（不循环依赖）
4. `SkillExecutor` 新增：严格 DSL 执行引擎（`read_content` + `write_file`）
5. Jinja2 autoescape 修复：默认开启，`body_html` 使用 `markupsafe.Markup`

### 3.1b In Scope — v0.4.1

6. 发布状态机完整扩展：`drafted` 落地、`ink syndicate`、`ink publish --push`、`ink doctor --migrate-status`
7. CLI 帮助文本标注：`[核心]`/`[技能]`/`[Agent]` 前缀区分
8. `ink build --include-drafted` 预览模式

### 3.2 Out of Scope

v0.4.0 / v0.4.1 SHALL NOT 包含以下能力：

1. Skill 执行引擎的高级步骤类型（如 `transform`、`call_api`）
2. Skill 沙箱安全策略增强（如路径白名单配置化）
3. Markdown 渲染器的自定义插件系统
4. CLI 帮助文本的国际化（i18n）
5. 新的内容对象类型（Conversation 等）
6. 多节点机制、Hub、Conversation 管理
7. `site.allow_raw_html` 配置项（v0.4.0 默认 safe=True，不提供放开选项）

---

## 4. 词汇表

- **SlugResolver**：slug 生成器，负责将文章标题转换为 URL 友好的路径片段
- **CJK**：中日韩统一表意文字（Unicode 范围 U+4E00–U+9FFF、U+3400–U+4DBF）
- **Fallback**：降级策略，当首选方案不可用时自动切换到备选方案
- **ArticleStatus**：文章生命周期状态枚举，定义合法状态值与迁移规则
- **SkillExecutor**：Skill 执行引擎，解释执行 SkillDefinition 中的步骤序列
- **SkillDefinition**：从 `.ink/skills/*.md` 文件解析出的 Skill 定义结构
- **StepContext**：步骤执行上下文，在步骤间传递数据
- **TemplateRenderer**：Jinja2 模板渲染器，负责将模板与数据合并生成 HTML
- **Markup**：Jinja2 提供的安全字符串标记，标记后的字符串不会被 autoescape 转义
- **autoescape**：Jinja2 的自动 HTML 转义机制，防止 XSS 注入
- **mistune**：轻量级 Python Markdown 解析库，零外部依赖
- **pypinyin**：Python 中文拼音转换库，将汉字转换为拼音

---

## 5. 需求

### 需求 1：中文 slug 分类 Fallback

**用户故事：** 作为中文内容创作者，我希望系统能为中文标题生成有意义的 slug，从而避免所有中文文章都退化为 `untitled` 导致路径冲突。

#### 验收标准

1. WHEN 标题为纯英文（不含 CJK 字符）时，THE SlugResolver SHALL 使用 ASCII 部分生成 slug
2. WHEN 标题包含 CJK 字符且 pypinyin 可用时，THE SlugResolver SHALL 使用组合策略生成 slug（ASCII 部分 + 拼音部分），确保中英混合标题保留完整语义（如 `"Python 深度学习"` → `python-shen-du-xue-xi`）
3. WHEN 标题包含 CJK 字符且 pypinyin 不可用，且 ASCII 部分 ≥ 3 个字符时，THE SlugResolver SHALL 使用 ASCII + SHA256 hash 前 4 位组合生成 slug（如 `python-a1b2`）
4. WHEN 标题包含 CJK 字符且 pypinyin 不可用，且 ASCII 部分不足 3 个字符时，THE SlugResolver SHALL 使用 SHA256 哈希前 8 位生成 slug，格式为 `post-<hash8>`
5. THE SlugResolver SHALL 对任意非空标题返回非空 slug，且 slug 仅包含 `[a-z0-9-]` 字符
6. THE SlugResolver SHALL 将 slug 长度限制在 60 个字符以内；WHEN 截断时，THE SlugResolver SHALL 尽量在连字符处断开
7. THE SlugResolver SHALL 对同一标题的多次调用返回相同结果（确定性）
8. THE SlugResolver SHALL 对包含至少一个 CJK 字符的标题返回非 `untitled` 的 slug
9. IF pypinyin 未安装，THEN THE SlugResolver SHALL 在日志中输出警告并自动降级到哈希方案，不中断执行

### 需求 2：发布状态机扩展

**用户故事：** 作为系统开发者，我希望状态机能区分"本地格式化文件已生成"和"已真实发布到远程平台"，从而为 Phase 2 的远程发布功能提供清晰的语义基础。

#### 验收标准

1. THE ArticleStatus SHALL 支持以下六个枚举值：`draft`、`review`、`ready`、`drafted`、`published`、`archived`
2. THE ArticleStatus SHALL 提供 `is_valid()` 方法，WHEN 传入合法枚举值时返回 `True`，WHEN 传入非法字符串时返回 `False`
3. THE ArticleStatus SHALL 提供 `valid_transitions()` 方法，返回每个状态的合法迁移目标列表
4. WHEN 状态迁移目标列表中包含某状态值时，THE ArticleStatus SHALL 保证该目标值本身也是合法状态值（迁移闭包）
5. THE ArticleStatus SHALL 提供 `is_publishable()` 方法，仅当状态为 `ready` 时返回 `True`
6. THE ArticleStatus SHALL 提供 `is_syndicatable()` 方法，仅当状态为 `drafted` 时返回 `True`
7. THE ArticleStatus SHALL 提供 `is_visible_in_search()` 方法，仅当状态为 `archived` 时返回 `False`
8. WHEN Phase 1 中执行 `ink publish` 时，THE PublishSkill SHALL 保持现有行为，将状态设为 `published`；但 SHALL 修复当前 bug：仅当至少一个渠道真正 `success` 时才更新状态，`draft_saved` 不应触发状态推进
9. IF Article 的 status 不为 `ready`，THEN THE PublishSkill SHALL 拒绝发布并返回当前状态值与合法迁移建议
10. THE SiteBuilder SHALL 在 v0.4.0 中保持默认仅构建 `status=published` 的文章（不变）；`drafted` 状态的文章默认不公开构建

### 需求 3：Markdown 渲染器替换

**用户故事：** 作为内容创作者，我希望 Markdown 渲染输出安全且功能完整，从而避免 XSS 风险并支持常见 Markdown 扩展语法。

#### 验收标准

1. THE render_markdown 函数 SHALL 优先使用 mistune 渲染 Markdown；IF mistune 不可用，THEN SHALL 回退到内置渲染器。内置渲染器 SHALL 完全自包含在 `ink_core/fs/markdown_renderer.py` 中，不得 import `ink_core/site/renderer.py` 中的任何函数
2. THE render_markdown 函数 SHALL 默认以 `safe=True` 模式运行，对 Markdown 中的原始 HTML 标签进行转义，确保输出中不包含未转义的 `<script` 或 `onerror=` 字符串
3. THE render_markdown 函数 SHALL 对同一 Markdown 输入的多次调用返回完全相同的结果（幂等性）
4. IF mistune 未安装，THEN THE System SHALL 在日志中输出警告并使用内置渲染器，不中断执行
5. THE 内置 fallback 渲染器 SHALL 修复 `_inline()` 函数中的 HTML 转义缺陷，默认对 `<`、`>`、`&` 字符进行转义
6. WHEN 渲染器处理代码块内容时，代码块中的原始 HTML SHALL 作为字面文本展示（被转义后输出），不作为可执行 HTML 渲染
7. v0.4.0 SHALL NOT 提供 `site.allow_raw_html` 配置项；如需允许可信作者原始 HTML，SHALL 在后续版本通过显式配置开放


### 需求 4：最小 Skill 执行引擎

**用户故事：** 作为 Skill 开发者，我希望在 `.ink/skills/*.md` 中定义的技能能够真正执行，从而让 Skill 系统不再是空壳。

#### 验收标准

1. THE SkillExecutor SHALL 支持 `read_content` 和 `write_file` 两种步骤类型
2. WHEN 执行包含 N 个受支持步骤的 SkillDefinition 时，THE SkillExecutor SHALL 在成功时返回长度为 N 的 outputs 列表
3. WHEN 执行过程中某步骤失败时，THE SkillExecutor SHALL 返回 `success=False`，并在 `changed_files` 中完整记录失败前已执行步骤产生的文件变更
4. WHEN SkillDefinition 包含不支持的步骤类型时，THE SkillExecutor SHALL 跳过该步骤并在 outputs 中记录跳过信息，不抛出异常
5. WHEN 执行 `read_content` 步骤时，THE SkillExecutor SHALL 根据参数读取目标文章的指定层级（L0/L1/L2）内容到上下文
6. WHEN 执行 `write_file` 步骤时，THE SkillExecutor SHALL 将当前上下文内容写入 `.ink/skill-output/` 目录下的指定路径
7. IF `write_file` 步骤未提供文件路径参数，THEN THE SkillExecutor SHALL 返回错误信息
8. IF `read_content` 步骤的目标文章不存在，THEN THE SkillExecutor SHALL 返回错误信息
9. THE FileDefinedSkill SHALL 通过 SkillExecutor 执行步骤，替代当前的"暂未实现"空壳逻辑
10. THE SkillExecutor SHALL 支持中文关键词映射（`读取` → `read_content`，`写入` → `write_file`）
11. WHEN `write_file` 的目标路径经 `resolve()` 规范化后不位于 `.ink/skill-output/` 目录下时（如包含 `../` 路径穿越），THE SkillExecutor SHALL 拒绝执行并返回错误，不写入任何文件
12. THE SkillExecutor SHALL 拒绝绝对路径作为 `write_file` 参数

### 需求 5：CLI 帮助文本标注（v0.4.1）

**用户故事：** 作为 CLI 用户，我希望从帮助文本中清晰区分核心命令和技能命令，从而理解系统的命令组织结构。

#### 验收标准

1. THE CLI 帮助文本 SHALL 清晰区分核心命令、技能命令和 Agent 命令（通过 help 字符串前缀标注，非 argparse 原生分组）
2. WHEN 显示核心命令时，THE CLI SHALL 在帮助文本中使用 `[核心]` 前缀标注
3. WHEN 显示技能命令时，THE CLI SHALL 在帮助文本中使用 `[技能]` 前缀标注
4. WHERE Agent 模式命令存在时，THE CLI SHALL 在帮助文本中使用 `[Agent]` 前缀标注
5. WHEN 执行 `ink skills list` 时，THE System SHALL 同时显示内置技能和自定义技能，并标注来源
6. THE CLI 帮助标注 SHALL 不改变底层路由机制（IntentRouter 的查找顺序不变）

### 需求 6：Jinja2 autoescape 默认开启

**用户故事：** 作为内容创作者，我希望模板渲染默认启用安全转义，从而防止文章标题或标签中的特殊字符导致 XSS 注入。

#### 验收标准

1. THE TemplateRenderer SHALL 在所有渲染路径中默认启用 `autoescape=True`
2. WHEN 文章标题包含 HTML 特殊字符（`<`、`>`、`&`、`"`、`'`）时，THE TemplateRenderer SHALL 在渲染输出中对这些字符进行 HTML 转义
3. THE TemplateRenderer SHALL 使用 `markupsafe.Markup`（而非 `jinja2.Markup`）标记 `body_html` 变量，确保已渲染的 HTML 内容不被二次转义
4. WHEN 渲染文章页面时，THE TemplateRenderer SHALL 保证 `body_html` 区域内的 HTML 标签（如 `<h1>`、`<p>`、`<code>`）保持原样输出
5. WHEN 用户自定义模板需要输出原始 HTML 时，THE TemplateRenderer SHALL 支持 Jinja2 的 `|safe` 过滤器

---

## 6. 非功能需求

### 6.1 向后兼容

1. THE System SHALL 保证已有文章的 slug 不受 SlugResolver 重构影响（已有文章不重新生成 slug）
2. THE System SHALL 在所有读取 status 的位置同时识别 `drafted` 和 `published` 状态
3. THE System SHALL 保证 Phase 1 中 `ink publish` 的行为不变（status → `published`）

### 6.2 可选依赖优雅降级

1. IF pypinyin 未安装，THEN THE System SHALL 自动降级到哈希方案，核心路径不受影响
2. IF mistune 未安装，THEN THE System SHALL 自动使用内置渲染器，核心路径不受影响
3. THE System SHALL 在可选依赖不可用时输出日志警告，不抛出异常

### 6.3 安全性

1. THE System SHALL 通过 Jinja2 autoescape 和 Markdown 渲染器 HTML 转义提供双重 XSS 防护
2. THE SkillExecutor SHALL 将写入路径限制在 `.ink/skill-output/` 目录下；WHEN 路径经 `resolve()` 规范化后越出该目录时（路径穿越），SHALL 拒绝执行
3. THE render_markdown 函数 SHALL 默认 `safe=True`，不在 v0.4.0 提供放开原始 HTML 的配置

### 6.4 可测试性

1. 所有六项硬伤修复 SHALL 提供对应的属性测试（Property-Based Tests），每个属性测试最少 100 次迭代
2. 所有属性测试 SHALL 使用 `hypothesis` 库实现

---

## 7. 风险与开放问题

1. `pypinyin` 的拼音转换对多音字的处理可能不完美，但对于 slug 生成场景可接受
2. `mistune` 的 HTML 转义策略可能与内置渲染器存在细微差异，需要通过属性测试验证一致性
3. `SkillExecutor` 仅支持两种步骤类型，复杂 Skill 可能需要在后续版本扩展
4. `drafted` 状态在 Phase 1 中不会被实际使用（`ink publish` 仍设为 `published`），但需要在代码中预留支持
5. CLI 帮助分组依赖 argparse 的子命令机制，分组标注通过 help 字符串前缀实现，非原生分组功能
