"""Tests for kt studio targets: registry, ClaudeCodeTarget, CopilotTarget, delegation."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from kohakuterrarium.studio.config import HookEntry, ProfileConfig, StudioConfig
from kohakuterrarium.studio.launcher import ProfileLauncher
from kohakuterrarium.studio.targets import (
    TARGET_REGISTRY,
    list_targets,
    register_target,
    resolve_target,
)
from kohakuterrarium.studio.targets.base import Target
from kohakuterrarium.studio.targets.claude_code import ClaudeCodeTarget
from kohakuterrarium.studio.targets.copilot import CopilotTarget


# -- Registry tests --


class TestTargetRegistry:
    def test_register_target(self):
        """Custom target class can be registered and resolved."""

        class _DummyTarget(Target):
            name = "_test_dummy"
            display_name = "Dummy"

            def detect(self) -> Path | None:
                return None

            def build_command(self, profile, settings_path=None) -> list[str]:
                return ["dummy"]

            def list_models(self) -> list[str]:
                return []

            def status(self) -> dict:
                return {}

        register_target(_DummyTarget)
        try:
            t = resolve_target("_test_dummy")
            assert isinstance(t, _DummyTarget)
            assert t.name == "_test_dummy"
        finally:
            TARGET_REGISTRY.pop("_test_dummy", None)

    def test_resolve_unknown_raises(self):
        """resolve_target raises ValueError for unknown name."""
        with pytest.raises(ValueError, match="Unknown target"):
            resolve_target("nonexistent_target_xyz")

    def test_list_targets_includes_builtins(self):
        """list_targets returns both claude-code and copilot."""
        targets = list_targets()
        names = {t.name for t in targets}
        assert "claude-code" in names
        assert "copilot" in names
        assert len(targets) >= 2


# -- ClaudeCodeTarget tests --


class TestClaudeCodeTarget:
    def test_detect_found(self):
        """shutil.which returns path -> detect() returns Path."""
        target = ClaudeCodeTarget()
        with patch(
            "kohakuterrarium.studio.targets.claude_code.shutil.which",
            return_value="/usr/bin/claude",
        ):
            result = target.detect()
        assert result == Path("/usr/bin/claude")

    def test_detect_missing(self):
        """shutil.which returns None -> detect() returns None."""
        target = ClaudeCodeTarget()
        with patch(
            "kohakuterrarium.studio.targets.claude_code.shutil.which",
            return_value=None,
        ):
            result = target.detect()
        assert result is None

    def test_build_command(self):
        """build_command produces correct claude CLI args."""
        target = ClaudeCodeTarget()
        profile = ProfileConfig(model="opus", effort="high")
        cmd = target.build_command(profile, Path("/tmp/s.json"))
        assert cmd[0] == "claude"
        assert "--settings" in cmd
        assert str(Path("/tmp/s.json")) in cmd
        assert "--model" in cmd
        assert "opus" in cmd
        assert "--effort" in cmd
        assert "high" in cmd

    def test_build_command_no_settings(self):
        """build_command without settings_path omits --settings."""
        target = ClaudeCodeTarget()
        profile = ProfileConfig(model="sonnet", effort="low")
        cmd = target.build_command(profile)
        assert "--settings" not in cmd
        assert "sonnet" in cmd

    def test_merge_settings_env(self, tmp_path: Path):
        """env dict-merge: base A=1, profile B=2 -> merged has both."""
        target = ClaudeCodeTarget()
        base = {"env": {"A": "1"}}
        profile = ProfileConfig(env={"B": "2"})
        merged = target.merge_settings(base, profile)
        assert merged["env"]["A"] == "1"
        assert merged["env"]["B"] == "2"

    def test_merge_settings_hooks_append(self):
        """hooks extend, not replace."""
        target = ClaudeCodeTarget()
        base = {
            "hooks": {
                "PreToolUse": [{"type": "command", "command": "echo base"}]
            }
        }
        profile = ProfileConfig(
            hooks={"PreToolUse": [HookEntry(command="echo profile", event="Bash")]}
        )
        merged = target.merge_settings(base, profile)
        hooks = merged["hooks"]["PreToolUse"]
        assert len(hooks) == 2
        assert hooks[0]["command"] == "echo base"
        assert hooks[1]["command"] == "echo profile"

    def test_list_models(self):
        """list_models returns Claude model shortnames."""
        target = ClaudeCodeTarget()
        models = target.list_models()
        assert "sonnet" in models
        assert "opus" in models
        assert "haiku" in models

    def test_settings_path(self):
        """settings_path returns ~/.claude/settings.json."""
        target = ClaudeCodeTarget()
        sp = target.settings_path()
        assert sp is not None
        assert sp.name == "settings.json"


# -- CopilotTarget tests --


class TestCopilotTarget:
    def test_detect(self):
        """Copilot detect delegates to find_copilot_cli."""
        target = CopilotTarget()
        with patch(
            "kohakuterrarium.studio.targets.copilot.copilot_module.find_copilot_cli",
            return_value=Path("/usr/bin/github-copilot-cli"),
        ):
            result = target.detect()
        assert result == Path("/usr/bin/github-copilot-cli")

    def test_list_models(self):
        """list_models returns non-empty list of copilot models."""
        target = CopilotTarget()
        models = target.list_models()
        assert len(models) > 0
        assert "gpt-4o" in models


# -- Integration tests --


class TestTargetIntegration:
    def test_profile_target_default(self):
        """ProfileConfig().target defaults to 'claude-code'."""
        assert ProfileConfig().target == "claude-code"

    def test_launcher_delegates_to_target(self, tmp_path: Path):
        """ProfileLauncher.build_settings_json delegates to target.merge_settings."""
        settings_path = tmp_path / "settings.json"
        settings_path.write_text(json.dumps({"env": {"X": "1"}}))

        profile = ProfileConfig(env={"Y": "2"})
        launcher = ProfileLauncher(profile, StudioConfig())
        with patch(
            "kohakuterrarium.studio.launcher.CLAUDE_SETTINGS_PATH", settings_path
        ):
            merged = launcher.build_settings_json()
        assert merged["env"]["X"] == "1"
        assert merged["env"]["Y"] == "2"

    def test_launcher_delegates_build_command(self, tmp_path: Path):
        """ProfileLauncher.build_command delegates to target.build_command."""
        profile = ProfileConfig(model="haiku", effort="low")
        launcher = ProfileLauncher(profile, StudioConfig())
        cmd = launcher.build_command(tmp_path / "settings.json")
        assert "claude" in cmd
        assert "haiku" in cmd
