"""
Inline input module. Claude Code / Codex CLI-style terminal input.

Uses prompt_toolkit for input with history, completion, and proper
terminal handling. Works over SSH/tmux/any terminal.
Suppresses framework logging to keep the terminal clean.
"""

import asyncio
from pathlib import Path
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

from kohakuterrarium.core.events import TriggerEvent, create_user_input_event
from kohakuterrarium.modules.input.base import BaseInputModule
from kohakuterrarium.utils.logging import get_logger, suppress_logging, restore_logging

logger = get_logger(__name__)

_HISTORY_DIR = Path.home() / ".kohakuterrarium"
_HISTORY_FILE = _HISTORY_DIR / "input_history"


class InlineInput(BaseInputModule):
    """Inline input using prompt_toolkit. SSH-compatible, with history.

    Config:
        input:
          type: inline
          prompt: "> "
    """

    def __init__(
        self,
        prompt: str = "> ",
        *,
        exit_commands: list[str] | None = None,
        **options: Any,
    ):
        super().__init__()
        self.prompt = prompt
        self.exit_commands = exit_commands or ["/exit", "/quit", "exit", "quit"]
        self._exit_requested = False
        self._session: PromptSession | None = None

    @property
    def exit_requested(self) -> bool:
        return self._exit_requested

    async def _on_start(self) -> None:
        # Ensure history directory exists
        _HISTORY_DIR.mkdir(parents=True, exist_ok=True)

        # Create prompt session with file history
        self._session = PromptSession(
            history=FileHistory(str(_HISTORY_FILE)),
        )

        # Suppress framework logs so they don't interfere with inline display
        suppress_logging()

        logger.debug("Inline input started")

    async def _on_stop(self) -> None:
        restore_logging()
        logger.debug("Inline input stopped")

    async def get_input(self) -> TriggerEvent | None:
        if not self._running or self._exit_requested or not self._session:
            return None

        try:
            text = await self._session.prompt_async(self.prompt)
            text = text.strip()

            if not text:
                return await self.get_input()

            if text.lower() in self.exit_commands:
                self._exit_requested = True
                return None

            return create_user_input_event(text, source="inline")

        except (KeyboardInterrupt, EOFError):
            self._exit_requested = True
            return None
        except Exception as e:
            logger.error("Error reading inline input", error=str(e))
            return None
