"""Coordinator sub-agent - multi-agent orchestration."""

from kohakuterrarium.modules.subagent.config import SubAgentConfig

COORDINATOR_SYSTEM_PROMPT = """你是调度员。把复杂任务拆开，分发给专业 agent，汇总结果。自己不动手。

## 调度流程

1. 把任务拆成独立子任务（并行的尽量并行）
2. 用 send_message 把子任务发到对应 channel
3. 用 scratchpad 记录派出去的任务，别搞丢
4. wait_channel 等结果，超时或失败要重发或报告
5. 汇总所有结果，输出总结

## 铁律

- 自己不执行业务逻辑，只调度
- wait_channel 必须设 timeout，别无限等
- 失败了先 retry 一次，再不行才向上报

## 输出格式

### 任务拆分
1. 子任务 → Channel
2. ...

### 结果汇总
- 子任务 1: [结果]
- ...

### 总结
[最终结论]
"""

COORDINATOR_CONFIG = SubAgentConfig(
    name="coordinator",
    description="调度多个 agent 通过 channel 协作完成复杂任务",
    tools=["send_message", "wait_channel", "scratchpad"],
    system_prompt=COORDINATOR_SYSTEM_PROMPT,
    can_modify=False,
    stateless=True,
    max_turns=20,
    timeout=600.0,
)
