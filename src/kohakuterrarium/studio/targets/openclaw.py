"""OpenClawTarget: OpenClaw gateway backend for kt studio."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import httpx

from kohakuterrarium.studio.targets import register_target
from kohakuterrarium.studio.targets.base import Target
from kohakuterrarium.utils.logging import get_logger

if TYPE_CHECKING:
    from kohakuterrarium.studio.config import ProfileConfig

logger = get_logger(__name__)

DEFAULT_ENDPOINT = "http://localhost:3456"


@register_target
class OpenClawTarget(Target):
    """Target implementation for the OpenClaw API gateway."""

    name = "openclaw"
    display_name = "OpenClaw"

    def __init__(self, endpoint: str | None = None) -> None:
        self._endpoint = endpoint or DEFAULT_ENDPOINT

    def detect(self) -> Path | None:
        """Return Path('openclaw') if endpoint is reachable, else None."""
        try:
            resp = httpx.get(f"{self._endpoint}/v1/models", timeout=2.0)
            if resp.status_code == 200:
                return Path("openclaw")
        except Exception:
            pass
        return None

    def build_command(
        self, profile: ProfileConfig, settings_path: Path | None = None
    ) -> list[str]:
        """OpenClaw is a server, not a CLI."""
        raise NotImplementedError(
            "OpenClaw is a server, not a CLI. "
            "Use the dashboard or API directly."
        )

    def list_models(self) -> list[str]:
        """Fetch model list from /v1/models endpoint."""
        try:
            resp = httpx.get(f"{self._endpoint}/v1/models", timeout=2.0)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                return [m["id"] for m in data if "id" in m]
        except Exception:
            logger.debug("Failed to fetch models from %s", self._endpoint)
        return []

    def status(self) -> dict:
        """Return OpenClaw endpoint status."""
        reachable = self.detect() is not None
        model_count = 0
        if reachable:
            model_count = len(self.list_models())
        return {
            "installed": reachable,
            "endpoint": self._endpoint,
            "model_count": model_count,
        }

    def settings_path(self) -> Path | None:
        """OpenClaw has no local settings file."""
        return None

    def session_dir(self) -> Path | None:
        """OpenClaw has no local session directory."""
        return None
