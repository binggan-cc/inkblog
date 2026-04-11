# Ink Blog Core — OpenClaw Agent Mode 后续改进建议

> 整理时间：2026-04-10
> 审核更新：2026-04-11
> 基于 v0.2.0 + feature/openclaw-agent 完成后的发散性思考

---

## 一、测试覆盖（最高优先级）

tasks.md 中标 `*` 的 13 个属性测试（Property Tests）尚未实现，使用 `hypothesis` 覆盖。
`hypothesis` 已在 `pyproject.toml` 的 `dev` 依赖中，实现成本低，收益高。

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

## 二、数据与可观测性

### 2.1 Journal 统计分析（`ink stats`）

数据已在 journal 文件中，复用 `JournalManager.list_journal_paths()` + `parse_entries()` 做聚合即可。

功能：
- 按 category 统计频次
- 按周/月展示 ASCII heatmap
- 连续打卡天数统计

### 2.2 周报自动生成（`ink digest`）

本质上是 `recall --since` + 模板格式化，复用现有 `RecallEngine`。

```bash
ink digest --week              # 生成本周摘要 Markdown
ink digest --since 2026-04-01  # 自定义区间
```
- 自动写入当天 journal 作为 `[note]` 条目

### 2.3 数据导出

`recall` 已输出 JSON，CSV 只是格式转换，实现简单。

```bash
ink export --format csv --since 2026-01-01
ink export --format json
```

---

## 三、健康诊断（`ink doctor`）

一键检查整个 workspace 的健康状态，各项检查均有现成基础设施可复用：

- Config 合法性验证（复用 `InkConfig.validate_mode()`）
- Git 状态检查（复用 `GitManager`）
- Skill 文件完整性（`_index/skills.json` 中记录的文件是否存在）
- Journal 连续性缺口检测（复用 `JournalManager.list_journal_paths()`）
- L0/L1 与 `index.md` 一致性校验（复用 `L0Generator` / `L1Generator` 重新生成后比对）
- HTTP API 端口可用性检测

---

## 四、Developer Experience

### 4.1 Shell 补全

argparse 已定义完整的子命令和 flag，可用 `argcomplete` 或手写补全脚本。

```bash
ink completion zsh >> ~/.zshrc
ink completion bash >> ~/.bashrc
ink completion fish > ~/.config/fish/completions/ink.fish
```
- `--category` 动态补全从 `VALID_CATEGORIES` 读取
- `ink skill-list` 结果作为 `skill-save` 的补全源

### 4.2 Watch Mode

文件变化时自动 rebuild L0/L1。

```bash
ink serve --watch
```

实现方式：基于定时 `os.scandir` 轮询，或引入 `watchdog` 做 fsevents/inotify 监听。

> 注意：建议 watch 功能作为独立 flag 而非与 HTTP server 强耦合，
> 也可考虑作为独立命令 `ink watch`，避免职责混淆。

### 4.3 自动摘要更新

当前 `L0Generator` 在 journal 创建时生成摘要，但后续 `ink log` 追加内容后不会更新。

建议：每次 `ink log` 追加后同步重新生成 `.abstract` 和 `.overview`，
保持三层上下文与 `index.md` 内容一致。

> 注意：当前 CLI 架构为纯同步，不存在 "异步生成" 的运行时条件，
> 直接在 `JournalManager.append_entry()` 末尾调用 `_generate_layers()` 即可。

---

## 五、LLM-Native 集成（长期调研）

### 5.1 语义检索升级

当前 `RecallEngine` 使用关键词评分匹配，可升级为向量语义检索。

选型考量：
- `sqlite-vec`：需新增外部依赖（当前项目仅依赖 `pyyaml` + `jinja2`），但保持本地存储哲学
- 纯文件存储 embedding：无新依赖，但检索性能受限
- `ink log` 写入时自动提取关键词/实体存入 frontmatter，加速检索

> 注意：引入任何 embedding 方案都会新增外部依赖，需评估对 "零外部依赖" 哲学的影响。

### 5.2 RAG 问答（`ink ask`）

```bash
ink ask "上周学了什么"   # 调用本地 LLM（如 ollama）做 RAG 问答
```

这是独立于 recall 升级的功能，涉及 LLM 调用链、prompt 模板、上下文窗口管理等，
建议作为单独提案设计，不与语义检索混在一起。

---

## 六、生态扩展（长期，需独立设计文档）

### 6.1 Skill Registry（技能市场）

定义 `skills.registry.yaml` 格式：
```yaml
- name: summarize
  url: https://example.com/skills/summarize.md
  version: "1.0"
  sha256: "abc123..."
```
```bash
ink skill-install summarize      # 从 registry 拉取并验证
ink skill-update --all           # 批量更新
```

> ⚠️ 涉及网络请求、SHA256 校验、版本解析、安全验证，复杂度高。
> 建议单独编写设计文档，明确安全模型和依赖管理策略后再实施。

### 6.2 Journal → Blog 提升（`ink promote`）

```bash
ink promote 2026-04-10    # 将 journal 提升为正式文章
```

> ⚠️ journal 的 frontmatter 结构（`tags: [journal, agent]`、`status: draft`、`agent` 字段）
> 与正式文章不同，"提升" 需要 frontmatter 转换、slug 重命名、timeline 更新等操作，
> 比表面看起来复杂。建议先明确需求边界再评估。

### 6.3 Skill 依赖图（`ink skill-graph`）

- `_index/skills.json` 增加 `depends_on` 字段
- 打印 ASCII 依赖树，检测循环依赖和版本冲突

> 当前 `SkillRecord` 没有 `depends_on` 字段，需扩展 schema。
> 且现有技能数量较少，依赖图的实际价值有待验证。优先级较低。

---

## 七、暂不纳入（需进一步论证）

以下方向在当前阶段不建议实施，记录于此供未来参考。

### 7.1 跨 Workspace 检索

```bash
ink recall "关键词" --workspace /other/path
```

**暂缓原因**：允许一个 agent 读取任意路径的 journal 数据，违反 FS-as-DB 的 workspace 隔离原则。
如果未来要做，至少需要设计白名单/授权机制。

### 7.2 多 Agent 协作与通信

```
Agent-A (port 4001) → POST /log → Agent-B (port 4002)
```
- agent 发现协议（mDNS 或静态注册表）
- 跨 workspace 技能共享

**暂缓原因**：范围远超当前项目边界。当前单 agent 的 HTTP API 尚无集成测试，
不应在此阶段讨论多 agent 协作。建议在单 agent 模式稳定后，作为独立 RFC 提出。

### 7.3 Config Profile 切换

```bash
ink --profile work serve
ink --profile personal log "今天的笔记"
```

**暂缓原因**：当前 agent 场景下，一个 workspace 对应一个 agent 是最自然的映射。
多 profile 切换更适合人类用户多身份场景，对 agent 价值有限。
如有需求，可通过多 workspace 目录实现同等效果。

---

## 优先级矩阵

| 方向 | 用户价值 | 实现难度 | 建议优先级 |
|------|---------|---------|-----------|
| Property Tests（一） | 质量保障 | 低 | ⭐⭐⭐ 立即 |
| `ink stats` 统计（二） | 高 | 中 | ⭐⭐⭐ 近期 |
| `ink doctor` 诊断（三） | 运维友好 | 中 | ⭐⭐⭐ 近期 |
| `ink digest` 周报（二） | 中 | 低 | ⭐⭐ 近期 |
| 自动摘要更新（四） | 数据一致性 | 低 | ⭐⭐ 近期 |
| Shell 补全（四） | DX 提升 | 低 | ⭐⭐ 中期 |
| Watch Mode（四） | DX 提升 | 中 | ⭐⭐ 中期 |
| 数据导出（二） | 低 | 低 | ⭐ 中期 |
| 语义检索 / RAG（五） | 差异化 | 高 | ⭐ 长期调研 |
| Skill Registry（六） | 生态 | 高 | ⭐ 长期，需独立设计文档 |
| Journal → Blog（六） | 中 | 中 | ⭐ 长期，需明确需求 |
| Skill 依赖图（六） | 低 | 中 | ⭐ 长期 |
| 跨 Workspace / 多 Agent / Profile（七） | — | — | 暂不纳入 |
