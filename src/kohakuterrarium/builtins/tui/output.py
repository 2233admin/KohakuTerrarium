"""TUI output module - writes to Textual app with visual turn separation."""

from typing import Any

from kohakuterrarium.builtins.tui.session import TUISession
from kohakuterrarium.core.session import get_session
from kohakuterrarium.modules.output.base import BaseOutputModule
from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)


class TUIOutput(BaseOutputModule):
    """
    Output module using Textual full-screen TUI.

    Each assistant turn is visually separated:
    - begin_assistant_turn() adds a header
    - streaming output appears incrementally
    - end_assistant_turn() adds a separator

    Config:
        output:
          type: tui
          session_key: my_agent  # optional
    """

    def __init__(self, session_key: str | None = None, **options: Any):
        super().__init__()
        self._session_key = session_key
        self._tui: TUISession | None = None
        self._stream_buffer: str = ""
        self._turn_started: bool = False

    async def _on_start(self) -> None:
        """Attach to shared TUI session."""
        session = get_session(self._session_key)
        if session.tui is None:
            session.tui = TUISession(
                agent_name=session.key if session.key != "__default__" else "agent",
            )
        self._tui = session.tui
        logger.debug("TUI output started", session_key=self._session_key)

    async def _on_stop(self) -> None:
        """Flush and cleanup."""
        await self.flush()
        logger.debug("TUI output stopped")

    def _ensure_turn_started(self) -> None:
        """Start a new assistant turn block if not already started."""
        if not self._turn_started and self._tui:
            self._tui.begin_assistant_turn()
            self._turn_started = True

    async def on_processing_start(self) -> None:
        """Show processing indicator when agent starts thinking."""
        if self._tui:
            self._tui.set_subtitle("KohakUwUing...")

    async def on_processing_end(self) -> None:
        """Clear processing indicator."""
        if self._tui:
            self._tui.set_subtitle("")

    async def write(self, content: str) -> None:
        """Write complete content to the output pane."""
        if self._tui and content:
            self._ensure_turn_started()
            self._tui.write_output(content)

    async def write_stream(self, chunk: str) -> None:
        """
        Buffer streaming chunks and flush on newlines.

        Each complete line is written to the output pane.
        """
        if not self._tui or not chunk:
            return

        self._ensure_turn_started()
        self._stream_buffer += chunk

        while "\n" in self._stream_buffer:
            line, self._stream_buffer = self._stream_buffer.split("\n", 1)
            if line:
                self._tui.write_output(line)

    async def flush(self) -> None:
        """Flush remaining buffered stream content."""
        if self._tui and self._stream_buffer:
            self._tui.write_output(self._stream_buffer)
            self._stream_buffer = ""

    def reset(self) -> None:
        """Reset between turns - end the current assistant block."""
        if self._turn_started and self._tui:
            self._tui.end_assistant_turn()
            self._turn_started = False
        self._stream_buffer = ""

    def on_activity(self, activity_type: str, detail: str) -> None:
        """Route tool/subagent activity to the Status tab."""
        if not self._tui:
            return
        self._tui.update_status(f"[{activity_type}] {detail}")
