---
title: Claude Code 的 15 个隐藏能力
slug: claude-code-15-hidden-features
date: '2026-04-04'
status: published
tags: []
published_at: '2026-04-05T01:30:00'
---


# Claude Code 的 15 个隐藏能力

> 来源：Boris Cherny (Claude Code创始人) 2025年3月30日  
> 核心观点：Claude Code的上限越来越不由模型决定，而是由你的工作环境决定

---

## TL;DR

这篇文章不是"15个技巧清单"，而是一套**AI编程工作环境的工程化设计方法论**——从验证、自动化、上下文管理、并行隔离到跨设备调度，构建一个可持续、可审计、可扩展的软件生产系统。

**核心转变**：从"我对大模型说很多话" → "我在调度一组职责不同的 worker"

---

## 一、核心框架：四层能力体系

| 层级 | 核心能力 | 解决的问题 |
|:---|:---|:---|
| **第一层** | **验证** | Claude 怎么验证自己是不是真的做对了 |
| **第二层** | **隔离** | 一个会话跑到一半，怎么安全地分叉出去 |
| **第三层** | **分叉** | 大任务怎么并行，不互相污染 |
| **第四层** | **调度** | 人不在电脑前时，Claude 怎么继续帮你干活 |

---

## 二、15个隐藏能力详解

### 【第一层】验证闭环：让 Claude 能自证

#### 1. Chrome Extension（浏览器集成）

| 项目 | 说明 |
|:---|:---|
| **功能** | 让 Claude 直接操作浏览器，读取 DOM、查看 console 报错、自动填表、走完用户流程 |
| **命令** | `claude --chrome` |
| **核心价值** | 终结"代码看起来对，但跑起来错"的循环，实现**验证闭环** |

**工程原则**：不要让模型靠"描述世界"来工作，要尽量让它**直接接触世界**

---

#### 2. Desktop App（桌面应用）

- 本地预览与测试
- 直接查看渲染效果
- 交互式调试

---

#### 3. `/loop`（自动化循环）

> Boris原话："/loop和/schedule是Claude Code最强大的两个功能"

**三种级别**：

| 级别 | 特性 | 适用场景 |
|:---|:---|:---|
| **Session级** (`/loop`) | 退出会话即消失 | 临时巡检、当前任务相关 |
| **Desktop级** | 本机持续执行，应用开着就跑 | 需要持久运行的任务 |
| **Cloud级** | 跑在Anthropic云端，电脑关了也能跑 | 需要关机后继续的任务 |

**Boris的循环任务示例**：
```bash
/loop 5m /babysit          # 每5分钟自动处理code review、rebase、护送PR到合并
/loop 30m /slack-feedback  # 每30分钟把Slack反馈整理成PR
/loop /post-merge-sweeper  # 自动清理合并后遗漏的review comments
/loop 1h /pr-pruner        # 每小时关掉过时PR
```

---

#### 4. Hooks（生命周期钩子）

| 钩子点 | 用途 |
|:---|:---|
| `SessionStart` | 每次启动时动态加载上下文 |
| `PreToolUse` | 每个bash命令运行前做日志记录 |
| `PermissionRequest` | 把权限审批请求转发到WhatsApp远程确认 |
| `Stop` | Claude停下来时自动"戳"它继续 |

> **本质**: `/loop`让Claude**持续工作**，Hooks让Claude**始终可控**

---

### 【第二层】上下文保护

#### 5. `/btw`（临时询问）

- 能看到当前上下文，但**无工具权限**
- 回答被丢弃、**不进主线历史**
- 临时小问不干扰主任务

#### 6. `/branch`（会话分叉）

- 创建**分支会话**，安全试错后再决定
- 重构、方案试验、定位复杂bug时使用
- 降低"搞坏当前状态"的心理负担

**创建方式**：
```bash
# 方式1: 当前session内
/branch

# 方式2: CLI恢复时新建分支
claude --resume <session-id> --fork-session
```

#### 7. `--bare`（最小模式）

- 跳过hooks、skills、plugins、MCP、auto memory
- **速度提升10倍**
- 适合快速查询、简单任务

---

### 【第三层】并行与隔离

#### 8. Git Worktrees

- 同一仓库相对安全地跑多个Claude，互相隔离
- 多任务同时进行的基础

#### 9. `/batch`

- 把可并行化的大改动切散
- 分发给多个worktree agents

#### 10. `--agent`（自定义Agent）

把口头约束变成**文件化、可复用、可分工**的工作角色：

```bash
# 创建只读agent
claude --agent=ReadOnly

# 项目级agent
claude --agent my-custom-agent
```

**典型agent角色**：
- **只读分析agent**: 负责看代码不改文件
- **安全审查agent**: 专门盯依赖、权限和敏感配置
- **前端验证agent**: 优先调用浏览器相关工具
- **迁移agent**: 专门做规则明确的大规模替换

---

### 【第四层】脱离当前电脑

#### 11. `--teleport`

- 把云端(手机/网页)发起的session拉回本地继续
- 移动端 → 桌面端

#### 12. `--remote-control`

- 让本地session被手机/浏览器远程接管
- 桌面端 → 移动端

#### 13. **Dispatch**

- 从手机发起**全新任务**（非接管现有）
- 适合"不在电脑前但得处理"的事

#### 14. `/voice`

- 语音驱动Claude
- CLI按空格、Desktop按语音按钮、iOS系统听写

#### 15. **Scheduled Tasks**

- 定时自动执行任务
- 本地版 vs Cloud版（关机继续）

---

## 三、优先学习的6个功能

| 优先级 | 功能 | 理由 |
|:---|:---|:---|
| **1** | 补验证 (`--chrome`/Desktop) | 最直接的质量提升器，没有验证很难确认"到底有没有做对" |
| **2** | `/loop`自动化 | 把重复巡检工作自动化，Boris后台挂4-5个循环任务 |
| **3** | `/btw`保护上下文 | 任务超过30分钟就该养成习惯，支线不污染主线 |
| **4** | `/branch`先分叉再试 | 重构、方案试验、定位复杂bug时，降低"搞坏当前状态"的心理负担 |
| **5** | worktree跑并行 | 未来多Claude同时工作的**地基** |
| **6** | `--agent`或项目agent | 把约束提前收进配置，跨仓协作加`--add-dir` |

---

## 四、关键边界与注意事项

| 功能 | 限制/风险 |
|:---|:---|
| Chrome integration | Beta阶段，**仅支持Chrome/Edge**，不支持Brave/Arc/WSL |
| `/loop` | Session级，退出即消失；循环任务**3天过期** |
| Desktop scheduled tasks | 电脑睡眠或应用关闭时**不会自动补跑** |
| Hooks | `Stop` hook配置不当可能导致Claude**永远停不下来** |
| `--bare` | 跳过memory/skills/hooks/CLAUDE.md，**约束更少** |
| worktree | 提高Git纪律要求，需规范命名、提交、回收、合并 |

---

## 五、核心认知升级

### 旧认知 → 新认知

| 旧认知 | 新认知 |
|:---|:---|
| `/loop`是定时器 | 是让Claude**持续接管重复工程巡检** |
| Hooks是高级配置 | 是让Claude行为**变得确定和可审计** |
| `/btw`是小玩具 | 是在**保护上下文** |
| `/branch`是方便命令 | 是在**降低试错成本** |
| worktree是Git花活 | 是在给**并行执行提供隔离层** |
| `--teleport`/Remote Control是移动端噱头 | 是在把"开发行为"从**当前电脑解耦** |
| Dispatch/scheduled tasks是自动发消息 | 是让Claude**接手原本需你持续在场的工程流程** |

---

## 六、与 OpenClaw 的对比思考

| Claude Code 能力 | OpenClaw 对应/潜在对应 |
|:---|:---|
| `--chrome` 浏览器集成 | Playwright / Scrapling 技能 ✅ |
| `/loop` 循环任务 | Cron 定时任务 ✅ |
| `/schedule` 定时调度 | Cron + Heartbeat ✅ |
| Hooks 生命周期钩子 | Skill 机制 + 预定义 hooks |
| `/btw` 保护上下文 | 子代理 (sessions_spawn) ✅ |
| `/branch` 分叉会话 | 子代理模式 ✅ |
| `--bare` 最小模式 | 可配置的系统提示词 |
| Git Worktrees | 多工作区支持 |
| `/batch` 批处理 | ClawFlow 并行任务 |
| `--agent` 自定义 Agent | 多 Agent 配置 |
| `--teleport` 会话转移 | sessions_send / 会话恢复 |
| `/remote-control` 远程控制 | Canvas + 远程访问 |
| `/voice` 语音输入 | TTS / ASR 技能 ✅ |

---

## 七、参考链接

- Boris原始X线程: https://x.com/bcherny/status/2038454336355999749
- GitHub整理: https://github.com/shanraisshan/claude-code-best-practice/blob/main/tips/claude-boris-15-tips-30-mar-26.md
- Claude Code Docs: https://code.claude.com/docs/en/overview

---

**总结**: 
> **Claude Code不再只是"帮你写代码更快一点"，它开始像一个可以慢慢打磨出来的软件生产系统。**
