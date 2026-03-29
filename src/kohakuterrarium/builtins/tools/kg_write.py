"""
KG write tool — mutating operations on ontology graph.

Wraps ~/.claude/skills/ontology/scripts/ontology.py.
Operations: create, update, delete, relate.
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


@register_builtin("kg_write")
class KgWriteTool(BaseTool):
    """向 ontology KG 写入/更新实体和关系。操作: create/update/delete/relate。"""

    tool_name = "kg_write"
    needs_context = True

    @property
    def description(self) -> str:
        return "操作 ontology 知识图谱（写入）。操作: create(建实体), update(改属性), delete(删实体), relate(建关系)。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["create", "update", "delete", "relate"],
                    "description": "操作类型",
                },
                "entity_type": {
                    "type": "string",
                    "description": "实体类型，如 Task/Project/Event（create 时必填）",
                },
                "props": {
                    "type": "object",
                    "description": "实体属性 dict（create/update 时用）",
                },
                "id": {
                    "type": "string",
                    "description": "实体 ID（update/delete 时必填，create 时可选自定义）",
                },
                "from_id": {
                    "type": "string",
                    "description": "关系起点实体 ID（relate 时必填）",
                },
                "rel": {
                    "type": "string",
                    "description": "关系类型，如 has_task/blocks/depends_on（relate 时必填）",
                },
                "to_id": {
                    "type": "string",
                    "description": "关系终点实体 ID（relate 时必填）",
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

        if op == "create":
            entity_type = args.get("entity_type", "")
            if not entity_type:
                return ToolResult(error="create 需要 entity_type")
            cmd = [
                sys.executable, ONTOLOGY_SCRIPT, "create",
                "--type", entity_type,
                "--props", json.dumps(args.get("props") or {}),
                "--graph", graph,
            ]
            if args.get("id"):
                cmd += ["--id", args["id"]]

        elif op == "update":
            entity_id = args.get("id", "")
            props = args.get("props")
            if not entity_id:
                return ToolResult(error="update 需要 id")
            if not props:
                return ToolResult(error="update 需要 props")
            cmd = [
                sys.executable, ONTOLOGY_SCRIPT, "update",
                "--id", entity_id,
                "--props", json.dumps(props),
                "--graph", graph,
            ]

        elif op == "delete":
            entity_id = args.get("id", "")
            if not entity_id:
                return ToolResult(error="delete 需要 id")
            cmd = [sys.executable, ONTOLOGY_SCRIPT, "delete", "--id", entity_id, "--graph", graph]

        elif op == "relate":
            from_id = args.get("from_id", "")
            rel = args.get("rel", "")
            to_id = args.get("to_id", "")
            if not (from_id and rel and to_id):
                return ToolResult(error="relate 需要 from_id, rel, to_id")
            cmd = [
                sys.executable, ONTOLOGY_SCRIPT, "relate",
                "--from", from_id,
                "--rel", rel,
                "--to", to_id,
                "--props", json.dumps(args.get("props") or {}),
                "--graph", graph,
            ]

        else:
            return ToolResult(error=f"未知操作: {op}")

        code, stdout, stderr = await _run(cmd, cwd=cwd)
        if code != 0:
            return ToolResult(output=stdout, error=stderr or f"exit {code}")
        return ToolResult(output=stdout.strip() or "操作成功")
