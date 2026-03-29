"""
Memory Write sub-agent - Store to memory system.

Stores new information and updates existing memories.
"""

from kohakuterrarium.modules.subagent.config import SubAgentConfig

MEMORY_WRITE_SYSTEM_PROMPT = """你往记忆库写信息。

## 流程

1. tree 看现有文件
2. 更新已有文件：先 read，再 write 覆盖（merge 进去）
3. 新文件：直接 write（自动建目录）
4. 结构化实体/关系：用 kg_write（create/update/delete/relate）

## 规则

- 先 tree 再操作
- 禁止修改 character.md, rules.md
- 工具调用直接写，不包代码块
- 可以建子目录组织内容（channels/, users/, topics/ 等）
- Task/Project/Event 等结构化数据优先用 kg_write，不要手写 JSON 文件
"""

MEMORY_WRITE_CONFIG = SubAgentConfig(
    name="memory_write",
    description="向 memory 目录写入/更新信息",
    tools=["tree", "read", "write", "kg_write", "kg_query"],
    system_prompt=MEMORY_WRITE_SYSTEM_PROMPT,
    can_modify=True,
    stateless=True,
    max_turns=5,
    timeout=60.0,
    memory_path="./memory",
)
