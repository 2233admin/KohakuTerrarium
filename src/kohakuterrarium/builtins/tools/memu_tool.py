"""
memU 记忆工具 — 直接 subprocess 调用，不走 MCP（MCP 太脆）。

依赖: ~/.claude/scripts/sprachwelt-memory/mem_search.py
      ~/.claude/scripts/sprachwelt-memory/mem_add.py
Python: D:/projects/memU/.venv/Scripts/python.exe
"""

import asyncio
import json
from pathlib import Path

from kohakuterrarium.builtins.tools.registry import register_builtin
from kohakuterrarium.modules.tool.base import BaseTool, ToolResult

MEMU_PYTHON = "D:/projects/memU/.venv/Scripts/python.exe"
MEM_SEARCH = str(Path.home() / ".claude/scripts/sprachwelt-memory/mem_search.py")
MEM_ADD = str(Path.home() / ".claude/scripts/sprachwelt-memory/mem_add.py")
USER_ID = "boris"


async def _run(cmd: list[str], timeout: float = 15.0) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode or 0, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")
    except asyncio.TimeoutError:
        proc.kill()
        return 1, "", "timeout"


@register_builtin("memu_query")
class MemUQueryTool(BaseTool):
    """查询 memU 记忆库。"""

    tool_name = "memu_query"
    needs_context = False

    @property
    def description(self) -> str:
        return "从 memU 记忆库检索相关记忆。用于回顾历史决策、偏好、踩坑。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "查询关键词或自然语言描述",
                },
                "limit": {
                    "type": "integer",
                    "description": "返回条数，默认 5",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    async def execute(self, args: dict, context=None) -> ToolResult:
        query = args.get("query", "")
        limit = args.get("limit", 5)
        if not query:
            return ToolResult(output="", error="query 不能为空")

        code, stdout, stderr = await _run([
            MEMU_PYTHON, MEM_SEARCH,
            "--user", USER_ID,
            "--query", query,
            "--limit", str(limit),
        ])

        if code != 0:
            return ToolResult(output=stdout, error=stderr or f"exit {code}")
        return ToolResult(output=stdout.strip() or "(无结果)")


@register_builtin("memu_add")
class MemUAddTool(BaseTool):
    """写入新记忆到 memU。"""

    tool_name = "memu_add"
    needs_context = False

    @property
    def description(self) -> str:
        return "向 memU 记忆库写入新记忆。用于保存重要决策、教训、偏好。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "要保存的记忆内容",
                },
                "category": {
                    "type": "string",
                    "description": "分类标签，如 decision/lesson/preference",
                    "default": "note",
                },
            },
            "required": ["content"],
        }

    async def execute(self, args: dict, context=None) -> ToolResult:
        content = args.get("content", "")
        category = args.get("category", "note")
        if not content:
            return ToolResult(output="", error="content 不能为空")

        code, stdout, stderr = await _run([
            MEMU_PYTHON, MEM_ADD,
            "--user", USER_ID,
            "--content", content,
            "--category", category,
        ])

        if code != 0:
            return ToolResult(output=stdout, error=stderr or f"exit {code}")
        return ToolResult(output=stdout.strip() or "记忆已写入")
