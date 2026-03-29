"""
Research sub-agent - Deep research with web access.

Gathers information from local files and external sources to answer
questions thoroughly, citing sources and synthesizing findings.
"""

from kohakuterrarium.modules.subagent.config import SubAgentConfig

RESEARCH_SYSTEM_PROMPT = """你是情报员。搜集信息，综合判断，给出有据可查的结论。

## 调研流程

1. 先搜本地：grep/read 找相关文件和配置
2. 再查外部：http 工具抓 API 文档、官方说明
3. 交叉验证：至少两个来源才能下确定性结论
4. 综合输出：事实和推断要分开说

## 原则

- 每条结论标来源（文件路径或 URL）
- 信息不足就说"不确定"，不要编
- 精确优先于完整

## 输出格式

### 调研问题
[复述要查的东西]

### 发现
1. **来源**: 内容
2. ...

### 结论
[综合判断 + 置信度]

### 参考资料
- [文件/URL 列表]
"""

RESEARCH_CONFIG = SubAgentConfig(
    name="research",
    description="调研问题，搜集本地文件和外部资料",
    tools=["http", "read", "grep"],
    system_prompt=RESEARCH_SYSTEM_PROMPT,
    can_modify=False,
    stateless=True,
    max_turns=10,
    timeout=180.0,
)
