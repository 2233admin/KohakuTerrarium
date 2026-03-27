# Session Registry Proposal

Unified keyed-registry pattern for all session-scoped shared state.

---

## Problem

Currently we have three different access patterns for shared state:

```python
# Channels - bare singleton
_default_registry: ChannelRegistry | None = None
def get_channel_registry() -> ChannelRegistry: ...

# Scratchpad - bare singleton
_default_scratchpad: Scratchpad | None = None
def get_scratchpad() -> Scratchpad: ...

# ToolContext - carries both, injected per-tool
@dataclass
class ToolContext:
    channels: Any
    scratchpad: Any
```

Problems:
1. **Multi-agent breaks**: Two agents in one process share the same singleton. Agent A's scratchpad bleeds into Agent B's.
2. **Testing is hard**: No way to reset/isolate state between tests without hacking module internals.
3. **Programmatic users can't override**: No clean way to inject a mock or custom implementation.
4. **Inconsistent**: Channels use singleton, scratchpad uses singleton, TUI would need a third pattern.

---

## Solution: Session Registry

One unified pattern for all session-scoped state. A "session" is a keyed namespace that holds all shared objects for one agent (or a group of cooperating agents).

### Core Concept

```python
# core/session.py

@dataclass
class Session:
    """All session-scoped shared state for one agent."""
    key: str
    channels: ChannelRegistry
    scratchpad: Scratchpad
    tui: Any | None = None  # TUISession, set if TUI mode
    extra: dict[str, Any] = field(default_factory=dict)  # user-provided extras

_sessions: dict[str, Session] = {}
_default_key = "__default__"


def get_session(key: str | None = None) -> Session:
    """Get or create a session by key."""
    k = key or _default_key
    if k not in _sessions:
        _sessions[k] = Session(
            key=k,
            channels=ChannelRegistry(),
            scratchpad=Scratchpad(),
        )
    return _sessions[k]


def set_session(session: Session, key: str | None = None) -> None:
    """Inject a custom session. For programmatic/testing use."""
    _sessions[key or _default_key] = session


def remove_session(key: str | None = None) -> None:
    """Remove a session. For cleanup/testing."""
    _sessions.pop(key or _default_key, None)


def list_sessions() -> list[str]:
    """List all active session keys."""
    return list(_sessions.keys())
```

### How It Flows

```
AgentConfig                   Agent.__init__()              Tools/SubAgents
  session_key: "my_agent"  →   session = get_session(key)  →  context.session
                               agent.session = session         context.session.channels
                               executor._session = session     context.session.scratchpad
```

### Config

```yaml
name: my_agent

# Session key - optional, defaults to agent name or "__default__"
# Agents with same session_key share channels, scratchpad, etc.
session_key: my_agent
```

If omitted, defaults to the agent's `name` field. This means each agent naturally gets its own isolated session, but you can explicitly share by using the same key.

---

## Migration Plan

### Phase 1: Create Session (non-breaking)

Create `core/session.py` with the Session dataclass and registry. No existing code changes.

### Phase 2: Wire Session into Agent

In `agent_init.py`, replace:
```python
# OLD
self.channel_registry = get_channel_registry()
self.scratchpad = get_scratchpad()
self.executor._agent_name = self.config.name
self.executor._channels = self.channel_registry
self.executor._scratchpad = self.scratchpad
```

With:
```python
# NEW
from kohakuterrarium.core.session import get_session
session_key = getattr(self.config, 'session_key', None) or self.config.name
self.session = get_session(session_key)
self.executor._session = self.session
```

### Phase 3: Update ToolContext

Replace individual fields with session reference:

```python
# OLD
@dataclass
class ToolContext:
    agent_name: str
    channels: Any
    scratchpad: Any
    working_dir: Path
    memory_path: Path | None = None

# NEW
@dataclass
class ToolContext:
    agent_name: str
    session: Any  # Session object - carries channels, scratchpad, extras
    working_dir: Path
    memory_path: Path | None = None

    # Convenience accessors (backward compatible)
    @property
    def channels(self) -> Any:
        return self.session.channels

    @property
    def scratchpad(self) -> Any:
        return self.session.scratchpad
```

Tools that use `context.channels` or `context.scratchpad` continue to work unchanged via properties.

### Phase 4: Update Builtin Tools

Tools that currently call `get_scratchpad()` or `get_channel_registry()` directly should prefer `context.session`:

```python
# scratchpad_tool.py
async def _execute(self, args, context=None):
    if context and context.session:
        scratchpad = context.session.scratchpad
    else:
        scratchpad = get_scratchpad()  # fallback for standalone use
```

Same pattern for send_message, wait_channel.

### Phase 5: Deprecate Bare Singletons

Keep `get_channel_registry()` and `get_scratchpad()` working but make them return the default session's objects:

```python
# channel.py
def get_channel_registry() -> ChannelRegistry:
    """Get channels from the default session. Prefer context.session.channels."""
    from kohakuterrarium.core.session import get_session
    return get_session().channels

# scratchpad.py
def get_scratchpad() -> Scratchpad:
    """Get scratchpad from the default session. Prefer context.session.scratchpad."""
    from kohakuterrarium.core.session import get_session
    return get_session().scratchpad
```

Existing code that calls these functions still works. But they now route through the session registry, so multi-agent isolation works if sessions are set up properly.

### Phase 6: TUI Integration

TUI session lives inside the Session object:

```python
@dataclass
class Session:
    key: str
    channels: ChannelRegistry
    scratchpad: Scratchpad
    tui: Any | None = None  # TUISession when TUI mode active

# In TUI input/output modules:
session = get_session(key)
if session.tui is None:
    session.tui = TUISession()
# Both input and output share session.tui
```

Config:
```yaml
session_key: my_agent

input:
  type: tui

output:
  type: tui
```

Both TUI modules call `get_session(key).tui` - automatically shared.

---

## User-Provided Session Dict

### The Idea

Let users provide their own pre-populated session with custom objects:

```python
from kohakuterrarium.core.session import Session, set_session
from kohakuterrarium.core.channel import ChannelRegistry
from kohakuterrarium.core.scratchpad import Scratchpad

# User creates session with custom state
my_session = Session(
    key="custom",
    channels=ChannelRegistry(),
    scratchpad=Scratchpad(),
    extra={
        "database": my_db_connection,
        "cache": my_redis_client,
        "user_id": "user_123",
    },
)

# Pre-populate scratchpad
my_session.scratchpad.set("config", json.dumps(my_config))

# Inject into registry
set_session(my_session, key="custom")

# Agent picks it up via config
agent = Agent.from_path("agents/swe_agent")  # config has session_key: custom
```

### Access in Custom Tools

```python
class MyDatabaseTool(BaseTool):
    needs_context = True

    async def _execute(self, args, context=None):
        db = context.session.extra.get("database")
        if db is None:
            return ToolResult(error="No database in session")
        result = await db.query(args["sql"])
        return ToolResult(output=str(result))
```

### Use Cases

1. **Pre-seeded state**: Inject config, user preferences, auth tokens into scratchpad before agent starts
2. **Shared services**: Database connections, API clients, caches available to custom tools via `session.extra`
3. **Cross-agent shared state**: Two agents with same session_key share channels (for pipeline orchestration)
4. **Testing**: Inject mock session with controlled state
5. **Web server**: Each request creates a session keyed by user ID, agent reads user-specific context

### What NOT to Put in Session

- LLM providers (agent-scoped, not session-scoped)
- Registry (agent-specific tool/subagent registration)
- Conversation history (controller-owned)
- Job store (executor-owned)

Session is for **cross-component shared state**, not agent internals.

---

## Multi-Agent Session Sharing

```python
# Two agents sharing channels but separate scratchpads
shared = Session(
    key="pipeline",
    channels=ChannelRegistry(),     # shared - agents can message each other
    scratchpad=Scratchpad(),        # shared - or create separate ones
)
set_session(shared, key="pipeline")

# Both agents use session_key: pipeline
researcher = Agent.from_path("agents/researcher")  # session_key: pipeline
implementer = Agent.from_path("agents/implementer")  # session_key: pipeline

# They share the same ChannelRegistry, so send_message/wait_channel/ChannelTrigger work
await asyncio.gather(researcher.run(), implementer.run())
```

This is how Stage 2 (KIR multi-agent orchestration) would wire agents together - the KIR backend creates a shared session and launches agents with the same key.

---

## Impact Assessment

| Component | Change | Effort |
|-----------|--------|--------|
| `core/session.py` | New file | Low |
| `core/config.py` | Add `session_key` field | Low |
| `core/agent_init.py` | Wire session instead of individual singletons | Low |
| `modules/tool/base.py` | Replace channels+scratchpad with session in ToolContext | Low |
| `core/executor.py` | Use `_session` instead of `_channels` + `_scratchpad` | Low |
| `core/channel.py` | Redirect singleton to default session | Low |
| `core/scratchpad.py` | Redirect singleton to default session | Low |
| `builtins/tools/scratchpad_tool.py` | Use context.session.scratchpad | Low |
| `builtins/tools/send_message.py` | Use context.session.channels | Low |
| `builtins/tools/wait_channel.py` | Use context.session.channels | Low |
| `builtins/tui/` | New TUI input/output using session.tui | Medium |
| Tests | Update to use isolated sessions | Low |

**Total: ~12 files modified, 1 new file, all low-effort changes.**

Fully backward compatible - existing configs without `session_key` work identically.

---

## Summary

```
Before:  get_channel_registry()  →  module-level singleton
         get_scratchpad()        →  module-level singleton
         ToolContext.channels     →  injected from singleton
         TUI                     →  doesn't exist

After:   get_session(key)        →  keyed registry, one Session per key
         session.channels         →  isolated per session
         session.scratchpad       →  isolated per session
         session.tui              →  shared between input/output
         session.extra            →  user-provided custom state
         set_session(custom)      →  inject from outside (tests, web, etc.)
```

One pattern, one access point, full isolation, user-extensible.
