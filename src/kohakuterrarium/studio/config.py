"""Studio configuration: dataclasses + YAML load/save for studio profiles."""

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)

KT_DIR = Path.home() / ".kohakuterrarium"
STUDIO_CONFIG_PATH = KT_DIR / "studio.yaml"


@dataclass
class StatuslineConfig:
    """Configuration for the Claude Code status bar."""

    segments: list[str] = field(default_factory=lambda: ["git", "model"])
    style: str = "minimal"


@dataclass
class HookEntry:
    """A single hook command entry."""

    command: str = ""
    event: str = ""


@dataclass
class ProfileConfig:
    """Configuration for a single studio profile."""

    model: str = "sonnet"
    effort: str = "high"
    theme: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    hooks: dict[str, list[HookEntry]] = field(default_factory=dict)
    statusline: StatuslineConfig | None = None
    permissions: dict[str, Any] = field(default_factory=dict)
    append_system_prompt_file: str | None = None
    mcp_config: str | None = None
    plugin_dirs: list[str] = field(default_factory=list)
    target: str = "claude-code"


@dataclass
class SessionEntry:
    """A named Claude Code session reference."""

    uuid: str
    project_dir: str = ""
    created: str = ""
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    target: str = "claude-code"


@dataclass
class StudioConfig:
    """Top-level studio configuration."""

    active_profile: str = "default"
    profiles: dict[str, ProfileConfig] = field(default_factory=dict)
    sessions: dict[str, SessionEntry] = field(default_factory=dict)


def _dict_to_hook(d: dict | str) -> HookEntry:
    """Convert a YAML dict (or plain string) to HookEntry."""
    if isinstance(d, str):
        return HookEntry(command=d)
    return HookEntry(
        command=d.get("command", ""),
        event=d.get("event", ""),
    )


def _dict_to_statusline(d: dict | None) -> StatuslineConfig | None:
    """Convert a YAML dict to StatuslineConfig."""
    if d is None:
        return None
    return StatuslineConfig(
        segments=d.get("segments", ["git", "model"]),
        style=d.get("style", "minimal"),
    )


def _dict_to_profile(d: dict) -> ProfileConfig:
    """Convert a YAML dict to ProfileConfig dataclass."""
    hooks_raw: dict[str, list] = d.get("hooks", {})
    hooks: dict[str, list[HookEntry]] = {}
    for event_name, entries in hooks_raw.items():
        hooks[event_name] = [_dict_to_hook(e) for e in entries]

    return ProfileConfig(
        model=d.get("model", "sonnet"),
        effort=d.get("effort", "high"),
        theme=d.get("theme"),
        env=d.get("env", {}),
        hooks=hooks,
        statusline=_dict_to_statusline(d.get("statusline")),
        permissions=d.get("permissions", {}),
        append_system_prompt_file=d.get("append_system_prompt_file"),
        mcp_config=d.get("mcp_config"),
        plugin_dirs=d.get("plugin_dirs", []),
        target=d.get("target", "claude-code"),
    )


def load_studio_config(path: Path | None = None) -> StudioConfig:
    """Load studio configuration from YAML.

    If the file does not exist, returns a StudioConfig with empty profiles.
    """
    config_path = path or STUDIO_CONFIG_PATH
    if not config_path.exists():
        return StudioConfig(profiles={})

    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not raw or not isinstance(raw, dict):
        return StudioConfig(profiles={})

    profiles: dict[str, ProfileConfig] = {}
    for name, profile_dict in raw.get("profiles", {}).items():
        if isinstance(profile_dict, dict):
            profiles[name] = _dict_to_profile(profile_dict)
        else:
            profiles[name] = ProfileConfig()

    sessions: dict[str, SessionEntry] = {}
    for name, session_dict in raw.get("sessions", {}).items():
        if isinstance(session_dict, dict):
            sessions[name] = SessionEntry(
                uuid=session_dict.get("uuid", ""),
                project_dir=session_dict.get("project_dir", ""),
                created=session_dict.get("created", ""),
                tags=session_dict.get("tags", []),
                notes=session_dict.get("notes", ""),
                target=session_dict.get("target", "claude-code"),
            )

    return StudioConfig(
        active_profile=raw.get("active_profile", "default"),
        profiles=profiles,
        sessions=sessions,
    )


def save_studio_config(config: StudioConfig, path: Path | None = None) -> None:
    """Save studio configuration to YAML.

    Creates parent directories if needed.
    """
    config_path = path or STUDIO_CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)

    data = _config_to_dict(config)
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def _config_to_dict(config: StudioConfig) -> dict:
    """Convert StudioConfig to a plain dict for YAML serialization."""
    profiles_dict: dict[str, dict] = {}
    for name, profile in config.profiles.items():
        profiles_dict[name] = _profile_to_dict(profile)

    sessions_dict: dict[str, dict] = {}
    for name, entry in config.sessions.items():
        sessions_dict[name] = dataclasses.asdict(entry)

    result: dict[str, Any] = {
        "active_profile": config.active_profile,
        "profiles": profiles_dict,
    }
    if sessions_dict:
        result["sessions"] = sessions_dict
    return result


def _profile_to_dict(profile: ProfileConfig) -> dict:
    """Convert ProfileConfig to a plain dict."""
    d: dict[str, Any] = {
        "model": profile.model,
        "effort": profile.effort,
    }
    if profile.theme is not None:
        d["theme"] = profile.theme
    if profile.env:
        d["env"] = profile.env
    if profile.hooks:
        hooks_dict: dict[str, list[dict]] = {}
        for event_name, entries in profile.hooks.items():
            hooks_dict[event_name] = [
                {"command": e.command, "event": e.event} for e in entries
            ]
        d["hooks"] = hooks_dict
    if profile.statusline is not None:
        d["statusline"] = dataclasses.asdict(profile.statusline)
    if profile.permissions:
        d["permissions"] = profile.permissions
    if profile.append_system_prompt_file is not None:
        d["append_system_prompt_file"] = profile.append_system_prompt_file
    if profile.mcp_config is not None:
        d["mcp_config"] = profile.mcp_config
    if profile.plugin_dirs:
        d["plugin_dirs"] = profile.plugin_dirs
    if profile.target != "claude-code":
        d["target"] = profile.target
    return d
