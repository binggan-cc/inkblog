# Implementation Plan: OpenClaw Agent Mode

## Overview

Extend `ink-blog-core` with an AI Agent mode: new `ink_core/agent/` subpackage, config extensions,
five new CLI commands (`log`, `recall`, `serve`, `skill-record`, `skill-save`, `skill-list`),
and an optional HTTP API. All data remains on the local filesystem (FS-as-DB).

## Tasks

- [ ] 1. Set up agent package structure and core data models
  - Create `ink_core/agent/__init__.py` and `ink_core/agent/commands/__init__.py`
  - Define `LogEntry` dataclass (`date`, `time`, `category`, `content`, `source`) in `ink_core/agent/__init__.py`
  - Define `SkillRecord` dataclass (`name`, `type`, `source`, `version`, `install_path`, `installed_at`) in `ink_core/agent/__init__.py`
  - Define `VALID_CATEGORIES` constant: `["work", "learning", "skill-installed", "memory", "note"]`
  - Create `tests/agent/__init__.py` and `tests/integration/__init__.py`
  - _Requirements: 2.2, 5.1, 9.2_

- [ ] 2. Extend InkConfig and errors with agent mode support
  - [ ] 2.1 Add `AgentModeError` to `ink_core/core/errors.py`
    - New exception class: `class AgentModeError(Exception): ...`
    - _Requirements: 1.6_

  - [ ] 2.2 Extend `InkConfig` in `ink_core/core/config.py`
    - Add `mode: human` and full `agent` block to `DEFAULT_CONFIG`
    - Add `validate_mode()` method: raises `ConfigError` for any value not in `{"human", "agent"}`
    - Call `validate_mode()` at the end of `load()`
    - Default `agent.default_category` to `"note"`, `agent.disable_human_commands` to `False`
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 1.6_

  - [ ]* 2.3 Write property test for InkConfig mode validation (Property 11)
    - **Property 11: Invalid mode config rejected**
    - **Validates: Requirements 1.6**
    - File: `tests/agent/test_config_agent.py`

  - [ ]* 2.4 Write property test for agent init config write+preserve (Property 12)
    - **Property 12: Agent init config write+preserve**
    - **Validates: Requirements 8.1, 8.3**
    - File: `tests/agent/test_config_agent.py`

- [ ] 3. Implement JournalManager
  - [ ] 3.1 Implement `JournalManager` in `ink_core/agent/journal.py`
    - `__init__(self, workspace_root: Path, config: InkConfig)`
    - `get_or_create_journal(date: str) -> tuple[Path, bool]`: creates `YYYY/MM/DD-journal/index.md` with correct YAML frontmatter (`title`, `date`, `status: draft`, `tags: [journal, agent]`, `agent`) and `## Entries` section; delegates to `ArticleManager` for `.abstract`/`.overview` creation
    - `append_entry(date: str, category: str, content: str) -> LogEntry`: normalises category to lowercase, formats entry as `\n## HH:MM [category]\n\n<content>\n`, appends to `index.md`
    - `parse_entries(journal_path: Path) -> list[LogEntry]`: parses all `## HH:MM [category]` blocks from `index.md`
    - `list_journal_paths(since: str | None = None) -> list[Path]`: globs `*/*/??-journal/index.md`, filters by date
    - _Requirements: 2.1, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ]* 3.2 Write property test for Log_Entry format (Property 2)
    - **Property 2: Log_Entry format correctness**
    - **Validates: Requirements 2.4, 2.6**
    - File: `tests/agent/test_journal_manager.py`

  - [ ]* 3.3 Write property test for Daily Journal creation completeness (Property 3)
    - **Property 3: Daily Journal creation completeness**
    - **Validates: Requirements 3.1, 3.2, 3.4**
    - File: `tests/agent/test_journal_manager.py`

- [ ] 4. Implement RecallEngine
  - [ ] 4.1 Implement `RecallEngine` in `ink_core/agent/recall.py`
    - `score_entry(entry: LogEntry, query: str) -> int`: exact word match scores higher than partial; count of keyword occurrences adds to score
    - `search(entries, query, *, category, since, limit) -> list[LogEntry]`: filter by category (if given), filter by since date (if given), score all entries, sort by score desc then date desc then time desc, return top `limit`
    - _Requirements: 4.3, 4.4, 4.5, 4.7_

  - [ ]* 4.2 Write property test for Recall result schema (Property 4)
    - **Property 4: Recall result schema compliance**
    - **Validates: Requirements 4.1, 4.2, 4.8**
    - File: `tests/agent/test_recall_engine.py`

  - [ ]* 4.3 Write property test for Recall category filter (Property 5)
    - **Property 5: Recall category filter correctness**
    - **Validates: Requirements 4.3, 5.3**
    - File: `tests/agent/test_recall_engine.py`

  - [ ]* 4.4 Write property test for Recall date filter (Property 6)
    - **Property 6: Recall date filter correctness**
    - **Validates: Requirements 4.4**
    - File: `tests/agent/test_recall_engine.py`

  - [ ]* 4.5 Write property test for Recall limit constraint (Property 7)
    - **Property 7: Recall limit constraint**
    - **Validates: Requirements 4.5**
    - File: `tests/agent/test_recall_engine.py`

  - [ ]* 4.6 Write property test for invalid limit rejected (Property 8)
    - **Property 8: Invalid limit rejected**
    - **Validates: Requirements 4.6**
    - File: `tests/agent/test_recall_engine.py`

- [ ] 5. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement LogCommand
  - [ ] 6.1 Implement `LogCommand` in `ink_core/agent/commands/log_command.py`
    - Guard: if `config.get("mode") != "agent"` return `SkillResult(success=False, message="ink log requires agent mode. Set mode: agent in .ink/config.yaml")`
    - Validate `--category` param; if invalid return `SkillResult(success=False)` listing valid categories
    - Call `JournalManager.append_entry()`; populate `changed_files` with journal path
    - If `git.auto_commit` is true, call `GitManager` with commit message `"log: HH:MM [category] <first 60 chars>"`
    - Return `SkillResult(success=True, message=<appended entry text>, changed_files=[path])`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.7, 2.8, 2.9_

  - [ ]* 6.2 Write property test for category case normalisation (Property 9)
    - **Property 9: Category case normalisation**
    - **Validates: Requirements 5.2**
    - File: `tests/agent/test_log_command.py`

  - [ ]* 6.3 Write property test for invalid category rejected (Property 10)
    - **Property 10: Invalid category rejected**
    - **Validates: Requirements 2.3**
    - File: `tests/agent/test_log_command.py`

- [ ] 7. Implement RecallCommand
  - [ ] 7.1 Implement `RecallCommand` in `ink_core/agent/commands/recall_command.py`
    - Guard: if `config.get("mode") != "agent"` return `SkillResult(success=False, message="ink recall requires agent mode. Set mode: agent in .ink/config.yaml")`
    - Validate `--limit` in [1, 500]; if invalid return `SkillResult(success=False)` with range message
    - Collect all entries via `JournalManager.list_journal_paths()` + `parse_entries()`
    - Call `RecallEngine.search()` with query, category, since, limit params
    - Serialise to `RecallResult` JSON: print to stdout (for CLI/machine consumers) AND store in `SkillResult.data` (for programmatic callers)
    - Return `SkillResult(success=True, data=recall_result_dict)`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.8, 4.9_

  - [ ]* 7.2 Write property test for log round-trip (Property 1)
    - **Property 1: Log round-trip**
    - **Validates: Requirements 2.1, 2.4, 2.6, 4.10**
    - File: `tests/agent/test_recall_command.py`

- [ ] 8. Implement SkillIndexManager
  - [ ] 8.1 Implement `SkillIndexManager` in `ink_core/agent/skill_index.py`
    - `__init__(self, workspace_root: Path)`: index path is `workspace_root / "_index" / "skills.json"`
    - `upsert(skill: SkillRecord) -> None`: load existing list, replace entry with same `name` or append, write back
    - `list_all() -> list[SkillRecord]`: read and deserialise `skills.json`; return `[]` if file absent
    - _Requirements: 9.2, 9.3_

  - [ ]* 8.2 Write property test for skill upsert no duplicates (Property 13)
    - **Property 13: Skill upsert no duplicates**
    - **Validates: Requirements 9.3**
    - File: `tests/agent/test_skill_index.py`

  - [ ]* 8.3 Write property test for skill frontmatter validation (Property 14)
    - **Property 14: Skill frontmatter validation**
    - **Validates: Requirements 9.10**
    - File: `tests/agent/test_skill_index.py`

- [ ] 9. Implement SkillRecordCommand and SkillSaveCommand
  - [ ] 9.1 Implement `SkillRecordCommand` in `ink_core/agent/commands/skill_record_command.py`
    - Guard: agent mode check
    - Require `--source`; return `SkillResult(success=False)` if missing
    - Build `SkillRecord(type="external", ...)` with optional `--version` and `--path`
    - Call `SkillIndexManager.upsert()`
    - Call `JournalManager.append_entry()` with category `"skill-installed"`
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ] 9.2 Implement `SkillSaveCommand` in `ink_core/agent/commands/skill_save_command.py`
    - Guard: agent mode check
    - Validate source file exists; return `SkillResult(success=False, message="Skill file not found: <path>")` if not
    - Parse frontmatter; validate `skill`, `version`, `context_requirement` fields; return `SkillResult(success=False)` listing missing fields
    - Copy file to `.ink/skills/<skill-name>.md`
    - Build `SkillRecord(type="custom", source="local", install_path=".ink/skills/<name>.md", ...)`
    - Call `SkillIndexManager.upsert()` and `JournalManager.append_entry(category="skill-installed")`
    - If `git.auto_commit`, commit with message `"skill: add <skill-name>"`
    - _Requirements: 9.6, 9.7, 9.8, 9.9, 9.10, 9.11_

  - [ ] 9.3 Implement `SkillListCommand` in `ink_core/agent/commands/skill_list_command.py`
    - Guard: agent mode check; return `SkillResult(success=False)` if not agent mode
    - Call `SkillIndexManager.list_all()`
    - Format and print each skill: name, type (`external`/`custom`), version, installed_at
    - Return `SkillResult(success=True, data={"skills": [<SkillRecord dicts>]})`
    - _Requirements: 9.12_

- [ ] 10. Extend InitCommand for agent mode
  - Modify `InitCommand.run()` in `ink_core/cli/builtin.py` to handle `--mode` and `--agent-name` params
  - If `--mode` value is not `human` or `agent`, return `SkillResult(success=False)` with descriptive message
  - If workspace already initialised, deep-merge only `mode` and `agent` fields into existing config
  - Default `agent_name` to `"OpenClaw"` when `--agent-name` is omitted
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ] 11. Implement human command compatibility guard
  - Modify `IntentRouter` or the relevant dispatch path in `ink_core/cli/intent.py` (or `parser.py`) to intercept `publish`, `build`, `search`, `analyze`, `rebuild` when `mode=agent` and `disable_human_commands=true`
  - Return `SkillResult(success=False, message="Command '<name>' is disabled in agent mode")`
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [ ]* 11.1 Write property test for disable_human_commands intercept (Property 15)
    - **Property 15: disable_human_commands intercept**
    - **Validates: Requirements 7.2**
    - File: `tests/agent/test_human_compat.py`

- [ ] 12. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Implement ServeCommand (HTTP API)
  - [ ] 13.1 Implement `ServeCommand` in `ink_core/agent/commands/serve_command.py`
    - Guard: agent mode check; return error if `mode != agent`
    - Check `agent.http_api.enabled`; if false return `SkillResult(success=False, message="HTTP API is disabled. Set agent.http_api.enabled: true in config")`
    - Start HTTP server on configured port (default 4242) using `http.server` or `flask`
    - Route `POST /log` → `LogCommand.run()`
    - Route `POST /recall` → `RecallCommand.run()`
    - Route `GET /health` → `{"status": "ok", "mode": "agent", "agent_name": <name>}`
    - Return HTTP 400 with `{"error": "<field> is required"}` for missing required fields
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

  - [ ]* 13.2 Write integration tests for HTTP API endpoints
    - Test `POST /log`, `POST /recall`, `GET /health` happy paths
    - Test HTTP 400 for missing required fields
    - Test `ink serve` refused when `mode != agent`
    - File: `tests/integration/test_http_api.py`
    - _Requirements: 6.1–6.7_

- [ ] 14. Register new commands in CLI parser
  - Modify `ink_core/cli/parser.py` to register `LogCommand`, `RecallCommand`, `ServeCommand`, `SkillRecordCommand`, `SkillSaveCommand`, and a `skill-list` subcommand
  - Wire `--category`, `--since`, `--limit`, `--source`, `--version`, `--path`, `--file`, `--mode`, `--agent-name` flags to the appropriate commands
  - Expose valid `Entry_Category` values in `ink log --help` output
  - Add `_index/skills.json` to `.gitignore`
  - _Requirements: 2.2, 4.3, 4.4, 4.5, 5.4, 8.1, 9.12, 9.14_

- [ ] 15. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property tests use `@given` + `@settings(max_examples=100)` from `hypothesis`
- `ServeCommand` blocks the process; users should run `ink serve` manually in a terminal
- `_index/skills.json` is a derived index and must be in `.gitignore`; only `.ink/skills/*.md` is committed
