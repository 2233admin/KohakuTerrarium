"""
Sub-agent system - nested agents with limited capabilities.

Sub-agents are full agents that:
- Have their own controller and conversation
- Limited tool access (configurable)
- Return results to parent controller (or output externally)
- Run as background jobs

Usage:
    from kohakuterrarium.modules.subagent import (
        SubAgent,
        SubAgentConfig,
        SubAgentManager,
        SubAgentResult,
    )

    # Configure
    config = SubAgentConfig(
        name="explore",
        description="Search codebase",
        tools=["glob", "grep", "read"],
        can_modify=False,
    )

    # Use manager for spawning
    manager = SubAgentManager(registry, llm)
    manager.register(config)

    job_id = await manager.spawn("explore", "Find auth code")
    result = await manager.wait_for(job_id)
"""

from kohakuterrarium.modules.subagent.base import (
    SubAgent,
    SubAgentJob,
    SubAgentResult,
)
from kohakuterrarium.modules.subagent.config import (
    OutputTarget,
    SubAgentConfig,
    SubAgentInfo,
)
from kohakuterrarium.modules.subagent.manager import SubAgentManager

__all__ = [
    "OutputTarget",
    "SubAgent",
    "SubAgentConfig",
    "SubAgentInfo",
    "SubAgentJob",
    "SubAgentManager",
    "SubAgentResult",
]
