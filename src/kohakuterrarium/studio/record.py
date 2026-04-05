"""Session recorder: capture and replay CLI sessions as JSONL."""

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RecordingEntry:
    """A single entry in a recorded session."""

    timestamp: str
    type: str  # "meta", "input", "output"
    content: str

    def to_dict(self) -> dict:
        """Serialize to plain dict."""
        return {
            "timestamp": self.timestamp,
            "type": self.type,
            "content": self.content,
        }


class SessionRecorder:
    """Records a CLI subprocess session to JSONL."""

    def __init__(self, output_path: Path, target_name: str) -> None:
        self.output_path = output_path
        self.target_name = target_name

    async def record(self, command: list[str]) -> int:
        """Spawn subprocess, capture stdout line-by-line to JSONL.

        Writes meta entry at start and end. Returns exit code.
        """
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        start = time.monotonic()
        start_ts = datetime.now(timezone.utc).isoformat()

        with open(self.output_path, "w", encoding="utf-8") as f:
            # Meta entry: session start
            meta = RecordingEntry(
                timestamp=start_ts,
                type="meta",
                content=json.dumps({
                    "target": self.target_name,
                    "command": command,
                    "event": "start",
                }),
            )
            f.write(json.dumps(meta.to_dict()) + "\n")

            proc = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            async for line_bytes in proc.stdout:
                line = line_bytes.decode("utf-8", errors="replace")
                ts = datetime.now(timezone.utc).isoformat()
                entry = RecordingEntry(timestamp=ts, type="output", content=line.rstrip("\n"))
                f.write(json.dumps(entry.to_dict()) + "\n")
                sys.stdout.write(line)
                sys.stdout.flush()

            await proc.wait()
            elapsed_ms = int((time.monotonic() - start) * 1000)

            # Meta entry: session end
            end_meta = RecordingEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                type="meta",
                content=json.dumps({
                    "event": "end",
                    "duration_ms": elapsed_ms,
                    "exit_code": proc.returncode,
                }),
            )
            f.write(json.dumps(end_meta.to_dict()) + "\n")

        return proc.returncode or 0


def replay(recording_path: Path, speed: float = 1.0) -> None:
    """Replay a recorded JSONL session with timing delays."""
    if not recording_path.exists():
        print(f"Recording not found: {recording_path}")
        return

    entries: list[dict] = []
    with open(recording_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    prev_ts: str | None = None
    for entry in entries:
        if entry.get("type") != "output":
            continue
        ts = entry.get("timestamp", "")
        if prev_ts and ts and speed > 0:
            try:
                t_prev = datetime.fromisoformat(prev_ts)
                t_curr = datetime.fromisoformat(ts)
                delay = (t_curr - t_prev).total_seconds() / speed
                if delay > 0:
                    time.sleep(min(delay, 2.0))  # cap at 2s
            except ValueError:
                pass
        print(entry.get("content", ""))
        prev_ts = ts


def handle_record_command(args: argparse.Namespace) -> int:
    """CLI handler for 'kt studio record'."""
    target_name = getattr(args, "target", None) or "claude-code"
    output = getattr(args, "output", None)
    if output:
        output_path = Path(output)
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_path = Path.home() / ".kohakuterrarium" / "recordings" / f"{ts}.jsonl"

    # Resolve target to get CLI command
    from kohakuterrarium.studio.targets import resolve_target
    from kohakuterrarium.studio.config import ProfileConfig

    try:
        target = resolve_target(target_name)
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    cmd = target.build_command(ProfileConfig())
    recorder = SessionRecorder(output_path, target_name)
    print(f"Recording to: {output_path}")
    return asyncio.run(recorder.record(cmd))


def handle_replay_command(args: argparse.Namespace) -> int:
    """CLI handler for 'kt studio replay'."""
    recording_path = Path(args.recording)
    speed = getattr(args, "speed", 1.0)
    replay(recording_path, speed=speed)
    return 0
