"""Tests for kt studio targets: registry, ClaudeCodeTarget, CopilotTarget, and new targets."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

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
from kohakuterrarium.studio.targets.codex import CodexTarget
from kohakuterrarium.studio.targets.copilot import CopilotTarget
from kohakuterrarium.studio.targets.gemini import GeminiTarget
from kohakuterrarium.studio.targets.openclaw import OpenClawTarget
from kohakuterrarium.studio.targets.aider import AiderTarget

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
        base = {"hooks": {"PreToolUse": [{"type": "command", "command": "echo base"}]}}
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


# -- CodexTarget tests --


class TestCodexTarget:
    def test_detect_found(self):
        """shutil.which returns path -> detect() returns Path."""
        target = CodexTarget()
        with patch(
            "kohakuterrarium.studio.targets.codex.shutil.which",
            return_value="/usr/bin/codex",
        ):
            result = target.detect()
        assert result == Path("/usr/bin/codex")

    def test_detect_missing(self):
        """shutil.which returns None -> detect() returns None."""
        target = CodexTarget()
        with patch(
            "kohakuterrarium.studio.targets.codex.shutil.which",
            return_value=None,
        ):
            result = target.detect()
        assert result is None

    def test_build_command(self):
        """build_command produces codex CLI args with model flag."""
        target = CodexTarget()
        profile = ProfileConfig(model="o4-mini")
        cmd = target.build_command(profile)
        assert cmd[0] == "codex"
        assert "--model" in cmd
        assert "o4-mini" in cmd

    def test_list_models(self):
        """list_models returns non-empty list including o4-mini."""
        target = CodexTarget()
        models = target.list_models()
        assert len(models) > 0
        assert "o4-mini" in models

    def test_status_installed(self):
        """status returns installed=True when CLI found."""
        target = CodexTarget()
        with patch(
            "kohakuterrarium.studio.targets.codex.shutil.which",
            return_value="/usr/bin/codex",
        ):
            info = target.status()
        assert info["installed"] is True
        assert info["cli_path"] is not None

    def test_settings_path(self):
        """settings_path returns ~/.codex path."""
        target = CodexTarget()
        sp = target.settings_path()
        assert sp is not None
        assert ".codex" in str(sp)


# -- GeminiTarget tests --


class TestGeminiTarget:
    def test_detect_found(self):
        """shutil.which returns path -> detect() returns Path."""
        target = GeminiTarget()
        with patch(
            "kohakuterrarium.studio.targets.gemini.shutil.which",
            return_value="/usr/bin/gemini",
        ):
            result = target.detect()
        assert result == Path("/usr/bin/gemini")

    def test_detect_missing(self):
        """shutil.which returns None -> detect() returns None."""
        target = GeminiTarget()
        with patch(
            "kohakuterrarium.studio.targets.gemini.shutil.which",
            return_value=None,
        ):
            result = target.detect()
        assert result is None

    def test_build_command(self):
        """build_command produces gemini CLI args with model flag."""
        target = GeminiTarget()
        profile = ProfileConfig(model="gemini-2.5-pro")
        cmd = target.build_command(profile)
        assert cmd[0] == "gemini"
        assert "--model" in cmd
        assert "gemini-2.5-pro" in cmd

    def test_list_models(self):
        """list_models returns non-empty list including gemini-2.5-pro."""
        target = GeminiTarget()
        models = target.list_models()
        assert len(models) > 0
        assert "gemini-2.5-pro" in models

    def test_status_installed(self):
        """status returns installed=True when CLI found."""
        target = GeminiTarget()
        with patch(
            "kohakuterrarium.studio.targets.gemini.shutil.which",
            return_value="/usr/bin/gemini",
        ):
            info = target.status()
        assert info["installed"] is True
        assert info["cli_path"] is not None


# -- OpenClawTarget tests --


class TestOpenClawTarget:
    def test_detect_reachable(self):
        """httpx.get success -> detect() returns Path('openclaw')."""
        target = OpenClawTarget()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch(
            "kohakuterrarium.studio.targets.openclaw.httpx.get",
            return_value=mock_resp,
        ):
            result = target.detect()
        assert result == Path("openclaw")

    def test_detect_unreachable(self):
        """httpx.get raises -> detect() returns None."""
        target = OpenClawTarget()
        with patch(
            "kohakuterrarium.studio.targets.openclaw.httpx.get",
            side_effect=Exception("Connection refused"),
        ):
            result = target.detect()
        assert result is None

    def test_list_models_success(self):
        """list_models parses /v1/models response."""
        target = OpenClawTarget()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [{"id": "claude-sonnet-4"}, {"id": "gpt-4o"}]
        }
        with patch(
            "kohakuterrarium.studio.targets.openclaw.httpx.get",
            return_value=mock_resp,
        ):
            models = target.list_models()
        assert "claude-sonnet-4" in models
        assert "gpt-4o" in models

    def test_list_models_error(self):
        """list_models returns empty list on connection error."""
        target = OpenClawTarget()
        with patch(
            "kohakuterrarium.studio.targets.openclaw.httpx.get",
            side_effect=Exception("timeout"),
        ):
            models = target.list_models()
        assert models == []

    def test_build_command_raises(self):
        """build_command raises NotImplementedError (server, not CLI)."""
        target = OpenClawTarget()
        profile = ProfileConfig()
        with pytest.raises(NotImplementedError):
            target.build_command(profile)

    def test_custom_endpoint(self):
        """OpenClawTarget accepts custom endpoint."""
        target = OpenClawTarget(endpoint="http://myhost:9999")
        assert target._endpoint == "http://myhost:9999"

    def test_status_reachable(self):
        """status returns installed=True when endpoint reachable."""
        target = OpenClawTarget()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"id": "m1"}, {"id": "m2"}]}
        with patch(
            "kohakuterrarium.studio.targets.openclaw.httpx.get",
            return_value=mock_resp,
        ):
            info = target.status()
        assert info["installed"] is True
        assert info["model_count"] == 2


# -- AiderTarget tests --


class TestAiderTarget:
    def test_detect_found(self):
        """shutil.which returns path -> detect() returns Path."""
        target = AiderTarget()
        with patch(
            "kohakuterrarium.studio.targets.aider.shutil.which",
            return_value="/usr/bin/aider",
        ):
            result = target.detect()
        assert result == Path("/usr/bin/aider")

    def test_detect_missing(self):
        """shutil.which returns None -> detect() returns None."""
        target = AiderTarget()
        with patch(
            "kohakuterrarium.studio.targets.aider.shutil.which",
            return_value=None,
        ):
            result = target.detect()
        assert result is None

    def test_build_command(self):
        """build_command produces aider CLI args with model flag."""
        target = AiderTarget()
        profile = ProfileConfig(model="gpt-4o")
        cmd = target.build_command(profile)
        assert cmd[0] == "aider"
        assert "--model" in cmd
        assert "gpt-4o" in cmd

    def test_list_models(self):
        """list_models returns non-empty list."""
        target = AiderTarget()
        models = target.list_models()
        assert len(models) > 0

    def test_status_installed(self):
        """status returns installed=True when CLI found."""
        target = AiderTarget()
        with patch(
            "kohakuterrarium.studio.targets.aider.shutil.which",
            return_value="/usr/bin/aider",
        ):
            info = target.status()
        assert info["installed"] is True
        assert info["cli_path"] is not None

    def test_settings_path(self):
        """settings_path returns ~/.aider.conf.yml."""
        target = AiderTarget()
        sp = target.settings_path()
        assert sp is not None
        assert ".aider" in str(sp)


# -- Updated registry count --


class TestRegistryCount:
    def test_list_targets_includes_all_six(self):
        """list_targets() returns all 6 registered targets."""
        targets = list_targets()
        names = {t.name for t in targets}
        assert names == {
            "claude-code",
            "copilot",
            "codex",
            "gemini",
            "openclaw",
            "aider",
        }
        assert len(targets) == 6


# -- Cross-tool session aggregation tests --


class TestScanAllSessions:
    def test_scan_all_sessions_aggregates(self):
        """scan_all_sessions aggregates from installed targets with 'target' field."""
        from kohakuterrarium.studio.sessions import scan_all_sessions

        mock_sessions_a = [{"uuid": "aaa", "modified": "2026-01-01T00:00:00Z"}]
        mock_sessions_b = [{"uuid": "bbb", "modified": "2026-01-02T00:00:00Z"}]

        target_a = MagicMock()
        target_a.name = "tool-a"
        target_a.detect.return_value = Path("/bin/a")
        target_a.scan_sessions.return_value = mock_sessions_a

        target_b = MagicMock()
        target_b.name = "tool-b"
        target_b.detect.return_value = Path("/bin/b")
        target_b.scan_sessions.return_value = mock_sessions_b

        with patch(
            "kohakuterrarium.studio.targets.list_targets",
            return_value=[target_a, target_b],
        ):
            result = scan_all_sessions()

        assert len(result) == 2
        # sorted by modified desc -- bbb first
        assert result[0]["uuid"] == "bbb"
        assert result[0]["target"] == "tool-b"
        assert result[1]["uuid"] == "aaa"
        assert result[1]["target"] == "tool-a"

    def test_scan_all_sessions_skips_uninstalled(self):
        """scan_all_sessions skips targets where detect() returns None."""
        from kohakuterrarium.studio.sessions import scan_all_sessions

        target_installed = MagicMock()
        target_installed.name = "installed"
        target_installed.detect.return_value = Path("/bin/inst")
        target_installed.scan_sessions.return_value = [
            {"uuid": "xxx", "modified": "2026-01-01T00:00:00Z"}
        ]

        target_missing = MagicMock()
        target_missing.name = "missing"
        target_missing.detect.return_value = None

        with patch(
            "kohakuterrarium.studio.targets.list_targets",
            return_value=[target_installed, target_missing],
        ):
            result = scan_all_sessions()

        assert len(result) == 1
        assert result[0]["target"] == "installed"
        target_missing.scan_sessions.assert_not_called()
