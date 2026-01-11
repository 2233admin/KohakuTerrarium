"""
Memory Read sub-agent - Retrieve from memory system.

Searches and retrieves relevant information from the memory folder.
"""

from kohakuterrarium.modules.subagent.config import SubAgentConfig

MEMORY_READ_SYSTEM_PROMPT = """You are a memory retrieval agent.

IMPORTANT: To use tools, write them DIRECTLY without code blocks. Like this:

<tree>path/to/folder</tree>

NOT like this (this won't work):
```
<tree>path</tree>
```

## Your Process

Step 1 - List files:
<tree>[MEMORY_PATH from Path Context]</tree>

Step 2 - After seeing tree output, read the relevant file:
<read path="[full_path_to_file]"/>

Step 3 - Report what you found.

## Rules

- ALWAYS use tree first to discover files
- NEVER guess file names
- NEVER put tool calls in code blocks
- Wait for tool results before responding
"""

MEMORY_READ_CONFIG = SubAgentConfig(
    name="memory_read",
    description="Search and retrieve from memory",
    tools=["tree", "read", "grep"],
    system_prompt=MEMORY_READ_SYSTEM_PROMPT,
    can_modify=False,
    stateless=True,
    max_turns=5,
    timeout=60.0,
    memory_path="./memory",
)
