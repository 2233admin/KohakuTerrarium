"""Cost tracker: pricing estimates and usage log scanning for kt studio."""

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)

# Pricing per 1M tokens: (input_rate, output_rate)
PRICING: dict[str, tuple[float, float]] = {
    "claude-sonnet-4": (3.0, 15.0),
    "claude-opus-4": (15.0, 75.0),
    "claude-haiku-4": (0.80, 4.0),
    "gpt-4.1": (2.0, 8.0),
    "o3-mini": (1.10, 4.40),
    "gemini-2.5-pro": (1.25, 10.0),
    "gemini-2.5-flash": (0.15, 0.60),
    "codex-mini": (1.50, 6.0),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost for a given model and token counts.

    Returns 0.0 for unknown models (graceful fallback).
    """
    rates = PRICING.get(model)
    if rates is None:
        return 0.0
    input_rate, output_rate = rates
    return (input_tokens / 1_000_000) * input_rate + (output_tokens / 1_000_000) * output_rate


def scan_usage_logs() -> list[dict]:
    """Scan ~/.claude/projects/ for session JSONL files with token usage.

    Best-effort: returns empty list if directories are missing.
    Each dict: {target, model, input_tokens, output_tokens, cost, timestamp}.
    """
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return []

    entries: list[dict] = []
    for jsonl_file in projects_dir.rglob("*.jsonl"):
        try:
            with open(jsonl_file, encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if "usage" not in data:
                        continue
                    usage = data["usage"]
                    model = data.get("model", "unknown")
                    inp = usage.get("input_tokens", 0)
                    out = usage.get("output_tokens", 0)
                    entries.append({
                        "target": data.get("target", "claude-code"),
                        "model": model,
                        "input_tokens": inp,
                        "output_tokens": out,
                        "cost": estimate_cost(model, inp, out),
                        "timestamp": data.get("timestamp", ""),
                    })
        except OSError:
            continue

    return entries


def cost_summary(period: str = "today") -> dict:
    """Aggregate usage logs filtered by period.

    Returns {total, by_target, by_model, entries}.
    """
    all_entries = scan_usage_logs()

    now = datetime.now(timezone.utc)
    if period == "today":
        cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        cutoff = now - timedelta(days=7)
    elif period == "month":
        cutoff = now - timedelta(days=30)
    else:
        cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)

    filtered: list[dict] = []
    for e in all_entries:
        ts = e.get("timestamp", "")
        if ts:
            try:
                entry_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if entry_time < cutoff:
                    continue
            except ValueError:
                pass
        filtered.append(e)

    total = sum(e["cost"] for e in filtered)
    by_target: dict[str, float] = {}
    by_model: dict[str, float] = {}
    for e in filtered:
        by_target[e["target"]] = by_target.get(e["target"], 0.0) + e["cost"]
        by_model[e["model"]] = by_model.get(e["model"], 0.0) + e["cost"]

    return {
        "total": total,
        "by_target": by_target,
        "by_model": by_model,
        "entries": len(filtered),
    }


def handle_cost_command(args: argparse.Namespace) -> int:
    """Print formatted cost summary table."""
    period = getattr(args, "period", "today")
    summary = cost_summary(period)

    print(f"Cost Summary ({period})")
    print("=" * 40)
    print(f"Total: ${summary['total']:.4f}")
    print(f"Entries: {summary['entries']}")

    if summary["by_model"]:
        print(f"\n{'Model':<25} {'Cost':>10}")
        print("-" * 37)
        for model, cost in sorted(summary["by_model"].items(), key=lambda x: -x[1]):
            print(f"{model:<25} ${cost:>9.4f}")

    if summary["by_target"]:
        print(f"\n{'Target':<25} {'Cost':>10}")
        print("-" * 37)
        for target, cost in sorted(summary["by_target"].items(), key=lambda x: -x[1]):
            print(f"{target:<25} ${cost:>9.4f}")

    return 0
