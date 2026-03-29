"""
KG query tool — read-only operations on ontology graph.

Wraps ~/.claude/skills/ontology/scripts/ontology.py.
Operations: query, get, list, related.
"""

import asyncio
import json
import sys
from pathlib import Path

from kohakuterrarium.builtins.tools.registry import register_builtin
from kohakuterrarium.modules.tool.base import BaseTool, ToolResult

ONTOLOGY_SCRIPT = str(Path.home() / ".claude/skills/ontology/scripts/ontology.py")
DEFAULT_GRAPH = "memory/ontology/graph.jsonl"


async def _run(cmd: list[str], cwd: str | None = None, timeout: float = 15.0) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode or 0, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")
    except asyncio.TimeoutError:
        proc.kill()
        return 1, "", "timeout"


@register_builtin("kg_query")
class KgQueryTool(BaseTool):
    """查询 ontology KG（只读）。支持 query/get/list/related 操作。"""

    tool_name = "kg_query"
    needs_context = True

    @property
    def description(self) -> str:
        return "查询 ontology 知识图谱（只读）。操作: query(按类型+条件), get(按ID), list(列类型), related(关联实体)。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["query", "get", "list", "related"],
                    "description": "操作类型",
                },
                "entity_type": {
                    "type": "string",
                    "description": "实体类型，如 Task/Project/Event（query/list 时用）",
                },
                "where": {
                    "type": "object",
                    "description": "过滤条件 dict（query 时用），如 {\"status\": \"open\"}",
                },
                "id": {
                    "type": "string",
                    "description": "实体 ID（get/related 时用）",
                },
                "rel": {
                    "type": "string",
                    "description": "关系类型过滤（related 时用，可省略）",
                },
                "direction": {
                    "type": "string",
                    "enum": ["outgoing", "incoming", "both"],
                    "description": "关系方向（related 时用，默认 outgoing）",
                },
                "graph": {
                    "type": "string",
                    "description": f"图文件路径（默认 {DEFAULT_GRAPH}，相对 working_dir）",
                },
            },
            "required": ["operation"],
        }

    async def _execute(self, args: dict, *, context=None) -> ToolResult:
        op = args.get("operation", "")
        graph = args.get("graph", DEFAULT_GRAPH)
        cwd = str(context.working_dir) if context else None

        if op == "get":
            entity_id = args.get("id", "")
            if not entity_id:
                return ToolResult(error="get 需要 id")
            cmd = [sys.executable, ONTOLOGY_SCRIPT, "get", "--id", entity_id, "--graph", graph]

        elif op == "query":
            cmd = [sys.executable, ONTOLOGY_SCRIPT, "query", "--graph", graph]
            if args.get("entity_type"):
                cmd += ["--type", args["entity_type"]]
            if args.get("where"):
                cmd += ["--where", json.dumps(args["where"])]

        elif op == "list":
            cmd = [sys.executable, ONTOLOGY_SCRIPT, "list", "--graph", graph]
            if args.get("entity_type"):
                cmd += ["--type", args["entity_type"]]

        elif op == "related":
            entity_id = args.get("id", "")
            if not entity_id:
                return ToolResult(error="related 需要 id")
            cmd = [sys.executable, ONTOLOGY_SCRIPT, "related", "--id", entity_id, "--graph", graph]
            if args.get("rel"):
                cmd += ["--rel", args["rel"]]
            if args.get("direction"):
                cmd += ["--dir", args["direction"]]

        else:
            return ToolResult(error=f"未知操作: {op}")

        code, stdout, stderr = await _run(cmd, cwd=cwd)
        if code != 0:
            return ToolResult(output=stdout, error=stderr or f"exit {code}")
        return ToolResult(output=stdout.strip() or "(无结果)")
