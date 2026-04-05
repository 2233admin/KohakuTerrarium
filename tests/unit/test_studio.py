"""Tests for kt studio subsystem: config, profiles, launcher, CLI."""

import argparse
import json
import shutil
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import pytest

from kohakuterrarium.studio.config import (
    HookEntry,
    ProfileConfig,
    StatuslineConfig,
    StudioConfig,
    load_studio_config,
    save_studio_config,
)
from kohakuterrarium.studio.profiles import (
    create_profile,
    delete_profile,
    list_profiles,
    set_active_profile,
    show_profile,
)


# ── Config dataclass defaults ──


class TestProfileConfigDefaults:
    def test_default_model(self):
        p = ProfileConfig()
        assert p.model == "sonnet"

    def test_default_effort(self):
        p = ProfileConfig()
        assert p.effort == "high"

    def test_default_theme_none(self):
        p = ProfileConfig()
        assert p.theme is None

    def test_default_env_empty(self):
        p = ProfileConfig()
        assert p.env == {}

    def test_default_hooks_empty(self):
        p = ProfileConfig()
        assert p.hooks == {}

    def test_default_statusline_none(self):
        p = ProfileConfig()
        assert p.statusline is None

    def test_default_permissions_empty(self):
        p = ProfileConfig()
        assert p.permissions == {}

    def test_default_append_system_prompt_file_none(self):
        p = ProfileConfig()
        assert p.append_system_prompt_file is None

    def test_default_mcp_config_none(self):
        p = ProfileConfig()
        assert p.mcp_config is None

    def test_default_plugin_dirs_empty(self):
        p = ProfileConfig()
        assert p.plugin_dirs == []


class TestStudioConfigDefaults:
    def test_default_active_profile(self):
        c = StudioConfig()
        assert c.active_profile == "default"

    def test_default_profiles_empty(self):
        c = StudioConfig()
        assert c.profiles == {}


# ── Config load/save ──


class TestConfigLoadSave:
    def test_load_missing_file_returns_empty(self, tmp_path: Path):
        config = load_studio_config(tmp_path / "nonexistent.yaml")
        assert isinstance(config, StudioConfig)
        assert config.profiles == {}

    def test_save_and_load_roundtrip(self, tmp_path: Path):
        path = tmp_path / "studio.yaml"
        original = StudioConfig(
            active_profile="dev",
            profiles={
                "dev": ProfileConfig(model="opus", effort="low"),
                "ci": ProfileConfig(model="haiku", theme="dark"),
            },
        )
        save_studio_config(original, path)
        loaded = load_studio_config(path)
        assert loaded.active_profile == "dev"
        assert loaded.profiles["dev"].model == "opus"
        assert loaded.profiles["dev"].effort == "low"
        assert loaded.profiles["ci"].model == "haiku"
        assert loaded.profiles["ci"].theme == "dark"

    def test_save_creates_parent_dirs(self, tmp_path: Path):
        path = tmp_path / "deep" / "nested" / "studio.yaml"
        save_studio_config(StudioConfig(), path)
        assert path.exists()

    def test_roundtrip_with_hooks(self, tmp_path: Path):
        path = tmp_path / "studio.yaml"
        profile = ProfileConfig(
            hooks={"PreToolUse": [HookEntry(command="echo hi", event="Bash")]}
        )
        original = StudioConfig(profiles={"test": profile})
        save_studio_config(original, path)
        loaded = load_studio_config(path)
        hook = loaded.profiles["test"].hooks["PreToolUse"][0]
        assert hook.command == "echo hi"
        assert hook.event == "Bash"

    def test_roundtrip_with_statusline(self, tmp_path: Path):
        path = tmp_path / "studio.yaml"
        profile = ProfileConfig(
            statusline=StatuslineConfig(segments=["git", "model", "cost"], style="full")
        )
        original = StudioConfig(profiles={"test": profile})
        save_studio_config(original, path)
        loaded = load_studio_config(path)
        sl = loaded.profiles["test"].statusline
        assert sl is not None
        assert sl.segments == ["git", "model", "cost"]
        assert sl.style == "full"


# ── Profile CRUD ──


class TestProfileCRUD:
    def test_create_profile_basic(self, tmp_path: Path):
        path = tmp_path / "studio.yaml"
        p = create_profile("test", model="sonnet", config_path=path)
        assert p.model == "sonnet"
        assert p.effort == "high"
        # Verify persisted
        loaded = load_studio_config(path)
        assert "test" in loaded.profiles

    def test_create_profile_duplicate_raises(self, tmp_path: Path):
        path = tmp_path / "studio.yaml"
        create_profile("test", config_path=path)
        with pytest.raises(ValueError, match="already exists"):
            create_profile("test", config_path=path)

    def test_delete_profile(self, tmp_path: Path):
        path = tmp_path / "studio.yaml"
        create_profile("test", config_path=path)
        delete_profile("test", config_path=path)
        loaded = load_studio_config(path)
        assert "test" not in loaded.profiles

    def test_delete_nonexistent_raises(self, tmp_path: Path):
        path = tmp_path / "studio.yaml"
        with pytest.raises(KeyError, match="not found"):
            delete_profile("nope", config_path=path)

    def test_delete_active_profile_clears_active(self, tmp_path: Path):
        path = tmp_path / "studio.yaml"
        create_profile("dev", config_path=path)
        set_active_profile("dev", config_path=path)
        delete_profile("dev", config_path=path)
        loaded = load_studio_config(path)
        assert loaded.active_profile == ""

    def test_list_profiles_sorted(self, tmp_path: Path):
        path = tmp_path / "studio.yaml"
        create_profile("beta", config_path=path)
        create_profile("alpha", config_path=path)
        result = list_profiles(config_path=path)
        names = [name for name, _ in result]
        assert names == ["alpha", "beta"]

    def test_show_profile_found(self, tmp_path: Path):
        path = tmp_path / "studio.yaml"
        create_profile("test", model="opus", config_path=path)
        p = show_profile("test", config_path=path)
        assert p is not None
        assert p.model == "opus"

    def test_show_profile_not_found(self, tmp_path: Path):
        path = tmp_path / "studio.yaml"
        assert show_profile("nope", config_path=path) is None

    def test_set_active_profile(self, tmp_path: Path):
        path = tmp_path / "studio.yaml"
        create_profile("dev", config_path=path)
        set_active_profile("dev", config_path=path)
        loaded = load_studio_config(path)
        assert loaded.active_profile == "dev"

    def test_set_active_profile_empty_string(self, tmp_path: Path):
        path = tmp_path / "studio.yaml"
        set_active_profile("", config_path=path)
        loaded = load_studio_config(path)
        assert loaded.active_profile == ""

    def test_set_active_nonexistent_raises(self, tmp_path: Path):
        path = tmp_path / "studio.yaml"
        with pytest.raises(KeyError, match="not found"):
            set_active_profile("nope", config_path=path)


# ── ProfileLauncher ──


from kohakuterrarium.studio.launcher import ProfileLauncher, doctor, find_claude_cli


class TestProfileLauncher:
    def _make_launcher(
        self, profile: ProfileConfig | None = None
    ) -> ProfileLauncher:
        if profile is None:
            profile = ProfileConfig()
        return ProfileLauncher(profile, StudioConfig())

    def test_build_settings_json_merges_env(self, tmp_path: Path):
        """Base env A=1, profile env B=2 -> merged has both."""
        base = {"env": {"A": "1"}}
        settings_path = tmp_path / "settings.json"
        settings_path.write_text(json.dumps(base))

        profile = ProfileConfig(env={"B": "2"})
        launcher = self._make_launcher(profile)
        with patch(
            "kohakuterrarium.studio.launcher.CLAUDE_SETTINGS_PATH", settings_path
        ):
            merged = launcher.build_settings_json()
        assert merged["env"]["A"] == "1"
        assert merged["env"]["B"] == "2"

    def test_build_settings_json_profile_env_wins(self, tmp_path: Path):
        """Base env A=1, profile env A=99 -> merged A=99."""
        base = {"env": {"A": "1"}}
        settings_path = tmp_path / "settings.json"
        settings_path.write_text(json.dumps(base))

        profile = ProfileConfig(env={"A": "99"})
        launcher = self._make_launcher(profile)
        with patch(
            "kohakuterrarium.studio.launcher.CLAUDE_SETTINGS_PATH", settings_path
        ):
            merged = launcher.build_settings_json()
        assert merged["env"]["A"] == "99"

    def test_build_settings_json_hooks_append(self, tmp_path: Path):
        """Base has PreToolUse hooks, profile adds more -> both present."""
        base = {
            "hooks": {
                "PreToolUse": [{"type": "command", "command": "echo base"}]
            }
        }
        settings_path = tmp_path / "settings.json"
        settings_path.write_text(json.dumps(base))

        profile = ProfileConfig(
            hooks={"PreToolUse": [HookEntry(command="echo profile", event="Bash")]}
        )
        launcher = self._make_launcher(profile)
        with patch(
            "kohakuterrarium.studio.launcher.CLAUDE_SETTINGS_PATH", settings_path
        ):
            merged = launcher.build_settings_json()

        hooks = merged["hooks"]["PreToolUse"]
        assert len(hooks) == 2
        assert hooks[0]["command"] == "echo base"
        assert hooks[1]["command"] == "echo profile"
        assert hooks[1]["matcher"] == "Bash"

    def test_build_command_includes_model_effort(self, tmp_path: Path):
        """profile model=opus, effort=high -> command contains --model opus --effort high."""
        profile = ProfileConfig(model="opus", effort="high")
        launcher = self._make_launcher(profile)
        temp_settings = tmp_path / "settings.json"
        cmd = launcher.build_command(temp_settings)
        assert "--model" in cmd
        assert "opus" in cmd
        assert "--effort" in cmd
        assert "high" in cmd

    def test_build_command_with_settings_path(self, tmp_path: Path):
        """Temp path appears after --settings."""
        launcher = self._make_launcher()
        temp_settings = tmp_path / "settings.json"
        cmd = launcher.build_command(temp_settings)
        idx = cmd.index("--settings")
        assert cmd[idx + 1] == str(temp_settings)

    def test_build_settings_json_no_base_file(self, tmp_path: Path):
        """No base settings file -> works with empty base."""
        settings_path = tmp_path / "nonexistent.json"
        profile = ProfileConfig(env={"X": "1"})
        launcher = self._make_launcher(profile)
        with patch(
            "kohakuterrarium.studio.launcher.CLAUDE_SETTINGS_PATH", settings_path
        ):
            merged = launcher.build_settings_json()
        assert merged["env"] == {"X": "1"}


class TestDoctor:
    def test_doctor_missing_claude(self):
        with patch("kohakuterrarium.studio.launcher.shutil.which", return_value=None):
            issues = doctor()
        assert any("claude CLI" in i for i in issues)

    def test_find_claude_cli_found(self):
        with patch(
            "kohakuterrarium.studio.launcher.shutil.which",
            return_value="/usr/bin/claude",
        ):
            result = find_claude_cli()
        assert result == Path("/usr/bin/claude")

    def test_find_claude_cli_not_found(self):
        with patch("kohakuterrarium.studio.launcher.shutil.which", return_value=None):
            result = find_claude_cli()
        assert result is None


# ── CLI integration ──


from kohakuterrarium.studio.cli import add_studio_subparser, handle_studio_command


class TestStudioCLI:
    def test_studio_subparser_registers(self):
        """Parser recognizes 'studio profiles' command."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        add_studio_subparser(subparsers)
        args = parser.parse_args(["studio", "profiles"])
        assert args.command == "studio"
        assert args.studio_command == "profiles"

    def test_studio_init_creates_config(self, tmp_path: Path):
        """Init creates studio.yaml."""
        config_path = tmp_path / "studio.yaml"
        with patch(
            "kohakuterrarium.studio.handlers.STUDIO_CONFIG_PATH", config_path
        ), patch(
            "kohakuterrarium.studio.handlers.save_studio_config",
            wraps=lambda c, p=None: save_studio_config(c, config_path),
        ):
            args = argparse.Namespace(studio_command="init")
            result = handle_studio_command(args)
        assert result == 0
        assert config_path.exists()

    def test_studio_doctor_with_claude(self):
        """Doctor reports no claude CLI issue when claude is found."""
        with patch(
            "kohakuterrarium.studio.launcher.shutil.which",
            return_value="/usr/bin/claude",
        ):
            issues = doctor()
        # Claude CLI issue should not be present
        assert not any("claude CLI" in i for i in issues)

    def test_studio_parse_profile_create(self):
        """Parser parses 'studio profile create myprof --model opus'."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        add_studio_subparser(subparsers)
        args = parser.parse_args(
            ["studio", "profile", "create", "myprof", "--model", "opus"]
        )
        assert args.command == "studio"
        assert args.studio_command == "profile"
        assert args.profile_action == "create"
        assert args.name == "myprof"
        assert args.model == "opus"

    def test_studio_parse_launch_default(self):
        """Parser parses 'studio launch' with no profile arg."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        add_studio_subparser(subparsers)
        args = parser.parse_args(["studio", "launch"])
        assert args.command == "studio"
        assert args.studio_command == "launch"
        assert args.profile is None

    def test_studio_parse_apply_with_output(self):
        """Parser parses 'studio apply dev -o /tmp/out.json'."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        add_studio_subparser(subparsers)
        args = parser.parse_args(["studio", "apply", "dev", "-o", "/tmp/out.json"])
        assert args.studio_command == "apply"
        assert args.profile == "dev"
        assert args.output == "/tmp/out.json"
