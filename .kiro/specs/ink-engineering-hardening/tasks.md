# Implementation Plan: 补工程硬伤（ink-engineering-hardening）

## Overview

对 Ink Blog Core 的六项工程硬伤进行修复，拆分为两个版本：

- **v0.4.0**（必做）：中文 slug、Markdown 渲染 + XSS、Jinja2 autoescape、Skill 执行引擎 — 底层硬伤，影响每次创建/渲染/执行
- **v0.4.1**（后做）：发布状态机完整扩展（drafted/syndicate）、CLI 命令/Skill 边界 — 语义与产品层清晰化

按基础设施层 → 领域层 → 能力层的顺序增量实现，确保每步可测试。

## Tasks

### v0.4.0 — 底层硬伤修复

- [-] 1. 新增依赖与基础设施准备
  - [x] 1.1 更新 `pyproject.toml` 添加可选依赖
    - 在 `[project.optional-dependencies]` 中添加 `pinyin = ["pypinyin>=0.50"]`、`markdown = ["mistune>=3.0"]`
    - 添加 `all = ["pypinyin>=0.50", "mistune>=3.0"]`
    - 更新 `dev` 依赖组包含 `pypinyin>=0.50`、`mistune>=3.0`
    - _Requirements: 3.1, NFR 6.2_

  - [-] 1.2 创建 `ink_core/core/status.py` — ArticleStatus 枚举
    - 实现 `ArticleStatus(str, Enum)` 枚举，包含六个值：`draft`、`review`、`ready`、`drafted`、`published`、`archived`
    - 实现 `is_valid()`、`valid_transitions()`、`is_publishable()`、`is_syndicatable()`、`is_visible_in_search()`
    - 注意：v0.4.0 只引入枚举和修复 PublishSkill 的 draft_saved bug，不实现 syndicate 命令
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [ ]* 1.3 写属性测试：状态枚举完整性（`tests/test_engineering_properties.py`）
    - **Property 5: 状态枚举完整性**
    - **Validates: Requirement 2.2**

  - [ ]* 1.4 写属性测试：状态迁移闭包（`tests/test_engineering_properties.py`）
    - **Property 6: 状态迁移闭包**
    - **Validates: Requirement 2.4**

  - [ ]* 1.5 写单元测试：ArticleStatus（`tests/test_article_status.py`）
    - 测试所有六个枚举值的各方法返回值、迁移表完整性
    - _Requirements: 2.1–2.7_

- [ ] 2. 硬伤 1：中文 slug 分类 Fallback
  - [ ] 2.1 重构 `SlugResolver`（`ink_core/fs/article.py`）
    - 重写 `generate_slug(title)` 实现分类 Fallback：纯英文 → ASCII；含 CJK + pypinyin → 组合拼音；含 CJK 无 pypinyin + ASCII ≥ 3 → ASCII+hash4；兜底 → post-hash8
    - 新增 `_extract_ascii`、`_has_cjk`、`_to_pinyin`、`_hash_slug`、`_short_hash`、`_check_pinyin`
    - 关键：中英混合标题优先组合 ASCII + 拼音，避免语义退化和碰撞
    - _Requirements: 1.1–1.9_

  - [ ]* 2.2 写属性测试：Slug 非空性 — **Property 1** — _Validates: 1.5, 1.6_
  - [ ]* 2.3 写属性测试：Slug 中文标题可用性 — **Property 2** — _Validates: 1.8_
  - [ ]* 2.4 写属性测试：Slug 确定性 — **Property 3** — _Validates: 1.7_
  - [ ]* 2.5 写属性测试：Slug 中英混合组合 — **Property 4** — _Validates: 1.1_
  - [ ]* 2.6 写单元测试：SlugResolver（`tests/test_slug_resolver.py`）
    - 纯英文、纯中文、中英混合（`Python 深度学习` vs `Python 机器学习` 必须不同）、emoji、超长标题、pypinyin 不可用降级
    - _Requirements: 1.1–1.4, 1.8, 1.9_

- [ ] 3. Checkpoint — 基础设施与领域层验证

- [ ] 4. 硬伤 3：Markdown 渲染器替换
  - [ ] 4.1 创建 `ink_core/fs/markdown_renderer.py` — 完全自包含
    - 实现 `render_markdown(md, *, safe=True)`、`_mistune_available()`、`_render_with_mistune()`
    - 从 `site/renderer.py` 迁移 `_md_to_html()` 和 `_inline()` 到此模块，重命名为 `_md_to_html_builtin()` 和 `_inline_safe()`
    - 关键约束：不得 import `ink_core/site/renderer.py`，避免循环依赖
    - _Requirements: 3.1, 3.2, 3.4_

  - [ ] 4.2 修复 `_inline_safe()` 的 HTML 转义缺陷
    - 默认对 `<`、`>`、`&` 转义
    - 代码块中的原始 HTML 作为字面文本展示（被转义后输出），不作为可执行 HTML 渲染
    - _Requirements: 3.5, 3.6_

  - [ ] 4.3 更新 `ink_core/site/renderer.py` 使用新渲染器
    - 替换 `_md_to_html(body)` 为 `render_markdown(body)` — 默认 `safe=True`，原始 HTML 被转义
    - 原始 `_md_to_html()` 可保留标记 deprecated
    - _Requirements: 3.1, 3.2_

  - [ ]* 4.4 写属性测试：渲染安全性 — **Property 8** — _Validates: 3.2, 3.5_
  - [ ]* 4.5 写属性测试：渲染幂等性 — **Property 9** — _Validates: 3.3_
  - [ ]* 4.6 写单元测试：render_markdown（`tests/test_markdown_renderer.py`）
    - mistune 可用/不可用、XSS payload、代码块保留、验证无循环依赖
    - _Requirements: 3.1, 3.2, 3.5, 3.6_

- [ ] 5. 硬伤 6：Jinja2 autoescape 默认开启
  - [ ] 5.1 修改 `ink_core/site/renderer.py` — autoescape 修复
    - `_render()` 默认 `autoescape=True`
    - 使用 `from markupsafe import Markup`（非 `jinja2.Markup`）标记 body_html
    - 删除 `_get_fs_env()` 缓存，每次创建新 env
    - _Requirements: 6.1–6.5_

  - [ ]* 5.2 写属性测试：变量转义 — **Property 13** — _Validates: 6.2_
  - [ ]* 5.3 写属性测试：body_html 不二次转义 — **Property 14** — _Validates: 6.3, 6.4_
  - [ ]* 5.4 写单元测试：autoescape（`tests/test_template_autoescape.py`） — _Requirements: 6.1–6.5_

- [ ] 6. Checkpoint — 渲染层安全修复验证

- [ ] 7. 硬伤 4：最小 Skill 执行引擎
  - [ ] 7.1 创建 `ink_core/skills/executor.py` — SkillExecutor（严格 DSL）
    - `StepContext` dataclass、`SkillExecutor` 类
    - 仅支持 `read_content <L0|L1|L2>` 和 `write_file <path>` 两种 DSL 命令
    - 写入路径限制在 `.ink/skill-output/`，必须 `resolve()` 后校验仍在目标目录下，拒绝绝对路径和 `../` 穿越
    - 不做自然语言步骤解释器
    - _Requirements: 4.1–4.8, 4.10, 4.11, 4.12_

  - [ ] 7.2 更新 `ink_core/skills/registry.py` — FileDefinedSkill 接入
    - `FileDefinedSkill.__init__(definition, workspace_root)`
    - `SkillRegistry.__init__` 新增 `workspace_root` 参数并持有
    - `SkillRegistry.load_from_directory(path)` 使用 `self._workspace_root` 传给 `FileDefinedSkill`
    - `create_with_builtins(workspace_root)` 工厂方法同步调整
    - 确保参数链闭合：`InkCLI` → `SkillRegistry(workspace_root)` → `FileDefinedSkill(def, workspace_root)` → `SkillExecutor(workspace_root)`
    - _Requirements: 4.9_

  - [ ]* 7.3 写属性测试：步骤完整性 — **Property 10** — _Validates: 4.2_
  - [ ]* 7.4 写属性测试：失败隔离 — **Property 11** — _Validates: 4.3_
  - [ ]* 7.5 写属性测试：不支持步骤跳过 — **Property 12** — _Validates: 4.4_
  - [ ]* 7.6 写单元测试：SkillExecutor（`tests/test_skill_executor.py`）
    - read_content + write_file 基本流程、不支持步骤跳过、目标不存在、write_file 无路径
    - 路径穿越测试：`../../etc/passwd` 和绝对路径 `/tmp/foo` 必须被拒绝
    - _Requirements: 4.1, 4.4–4.8, 4.11, 4.12_

- [ ] 8. 硬伤 2（v0.4.0 部分）：PublishSkill 语义修复
  - [ ] 8.1 更新 `ink_core/skills/publish.py` 使用 ArticleStatus
    - 替换硬编码状态字符串为枚举
    - 修复 bug：仅 `success` 渠道触发状态推进，`draft_saved` 不推进
    - _Requirements: 2.5, 2.8, 2.9_

  - [ ]* 8.2 写属性测试：发布门控 — **Property 7** — _Validates: 2.5, 2.9_

- [ ] 9. Checkpoint — v0.4.0 全部硬伤修复验证

- [ ] 10. 集成测试
  - [ ] 10.1 中文标题文章创建端到端（`tests/test_engineering_integration.py`）
    - 中英混合标题生成不同 slug — _Requirements: 1.1, 1.2, 1.8_
  - [ ] 10.2 XSS payload 文章构建安全 — _Requirements: 3.2, 6.2, 6.3_
  - [ ] 10.3 自定义 Skill 执行链路 — _Requirements: 4.1, 4.9_
  - [ ] 10.4 PublishSkill draft_saved 不推进状态 — _Requirements: 2.8_

- [ ] 11. Final checkpoint — v0.4.0 全量测试通过

### v0.4.1 — 语义与产品层清晰化（后续版本）

- [ ] 12. 硬伤 2 完整扩展：发布状态机
  - [ ] 12.1 `ink publish` 改为设置 `drafted`，新增 `ink syndicate` 和 `ink publish --push`
  - [ ] 12.2 `ink build --include-drafted` 预览模式
  - [ ] 12.3 `ink doctor --migrate-status` 迁移工具

- [ ] 13. 硬伤 5：CLI 帮助文本分组
  - [ ] 13.1 帮助文本 `[核心]`/`[技能]`/`[Agent]` 前缀 — _Requirements: 5.1–5.4, 5.6_
  - [ ] 13.2 `ink skills list` 区分内置/自定义技能 — _Requirements: 5.5_
  - [ ]* 13.3 写单元测试 — _Requirements: 5.1–5.3, 5.5_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- v0.4.0 聚焦底层硬伤，v0.4.1 做语义清晰化
- Markdown 渲染器完全自包含，不回头 import site/renderer.py
- SkillExecutor 是严格 DSL 解释器，不是 Agent Runtime
- Markup 从 markupsafe 导入，不从 jinja2 导入
- 中英混合 slug 优先组合 ASCII + 拼音，不再"ASCII ≥ 3 就直接返回"
