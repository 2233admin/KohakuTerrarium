---
phase: 5c-workbench-tools
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/kohakuterrarium/studio/cli.py
  - src/kohakuterrarium/studio/handlers.py
  - src/kohakuterrarium/studio/cost.py
  - src/kohakuterrarium/studio/record.py
  - src/kohakuterrarium/studio/compare.py
  - src/kohakuterrarium/studio/completion.py
  - src/kohakuterrarium/studio/profiles.py
  - tests/unit/test_studio_workbench.py
autonomous: true
requirements: [WB-01, WB-02, WB-03, WB-04, WB-05]

must_haves:
  truths:
    - "kt studio cost shows pricing estimates for common models"
    - "kt studio record wraps a subprocess and captures timestamped JSONL"
    - "kt studio compare runs same task on multiple targets in parallel"
    - "kt studio completion bash|zsh|fish|powershell emits valid shell scripts"
    - "kt studio diff profile-a profile-b shows field-by-field differences"
    - "cli.py stays under 600 lines after adding all 5 new subcommands"
  artifacts:
    - path: "src/kohakuterrarium/studio/handlers.py"
      provides: "Extracted handler dispatch from cli.py"
      min_lines: 350
    - path: "src/kohakuterrarium/studio/cost.py"
      provides: "Cost tracker with pricing table and log scanning"
      min_lines: 80
    - path: "src/kohakuterrarium/studio/record.py"
      provides: "Session recorder and replay"
      min_lines: 80
    - path: "src/kohakuterrarium/studio/compare.py"
      provides: "Compare runner for multi-target task execution"
      min_lines: 100
    - path: "src/kohakuterrarium/studio/completion.py"
      provides: "Shell completion script generators"
      min_lines: 80
    - path: "tests/unit/test_studio_workbench.py"
      provides: "Tests for all 5 workbench modules"
      min_lines: 200
  key_links:
    - from: "src/kohakuterrarium/studio/cli.py"
      to: "src/kohakuterrarium/studio/handlers.py"
      via: "handle_studio_command dispatch"
      pattern: "from kohakuterrarium\\.studio\\.handlers import handle_studio_command"
    - from: "src/kohakuterrarium/studio/handlers.py"
      to: "src/kohakuterrarium/studio/cost.py"
      via: "handle_cost_command import"
      pattern: "from kohakuterrarium\\.studio\\.cost import handle_cost_command"
    - from: "src/kohakuterrarium/studio/compare.py"
      to: "src/kohakuterrarium/studio/targets/__init__.py"
      via: "resolve_target for building commands"
      pattern: "from kohakuterrarium\\.studio\\.targets import resolve_target"
---

<objective>
Add 5 workbench tools to kt studio (cost tracker, session recorder, compare runner, shell completion, profile diff) while keeping cli.py under the 600-line hard limit.

Purpose: These tools complete the studio's developer ergonomics layer -- cost visibility, session recording, cross-target comparison, shell completions, and profile diffing.

Output: 4 new modules (cost.py, record.py, compare.py, completion.py), profile diff added to profiles.py, handlers.py extracted from cli.py, comprehensive tests.
</objective>

<execution_context>
@.planning/quick/260405-ruy-kt-studio-phase-5c-workbench-tools-cost-/260405-ruy-PLAN.md
</execution_context>

<context>
@src/kohakuterrarium/studio/cli.py
@src/kohakuterrarium/studio/config.py
@src/kohakuterrarium/studio/profiles.py
@src/kohakuterrarium/studio/targets/base.py
@src/kohakuterrarium/studio/targets/__init__.py

<interfaces>
From src/kohakuterrarium/studio/targets/base.py:
```python
class Target(ABC):
    name: str
    display_name: str
    def detect(self) -> Path | None: ...
    def build_command(self, profile: ProfileConfig, settings_path: Path | None = None) -> list[str]: ...
    def list_models(self) -> list[str]: ...
    def status(self) -> dict: ...
    def session_dir(self) -> Path | None: ...
    def scan_sessions(self) -> list[dict]: ...
```

From src/kohakuterrarium/studio/targets/__init__.py:
```python
def resolve_target(name: str) -> Target: ...
def list_targets() -> list[Target]: ...
```

From src/kohakuterrarium/studio/config.py:
```python
@dataclass
class ProfileConfig:
    model: str = "sonnet"
    effort: str = "high"
    theme: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    hooks: dict[str, list[HookEntry]] = field(default_factory=dict)
    statusline: StatuslineConfig | None = None
    permissions: dict[str, Any] = field(default_factory=dict)
    append_system_prompt_file: str | None = None
    mcp_config: str | None = None
    plugin_dirs: list[str] = field(default_factory=list)
    target: str = "claude-code"

def load_studio_config(path: Path | None = None) -> StudioConfig: ...
def save_studio_config(config: StudioConfig, path: Path | None = None) -> None: ...
```

From src/kohakuterrarium/studio/profiles.py:
```python
def create_profile(name, model, effort, theme, config_path) -> ProfileConfig: ...
def delete_profile(name, config_path) -> None: ...
def list_profiles(config_path) -> list[tuple[str, ProfileConfig]]: ...
def show_profile(name, config_path) -> ProfileConfig | None: ...
def edit_profile(name, config_path) -> None: ...
def set_active_profile(name, config_path) -> None: ...
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Extract handlers.py from cli.py + add new subparser defs</name>
  <files>
    src/kohakuterrarium/studio/handlers.py
    src/kohakuterrarium/studio/cli.py
  </files>
  <action>
**Step 1: Create handlers.py** -- Move ALL handler functions out of cli.py into a new handlers.py module. This includes:
- `_handle_init`, `_resolve_profile`, `_handle_launch`, `_handle_apply`
- `_handle_profiles`, `_handle_profile_subcommand`, `_handle_doctor`
- `_handle_sessions_list`, `_handle_session_subcommand`
- `_resolve_statusline_config`, `_handle_statusline_subcommand`
- `_handle_theme_subcommand`, `_handle_targets_list`, `_handle_target_subcommand`
- `_handle_copilot_subcommand`
- The `handle_studio_command` dispatch function itself

handlers.py gets ALL the imports these functions need (config, launcher, profiles, copilot, sessions, targets, statusline, themes, logging). Move them from cli.py.

The `handle_studio_command` match block gets 5 new cases added:
- `"cost"` -> calls `handle_cost_command(args)` from `cost.py`
- `"record"` -> calls `handle_record_command(args)` from `record.py`
- `"replay"` -> calls `handle_replay_command(args)` from `record.py`
- `"compare"` -> calls `handle_compare_command(args)` from `compare.py`
- `"completion"` -> calls `handle_completion_command(args)` from `completion.py`
- `"diff"` -> calls `handle_diff_command(args)` from `profiles.py`

Update the usage string in the default case to include the new commands.

**Step 2: Slim down cli.py** -- cli.py retains ONLY:
- `import argparse` and `from kohakuterrarium.studio.handlers import handle_studio_command`
- The `add_studio_subparser` function (all subparser definitions)
- Add 6 new subparser definitions (compact, ~2-3 lines each):

```python
# studio cost [--today|--week|--month]
cost_p = studio_sub.add_parser("cost", help="Show API cost summary")
cost_p.add_argument("--period", default="today", choices=["today", "week", "month"])

# studio record [--target X] [--output file.jsonl]
record_p = studio_sub.add_parser("record", help="Record a CLI session as JSONL")
record_p.add_argument("--target", default=None, help="Target to record")
record_p.add_argument("--output", default=None, help="Output JSONL path")

# studio replay <file> [--speed N]
replay_p = studio_sub.add_parser("replay", help="Replay a recorded session")
replay_p.add_argument("recording", help="Path to recording JSONL")
replay_p.add_argument("--speed", type=float, default=1.0, help="Playback speed")

# studio compare "task" [--targets a,b,c]
compare_p = studio_sub.add_parser("compare", help="Run task on multiple targets")
compare_p.add_argument("task", help="Task string or path to task file")
compare_p.add_argument("--targets", default=None, help="Comma-separated target names")
compare_p.add_argument("--timeout", type=int, default=120, help="Per-target timeout (sec)")

# studio completion bash|zsh|fish|powershell
comp_p = studio_sub.add_parser("completion", help="Generate shell completion script")
comp_p.add_argument("shell", choices=["bash", "zsh", "fish", "powershell"])

# studio diff <profile-a> <profile-b>
diff_p = studio_sub.add_parser("diff", help="Compare two profiles")
diff_p.add_argument("profile_a", help="First profile name")
diff_p.add_argument("profile_b", help="Second profile name")
```

cli.py should end up at roughly 200 lines (subparser defs only + 1 import + the `add_studio_subparser` function).

**Critical**: `handle_studio_command` is exported from handlers.py. cli.py only re-exports it. All existing tests that import `handle_studio_command` from `cli` must still work -- add a re-export: `from kohakuterrarium.studio.handlers import handle_studio_command` at top of cli.py so the public API is unchanged.

Follow project import rules: built-in first, third-party second, KT modules third. No in-function imports except lazy/optional deps.
  </action>
  <verify>
    <automated>cd D:/projects/KohakuTerrarium && python -c "from kohakuterrarium.studio.cli import add_studio_subparser, handle_studio_command; print('imports OK')" && python -c "import ast; t=ast.parse(open('src/kohakuterrarium/studio/cli.py').read()); print(f'cli.py: {t.body[-1].end_lineno} lines')" && python -m pytest tests/unit/test_studio.py tests/unit/test_studio_copilot.py tests/unit/test_studio_sessions.py tests/unit/test_studio_statusline.py tests/unit/test_studio_targets.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <done>
    - handlers.py exists with all handler functions + handle_studio_command dispatch (including 6 new cases)
    - cli.py is under 600 lines, contains only add_studio_subparser + re-export of handle_studio_command
    - All 168 existing tests pass unchanged
    - New subparser defs for cost, record, replay, compare, completion, diff are registered
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement 5 workbench modules</name>
  <files>
    src/kohakuterrarium/studio/cost.py
    src/kohakuterrarium/studio/record.py
    src/kohakuterrarium/studio/compare.py
    src/kohakuterrarium/studio/completion.py
    src/kohakuterrarium/studio/profiles.py
    tests/unit/test_studio_workbench.py
  </files>
  <behavior>
    # cost.py
    - test_pricing_table_has_common_models: PRICING dict contains at least claude-sonnet-4, claude-opus-4, gpt-4.1, gemini-2.5-pro
    - test_estimate_cost_zero_tokens: estimate_cost("claude-sonnet-4", 0, 0) == 0.0
    - test_estimate_cost_calculation: estimate_cost("claude-sonnet-4", 1_000_000, 1_000_000) == 3.0 + 15.0 == 18.0
    - test_estimate_cost_unknown_model: estimate_cost("unknown-model", 1000, 1000) returns 0.0 (graceful fallback)
    - test_cost_summary_empty: cost_summary() returns dict with total=0.0 when no log data

    # record.py
    - test_recording_entry_to_json: RecordingEntry serializes to dict with timestamp, type, content keys
    - test_recorder_init: SessionRecorder(path, "claude-code") stores output_path and target_name
    - test_recorder_writes_jsonl: mock subprocess, verify JSONL lines written to file (at least meta entry)

    # compare.py
    - test_compare_result_dataclass: CompareResult fields (target, output, duration_ms, exit_code) accessible
    - test_compare_runner_init: CompareRunner(["claude-code", "codex"]) stores target list
    - test_format_results_table: format_results with 2 CompareResults produces table string with target names and durations
    - test_compare_runner_parallel: mock subprocess, verify asyncio.gather runs targets concurrently (2 results returned)

    # completion.py
    - test_bash_completion_has_subcommands: output contains "studio" and "launch" and "cost"
    - test_zsh_completion_has_subcommands: output contains "studio" and "launch"
    - test_fish_completion_valid: output contains "complete" (fish syntax)
    - test_powershell_completion_valid: output contains "Register-ArgumentCompleter" or "kt"

    # profiles.py (diff addition)
    - test_diff_profiles_identical: diff_profiles on two identical profiles returns empty dict
    - test_diff_profiles_different_model: profiles with different model field returns {"model": ("sonnet", "opus")}
    - test_diff_profiles_missing_profile: diff_profiles with nonexistent name raises KeyError
  </behavior>
  <action>
**cost.py** (~120 lines):
- `PRICING: dict[str, tuple[float, float]]` -- hardcoded pricing table with 8 models from the design (claude-sonnet-4, claude-opus-4, claude-haiku-4, gpt-4.1, o3-mini, gemini-2.5-pro, gemini-2.5-flash, codex-mini)
- `estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float` -- lookup model in PRICING, calculate `(input_tokens / 1_000_000) * input_rate + (output_tokens / 1_000_000) * output_rate`. Return 0.0 for unknown models.
- `scan_usage_logs() -> list[dict]` -- scan `~/.claude/projects/` for session JSONL files with token counts. Best-effort, return empty list if dirs missing. Each dict: `{target, model, input_tokens, output_tokens, cost, timestamp}`.
- `cost_summary(period: str = "today") -> dict` -- aggregate scan_usage_logs() filtered by period. Returns `{total: float, by_target: dict, by_model: dict, entries: int}`.
- `handle_cost_command(args) -> int` -- print formatted cost summary table. Uses args.period.

**record.py** (~120 lines):
- `@dataclass RecordingEntry` with timestamp (str), type (str: "input"/"output"/"meta"), content (str). Add `to_dict() -> dict` method.
- `class SessionRecorder` with `__init__(self, output_path: Path, target_name: str)`.
- `async def record(self, command: list[str]) -> int` -- spawn subprocess with `asyncio.create_subprocess_exec`, pipe stdout, read line by line, write each line as RecordingEntry to output JSONL file, also forward to sys.stdout. Write meta entry at start (target, timestamp) and end (duration, exit_code). Return exit code.
- `def replay(recording_path: Path, speed: float = 1.0) -> None` -- read JSONL, print output entries with timing delays divided by speed.
- `handle_record_command(args) -> int` and `handle_replay_command(args) -> int` -- CLI handlers.

**compare.py** (~150 lines):
- `@dataclass CompareResult` with target (str), output (str), duration_ms (int), exit_code (int).
- `class CompareRunner` with `__init__(self, targets: list[str])`.
- `async def run(self, task: str, timeout: int = 120) -> list[CompareResult]` -- for each target name, resolve via `resolve_target()`, build a command with task as stdin/arg, run via `asyncio.create_subprocess_exec` with timeout. Use `asyncio.gather(*tasks)` for parallel execution. If task is a file path (exists on disk), read its content. Return results sorted by duration_ms.
- `def format_results(self, results: list[CompareResult]) -> str` -- format as aligned table: Target | Duration | Exit | Output (first 200 chars).
- `handle_compare_command(args) -> int` -- parse args.targets (comma-split or default to all installed), create CompareRunner, asyncio.run, print format_results.

**completion.py** (~100 lines):
- `generate_bash_completion() -> str` -- emit a bash completion script. Include all subcommands (init, launch, apply, profiles, profile, doctor, sessions, session, statusline, theme, targets, target, copilot, cost, record, replay, compare, completion, diff). Include dynamic profile name completion via `$(kt studio profiles --names-only 2>/dev/null)` or hardcoded subcommand list.
- `generate_zsh_completion() -> str` -- zsh compdef script with same subcommands.
- `generate_fish_completion() -> str` -- fish complete commands.
- `generate_powershell_completion() -> str` -- PowerShell Register-ArgumentCompleter block.
- `handle_completion_command(args) -> int` -- match args.shell, print the corresponding script, return 0.

**profiles.py** (~30 lines added):
- Add `diff_profiles(name_a: str, name_b: str, config_path: Path | None = None) -> dict[str, tuple]` -- load config, get both profiles (raise KeyError if not found), compare field by field using `dataclasses.asdict()`. Return `{field_name: (value_a, value_b)}` for fields that differ. Empty dict means identical.
- Add `handle_diff_command(args) -> int` -- call diff_profiles(args.profile_a, args.profile_b), print each differing field as `{field}: {value_a} -> {value_b}`, or "Profiles are identical." if empty.

**test_studio_workbench.py** -- implement all tests from the behavior block above. Use `tmp_path` for file I/O tests. Use `unittest.mock.patch` and `AsyncMock` for subprocess mocking. Import directly from each module.

Follow project conventions: no in-function imports, dataclasses not pydantic, get_logger(__name__) for logging, Python 3.10+ type hints (X | None not Optional[X]).
  </action>
  <verify>
    <automated>cd D:/projects/KohakuTerrarium && python -m pytest tests/unit/test_studio_workbench.py -x -q 2>&1 | tail -10</automated>
  </verify>
  <done>
    - cost.py: PRICING table with 8 models, estimate_cost returns correct values, cost_summary aggregates
    - record.py: RecordingEntry dataclass, SessionRecorder wraps subprocess to JSONL, replay with timing
    - compare.py: CompareRunner runs targets in parallel via asyncio.gather, format_results produces table
    - completion.py: 4 shell generators emit valid completion scripts with all subcommands
    - profiles.py: diff_profiles returns field-by-field comparison dict
    - All ~18 new tests pass
  </done>
</task>

<task type="auto">
  <name>Task 3: Integration verify -- all 168+ tests green, cli.py under limit</name>
  <files>
    src/kohakuterrarium/studio/cli.py
  </files>
  <action>
Run the full test suite to confirm no regressions. Verify cli.py line count is under 600. Fix any import issues or broken references from the handler extraction.

Specific checks:
1. `wc -l src/kohakuterrarium/studio/cli.py` -- must be under 600
2. `python -m pytest tests/unit/ -x -q` -- all tests pass
3. `python -c "from kohakuterrarium.studio.cli import add_studio_subparser, handle_studio_command"` -- public API intact
4. `python -c "from kohakuterrarium.studio.cost import PRICING, estimate_cost"` -- cost module importable
5. `python -c "from kohakuterrarium.studio.compare import CompareRunner, CompareResult"` -- compare module importable
6. `python -c "from kohakuterrarium.studio.completion import generate_bash_completion"` -- completion module importable

If cli.py is still over 600 lines, further trim by removing blank lines or consolidating subparser defs that are excessively verbose. The subparser definitions should be compact.

If any existing tests fail due to import path changes (handle_studio_command moved), ensure the re-export in cli.py covers them.
  </action>
  <verify>
    <automated>cd D:/projects/KohakuTerrarium && python -m pytest tests/unit/ -x -q 2>&1 | tail -5 && wc -l src/kohakuterrarium/studio/cli.py && echo "DONE"</automated>
  </verify>
  <done>
    - All tests pass (168 existing + ~18 new = 186+)
    - cli.py is under 600 lines
    - All new modules import cleanly
    - No regressions in any existing functionality
  </done>
</task>

</tasks>

<verification>
1. `python -m pytest tests/unit/ -x -q` -- all tests pass
2. `wc -l src/kohakuterrarium/studio/cli.py` -- under 600
3. `python -c "from kohakuterrarium.studio.handlers import handle_studio_command"` -- handler dispatch importable
4. `python -c "from kohakuterrarium.studio.cost import PRICING; assert len(PRICING) >= 8"` -- pricing table populated
5. `python -c "from kohakuterrarium.studio.completion import generate_bash_completion; s = generate_bash_completion(); assert 'cost' in s and 'compare' in s"` -- completions include new commands
</verification>

<success_criteria>
- 5 new workbench modules functional: cost, record, compare, completion, profile-diff
- cli.py extracted to handlers.py, stays under 600-line limit
- All existing 168 tests pass unchanged
- ~18 new tests for workbench modules pass
- All new subcommands registered in argparse and dispatchable
</success_criteria>

<output>
After completion, create `.planning/quick/260405-ruy-kt-studio-phase-5c-workbench-tools-cost-/260405-ruy-SUMMARY.md`
</output>
