"""
KG write tool — mutating operations on ontology graph.

Wraps ~/.claude/skills/ontology/scripts/ontology.py.
Operations: create, update, delete, relate, upsert.

Improvements over v1:
- `upsert` operation: create-or-update by type+name (most common pattern)
- `id` accepts semantic slugs (e.g. "task-fix-login") — non-UUID values used directly
- `create` warns on stderr when props contains `name` (suggesting upsert instead)
- Shared `run_subprocess` from _kg_utils (no duplicate _run)
- `timeout` configurable per-call
"""

import json
import sys
from pathlib import Path

from kohakuterrarium.builtins.tools._kg_utils import is_uuid_like, run_subprocess
from kohakuterrarium.builtins.tools.registry import register_builtin
from kohakuterrarium.modules.tool.base import BaseTool, ToolResult

ONTOLOGY_SCRIPT = str(Path.home() / ".claude/skills/ontology/scripts/ontology.py")
DEFAULT_GRAPH = "memory/ontology/graph.jsonl"


@register_builtin("kg_write")
class KgWriteTool(BaseTool):
    """向 ontology KG 写入/更新实体和关系。操作: create/update/delete/relate/upsert。"""

    tool_name = "kg_write"
    needs_context = True

    @property
    def description(self) -> str:
        return (
            "操作 ontology 知识图谱（写入）。"
            "操作: upsert(按name去重，最常用), create(建实体), update(改属性), delete(删实体), relate(建关系)。"
            "upsert = 同 type+name 已存在则 update，否则 create。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["upsert", "create", "update", "delete", "relate"],
                    "description": "操作类型。upsert 是最常用的，防止重复创建。",
                },
                "entity_type": {
                    "type": "string",
                    "description": "实体类型，如 Task/Project/Event（upsert/create 时必填）",
                },
                "props": {
                    "type": "object",
                    "description": "实体属性 dict（upsert/create/update 时用）",
                },
                "id": {
                    "type": "string",
                    "description": (
                        "实体 ID（update/delete 时必填，create 时可选自定义）。"
                        "支持语义 slug，如 'task-fix-login'——非 UUID 格式直接存为 id。"
                    ),
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
                    "description": "防重复创建：用 upsert 而非 create，按名称去重",
                    "input": {"operation": "upsert", "entity_type": "Task", "props": {"name": "修复登录bug", "status": "open", "priority": "high"}},
                    "output": "操作成功 (created task-001)",
                },
                {
                    "description": "建立任务依赖关系",
                    "input": {"operation": "relate", "from_id": "task-002", "rel": "depends_on", "to_id": "task-001"},
                    "output": "操作成功",
                },
                {
                    "description": "用语义 slug ID 创建（而非 UUID）",
                    "input": {"operation": "create", "entity_type": "Project", "id": "project-auth", "props": {"name": "认证模块", "status": "active"}},
                    "output": "操作成功 (id=project-auth)",
                },
            ],
        }

    async def _execute(self, args: dict, *, context=None) -> ToolResult:
        op = args.get("operation", "")
        graph = args.get("graph", DEFAULT_GRAPH)
        timeout = float(args.get("timeout", 15.0))
        cwd = str(context.working_dir) if context else None

        if op == "upsert":
            entity_type = args.get("entity_type", "")
            props = args.get("props") or {}
            if not entity_type:
                return ToolResult(error="upsert 需要 entity_type")
            name = props.get("name") or args.get("id", "")
            if not name:
                return ToolResult(error="upsert 需要 props.name 或 id 作为去重键")

            # Try to find existing entity by type + name
            find_cmd = [
                sys.executable, ONTOLOGY_SCRIPT, "query",
                "--type", entity_type,
                "--where", json.dumps({"name": name}),
                "--graph", graph,
            ]
            code, stdout, _ = await run_subprocess(find_cmd, cwd=cwd, timeout=timeout)
            existing_id = _extract_first_id(stdout) if code == 0 else None

            if existing_id:
                # Update existing
                update_cmd = [
                    sys.executable, ONTOLOGY_SCRIPT, "update",
                    "--id", existing_id,
                    "--props", json.dumps(props),
                    "--graph", graph,
                ]
                code, stdout, stderr = await run_subprocess(update_cmd, cwd=cwd, timeout=timeout)
                action = f"updated (id={existing_id})"
            else:
                # Create new; use provided id as slug if given and not UUID-like
                create_cmd = [
                    sys.executable, ONTOLOGY_SCRIPT, "create",
                    "--type", entity_type,
                    "--props", json.dumps(props),
                    "--graph", graph,
                ]
                custom_id = args.get("id", "")
                if custom_id:
                    create_cmd += ["--id", custom_id]
                code, stdout, stderr = await run_subprocess(create_cmd, cwd=cwd, timeout=timeout)
                action = "created"

            if code != 0:
                return ToolResult(output=stdout, error=stderr or f"exit {code}")
            return ToolResult(output=f"upsert {action}: {stdout.strip()}")

        elif op == "create":
            entity_type = args.get("entity_type", "")
            if not entity_type:
                return ToolResult(error="create 需要 entity_type")
            props = args.get("props") or {}
            cmd = [
                sys.executable, ONTOLOGY_SCRIPT, "create",
                "--type", entity_type,
                "--props", json.dumps(props),
                "--graph", graph,
            ]
            custom_id = args.get("id", "")
            if custom_id:
                cmd += ["--id", custom_id]

            # Stderr hint when name is in props but upsert wasn't used
            hint = ""
            if props.get("name"):
                hint = "[hint] props 含 name 字段，建议用 upsert 防重复\n"

            code, stdout, stderr = await run_subprocess(cmd, cwd=cwd, timeout=timeout)
            if code != 0:
                return ToolResult(output=stdout, error=hint + (stderr or f"exit {code}"))
            return ToolResult(output=hint + (stdout.strip() or "创建成功"))

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
            code, stdout, stderr = await run_subprocess(cmd, cwd=cwd, timeout=timeout)
            if code != 0:
                return ToolResult(output=stdout, error=stderr or f"exit {code}")
            return ToolResult(output=stdout.strip() or "更新成功")

        elif op == "delete":
            entity_id = args.get("id", "")
            if not entity_id:
                return ToolResult(error="delete 需要 id")
            cmd = [sys.executable, ONTOLOGY_SCRIPT, "delete", "--id", entity_id, "--graph", graph]
            code, stdout, stderr = await run_subprocess(cmd, cwd=cwd, timeout=timeout)
            if code != 0:
                return ToolResult(output=stdout, error=stderr or f"exit {code}")
            return ToolResult(output=stdout.strip() or "删除成功")

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
            code, stdout, stderr = await run_subprocess(cmd, cwd=cwd, timeout=timeout)
            if code != 0:
                return ToolResult(output=stdout, error=stderr or f"exit {code}")
            return ToolResult(output=stdout.strip() or "关系建立成功")

        else:
            return ToolResult(error=f"未知操作: {op}")


def _extract_first_id(output: str) -> str | None:
    """Parse the first entity id from ontology.py JSON output (array or single object)."""
    import json as _json

    output = output.strip()
    if not output:
        return None

    # Try line-by-line JSONL
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = _json.loads(line)
            if isinstance(obj, list) and obj:
                return obj[0].get("id")
            if isinstance(obj, dict):
                return obj.get("id")
        except _json.JSONDecodeError:
            pass

    # Try whole blob
    try:
        obj = _json.loads(output)
        if isinstance(obj, list) and obj:
            return obj[0].get("id")
        if isinstance(obj, dict):
            return obj.get("id")
    except _json.JSONDecodeError:
        pass

    return None
