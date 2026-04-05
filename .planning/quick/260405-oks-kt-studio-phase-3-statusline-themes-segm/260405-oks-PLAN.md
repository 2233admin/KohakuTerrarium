---
phase: quick
plan: 260405-oks
type: execute
wave: 1
depends_on: []
files_modified:
  - src/kohakuterrarium/studio/themes.py
  - src/kohakuterrarium/studio/statusline.py
  - src/kohakuterrarium/studio/cli.py
  - tests/unit/test_studio_statusline.py
autonomous: true
requirements: [statusline-segments, themes-builtin, cli-commands]

must_haves:
  truths:
    - "6 built-in themes are available and queryable by name"
    - "StatusLineBuilder generates a standalone Python script with no KT imports"
    - "Segments (git, tokens, cost, model, session, clock) each produce a string"
    - "Three styles (minimal, powerline, capsule) format segments differently"
    - "CLI subcommands for statusline install/preview/uninstall and theme list/show/apply work"
    - "Install writes statusLine.command into Claude Code settings.json"
  artifacts:
    - path: "src/kohakuterrarium/studio/themes.py"
      provides: "Theme registry, 6 built-in themes, preview/convert functions"
      exports: ["ThemeColors", "BUILTIN_THEMES", "list_themes", "get_theme", "preview_theme", "theme_to_settings"]
    - path: "src/kohakuterrarium/studio/statusline.py"
      provides: "StatusLineBuilder, segment registry, style rendering"
      exports: ["StatusLineBuilder", "SEGMENT_REGISTRY", "render_segments"]
    - path: "tests/unit/test_studio_statusline.py"
      provides: "16 test cases covering themes + statusline"
      min_lines: 180
  key_links:
    - from: "src/kohakuterrarium/studio/statusline.py"
      to: "src/kohakuterrarium/studio/config.py"
      via: "StatuslineConfig dataclass import"
      pattern: "from kohakuterrarium.studio.config import StatuslineConfig"
    - from: "src/kohakuterrarium/studio/cli.py"
      to: "src/kohakuterrarium/studio/themes.py"
      via: "theme subcommand imports"
      pattern: "from kohakuterrarium.studio.themes import"
    - from: "src/kohakuterrarium/studio/cli.py"
      to: "src/kohakuterrarium/studio/statusline.py"
      via: "statusline subcommand imports"
      pattern: "from kohakuterrarium.studio.statusline import"
---

<objective>
Add status line generation and theme management to kt studio.

Purpose: Enable users to customize Claude Code's status bar with configurable segments (git, model, tokens, cost, session, clock) in three styles (minimal, powerline, capsule), and apply one of 6 built-in color themes.

Output: Two new modules (themes.py, statusline.py), CLI subcommands wired in cli.py, and a comprehensive test suite.
</objective>

<execution_context>
@C:/Users/Administrator/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Administrator/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@D:/projects/KohakuTerrarium/CLAUDE.md
@D:/projects/KohakuTerrarium/src/kohakuterrarium/studio/config.py
@D:/projects/KohakuTerrarium/src/kohakuterrarium/studio/cli.py
@D:/projects/KohakuTerrarium/src/kohakuterrarium/studio/launcher.py

<interfaces>
<!-- Executor needs these existing types and patterns -->

From src/kohakuterrarium/studio/config.py:
```python
@dataclass
class StatuslineConfig:
    segments: list[str] = field(default_factory=lambda: ["git", "model"])
    style: str = "minimal"

@dataclass
class ProfileConfig:
    theme: str | None = None
    statusline: StatuslineConfig | None = None
    # ... other fields

KT_DIR = Path.home() / ".kohakuterrarium"
```

From src/kohakuterrarium/studio/launcher.py:
```python
CLAUDE_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"

class ProfileLauncher:
    def build_settings_json(self) -> dict[str, Any]:
        # statusline -> userStatusBar
        if profile.statusline:
            base["userStatusBar"] = {
                "segments": profile.statusline.segments,
                "style": profile.statusline.style,
            }
```

From src/kohakuterrarium/utils/logging.py:
```python
def get_logger(name: str) -> logging.Logger: ...
```

CLI dispatch pattern (from cli.py):
- add_studio_subparser registers argparse subcommands
- handle_studio_command uses match-case dispatch
- Each subcommand handler is a private function returning int (0=ok, 1=error)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create themes.py and statusline.py modules</name>
  <files>
    src/kohakuterrarium/studio/themes.py
    src/kohakuterrarium/studio/statusline.py
  </files>
  <behavior>
    - list_themes() returns exactly 6 names: dark, light, nord, tokyo-night, rose-pine, gruvbox
    - get_theme("nord") returns a dict with color keys (primary, secondary, accent, background, surface, text)
    - get_theme("nonexistent") returns None
    - preview_theme("dark") returns a non-empty string (Rich markup)
    - theme_to_settings("nord") returns a dict with a "theme" key containing Claude Code-compatible format
    - render_segments(["main +1", "sonnet"], "minimal") produces "main +1 | sonnet"
    - render_segments(["main", "sonnet"], "powerline") includes arrow separator chars
    - render_segments(["main", "sonnet"], "capsule") wraps each in brackets like "[main] [sonnet]"
    - Each segment function (git, tokens, cost, model, session, clock) returns a string
    - segment_clock returns HH:MM pattern
    - segment_model reads MODEL env var
    - StatusLineBuilder.generate_script() produces valid Python source (passes compile())
    - StatusLineBuilder.generate_script() output contains no "from kohakuterrarium" imports
    - StatusLineBuilder.install() writes statusLine.command to settings.json
    - StatusLineBuilder.uninstall() removes statusLine.command from settings.json
    - StatusLineBuilder with a theme_name passes theme colors into generated script
  </behavior>
  <action>
**themes.py** (~150 lines):

1. Create `ThemeColors` dataclass with fields: primary, secondary, accent, background, surface, text, dimmed, success, warning, error (all str, hex color values).

2. Define 6 built-in themes as dicts in `BUILTIN_THEMES: dict[str, dict[str, str]]`:
   - `dark`: deep gray bg (#1a1a2e), blue accent (#0f3460), light text (#e0e0e0)
   - `light`: white bg (#fafafa), blue accent (#1976d2), dark text (#212121)
   - `nord`: Arctic palette -- bg #2e3440, accent #88c0d0, text #eceff4
   - `tokyo-night`: bg #1a1b26, accent #7aa2f7, text #c0caf5
   - `rose-pine`: bg #191724, accent #ebbcba, text #e0def4
   - `gruvbox`: bg #282828, accent #fe8019, text #ebdbb2

3. `list_themes() -> list[str]`: return sorted(BUILTIN_THEMES.keys())

4. `get_theme(name: str) -> dict[str, str] | None`: lookup in BUILTIN_THEMES

5. `preview_theme(name: str) -> str`: use Rich markup to show color swatches -- for each color key, produce a line with the color name and a colored block using `[on {hex}]   [/]` syntax. Return the composed string (caller prints it).

6. `theme_to_settings(name: str) -> dict`: convert theme to Claude Code settings.json `"theme"` format: `{"theme": {"dark": {color_key: hex_value, ...}}}`. Return empty dict if theme not found.

**statusline.py** (~250 lines):

1. Import `StatuslineConfig` from `kohakuterrarium.studio.config` and `get_logger` from utils.

2. Segment functions -- each takes no args, returns str. Use subprocess/os/datetime internally:
   - `_segment_git()`: run `git rev-parse --abbrev-ref HEAD` + `git diff --shortstat`, return "branch +N-M" or "no-git"
   - `_segment_tokens()`: read env var `CLAUDE_TOKEN_COUNT` or return ""
   - `_segment_cost()`: read env `CLAUDE_TOKEN_COUNT`, estimate cost (rough: tokens * 0.000003), return "$X.XX" or ""
   - `_segment_model()`: read env `CLAUDE_MODEL` or return ""
   - `_segment_session()`: read env `CLAUDE_SESSION_ID`, return first 8 chars or ""
   - `_segment_clock()`: return `datetime.now().strftime("%H:%M")`

3. `SEGMENT_REGISTRY: dict[str, Callable[[], str]]` mapping "git" -> _segment_git, etc.

4. `render_segments(segments: list[str], style: str) -> str`:
   - Filter out empty segments
   - "minimal": join with " | "
   - "powerline": join with " \ue0b0 " (powerline arrow)
   - "capsule": wrap each in brackets "[seg]", join with " "
   - Default to minimal for unknown style

5. `class StatusLineBuilder`:
   - `__init__(self, config: StatuslineConfig, theme_name: str | None = None)`
   - `generate_script(self) -> str`: produce a self-contained Python script as a string. The script:
     - Has `#!/usr/bin/env python3` shebang
     - Imports only stdlib (subprocess, os, datetime, sys)
     - Defines inline versions of the segment functions for each segment in config.segments
     - Defines the render function for config.style
     - If theme_name provided, embeds ANSI color codes from the theme
     - Calls everything in `if __name__ == "__main__": print(result)`
   - `install(self, settings_path: Path | None = None) -> None`:
     - Generate script, write to `~/.kohakuterrarium/studio/statusline_runner.py`
     - Read settings.json (from settings_path or CLAUDE_SETTINGS_PATH)
     - Set `settings["statusLine"] = {"command": "python PATH/statusline_runner.py"}`
     - Write settings.json back
   - `uninstall(self, settings_path: Path | None = None) -> None`:
     - Read settings.json, remove "statusLine" key, write back
     - Delete runner script if exists
   - `preview(self) -> str`: run each segment function from SEGMENT_REGISTRY for the configured segments, pass through render_segments, return result

Use `get_logger(__name__)` for logging, no print() in library code. Use match-case for style dispatch. Python 3.10+ type hints throughout.
  </action>
  <verify>
    <automated>cd D:/projects/KohakuTerrarium && python -c "from kohakuterrarium.studio.themes import list_themes, get_theme, theme_to_settings; assert len(list_themes()) == 6; assert get_theme('nord') is not None; assert get_theme('nope') is None; print('themes OK')" && python -c "from kohakuterrarium.studio.statusline import StatusLineBuilder, render_segments; from kohakuterrarium.studio.config import StatuslineConfig; r = render_segments(['a','b'], 'minimal'); assert '|' in r; cfg = StatuslineConfig(segments=['clock','model'], style='minimal'); b = StatusLineBuilder(cfg); s = b.generate_script(); compile(s, '<test>', 'exec'); assert 'kohakuterrarium' not in s; print('statusline OK')"</automated>
  </verify>
  <done>
    - themes.py exports ThemeColors, BUILTIN_THEMES (6 themes), list_themes, get_theme, preview_theme, theme_to_settings
    - statusline.py exports StatusLineBuilder, SEGMENT_REGISTRY (6 segments), render_segments
    - generate_script() produces valid standalone Python with no KT imports
    - Three styles produce distinct formatting
  </done>
</task>

<task type="auto">
  <name>Task 2: Wire statusline + theme subcommands into CLI</name>
  <files>
    src/kohakuterrarium/studio/cli.py
  </files>
  <action>
Add two new subcommand groups to `add_studio_subparser` and two handler functions. Follow the exact pattern used by existing "profile" and "session" subcommands.

**In `add_studio_subparser`**, after the session subparser block, add:

1. **statusline subparser**:
   ```
   statusline_p = studio_sub.add_parser("statusline", help="Manage status line")
   statusline_sub = statusline_p.add_subparsers(dest="statusline_action")
   ```
   - `install`: no extra args (uses active profile's statusline config)
   - `preview`: no extra args
   - `uninstall`: no extra args

2. **theme subparser**:
   ```
   theme_p = studio_sub.add_parser("theme", help="Manage themes")
   theme_sub = theme_p.add_subparsers(dest="theme_action")
   ```
   - `list`: no extra args
   - `show <name>`: positional arg `name`
   - `apply <name>`: positional arg `name`, optional `--profile` flag

**In `handle_studio_command`**, add two new match arms:
   - `case "statusline": return _handle_statusline_subcommand(args)`
   - `case "theme": return _handle_theme_subcommand(args)`

Update the default case usage string to include statusline and theme.

**Add `_handle_statusline_subcommand(args) -> int`**:
   - match on `args.statusline_action`
   - `"install"`: load config, get active profile, if profile.statusline is None create default StatuslineConfig, build StatusLineBuilder with profile's theme, call install(), print success
   - `"preview"`: same setup, call preview(), print result
   - `"uninstall"`: build StatusLineBuilder with default config, call uninstall(), print success
   - default: print usage

**Add `_handle_theme_subcommand(args) -> int`**:
   - match on `args.theme_action`
   - `"list"`: call list_themes(), print each name (mark active if matches profile.theme)
   - `"show"`: call preview_theme(args.name), print result. If None, print error + return 1
   - `"apply"`: call get_theme(args.name) to validate exists, then load config, set profile.theme = args.name, save config, print confirmation
   - default: print usage

**Imports to add at top of cli.py**:
```python
from kohakuterrarium.studio.statusline import StatusLineBuilder
from kohakuterrarium.studio.themes import (
    get_theme,
    list_themes,
    preview_theme,
)
```
  </action>
  <verify>
    <automated>cd D:/projects/KohakuTerrarium && python -c "from kohakuterrarium.studio.cli import add_studio_subparser; import argparse; p = argparse.ArgumentParser(); s = p.add_subparsers(); add_studio_subparser(s); ns = p.parse_args(['studio', 'theme', 'list']); assert ns.studio_command == 'theme'; assert ns.theme_action == 'list'; ns2 = p.parse_args(['studio', 'statusline', 'preview']); assert ns2.statusline_action == 'preview'; print('CLI wiring OK')"</automated>
  </verify>
  <done>
    - `kt studio statusline {install,preview,uninstall}` subcommands parse and dispatch correctly
    - `kt studio theme {list,show,apply}` subcommands parse and dispatch correctly
    - All handlers follow existing pattern: load config, call module function, print result, return 0/1
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Test suite for themes + statusline</name>
  <files>
    tests/unit/test_studio_statusline.py
  </files>
  <behavior>
    - test_list_themes_returns_6: len(list_themes()) == 6
    - test_get_theme_valid: get_theme("nord") returns dict with "background" key
    - test_get_theme_invalid: get_theme("nonexistent") is None
    - test_preview_theme_returns_string: preview_theme("dark") is non-empty str
    - test_preview_theme_invalid: preview_theme("nope") returns empty or handles gracefully
    - test_theme_to_settings_valid: theme_to_settings("gruvbox") has "theme" key with nested dict
    - test_theme_to_settings_invalid: theme_to_settings("nope") returns empty dict
    - test_segment_clock_format: matches r"\d{2}:\d{2}"
    - test_segment_model_from_env: with CLAUDE_MODEL="opus" in env, returns "opus"
    - test_segment_git_mocked: with mocked subprocess, returns branch string
    - test_render_minimal: " | " separator
    - test_render_powerline: arrow char separator
    - test_render_capsule: bracket wrapping
    - test_render_empty_segments_filtered: empty strings removed before joining
    - test_generate_script_compiles: compile(script, ..., "exec") succeeds
    - test_generate_script_no_kt_imports: "kohakuterrarium" not in script
    - test_install_writes_settings: statusLine.command appears in settings.json
    - test_uninstall_removes_settings: statusLine key removed from settings.json
    - test_preview_returns_string: preview() returns non-empty str
    - test_builder_with_theme: StatusLineBuilder(config, theme_name="nord") generates script containing theme color reference
  </behavior>
  <action>
Create `tests/unit/test_studio_statusline.py` following the existing test_studio_sessions.py patterns:

- Use `pytest` and `unittest.mock.patch`
- Use `tmp_path` fixture for temp settings.json files
- Group tests into sections with `# -- Themes --` and `# -- Statusline --` comments
- For git segment: mock `subprocess.run` to return fake branch/diff output
- For env-based segments: use `patch.dict(os.environ, {...})`
- For install/uninstall: create a tmp settings.json, pass its path to install/uninstall
- For generate_script: just verify compile() succeeds and string content checks
- Import from `kohakuterrarium.studio.themes` and `kohakuterrarium.studio.statusline`

Each test function should be small (5-15 lines), one assertion focus. Use descriptive names like `test_render_segments_minimal_joins_with_pipe`.
  </action>
  <verify>
    <automated>cd D:/projects/KohakuTerrarium && python -m pytest tests/unit/test_studio_statusline.py -v --tb=short 2>&1 | tail -30</automated>
  </verify>
  <done>
    - 16+ test cases all pass
    - Covers themes (list, get, preview, to_settings) and statusline (segments, render, generate, install, uninstall, preview, builder)
    - No test uses network or real filesystem outside tmp_path
  </done>
</task>

</tasks>

<verification>
```bash
# All new tests pass
cd D:/projects/KohakuTerrarium && python -m pytest tests/unit/test_studio_statusline.py -v

# Existing tests still pass
python -m pytest tests/unit/test_studio_config.py tests/unit/test_studio_sessions.py -v

# Import smoke test
python -c "from kohakuterrarium.studio.themes import BUILTIN_THEMES; from kohakuterrarium.studio.statusline import StatusLineBuilder; print(f'{len(BUILTIN_THEMES)} themes, builder OK')"

# CLI parse test
python -c "import argparse; from kohakuterrarium.studio.cli import add_studio_subparser; p = argparse.ArgumentParser(); s = p.add_subparsers(); add_studio_subparser(s); print('CLI OK')"

# Ruff + black
python -m ruff check src/kohakuterrarium/studio/themes.py src/kohakuterrarium/studio/statusline.py --config pyproject.toml
python -m black --check src/kohakuterrarium/studio/themes.py src/kohakuterrarium/studio/statusline.py
```
</verification>

<success_criteria>
- 6 built-in themes queryable by name, convertible to Claude Code settings format
- StatusLineBuilder generates standalone Python script (no KT imports) with configured segments and style
- 3 rendering styles produce distinct output (pipe-separated, powerline arrows, bracketed)
- CLI subcommands for statusline install/preview/uninstall and theme list/show/apply all functional
- 16+ tests pass covering both modules
- Ruff and black clean
</success_criteria>

<output>
After completion, create `.planning/quick/260405-oks-kt-studio-phase-3-statusline-themes-segm/260405-oks-SUMMARY.md`
</output>
