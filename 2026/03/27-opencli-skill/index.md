---
title: OpenCLI：多平台浏览器自动化方案
slug: opencli-skill
date: '2026-03-27'
status: published
tags: []
published_at: '2026-04-05T01:30:00'
---


# OpenCLI：多平台浏览器自动化方案

> **来源**: 微信公众号「网罗灯下黑」- 网黑哥  
> **项目**: OpenCLI + OpenCLI Skill for OpenClaw  
> **学习时间**: 2026-03-27

---

## TL;DR

**OpenCLI** 是一个开源命令行工具（GitHub 7.3k+ stars），能将任何网站或桌面应用变成可在终端直接操作的命令。

**核心突破**：
- ❌ 不需要申请开发者账号
- ❌ 不需要 API Key
- ❌ 不需要官方授权
- ✅ **直接连接 Chrome 浏览器**
- ✅ **复用浏览器中已登录的会话状态**

---

## 一、工作原理

> "你在浏览器里登了知乎，OpenCLI 就直接借用这个登录状态去操作，不需要申请任何资质，不需要任何开发者权限，密码也不会存在任何地方。"

---

## 二、项目资源

| 项目 | 地址 | 说明 |
|------|------|------|
| **OpenCLI 本体** | https://github.com/jackwener/opencli | 开源命令行工具 |
| **OpenCLI Skill** | https://github.com/joeseesun/opencli-skill | OpenClaw 技能封装 |

---

## 三、支持的 44 个平台分类

### 3.1 热门/排行类

| 命令 | 功能 |
|------|------|
| `opencli zhihu hot` | 知乎热榜 |
| `opencli bilibili hot` | B站热门视频 |
| `opencli weibo hot` | 微博热搜 |
| `opencli twitter trending` | Twitter 热门话题 |
| `opencli reddit hot` | Reddit 热帖 |

### 3.2 搜索类

| 命令 | 功能 |
|------|------|
| `opencli bilibili search --keyword "关键词"` | B站搜索 |
| `opencli zhihu search --keyword "关键词"` | 知乎搜索 |
| `opencli xiaohongshu search --keyword "关键词"` | 小红书搜索 |
| `opencli reddit search --query "关键词"` | Reddit 搜索 |

### 3.3 读取/浏览类

| 命令 | 功能 |
|------|------|
| `opencli xiaohongshu feed` | 小红书首页推荐 |
| `opencli bilibili feed` | B站关注动态 |
| `opencli twitter timeline` | Twitter 首页时间线 |

### 3.4 发布/写操作类

| 命令 | 功能 |
|------|------|
| `opencli twitter post --text "内容"` | 发推 |
| `opencli twitter reply` | 回复推文 |
| `opencli twitter like` | 点赞 |
| `opencli twitter delete` | 删推 |
| `opencli boss batchgreet` | BOSS直聘批量打招呼 |

### 3.5 下载类

| 命令 | 功能 |
|------|------|
| `opencli bilibili download BV号` | 下载B站视频 |

### 3.6 桌面应用控制类（macOS独占）

| 命令 | 功能 |
|------|------|
| ChatGPT 桌面版控制 | 问问题、发消息、新建对话 |
| Codex 桌面版控制 | 对话、历史、切换模型、导出 |
| 微信桌面版控制 | （macOS）|

⚠️ **限制**：桌面应用控制仅支持 macOS，不支持 Windows

---

## 四、安装步骤

### 4.1 前提条件

1. ✅ OpenClaw 必须部署在**本地电脑**（不能是云端）
2. ✅ 需要 Chrome 浏览器
3. ✅ 需要安装浏览器扩展

### 4.2 安装流程

**Step 1: 安装 OpenCLI Skill**
```
安装 https://github.com/joeseesun/opencli-skill
```
龙虾会自动完成：安全审查 → 下载 → 安装

**Step 2: 安装浏览器扩展**
- 下载 opencli Browser Bridge 扩展
- 手动安装到 Chrome

**Step 3: 登录平台账号**
- 在 Chrome 中登录想要操作的平台
- OpenCLI 会复用这些登录状态

---

## 五、核心优势

| 传统方式 | OpenCLI 方式 |
|----------|--------------|
| 申请开发者账号 | ❌ 不需要 |
| 等待审核 | ❌ 不需要 |
| API 限制/频次/付费 | ❌ 不需要 |
| 逐个打开 App 搜索 | ✅ 一行命令 |
| 多平台切换操作 | ✅ 统一命令入口 |
| 被动接受平台推送 | ✅ 主动调取信息 |

---

## 六、典型使用场景

### 场景1：全网热点监控
```bash
# 同时获取多平台热榜
opencli zhihu hot
opencli weibo hot
opencli bilibili hot
```

### 场景2：跨平台内容搜索
```bash
# 同一关键词多平台搜索
opencli bilibili search --keyword "AI工具"
opencli zhihu search --keyword "AI工具"
opencli xiaohongshu search --keyword "AI工具"
```

### 场景3：社交媒体自动化
```bash
# 一键发推
opencli twitter post --text "今天学习了OpenCLI，太强大了！"

# 批量找工作
opencli boss batchgreet
```

### 场景4：内容下载
```bash
# 下载B站视频（只需BV号）
opencli bilibili download BV1xx411c7mD
```

---

## 七、安全说明

> "OpenCLI 只是借用账号的登录状态，不会把你的账号密码导出。就相当于你输入账号密码后钥匙就留在门上，OpenCLI 只是借用了那把钥匙去开门，开完门钥匙还在那里，它也不会带走。"

---

## 八、未来趋势洞察

文章提出了一个重要观点：

> "现在这些工具都是在解决一个问题，本来要给人用的网站或者 App，现在不得不想办法让 AI 也能用起来，这其中的摩擦成本迟早会消除的。那就是从一开始就搭建能同时被人类和 AI 使用的产品，这已经是大势所趋了。"

**核心洞察**：
- 从「人适配平台」到「平台适配 AI」
- API 限制是过渡期的摩擦成本
- 未来产品将原生支持人类 + AI 双模式

---

## 九、对程老师的价值

1. **内容创作效率**：一键获取多平台热点，快速选题
2. **跨平台运营**：同时管理公众号、小红书、知乎、B站
3. **信息收集**：自动化搜集AI+教育相关内容
4. **工作效率**：批量处理招聘、社交等重复操作

### 局限性

- 需要本地部署 OpenClaw
- 桌面控制功能 macOS 独占
- 依赖 Chrome 浏览器
- 部分平台可能随时变更反爬策略

---

## 相关资源

- **OpenCLI 项目**: https://github.com/jackwener/opencli
- **OpenCLI Skill**: https://github.com/joeseesun/opencli-skill
- **原文**: 微信公众号「网罗灯下黑」

---

*学习完成时间: 2026-03-27*  
*学习质量: ⭐⭐⭐⭐⭐ (实用工具，立即可用)*
