"""
Inline output module. Claude Code / Codex CLI-style terminal output.

Streams text inline (no alternate screen buffer), shows tool activity
as collapsed one-liners, works over SSH/tmux/any terminal.
Uses Rich for styling.
"""

import sys

from rich.console import Console
from rich.markup import escape
from rich.text import Text

from kohakuterrarium.modules.output.base import BaseOutputModule
from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)

# Dim separator between turns
_SEPARATOR = Text("─" * 60, style="dim")


class InlineOutput(BaseOutputModule):
    """Inline terminal output using Rich. No alternate screen buffer.

    Config:
        output:
          type: inline
    """

    def __init__(self, **options):
        super().__init__()
        self._console = Console(highlight=False)
        self._has_output = False
        self._in_turn = False

    async def _on_start(self) -> None:
        logger.debug("Inline output started")

    async def _on_stop(self) -> None:
        if self._in_turn:
            self._end_turn()
        logger.debug("Inline output stopped")

    async def on_processing_start(self) -> None:
        pass

    async def on_processing_end(self) -> None:
        if self._in_turn:
            self._end_turn()

    async def write(self, content: str) -> None:
        if not content:
            return
        self._ensure_turn()
        sys.stdout.write(content)
        sys.stdout.flush()
        self._has_output = True

    async def write_stream(self, chunk: str) -> None:
        if not chunk:
            return
        self._ensure_turn()
        sys.stdout.write(chunk)
        sys.stdout.flush()
        self._has_output = True

    async def flush(self) -> None:
        if self._has_output:
            sys.stdout.flush()

    def reset(self) -> None:
        self._has_output = False

    def _ensure_turn(self) -> None:
        if not self._in_turn:
            self._in_turn = True

    def _end_turn(self) -> None:
        if self._has_output:
            sys.stdout.write("\n")
            sys.stdout.flush()
        self._in_turn = False
        self._has_output = False

    def on_activity(self, activity_type: str, detail: str) -> None:
        name, rest = _parse_detail(detail)
        line = _format_activity(activity_type, name, rest)
        if line:
            # Flush any pending text before activity line
            sys.stdout.flush()
            self._console.print(line)

    async def on_resume(self, events: list[dict]) -> None:
        """Show session history inline with Rich styling."""
        if not events:
            return

        turns = _group_into_turns(events)
        if not turns:
            return

        self._console.print()
        self._console.print(
            Text(f"  Resumed session ({len(turns)} turns)  ", style="bold dim")
        )
        self._console.print()

        for turn in turns:
            # User input
            if turn["input_type"] == "user_input":
                self._console.print(
                    Text("You: ", style="bold cyan") + Text(turn["input"][:200])
                )
            else:
                self._console.print(
                    Text("Trigger: ", style="bold yellow") + Text(turn["input"][:200])
                )

            # Tool activity (collapsed one-liners)
            for atype, aname in turn["activities"]:
                line = _format_activity(atype, aname, "")
                if line:
                    self._console.print(line)

            # Assistant text
            text = "".join(turn["text_parts"]).strip()
            if text:
                preview = text[:300]
                if len(text) > 300:
                    preview += "..."
                self._console.print(Text(preview, style=""))
            self._console.print()

        self._console.print(
            Text("  End of history  ", style="bold dim")
        )
        self._console.print()


def _parse_detail(detail: str) -> tuple[str, str]:
    """Extract [name] prefix from detail string."""
    if detail.startswith("["):
        try:
            end = detail.index("]", 1)
            return detail[1:end], detail[end + 2:]
        except (ValueError, IndexError):
            pass
    return "unknown", detail


def _format_activity(activity_type: str, name: str, rest: str) -> Text | None:
    """Format a tool/subagent activity as a one-line Rich Text."""
    match activity_type:
        case "tool_start":
            t = Text("  \u25cb ", style="dim")
            t.append(name, style="bold cyan")
            if rest:
                t.append(f"  {rest[:80]}", style="dim")
            return t
        case "tool_done":
            t = Text("  \u25cf ", style="green")
            t.append(name, style="bold cyan")
            if rest:
                t.append(f"  {rest[:80]}", style="dim green")
            return t
        case "tool_error":
            t = Text("  \u25cf ", style="red")
            t.append(name, style="bold red")
            if rest:
                t.append(f"  {rest[:80]}", style="red")
            return t
        case "subagent_start":
            t = Text("  \u25cb ", style="dim")
            t.append(f"[sub] {name}", style="bold magenta")
            if rest:
                t.append(f"  {rest[:80]}", style="dim")
            return t
        case "subagent_done":
            t = Text("  \u25cf ", style="green")
            t.append(f"[sub] {name}", style="bold magenta")
            if rest:
                t.append(f"  {rest[:60]}", style="dim green")
            return t
        case "subagent_error":
            t = Text("  \u25cf ", style="red")
            t.append(f"[sub] {name}", style="bold red")
            if rest:
                t.append(f"  {rest[:80]}", style="red")
            return t
        case _:
            return None


def _group_into_turns(events: list[dict]) -> list[dict]:
    """Group session events into turns for resume display."""
    turns: list[dict] = []
    current: dict | None = None

    for evt in events:
        etype = evt.get("type", "")
        if etype == "user_input":
            if current:
                turns.append(current)
            current = {
                "input_type": "user_input",
                "input": evt.get("content", ""),
                "text_parts": [],
                "activities": [],
            }
        elif etype == "trigger_fired":
            if current:
                turns.append(current)
            ch = evt.get("channel", "")
            sender = evt.get("sender", "")
            current = {
                "input_type": "trigger",
                "input": f"[{ch}] from {sender}: {evt.get('content', '')}",
                "text_parts": [],
                "activities": [],
            }
        elif current is not None:
            if etype == "text":
                current["text_parts"].append(evt.get("content", ""))
            elif etype == "tool_call":
                current["activities"].append(("tool_start", evt.get("name", "tool")))
            elif etype == "tool_result":
                atype = "tool_error" if evt.get("error") else "tool_done"
                current["activities"].append((atype, evt.get("name", "tool")))
            elif etype == "subagent_call":
                current["activities"].append(
                    ("subagent_start", evt.get("name", "subagent"))
                )
            elif etype == "subagent_result":
                current["activities"].append(
                    ("subagent_done", evt.get("name", "subagent"))
                )

    if current:
        turns.append(current)
    return turns
