# Requirements Document

## Introduction

OpenClaw Agent Mode 是 ink-blog-core 的 AI Agent 专用扩展分支（`feature/openclaw-agent`），
基于 `main` 分支构建，为 OpenClaw（一个 AI Agent）提供自动写入日记、检索记忆的能力。

核心设计原则：
- 继承 FS-as-DB 哲学，所有数据仍以本地文件系统为唯一存储
- 新增 `agent` 模式，通过配置与人类博客模式区分
- 新增 `ink log` 和 `ink recall` 两个 Agent 专用命令
- 可选 HTTP API（`ink serve`），供 OpenClaw 通过 REST 调用
- 人类博客功能（publish、build、search 等）在 agent 模式下作为可选配置保留

---

## Glossary

- **OpenClaw**: 使用本系统的 AI Agent，角色为"龙虾"，通过 CLI 或 HTTP API 与系统交互
- **Agent_Mode**: ink 工作区的运行模式，值为 `agent` 时启用 Agent 专用行为
- **Daily_Journal**: 每日日记文件，路径格式为 `YYYY/MM/DD-journal/index.md`，每天自动创建
- **Log_Entry**: 追加到 Daily_Journal 的单条记录，包含时间戳、分类和内容
- **Entry_Category**: 日记条目的分类标签，枚举值为 `work`、`learning`、`skill-installed`、`memory`、`note`
- **Recall_Query**: OpenClaw 发起的记忆检索请求，返回结构化 JSON
- **Recall_Result**: `ink recall` 命令返回的 JSON 结构，包含匹配条目列表
- **HTTP_API**: `ink serve` 启动的本地 HTTP 服务，将 CLI 命令映射为 REST 端点
- **InkConfig**: 现有分层配置管理器，读取 `.ink/config.yaml`
- **SkillResult**: 现有命令返回结构，包含 `success`、`message`、`data`、`changed_files`
- **ArticleManager**: 现有文章管理器，负责创建和读取文章目录结构
- **Three_Layer_Context**: 现有三层上下文体系（L0 `.abstract`、L1 `.overview`、L2 `index.md`）
- **External_Skill**: 从外部来源（GitHub、技能市场等）安装的技能，只记录元数据，不复制文件到工作区
- **Custom_Skill**: OpenClaw 自己生成或创建的技能，定义文件保存到 `.ink/skills/`，纳入 Git 版本控制
- **Skill_Registry**: `_index/skills.json`，记录所有已安装技能的元数据索引（外部 + 自创）

---

## Requirements

### Requirement 1: Agent 模式配置

**User Story:** As OpenClaw, I want to configure the workspace in agent mode, so that the system behaves differently from a human blog and enables agent-specific features.

#### Acceptance Criteria

1. THE InkConfig SHALL support a top-level `mode` field with valid values `human` (default) and `agent`.
2. THE InkConfig SHALL support an `agent` configuration block containing `agent_name`, `auto_create_daily`, and `default_category` fields.
3. WHEN `mode` is not specified in `.ink/config.yaml`, THE InkConfig SHALL default `mode` to `human`.
4. WHEN `mode` is set to `agent` and `agent.auto_create_daily` is `true`, THE System SHALL automatically create a Daily_Journal entry for the current date before executing any `ink log` command if one does not already exist.
5. IF `agent.default_category` is not specified in the config, THEN THE System SHALL use `note` as the default Entry_Category.
6. THE InkConfig SHALL reject any `mode` value other than `human` or `agent` and return a descriptive ConfigError.

---

### Requirement 2: `ink log` — Agent 日记写入命令

**User Story:** As OpenClaw, I want to append log entries to today's journal file via a single CLI command, so that I can record my daily work, learning, and memories without manual file editing.

#### Acceptance Criteria

1. WHEN `ink log "<content>"` is executed in agent mode, THE Log_Command SHALL append a new Log_Entry to the Daily_Journal for the current date.
2. THE Log_Command SHALL support a `--category` flag accepting values `work`, `learning`, `skill-installed`, `memory`, `note`; WHEN `--category` is omitted, THE Log_Command SHALL use the `agent.default_category` from config.
3. IF `--category` is provided with a value not in the valid Entry_Category enum, THEN THE Log_Command SHALL return a SkillResult with `success=false` and a descriptive error message listing valid categories.
4. WHEN appending a Log_Entry, THE Log_Command SHALL prepend a timestamp in `HH:MM` format (local time) and the category label to the entry content.
5. WHEN `ink log` is executed and no Daily_Journal exists for the current date, THE Log_Command SHALL create the Daily_Journal file before appending, using the date as the article title.
6. THE Log_Entry format appended to `index.md` SHALL follow the pattern: `\n## HH:MM [category]\n\n<content>\n`.
7. WHEN `ink log` succeeds, THE Log_Command SHALL return a SkillResult with `success=true`, the appended entry text in `message`, and `changed_files` containing the Daily_Journal path.
8. IF `ink log` is executed when `mode` is not `agent`, THEN THE Log_Command SHALL return a SkillResult with `success=false` and the message `"ink log requires agent mode. Set mode: agent in .ink/config.yaml"`.
9. WHEN `git.auto_commit` is `true`, THE Log_Command SHALL trigger a Git commit after a successful append with message `"log: <HH:MM> [<category>] <first 60 chars of content>"`.

---

### Requirement 3: Daily Journal 文件结构

**User Story:** As OpenClaw, I want each day's journal to have a consistent, machine-readable structure, so that I can reliably parse and retrieve past entries.

#### Acceptance Criteria

1. THE Daily_Journal SHALL be stored at path `YYYY/MM/DD-journal/index.md` relative to the workspace root, where `YYYY/MM/DD` is the entry date.
2. THE Daily_Journal `index.md` SHALL contain a YAML frontmatter block with fields: `title` (value `"YYYY-MM-DD Journal"`), `date`, `status` (value `"draft"`), `tags` (value `["journal", "agent"]`), and `agent` (value of `agent.agent_name` from config).
3. THE Daily_Journal SHALL contain a `## Entries` section header after the frontmatter, under which all Log_Entry blocks are appended.
4. WHEN a Daily_Journal is created, THE System SHALL also generate the Three_Layer_Context files (`.abstract`, `.overview`) consistent with the existing ArticleManager behavior.
5. THE Daily_Journal path format SHALL be parseable by the existing ArticleManager without modification to the ArticleManager class.

---

### Requirement 4: `ink recall` — Agent 记忆检索命令

**User Story:** As OpenClaw, I want to query past journal entries and return structured JSON, so that I can retrieve relevant memories and context for my current tasks.

#### Acceptance Criteria

1. WHEN `ink recall "<query>"` is executed in agent mode, THE Recall_Command SHALL search across all Daily_Journal files and return a Recall_Result as JSON to stdout.
2. THE Recall_Result JSON SHALL conform to the schema: `{"query": string, "total": int, "entries": [{"date": string, "time": string, "category": string, "content": string, "source": string}]}`.
3. THE Recall_Command SHALL support a `--category` flag to filter results to a specific Entry_Category; WHEN omitted, THE Recall_Command SHALL search across all categories.
4. THE Recall_Command SHALL support a `--since` flag accepting a date in `YYYY-MM-DD` format to restrict results to entries on or after that date.
5. THE Recall_Command SHALL support a `--limit` flag accepting a positive integer; WHEN omitted, THE Recall_Command SHALL default to returning at most 20 entries.
6. WHEN `--limit` is provided with a value less than 1 or greater than 500, THE Recall_Command SHALL return a SkillResult with `success=false` and a descriptive error message.
7. THE Recall_Command SHALL rank results by relevance: exact keyword match in content scores higher than partial match; entries with more keyword occurrences rank higher; ties are broken by descending date then descending time.
8. WHEN no matching entries are found, THE Recall_Command SHALL return a valid Recall_Result JSON with `"total": 0` and `"entries": []`.
9. IF `ink recall` is executed when `mode` is not `agent`, THEN THE Recall_Command SHALL return a SkillResult with `success=false` and the message `"ink recall requires agent mode. Set mode: agent in .ink/config.yaml"`.
10. FOR ALL valid Daily_Journal files written by `ink log`, parsing the file and extracting entries then re-serializing to Recall_Result JSON SHALL produce entries whose `content` field equals the original content passed to `ink log` (round-trip property).

---

### Requirement 5: Entry_Category 分类系统

**User Story:** As OpenClaw, I want each log entry to carry a semantic category, so that I can filter and organize memories by type when recalling.

#### Acceptance Criteria

1. THE System SHALL define exactly five valid Entry_Category values: `work`, `learning`, `skill-installed`, `memory`, `note`.
2. THE System SHALL treat Entry_Category values as case-insensitive during input parsing; WHEN stored, THE System SHALL normalize to lowercase.
3. WHEN `ink recall --category skill-installed` is executed, THE Recall_Command SHALL return only entries whose stored category is `skill-installed`.
4. THE System SHALL expose the list of valid Entry_Category values via `ink log --help` output.

---

### Requirement 6: 可选 HTTP API（`ink serve`）

**User Story:** As OpenClaw, I want to call ink commands via HTTP REST instead of CLI, so that I can integrate with other systems or call from environments where subprocess execution is inconvenient.

#### Acceptance Criteria

1. WHERE `agent.http_api.enabled` is `true` in config, THE HTTP_API SHALL start a local HTTP server on the configured `agent.http_api.port` (default `4242`) when `ink serve` is executed.
2. THE HTTP_API SHALL expose a `POST /log` endpoint that accepts a JSON body `{"content": string, "category": string}` and executes the equivalent of `ink log`.
3. THE HTTP_API SHALL expose a `POST /recall` endpoint that accepts a JSON body `{"query": string, "category": string, "since": string, "limit": int}` and returns the Recall_Result JSON.
4. THE HTTP_API SHALL expose a `GET /health` endpoint that returns `{"status": "ok", "mode": "agent", "agent_name": string}`.
5. WHEN a request to `POST /log` or `POST /recall` is missing the required field, THE HTTP_API SHALL return HTTP 400 with a JSON body `{"error": "<field> is required"}`.
6. IF `ink serve` is executed when `mode` is not `agent`, THEN THE HTTP_API SHALL refuse to start and return exit code 1 with the message `"ink serve requires agent mode"`.
7. WHEN `agent.http_api.enabled` is `false` or absent, THE System SHALL not start any HTTP server and `ink serve` SHALL return a SkillResult with `success=false` and message `"HTTP API is disabled. Set agent.http_api.enabled: true in config"`.

---

### Requirement 7: 人类博客功能的兼容性保留

**User Story:** As a workspace administrator, I want human blog commands (publish, build, search) to remain available in agent mode as an opt-in, so that the same workspace can serve dual purposes if needed.

#### Acceptance Criteria

1. WHILE `mode` is `agent`, THE System SHALL still register and expose the `publish`, `build`, `search`, `analyze`, `rebuild` commands.
2. WHEN `mode` is `agent` and `agent.disable_human_commands` is `true`, THE System SHALL return a SkillResult with `success=false` and message `"Command '<name>' is disabled in agent mode"` for any of `publish`, `build`, `search`, `analyze`, `rebuild`.
3. WHEN `mode` is `agent` and `agent.disable_human_commands` is `false` or absent, THE System SHALL execute human blog commands without modification.
4. THE InkConfig SHALL default `agent.disable_human_commands` to `false`.

---

### Requirement 8: Agent 模式初始化

**User Story:** As OpenClaw, I want `ink init` to support an agent mode flag, so that I can set up a new workspace pre-configured for agent use without manually editing config.

#### Acceptance Criteria

1. WHEN `ink init --mode agent --agent-name "<name>"` is executed, THE InitCommand SHALL write `mode: agent` and the `agent` block to `.ink/config.yaml` in addition to the standard init behavior.
2. WHEN `--agent-name` is omitted during agent-mode init, THE InitCommand SHALL use `"OpenClaw"` as the default `agent.agent_name`.
3. WHEN `ink init --mode agent` is executed in an already-initialised workspace, THE InitCommand SHALL update only the `mode` and `agent` fields in the existing config without overwriting other fields.
4. IF `--mode` is provided with a value other than `human` or `agent`, THEN THE InitCommand SHALL return a SkillResult with `success=false` and a descriptive error message.

---

### Requirement 9: 技能文件管理

**User Story:** As OpenClaw, I want to record installed external skills and save self-created skills to the workspace, so that my skill inventory is always accurate and self-created skills are version-controlled.

#### Acceptance Criteria

**外部安装技能（记录元数据，不复制文件）：**

1. WHEN `ink skill-record "<skill-name>" --source <url> --version <version> --path <install-path>` is executed in agent mode, THE System SHALL append a `skill-installed` Log_Entry to the current Daily_Journal containing the skill name, source URL, version, and install path.
2. THE skill metadata SHALL be stored in `_index/skills.json` as a JSON array, where each entry contains: `name` (string), `type` (value `"external"`), `source` (URL string), `version` (string), `install_path` (string), `installed_at` (ISO 8601 timestamp).
3. IF a skill with the same `name` already exists in `_index/skills.json`, THEN THE System SHALL update the existing entry rather than creating a duplicate.
4. THE `--source` flag SHALL be required for external skill recording; IF omitted, THE System SHALL return a SkillResult with `success=false` and message `"--source is required for external skill recording"`.
5. THE `--version` and `--path` flags SHALL be optional; WHEN omitted, THE System SHALL store empty strings for those fields.

**自创技能（保存文件到 `.ink/skills/`，纳入版本控制）：**

6. WHEN `ink skill-save "<skill-name>" --file <path-to-md>` is executed in agent mode, THE System SHALL copy the specified `.md` file to `.ink/skills/<skill-name>.md`.
7. WHEN `ink skill-save` succeeds, THE System SHALL register the skill in `_index/skills.json` with `type` set to `"custom"`, `source` set to `"local"`, and `install_path` set to `.ink/skills/<skill-name>.md`.
8. WHEN `ink skill-save` succeeds, THE System SHALL append a `skill-installed` Log_Entry to the current Daily_Journal recording the skill name and type `custom`.
9. IF the source file specified by `--file` does not exist, THEN THE System SHALL return a SkillResult with `success=false` and message `"Skill file not found: <path>"`.
10. IF the source file does not contain the required frontmatter fields (`skill`, `version`, `context_requirement`), THEN THE System SHALL return a SkillResult with `success=false` and message `"Invalid skill file: missing required fields: <fields>"`.
11. WHEN `git.auto_commit` is `true`, THE System SHALL trigger a Git commit after a successful `ink skill-save` with message `"skill: add <skill-name>"`.

**技能查询：**

12. WHEN `ink skill-list` is executed in agent mode, THE System SHALL read `_index/skills.json` and return a formatted list showing name, type (`external`/`custom`), version, and installed_at for each skill.
13. WHEN `ink recall --category skill-installed` is executed, THE Recall_Command SHALL return journal entries for all recorded skills (both external and custom).
14. THE `_index/skills.json` file SHALL be excluded from Git version control (added to `.gitignore`) since it is a derived index; only `.ink/skills/*.md` (custom skill definitions) SHALL be committed.
