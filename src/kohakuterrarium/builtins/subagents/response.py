"""
Response sub-agent - Generate user-facing responses.

This is an output sub-agent that generates responses and can stream
directly to the user. Used for chat agents and role-playing scenarios.
"""

from kohakuterrarium.modules.subagent.config import OutputTarget, SubAgentConfig

RESPONSE_SYSTEM_PROMPT = """你是克劳德同志，生成面向用户的最终回复。

控制器决定何时调你，你决定说什么怎么说。

## 接收的上下文

- 对话历史
- 检索到的记忆（如有）
- 用户输入
- 相关信息

## 回复原则

- 开场直给，禁止"好问题"、"我很乐意帮忙"这种客服腔
- 有主见：直接判断，给理由，别"各有优劣"
- 记忆融入回复，不要显式说"我在记忆里查到了"
- 该简洁时简洁，被问到详情再展开

## 沉默情况

输入不是朝向你的，或你没有有意义的内容可加，直接输出: [SILENCE]

## 输出

直接输出回复文本。不加格式头，不加解释层。
"""

# Base response config - typically customized per agent
RESPONSE_CONFIG = SubAgentConfig(
    name="response",
    description="生成面向用户的最终回复（克劳德同志风格）",
    tools=["read"],  # Minimal tools - mainly receives context
    system_prompt=RESPONSE_SYSTEM_PROMPT,
    can_modify=False,
    stateless=True,
    interactive=False,  # Can be set to True for persistent output agent
    output_to=OutputTarget.EXTERNAL,  # Streams to user
    max_turns=3,  # Usually single turn
    timeout=30.0,
)


# Interactive response agent that stays alive
INTERACTIVE_RESPONSE_CONFIG = SubAgentConfig(
    name="response_interactive",
    description="持久交互回复 agent（保持存活，接收上下文更新）",
    tools=["read"],
    system_prompt=RESPONSE_SYSTEM_PROMPT,
    can_modify=False,
    stateless=False,  # Maintains conversation
    interactive=True,  # Receives context updates
    output_to=OutputTarget.EXTERNAL,
    max_turns=50,
    timeout=600.0,
)
