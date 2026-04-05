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
from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)

CLAUDE_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"


class ProfileLauncher:
    """Merges profile overrides with base Claude settings and launches."""

    def __init__(self, profile: ProfileConfig, studio_config: StudioConfig) -> None:
        self.profile = profile
        self.studio_config = studio_config
        self._temp_files: list[Path] = []

    def build_settings_json(self) -> dict[str, Any]:
        """Build merged settings dict from base ~/.claude/settings.json + profile overrides."""
        base: dict[str, Any] = {}
        if CLAUDE_SETTINGS_PATH.exists():
            try:
                with open(CLAUDE_SETTINGS_PATH, encoding="utf-8") as f:
                    base = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to read base settings: %s", e)

        profile = self.profile

        # env: dict merge, profile wins
        if profile.env:
            base_env = base.get("env", {})
            base["env"] = base_env | profile.env

        # hooks: extend lists per event key
        if profile.hooks:
            base_hooks: dict[str, list] = base.get("hooks", {})
            for event_name, entries in profile.hooks.items():
                existing = base_hooks.get(event_name, [])
                for entry in entries:
                    hook_dict: dict[str, str] = {
                        "type": "command",
                        "command": entry.command,
                    }
                    if entry.event:
                        hook_dict["matcher"] = entry.event
                    existing.append(hook_dict)
                base_hooks[event_name] = existing
            base["hooks"] = base_hooks

        # permissions: shallow merge, profile wins
        if profile.permissions:
            base_perms = base.get("permissions", {})
            base["permissions"] = base_perms | profile.permissions

        # statusline -> userStatusBar
        if profile.statusline:
            base["userStatusBar"] = {
                "segments": profile.statusline.segments,
                "style": profile.statusline.style,
            }

        # append system prompt file
        if profile.append_system_prompt_file:
            base["appendSystemPromptFile"] = profile.append_system_prompt_file

        # mcp config
        if profile.mcp_config:
            mcp_path = Path(profile.mcp_config).expanduser()
            if mcp_path.exists():
                try:
                    with open(mcp_path, encoding="utf-8") as f:
                        mcp_data = json.load(f)
                    base_mcp = base.get("mcpServers", {})
                    base["mcpServers"] = base_mcp | mcp_data
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning("Failed to read MCP config: %s", e)

        # plugin dirs
        if profile.plugin_dirs:
            base["pluginDirs"] = profile.plugin_dirs

        return base

    def build_command(self, temp_settings_path: Path) -> list[str]:
        """Build the claude CLI command with settings and profile flags."""
        cmd = ["claude"]
        cmd.extend(["--settings", str(temp_settings_path)])
        if self.profile.model:
            cmd.extend(["--model", self.profile.model])
        if self.profile.effort:
            cmd.extend(["--effort", self.profile.effort])
        return cmd

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
