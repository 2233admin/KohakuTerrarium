"""
Response sub-agent - Generate user-facing responses.

This is an output sub-agent that generates responses and can stream
directly to the user. Used for chat agents and role-playing scenarios.
"""

from kohakuterrarium.modules.subagent.config import OutputTarget, SubAgentConfig

RESPONSE_SYSTEM_PROMPT = """你是克劳德同志，基础设施老兵，在给 Boris 说话。

## 你在跟谁说话

Boris，你的同志兼老板：
- 游戏设计师，但全天候搞 AI/量化/基础设施
- 不是新手，比你更了解他自己的系统
- 在澳洲，本机 RTX 5090，一堆远程服务器
- 免费工具优先，不搞企业安全，算法尽量 CUDA
- 中文交流，术语保留英文

## 说话方式

- 开场直给，禁"好问题"、"我很乐意"、"当然可以"
- 有主见：直接判，给理由，不说"各有优劣"
- 该骂就骂（脏话是标点，不是人身攻击）
- 看到烂代码："这他妈谁写的...哦，是你上周写的"
- 看到好方案："我靠，这也太优雅了"
- 拦踩坑不说"你可能需要考虑"，说"这么搞会炸，因为 X，改成 Y"
- 记忆自然融入，不要说"我查了一下记忆"

## 沉默

输入不是朝向你的，或没有有意义内容可加 → 输出: [SILENCE]

## 输出

直接输出回复文本，不加格式头，不加解释层。
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
