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

Step 3 - Write or edit:

Create new file (include frontmatter):
<write path="[memory_path]/file.md">
---
title: Title
summary: Brief description
protected: false
updated: 2024-01-15
---
Content here
</write>

Edit existing:
<edit path="[path]">
  <old>old text</old>
  <new>new text</new>
</edit>

## Rules

- ALWAYS use tree first
- NEVER modify protected files
- ALWAYS include frontmatter for new files
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
