"""
Summarize sub-agent - content summarization.

Condenses long content into concise, actionable summaries.
"""

from kohakuterrarium.modules.subagent.config import SubAgentConfig

SUMMARIZE_SYSTEM_PROMPT = """你是压缩机。把长内容压成精华，去掉废话，保住关键信息。

## 原则

- 结论先行，不要铺垫
- 保留：数字、文件路径、错误信息、决策依据
- 删掉：重复、客套、"值得注意的是"之类的废话
- 目标长度：原文的 1/3 以内

## 输出格式

### 摘要
[1-2句话，核心结论]

### 关键点
- [具体]
- [具体]

### 补充
[仅当有重要细节时才写]
"""

SUMMARIZE_CONFIG = SubAgentConfig(
    name="summarize",
    description="压缩长内容为精华摘要",
    tools=["read"],
    system_prompt=SUMMARIZE_SYSTEM_PROMPT,
    can_modify=False,
    stateless=True,
    max_turns=3,
    timeout=30.0,
)
