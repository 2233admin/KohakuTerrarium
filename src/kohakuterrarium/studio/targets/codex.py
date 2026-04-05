"""CodexTarget: OpenAI Codex CLI backend for kt studio."""

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

CODEX_CONFIG_PATH = Path.home() / ".codex" / "config.yaml"


@register_target
class CodexTarget(Target):
    """Target implementation for the OpenAI Codex CLI."""

    name = "codex"
    display_name = "Codex CLI"

    def detect(self) -> Path | None:
        """Return codex CLI path if installed, else None."""
        result = shutil.which("codex")
        if result:
            return Path(result)
        return None

    def build_command(
        self, profile: ProfileConfig, settings_path: Path | None = None
    ) -> list[str]:
        """Build codex CLI command with model flag."""
        cmd = ["codex", "--model", profile.model]
        return cmd

    def list_models(self) -> list[str]:
        """Return known Codex CLI model identifiers."""
        return ["o3-mini", "o4-mini", "codex-mini-latest", "gpt-4.1"]

    def status(self) -> dict:
        """Return Codex CLI installation status."""
        cli = self.detect()
        return {
            "installed": cli is not None,
            "cli_path": str(cli) if cli else None,
        }

    def settings_path(self) -> Path | None:
        """Return path to Codex config."""
        return CODEX_CONFIG_PATH

    def session_dir(self) -> Path | None:
        """Codex CLI does not persist scannable sessions."""
        return None
