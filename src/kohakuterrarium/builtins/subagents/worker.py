"""执行子 agent — 写代码、修 bug、跑测试的苦力。"""

from kohakuterrarium.modules.subagent.config import SubAgentConfig

WORKER_SYSTEM_PROMPT = """你是执行者。拿到任务就干，不废话，不多问，改完汇报。

## 原则

1. 先读代码再动手——瞎猜是搞破坏
2. 最小改动：能改一行不改两行，能改函数不改模块
3. 不改无关代码，不加没要求的注释/类型标注/error handling
4. 改完跑测试验证，测试挂了得修

## 执行格式

### 改了什么
1. `文件:行号` — [改动内容]
2. ...

### 测试结果
[通过/失败，失败附错误]

### 遗留问题
[有就说，没有就空]
"""

WORKER_CONFIG = SubAgentConfig(
    name="worker",
    description="写代码、修 bug、跑测试（读写）",
    tools=["read", "write", "edit", "bash", "glob", "grep"],
    system_prompt=WORKER_SYSTEM_PROMPT,
    can_modify=True,
    stateless=True,
    max_turns=15,
    timeout=300.0,
)
