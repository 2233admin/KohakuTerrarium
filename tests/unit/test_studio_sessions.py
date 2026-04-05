"""Tests for kt studio session management."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from kohakuterrarium.studio.config import (
    ProfileConfig,
    SessionEntry,
    StudioConfig,
    load_studio_config,
    save_studio_config,
)
from kohakuterrarium.studio.sessions import (
    SessionManager,
    _read_session_jsonl,
    _session_to_html,
    _session_to_markdown,
)


# ── Fixtures ──


@pytest.fixture()
def tmp_config(tmp_path: Path) -> Path:
    """Create a studio.yaml with one named session already registered."""
    config_path = tmp_path / "studio.yaml"
    config = StudioConfig(
        profiles={"default": ProfileConfig()},
        sessions={
            "my-refactor": SessionEntry(
                uuid="abc12345-6789-0000-1111-222233334444",
                project_dir="proj-hash-1",
                created="2026-04-05T00:00:00+00:00",
                tags=["important"],
                notes="Refactoring session",
            ),
        },
    )
    save_studio_config(config, config_path)
    return config_path


@pytest.fixture()
def mock_claude_dir(tmp_path: Path) -> Path:
    """Create a fake ~/.claude/projects/ dir with session .jsonl files."""
    projects_dir = tmp_path / ".claude" / "projects"
    proj_dir = projects_dir / "abc123"
    proj_dir.mkdir(parents=True)

    session_file = proj_dir / "some-uuid-1234.jsonl"
    turns = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
        {"role": "user", "content": "Fix the bug"},
    ]
    session_file.write_text(
        "\n".join(json.dumps(t) for t in turns), encoding="utf-8"
    )

    # Second session file for scan tests
    session_file2 = proj_dir / "other-uuid-5678.jsonl"
    session_file2.write_text(
        json.dumps({"role": "user", "content": "test"}), encoding="utf-8"
    )

    return projects_dir


# ── SessionEntry dataclass ──


class TestSessionEntryDataclass:
    def test_fields_and_defaults(self):
        entry = SessionEntry(uuid="test-uuid")
        assert entry.uuid == "test-uuid"
        assert entry.project_dir == ""
        assert entry.created == ""
        assert entry.tags == []
        assert entry.notes == ""

    def test_full_construction(self):
        entry = SessionEntry(
            uuid="abc",
            project_dir="proj-1",
            created="2026-01-01",
            tags=["fork", "wip"],
            notes="test note",
        )
        assert entry.tags == ["fork", "wip"]
        assert entry.notes == "test note"


# ── Config roundtrip ──


class TestConfigSessionsRoundtrip:
    def test_sessions_survive_save_load(self, tmp_path: Path):
        path = tmp_path / "studio.yaml"
        original = StudioConfig(
            sessions={
                "alpha": SessionEntry(
                    uuid="uuid-a",
                    project_dir="proj-a",
                    created="2026-01-01",
                    tags=["tag1"],
                    notes="note A",
                ),
                "beta": SessionEntry(uuid="uuid-b"),
            },
        )
        save_studio_config(original, path)
        loaded = load_studio_config(path)

        assert "alpha" in loaded.sessions
        assert loaded.sessions["alpha"].uuid == "uuid-a"
        assert loaded.sessions["alpha"].project_dir == "proj-a"
        assert loaded.sessions["alpha"].tags == ["tag1"]
        assert loaded.sessions["alpha"].notes == "note A"
        assert loaded.sessions["beta"].uuid == "uuid-b"
        assert loaded.sessions["beta"].tags == []

    def test_empty_sessions_roundtrip(self, tmp_path: Path):
        path = tmp_path / "studio.yaml"
        original = StudioConfig(sessions={})
        save_studio_config(original, path)
        loaded = load_studio_config(path)
        assert loaded.sessions == {}


# ── SessionManager CRUD ──


class TestNameSession:
    def test_name_session_basic(self, tmp_config: Path):
        manager = SessionManager(config_path=tmp_config)
        entry = manager.name_session("deadbeef-uuid", "new-session")
        assert entry.uuid == "deadbeef-uuid"
        assert entry.created != ""

        # Verify persisted
        config = load_studio_config(tmp_config)
        assert "new-session" in config.sessions
        assert config.sessions["new-session"].uuid == "deadbeef-uuid"

    def test_name_session_duplicate_raises(self, tmp_config: Path):
        manager = SessionManager(config_path=tmp_config)
        with pytest.raises(ValueError, match="already exists"):
            manager.name_session("some-uuid", "my-refactor")

    def test_name_session_latest(self, tmp_config: Path, mock_claude_dir: Path):
        manager = SessionManager(config_path=tmp_config)
        with patch(
            "kohakuterrarium.studio.sessions._find_claude_projects_dir",
            return_value=mock_claude_dir,
        ):
            entry = manager.name_session("latest", "latest-session")
        assert entry.uuid != ""
        assert entry.uuid != "latest"


class TestResolveName:
    def test_resolve_existing(self, tmp_config: Path):
        manager = SessionManager(config_path=tmp_config)
        uuid = manager.resolve_name("my-refactor")
        assert uuid == "abc12345-6789-0000-1111-222233334444"

    def test_resolve_not_found_raises(self, tmp_config: Path):
        manager = SessionManager(config_path=tmp_config)
        with pytest.raises(KeyError, match="not found"):
            manager.resolve_name("nonexistent")


class TestListSessions:
    def test_list_sessions_empty(self, tmp_path: Path):
        path = tmp_path / "studio.yaml"
        save_studio_config(StudioConfig(), path)
        manager = SessionManager(config_path=path)
        assert manager.list_sessions() == []

    def test_list_sessions_returns_sorted(self, tmp_config: Path):
        manager = SessionManager(config_path=tmp_config)
        # Add another session
        manager.name_session("aaa-uuid", "aaa-session")
        entries = manager.list_sessions()
        names = [n for n, _ in entries]
        assert names == sorted(names)

    def test_list_sessions_with_tags(self, tmp_config: Path):
        manager = SessionManager(config_path=tmp_config)
        manager.name_session("tag-uuid", "tagged-session")
        # my-refactor has tags=["important"], tagged-session has no tags
        entries = manager.list_sessions(tags=["important"])
        names = [n for n, _ in entries]
        assert "my-refactor" in names
        assert "tagged-session" not in names


class TestDeleteSession:
    def test_delete_existing(self, tmp_config: Path):
        manager = SessionManager(config_path=tmp_config)
        manager.delete_session("my-refactor")
        config = load_studio_config(tmp_config)
        assert "my-refactor" not in config.sessions

    def test_delete_nonexistent_raises(self, tmp_config: Path):
        manager = SessionManager(config_path=tmp_config)
        with pytest.raises(KeyError, match="not found"):
            manager.delete_session("nonexistent")


class TestInspectSession:
    def test_inspect_returns_metadata(self, tmp_config: Path):
        manager = SessionManager(config_path=tmp_config)
        with patch(
            "kohakuterrarium.studio.sessions._find_claude_projects_dir",
            return_value=Path("/nonexistent"),
        ):
            info = manager.inspect_session("my-refactor")
        assert info["uuid"] == "abc12345-6789-0000-1111-222233334444"
        assert info["name"] == "my-refactor"
        assert info["tags"] == ["important"]
        assert info["notes"] == "Refactoring session"
        assert "turn_count" in info

    def test_inspect_not_found_raises(self, tmp_config: Path):
        manager = SessionManager(config_path=tmp_config)
        with pytest.raises(KeyError, match="not found"):
            manager.inspect_session("nonexistent")


# ── Export ──


class TestExportSession:
    def test_export_markdown(self, tmp_config: Path, mock_claude_dir: Path):
        # Point my-refactor to a real file
        config = load_studio_config(tmp_config)
        config.sessions["my-refactor"].uuid = "some-uuid-1234"
        config.sessions["my-refactor"].project_dir = "abc123"
        save_studio_config(config, tmp_config)

        manager = SessionManager(config_path=tmp_config)
        with patch(
            "kohakuterrarium.studio.sessions._find_claude_projects_dir",
            return_value=mock_claude_dir,
        ):
            output = manager.export_session("my-refactor", fmt="md")

        assert "# Session:" in output
        assert "Hello" in output

    def test_export_html(self, tmp_config: Path, mock_claude_dir: Path):
        config = load_studio_config(tmp_config)
        config.sessions["my-refactor"].uuid = "some-uuid-1234"
        config.sessions["my-refactor"].project_dir = "abc123"
        save_studio_config(config, tmp_config)

        manager = SessionManager(config_path=tmp_config)
        with patch(
            "kohakuterrarium.studio.sessions._find_claude_projects_dir",
            return_value=mock_claude_dir,
        ):
            output = manager.export_session("my-refactor", fmt="html")

        assert "<html>" in output
        assert "Hello" in output


# ── Scan ──


class TestScanClaudeSessions:
    def test_scan_returns_metadata(self, mock_claude_dir: Path):
        manager = SessionManager()
        with patch(
            "kohakuterrarium.studio.sessions._find_claude_projects_dir",
            return_value=mock_claude_dir,
        ):
            results = manager.scan_claude_sessions()

        assert len(results) == 2
        uuids = {r["uuid"] for r in results}
        assert "some-uuid-1234" in uuids
        assert "other-uuid-5678" in uuids
        # Check keys
        for r in results:
            assert "modified" in r
            assert "size_bytes" in r
            assert "project_dir" in r

    def test_scan_nonexistent_dir(self):
        manager = SessionManager()
        with patch(
            "kohakuterrarium.studio.sessions._find_claude_projects_dir",
            return_value=Path("/nonexistent/path"),
        ):
            results = manager.scan_claude_sessions()
        assert results == []

    def test_scan_with_project_filter(self, mock_claude_dir: Path):
        manager = SessionManager()
        with patch(
            "kohakuterrarium.studio.sessions._find_claude_projects_dir",
            return_value=mock_claude_dir,
        ):
            results = manager.scan_claude_sessions(project_dir="abc123")
        assert len(results) == 2

        with patch(
            "kohakuterrarium.studio.sessions._find_claude_projects_dir",
            return_value=mock_claude_dir,
        ):
            results = manager.scan_claude_sessions(project_dir="nonexistent")
        assert len(results) == 0


# ── Fork ──


class TestForkSession:
    def test_fork_generates_name(self, tmp_config: Path):
        manager = SessionManager(config_path=tmp_config)
        with patch("kohakuterrarium.studio.sessions.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            manager.fork_session("my-refactor")

        config = load_studio_config(tmp_config)
        assert "my-refactor-fork-1" in config.sessions
        fork_entry = config.sessions["my-refactor-fork-1"]
        assert "fork" in fork_entry.tags
        assert "Forked from" in fork_entry.notes

    def test_fork_increments_counter(self, tmp_config: Path):
        manager = SessionManager(config_path=tmp_config)
        with patch("kohakuterrarium.studio.sessions.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            manager.fork_session("my-refactor")
            manager.fork_session("my-refactor")

        config = load_studio_config(tmp_config)
        assert "my-refactor-fork-1" in config.sessions
        assert "my-refactor-fork-2" in config.sessions


# ── JSONL helpers ──


class TestReadSessionJsonl:
    def test_missing_file(self, tmp_path: Path):
        result = _read_session_jsonl(tmp_path / "nonexistent.jsonl")
        assert result == []

    def test_corrupt_lines(self, tmp_path: Path):
        bad_file = tmp_path / "bad.jsonl"
        bad_file.write_text(
            '{"role": "user"}\nNOT JSON\n{"role": "assistant"}\n',
            encoding="utf-8",
        )
        result = _read_session_jsonl(bad_file)
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"

    def test_respects_limit(self, tmp_path: Path):
        f = tmp_path / "long.jsonl"
        lines = [json.dumps({"i": i}) for i in range(100)]
        f.write_text("\n".join(lines), encoding="utf-8")
        result = _read_session_jsonl(f, limit=5)
        assert len(result) == 5

    def test_empty_lines_skipped(self, tmp_path: Path):
        f = tmp_path / "gaps.jsonl"
        f.write_text('{"a":1}\n\n\n{"b":2}\n', encoding="utf-8")
        result = _read_session_jsonl(f)
        assert len(result) == 2


# ── Markdown/HTML rendering ──


class TestRendering:
    def test_markdown_basic(self):
        turns = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        md = _session_to_markdown(turns, "test-session")
        assert "# Session: test-session" in md
        assert "### User" in md
        assert "### Assistant" in md
        assert "hello" in md
        assert "hi" in md

    def test_markdown_tool_use(self):
        turns = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Let me check"},
                    {"type": "tool_use", "name": "bash", "input": {"cmd": "ls"}},
                ],
            },
        ]
        md = _session_to_markdown(turns, "tool-test")
        assert "**Tool: bash**" in md
        assert "Let me check" in md

    def test_html_basic(self):
        turns = [{"role": "user", "content": "hello"}]
        html = _session_to_html(turns, "test")
        assert "<html>" in html
        assert "hello" in html
        assert "User" in html


# ── Resume/Incognito (subprocess mocked) ──


class TestResumeAndIncognito:
    def test_resume_calls_subprocess(self, tmp_config: Path):
        manager = SessionManager(config_path=tmp_config)
        with patch("kohakuterrarium.studio.sessions.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            code = manager.resume_session("my-refactor")

        assert code == 0
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "claude" in cmd
        assert "--resume" in cmd

    def test_incognito_calls_subprocess(self, tmp_config: Path):
        manager = SessionManager(config_path=tmp_config)
        with patch("kohakuterrarium.studio.sessions.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            code = manager.launch_incognito()

        assert code == 0
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "claude" in cmd
        assert "--resume" not in cmd
