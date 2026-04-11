# Implementation Plan: 补工程硬伤（ink-engineering-hardening）

> v1.1 定稿 — 2026-04-12

## Overview

对 Ink Blog Core 的六项工程硬伤进行修复，拆分为两个版本：

- **v0.4.0**（必做）：中文 slug、Markdown 渲染 + XSS、Jinja2 autoescape、Skill 执行引擎、PublishSkill bug fix
- **v0.4.1**（后做）：发布状态机完整扩展（drafted/syndicate）、CLI 标注、README 同步

按基础设施层 → 领域层 → 能力层的顺序增量实现。

## 优先级说明

- **P0**：必须在本版本完成，不可跳过
- **P1**：强烈建议本版本完成，跳过需记录原因
- **P2**：可后移到下一版本

所有属性测试均为 P0（requirements 中 SHALL 约束），不标记为 optional。

## Tasks

### v0.4.0 — 底层硬伤修复

- [x] 1. 新增依赖与基础设施准备
  - [x] 1.1 [P0] 更新 `pyproject.toml` 添加可选依赖
    - 在 `[project.optional-dependencies]` 中添加 `pinyin = ["pypinyin>=0.50"]`、`markdown = ["mistune>=3.0"]`
    - 添加 `all = ["pypinyin>=0.50", "mistune>=3.0"]`
    - 更新 `dev` 依赖组包含 `pypinyin>=0.50`、`mistune>=3.0`
    - _Requirements: 3.1, NFR 6.2_

  - [x] 1.2 [P0] 创建 `ink_core/core/status.py` — ArticleStatus 枚举
    - 实现 `ArticleStatus(str, Enum)` 枚举，包含六个值：`draft`、`review`、`ready`、`drafted`、`published`、`archived`
    - 实现 `is_valid()`、`valid_transitions()`、`is_publishable()`、`is_syndicatable()`、`is_visible_in_search()`
    - 注意：v0.4.0 只引入枚举和修复 PublishSkill 的 draft_saved bug，不实现 syndicate 命令
    - _Requirements: 2.1–2.7_

  - [x] 1.3 [P0] 写属性测试：状态枚举完整性（`tests/test_engineering_properties.py`）
    - **Property 5: 状态枚举完整性**
    - **Validates: Requirement 2.2**

  - [x] 1.4 [P0] 写属性测试：状态迁移闭包（`tests/test_engineering_properties.py`）
    - **Property 6: 状态迁移闭包**
    - **Validates: Requirement 2.4**

  - [x] 1.5 [P1] 写单元测试：ArticleStatus（`tests/test_article_status.py`）
    - 测试所有六个枚举值的各方法返回值、迁移表完整性
    - _Requirements: 2.1–2.7_

- [x] 2. 硬伤 1：中文 slug 分类 Fallback
  - [x] 2.1 [P0] 重构 `SlugResolver`（`ink_core/fs/article.py`）
    - 重写 `generate_slug(title)` 实现分类 Fallback：纯英文 → ASCII；含 CJK + pypinyin → 组合拼音；含 CJK 无 pypinyin + ASCII ≥ 3 → ASCII+hash4；兜底 → post-hash8
    - 新增 `_extract_ascii`、`_has_cjk`、`_to_pinyin`、`_hash_slug`、`_short_hash`、`_check_pinyin`
    - 关键：中英混合标题优先组合 ASCII + 拼音，避免语义退化和碰撞
    - _Requirements: 1.1–1.9_

  - [x] 2.2 [P0] 写属性测试：Slug 非空性 — **Property 1** — _Validates: 1.5, 1.6_
  - [x] 2.3 [P0] 写属性测试：Slug 中文标题可用性 — **Property 2** — _Validates: 1.8_
  - [x] 2.4 [P0] 写属性测试：Slug 确定性 — **Property 3** — _Validates: 1.7_
  - [x] 2.5 [P0] 写属性测试：Slug 中英混合组合 — **Property 4** — _Validates: 1.1_

  - [x] 2.6 [P1] 写单元测试：SlugResolver（`tests/test_slug_resolver.py`）
    - 纯英文、纯中文、中英混合（`Python 深度学习` vs `Python 机器学习` 必须不同）、emoji、超长标题、pypinyin 不可用降级
    - _Requirements: 1.1–1.4, 1.8, 1.9_

- [x] 3. Checkpoint — 基础设施与领域层验证

- [x] 4. 硬伤 3：Markdown 渲染器替换
  - [x] 4.1 [P0] 创建 `ink_core/fs/markdown_renderer.py` — 完全自包含
    - 实现 `render_markdown(md, *, safe=True)`、`_mistune_available()`、`_render_with_mistune()`
    - 从 `site/renderer.py` 迁移 `_md_to_html()` 和 `_inline()` 到此模块，重命名为 `_md_to_html_builtin()` 和 `_inline_safe()`
    - 关键约束：不得 import `ink_core/site/renderer.py`，避免循环依赖
    - _Requirements: 3.1, 3.2, 3.4_

  - [x] 4.2 [P0] 修复 `_inline_safe()` 的 HTML 转义缺陷
    - 默认对 `<`、`>`、`&` 转义
    - 代码块中的原始 HTML 作为字面文本展示（被转义后输出），不作为可执行 HTML 渲染
    - _Requirements: 3.5, 3.6_

  - [x] 4.3 [P0] 更新 `ink_core/site/renderer.py` 使用新渲染器（与 5.1 联动）
    - 替换 `_md_to_html(body)` 为 `render_markdown(body, safe=True)` — 原始 HTML 默认被转义
    - body_html 仅在 Markdown 已安全渲染后再用 `Markup()` 标记
    - 原始 HTML 默认不透传，v0.4.0 不提供 `allow_raw_html` 配置
    - 原始 `_md_to_html()` 可保留标记 deprecated，但 v0.4.0 主渲染路径不得再调用 `site/renderer.py` 中旧的 `_md_to_html()`
    - _Requirements: 3.1, 3.2, 3.6_

  - [x] 4.4 [P0] 写属性测试：渲染安全性 — **Property 8** — _Validates: 3.2, 3.5_
  - [x] 4.5 [P0] 写属性测试：渲染幂等性 — **Property 9** — _Validates: 3.3_

  - [x] 4.6 [P1] 写单元测试：render_markdown（`tests/test_markdown_renderer.py`）
    - mistune 可用/不可用、XSS payload、代码块中 `<script>` 必须被转义为字面文本、验证无循环依赖
    - _Requirements: 3.1, 3.2, 3.5, 3.6_

- [x] 5. 硬伤 6：Jinja2 autoescape 默认开启
  - [x] 5.1 [P0] 修改 `ink_core/site/renderer.py` — autoescape 修复（与 4.3 联动）
    - `_render()` 默认 `autoescape=True`
    - 使用 `from markupsafe import Markup`（非 `jinja2.Markup`）标记 body_html
    - 删除 `_get_fs_env()` 缓存，每次创建新 env
    - 确认 body_html 来源是 `render_markdown(body, safe=True)` 后再 `Markup()`，双重防护闭合
    - _Requirements: 6.1–6.5_

  - [x] 5.2 [P0] 写属性测试：变量转义 — **Property 13** — _Validates: 6.2_
  - [x] 5.3 [P0] 写属性测试：body_html 不二次转义 — **Property 14** — _Validates: 6.3, 6.4_

  - [x] 5.4 [P1] 写单元测试：autoescape（`tests/test_template_autoescape.py`） — _Requirements: 6.1–6.5_

- [x] 6. Checkpoint — 渲染层安全修复验证

- [x] 7. 硬伤 4：最小 Skill 执行引擎
  - [x] 7.1 [P0] 创建 `ink_core/skills/executor.py` — SkillExecutor（严格 DSL）
    - `StepContext` dataclass、`SkillExecutor` 类
    - 仅支持 `read_content <L0|L1|L2>` 和 `write_file <path>` 两种 DSL 命令
    - write_file 路径安全约束（显式执行项）：
      - 拒绝绝对路径
      - 拒绝空路径
      - 对目标路径执行 `resolve()`
      - 校验 resolve 后路径必须位于 `.ink/skill-output/` 下
      - `../` 穿越必须被拦截并返回错误
    - 不做自然语言步骤解释器
    - _Requirements: 4.1–4.8, 4.10, 4.11, 4.12_

  - [x] 7.2 [P0] 重构 `SkillRegistry` 持有 workspace_root（`ink_core/skills/registry.py`）
    - `SkillRegistry.__init__` 新增 `workspace_root: Path` 参数并持有
    - `create_with_builtins(workspace_root)` 工厂方法同步调整
    - _Requirements: 4.9_

  - [x] 7.3 [P0] 更新 `FileDefinedSkill` 构造与 `load_from_directory` 参数链
    - `FileDefinedSkill.__init__(definition, workspace_root)`
    - `SkillRegistry.load_from_directory(path)` 使用 `self._workspace_root` 传给 `FileDefinedSkill`
    - 确保参数链闭合：`InkCLI` → `SkillRegistry(workspace_root)` → `FileDefinedSkill(def, workspace_root)` → `SkillExecutor(workspace_root)`
    - _Requirements: 4.9_

  - [x] 7.4 [P0] 写属性测试：步骤完整性 — **Property 10** — _Validates: 4.2_
  - [x] 7.5 [P0] 写属性测试：失败隔离 — **Property 11** — _Validates: 4.3_
  - [x] 7.6 [P0] 写属性测试：不支持步骤跳过 — **Property 12** — _Validates: 4.4_

  - [x] 7.7 [P1] 写单元测试：SkillExecutor（`tests/test_skill_executor.py`）
    - read_content + write_file 基本流程、不支持步骤跳过、目标不存在、write_file 无路径
    - 路径穿越测试：`../../etc/passwd` 和绝对路径 `/tmp/foo` 必须被拒绝
    - _Requirements: 4.1, 4.4–4.8, 4.11, 4.12_

- [x] 8. 硬伤 2（v0.4.0 部分）：PublishSkill 语义修复 + 状态枚举收敛
  - [x] 8.1 [P0] 更新 `ink_core/skills/publish.py` 使用 ArticleStatus
    - 替换硬编码状态字符串为枚举
    - 修复 bug：仅 `success` 渠道触发状态推进，`draft_saved` 不推进
    - 当所有渠道均为 `draft_saved` 或 `failed`（无任何 `success`）时：
      - `SkillResult.success = True`（操作本身没出错，草稿已保存）
      - 不更新 `index.md` 的 status（保持 `ready`）
      - 不调用 `update_layers()` / `update_timeline()`
      - 仍写 publish history 记录（记录本次尝试）
    - _Requirements: 2.5, 2.8, 2.9_

  - [x] 8.2 [P0] 更新 SearchSkill / SiteBuilder 状态判断统一走 ArticleStatus
    - SearchSkill 使用 `ArticleStatus.is_visible_in_search()` 替代硬编码 `archived` 判断
    - SiteBuilder 明确保持 v0.4.0 默认仅构建 `status=published`，使用 `ArticleStatus.PUBLISHED.value`
    - 避免状态字符串继续散落在各模块中
    - _Requirements: 2.7, 2.10_

  - [x] 8.3 [P0] 写属性测试：发布门控 — **Property 7** — _Validates: 2.5, 2.9_

- [x] 9. Checkpoint — v0.4.0 全部硬伤修复验证

- [x] 10. 集成测试
  - [x] 10.1 [P0] 中文标题文章创建端到端（`tests/test_engineering_integration.py`）
    - 中英混合标题生成不同 slug — _Requirements: 1.1, 1.2, 1.8_
  - [x] 10.2 [P0] XSS payload 文章构建安全
    - 标题含 `<script>` → build → HTML 中标题已转义
    - 正文含 `<script>` → render_markdown(safe=True) → body_html 中已转义 → Markup 不二次转义
    - _Requirements: 3.2, 3.6, 6.2, 6.3_
  - [x] 10.3 [P0] 自定义 Skill 执行链路
    - 创建 `.ink/skills/test-skill.md` → 注册 → CLI 调用 → SkillExecutor 执行 → 输出文件生成
    - 路径穿越 Skill 定义 → 执行被拒绝
    - _Requirements: 4.1, 4.9, 4.11_
  - [x] 10.4 [P0] PublishSkill draft_saved 不推进状态
    - 创建文章 → status=ready → publish 到 mastodon（返回 draft_saved）→ 验证：
      - status 仍为 ready（未被推进）
      - SkillResult.success = True（草稿保存成功，不算失败）
      - publish history 已写入（记录了本次尝试）
      - timeline.json 未更新（status 没变）
    - _Requirements: 2.8_

- [x] 11. 收尾与发布
  - [x] 11.1 [P0] Final checkpoint — v0.4.0 全量测试通过

  - [x] 11.2 [P1] 文档与版本收尾
    - 更新 README：记录 v0.4.0 新增可选依赖安装方式（`pip install -e ".[all]"`）
    - 记录已知限制：SkillExecutor 仅支持严格 DSL（`read_content` / `write_file`）
    - 更新 pyproject.toml 版本号
    - 更新 CHANGELOG（如有）
    - _Requirements: —_

### v0.4.1 — 语义与产品层清晰化（后续版本）

- [ ] 12. 硬伤 2 完整扩展：发布状态机
  - [ ] 12.1 `ink publish` 改为设置 `drafted`，新增 `ink syndicate` 和 `ink publish --push`
  - [ ] 12.2 `ink build --include-drafted` 预览模式
  - [ ] 12.3 `ink doctor --migrate-status` 迁移工具

- [ ] 13. 硬伤 5：CLI 帮助文本标注
  - [ ] 13.1 帮助文本 `[核心]`/`[技能]`/`[Agent]` 前缀标注 — _Requirements: 5.1–5.4, 5.6_
  - [ ] 13.2 `ink skills list` 区分内置/自定义技能 — _Requirements: 5.5_
  - [ ] 13.3 写单元测试 — _Requirements: 5.1–5.3, 5.5_
  - [ ] 13.4 更新 README / CLI 使用说明
    - 说明哪些是 [核心] 命令、哪些是 [技能] 命令
    - `ink skills list` 如何区分内置/自定义技能
    - 与 CLI 帮助标注保持一致

## Notes

- 所有属性测试为 P0（requirements 中 SHALL 约束），不可跳过
- P1 单元测试强烈建议本版本完成，跳过需记录原因
- v0.4.0 聚焦底层硬伤，v0.4.1 做语义清晰化
- Markdown 渲染器完全自包含，不回头 import site/renderer.py
- render_markdown 默认 safe=True，原始 HTML 被转义后再 Markup()，双重防护闭合
- SkillExecutor 是严格 DSL 解释器，不是 Agent Runtime
- write_file 必须 resolve() 后校验路径在 .ink/skill-output/ 下
- Markup 从 markupsafe 导入，不从 jinja2 导入
- 中英混合 slug 优先组合 ASCII + 拼音，不再"ASCII ≥ 3 就直接返回"
- SkillRegistry 参数链：InkCLI → SkillRegistry(workspace_root) → FileDefinedSkill(def, ws) → SkillExecutor(ws)
