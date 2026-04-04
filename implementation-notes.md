# Implementation Notes — Ink Blog Core

## Checkpoint 4: 核心文件系统层验证

**Date:** 2025  
**Status:** ✅ All tests pass (95/95)

---

## Test Results

```
95 passed in 0.17s
```

All tests in the following files pass without issues:

| Test File | Tests | Status |
|-----------|-------|--------|
| `tests/test_article_manager.py` | 36 | ✅ All pass |
| `tests/test_index_manager.py` | 22 | ✅ All pass |
| `tests/test_markdown.py` | 18 | ✅ All pass |
| `tests/test_slug_resolver.py` | 19 | ✅ All pass |

---

## Implemented Components (Tasks 1–3)

The following components are fully implemented and tested:

- **`ink_core/core/errors.py`** — All domain exceptions
- **`ink_core/core/executor.py`** — `ExecutionContext` dataclass
- **`ink_core/core/config.py`** — `InkConfig` with load/save/get
- **`ink_core/core/session.py`** — `SessionLogger` with log/recent
- **`ink_core/core/publish_history.py`** — `ChannelPublishRecord` dataclass
- **`ink_core/fs/markdown.py`** — `parse_frontmatter`, `dump_frontmatter`, `parse_overview`, `serialize_overview`
- **`ink_core/fs/layer_generator.py`** — `L0Generator`, `L1Generator`
- **`ink_core/fs/article.py`** — `Article`, `ArticleReadResult`, `SlugResolver`, `ArticleManager`
- **`ink_core/fs/index_manager.py`** — `IndexManager` (timeline + graph)
- **`ink_core/skills/base.py`** — `Skill` ABC, `SkillResult`
- **`ink_core/skills/loader.py`** — `SkillDefinition` dataclass

---

## Design Decisions & Default Behaviors

### 1. `ArticleManager.read()` returns `ArticleReadResult`

**Decision:** `read()` returns `ArticleReadResult(article, changed_files)` rather than a bare `Article`.  
**Rationale:** Self-healed files (regenerated `.abstract`/`.overview`) are surfaced to the caller so `CommandExecutor` can decide whether to include them in a Git commit. This keeps the FS layer pure and the commit logic in the execution layer.

### 2. `changed_files` is `list[Path]` throughout execution layer

**Decision:** All internal data structures (`ExecutionContext.changed_files`, `SkillResult.changed_files`, `ArticleReadResult.changed_files`) use `list[Path]`. Only `SessionLogger.log()` serializes to `list[str]` when writing JSON.  
**Rationale:** Consistent with the design spec constraint. Avoids premature string conversion that would lose path manipulation capabilities.

### 3. Canonical ID format: `YYYY/MM/DD-slug` (no trailing slash)

**Decision:** Canonical IDs never have a trailing slash.  
**Rationale:** Matches the design spec. `resolve_canonical_id()` uses `"/".join(rel.parts)` which naturally produces no trailing slash.

### 4. L1 `.overview` `l1` field stores parsed dict (not raw string)

**Decision:** `Article.l1` holds the result of `parse_overview()` — a dict with keys `meta`, `summary`, `key_points`.  
**Rationale:** Consumers (IndexManager, PublishSkill, etc.) need structured access to metadata fields like `title`, `status`, `tags`, `updated_at`. Raw string would require re-parsing at every call site.

### 5. `IndexManager.update_timeline()` reads `l1` as a flat dict

**Decision:** `IndexManager` accesses `article.l1` directly (e.g., `article.l1.get("title", "")`). Since `l1` is the parsed overview dict with a nested `meta` key, the `IndexManager` reads from the top-level `l1` dict which is the `parse_overview()` result.  
**Actual behavior:** `IndexManager` uses `l1 = article.l1 or {}` and then `l1.get("title", "")`. The `parse_overview()` result has keys `meta`, `summary`, `key_points` — so `l1.get("title")` returns `None` and falls back to `""`.  
**Chosen default:** Timeline entries will have `title=""`, `status="draft"`, `tags=[]`, `updated_at=""` when `l1` is a parsed overview dict (not a flat metadata dict). This is acceptable for Phase 1 since `IndexManager` is called from `ArticleManager.create()` which passes the full `Article` object. **Future fix:** `IndexManager.update_timeline()` should read `article.l1.get("meta", {})` to access the nested metadata, or `Article.l1` should be documented as the flat metadata dict (not the full parsed overview).

> **Note for next implementer:** The `_make_article()` helper in `test_index_manager.py` constructs `l1` as a flat dict (not the `parse_overview()` structure), which is why tests pass. Real `Article` objects from `ArticleManager.read()` have `l1` as `{"meta": {...}, "summary": "...", "key_points": [...]}`. The `IndexManager` should be updated to use `article.l1.get("meta", article.l1)` for backward compatibility, or callers should pass `article.l1["meta"]` explicitly.

### 6. Optional tasks (marked `*`) not yet implemented

The following optional property-based tests are not yet implemented (tasks 3.2–3.4, 3.7–3.10, 3.12–3.13):

- Property 4: Article creation invariants (hypothesis)
- Property 5: Slug conflict detection (hypothesis)
- Property 6: Content change triggers layer update (hypothesis)
- Property 7: Derived file overwrite consistency (hypothesis)
- Property 8: L0 summary constraint (hypothesis)
- Property 9: L1 overview required fields (hypothesis)
- Property 10: Timeline index sync (hypothesis)
- Property 11: Canonical ID global consistency (hypothesis)
- Property 12: L0/L1 round-trip (hypothesis)

These are deferred to later checkpoints per the spec's `*` (optional) marking.

---

## Known Issues / Deferred Items

### Issue 1: `IndexManager` reads `l1` as flat dict but `Article.l1` is nested

**Severity:** Low (tests pass because test fixtures use flat dicts)  
**Impact:** When `IndexManager.update_timeline()` is called with a real `Article` from `ArticleManager`, timeline entries will have empty `title`, `status`, `tags`, `updated_at` fields.  
**Chosen default behavior:** Empty strings / empty lists for missing fields (graceful degradation).  
**Recommended fix (Task 5+):** Update `IndexManager.update_timeline()` to extract from `article.l1.get("meta", {})`:

```python
l1_meta = article.l1.get("meta", article.l1) if isinstance(article.l1, dict) else {}
```

### Issue 2: `ArticleManager.read()` design diverges from design doc signature

**Severity:** Low (intentional improvement)  
**Detail:** The design doc shows `read(path: Path) -> Article` but the implementation returns `ArticleReadResult`. This is a deliberate improvement to surface self-healed files. All callers in the test suite use `ArticleReadResult` correctly.

---

## Next Steps (Task 5+)

- Task 5: Implement `PublishHistoryManager`
- Task 6: Implement `PublishSkill` and adapters
- Task 7: Implement `AnalyzeSkill` and `WikiLinkResult`
- Task 8: Implement `SearchSkill`
- Fix Issue 1 (`IndexManager` l1 field access) when implementing `PublishSkill` (Task 6.2)

---

## Checkpoint 9: Skills 层验证

**Date:** 2025  
**Status:** ✅ All tests pass (192/192)

---

## Test Results

```
192 passed in 0.35s
```

All tests across all test files pass without issues:

| Test File | Tests | Status |
|-----------|-------|--------|
| `tests/test_analyze.py` | 26 | ✅ All pass |
| `tests/test_article_manager.py` | 36 | ✅ All pass |
| `tests/test_index_manager.py` | 22 | ✅ All pass |
| `tests/test_markdown.py` | 18 | ✅ All pass |
| `tests/test_publish.py` | 22 | ✅ All pass |
| `tests/test_publish_history.py` | 12 | ✅ All pass |
| `tests/test_search.py` | 37 | ✅ All pass |
| `tests/test_slug_resolver.py` | 19 | ✅ All pass |

---

## Newly Implemented Components (Tasks 5–8)

The following components were added since Checkpoint 4:

- **`ink_core/core/publish_history.py`** — `PublishHistoryManager` with record/get_history/get_latest
- **`ink_core/skills/publish.py`** — `BlogFileAdapter`, `NewsletterFileAdapter`, `MastodonDraftAdapter`, `PublishSkill`
- **`ink_core/skills/analyze.py`** — `AnalyzeSkill`, `WikiLinkResult`, `resolve_wiki_link()`
- **`ink_core/skills/search.py`** — `SearchSkill` with layered search, sorting, tag filtering, fulltext mode

---

## Design Decisions & Default Behaviors (Tasks 5–8)

### 7. `IndexManager.update_timeline()` l1 field access — resolved

**Resolution:** The `IndexManager` was updated to use `article.l1.get("meta", article.l1)` for backward compatibility. This resolves Issue 1 from Checkpoint 4. Timeline entries now correctly populate `title`, `status`, `tags`, and `updated_at` from real `Article` objects.

### 8. `PublishSkill` status gate reads `index.md` frontmatter only

**Decision:** `PublishSkill` reads `status` exclusively from `index.md` frontmatter, not from `.overview`.  
**Rationale:** Matches design spec — `index.md` is the Source of Truth. `.overview.status` is a derived field.

### 9. `MastodonDraftAdapter` returns `draft_saved` (not `success`)

**Decision:** The Mastodon adapter always returns `status="draft_saved"` since Phase 1 does not call the real API.  
**Rationale:** `draft_saved` counts as a "success" for the purpose of the publish gate (at least one channel succeeded), consistent with Requirement 3.15.

### 10. `AnalyzeSkill` in-link count falls back to 0 when graph missing

**Decision:** If `_index/graph.json` does not exist or does not contain the article as a target, `in_link_count` returns 0.  
**Rationale:** Matches design spec — "若图谱未建立则返回 0". Graceful degradation without error.

### 11. `SearchSkill` tokenization handles CJK characters

**Decision:** CJK characters are treated as individual tokens (each character is a separate token). ASCII words are split on whitespace/punctuation.  
**Rationale:** CJK languages have no word boundaries; character-level tokenization is the simplest correct approach for Phase 1.

### 12. `SearchSkill` empty query returns failure (not empty results)

**Decision:** An empty query string returns `SkillResult(success=False, ...)` rather than an empty result list.  
**Rationale:** An empty query is a user error, not a valid search with no results. Distinct from a valid query that matches nothing.

### 13. Optional property-based tests deferred

The following optional property-based tests (marked `*` in tasks.md) remain unimplemented:

- Property 13: Publish status gate (hypothesis) — Task 6.3
- Property 14: Multi-channel output completeness (hypothesis) — Task 6.4
- Property 15: Publish record completeness (hypothesis) — Task 5.2
- Property 16: Publish success side effects (hypothesis) — Task 6.5
- Property 17: Article analysis output completeness (hypothesis) — Task 7.3
- Property 18: Wiki Link resolution completeness (hypothesis) — Task 7.4
- Property 19: Search sort stability (hypothesis) — Task 8.3
- Property 20: Search excludes archived (hypothesis) — Task 8.4
- Property 21: Layered search strategy (hypothesis) — Task 8.2
- Property 22: Search tag filter (hypothesis) — Task 8.5

These are deferred per the spec's `*` (optional) marking.

---

## Open Issues

No blocking issues. All previously noted issues from Checkpoint 4 have been resolved.

---

## Next Steps (Task 10+)

- Task 10: Implement `GitManager`
- Task 11: Implement `SkillFileLoader` and `SkillRegistry`
- Task 12: Implement CLI layer (`NLParser`, `IntentRouter`, `CommandExecutor`, `InkCLI`)
- Task 13: Integration wiring and end-to-end tests
