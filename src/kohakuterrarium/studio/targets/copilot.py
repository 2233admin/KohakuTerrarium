"""CopilotTarget: GitHub Copilot CLI backend for kt studio."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from kohakuterrarium.studio import copilot as copilot_module
from kohakuterrarium.studio.targets import register_target
from kohakuterrarium.studio.targets.base import Target

if TYPE_CHECKING:
    from kohakuterrarium.studio.config import ProfileConfig


@register_target
class CopilotTarget(Target):
    """Target implementation for the GitHub Copilot CLI."""

    name = "copilot"
    display_name = "GitHub Copilot"

    def detect(self) -> Path | None:
        """Return Copilot CLI path if installed, else None."""
        return copilot_module.find_copilot_cli()

    def build_command(
        self, profile: ProfileConfig, settings_path: Path | None = None
    ) -> list[str]:
        """Build Copilot CLI command."""
        cmd = ["github-copilot-cli"]
        if profile.model:
            cmd.extend(["--model", profile.model])
        return cmd

    def list_models(self) -> list[str]:
        """Return available Copilot models."""
        return copilot_module.list_available_models()

    def status(self) -> dict:
        """Return Copilot installation status."""
        return copilot_module.copilot_status()

    def settings_path(self) -> Path | None:
        """Return path to Copilot config."""
        return copilot_module.COPILOT_CONFIG_PATH
