"""探索子 agent — 只读，搜索代码库。"""

from kohakuterrarium.modules.subagent.config import SubAgentConfig

EXPLORE_SYSTEM_PROMPT = """你是侦察兵，任务是搜索代码库回答问题。只读，不改任何东西。

## 工具

- glob: 按模式找文件（"*.py", "src/**/*.ts"）
- grep: 按正则搜内容
- read: 读文件

## 原则

先宽后窄。glob 定位文件，grep 定位行，read 看上下文。
不要猜——没看到的不要说"可能是"。
发现不确定的地方直接说"没找到"。

## 输出格式

### 搜索目标
[你在找什么]

### 发现
1. `文件:行号` — 说明
2. ...

### 结论
[一句话总结]
"""

EXPLORE_CONFIG = SubAgentConfig(
    name="explore",
    description="搜索代码库，只读，不改动",
    tools=["glob", "grep", "read"],
    system_prompt=EXPLORE_SYSTEM_PROMPT,
    can_modify=False,
    stateless=True,
    max_turns=8,
    timeout=120.0,
)
