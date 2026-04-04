# Liquid Blog v2.0 - 系统文档

> 🌊 像水一样流动的博客系统 | Skills + Markdown + 意图驱动

---

## 📚 完善内容总览

### 1️⃣ 三层上下文架构（已完善）

**自动生成系统** (`.ink/scripts/layer-generator.py`)

| 层级 | 文件 | 内容 | 用途 |
|------|------|------|------|
| **L0** | `.abstract` | 一句话摘要 | 快速检索、列表展示 |
| **L1** | `.overview` | YAML 结构化元数据 | 决策支持、关联推荐 |
| **L2** | `index.md` | 完整 Markdown 内容 | 深度阅读、全文搜索 |

**功能**:
- ✅ 自动生成 L0/L1 层
- ✅ 提取标题、标签、关键词
- ✅ 统计代码块、字数、阅读时间
- ✅ 批量处理所有文章

**用法**:
```bash
ink layer --generate                    # 生成全部
ink layer --generate 2025/03/20-xxx/    # 生成指定文章
ink layer --info 2025/03/20-xxx/        # 查看信息
```

---

### 2️⃣ Skills 系统（已增强）

| Skill | 功能 | 状态 |
|-------|------|------|
| **publish** | 多渠道发布 | ✅ |
| **analyze** | 内容分析 | ✅ |
| **search** | 语义搜索 | ✅ |
| **sync** ⭐ | Git 同步 | ✅ 新增 |
| **template** ⭐ | 模板管理 | ✅ 新增 |

**新增 Skills**:

#### sync - 同步到 Git
```bash
ink sync                              # 同步全部
ink sync 2025/03/20-xxx/             # 同步指定文章
ink sync --message "自定义提交信息"
ink sync --status                    # 查看同步状态
```

#### template - 模板系统
```bash
ink template list                     # 列出模板
ink template apply tech-review "标题" # 使用模板
ink template create my-template       # 创建模板
ink template edit my-template        # 编辑模板
```

**模板列表**:
- `default` - 默认文章模板
- `tech-review` - 技术评测模板 ⭐
- `weekly-report` - 周报模板 ⭐

---

### 3️⃣ Git 集成（已完善）

**完整 Git 工作流** (`.ink/scripts/git-integration.py`)

| 功能 | 命令 |
|------|------|
| 初始化仓库 | `ink git init` |
| 查看状态 | `ink git status` |
| 提交变更 | `ink git commit -m "消息"` |
| 查看历史 | `ink git log -n 20` |
| 文件溯源 | `ink git blame path/to/file` |
| 文章历史 | `ink git history 2025/03/20-xxx/` |
| 统计报告 | `ink git stats --period week` |
| 推送到远程 | `ink git push` |
| 拉取更新 | `ink git pull` |

**自动功能**:
- ✅ 自动初始化 `.gitignore`
- ✅ 提交信息模板
- ✅ 文章修改历史追踪
- ✅ 统计报告生成

---

### 4️⃣ CLI 增强（已完善）

**Ink CLI v2** (`ink-v2`)

#### 新增功能

| 功能 | 说明 |
|------|------|
| **彩色输出** | 状态、路径、层级用颜色区分 |
| **标签支持** | `ink new "标题" --tags ai,ml` |
| **分类支持** | `ink new "标题" --category tech` |
| **模板选择** | `ink new "标题" --template tech-review` |
| **自动 L0/L1** | 创建文章后自动生成三层上下文 |
| **编辑后更新** | 编辑完成自动更新 L0/L1 |
| **NLP 增强** | 更多自然语言意图识别 |

#### 命令对比

| v1 (ink) | v2 (ink-v2) | 改进 |
|----------|-------------|------|
| `ink status` | `ink status` | +Git 状态 |
| `ink new` | `ink new` | +模板/标签/自动 L0/L1 |
| - | `ink layer` | ⭐ 新增三层管理 |
| - | `ink git` | ⭐ 新增 Git 命令 |
| `ink sync` | `ink sync` | 调用 sync skill |
| `ink template` | `ink template` | 调用 template skill |

#### 自然语言命令示例

```bash
ink "创建一篇关于 AI 的技术评测"
ink "搜索上周写的文章"
ink "同步今天的变更到 Git"
ink "把草稿状态的文章发布出去"
ink "生成周报模板"
```

---

## 📁 完整目录结构

```
~/ink/                          # Blog 宇宙
│
├── .ink/                       # 系统目录
│   ├── config.yaml            # 全局配置
│   │
│   ├── skills/                # Skills（可复用能力）⭐
│   │   ├── publish.md         # 发布
│   │   ├── analyze.md         # 分析
│   │   ├── search.md          # 搜索
│   │   ├── sync.md            # 同步 ⭐
│   │   └── template.md        # 模板 ⭐
│   │
│   ├── scripts/               # 核心脚本 ⭐
│   │   ├── layer-generator.py # 三层上下文生成 ⭐
│   │   └── git-integration.py # Git 集成 ⭐
│   │
│   ├── workflows/             # 工作流
│   │   └── morning-routine.md
│   │
│   └── sessions/              # 会话记忆
│
├── 2025/03/20-liquid-blog/    # 文章示例
│   ├── .abstract              # L0: 摘要 ⭐
│   ├── .overview              # L1: 概览 ⭐
│   ├── index.md               # L2: 详情
│   └── assets/
│
├── _templates/                # 模板库 ⭐
│   ├── default/               # 默认模板
│   ├── tech-review/           # 技术评测 ⭐
│   └── weekly-report/         # 周报 ⭐
│
├── _index/                    # 全局索引
│
├── ink                        # CLI v1
├── ink-v2                     # CLI v2 ⭐
├── install.sh                 # 安装脚本
├── quickstart.sh              # 快速开始 ⭐
├── demo.html                  # 可视化演示
└── README.md                  # 项目文档
```

---

## 🚀 快速开始

```bash
# 1. 初始化
cd ~/ink
./ink-v2 init

# 2. 或使用快速开始脚本
./quickstart.sh

# 3. 创建文章
./ink-v2 new "我的第一篇博客" --tags demo --template default

# 4. 编辑
./ink-v2 edit 2025/03/20-我的第一篇博客/

# 5. 同步到 Git
./ink-v2 sync --message "首次提交"

# 6. 或使用自然语言
./ink-v2 "发布昨天的文章"
```

---

## 📊 系统特点

| 特性 | 实现 | 效果 |
|------|------|------|
| **三层上下文** | L0/L1/L2 自动生成 | Token 成本 -90% |
| **Skills 即代码** | Markdown + Python | 可复用、自文档化 |
| **Git 原生集成** | 完整工作流 | 版本控制、历史追踪 |
| **意图驱动** | NLP 解析 | 自然语言交互 |
| **模板系统** | 多场景模板 | 快速结构化写作 |
| **文件即数据** | FS-as-DB | 零锁定、易迁移 |

---

## 🛠️ 扩展开发

### 添加新 Skill

1. 创建 `.ink/skills/my-skill.md`
2. 添加 frontmatter 元数据
3. 编写使用文档
4. 嵌入 Python 代码块
5. 完成！自动可用

### 添加新模板

1. 创建 `_templates/my-template/` 目录
2. 添加 `index.md`、`.overview`、`.abstract`
3. 使用 `{{变量}}` 占位
4. 可用：`ink template apply my-template "标题"`

### 自定义脚本

1. 放入 `.ink/scripts/`
2. 通过 `ink` 命令调用
3. 或独立运行

---

## 📖 设计理念

```
Liquid CLI 哲学
    │
    ├── 像水一样适应容器 → 意图驱动，无需记忆命令
    ├── Skills 即能力 → 可复用、可组合
    ├── 文件即数据 → 无锁定、可迁移
    └── 三层上下文 → 高效 Token 使用
```

---

*Built with 💧 Liquid Philosophy*  
*Version 2.0 | 2025-03-20*
