"""Session management for kt studio -- named sessions, resume, fork, export."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from kohakuterrarium.studio.config import (
    SessionEntry,
    StudioConfig,
    load_studio_config,
    save_studio_config,
)
from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)


def _find_claude_projects_dir() -> Path:
    """Return the path to Claude Code's projects directory."""
    return Path.home() / ".claude" / "projects"


def _scan_project_sessions(project_path: Path) -> list[dict]:
    """List .jsonl files in a project directory, return metadata dicts."""
    results: list[dict] = []
    if not project_path.is_dir():
        return results

    for jsonl_file in project_path.glob("*.jsonl"):
        stat = jsonl_file.stat()
        results.append({
            "uuid": jsonl_file.stem,
            "project_dir": project_path.name,
            "modified": datetime.fromtimestamp(
                stat.st_mtime, tz=timezone.utc
            ).isoformat(),
            "size_bytes": stat.st_size,
        })
    return results


def _read_session_jsonl(session_path: Path, limit: int = 50) -> list[dict]:
    """Read up to limit lines from a .jsonl file, parsing each as JSON.

    Returns empty list for missing or corrupt files.
    """
    if not session_path.exists():
        return []

    turns: list[dict] = []
    try:
        with open(session_path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= limit:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    turns.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.debug("Skipping corrupt JSON line %d in %s", i, session_path)
    except OSError as e:
        logger.warning("Failed to read session file %s: %s", session_path, e)
    return turns


def _session_to_markdown(turns: list[dict], name: str) -> str:
    """Render session turns as markdown."""
    lines: list[str] = [f"# Session: {name}", ""]

    for turn in turns:
        role = turn.get("role", "unknown")
        lines.append(f"### {role.capitalize()}")
        lines.append("")

        content = turn.get("content", "")
        match content:
            case str():
                lines.append(content)
            case list():
                for block in content:
                    if isinstance(block, dict):
                        block_type = block.get("type", "")
                        match block_type:
                            case "text":
                                lines.append(block.get("text", ""))
                            case "tool_use":
                                tool_name = block.get("name", "unknown")
                                tool_input = json.dumps(
                                    block.get("input", {}), indent=2
                                )
                                lines.append(f"**Tool: {tool_name}**")
                                lines.append(f"```json\n{tool_input}\n```")
                            case "tool_result":
                                lines.append(f"**Result:** {block.get('content', '')}")
                            case _:
                                lines.append(str(block))
                    else:
                        lines.append(str(block))
            case _:
                lines.append(str(content))

        lines.append("")

    return "\n".join(lines)


def _session_to_html(turns: list[dict], name: str) -> str:
    """Render session turns as a basic HTML document."""
    style = (
        "body{font-family:sans-serif;max-width:800px;margin:0 auto;padding:20px}"
        ".turn{margin:10px 0;padding:10px;border-radius:5px}"
        ".user{background:#e3f2fd}.assistant{background:#f5f5f5}"
        ".tool{background:#fff3e0;font-family:monospace;font-size:0.9em}"
        "h1{border-bottom:2px solid #333}"
    )

    parts: list[str] = [
        "<html><head>",
        f"<title>Session: {name}</title>",
        f"<style>{style}</style>",
        "</head><body>",
        f"<h1>Session: {name}</h1>",
    ]

    for turn in turns:
        role = turn.get("role", "unknown")
        css_class = role if role in ("user", "assistant") else "tool"
        content = turn.get("content", "")

        text = ""
        match content:
            case str():
                text = content
            case list():
                fragments: list[str] = []
                for block in content:
                    if isinstance(block, dict):
                        fragments.append(block.get("text", str(block)))
                    else:
                        fragments.append(str(block))
                text = "<br>".join(fragments)
            case _:
                text = str(content)

        parts.append(
            f'<div class="turn {css_class}">'
            f"<strong>{role.capitalize()}</strong><br>{text}</div>"
        )

    parts.append("</body></html>")
    return "\n".join(parts)


def scan_all_sessions() -> list[dict]:
    """Aggregate sessions from all installed targets.

    Scans each target that is detected as installed, collects sessions,
    tags each with the target name, and returns sorted by modified desc.
    """
    from kohakuterrarium.studio.targets import list_targets

    all_sessions: list[dict] = []
    for target in list_targets():
        if target.detect() is None:
            continue
        try:
            sessions = target.scan_sessions()
            for s in sessions:
                s.setdefault("target", target.name)
            all_sessions.extend(sessions)
        except Exception:
            logger.debug("Failed to scan sessions for %s", target.name)

    all_sessions.sort(key=lambda s: s.get("modified", ""), reverse=True)
    return all_sessions


class SessionManager:
    """Manages named Claude Code sessions -- CRUD, resume, fork, export."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_path = config_path

    def _load(self) -> StudioConfig:
        return load_studio_config(self._config_path)

    def _save(self, config: StudioConfig) -> None:
        save_studio_config(config, self._config_path)

    def scan_claude_sessions(self, project_dir: str | None = None) -> list[dict]:
        """Scan ~/.claude/projects/ for session .jsonl files.

        Returns list of dicts: uuid, project_dir, modified, size_bytes.
        Sorted by modified descending.
        """
        base = _find_claude_projects_dir()
        if not base.is_dir():
            logger.debug("Claude projects dir not found: %s", base)
            return []

        all_sessions: list[dict] = []
        if project_dir:
            target = base / project_dir
            all_sessions.extend(_scan_project_sessions(target))
        else:
            for child in base.iterdir():
                if child.is_dir():
                    all_sessions.extend(_scan_project_sessions(child))

        all_sessions.sort(key=lambda s: s["modified"], reverse=True)
        return all_sessions

    def name_session(self, identifier: str, name: str) -> SessionEntry:
        """Name a session by UUID or 'latest'.

        Raises ValueError if name already exists.
        """
        config = self._load()
        if name in config.sessions:
            raise ValueError(f"Session name '{name}' already exists")

        uuid = identifier
        project_dir = ""
        if identifier == "latest":
            scanned = self.scan_claude_sessions()
            if not scanned:
                raise ValueError("No Claude sessions found to name")
            uuid = scanned[0]["uuid"]
            project_dir = scanned[0].get("project_dir", "")
        else:
            # Try to detect project_dir from scan
            scanned = self.scan_claude_sessions()
            for s in scanned:
                if s["uuid"] == identifier:
                    project_dir = s.get("project_dir", "")
                    break

        now = datetime.now(tz=timezone.utc).isoformat()
        entry = SessionEntry(uuid=uuid, created=now, project_dir=project_dir)
        config.sessions[name] = entry
        self._save(config)
        logger.info("Named session '%s' -> %s", name, uuid)
        return entry

    def resolve_name(self, name: str) -> str:
        """Return UUID for a named session. Raises KeyError if not found."""
        config = self._load()
        entry = config.sessions.get(name)
        if entry is None:
            raise KeyError(f"Session '{name}' not found")
        return entry.uuid

    def list_sessions(
        self, tags: list[str] | None = None
    ) -> list[tuple[str, SessionEntry]]:
        """List named sessions, sorted by name.

        If tags provided, filter to entries where all tags are present.
        """
        config = self._load()
        entries = sorted(config.sessions.items(), key=lambda x: x[0])

        if tags:
            entries = [
                (n, e) for n, e in entries if all(t in e.tags for t in tags)
            ]

        return entries

    def resume_session(self, name: str, profile: str | None = None) -> int:
        """Resume a named session via claude --resume.

        Returns subprocess exit code.
        """
        uuid = self.resolve_name(name)
        cmd = ["claude", "--resume", uuid]

        env = self._build_profile_env(profile)
        logger.info("Resuming session '%s' (uuid=%s)", name, uuid)
        result = subprocess.run(cmd, env=env, check=False)
        return result.returncode

    def fork_session(self, name: str, new_name: str | None = None) -> int:
        """Fork a named session. Registers the fork and launches claude --continue.

        Returns subprocess exit code.
        """
        uuid = self.resolve_name(name)

        if new_name is None:
            config = self._load()
            counter = 1
            while f"{name}-fork-{counter}" in config.sessions:
                counter += 1
            new_name = f"{name}-fork-{counter}"

        # Register the fork before launching
        config = self._load()
        now = datetime.now(tz=timezone.utc).isoformat()
        original = config.sessions.get(name)
        project_dir = original.project_dir if original else ""
        config.sessions[new_name] = SessionEntry(
            uuid=uuid,
            created=now,
            project_dir=project_dir,
            tags=["fork"],
            notes=f"Forked from '{name}'",
        )
        self._save(config)

        cmd = ["claude", "--resume", uuid, "--continue"]
        logger.info("Forking session '%s' as '%s' (uuid=%s)", name, new_name, uuid)
        result = subprocess.run(cmd, check=False)
        return result.returncode

    def inspect_session(self, name: str) -> dict:
        """Inspect a named session -- returns metadata dict."""
        config = self._load()
        entry = config.sessions.get(name)
        if entry is None:
            raise KeyError(f"Session '{name}' not found")

        info: dict = {
            "name": name,
            "uuid": entry.uuid,
            "project_dir": entry.project_dir,
            "created": entry.created,
            "tags": entry.tags,
            "notes": entry.notes,
        }

        # Try to find live data from the session file
        session_path = self._find_session_file(entry.uuid, entry.project_dir)
        if session_path and session_path.exists():
            stat = session_path.stat()
            info["size_bytes"] = stat.st_size
            info["modified"] = datetime.fromtimestamp(
                stat.st_mtime, tz=timezone.utc
            ).isoformat()
            turns = _read_session_jsonl(session_path, limit=1000)
            info["turn_count"] = len(turns)
        else:
            info["size_bytes"] = 0
            info["modified"] = ""
            info["turn_count"] = 0

        return info

    def delete_session(self, name: str) -> None:
        """Remove a named session from the registry. Does NOT delete session files."""
        config = self._load()
        if name not in config.sessions:
            raise KeyError(f"Session '{name}' not found")

        del config.sessions[name]
        self._save(config)
        logger.info("Deleted session name '%s'", name)

    def export_session(self, name: str, fmt: str = "md") -> str:
        """Export a session as markdown or HTML string."""
        config = self._load()
        entry = config.sessions.get(name)
        if entry is None:
            raise KeyError(f"Session '{name}' not found")

        session_path = self._find_session_file(entry.uuid, entry.project_dir)
        if session_path is None or not session_path.exists():
            raise FileNotFoundError(
                f"Session file not found for '{name}' (uuid={entry.uuid})"
            )

        turns = _read_session_jsonl(session_path)

        match fmt:
            case "html":
                return _session_to_html(turns, name)
            case _:
                return _session_to_markdown(turns, name)

    def launch_incognito(self, profile: str | None = None) -> int:
        """Launch an ephemeral claude session (no resume flag)."""
        cmd = ["claude"]
        env = self._build_profile_env(profile)
        logger.info("Launching incognito session")
        result = subprocess.run(cmd, env=env, check=False)
        return result.returncode

    # ── Private helpers ──

    def _find_session_file(
        self, uuid: str, project_dir: str = ""
    ) -> Path | None:
        """Locate a session .jsonl file by UUID."""
        base = _find_claude_projects_dir()
        if not base.is_dir():
            return None

        if project_dir:
            candidate = base / project_dir / f"{uuid}.jsonl"
            if candidate.exists():
                return candidate

        # Search all project dirs
        for child in base.iterdir():
            if child.is_dir():
                candidate = child / f"{uuid}.jsonl"
                if candidate.exists():
                    return candidate
        return None

    def _build_profile_env(self, profile_name: str | None) -> dict[str, str] | None:
        """Build environment variables dict from a profile. Returns None if no profile."""
        if not profile_name:
            return None

        config = self._load()
        profile = config.profiles.get(profile_name)
        if profile is None:
            logger.warning("Profile '%s' not found, using default env", profile_name)
            return None

        if not profile.env:
            return None

        import os

        env = dict(os.environ)
        env.update(profile.env)
        return env
