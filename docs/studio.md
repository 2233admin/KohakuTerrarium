# kt studio -- AI Coding Tool Workbench

A unified workbench for managing multiple AI coding CLI tools from KohakuTerrarium.

Instead of configuring Claude Code, Codex, Gemini, Aider, and Copilot separately, `kt studio` provides one interface to manage profiles, sessions, themes, status lines, and costs across all of them.

## Quick Start

```bash
# Initialize studio with a default profile
kt studio init

# Create profiles for different workflows
kt studio profile create research --model opus --effort high
kt studio profile create quick --model haiku --effort low

# Launch Claude Code with a profile
kt studio launch research

# Check what tools are available
kt studio targets
```

## Concepts

### Targets

A **target** is an AI coding CLI tool that studio can manage. Each target implements a common interface: detect, launch, list models, check status.

Built-in targets:

| Target | CLI Command | Config Path |
|--------|-------------|-------------|
| `claude-code` | `claude` | `~/.claude/settings.json` |
| `codex` | `codex` | `~/.codex/` |
| `gemini` | `gemini` | `~/.gemini/` |
| `copilot` | `github-copilot-cli` | `~/.copilot/config.json` |
| `openclaw` | HTTP endpoint | `endpoint` in profile |
| `aider` | `aider` | `~/.aider.conf.yml` |

### Profiles

A **profile** bundles target selection, model, effort level, environment variables, hooks, theme, and status line config into a named preset.

```yaml
# ~/.kohakuterrarium/studio.yaml
profiles:
  daily:
    target: claude-code
    model: sonnet
    effort: high
    theme: tokyo-night
    statusline:
      segments: [git, tokens, cost, model]
      style: powerline
  research:
    target: gemini
    model: gemini-2.5-pro
```

### Sessions

Named sessions map human-readable names to tool-specific session IDs. Resume, fork, inspect, export, or delete sessions by name.

## Commands

### Profile Management

```bash
kt studio init                          # Create default studio.yaml
kt studio profiles                      # List all profiles
kt studio profile create <name> [--model X] [--effort Y] [--theme Z]
kt studio profile show <name>
kt studio profile edit <name>           # Open in $EDITOR
kt studio profile delete <name>
kt studio launch [profile]              # Launch tool with merged settings
kt studio apply [profile]               # Output merged settings JSON
kt studio doctor                        # Health check
kt studio diff <profile-a> <profile-b>  # Compare two profiles
```

### Session Management

```bash
kt studio sessions                      # List named sessions
kt studio session name <uuid|latest> <name>
kt studio session resume <name> [--profile X]
kt studio session fork <name> [new_name]
kt studio session inspect <name>
kt studio session delete <name>
kt studio session export <name> [--format html|md]
kt studio session incognito [--profile X]
```

### Status Line and Themes

```bash
kt studio statusline install            # Install status line into settings
kt studio statusline preview            # Preview in terminal
kt studio statusline uninstall
kt studio theme list                    # 6 built-in themes
kt studio theme show <name>             # Preview colors
kt studio theme apply <name>            # Apply to active profile
```

Available themes: `dark`, `light`, `nord`, `tokyo-night`, `rose-pine`, `gruvbox`

### Target Management

```bash
kt studio targets                       # List all targets with status
kt studio target <name> status          # Detailed target info
```

### Workbench Tools

```bash
kt studio cost [--period today|week|month]   # Cross-tool cost summary
kt studio record [--target X] [--output F]   # Record CLI session as JSONL
kt studio replay <file.jsonl> [--speed 2.0]  # Replay recorded session
kt studio compare <task> [--targets a,b,c]   # Run task on multiple tools
kt studio completion bash|zsh|fish|powershell # Generate shell completion
```

### Copilot-Specific

```bash
kt studio copilot status
kt studio copilot model <model>
kt studio copilot models
kt studio copilot patch                 # AST patch for extended models
kt studio copilot unpatch
```

## How Launch Works

`kt studio launch` does NOT modify your existing tool settings. Instead:

1. Reads your existing settings (e.g., `~/.claude/settings.json`)
2. Merges profile overrides (env, hooks, permissions, theme)
3. Writes merged result to a temporary file
4. Launches the tool with `--settings <temp-file>`

Your original settings are never touched.

## Architecture

```
studio/
    cli.py            # Subparser registration (179 lines)
    handlers.py       # Command dispatch (486 lines)
    config.py         # Dataclasses + YAML load/save
    profiles.py       # Profile CRUD + diff
    launcher.py       # Target-delegating launcher
    sessions.py       # Cross-tool session management
    statusline.py     # Status line builder + script generator
    themes.py         # 6 built-in themes
    copilot.py        # Copilot integration
    cost.py           # Cross-tool cost tracking
    record.py         # Session recording/replay
    compare.py        # Multi-tool comparison runner
    completion.py     # Shell completion generator
    targets/
        base.py       # Target ABC
        __init__.py   # Registry + resolve
        claude_code.py
        codex.py
        gemini.py
        copilot.py
        openclaw.py
        aider.py
```

## Dependencies

Zero additional dependencies beyond KohakuTerrarium's existing requirements.
