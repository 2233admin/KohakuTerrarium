"""Headless terrarium runner for Claude Code integration.

Usage:
    py -3.13 scripts/headless_run.py deep_research "研究问题" [--llm claude-sonnet-4.6] [--timeout 300]
    py -3.13 scripts/headless_run.py auto_research "研究目标" [--llm claude-sonnet-4.6] [--timeout 600]
"""

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

# Add src to path and load .env
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from kohakuterrarium.terrarium.config import load_terrarium_config
from kohakuterrarium.terrarium.runtime import TerrariumRuntime


TERRARIUM_BASE = Path(__file__).parent.parent / "kohaku-creatures" / "terrariums"

# Map terrarium name to seed channel
SEED_CHANNELS = {
    "deep_research": "questions",
    "auto_research": "goals",
    "swe_team": "tasks",
}

# Map terrarium name to result channel
RESULT_CHANNELS = {
    "deep_research": "final",
    "auto_research": "feedback",
    "swe_team": "feedback",
}


async def run_headless(terrarium_name: str, seed: str, llm: str | None, timeout: int):
    terrarium_path = TERRARIUM_BASE / terrarium_name
    if not terrarium_path.exists():
        print(f"Error: terrarium not found: {terrarium_path}", file=sys.stderr)
        sys.exit(1)

    config = load_terrarium_config(str(terrarium_path))
    print(f"[kt] Terrarium: {config.name}", file=sys.stderr)
    print(f"[kt] Creatures: {[c.name for c in config.creatures]}", file=sys.stderr)
    print(f"[kt] LLM: {llm or 'default'}", file=sys.stderr)
    print(f"[kt] Timeout: {timeout}s", file=sys.stderr)
    print(f"[kt] Seed: {seed[:100]}", file=sys.stderr)

    runtime = TerrariumRuntime(config, llm_override=llm)
    await runtime.start()

    # Wait for runtime
    for _ in range(20):
        await asyncio.sleep(0.25)
        if runtime.is_running:
            break

    if not runtime.is_running:
        print("Error: runtime failed to start", file=sys.stderr)
        sys.exit(1)

    # Collect messages from all channels
    collected = []

    for ch in runtime.environment.shared_channels._channels.values():
        ch_name = ch.name

        def _make_cb(channel_name: str):
            def _cb(cn: str, message) -> None:
                sender = message.sender if hasattr(message, "sender") else ""
                content = message.content if hasattr(message, "content") else str(message)
                collected.append({
                    "channel": channel_name,
                    "sender": sender,
                    "content": content,
                    "time": time.time(),
                })
                print(f"[{channel_name}] {sender}: {content[:200]}", file=sys.stderr)
            return _cb

        ch.on_send(_make_cb(ch_name))

    # Inject seed
    seed_channel = SEED_CHANNELS.get(terrarium_name, "seed")
    await runtime.api.send_to_channel(seed_channel, seed, sender="human")
    print(f"[kt] Seed sent to '{seed_channel}'", file=sys.stderr)

    # Run creatures with timeout
    creature_tasks = []
    for handle in runtime._creatures.values():
        task = asyncio.create_task(
            runtime._run_creature(handle),
            name=f"creature_{handle.name}",
        )
        creature_tasks.append(task)
        runtime._creature_tasks.append(task)

    try:
        await asyncio.wait_for(
            asyncio.gather(*creature_tasks, return_exceptions=True),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        print(f"[kt] Timeout after {timeout}s, collecting results...", file=sys.stderr)
    except KeyboardInterrupt:
        print("[kt] Interrupted", file=sys.stderr)
    finally:
        await runtime.stop()

    # Output final results to stdout
    result_channel = RESULT_CHANNELS.get(terrarium_name, "final")
    finals = [m for m in collected if m["channel"] == result_channel]

    if finals:
        print("\n--- RESULTS ---\n")
        for m in finals:
            print(f"[{m['sender']}]\n{m['content']}\n")
    else:
        # Fallback: print all collected messages
        print("\n--- ALL MESSAGES ---\n")
        for m in collected:
            print(f"[{m['channel']}] {m['sender']}:\n{m['content'][:500]}\n")

    if not collected:
        print("(no messages collected)", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Headless terrarium runner")
    parser.add_argument("terrarium", help="Terrarium name (deep_research, auto_research, swe_team)")
    parser.add_argument("seed", help="Seed prompt / research question")
    parser.add_argument("--llm", default=None, help="LLM profile override")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout in seconds (default: 300)")
    args = parser.parse_args()

    asyncio.run(run_headless(args.terrarium, args.seed, args.llm, args.timeout))


if __name__ == "__main__":
    main()
