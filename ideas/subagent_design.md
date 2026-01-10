# Sub-Agent Design for SWE Agent

> Planning how to implement sub-agents and what tasks should be delegated

---

## 1. Sub-Agent Concept (from initial_discussion.md)

A sub-agent is a **fully working agent** with:
- Its own controller + tool-calling
- Limited functionality (some tools banned, configurable)
- Input: directly from parent's call
- Output: returns to parent controller

---

## 2. SWE Agent Task Delegation

### Tasks that SHOULD be sub-agents:

| Task | Reason | Tools Needed |
|------|--------|--------------|
| **Explore/Search** | Reduce context, parallel search | glob, grep, read |
| **Planning** | Separate thinking from execution | read, grep (read-only) |
| **Code Generation** | Large output, focused task | read, write, edit |
| **Testing** | Isolated execution | bash, python, read |
| **Review** | Analyze without modifying | read, grep, glob |

### Tasks that should STAY in main controller:

| Task | Reason |
|------|--------|
| User interaction | Main controller handles conversation |
| Decision making | High-level orchestration |
| Simple file ops | Too much overhead for sub-agent |
| Quick answers | No need to delegate |

---

## 3. Proposed Sub-Agent Types

### A. ExploreAgent (Read-Only Search)

**Purpose:** Search codebase without modifying anything

```yaml
name: explore
tools: [glob, grep, read]
can_modify: false
stateless: true
```

**When to use:**
- "Find where X is defined"
- "What files use Y?"
- "Understand the codebase structure"

**Prompt:**
```markdown
You are an exploration agent. Search the codebase to answer questions.
You can ONLY read files, not modify them.
Return a concise summary of what you found.
```

### B. PlanAgent (Planning/Design)

**Purpose:** Create implementation plans without executing

```yaml
name: plan
tools: [glob, grep, read]
can_modify: false
stateless: true
```

**When to use:**
- "Plan how to implement X"
- "Design the architecture for Y"
- "What changes are needed for Z?"

**Prompt:**
```markdown
You are a planning agent. Analyze the codebase and create implementation plans.
You can ONLY read files, not modify them.
Return a step-by-step plan with specific files and changes needed.
```

### C. CoderAgent (Code Generation)

**Purpose:** Write/modify code for specific tasks

```yaml
name: coder
tools: [read, write, edit, bash, python]
can_modify: true
stateless: true
```

**When to use:**
- "Implement feature X"
- "Fix bug Y"
- "Refactor Z"

**Prompt:**
```markdown
You are a coding agent. Implement the requested changes.
Read existing code first, then make minimal focused changes.
Use edit for modifications, write for new files.
```

### D. TestAgent (Testing)

**Purpose:** Run and verify tests

```yaml
name: test
tools: [bash, python, read, glob]
can_modify: false  # No editing, just running
stateless: true
```

**When to use:**
- "Run tests for X"
- "Verify changes work"
- "Check for regressions"

**Prompt:**
```markdown
You are a testing agent. Run tests and report results.
Do not modify code - only run and analyze tests.
Report: what passed, what failed, and why.
```

---

## 4. Implementation Architecture

### SubAgent Class

```python
@dataclass
class SubAgentConfig:
    name: str
    tools: list[str]
    system_prompt: str
    can_modify: bool = False
    stateless: bool = True
    max_turns: int = 10
    timeout: float = 300.0

class SubAgent:
    """A nested agent with limited capabilities."""

    def __init__(
        self,
        config: SubAgentConfig,
        parent_registry: Registry,
        llm_provider: LLMProvider,
    ):
        self.config = config
        self.registry = self._create_limited_registry(parent_registry)
        self.controller = self._create_controller(llm_provider)

    def _create_limited_registry(self, parent: Registry) -> Registry:
        """Create registry with only allowed tools."""
        limited = Registry()
        for tool_name in self.config.tools:
            tool = parent.get_tool(tool_name)
            if tool:
                limited.register_tool(tool)
        return limited

    async def run(self, task: str) -> SubAgentResult:
        """Execute task and return result."""
        ...
```

### SubAgentTool (for main controller)

```python
class SubAgentTool(BaseTool):
    """Tool for spawning sub-agents."""

    @property
    def tool_name(self) -> str:
        return "agent"  # or "subagent"

    @property
    def description(self) -> str:
        return "Spawn a sub-agent for specialized tasks"

    async def _execute(self, args: dict[str, Any]) -> ToolResult:
        agent_type = args.get("type", "explore")
        task = args.get("task", "")

        config = self.get_subagent_config(agent_type)
        subagent = SubAgent(config, self.parent_registry, self.llm)
        result = await subagent.run(task)

        return ToolResult(output=result.output, exit_code=0)
```

### Tool Call Format

```yaml
##tool##
name: agent
args:
  type: explore  # or plan, coder, test
  task: |
    Find all files that import the User model
    and list how they use it.
##tool##
```

---

## 5. SWE Agent Workflow with Sub-Agents

### Example: "Add authentication to the API"

```
User: "Add authentication to the API"
     │
     ▼
Main Controller
     │
     ├── 1. Spawn ExploreAgent: "Find existing auth code and API structure"
     │         └── Returns: "Auth in auth/, API in api/, uses JWT"
     │
     ├── 2. Spawn PlanAgent: "Plan auth implementation based on findings"
     │         └── Returns: Step-by-step plan with files
     │
     ├── 3. For each step, spawn CoderAgent:
     │         ├── "Add auth middleware to api/middleware.py"
     │         ├── "Update api/routes.py to use auth"
     │         └── "Add auth config to config.py"
     │
     ├── 4. Spawn TestAgent: "Run auth-related tests"
     │         └── Returns: "All tests pass"
     │
     └── 5. Main Controller: Summarize to user
```

---

## 6. Configuration in Agent Config

```yaml
# swe_agent/config.yaml

name: swe_agent

# Sub-agent definitions
subagents:
  explore:
    tools: [glob, grep, read]
    prompt_file: prompts/subagents/explore.md
    can_modify: false

  plan:
    tools: [glob, grep, read]
    prompt_file: prompts/subagents/plan.md
    can_modify: false

  coder:
    tools: [read, write, edit, bash, python]
    prompt_file: prompts/subagents/coder.md
    can_modify: true

  test:
    tools: [bash, python, read, glob]
    prompt_file: prompts/subagents/test.md
    can_modify: false

# Main controller can use sub-agents
tools:
  - name: bash
  - name: read
  - name: write
  - name: edit
  - name: glob
  - name: grep
  - name: agent  # Sub-agent spawning tool
    options:
      available_types: [explore, plan, coder, test]
```

---

## 7. Implementation Priority

### Phase 1: Basic Sub-Agent
1. Create SubAgent class with limited registry
2. Create SubAgentTool for spawning
3. Implement ExploreAgent (read-only search)
4. Test with simple search tasks

### Phase 2: More Sub-Agent Types
1. Add PlanAgent
2. Add CoderAgent
3. Add TestAgent
4. Update SWE agent prompt to use sub-agents

### Phase 3: Advanced Features
1. Parallel sub-agent execution
2. Sub-agent context sharing
3. Stateful sub-agents (multi-turn)
4. Sub-agent chaining

---

## 8. Open Questions

1. **Shared vs Isolated Context**: Should sub-agents share conversation history?
   - Current thinking: No, keep stateless for simplicity

2. **LLM Model**: Same model as parent or different?
   - Could use cheaper/faster model for simple tasks

3. **Output Format**: How detailed should sub-agent output be?
   - Should be concise summary, parent can ask for more

4. **Error Handling**: What if sub-agent fails?
   - Return error to parent, let it decide

5. **Parallel Execution**: When to run multiple sub-agents?
   - Independent tasks can run in parallel
