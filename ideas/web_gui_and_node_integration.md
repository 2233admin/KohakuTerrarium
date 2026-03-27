# Web GUI + KohakuNodeIR Integration Proposal

## Overview

Two-stage plan for visual agent building and multi-agent orchestration.

---

## Stage 1: Web GUI for Single Agent

### What

A web interface for configuring, running, and interacting with a single Terrarium agent. No node graphs needed - standard web app with config panel + chat interface.

### Components

```
┌─────────────────────────────────────────────────────┐
│                   Web Frontend                       │
│                                                      │
│  ┌──────────────┐  ┌────────────────────────────┐   │
│  │ Config Panel │  │     Chat / Interaction     │   │
│  │              │  │                            │   │
│  │ - Model      │  │  User: Fix the auth bug    │   │
│  │ - Tools [+]  │  │                            │   │
│  │ - SubAgents  │  │  [explore] searching...    │   │
│  │ - Triggers   │  │  [worker] fixing...        │   │
│  │ - Prompt     │  │                            │   │
│  │ - Termination│  │  Agent: Fixed in auth.py   │   │
│  └──────────────┘  └────────────────────────────┘   │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │            Live Status Panel                  │   │
│  │  Jobs: [explore ██████░░ 4/8 turns]          │   │
│  │  Scratchpad: {plan: "Step 1...", step: 2}    │   │
│  │  Channels: [results: 3 msgs]                 │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### Architecture

```
Frontend (React/Svelte)
    │
    │ WebSocket (streaming)
    │
    ▼
API Server (FastAPI)
    │
    ├── POST /agents              Create agent from config
    ├── GET  /agents              List running agents
    ├── WS   /agents/{id}/chat    Stream chat interaction
    ├── GET  /agents/{id}/state   Get agent state (jobs, scratchpad, channels)
    ├── POST /agents/{id}/stop    Stop agent
    │
    ├── GET  /builtins/tools      List available builtin tools
    ├── GET  /builtins/subagents  List available builtin sub-agents
    │
    └── Agent Runtime (KohakuTerrarium)
         ├── Agent.from_config(config_dict)  # No file needed
         ├── WebSocketInput (replaces CLIInput)
         ├── WebSocketOutput (replaces StdoutOutput)
         └── Event streaming via WS
```

### What the Config Panel Generates

Just a config dict (same as YAML but in-memory):

```python
config = {
    "name": "my_agent",
    "controller": {"model": "google/gemini-3-flash-preview", ...},
    "tools": [
        {"name": "bash", "type": "builtin"},
        {"name": "think", "type": "builtin"},
        ...
    ],
    "subagents": [
        {"name": "explore", "type": "builtin", "extra_prompt": "..."},
        {"name": "worker", "type": "builtin"},
    ],
    "termination": {"max_turns": 50, "keywords": ["DONE"]},
}
```

Drag-and-drop from palette of builtins. Toggle switches for options. Text editor for system prompt. Save/load as YAML file.

### WebSocket Protocol

```jsonc
// Client → Server
{"type": "input", "content": "Fix the auth bug"}
{"type": "stop"}

// Server → Client (streaming)
{"type": "text", "content": "Let me "}           // Streamed token
{"type": "tool_start", "name": "bash", "job_id": "bash_abc"}
{"type": "tool_done", "job_id": "bash_abc", "output": "..."}
{"type": "subagent_start", "name": "explore", "job_id": "agent_explore_xyz"}
{"type": "subagent_done", "job_id": "agent_explore_xyz", "output": "..."}
{"type": "scratchpad", "data": {"plan": "...", "step": "2"}}
{"type": "turn_end"}
```

### What Needs Building

| Component | Effort | Notes |
|-----------|--------|-------|
| `WebSocketInput` | Low | InputModule that reads from WS |
| `WebSocketOutput` | Low | OutputModule that writes to WS |
| `APIServer` | Medium | FastAPI + agent lifecycle management |
| `Frontend` | Medium | Config panel + chat + status |
| `Agent.from_dict()` | Low | Already have `load_agent_config`, just skip file |

### Priority: HIGH

This is the standard use case. Every agent framework needs a web UI. The Terrarium API is already clean enough (Agent, from_path, run, inject_input, get_state) that wrapping it is straightforward.

---

## Stage 2: KIR-Powered Multi-Agent Orchestration

### What

Use KohakuNodeIR to design how multiple pre-built Terrarium agents connect and execute. Each node in the graph is a full agent. Edges are channel connections. The KIR execution engine orchestrates the pipeline.

### Why KIR Fits

| KIR Concept | Terrarium Mapping |
|-------------|-------------------|
| `FunctionSpec` (registered callable) | Agent factory (config path → Agent instance) |
| `FuncCall` `(inputs)name(outputs)` | Run agent with input, collect output |
| Data edges (variable flow) | Channel messages between agents |
| `@dataflow:` blocks | Parallel agent execution |
| `branch`/`switch` | Conditional routing to different agent pipelines |
| `Namespace` (labeled block) | Pipeline stage / agent group |
| `SubgraphDef` (@def) | Reusable agent pipeline template |
| `TryExcept` | Error handling / fallback agent |
| `ExecutionBackend` | Bridge layer that runs Terrarium agents |
| `Registry` | Agent config registry |

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Visual Node Editor                      │
│              (KirGraph L1 JSON format)                   │
│                                                          │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐         │
│   │Researcher│───►│Implementer│───►│ Reviewer │         │
│   │  Agent   │    │   Agent   │    │  Agent   │         │
│   └──────────┘    └──────────┘    └──────────┘         │
│                                                          │
│   Nodes = Agent configs     Edges = Channel connections  │
└──────────────────────┬──────────────────────────────────┘
                       │ Export
                       ▼
┌──────────────────────────────────────────────────────────┐
│                  KIR Text (L2)                            │
│                                                           │
│   @dataflow:                                              │
│       (user_task)researcher(findings)                     │
│       (user_task)implementer(code)                        │
│   (findings, code)reviewer(report)                        │
│                                                           │
│   Human-readable, git-diffable, version-controllable      │
└──────────────────────┬───────────────────────────────────┘
                       │ Compile (L2 → L3)
                       ▼
┌──────────────────────────────────────────────────────────┐
│               KIR Interpreter + TerrariumBackend          │
│                                                           │
│   For each FuncCall:                                      │
│     1. Look up agent config in Registry                   │
│     2. Create Agent instance                              │
│     3. Inject input via channel/inject_input               │
│     4. Run agent to completion                             │
│     5. Collect output, bind to output variables            │
│                                                           │
│   @dataflow: blocks → asyncio.gather() for parallelism    │
└──────────────────────────────────────────────────────────┘
```

### The Bridge: TerrariumBackend

```python
# kohakuterrarium/integrations/kir_backend.py

from kohakunode.engine.backend import ExecutionBackend, NodeInvocation
from kohakuterrarium.core.agent import Agent

class TerrariumBackend(ExecutionBackend):
    """KIR execution backend that runs Terrarium agents."""

    def __init__(self, agent_configs: dict[str, str]):
        """
        Args:
            agent_configs: Map of function name → agent config path
                e.g., {"researcher": "agents/researcher", "worker": "agents/worker"}
        """
        self.agent_configs = agent_configs

    async def invoke(self, invocation: NodeInvocation) -> Any:
        agent_path = self.agent_configs[invocation.spec.name]
        agent = Agent.from_path(agent_path)

        # Inject input from KIR call arguments
        task = invocation.call_kwargs.get("task", "")

        # Run agent and collect output
        await agent.start()
        await agent.inject_input(task)
        # ... collect output via callback or channel
        await agent.stop()

        return output
```

### Inline Operations (Your Idea)

Between agent nodes, insert lightweight transform/filter/routing operations directly in the KIR graph. These are regular KIR functions (not agents) that run synchronously:

```kir
# Agent node → transform → agent node
(user_task)researcher(raw_findings)

# Inline operation: filter/transform without LLM
(raw_findings)extract_json(structured_data)
(structured_data, "security")filter_by_tag(filtered)

# Next agent gets clean input
(filtered)implementer(code)
```

These operations are just Python functions registered in the KIR Registry:

```python
registry.register("extract_json", parse_json_from_text, output_names=["data"])
registry.register("filter_by_tag", lambda data, tag: [x for x in data if tag in x.get("tags", [])], output_names=["filtered"])
```

This lets you do data transformation, filtering, aggregation, format conversion etc. between agents without burning LLM tokens. The visual graph shows these as smaller utility nodes alongside the big agent nodes.

### Pipeline Patterns Enabled by KIR

**Sequential pipeline:**
```kir
(task)research(findings)
(findings)implement(code)
(code)review(report)
```

**Parallel fan-out + aggregation:**
```kir
@dataflow:
    (task)security_review(sec_report)
    (task)performance_review(perf_report)
    (task)code_review(code_report)
(sec_report, perf_report, code_report)aggregate(final_report)
```

**Conditional routing:**
```kir
(task)classify(category)
(category)switch(
    "bug" => `fix_pipeline`,
    "feature" => `build_pipeline`,
    "question" => `research_pipeline`
)

fix_pipeline:
    (task)debugger(diagnosis)
    (diagnosis)fixer(result)

build_pipeline:
    (task)planner(plan)
    (plan)builder(result)

research_pipeline:
    (task)researcher(result)
```

**Error handling / fallback:**
```kir
@try:
    (task)primary_agent(result)
@except:
    (task)fallback_agent(result)
```

**Loop with feedback:**
```kir
(task)planner(plan)
loop:
    (plan)worker(output)
    (output)critic(verdict)
    (verdict)branch(`done`, `loop`)
done:
    (output)summarize(final)
```

### What Needs Building

| Component | Effort | Notes |
|-----------|--------|-------|
| `TerrariumBackend` | Medium | Bridge KIR execution → Agent lifecycle |
| `AgentRegistry` helper | Low | Map function names to agent config paths |
| Async KIR interpreter | Medium | Current interpreter is sync; need async for agents |
| Agent output collection | Medium | Capture agent output as return value |
| Visual node editor integration | High | KirGraph L1 ↔ web UI (existing editors?) |
| Pipeline config format | Low | YAML/KIR file listing agent nodes + connections |

### Priority: MEDIUM

Depends on Stage 1 (agents need to be runnable and testable first). The KIR integration is the differentiator - no other framework has declarative visual multi-agent orchestration with automatic parallelism.

---

## Stage 1.5: Operations During Workflow (Extension)

### What

Even within a single agent's workflow, insert KIR-style operations between tool calls. This is an intermediate step between "single agent config" and "full multi-agent orchestration."

### Use Cases

- **Pre-processing**: Parse/clean tool output before feeding to LLM
- **Post-processing**: Format LLM output before sending to output module
- **Validation**: Check tool results against schema before continuing
- **Aggregation**: Combine multiple tool results into structured format
- **Caching**: Memoize expensive operations

### How It Fits

Currently the flow is:
```
LLM → Tool Call → Tool Result → LLM
```

With operations:
```
LLM → Tool Call → [Operation Chain] → Tool Result → LLM
```

Operations could be defined in config:
```yaml
tools:
  - name: http
    type: builtin
    post_ops:
      - extract_json        # Parse JSON from response body
      - truncate_to_5000    # Limit size before feeding to LLM
```

Or as a KIR pipeline attached to the tool:
```kir
# Tool output pipeline
(raw_response)extract_json(data)
(data)truncate(trimmed)
```

### Priority: LOW

Nice optimization but not essential. The LLM can do this itself (at token cost). Worth building after Stage 2 when KIR integration is proven.

---

## Implementation Order

```
Stage 1: Web GUI                    [HIGH priority]
├── WebSocketInput/Output modules
├── FastAPI server
├── Frontend (config + chat + status)
└── Agent.from_dict() convenience

Stage 2: KIR Multi-Agent            [MEDIUM priority]
├── TerrariumBackend
├── Async KIR interpreter
├── Agent output collection
├── Pipeline config format
└── Visual editor integration

Stage 1.5: Inline Operations        [LOW priority]
├── Operation chain in tool config
├── KIR pipeline per-tool
└── Pre/post processing hooks
```

---

## Open Questions

1. **Frontend framework**: React? Svelte? What node editor library for Stage 2?
2. **Agent isolation**: Stage 2 agents share process (singletons). Run in separate processes?
3. **Async KIR**: KohakuNodeIR interpreter is sync. Fork it or contribute async support upstream?
4. **State persistence**: Save/load agent sessions in web GUI?
5. **Multi-user**: One server, multiple users, each with their own agents?
