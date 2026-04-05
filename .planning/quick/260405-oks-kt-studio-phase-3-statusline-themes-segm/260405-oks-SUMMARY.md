---
phase: quick
plan: 260405-oks
subsystem: studio
tags: [statusline, themes, cli, tdd]
dependency_graph:
  requires: [studio-p1 config/profiles/launcher, quick-01 sessions/cli]
  provides: [themes-registry, statusline-builder, cli-statusline-commands, cli-theme-commands]
  affects: [studio/cli.py, studio/config.py]
tech_stack:
  added: []
  patterns: [segment-registry, standalone-script-generation, match-case-dispatch]
key_files:
  created:
    - src/kohakuterrarium/studio/themes.py
    - src/kohakuterrarium/studio/statusline.py
    - tests/unit/test_studio_statusline.py
  modified:
    - src/kohakuterrarium/studio/cli.py
decisions:
  - "Theme colors stored as flat dicts (not ThemeColors dataclass instances) for easy serialization"
  - "Standalone script uses inline segment function templates, no external dependencies"
  - "theme_to_settings wraps in dark key for Claude Code compatibility"
metrics:
  duration: "6m 13s"
  completed: "2026-04-05"
  tasks: 3
  files: 4
  tests_added: 29
  tests_total: 104
---

# Quick Plan 260405-oks: kt studio Phase 3 -- Statusline + Themes Summary

6 built-in color themes with preview/convert, StatusLineBuilder generating standalone Python runner scripts with 6 segments and 3 styles, CLI subcommands for statusline install/preview/uninstall and theme list/show/apply.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create themes.py and statusline.py modules | 0637e6d | themes.py, statusline.py |
| 2 | Wire statusline + theme subcommands into CLI | 053bdf9 | cli.py |
| 3 | Test suite for themes + statusline | 3c4da3f | test_studio_statusline.py |

## Implementation Details

### themes.py (115 lines)
- `ThemeColors` dataclass with 10 color fields (primary, secondary, accent, background, surface, text, dimmed, success, warning, error)
- `BUILTIN_THEMES`: 6 themes -- dark, light, nord, tokyo-night, rose-pine, gruvbox
- `list_themes()`, `get_theme()`, `preview_theme()`, `theme_to_settings()`
- Rich markup preview with color swatches

### statusline.py (290 lines)
- 6 segment functions: git (branch+diff), tokens, cost, model, session, clock
- `SEGMENT_REGISTRY` dict mapping names to callables
- `render_segments()` with 3 styles: minimal (pipe), powerline (arrow), capsule (brackets)
- `StatusLineBuilder`: generates standalone Python scripts with no KT imports
  - `install()`: writes runner script + updates settings.json with statusLine.command
  - `uninstall()`: removes statusLine from settings + deletes runner
  - `preview()`: runs segments live and renders with configured style
  - `generate_script()`: embeds inline segment functions and theme colors

### cli.py additions (503 lines total)
- `kt studio statusline {install,preview,uninstall}` subcommands
- `kt studio theme {list,show,apply}` subcommands
- Both follow existing match-case dispatch pattern

## Verification Results

- 29 new tests: all passing
- 75 existing studio tests: all passing (no regressions)
- Import smoke test: 6 themes, builder OK
- CLI parse test: all subcommands recognized
- ruff lint: all checks passed
- black: formatted clean

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Restored missing studio module files from git history**
- **Found during:** Pre-task setup
- **Issue:** Studio files (config.py, cli.py, launcher.py, profiles.py, sessions.py, tests) existed in git commit 08b4f01 but were missing from HEAD working tree
- **Fix:** `git checkout 08b4f01 -- src/kohakuterrarium/studio/` to restore all prerequisite files
- **Files restored:** 6 source + 2 test files
- **Commit:** 668f5cb

## Known Stubs

None -- all functionality is wired end-to-end.

## Self-Check: PASSED
