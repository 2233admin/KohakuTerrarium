"""ProfileLauncher: settings merge, command builder, and async launch."""

import asyncio
import atexit
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from kohakuterrarium.studio.config import (
    ProfileConfig,
    StudioConfig,
    load_studio_config,
)
from kohakuterrarium.studio.targets import resolve_target
from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)

CLAUDE_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"


class ProfileLauncher:
    """Merges profile overrides with base Claude settings and launches."""

    def __init__(self, profile: ProfileConfig, studio_config: StudioConfig) -> None:
        self.profile = profile
        self.studio_config = studio_config
        self.target = resolve_target(profile.target)
        self._temp_files: list[Path] = []

    def build_settings_json(self) -> dict[str, Any]:
        """Build merged settings dict from base settings + profile overrides."""
        base: dict[str, Any] = {}
        if CLAUDE_SETTINGS_PATH.exists():
            try:
                with open(CLAUDE_SETTINGS_PATH, encoding="utf-8") as f:
                    base = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to read base settings: %s", e)
        return self.target.merge_settings(base, self.profile)

    def build_command(self, temp_settings_path: Path) -> list[str]:
        """Build CLI command by delegating to the resolved target."""
        return self.target.build_command(self.profile, temp_settings_path)

    async def launch(self) -> int:
        """Write merged settings to temp file and launch claude CLI."""
        merged = self.build_settings_json()

        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            prefix="kt_studio_",
            delete=False,
            encoding="utf-8",
        )
        json.dump(merged, tmp, indent=2)
        tmp.close()
        temp_path = Path(tmp.name)
        self._temp_files.append(temp_path)
        atexit.register(self.cleanup)

        cmd = self.build_command(temp_path)
        logger.info("Launching: %s", " ".join(cmd))

        proc = await asyncio.create_subprocess_exec(*cmd)
        return await proc.wait()

    def cleanup(self) -> None:
        """Remove temporary settings files."""
        for temp_file in self._temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    logger.debug("Cleaned up temp file: %s", temp_file)
            except OSError:
                pass
        self._temp_files.clear()


def find_claude_cli() -> Path | None:
    """Check if claude CLI is available on PATH."""
    result = shutil.which("claude")
    if result:
        return Path(result)
    return None


def doctor() -> list[str]:
    """Run health checks for studio. Returns list of issues (empty = healthy)."""
    issues: list[str] = []

    # Check claude CLI
    if find_claude_cli() is None:
        issues.append("claude CLI not found on PATH")

    # Check base settings
    if not CLAUDE_SETTINGS_PATH.exists():
        issues.append(f"Base settings not found: {CLAUDE_SETTINGS_PATH}")

    # Check studio config
    from kohakuterrarium.studio.config import STUDIO_CONFIG_PATH

    if not STUDIO_CONFIG_PATH.exists():
        issues.append(f"Studio config not found: {STUDIO_CONFIG_PATH}")
    else:
        try:
            config = load_studio_config()
            if not config.profiles:
                issues.append("No profiles defined in studio.yaml")
        except Exception as e:
            issues.append(f"Invalid studio.yaml: {e}")

    return issues
