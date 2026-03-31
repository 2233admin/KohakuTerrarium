# Execution Model

How agents process events, execute tools, and deliver results at runtime.

## Event Sources

An agent has three concurrent event sources. All converge on `_process_event()`, serialized by a processing lock.

```
                  +-------------------+
                  |  _process_event() |  <-- asyncio.Lock serializes
                  +-------------------+
                    ^       ^       ^
                    |       |       |
              +-----+  +---+---+  +--------+
              |Input |  |Trigger|  |BG Tool |
              |Loop  |  |Tasks  |  |Callback|
              +------+  +-------+  +--------+
```

**Input loop** (`agent.run()`): The main loop. Blocks on `input.get_input()` waiting for user messages. When a message arrives, calls `_process_event()`.

**Trigger tasks**: Each trigger (channel message, timer, etc.) runs as a separate `asyncio.Task` created during `agent.start()`. When a trigger fires, it calls `_process_event()` directly -- does NOT go through the input loop.

**Background tool callback**: When a background tool or sub-agent finishes, the executor calls `_on_bg_complete()` which creates a new `asyncio.Task` calling `_process_event()`. Same delivery path as triggers.

The `_processing_lock` ensures only one `_process_event` runs at a time. If a trigger fires while an LLM turn is in progress, it waits for the lock.

## Processing Loop

`_process_event()` handles one event and all its direct tool calls. It loops only while there is immediate feedback to deliver.

```
PHASE 1  Reset output router state

PHASE 2  Run controller.run_once() (LLM generation + parsing)
         For each parse event:
         +-- ToolCallEvent (direct)     -> start task, track for waiting
         +-- ToolCallEvent (background) -> start task, add placeholder to conversation
         +-- SubAgentCallEvent          -> start sub-agent (always background)
         +-- TextEvent                  -> route to output
         +-- CommandResultEvent         -> activity notification

PHASE 3  Termination check (max_turns, keywords, duration)

PHASE 4  Collect feedback
         +-- Output feedback (what was sent to named outputs)
         +-- Direct tool results (awaited)

PHASE 5  Exit if no feedback
         Otherwise push feedback to controller, loop to PHASE 1
```

The loop exits when there is nothing immediate to process. Background jobs do NOT block exit.

## Tool Execution Modes

| Mode | How declared | Behavior |
|------|-------------|----------|
| **Direct** | `execution_mode = DIRECT` | Processing loop waits for result, feeds it back to LLM in same turn |
| **Forced background** | `execution_mode = BACKGROUND` | Placeholder response added to conversation. Result delivered later via `_on_bg_complete` |
| **Opt-in background** | Model passes `run_in_background=True` | Same as forced background, but decided per-call by the model |

Direct is the default. The model gets the result immediately and can use it to decide next steps.

Forced background cannot be overridden by the model. Used for tools that wait indefinitely for external events (e.g. `terrarium_observe` waiting for a channel message).

## Background Tool Lifecycle

```
1. LLM calls terrarium_observe(channel=results)
2. Tool declares BACKGROUND mode -> forced background
3. Executor starts asyncio.Task running the tool
4. Placeholder added to conversation: "Running in background"
5. Processing loop sees no more direct feedback -> exits
6. Agent returns to idle (input.get_input())

   ... time passes, creatures work ...

7. Channel message arrives, terrarium_observe receives it
8. Executor._run_tool() completes, calls _on_complete callback
9. _on_bg_complete() creates asyncio.create_task(_process_event(result))
10. _processing_lock acquired, LLM runs with the result
11. LLM summarizes result for user
12. Processing loop exits, agent returns to idle
```

Between steps 6 and 9, the agent is fully idle. It can receive user input or other trigger events. The background tool runs concurrently without blocking anything.

## Terrarium Creature Event Flow

Creatures inside a terrarium use triggers for inter-creature communication:

```
Creature A calls send_message(channel="review", message="...")
    |
    v
Channel "review" receives message
    |
    v
Creature B has ChannelTrigger on "review"
    -> trigger.wait_for_trigger() returns TriggerEvent
    -> _process_event(event) fires on Creature B
    -> Creature B's LLM sees the message and responds
```

Each creature has `NoneInput` (blocks forever). All creature activity comes through triggers. The terrarium injects `ChannelTrigger` instances during setup.

## Root Agent Event Flow

The root agent sits OUTSIDE the terrarium. It uses tools (not triggers) to interact:

```
User: "Fix the auth bug"
    |
    v
Root agent (via input loop):
    -> LLM calls terrarium_send(channel=tasks, message="Fix auth")  [direct]
    -> LLM calls terrarium_observe(channel=results)                  [forced bg]
    -> terrarium_send result fed back immediately
    -> terrarium_observe gets placeholder "Running in background"
    -> LLM responds: "Task dispatched. I'll report when results arrive."
    -> No more feedback -> loop exits
    -> Root returns to idle

   ... swe creature works, posts to results channel ...

terrarium_observe receives message -> _on_bg_complete fires:
    -> _process_event(tool_complete with result)
    -> LLM sees result, summarizes for user
    -> "The team fixed the auth bug. Here's what they changed: ..."
```

## Concurrency Model

- **Within one agent**: Single-threaded async. One `_process_event` at a time (lock). Multiple tools run concurrently via `asyncio.Task`.
- **Between creatures**: Fully concurrent. Each creature has its own agent, own lock, own LLM calls. Communication is explicit via channels.
- **Root vs terrarium**: Root agent and creatures run concurrently. Root's background tools (`terrarium_observe`) bridge the two.
