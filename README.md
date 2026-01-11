# KohakuTerrarium

> **Build any agent. Any purpose. Any workflow.**

KohakuTerrarium is a universal Python framework for building fully autonomous agent systems - from coding assistants like Claude Code to conversational AI like Neuro-sama to self-healing drone controllers.

```
     ┌─────────────────────────────────────────┐
     │           KohakuTerrarium               │
     │                                         │
     │    ┌─────────┐      ┌─────────┐        │
     │    │  Input  │      │ Trigger │        │
     │    └────┬────┘      └────┬────┘        │
     │         └──────┬─────────┘             │
     │                ▼                       │
     │         ┌────────────┐                 │
     │         │ Controller │◄──► Tools       │
     │         │    (LLM)   │◄──► Sub-Agents  │
     │         └─────┬──────┘                 │
     │               ▼                        │
     │          ┌────────┐                    │
     │          │ Output │                    │
     │          └────────┘                    │
     └─────────────────────────────────────────┘
```

## Why KohakuTerrarium?

Most agent frameworks are built for one thing - chatbots, or coding assistants, or automation. KohakuTerrarium is different: **one framework, infinite possibilities**.

| Feature | KohakuTerrarium | Traditional Frameworks |
|---------|-----------------|------------------------|
| **Agent Types** | Any - coding, chat, monitoring, autonomous | Usually single-purpose |
| **Output** | Streaming-first with parallel routing | Often blocking |
| **Tools** | Background execution, non-blocking | Sequential execution |
| **Sub-Agents** | Full nested agents with own LLM | Simple function calls |
| **Memory** | First-citizen folder-based system | External databases only |
| **Configuration** | YAML + Markdown, minimal code | Heavy code required |

## Quick Start

```bash
# Clone and install
git clone https://github.com/KBlueLeaf/KohakuTerrarium.git
cd KohakuTerrarium
uv pip install -e .

# Set API key
export OPENROUTER_API_KEY=your_key_here

# Run the SWE agent
python -m kohakuterrarium.run agents/swe_agent

# Or the RP chatbot agent
python -m kohakuterrarium.run agents/rp_agent
```

## Core Concepts

### Five Systems, One Framework

```
Input ──────┐
            ├──► Controller ◄──► Tool Calling
Trigger ────┘         │
                      ▼
                   Output
```

1. **Input**: User requests, chat messages, API calls, ASR streams
2. **Trigger**: Timers, events, conditions - for autonomous operation
3. **Controller**: The LLM brain - orchestrates everything (doesn't do heavy work)
4. **Tool Calling**: Background execution of tools and sub-agents (non-blocking, parallel)
5. **Output**: Streaming to stdout, files, TTS, APIs - with smart routing

### Controller as Orchestrator (Key Design Principle)

The controller's job is to **dispatch tasks**, not do heavy work itself:

```
Controller decides → Tools/Sub-agents execute → Results flow back
        │                    │                        │
    (fast, lean)        (parallel)              (batched events)
```

- Controller outputs should be SHORT: tool calls, status updates, decisions
- Long outputs (code, explanations) come from specialized sub-agents
- This keeps the controller lightweight, context small, decisions fast

### Sub-Agents: Nested Intelligence

Sub-agents are full agents with their own LLM, but scoped and specialized:

```xml
<!-- Main controller spawns specialized sub-agents -->
<agent type="explore">Find authentication code</agent>
<agent type="plan">Design login flow</agent>
<agent type="coder">Implement the plan</agent>
```

**Built-in Sub-Agents**:
| Sub-Agent | Purpose | Tools Access |
|-----------|---------|--------------|
| `explore` | Search & analyze codebase | glob, grep, read (read-only) |
| `plan` | Implementation planning | glob, grep, read (read-only) |
| `memory_read` | Retrieve from memory | read, glob (read-only) |
| `memory_write` | Store to memory | read, write |
| `response` | Generate user responses | (output sub-agent) |

### Memory: First-Class Citizen

Folder-based memory that's always available, no external database needed:

```
memory/
├── character.md     # Protected - character/agent definition
├── rules.md         # Protected - constraints and guidelines
├── preferences.md   # Writable - user preferences
├── facts.md         # Writable - learned information
└── context.md       # Writable - current session context
```

## Example Agents

### SWE Agent (Coding Assistant)

A software engineering agent for code analysis, file manipulation, and system tasks.

```yaml
# agents/swe_agent/config.yaml
name: swe_agent
model: qwen/qwen3-32b

tools:
  - bash      # Run commands
  - read      # Read files
  - write     # Create files
  - edit      # Modify files
  - glob      # Find files
  - grep      # Search content

subagents:
  - explore   # Search codebase
  - plan      # Create plans
```

**Features**:
- Direct file access and modification
- Shell command execution
- Codebase exploration via sub-agents
- On-demand tool documentation (`<info>tool_name</info>`)

### RP Agent (Character Chatbot)

A roleplay chatbot with persistent character memory and personality.

```yaml
# agents/rp_agent/config.yaml
name: rp_agent
model: qwen/qwen3-32b

tools:
  - read      # Memory access
  - glob      # File searching

subagents:
  - memory_read   # Recall memories
  - memory_write  # Store memories
  - response      # Generate replies

memory:
  init_files:
    - character.md  # Read-only character definition
    - rules.md      # Protected rules
  writable_files:
    - context.md
    - facts.md
    - preferences.md
```

**Features**:
- Character defined in memory (not hardcoded in prompt)
- Must read character before responding (memory-first)
- Persistent facts and context across sessions
- Turn detection (waits for complete user input)

### Monitoring Agent (Autonomous System)

```yaml
name: monitor_agent
input: null  # No user input - fully autonomous

triggers:
  - type: timer
    interval: 60
    prompt: "Check system health"
  - type: condition
    check: "cpu_temp > 80"
    prompt: "Temperature critical"

tools:
  - read_sensors
  - execute_command
  - compile_code
```

## Architecture

```
src/kohakuterrarium/
├── core/                 # Runtime engine
│   ├── agent.py          # Main orchestrator - wires everything together
│   ├── controller.py     # LLM conversation loop + event queue
│   ├── executor.py       # Background job runner (parallel execution)
│   ├── events.py         # Unified TriggerEvent system
│   ├── job.py            # Job status tracking
│   ├── conversation.py   # Message history management
│   └── registry.py       # Module registration
│
├── modules/              # Pluggable modules (protocols)
│   ├── input/            # Input handlers (CLI, webhook, ASR)
│   ├── trigger/          # Trigger systems (timer, condition)
│   ├── tool/             # Tool definitions (BaseTool protocol)
│   ├── output/           # Output routing (stdout, file, TTS)
│   └── subagent/         # Sub-agent lifecycle management
│
├── parsing/              # Stream parsing
│   ├── state_machine.py  # Real-time XML-style detection
│   └── events.py         # ParseEvent types
│
├── builtins/             # Built-in implementations
│   ├── tools/            # bash, read, write, edit, glob, grep
│   └── subagents/        # explore, plan, memory_read, memory_write
│
├── prompt/               # Prompt system
│   ├── aggregator.py     # System prompt building
│   └── template.py       # Jinja2 templating
│
├── llm/                  # LLM abstraction
│   ├── base.py           # Provider protocol
│   └── openai.py         # OpenAI/OpenRouter implementation
│
└── utils/                # Utilities
    └── logging.py        # Structured colored logging
```

## Tool Call Format

KohakuTerrarium uses XML-style tool calls that work with any LLM:

```xml
<!-- Simple command -->
<bash>ls -la</bash>

<!-- File operations -->
<read path="src/main.py"/>

<write path="hello.py">
print("Hello, World!")
</write>

<edit path="config.py">
  <old>debug = False</old>
  <new>debug = True</new>
</edit>

<!-- Sub-agent delegation -->
<agent type="explore">Find all API endpoints</agent>

<!-- On-demand documentation -->
<info>bash</info>
```

## Event-Driven Architecture

Everything flows through `TriggerEvent`:

```python
TriggerEvent(
    type="user_input" | "tool_complete" | "subagent_output" | "timer" | "idle",
    content="...",
    context={...},
    job_id="...",
    stackable=True  # Can batch with simultaneous events
)
```

**Event Sources**:
- Input modules → `"user_input"`
- Triggers (timers, conditions) → `"timer"`, `"idle"`, etc.
- Tool executor → `"tool_complete"`
- Sub-agents → `"subagent_output"`

**Flow**:
```
Event collected → Controller batches events → LLM responds
    → Parser detects tool calls → Tools execute in background
    → Results batched → Re-injected as new event → Repeat
```

## Key Features

### Non-Blocking Tool Execution
```python
# Tools start immediately when detected in stream
# Controller continues streaming while tools run
# All tools execute in parallel via asyncio.gather()
```

### Automatic Retry with Backoff
```python
# LLM provider retries on:
# - 5xx server errors
# - 429 rate limits
# - Connection errors (incomplete reads, timeouts)
# With exponential backoff: 1s, 2s, 4s
```

### Structured Logging
```
[14:32:05] [kohakuterrarium.core.agent] [INFO] Agent started
[14:32:06] [kohakuterrarium.llm.openai] [DEBUG] Streaming response
[14:32:07] [kohakuterrarium.modules.subagent] [INFO] Sub-agent executing tools
```

### Skills Documentation
```xml
<!-- Get full documentation for any tool/sub-agent -->
<info>bash</info>
<info>explore</info>
```

## Current Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | Done | Core foundation (LLM, events, conversation) |
| Phase 2 | Done | Stream parsing (XML-style tool detection) |
| Phase 3 | Done | Controller loop (multi-turn conversation) |
| Phase 4 | Done | Tool execution (background, parallel) |
| Phase 5 | Done | Agent assembly (config loading, I/O) |
| Phase 6 | Done | Sub-agents (nested agents with lifecycle) |
| Phase 7 | In Progress | Advanced features (triggers, output routing) |
| Phase 8 | Planned | Complete example agents |

**152 tests passing**

## Why "Terrarium"?

A terrarium is a self-contained ecosystem - some fully closed and autonomous, others open to interaction. KohakuTerrarium lets you build different agent "terrariums":

- **Closed**: Monitoring systems that run autonomously (no user input)
- **Open**: Coding assistants that respond to user requests
- **Hybrid**: Chat bots that both respond and initiate conversation

The name reflects the vision: build self-contained agent ecosystems, each with their own rules, tools, and behaviors.

## Documentation

- [CLAUDE.md](CLAUDE.md) - Code conventions and project guidelines
- [docs/SPECIFICATION.md](docs/SPECIFICATION.md) - Full framework specification
- [docs/STRUCTURE.md](docs/STRUCTURE.md) - Project structure guide
- [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) - Development roadmap
- [docs/SUBAGENT_DESIGN.md](docs/SUBAGENT_DESIGN.md) - Sub-agent system design

## Contributing

Contributions are welcome! Please read [CLAUDE.md](CLAUDE.md) for:
- Code conventions (imports, typing, file organization)
- Architecture guidelines (controller as orchestrator)
- Logging standards (structured, colored, no print())

## License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  <i>Build agents that think, act, and remember.</i>
  <br><br>
  <b>KohakuTerrarium</b> - Universal Agent Framework
</p>
