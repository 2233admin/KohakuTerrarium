"""Tests for kt studio themes + statusline modules."""

import json
import os
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kohakuterrarium.studio.config import StatuslineConfig

# -- Themes --


from kohakuterrarium.studio.themes import (
    BUILTIN_THEMES,
    ThemeColors,
    get_theme,
    list_themes,
    preview_theme,
    theme_to_settings,
)


class TestListThemes:
    def test_returns_6_themes(self):
        result = list_themes()
        assert len(result) == 6

    def test_returns_sorted(self):
        result = list_themes()
        assert result == sorted(result)

    def test_known_names(self):
        result = list_themes()
        for name in ["dark", "light", "nord", "tokyo-night", "rose-pine", "gruvbox"]:
            assert name in result


class TestGetTheme:
    def test_valid_theme_returns_dict(self):
        result = get_theme("nord")
        assert isinstance(result, dict)
        assert "background" in result
        assert "accent" in result
        assert "text" in result

    def test_invalid_theme_returns_none(self):
        assert get_theme("nonexistent") is None

    def test_all_themes_have_required_keys(self):
        required = {"primary", "secondary", "accent", "background", "surface", "text"}
        for name in list_themes():
            theme = get_theme(name)
            assert theme is not None
            assert required.issubset(theme.keys()), f"{name} missing keys"


class TestPreviewTheme:
    def test_valid_theme_returns_string(self):
        result = preview_theme("dark")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_invalid_theme_returns_empty(self):
        result = preview_theme("nope")
        assert result == ""


class TestThemeToSettings:
    def test_valid_theme(self):
        result = theme_to_settings("gruvbox")
        assert "theme" in result
        assert isinstance(result["theme"], dict)

    def test_invalid_theme_returns_empty(self):
        result = theme_to_settings("nope")
        assert result == {}


# -- Statusline --


from kohakuterrarium.studio.statusline import (
    SEGMENT_REGISTRY,
    StatusLineBuilder,
    render_segments,
)


class TestSegments:
    def test_clock_format(self):
        fn = SEGMENT_REGISTRY["clock"]
        result = fn()
        assert re.match(r"\d{2}:\d{2}", result)

    def test_model_from_env(self):
        fn = SEGMENT_REGISTRY["model"]
        with patch.dict(os.environ, {"CLAUDE_MODEL": "opus"}):
            result = fn()
        assert result == "opus"

    def test_model_empty_when_no_env(self):
        fn = SEGMENT_REGISTRY["model"]
        with patch.dict(os.environ, {}, clear=True):
            result = fn()
        assert result == ""

    def test_git_mocked(self):
        fn = SEGMENT_REGISTRY["git"]
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "main\n"
        diff_result = MagicMock()
        diff_result.returncode = 0
        diff_result.stdout = " 2 files changed, 10 insertions(+), 3 deletions(-)\n"
        with patch(
            "kohakuterrarium.studio.statusline.subprocess.run",
            side_effect=[mock_result, diff_result],
        ):
            result = fn()
        assert "main" in result

    def test_session_from_env(self):
        fn = SEGMENT_REGISTRY["session"]
        with patch.dict(os.environ, {"CLAUDE_SESSION_ID": "abcdef1234567890"}):
            result = fn()
        assert result == "abcdef12"

    def test_all_segments_registered(self):
        expected = {"git", "tokens", "cost", "model", "session", "clock"}
        assert expected == set(SEGMENT_REGISTRY.keys())


class TestRenderSegments:
    def test_minimal_joins_with_pipe(self):
        result = render_segments(["main +1", "sonnet"], "minimal")
        assert result == "main +1 | sonnet"

    def test_powerline_includes_arrow(self):
        result = render_segments(["main", "sonnet"], "powerline")
        assert "\ue0b0" in result

    def test_capsule_wraps_brackets(self):
        result = render_segments(["main", "sonnet"], "capsule")
        assert "[main]" in result
        assert "[sonnet]" in result

    def test_empty_segments_filtered(self):
        result = render_segments(["main", "", "sonnet", ""], "minimal")
        assert result == "main | sonnet"

    def test_unknown_style_defaults_to_minimal(self):
        result = render_segments(["a", "b"], "unknown_style")
        assert result == "a | b"


class TestStatusLineBuilder:
    def test_generate_script_compiles(self):
        cfg = StatuslineConfig(segments=["clock", "model"], style="minimal")
        builder = StatusLineBuilder(cfg)
        script = builder.generate_script()
        compile(script, "<test>", "exec")

    def test_generate_script_no_kt_imports(self):
        cfg = StatuslineConfig(segments=["clock", "model"], style="minimal")
        builder = StatusLineBuilder(cfg)
        script = builder.generate_script()
        assert "kohakuterrarium" not in script

    def test_generate_script_has_shebang(self):
        cfg = StatuslineConfig(segments=["clock"], style="minimal")
        builder = StatusLineBuilder(cfg)
        script = builder.generate_script()
        assert script.startswith("#!/usr/bin/env python3")

    def test_preview_returns_string(self):
        cfg = StatuslineConfig(segments=["clock"], style="minimal")
        builder = StatusLineBuilder(cfg)
        result = builder.preview()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_builder_with_theme(self):
        cfg = StatuslineConfig(segments=["clock"], style="minimal")
        builder = StatusLineBuilder(cfg, theme_name="nord")
        script = builder.generate_script()
        # Should contain some reference to nord's accent color
        assert "#88c0d0" in script or "THEME" in script

    def test_install_writes_settings(self, tmp_path: Path):
        cfg = StatuslineConfig(segments=["clock"], style="minimal")
        builder = StatusLineBuilder(cfg)
        settings_path = tmp_path / "settings.json"
        settings_path.write_text("{}", encoding="utf-8")
        runner_dir = tmp_path / "studio"
        runner_dir.mkdir()

        with patch("kohakuterrarium.studio.statusline.KT_DIR", tmp_path):
            builder.install(settings_path=settings_path)

        data = json.loads(settings_path.read_text(encoding="utf-8"))
        assert "statusLine" in data
        assert "command" in data["statusLine"]
        assert "python" in data["statusLine"]["command"]

    def test_uninstall_removes_settings(self, tmp_path: Path):
        cfg = StatuslineConfig(segments=["clock"], style="minimal")
        builder = StatusLineBuilder(cfg)
        settings_path = tmp_path / "settings.json"
        settings_path.write_text(
            json.dumps({"statusLine": {"command": "python foo.py"}}),
            encoding="utf-8",
        )
        runner_dir = tmp_path / "studio"
        runner_dir.mkdir()
        runner_file = runner_dir / "statusline_runner.py"
        runner_file.write_text("# dummy", encoding="utf-8")

        with patch("kohakuterrarium.studio.statusline.KT_DIR", tmp_path):
            builder.uninstall(settings_path=settings_path)

        data = json.loads(settings_path.read_text(encoding="utf-8"))
        assert "statusLine" not in data
        assert not runner_file.exists()

    def test_generate_all_segments(self):
        cfg = StatuslineConfig(
            segments=["git", "tokens", "cost", "model", "session", "clock"],
            style="capsule",
        )
        builder = StatusLineBuilder(cfg)
        script = builder.generate_script()
        compile(script, "<test>", "exec")
        assert "kohakuterrarium" not in script
