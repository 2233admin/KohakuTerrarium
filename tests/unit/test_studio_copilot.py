"""Tests for kt studio Copilot CLI integration."""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from kohakuterrarium.studio.copilot import (
    find_copilot_cli,
    get_copilot_version,
    get_current_model,
    set_model,
    list_available_models,
    copilot_status,
    PatchDriver,
    COPILOT_MODEL_ENV,
)

# -- find / version --


class TestFindCopilotCli:
    def test_not_installed(self):
        with patch("kohakuterrarium.studio.copilot.shutil.which", return_value=None):
            assert find_copilot_cli() is None

    def test_installed(self):
        with patch(
            "kohakuterrarium.studio.copilot.shutil.which",
            return_value="/usr/bin/github-copilot-cli",
        ):
            result = find_copilot_cli()
            assert result == Path("/usr/bin/github-copilot-cli")


class TestGetCopilotVersion:
    def test_returns_version_string(self):
        mock_result = MagicMock()
        mock_result.stdout = "1.2.3\n"
        mock_result.returncode = 0
        with (
            patch(
                "kohakuterrarium.studio.copilot.find_copilot_cli",
                return_value=Path("/usr/bin/github-copilot-cli"),
            ),
            patch(
                "kohakuterrarium.studio.copilot.subprocess.run",
                return_value=mock_result,
            ),
        ):
            assert get_copilot_version() == "1.2.3"

    def test_returns_none_when_not_installed(self):
        with patch(
            "kohakuterrarium.studio.copilot.find_copilot_cli", return_value=None
        ):
            assert get_copilot_version() is None


# -- model listing --


class TestListAvailableModels:
    def test_returns_non_empty_list(self):
        models = list_available_models()
        assert len(models) > 0

    def test_contains_expected_models(self):
        models = list_available_models()
        for expected in ("gpt-4o", "claude-sonnet-4", "gemini-2.5-pro"):
            assert expected in models

    def test_returns_copy(self):
        a = list_available_models()
        b = list_available_models()
        assert a is not b


# -- set / get model --


class TestSetModel:
    def test_writes_config(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        set_model("gpt-4o", config_path=config_path)
        data = json.loads(config_path.read_text(encoding="utf-8"))
        assert data["model"] == "gpt-4o"

    def test_creates_parent_dirs(self, tmp_path: Path):
        config_path = tmp_path / "deep" / "nested" / "config.json"
        set_model("o3-mini", config_path=config_path)
        assert config_path.exists()

    def test_preserves_existing_keys(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"locale": "en", "model": "old"}))
        set_model("gpt-4o", config_path=config_path)
        data = json.loads(config_path.read_text(encoding="utf-8"))
        assert data["model"] == "gpt-4o"
        assert data["locale"] == "en"


class TestGetCurrentModel:
    def test_from_env(self, monkeypatch):
        monkeypatch.setenv(COPILOT_MODEL_ENV, "o3-mini")
        assert get_current_model() == "o3-mini"

    def test_from_config(self, tmp_path: Path, monkeypatch):
        monkeypatch.delenv(COPILOT_MODEL_ENV, raising=False)
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"model": "gpt-4.1"}))
        assert get_current_model(config_path=config_path) == "gpt-4.1"

    def test_env_priority_over_config(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv(COPILOT_MODEL_ENV, "o3-mini")
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"model": "gpt-4.1"}))
        assert get_current_model(config_path=config_path) == "o3-mini"

    def test_returns_none_when_nothing_set(self, tmp_path: Path, monkeypatch):
        monkeypatch.delenv(COPILOT_MODEL_ENV, raising=False)
        config_path = tmp_path / "nonexistent.json"
        assert get_current_model(config_path=config_path) is None


# -- copilot_status --


class TestCopilotStatus:
    def test_not_installed(self):
        with (
            patch("kohakuterrarium.studio.copilot.find_copilot_cli", return_value=None),
            patch(
                "kohakuterrarium.studio.copilot.get_copilot_version", return_value=None
            ),
            patch(
                "kohakuterrarium.studio.copilot.get_current_model", return_value=None
            ),
        ):
            info = copilot_status()
            assert info["installed"] is False
            assert info["version"] is None

    def test_installed(self):
        with (
            patch(
                "kohakuterrarium.studio.copilot.find_copilot_cli",
                return_value=Path("/usr/bin/github-copilot-cli"),
            ),
            patch(
                "kohakuterrarium.studio.copilot.get_copilot_version",
                return_value="1.2.3",
            ),
            patch(
                "kohakuterrarium.studio.copilot.get_current_model",
                return_value="gpt-4o",
            ),
        ):
            info = copilot_status()
            assert info["installed"] is True
            assert info["version"] == "1.2.3"
            assert info["model"] == "gpt-4o"


# -- PatchDriver --


class TestPatchDriver:
    def test_no_node(self):
        driver = PatchDriver()
        with patch("kohakuterrarium.studio.copilot.shutil.which", return_value=None):
            result = driver.apply_patch()
            assert result is False

    def test_graceful_failure(self):
        driver = PatchDriver()
        with (
            patch(
                "kohakuterrarium.studio.copilot.shutil.which",
                return_value="/usr/bin/node",
            ),
            patch(
                "kohakuterrarium.studio.copilot.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "node"),
            ),
            patch.object(
                driver, "detect_install", return_value=Path("/fake/bundle.js")
            ),
        ):
            result = driver.apply_patch()
            assert result is False

    def test_is_patched_false_by_default(self, tmp_path: Path):
        driver = PatchDriver()
        with patch.object(
            driver, "detect_install", return_value=tmp_path / "bundle.js"
        ):
            assert driver.is_patched() is False

    def test_is_patched_true_when_backup_exists(self, tmp_path: Path):
        bundle = tmp_path / "bundle.js"
        backup = tmp_path / "bundle.js.bak"
        bundle.write_text("original")
        backup.write_text("backup")
        driver = PatchDriver()
        with patch.object(driver, "detect_install", return_value=bundle):
            assert driver.is_patched() is True

    def test_unpatch_restores_backup(self, tmp_path: Path):
        bundle = tmp_path / "bundle.js"
        backup = tmp_path / "bundle.js.bak"
        bundle.write_text("patched content")
        backup.write_text("original content")
        driver = PatchDriver()
        with patch.object(driver, "detect_install", return_value=bundle):
            result = driver.unpatch()
        assert result is True
        assert bundle.read_text() == "original content"
        assert not backup.exists()
