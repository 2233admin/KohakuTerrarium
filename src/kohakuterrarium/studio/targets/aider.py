"""AiderTarget: Aider CLI backend for kt studio."""

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

AIDER_CONFIG_PATH = Path.home() / ".aider.conf.yml"


@register_target
class AiderTarget(Target):
    """Target implementation for the Aider CLI."""

    name = "aider"
    display_name = "Aider"

    def detect(self) -> Path | None:
        """Return aider CLI path if installed, else None."""
        result = shutil.which("aider")
        if result:
            return Path(result)
        return None

    def build_command(
        self, profile: ProfileConfig, settings_path: Path | None = None
    ) -> list[str]:
        """Build aider CLI command with model flag."""
        cmd = ["aider", "--model", profile.model]
        return cmd

    def list_models(self) -> list[str]:
        """Return commonly used Aider model identifiers."""
        return [
            "gpt-4o",
            "claude-sonnet-4-20250514",
            "deepseek/deepseek-chat",
            "o4-mini",
        ]

    def status(self) -> dict:
        """Return Aider CLI installation status."""
        cli = self.detect()
        return {
            "installed": cli is not None,
            "cli_path": str(cli) if cli else None,
        }

    def settings_path(self) -> Path | None:
        """Return path to Aider config."""
        return AIDER_CONFIG_PATH

    def session_dir(self) -> Path | None:
        """Aider does not persist scannable sessions."""
        return None
