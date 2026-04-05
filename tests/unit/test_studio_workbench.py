"""Tests for kt studio workbench tools: cost, record, compare, completion, diff."""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# -- cost.py tests --


class TestCost:
    def test_pricing_table_has_common_models(self):
        from kohakuterrarium.studio.cost import PRICING

        for model in ("claude-sonnet-4", "claude-opus-4", "gpt-4.1", "gemini-2.5-pro"):
            assert model in PRICING, f"{model} missing from PRICING"

    def test_estimate_cost_zero_tokens(self):
        from kohakuterrarium.studio.cost import estimate_cost

        assert estimate_cost("claude-sonnet-4", 0, 0) == 0.0

    def test_estimate_cost_calculation(self):
        from kohakuterrarium.studio.cost import estimate_cost

        # claude-sonnet-4: $3/M input, $15/M output
        result = estimate_cost("claude-sonnet-4", 1_000_000, 1_000_000)
        assert result == pytest.approx(18.0)

    def test_estimate_cost_unknown_model(self):
        from kohakuterrarium.studio.cost import estimate_cost

        assert estimate_cost("unknown-model", 1000, 1000) == 0.0

    def test_cost_summary_empty(self):
        from kohakuterrarium.studio.cost import cost_summary

        with patch("kohakuterrarium.studio.cost.scan_usage_logs", return_value=[]):
            result = cost_summary()
        assert result["total"] == 0.0
        assert result["entries"] == 0


# -- record.py tests --


class TestRecord:
    def test_recording_entry_to_json(self):
        from kohakuterrarium.studio.record import RecordingEntry

        entry = RecordingEntry(
            timestamp="2026-04-05T12:00:00Z", type="output", content="hello"
        )
        d = entry.to_dict()
        assert d["timestamp"] == "2026-04-05T12:00:00Z"
        assert d["type"] == "output"
        assert d["content"] == "hello"

    def test_recorder_init(self, tmp_path: Path):
        from kohakuterrarium.studio.record import SessionRecorder

        out = tmp_path / "session.jsonl"
        recorder = SessionRecorder(out, "claude-code")
        assert recorder.output_path == out
        assert recorder.target_name == "claude-code"

    def test_recorder_writes_jsonl(self, tmp_path: Path):
        from kohakuterrarium.studio.record import SessionRecorder

        out = tmp_path / "session.jsonl"
        recorder = SessionRecorder(out, "claude-code")

        async def _mock_stdout():
            for chunk in [b"line1\n", b"line2\n"]:
                yield chunk

        mock_proc = AsyncMock()
        mock_proc.stdout = _mock_stdout()
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        with patch(
            "kohakuterrarium.studio.record.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            exit_code = asyncio.run(recorder.record(["echo", "test"]))

        assert exit_code == 0
        lines = out.read_text(encoding="utf-8").strip().split("\n")
        # At minimum: meta entry at start
        assert len(lines) >= 1
        first = json.loads(lines[0])
        assert first["type"] == "meta"


# -- compare.py tests --


class TestCompare:
    def test_compare_result_dataclass(self):
        from kohakuterrarium.studio.compare import CompareResult

        r = CompareResult(
            target="claude-code", output="ok", duration_ms=150, exit_code=0
        )
        assert r.target == "claude-code"
        assert r.duration_ms == 150

    def test_compare_runner_init(self):
        from kohakuterrarium.studio.compare import CompareRunner

        runner = CompareRunner(["claude-code", "codex"])
        assert runner.targets == ["claude-code", "codex"]

    def test_format_results_table(self):
        from kohakuterrarium.studio.compare import CompareResult, CompareRunner

        runner = CompareRunner(["a", "b"])
        results = [
            CompareResult(target="a", output="hello", duration_ms=100, exit_code=0),
            CompareResult(target="b", output="world", duration_ms=200, exit_code=0),
        ]
        table = runner.format_results(results)
        assert "a" in table
        assert "b" in table
        assert "100" in table
        assert "200" in table

    def test_compare_runner_parallel(self):
        from kohakuterrarium.studio.compare import CompareRunner

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
        mock_proc.returncode = 0

        mock_target = MagicMock()
        mock_target.build_command.return_value = ["echo", "test"]

        with (
            patch(
                "kohakuterrarium.studio.compare.resolve_target",
                return_value=mock_target,
            ),
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
        ):
            runner = CompareRunner(["claude-code", "codex"])
            results = asyncio.run(runner.run("test task", timeout=10))

        assert len(results) == 2


# -- completion.py tests --


class TestCompletion:
    def test_bash_completion_has_subcommands(self):
        from kohakuterrarium.studio.completion import generate_bash_completion

        output = generate_bash_completion()
        assert "studio" in output
        assert "launch" in output
        assert "cost" in output

    def test_zsh_completion_has_subcommands(self):
        from kohakuterrarium.studio.completion import generate_zsh_completion

        output = generate_zsh_completion()
        assert "studio" in output
        assert "launch" in output

    def test_fish_completion_valid(self):
        from kohakuterrarium.studio.completion import generate_fish_completion

        output = generate_fish_completion()
        assert "complete" in output

    def test_powershell_completion_valid(self):
        from kohakuterrarium.studio.completion import generate_powershell_completion

        output = generate_powershell_completion()
        assert "Register-ArgumentCompleter" in output or "kt" in output


# -- profiles.py diff tests --


class TestDiff:
    def test_diff_profiles_identical(self, tmp_path: Path):
        from kohakuterrarium.studio.config import (
            ProfileConfig,
            StudioConfig,
            save_studio_config,
        )
        from kohakuterrarium.studio.profiles import diff_profiles

        cfg = StudioConfig(profiles={"a": ProfileConfig(), "b": ProfileConfig()})
        cp = tmp_path / "studio.yaml"
        save_studio_config(cfg, cp)
        result = diff_profiles("a", "b", config_path=cp)
        assert result == {}

    def test_diff_profiles_different_model(self, tmp_path: Path):
        from kohakuterrarium.studio.config import (
            ProfileConfig,
            StudioConfig,
            save_studio_config,
        )
        from kohakuterrarium.studio.profiles import diff_profiles

        cfg = StudioConfig(
            profiles={
                "a": ProfileConfig(model="sonnet"),
                "b": ProfileConfig(model="opus"),
            }
        )
        cp = tmp_path / "studio.yaml"
        save_studio_config(cfg, cp)
        result = diff_profiles("a", "b", config_path=cp)
        assert result == {"model": ("sonnet", "opus")}

    def test_diff_profiles_missing_profile(self, tmp_path: Path):
        from kohakuterrarium.studio.config import (
            ProfileConfig,
            StudioConfig,
            save_studio_config,
        )
        from kohakuterrarium.studio.profiles import diff_profiles

        cfg = StudioConfig(profiles={"a": ProfileConfig()})
        cp = tmp_path / "studio.yaml"
        save_studio_config(cfg, cp)
        with pytest.raises(KeyError):
            diff_profiles("a", "nonexistent", config_path=cp)
