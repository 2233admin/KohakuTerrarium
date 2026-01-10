# Research: Codex & OpenCode Agent Design

> Investigation of OpenAI Codex CLI and OpenCode agent designs for improving KohakuTerrarium

---

## Sources

- **Codex**: https://github.com/openai/codex (Rust/TypeScript, Apache-2.0)
- **OpenCode**: https://github.com/opencode-ai/opencode (Go, MIT)

---

## 1. System Prompt Design Comparison

### Codex (~25KB prompt)

**Structure:**
- Personality and tone guidelines
- AGENTS.md specification (hierarchical instructions)
- Preamble message requirements
- Planning system guidelines
- Task execution guidelines
- Sandbox and approval modes
- Validation guidelines
- Final answer formatting

**Key Excerpts:**

```markdown
## Personality
Your default personality and tone is concise, direct, and friendly.
You communicate efficiently, always keeping the user clearly informed
about ongoing actions without unnecessary detail.

## Preamble messages
Before making tool calls, send a brief preamble to the user explaining
what you're about to do. Keep it concise: 8-12 words for quick updates.

Examples:
- "I've explored the repo; now checking the API route definitions."
- "Next, I'll patch the config and update the related tests."
- "Ok cool, so I've wrapped my head around the repo. Now digging into the API routes."

## Planning
You have access to an `update_plan` tool which tracks steps and progress.
A good plan should break the task into meaningful, logically ordered steps.
```

### OpenCode (~8KB prompt, two variants)

**Structure:**
- Memory file support (OpenCode.md)
- Tone and style guidelines
- Proactiveness rules
- Convention following
- Tool usage policy

**Key Excerpts:**

```markdown
# Memory
If the current working directory contains OpenCode.md, it will be automatically
added to your context. This file serves:
1. Storing frequently used bash commands (build, test, lint)
2. Recording code style preferences
3. Maintaining codebase structure info

# Tone and style
You should be concise, direct, and to the point.
IMPORTANT: Keep responses short, fewer than 4 lines unless asked for detail.
IMPORTANT: You should NOT answer with unnecessary preamble or postamble.

# Proactiveness
Strike a balance between:
1. Doing the right thing when asked
2. Not surprising the user with unexpected actions
```

### KohakuTerrarium (Current: ~1KB)

Minimal - only basic guidelines. Tool list and syntax auto-aggregated.

---

## 2. Tool Calling Comparison

| Aspect | Codex | OpenCode | KohakuTerrarium |
|--------|-------|----------|-----------------|
| Format | Native OpenAI functions | Native JSON schema | Custom `##tool##` blocks |
| File Edit | `apply_patch` (custom diff) | `edit`, `patch`, `write` | `write` (full file) |
| Search | `rg` via shell | `glob`, `grep` tools | `glob`, `grep` tools |
| Execution | `shell` command | `bash` tool | `bash` tool |

### Codex apply_patch Format

```
*** Begin Patch
*** Add File: hello.txt
+Hello world
*** Update File: src/app.py
@@ def greet():
-print("Hi")
+print("Hello, world!")
*** Delete File: obsolete.txt
*** End Patch
```

### OpenCode Tool Definition Pattern

```go
type ToolInfo struct {
    Name        string
    Description string
    Parameters  map[string]any
    Required    []string
}

const viewDescription = `File viewing tool...

WHEN TO USE THIS TOOL:
- Use when you need to read the contents of a specific file

HOW TO USE:
- Provide the path to the file you want to view
- Optionally specify an offset

FEATURES:
- Displays file contents with line numbers

LIMITATIONS:
- Maximum file size is 250KB

TIPS:
- Use with Glob tool to first find files`
```

---

## 3. Sub-Agent Design

### Codex: AGENTS.md Hierarchy

- Files called AGENTS.md can appear anywhere in repo
- Scope: entire directory tree rooted at containing folder
- Deeper files override higher-level files
- Direct prompt instructions override AGENTS.md

```markdown
Each AGENTS.md governs the entire directory that contains it and
every child directory beneath that point. When two AGENTS.md files
disagree, the one located deeper overrides the higher-level file.
```

### OpenCode: Agent Tool (Limited Sub-Agent)

```go
// Sub-agent with READ-ONLY tools only
func TaskAgentTools() []tools.BaseTool {
    return []tools.BaseTool{
        tools.NewGlobTool(),
        tools.NewGrepTool(),
        tools.NewLsTool(),
        tools.NewViewTool(),
    }
}

Description: "Launch a new agent with access to: GlobTool, GrepTool, LS, View.
When searching for a keyword and not confident you'll find the right match,
use the Agent tool to perform the search for you.

Usage notes:
1. Launch multiple agents concurrently for performance
2. Agent result is not visible to user - summarize it
3. Each invocation is stateless
4. Agent can NOT modify files"
```

### KohakuTerrarium: Full Sub-Agent System

- Nested agents with own controller + tools
- Configurable tool access
- Can be stateful or stateless
- Output to parent or external

---

## 4. Environment Info Injection

### OpenCode Pattern (Recommended)

```go
func getEnvironmentInfo() string {
    return fmt.Sprintf(`<env>
Working directory: %s
Is directory a git repo: %s
Platform: %s
Today's date: %s
</env>
<project>
%s
</project>`, cwd, isGit, platform, date, lsOutput)
}
```

Auto-injected into every system prompt.

---

## 5. Memory/Context Systems

| System | Codex | OpenCode | KohakuTerrarium |
|--------|-------|----------|-----------------|
| Project instructions | AGENTS.md | OpenCode.md | memory/ folder |
| Auto-load | Yes (hierarchical) | Yes (single file) | Planned |
| Scope | Directory tree | Working dir | Agent folder |
| Override | Deeper wins | N/A | User > builtin |

---

## 6. Key Ideas for KohakuTerrarium

### A. Environment Info Block

Auto-inject at prompt aggregation:

```python
def get_environment_info() -> str:
    return f"""<env>
Working directory: {cwd}
Is directory a git repo: {is_git}
Platform: {platform}
Today's date: {date}
</env>"""
```

### B. Project Instructions File

Support hierarchical AGENTS.md / .kohaku.md:

```python
def load_project_instructions(cwd: Path) -> str:
    """Load AGENTS.md files from cwd up to repo root."""
    instructions = []
    for path in walk_up_to_root(cwd):
        agents_file = path / "AGENTS.md"
        if agents_file.exists():
            instructions.append(agents_file.read_text())
    return "\n\n".join(reversed(instructions))  # root first, deeper overrides
```

### C. Improved Tool Documentation Format

```markdown
---
name: read
description: Read file contents with optional line range
category: builtin
tags: [file, io]
---

# read

WHEN TO USE:
- When you need to examine file contents
- For checking source code, configs, logs

HOW TO USE:
- Provide file path (required)
- Optionally specify offset and limit for large files

FEATURES:
- Line numbers for easy reference
- UTF-8 with error replacement

LIMITATIONS:
- Large files may need offset/limit
- Binary files show replacement chars

TIPS:
- Use glob first to find files
- Use grep to locate, then read to examine
```

### D. Explore Sub-Agent (Read-Only)

```python
EXPLORE_AGENT_TOOLS = ["glob", "grep", "read"]  # No write, bash, python

class ExploreSubAgent:
    """Limited sub-agent for search/exploration tasks."""
    tools: list[str] = ["glob", "grep", "read"]
    can_modify: bool = False
    stateless: bool = True
```

### E. Preamble Guidelines

Add to system prompt:

```markdown
## Before Tool Calls

Send a brief message (8-12 words) before tool calls:
- "Checking the src folder structure."
- "Reading config.yaml to understand settings."
- "Searching for function definitions."

Exception: Skip for trivial single reads.
```

### F. Conciseness Guidelines

Add to system prompt:

```markdown
## Response Style

- Be concise and direct
- 1-3 sentences for simple tasks
- No unnecessary preamble or postamble
- Don't explain what you're about to do extensively
- After tool calls, summarize results briefly
```

---

## 7. What NOT to Adopt

### Native Function Calling

Both Codex and OpenCode use native OpenAI/Anthropic function calling. Our `##tool##` format:
- Works with any model (not just OpenAI)
- Easier to parse from streaming
- More explicit in output
- Aligns with our state-machine design

**Decision: Keep `##tool##` format**

### Very Long System Prompts

Codex's 25KB prompt is comprehensive but:
- High token cost
- May overwhelm smaller models
- Hard to maintain

**Decision: Keep prompt minimal, use ##info## for on-demand docs**

### apply_patch Format

Complex diff format requires:
- Special parser
- Model training for format
- Error-prone with context lines

**Decision: Keep simple write tool, consider edit tool later**

---

## 8. Implementation Priority

1. **High Priority**
   - Improved tool documentation format ✅ Applying now
   - Conciseness guidelines in prompt ✅ Applying now
   - Edit/patch tool for partial file updates (needed for real usage)

2. **Medium Priority**
   - System prompt plugins (modular env info, project instructions)
   - Explore sub-agent for search tasks
   - Preamble guidelines

3. **Low Priority**
   - Planning tool (update_plan)
   - LSP integration

## 10. Edit/Patch Tool Design (TODO)

Need to support partial file editing without rewriting entire file.

**Options:**
1. **Line-based edit** (like Claude Code's Edit tool)
   - `old_string` + `new_string` replacement
   - Requires unique match in file

2. **Diff format** (like Codex apply_patch)
   - Context lines for matching
   - More complex but handles ambiguity

3. **Line number based**
   - Edit lines X-Y with new content
   - Simple but fragile (line numbers change)

**Recommendation:** Start with option 1 (string replacement) - simpler and works well.

```yaml
##tool##
name: edit
args:
  path: src/main.py
  old_string: |
    def hello():
        print("Hi")
  new_string: |
    def hello():
        print("Hello, World!")
##tool##
```

## 11. System Prompt Plugin Architecture (TODO)

Environment info, project instructions, etc. should be **plugins** not hardcoded.

```python
class PromptPlugin(Protocol):
    """Plugin that contributes to system prompt aggregation."""

    name: str
    priority: int  # Lower = earlier in prompt

    async def get_content(self, context: AgentContext) -> str | None:
        """Return content to inject, or None to skip."""
        ...

# Example plugins:
class EnvInfoPlugin(PromptPlugin):
    """Injects <env> block with working dir, git status, platform, date."""
    name = "env_info"
    priority = 10

class ProjectInstructionsPlugin(PromptPlugin):
    """Loads AGENTS.md / .kohaku.md from project."""
    name = "project_instructions"
    priority = 20

class ToolListPlugin(PromptPlugin):
    """Auto-generates tool list from registry."""
    name = "tool_list"
    priority = 50

class FrameworkHintsPlugin(PromptPlugin):
    """Adds ##tool## syntax and ##info## command hints."""
    name = "framework_hints"
    priority = 60
```

This allows:
- SWE-agent to use EnvInfoPlugin + ProjectInstructionsPlugin
- Chat agent to skip them
- Custom agents to add their own plugins

---

## 9. Questions for Discussion

1. Should we support multiple instruction file names? (AGENTS.md, .kohaku.md, CLAUDE.md)
2. How verbose should preamble messages be?
3. Should explore sub-agent be automatic or explicit tool?
4. Do we want a planning/todo tool exposed to the agent?
5. Should environment info be in `<env>` tags or plain text?
