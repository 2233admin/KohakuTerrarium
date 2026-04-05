---
phase: quick
plan: 260405-p5r
subsystem: studio
tags: [copilot, cli, patch-driver]
dependency_graph:
  requires: [260405-nm0, 260405-o7l, 260405-oks]
  provides: [copilot-cli-management, copilot-model-switching, copilot-ast-patch]
  affects: [studio-cli]
tech_stack:
  added: []
  patterns: [shutil.which, subprocess.run, json-config, match-case-dispatch]
key_files:
  created:
    - src/kohakuterrarium/studio/copilot.py
    - tests/unit/test_studio_copilot.py
  modified:
    - src/kohakuterrarium/studio/cli.py
decisions:
  - JSON config at ~/.copilot/config.json (not YAML -- matches Copilot CLI convention)
  - Env var COPILOT_MODEL takes priority over config file
  - 9 hardcoded known models (gpt-4o, gpt-4.1, gpt-4.1-mini, o3-mini, o4-mini, claude-sonnet-4, claude-sonnet-4-20250514, gemini-2.5-pro, gemini-2.5-flash)
  - PatchDriver uses meriyah+astring AST rewriting via Node.js subprocess
metrics:
  duration: 4m7s
  completed: 2026-04-05
  tasks: 2/2
  tests: 21 new (125 total studio)
  lines: ~200 (copilot.py) + ~50 (cli.py additions) + ~170 (tests)
---

# Phase 4 Plan 260405-p5r: Copilot CLI Integration Summary

Copilot CLI management module with model switching, status checks, and opt-in AST patch driver via Node.js subprocess -- 21 tests, all 125 studio tests green.

## Task Summary

| # | Task | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | copilot.py module + 21-test suite (TDD) | 883dcbc | find_copilot_cli, get/set_model, copilot_status, PatchDriver, 21 tests |
| 2 | Wire copilot subcommands into CLI | 171e9f8 | Import + subparser + dispatch + _handle_copilot_subcommand |

## What Was Built

**copilot.py** (~200 lines):
- `find_copilot_cli()` -- locates github-copilot-cli via shutil.which + Windows fallback
- `get_copilot_version()` -- subprocess --version capture
- `get_current_model()` -- env var priority, then JSON config file
- `set_model()` -- writes/updates ~/.copilot/config.json preserving existing keys
- `list_available_models()` -- returns copy of 9 known models
- `copilot_status()` -- aggregated status dict (installed, version, model, config_path)
- `PatchDriver` class -- detect_install, is_patched, apply_patch (Node.js + meriyah/astring), unpatch (restore from .bak)

**cli.py** (+50 lines):
- `kt studio copilot status` -- display Copilot CLI status + patch state
- `kt studio copilot model <name>` -- set active model (warns if unknown)
- `kt studio copilot models` -- list all known models
- `kt studio copilot patch` -- apply AST patch for extended model support
- `kt studio copilot unpatch` -- restore original bundle from backup

## Verification

- 21 new copilot tests pass (find, version, model get/set, status, PatchDriver graceful degradation)
- 125 total studio tests pass (0 regressions)
- ruff lint clean on all studio modules
- CLI parser accepts all 5 copilot subcommands
- Module imports cleanly

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None -- all functions fully implemented with graceful degradation when dependencies missing.
