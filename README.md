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

## What Makes It Different

| Feature | KohakuTerrarium | Traditional Frameworks |
|---------|-----------------|------------------------|
| **Agent Types** | Any - coding, chat, monitoring, autonomous | Usually single-purpose |
| **Output** | Streaming-first with parallel routing | Often blocking |
| **Tools** | Background execution, non-blocking | Sequential execution |
| **Sub-Agents** | Full nested agents with own LLM | Simple function calls |
| **Memory** | First-citizen folder-based system | External databases only |
| **Configuration** | YAML + Markdown, minimal code | Heavy code required |

## Quick Example

```python
from kohakuterrarium import Agent, load_agent_config

# Load agent from configuration folder
config = load_agent_config("agents/my_agent")
agent = Agent(config)

# Run the agent
await agent.run()
```

Agent folder structure:
```
my_agent/
├── config.yaml         # Model, tools, settings
├── prompts/
│   └── system.md       # Agent personality
└── memory/             # Persistent memory
    └── context.md
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

1. **Input**: User requests, chat messages, API calls, ASR
2. **Trigger**: Timers, events, conditions - for autonomous operation
3. **Controller**: The LLM brain - orchestrates everything
4. **Tool Calling**: Background execution of tools and sub-agents
5. **Output**: Streaming to stdout, files, TTS, APIs

### Sub-Agents: Nested Intelligence

Sub-agents are full agents with their own LLM, but scoped:

```python
# Main controller spawns specialized sub-agents
<agent type="explore">Find authentication code</agent>
<agent type="plan">Design login flow</agent>
<agent type="coder">Implement the plan</agent>
```

**Builtin Sub-Agents**:
- `explore` - Read-only codebase search
- `plan` - Implementation planning
- `coder` - Code generation
- `test` - Test execution
- `memory_read` - Memory retrieval
- `memory_write` - Memory storage

### Memory: First-Class Citizen

Folder-based memory that's always available:

```
memory/
├── rules.md         # Protected constraints
├── preferences.md   # User preferences
├── facts.md         # Learned information
└── context.md       # Current session
```

## Example Agents

### 1. SWE Agent (Coding Assistant)

```yaml
name: swe_agent
model: gpt-4o

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
  - coder     # Implement changes
```

### 2. Chat Agent (Conversational Bot)

```yaml
name: chat_agent
model: gpt-4o-mini

triggers:
  - type: idle
    timeout: 300
    prompt: "Generate a new topic"

subagents:
  - memory_read   # Recall context
  - memory_write  # Store memories
  - response      # Generate replies (output_to: external)
```

### 3. Monitoring Agent (Autonomous System)

```yaml
name: monitor_agent
input: null  # No user input

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

## Installation

```bash
# Clone the repository
git clone https://github.com/KBlueLeaf/KohakuTerrarium.git
cd KohakuTerrarium

# Install with uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .
```

## Quick Start

1. **Set your API key**:
   ```bash
   export OPENROUTER_API_KEY=your_key_here
   ```

2. **Run the example SWE agent**:
   ```bash
   python -m kohakuterrarium.run agents/swe_agent
   ```

3. **Create your own agent**:
   ```bash
   mkdir my_agent
   # Create config.yaml and prompts/system.md
   python -m kohakuterrarium.run my_agent
   ```

## Architecture

```
src/kohakuterrarium/
├── core/                 # Runtime engine
│   ├── agent.py          # Main orchestrator
│   ├── controller.py     # LLM conversation loop
│   ├── executor.py       # Background job runner
│   └── events.py         # Unified event system
│
├── modules/              # Pluggable modules
│   ├── input/            # Input handlers
│   ├── trigger/          # Trigger systems
│   ├── tool/             # Tool definitions
│   ├── output/           # Output routing
│   └── subagent/         # Sub-agent system
│
├── parsing/              # Stream parsing
│   └── state_machine.py  # XML-style tool detection
│
├── builtins/             # Built-in implementations
│   ├── tools/            # bash, read, write, edit, glob, grep
│   └── subagents/        # explore, plan, coder, test, memory
│
└── prompt/               # Prompt system
    └── aggregator.py     # System prompt building
```

## Tool Call Format

KohakuTerrarium uses XML-style tool calls that work with any LLM:

```xml
<bash>ls -la</bash>

<read path="src/main.py"/>

<write path="hello.py">
print("Hello, World!")
</write>

<edit path="config.py">
  <old>debug = False</old>
  <new>debug = True</new>
</edit>
```

## Key Design Principles

1. **Controller as Orchestrator**
   - Controller dispatches tasks, doesn't do heavy work
   - Long outputs come from sub-agents
   - Keeps context lean and decisions fast

2. **Streaming First**
   - All LLM output is streaming
   - Tools start executing immediately when detected
   - Minimal latency throughout

3. **Background Everything**
   - Tools run in parallel, not sequentially
   - Sub-agents are async tasks
   - Controller continues while tools execute

4. **Unified Events**
   - Everything flows through `TriggerEvent`
   - Input, triggers, tool results, sub-agent outputs
   - Stackable for batch processing

## Documentation

- [Specification](docs/SPECIFICATION.md) - Full framework specification
- [Structure](docs/STRUCTURE.md) - Project structure guide
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md) - Development roadmap
- [Sub-Agent Design](docs/SUBAGENT_DESIGN.md) - Sub-agent system design

## Current Status

- [x] Phase 1: Core foundation (LLM, events, conversation)
- [x] Phase 2: Stream parsing (XML-style tool detection)
- [x] Phase 3: Controller loop (multi-turn conversation)
- [x] Phase 4: Tool execution (background, parallel)
- [x] Phase 5: Agent assembly (config loading, I/O)
- [ ] Phase 6: Sub-agents (nested agents)
- [ ] Phase 7: Advanced features (triggers, memory tools)
- [ ] Phase 8: Example agents (SWE, chat, monitoring)

## Why "Terrarium"?

A terrarium is a self-contained ecosystem - some fully closed and autonomous, others open to interaction. KohakuTerrarium lets you build different agent "terrariums":

- **Closed**: Monitoring systems that run autonomously
- **Open**: Coding assistants that respond to requests
- **Hybrid**: Chat bots that both respond and initiate

## Contributing

Contributions are welcome! Please read the [CLAUDE.md](CLAUDE.md) for code conventions and development guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  <i>Build agents that think, act, and remember.</i>
</p>
