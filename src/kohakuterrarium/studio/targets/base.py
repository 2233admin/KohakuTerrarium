"""Target ABC: interface for external AI coding CLI backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kohakuterrarium.studio.config import ProfileConfig


class Target(ABC):
    """Abstract base for an AI coding CLI target (Claude Code, Copilot, etc)."""

    name: str  # registry key, e.g. "claude-code"
    display_name: str  # human label, e.g. "Claude Code"

    @abstractmethod
    def detect(self) -> Path | None:
        """Return CLI path if installed, else None."""
        ...

    @abstractmethod
    def build_command(
        self, profile: ProfileConfig, settings_path: Path | None = None
    ) -> list[str]:
        """Build CLI launch command list."""
        ...

    @abstractmethod
    def list_models(self) -> list[str]:
        """Return available model identifiers."""
        ...

    @abstractmethod
    def status(self) -> dict:
        """Return status dict (installed, version, model, etc)."""
        ...

    # -- Optional hooks with sensible defaults --

    def settings_path(self) -> Path | None:
        """Return path to the target's settings file, or None."""
        return None

    def merge_settings(
        self, base: dict[str, Any], profile: ProfileConfig
    ) -> dict[str, Any]:
        """Merge base settings with profile overrides. Default: return base as-is."""
        return base

    def session_dir(self) -> Path | None:
        """Return path to the target's session/projects directory, or None."""
        return None

    def scan_sessions(self) -> list[dict]:
        """Return list of session metadata dicts. Default: empty."""
        return []
