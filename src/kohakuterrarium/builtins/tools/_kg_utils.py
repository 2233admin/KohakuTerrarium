"""
Shared utilities for kg_query and kg_write tools.
"""

import asyncio
import re
import uuid


async def run_subprocess(
    cmd: list[str],
    cwd: str | None = None,
    timeout: float = 15.0,
) -> tuple[int, str, str]:
    """Run a subprocess and return (returncode, stdout, stderr)."""
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
        return 1, "", f"timeout after {timeout}s"


_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_UUID_HEX_RE = re.compile(r"^[a-z]{1,4}_[0-9a-f]{8}$")  # ontology.py internal IDs


def is_uuid_like(value: str) -> bool:
    """Return True if value looks like a UUID or ontology-generated ID (type_hex8)."""
    return bool(_UUID_RE.match(value) or _UUID_HEX_RE.match(value))


def to_concise(raw_output: str) -> str:
    """
    Post-process JSON output from ontology.py into id+name+type summary lines.

    Handles both a single JSON object and a JSON array (one per line or full array).
    Falls back to returning raw_output unchanged if parsing fails.
    """
    import json

    lines = raw_output.strip().splitlines()
    results: list[dict] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, list):
                results.extend(obj)
            elif isinstance(obj, dict):
                results.append(obj)
        except json.JSONDecodeError:
            pass

    if not results:
        # Maybe the whole thing is one JSON blob
        try:
            obj = json.loads(raw_output)
            if isinstance(obj, list):
                results = obj
            elif isinstance(obj, dict):
                results = [obj]
        except json.JSONDecodeError:
            return raw_output  # give up, return as-is

    summary_lines = []
    for item in results:
        entity_id = item.get("id", "?")
        name = item.get("name") or item.get("props", {}).get("name", "")
        entity_type = item.get("type", "")
        parts = [f"id={entity_id}"]
        if entity_type:
            parts.append(f"type={entity_type}")
        if name:
            parts.append(f"name={name}")
        summary_lines.append("  ".join(parts))

    return "\n".join(summary_lines) if summary_lines else raw_output
