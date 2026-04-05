"""Profile CRUD operations for kt studio."""

import argparse
import dataclasses
import os
import subprocess
from pathlib import Path

from kohakuterrarium.studio.config import (
    ProfileConfig,
    load_studio_config,
    save_studio_config,
)
from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)


def create_profile(
    name: str,
    model: str = "sonnet",
    effort: str = "high",
    theme: str | None = None,
    config_path: Path | None = None,
) -> ProfileConfig:
    """Create a new profile.

    Raises ValueError if a profile with the same name already exists.
    """
    config = load_studio_config(config_path)
    if name in config.profiles:
        raise ValueError(f"Profile '{name}' already exists")

    profile = ProfileConfig(model=model, effort=effort, theme=theme)
    config.profiles[name] = profile
    save_studio_config(config, config_path)
    logger.info("Created profile '%s' (model=%s, effort=%s)", name, model, effort)
    return profile


def delete_profile(name: str, config_path: Path | None = None) -> None:
    """Delete a profile.

    Raises KeyError if the profile does not exist.
    Clears active_profile if the deleted profile was active.
    """
    config = load_studio_config(config_path)
    if name not in config.profiles:
        raise KeyError(f"Profile '{name}' not found")

    del config.profiles[name]
    if config.active_profile == name:
        config.active_profile = ""
    save_studio_config(config, config_path)
    logger.info("Deleted profile '%s'", name)


def list_profiles(
    config_path: Path | None = None,
) -> list[tuple[str, ProfileConfig]]:
    """List all profiles, sorted by name."""
    config = load_studio_config(config_path)
    return sorted(config.profiles.items(), key=lambda x: x[0])


def show_profile(name: str, config_path: Path | None = None) -> ProfileConfig | None:
    """Show a single profile by name. Returns None if not found."""
    config = load_studio_config(config_path)
    return config.profiles.get(name)


def edit_profile(name: str, config_path: Path | None = None) -> None:
    """Open the studio config in $EDITOR for editing.

    Validates that the profile exists before opening.
    Raises KeyError if the profile does not exist.
    """
    config = load_studio_config(config_path)
    if name not in config.profiles:
        raise KeyError(f"Profile '{name}' not found")

    from kohakuterrarium.studio.config import STUDIO_CONFIG_PATH

    target = config_path or STUDIO_CONFIG_PATH
    editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "nano"))
    subprocess.run([editor, str(target)], check=False)


def set_active_profile(name: str, config_path: Path | None = None) -> None:
    """Set the active profile.

    Empty string clears the active profile.
    Raises KeyError if name is non-empty and profile does not exist.
    """
    config = load_studio_config(config_path)
    if name and name not in config.profiles:
        raise KeyError(f"Profile '{name}' not found")

    config.active_profile = name
    save_studio_config(config, config_path)
    logger.info("Active profile set to '%s'", name)


def diff_profiles(
    name_a: str,
    name_b: str,
    config_path: Path | None = None,
) -> dict[str, tuple]:
    """Compare two profiles field by field.

    Returns {field_name: (value_a, value_b)} for fields that differ.
    Empty dict means identical. Raises KeyError if either profile not found.
    """
    config = load_studio_config(config_path)
    profile_a = config.profiles.get(name_a)
    if profile_a is None:
        raise KeyError(f"Profile '{name_a}' not found")
    profile_b = config.profiles.get(name_b)
    if profile_b is None:
        raise KeyError(f"Profile '{name_b}' not found")

    dict_a = dataclasses.asdict(profile_a)
    dict_b = dataclasses.asdict(profile_b)

    diffs: dict[str, tuple] = {}
    all_keys = set(dict_a.keys()) | set(dict_b.keys())
    for key in sorted(all_keys):
        val_a = dict_a.get(key)
        val_b = dict_b.get(key)
        if val_a != val_b:
            diffs[key] = (val_a, val_b)
    return diffs


def handle_diff_command(args: argparse.Namespace) -> int:
    """CLI handler for 'kt studio diff'."""
    try:
        diffs = diff_profiles(args.profile_a, args.profile_b)
    except KeyError as e:
        print(f"Error: {e}")
        return 1

    if not diffs:
        print("Profiles are identical.")
        return 0

    print(f"{'Field':<30} {'Profile A':<25} {'Profile B'}")
    print("-" * 80)
    for field_name, (val_a, val_b) in diffs.items():
        print(f"{field_name:<30} {str(val_a):<25} {str(val_b)}")
    return 0
