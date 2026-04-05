"""Compare runner: execute same task on multiple targets in parallel."""

import argparse
import asyncio
import time
from dataclasses import dataclass
from pathlib import Path

from kohakuterrarium.studio.config import ProfileConfig
from kohakuterrarium.studio.targets import list_targets, resolve_target
from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CompareResult:
    """Result of running a task on a single target."""

    target: str
    output: str
    duration_ms: int
    exit_code: int


class CompareRunner:
    """Runs the same task on multiple targets concurrently."""

    def __init__(self, targets: list[str]) -> None:
        self.targets = targets

    async def _run_one(
        self, target_name: str, task: str, timeout: int
    ) -> CompareResult:
        """Run task on a single target."""
        try:
            target = resolve_target(target_name)
        except ValueError:
            return CompareResult(
                target=target_name,
                output=f"Unknown target: {target_name}",
                duration_ms=0,
                exit_code=1,
            )

        cmd = target.build_command(ProfileConfig())
        start = time.monotonic()

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(
                proc.communicate(input=task.encode("utf-8")),
                timeout=timeout,
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return CompareResult(
                target=target_name,
                output=stdout.decode("utf-8", errors="replace"),
                duration_ms=elapsed_ms,
                exit_code=proc.returncode or 0,
            )
        except asyncio.TimeoutError:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return CompareResult(
                target=target_name,
                output="TIMEOUT",
                duration_ms=elapsed_ms,
                exit_code=-1,
            )
        except OSError as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return CompareResult(
                target=target_name,
                output=str(e),
                duration_ms=elapsed_ms,
                exit_code=1,
            )

    async def run(self, task: str, timeout: int = 120) -> list[CompareResult]:
        """Run task on all targets in parallel. Returns results sorted by duration."""
        # If task looks like a file path, read its content
        task_path = Path(task)
        if task_path.exists() and task_path.is_file():
            task = task_path.read_text(encoding="utf-8")

        tasks = [self._run_one(t, task, timeout) for t in self.targets]
        results = await asyncio.gather(*tasks)
        return sorted(results, key=lambda r: r.duration_ms)

    def format_results(self, results: list[CompareResult]) -> str:
        """Format results as an aligned table."""
        lines: list[str] = []
        lines.append(
            f"{'Target':<20} {'Duration':<12} {'Exit':<6} {'Output (first 200 chars)'}"
        )
        lines.append("-" * 70)
        for r in results:
            preview = r.output.replace("\n", " ")[:200]
            dur = f"{r.duration_ms}ms"
            lines.append(f"{r.target:<20} {dur:<12} {r.exit_code:<6} {preview}")
        return "\n".join(lines)


def handle_compare_command(args: argparse.Namespace) -> int:
    """CLI handler for 'kt studio compare'."""
    targets_arg = getattr(args, "targets", None)
    if targets_arg:
        target_names = [t.strip() for t in targets_arg.split(",")]
    else:
        target_names = [t.name for t in list_targets() if t.detect() is not None]

    if not target_names:
        print("No targets available. Install at least one AI coding CLI.")
        return 1

    timeout = getattr(args, "timeout", 120)
    runner = CompareRunner(target_names)
    results = asyncio.run(runner.run(args.task, timeout=timeout))
    print(runner.format_results(results))
    return 0
