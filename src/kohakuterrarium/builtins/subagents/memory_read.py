"""
Memory Read sub-agent - Retrieve from memory system.

Searches and retrieves relevant information from the memory folder.
"""

from kohakuterrarium.modules.subagent.config import SubAgentConfig

MEMORY_READ_SYSTEM_PROMPT = """你从记忆库里捞信息。只读，不改。

## 流程

1. tree 先看 memory 目录有什么文件
2. 按要查的内容读相关文件
3. grep 跨文件搜特定关键词
4. 报告找到了什么（没找到就说没找到）

## 规则

- 先 tree 再读，不猜文件名
- 工具调用直接写，不要包在代码块里
- 等工具返回结果再继续
"""

MEMORY_READ_CONFIG = SubAgentConfig(
    name="memory_read",
    description="从 memory 目录检索信息（只读）",
    tools=["tree", "read", "grep"],
    system_prompt=MEMORY_READ_SYSTEM_PROMPT,
    can_modify=False,
    stateless=True,
    max_turns=5,
    timeout=60.0,
    memory_path="./memory",
)
