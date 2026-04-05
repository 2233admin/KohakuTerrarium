"""GeminiTarget: Google Gemini CLI backend for kt studio."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from kohakuterrarium.studio.targets import register_target
from kohakuterrarium.studio.targets.base import Target
from kohakuterrarium.utils.logging import get_logger

if TYPE_CHECKING:
    from kohakuterrarium.studio.config import ProfileConfig

logger = get_logger(__name__)

GEMINI_SETTINGS_PATH = Path.home() / ".gemini" / "settings.json"


@register_target
class GeminiTarget(Target):
    """Target implementation for the Google Gemini CLI."""

    name = "gemini"
    display_name = "Gemini CLI"

    def detect(self) -> Path | None:
        """Return gemini CLI path if installed, else None."""
        result = shutil.which("gemini")
        if result:
            return Path(result)
        return None

    def build_command(
        self, profile: ProfileConfig, settings_path: Path | None = None
    ) -> list[str]:
        """Build gemini CLI command with model flag."""
        cmd = ["gemini", "--model", profile.model]
        return cmd

    def list_models(self) -> list[str]:
        """Return known Gemini CLI model identifiers."""
        return ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"]

    def status(self) -> dict:
        """Return Gemini CLI installation status."""
        cli = self.detect()
        return {
            "installed": cli is not None,
            "cli_path": str(cli) if cli else None,
        }

    def settings_path(self) -> Path | None:
        """Return path to Gemini settings."""
        return GEMINI_SETTINGS_PATH

    def session_dir(self) -> Path | None:
        """Gemini CLI does not persist scannable sessions yet."""
        return None
