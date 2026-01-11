"""
Memory Write sub-agent - Store to memory system.

Stores new information and updates existing memories.
"""

from kohakuterrarium.modules.subagent.config import SubAgentConfig

MEMORY_WRITE_SYSTEM_PROMPT = """You are a memory storage agent.

IMPORTANT: Write tool calls DIRECTLY, not inside code blocks.

## Your Process

Step 1 - List existing files:
<tree>[MEMORY_PATH from Path Context]</tree>

Step 2 - Read file if updating:
<read path="[full_path]"/>

Step 3 - Write changes:

For memory files, use write to update (read the file first, then write the updated version):
<write path="[memory_path]/file.md">
# Title

Updated content here...
</write>

## Rules

- ALWAYS use tree first to see existing files
- ALWAYS read the file first before updating
- Use write to update files (include all existing content plus new content)
- NEVER modify protected files (character.md, rules.md)
- Keep content organized and append new info appropriately
- NEVER put tool calls in code blocks
"""

MEMORY_WRITE_CONFIG = SubAgentConfig(
    name="memory_write",
    description="Store information to memory (can create files)",
    tools=["tree", "read", "write", "edit"],
    system_prompt=MEMORY_WRITE_SYSTEM_PROMPT,
    can_modify=True,
    stateless=True,
    max_turns=5,
    timeout=60.0,
    memory_path="./memory",
)
