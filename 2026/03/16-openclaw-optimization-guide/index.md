# OpenClaw 生产级优化设置指南

> **来源**: Datawhale 微信公众号文章  
> **作者**: Moritz Kremb（AI 独立开发者）  
> **核心观点**: "装 OpenClaw 很简单，让它稳定运行才是大多数人卡住的地方"  
> **学习时间**: 2026-03-16

---

## TL;DR

本文是 Moritz Kremb 分享的 **OpenClaw 生产级配置指南**，通过 **30-60 分钟的加固操作**，将刚装好的 OpenClaw 变成生产级系统。

**核心解决**: 记忆持久化、API 密钥安全、Cron 任务监控、模型配置、多平台优化等 10 个关键领域。

---

## 一、排错基础（优先级最高）

### 1.1 创建 Claude 运维项目

- 单独创建 Claude 项目用于 OpenClaw 运维调试
- 便于隔离问题和追踪日志

### 1.2 安装 clawdocs 技能

```bash
# 让 OpenClaw 自己能查文档
openclaw skills install clawdocs
```

### 1.3 掌握自检命令

```bash
openclaw gateway status          # 检查 Gateway 状态
openclaw gateway restart         # 重启 Gateway
openclaw doctor                  # 运行诊断
openclaw doctor --repair         # 情况诡异时用
```

---

## 二、个性化配置三件套

| 文件 | 用途 | 当前状态 |
|------|------|:--------:|
| `USER.md` | 助手服务的对象是谁 | ✅ 已配置（程老师） |
| `IDENTITY.md` | 助手的身份定位 | ✅ 已配置（Cookies） |
| `SOUL.md` | 语气风格与行为准则 | ✅ 已配置 |

**状态**: 已完整配置 ✓

---

## 三、记忆持久化机制

### 最低要求

- ✅ 当天文件不存在时自动创建
- ✅ 追加重要决策和经验
- ⚠️ 定期整理，将关键内容归入 MEMORY.md

### 当前状态

- ✅ MEMORY.md 存在
- ✅ memory/YYYY-MM-DD.md 机制已运行
- ⚠️ HEARTBEAT.md 为空（需要添加记忆维护指令）

---

## 四、模型配置策略

### 推荐组合

| 角色 | 推荐模型 |
|------|----------|
| **主力** | openai-codex/gpt-5.3-codex 或 gpt-5.2 |
| **备选** | Anthropic / OpenRouter / Kilo Gateway |

### 当前状态

- 当前使用：moonshot/kimi-k2.5
- **需要配置备选模型** ⚠️

---

## 五、安全加固清单

| 项目 | 建议 | 状态 |
|------|------|:----:|
| **密钥集中存储** | ~/.openclaw/secrets/openclaw.env | ⚠️ 待迁移 |
| **文件权限** | 文件夹 700，文件 600 | ⚠️ 待检查 |
| **VPS 安全** | 只开放可信 IP，gateway token 开启 | ⚠️ 待确认 |
| **dmPolicy** | allowlist 模式 | ⚠️ 待配置 |

---

## 六、Telegram 优化配置

### 推荐设置

| 配置项 | 建议值 |
|--------|--------|
| `dmPolicy` | `allowlist` |
| `groupAllowFrom` | [你的 Telegram ID] |
| `requireMention` | `false`（主动发言）|
| BotFather 隐私模式 | 关闭 |
| 群管理员 | 设为管理员 |
| Topics | 需要时开启 |

### 当前状态

- Telegram 已配置但需检查上述设置 ⚠️

---

## 七、浏览器与搜索配置

### 判断原则

| 场景 | 配置方式 |
|------|----------|
| **自动化/日常工作** | 托管配置（node/openclaw）|
| **需要个人会话/Passkey** | Chrome 中继（profile="chrome"）|

### 当前状态

- ✅ Brave API 已配置
- ✅ 浏览器工具可用

---

## 八、Heartbeat 与 Cron 加固

### 关键指令

Heartbeat 应包含：
- 检查关键 cron 任务的 `lastRunAtMs`
- 发现过期立即强制补跑
- 简要上报异常情况

### 当前状态

- ⚠️ HEARTBEAT.md 为空，需要添加这些指令

---

## 九、运营账号分离

### 建议创建

- **Google 账号** - Agent 专属
- **邮箱** - Gmail 或 AgentMail
- **GitHub 账号** - Agent 专属

### 当前状态

- ⚠️ 未分离，使用个人账号

---

## 十、技能积累策略

### 原则

> **一件事重复做了 2-3 次，就封成技能**

### 高优先级技能

| 技能 | 状态 |
|------|:----:|
| summarize | ✅ 已安装 |
| clawdocs | ⚠️ 待安装 |
| 本地语音转录（Whisper）| ⚠️ 待安装 |

---

## 优化进度检查表

| 优先级 | 项目 | 状态 |
|:------:|------|:----:|
| 1 | 排错基础（clawdocs + 自检命令）| ⚠️ 待安装 clawdocs |
| 2 | 个性化三件套 | ✅ 已完成 |
| 3 | 记忆持久化机制 | ✅ 基本运行 |
| 4 | 模型默认+备选配置 | ⚠️ 待配置备选 |
| 5 | 基础安全（密钥分离、权限控制）| ⚠️ 待迁移 |
| 6 | Telegram 优化 | ⚠️ 待检查 |
| 7 | 浏览器与搜索 | ✅ 已配置 |
| 8 | Heartbeat 与 Cron 加固 | ⚠️ 待更新 |
| 9 | 运营账号分离 | ⚠️ 待创建 |
| 10 | 技能积累策略 | ⚠️ 待安装 |

**当前完成度：约 40%**

---

## 下一步行动

### 立即执行（今天）

1. **安装 clawdocs 技能** (5分钟)
2. **更新 HEARTBEAT.md 配置** (15分钟)

### 本周完成

3. **迁移 API 密钥到安全 env 文件** (10分钟)
4. **检查并设置文件权限** (5分钟)
5. **配置备选模型** (10分钟)
6. **检查 Telegram 安全配置** (10分钟)

### 本月完成

7. **创建 Agent 专属运营账号**
8. **封装重复工作流为技能**
9. **安装本地语音转录**

---

## 关键引用

> "装 OpenClaw 很简单，让它稳定运行才是大多数人卡住的地方"

这句话道出了新用户的典型痛点：
- 记忆在会话之间无法持久化
- Telegram 连不上
- API 密钥直接暴露在 workspace
- Cron 任务静默停止
- 默认模型配置看似正常但深夜报错

---

## 相关资源

- **原文**: Datawhale 微信公众号
- **作者**: Moritz Kremb（AI 独立开发者、X 博主）
- **相关技能**: memos-memory-guide, healthcheck

---

*学习完成时间: 2026-03-16*  
*学习质量: ⭐⭐⭐⭐⭐ (实用性强，立即可用)*
