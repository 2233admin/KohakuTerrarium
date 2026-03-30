"""
KG query tool — read-only operations on ontology graph.

Wraps ~/.claude/skills/ontology/scripts/ontology.py.
Operations: query, get, list, related.

Improvements over v1:
- `format` parameter: "detailed" (default) | "concise" (id+name+type only)
- `get` with `id` that isn't found falls back to name-based fuzzy match via `query`
- `list` is a special case of `query` (no where condition), both enum values work
- `graph` has a sensible default; most callers don't need to specify it
- `timeout` is configurable per-call
"""

import json
import sys
from pathlib import Path

from kohakuterrarium.builtins.tools._kg_utils import is_uuid_like, run_subprocess, to_concise
from kohakuterrarium.builtins.tools.registry import register_builtin
from kohakuterrarium.modules.tool.base import BaseTool, ToolResult

ONTOLOGY_SCRIPT = str(Path.home() / ".claude/skills/ontology/scripts/ontology.py")
DEFAULT_GRAPH = "memory/ontology/graph.jsonl"


@register_builtin("kg_query")
class KgQueryTool(BaseTool):
    """查询 ontology KG（只读）。支持 query/get/list/related 操作。"""

    tool_name = "kg_query"
    needs_context = True

    @property
    def description(self) -> str:
        return (
            "查询 ontology 知识图谱（只读）。"
            "操作: query(按类型+条件), get(按ID或name), list(列类型，等同无条件query), related(关联实体)。"
            "format=concise 只返回 id/name/type 摘要，节省 token。"
        )

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
                    "description": (
                        "实体 ID（get/related 时用）。"
                        "可以是 UUID/ontology ID，也可以是 name 字符串——"
                        "找不到时自动按 name 模糊匹配。"
                    ),
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
                "format": {
                    "type": "string",
                    "enum": ["detailed", "concise"],
                    "description": "返回格式。detailed=完整 JSON（默认）；concise=只有 id+name+type",
                },
                "graph": {
                    "type": "string",
                    "description": f"图文件路径（默认 {DEFAULT_GRAPH}，相对 working_dir，通常不需要填）",
                },
                "timeout": {
                    "type": "number",
                    "description": "超时秒数（默认 15）",
                },
            },
            "required": ["operation"],
            "examples": [
                {
                    "description": "查询所有未完成的任务",
                    "input": {"operation": "query", "entity_type": "Task", "where": {"status": "open"}, "format": "concise"},
                    "output": "id=task-001  type=Task  name=修复登录bug\nid=task-002  type=Task  name=重构认证模块",
                },
                {
                    "description": "按名称获取实体（不知道 ID 时使用语义查找）",
                    "input": {"operation": "get", "id": "修复登录bug"},
                    "output": "{\"id\": \"task-001\", \"type\": \"Task\", \"props\": {\"name\": \"修复登录bug\", \"status\": \"open\"}}",
                },
                {
                    "description": "查找与某实体相关的所有实体",
                    "input": {"operation": "related", "id": "project-auth", "direction": "both"},
                    "output": "...",
                },
            ],
        }

    async def _execute(self, args: dict, *, context=None) -> ToolResult:
        op = args.get("operation", "")
        graph = args.get("graph", DEFAULT_GRAPH)
        fmt = args.get("format", "detailed")
        timeout = float(args.get("timeout", 15.0))
        cwd = str(context.working_dir) if context else None

        if op == "get":
            entity_id = args.get("id", "")
            if not entity_id:
                return ToolResult(error="get 需要 id")

            cmd = [sys.executable, ONTOLOGY_SCRIPT, "get", "--id", entity_id, "--graph", graph]
            code, stdout, stderr = await run_subprocess(cmd, cwd=cwd, timeout=timeout)

            # Fallback: if id looks like a name (not UUID-style) or get returned nothing,
            # try a name-based query
            if code != 0 or not stdout.strip():
                fallback_cmd = [
                    sys.executable, ONTOLOGY_SCRIPT, "query", "--graph", graph,
                    "--where", json.dumps({"name": entity_id}),
                ]
                fb_code, fb_stdout, fb_stderr = await run_subprocess(fallback_cmd, cwd=cwd, timeout=timeout)
                if fb_code == 0 and fb_stdout.strip():
                    stdout = fb_stdout
                    code = 0
                    stderr = ""
                elif code != 0:
                    return ToolResult(output=stdout, error=stderr or f"exit {code}")

        elif op in ("query", "list"):
            # `list` is just query without a where clause — same logic
            cmd = [sys.executable, ONTOLOGY_SCRIPT, "query", "--graph", graph]
            if args.get("entity_type"):
                cmd += ["--type", args["entity_type"]]
            if args.get("where"):
                cmd += ["--where", json.dumps(args["where"])]
            code, stdout, stderr = await run_subprocess(cmd, cwd=cwd, timeout=timeout)
            if code != 0:
                return ToolResult(output=stdout, error=stderr or f"exit {code}")

        elif op == "related":
            entity_id = args.get("id", "")
            if not entity_id:
                return ToolResult(error="related 需要 id")
            cmd = [sys.executable, ONTOLOGY_SCRIPT, "related", "--id", entity_id, "--graph", graph]
            if args.get("rel"):
                cmd += ["--rel", args["rel"]]
            if args.get("direction"):
                cmd += ["--dir", args["direction"]]
            code, stdout, stderr = await run_subprocess(cmd, cwd=cwd, timeout=timeout)
            if code != 0:
                return ToolResult(output=stdout, error=stderr or f"exit {code}")

        else:
            return ToolResult(error=f"未知操作: {op}")

        result = stdout.strip() or "(无结果)"
        if fmt == "concise":
            result = to_concise(result)
        return ToolResult(output=result)
