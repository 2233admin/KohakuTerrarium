---
phase: 5c-workbench-tools
plan: 01
subsystem: studio
tags: [workbench, cost, record, compare, completion, diff, cli-extraction]
dependency_graph:
  requires: [studio-cli, studio-targets, studio-profiles]
  provides: [cost-tracker, session-recorder, compare-runner, shell-completion, profile-diff]
  affects: [cli.py, handlers.py, profiles.py]
tech_stack:
  added: []
  patterns: [handler-extraction, asyncio-gather-parallel, dataclass-serialization]
key_files:
  created:
    - src/kohakuterrarium/studio/handlers.py
    - src/kohakuterrarium/studio/cost.py
    - src/kohakuterrarium/studio/record.py
    - src/kohakuterrarium/studio/compare.py
    - src/kohakuterrarium/studio/completion.py
    - tests/unit/test_studio_workbench.py
  modified:
    - src/kohakuterrarium/studio/cli.py
    - src/kohakuterrarium/studio/profiles.py
    - tests/unit/test_studio.py
decisions:
  - Lazy imports for new module dispatch in handlers.py (cost/record/compare/completion/diff) to avoid circular deps and keep startup fast
  - Test patch targets updated from cli to handlers module (necessary consequence of extraction)
metrics:
  duration: ~10min
  completed: 2026-04-05
  tasks: 3
  files_created: 6
  files_modified: 3
  tests_added: 19
  total_tests: 187
---

# Phase 5c Plan 01: Workbench Tools Summary

Extracted handler dispatch from cli.py (598 -> 179 lines) into handlers.py, then implemented 5 workbench tools: cost tracker with 8-model pricing table, session recorder with JSONL capture, parallel compare runner via asyncio.gather, 4-shell completion generators, and profile diff via dataclasses.asdict comparison.

## Tasks Completed

### Task 1: Extract handlers.py from cli.py + add new subparser defs
- **Commit:** 128ed1d
- Moved all 15 handler functions + handle_studio_command dispatch to handlers.py (486 lines)
- cli.py reduced from 598 to 179 lines (subparser defs + re-export only)
- Added 6 new subparser definitions: cost, record, replay, compare, completion, diff
- handle_studio_command dispatch updated with 6 new cases

### Task 2: Implement 5 workbench modules (TDD)
- **RED commit:** aad8f06 -- 19 failing tests (ModuleNotFoundError)
- **GREEN commit:** d225f2e -- all 19 tests passing

Modules implemented:
- **cost.py** (145 lines): PRICING dict with 8 models, estimate_cost with graceful fallback for unknown models, scan_usage_logs scans ~/.claude/projects/ JSONL, cost_summary aggregates by period/target/model
- **record.py** (157 lines): RecordingEntry dataclass with to_dict, SessionRecorder wraps subprocess with async stdout capture to JSONL, replay with timing delays, meta entries at start/end
- **compare.py** (121 lines): CompareResult dataclass, CompareRunner uses asyncio.gather for parallel target execution, format_results produces aligned table, timeout handling
- **completion.py** (189 lines): bash/zsh/fish/powershell completion script generators, all include full subcommand list including new commands
- **profiles.py** (+49 lines): diff_profiles uses dataclasses.asdict for field-by-field comparison, handle_diff_command formats output table

### Task 3: Integration verification
- All 187 studio tests pass (168 existing + 19 new)
- cli.py at 179 lines (well under 600 limit)
- All new modules import cleanly
- Lint clean (ruff)
- 5 pre-existing failures in unrelated modules (bootstrap, packages, phase8, web_tools) -- out of scope

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated test patch targets after handler extraction**
- **Found during:** Task 1
- **Issue:** test_studio.py patched `kohakuterrarium.studio.cli.STUDIO_CONFIG_PATH` and `cli.save_studio_config`, but those names moved to handlers.py
- **Fix:** Updated 2 patch targets from `cli` to `handlers` in test_studio.py
- **Files modified:** tests/unit/test_studio.py
- **Commit:** 128ed1d

**2. [Rule 1 - Bug] Fixed async mock for subprocess stdout in test**
- **Found during:** Task 2 GREEN phase
- **Issue:** AsyncMock.__aiter__ returning plain iterator incompatible with `async for`
- **Fix:** Used async generator function for mock_proc.stdout
- **Files modified:** tests/unit/test_studio_workbench.py
- **Commit:** d225f2e

## Known Stubs

None -- all modules are fully wired with real implementations.

## Self-Check: PASSED

- All 6 created files exist on disk
- All 3 commits (128ed1d, aad8f06, d225f2e) found in git log
