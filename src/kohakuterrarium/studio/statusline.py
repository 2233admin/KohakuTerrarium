"""StatusLineBuilder, segment registry, and style rendering for kt studio."""

import json
import os
import subprocess
import textwrap
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from kohakuterrarium.studio.config import KT_DIR, StatuslineConfig
from kohakuterrarium.studio.themes import get_theme
from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)

CLAUDE_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"


# -- Segment functions --


def _segment_git() -> str:
    """Return current branch + short diff stat, or 'no-git'."""
    try:
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if branch_result.returncode != 0:
            return "no-git"

        branch = branch_result.stdout.strip()

        diff_result = subprocess.run(
            ["git", "diff", "--shortstat"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        stat = diff_result.stdout.strip()
        if stat:
            # Extract +N -M from shortstat
            parts: list[str] = []
            for token in stat.split(","):
                token = token.strip()
                if "insertion" in token:
                    num = token.split()[0]
                    parts.append(f"+{num}")
                elif "deletion" in token:
                    num = token.split()[0]
                    parts.append(f"-{num}")
            if parts:
                return f"{branch} {''.join(parts)}"

        return branch
    except (OSError, subprocess.TimeoutExpired):
        return "no-git"


def _segment_tokens() -> str:
    """Read CLAUDE_TOKEN_COUNT from env."""
    return os.environ.get("CLAUDE_TOKEN_COUNT", "")


def _segment_cost() -> str:
    """Estimate cost from token count."""
    token_str = os.environ.get("CLAUDE_TOKEN_COUNT", "")
    if not token_str:
        return ""
    try:
        tokens = int(token_str)
        cost = tokens * 0.000003
        return f"${cost:.2f}"
    except ValueError:
        return ""


def _segment_model() -> str:
    """Read CLAUDE_MODEL from env."""
    return os.environ.get("CLAUDE_MODEL", "")


def _segment_session() -> str:
    """Read CLAUDE_SESSION_ID, return first 8 chars."""
    session_id = os.environ.get("CLAUDE_SESSION_ID", "")
    if session_id:
        return session_id[:8]
    return ""


def _segment_clock() -> str:
    """Return current time as HH:MM."""
    return datetime.now().strftime("%H:%M")


SEGMENT_REGISTRY: dict[str, Callable[[], str]] = {
    "git": _segment_git,
    "tokens": _segment_tokens,
    "cost": _segment_cost,
    "model": _segment_model,
    "session": _segment_session,
    "clock": _segment_clock,
}


def render_segments(segments: list[str], style: str) -> str:
    """Render segment values using the given style.

    Filters out empty segments before joining.
    """
    filtered = [s for s in segments if s]

    match style:
        case "powerline":
            return f" \ue0b0 ".join(filtered)
        case "capsule":
            return " ".join(f"[{s}]" for s in filtered)
        case _:
            # minimal (default)
            return " | ".join(filtered)


# -- Script generation templates --

_SEGMENT_TEMPLATES: dict[str, str] = {
    "git": textwrap.dedent("""\
        def _seg_git():
            try:
                r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                                   capture_output=True, text=True, timeout=5)
                if r.returncode != 0:
                    return "no-git"
                branch = r.stdout.strip()
                d = subprocess.run(["git", "diff", "--shortstat"],
                                   capture_output=True, text=True, timeout=5)
                stat = d.stdout.strip()
                if stat:
                    parts = []
                    for tok in stat.split(","):
                        tok = tok.strip()
                        if "insertion" in tok:
                            parts.append("+" + tok.split()[0])
                        elif "deletion" in tok:
                            parts.append("-" + tok.split()[0])
                    if parts:
                        return branch + " " + "".join(parts)
                return branch
            except Exception:
                return "no-git"
        """),
    "tokens": textwrap.dedent("""\
        def _seg_tokens():
            return os.environ.get("CLAUDE_TOKEN_COUNT", "")
        """),
    "cost": textwrap.dedent("""\
        def _seg_cost():
            t = os.environ.get("CLAUDE_TOKEN_COUNT", "")
            if not t:
                return ""
            try:
                return "$" + f"{int(t) * 0.000003:.2f}"
            except ValueError:
                return ""
        """),
    "model": textwrap.dedent("""\
        def _seg_model():
            return os.environ.get("CLAUDE_MODEL", "")
        """),
    "session": textwrap.dedent("""\
        def _seg_session():
            s = os.environ.get("CLAUDE_SESSION_ID", "")
            return s[:8] if s else ""
        """),
    "clock": textwrap.dedent("""\
        def _seg_clock():
            return datetime.now().strftime("%H:%M")
        """),
}

_RENDER_TEMPLATES: dict[str, str] = {
    "minimal": 'return " | ".join(filtered)',
    "powerline": 'return " \\ue0b0 ".join(filtered)',
    "capsule": 'return " ".join("[" + s + "]" for s in filtered)',
}


class StatusLineBuilder:
    """Builds standalone statusline runner scripts and manages installation."""

    def __init__(
        self, config: StatuslineConfig, theme_name: str | None = None
    ) -> None:
        self.config = config
        self.theme_name = theme_name

    def generate_script(self) -> str:
        """Generate a standalone Python script for the status line.

        The script imports only stdlib modules and has no KT dependencies.
        """
        lines: list[str] = [
            "#!/usr/bin/env python3",
            '"""Auto-generated statusline runner -- do not edit."""',
            "",
            "import os",
            "import subprocess",
            "import sys",
            "from datetime import datetime",
            "",
        ]

        # Embed theme colors if provided
        if self.theme_name:
            theme = get_theme(self.theme_name)
            if theme:
                lines.append(f"THEME = {theme!r}")
                lines.append("")

        # Segment functions
        for seg_name in self.config.segments:
            template = _SEGMENT_TEMPLATES.get(seg_name)
            if template:
                lines.append(template)

        # Render function
        style = self.config.style
        render_body = _RENDER_TEMPLATES.get(style, _RENDER_TEMPLATES["minimal"])
        lines.append("def render(segments):")
        lines.append("    filtered = [s for s in segments if s]")
        lines.append(f"    {render_body}")
        lines.append("")

        # Main block
        lines.append('if __name__ == "__main__":')
        lines.append("    segments = []")
        for seg_name in self.config.segments:
            func_name = f"_seg_{seg_name}"
            lines.append(f"    segments.append({func_name}())")
        lines.append("    print(render(segments))")
        lines.append("")

        return "\n".join(lines)

    def install(self, settings_path: Path | None = None) -> None:
        """Install the statusline runner and update Claude Code settings."""
        runner_dir = KT_DIR / "studio"
        runner_dir.mkdir(parents=True, exist_ok=True)
        runner_path = runner_dir / "statusline_runner.py"

        script = self.generate_script()
        runner_path.write_text(script, encoding="utf-8")
        logger.info("Wrote statusline runner: %s", runner_path)

        target = settings_path or CLAUDE_SETTINGS_PATH
        settings: dict = {}
        if target.exists():
            try:
                settings = json.loads(target.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to read settings: %s", e)

        settings["statusLine"] = {
            "command": f"python {runner_path}",
        }

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        logger.info("Updated settings: %s", target)

    def uninstall(self, settings_path: Path | None = None) -> None:
        """Remove statusline from settings and delete the runner script."""
        target = settings_path or CLAUDE_SETTINGS_PATH
        if target.exists():
            try:
                settings = json.loads(target.read_text(encoding="utf-8"))
                settings.pop("statusLine", None)
                target.write_text(
                    json.dumps(settings, indent=2), encoding="utf-8"
                )
                logger.info("Removed statusLine from settings: %s", target)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to update settings: %s", e)

        runner_path = KT_DIR / "studio" / "statusline_runner.py"
        if runner_path.exists():
            runner_path.unlink()
            logger.info("Deleted runner: %s", runner_path)

    def preview(self) -> str:
        """Run segments live and render with the configured style."""
        values: list[str] = []
        for seg_name in self.config.segments:
            fn = SEGMENT_REGISTRY.get(seg_name)
            if fn:
                values.append(fn())
            else:
                values.append("")
        return render_segments(values, self.config.style)
