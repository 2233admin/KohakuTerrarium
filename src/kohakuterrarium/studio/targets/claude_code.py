"""ClaudeCodeTarget: Claude Code CLI backend for kt studio."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

from kohakuterrarium.studio.targets import register_target
from kohakuterrarium.studio.targets.base import Target
from kohakuterrarium.utils.logging import get_logger

if TYPE_CHECKING:
    from kohakuterrarium.studio.config import ProfileConfig

logger = get_logger(__name__)

CLAUDE_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"


@register_target
class ClaudeCodeTarget(Target):
    """Target implementation for the Claude Code CLI."""

    name = "claude-code"
    display_name = "Claude Code"

    def detect(self) -> Path | None:
        """Return claude CLI path if installed, else None."""
        result = shutil.which("claude")
        if result:
            return Path(result)
        return None

    def build_command(
        self, profile: ProfileConfig, settings_path: Path | None = None
    ) -> list[str]:
        """Build claude CLI command with settings and profile flags."""
        cmd = ["claude"]
        if settings_path is not None:
            cmd.extend(["--settings", str(settings_path)])
        if profile.model:
            cmd.extend(["--model", profile.model])
        if profile.effort:
            cmd.extend(["--effort", profile.effort])
        return cmd

    def merge_settings(
        self, base: dict[str, Any], profile: ProfileConfig
    ) -> dict[str, Any]:
        """Load ~/.claude/settings.json and apply profile overrides.

        Merge semantics:
        - env: dict merge, profile wins
        - hooks: extend lists per event key
        - permissions: shallow merge, profile wins
        - statusline -> userStatusBar
        - append_system_prompt_file -> appendSystemPromptFile
        - mcp_config -> mcpServers (merge from JSON file)
        - plugin_dirs -> pluginDirs
        """
        merged: dict[str, Any] = {}
        if CLAUDE_SETTINGS_PATH.exists():
            try:
                with open(CLAUDE_SETTINGS_PATH, encoding="utf-8") as f:
                    merged = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to read base settings: %s", e)

        # env: dict merge, profile wins
        if profile.env:
            base_env = merged.get("env", {})
            merged["env"] = base_env | profile.env

        # hooks: extend lists per event key
        if profile.hooks:
            base_hooks: dict[str, list] = merged.get("hooks", {})
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
            merged["hooks"] = base_hooks

        # permissions: shallow merge, profile wins
        if profile.permissions:
            base_perms = merged.get("permissions", {})
            merged["permissions"] = base_perms | profile.permissions

        # statusline -> userStatusBar
        if profile.statusline:
            merged["userStatusBar"] = {
                "segments": profile.statusline.segments,
                "style": profile.statusline.style,
            }

        # append system prompt file
        if profile.append_system_prompt_file:
            merged["appendSystemPromptFile"] = profile.append_system_prompt_file

        # mcp config
        if profile.mcp_config:
            mcp_path = Path(profile.mcp_config).expanduser()
            if mcp_path.exists():
                try:
                    with open(mcp_path, encoding="utf-8") as f:
                        mcp_data = json.load(f)
                    base_mcp = merged.get("mcpServers", {})
                    merged["mcpServers"] = base_mcp | mcp_data
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning("Failed to read MCP config: %s", e)

        # plugin dirs
        if profile.plugin_dirs:
            merged["pluginDirs"] = profile.plugin_dirs

        return merged

    def list_models(self) -> list[str]:
        """Return Claude model shortnames."""
        return ["sonnet", "opus", "haiku"]

    def status(self) -> dict:
        """Return Claude Code installation status."""
        cli = self.detect()
        return {
            "installed": cli is not None,
            "cli_path": str(cli) if cli else None,
            "settings_path": str(CLAUDE_SETTINGS_PATH),
        }

    def settings_path(self) -> Path | None:
        """Return path to Claude settings.json."""
        return CLAUDE_SETTINGS_PATH

    def session_dir(self) -> Path | None:
        """Return Claude Code projects directory."""
        return Path.home() / ".claude" / "projects"
