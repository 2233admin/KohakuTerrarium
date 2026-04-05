"""Target registry: register, resolve, and list AI coding CLI backends."""

from __future__ import annotations

from kohakuterrarium.studio.targets.base import Target

TARGET_REGISTRY: dict[str, type[Target]] = {}


def register_target(cls: type[Target]) -> type[Target]:
    """Class decorator: register a Target subclass by its ``name`` attribute."""
    TARGET_REGISTRY[cls.name] = cls
    return cls


def resolve_target(name: str) -> Target:
    """Instantiate a registered target by name. Raises ValueError if unknown."""
    cls = TARGET_REGISTRY.get(name)
    if not cls:
        raise ValueError(f"Unknown target: {name!r}")
    return cls()


def list_targets() -> list[Target]:
    """Return instantiated list of all registered targets."""
    return [cls() for cls in TARGET_REGISTRY.values()]


# Import concrete targets to trigger registration.
from kohakuterrarium.studio.targets import aider as _ai  # noqa: E402, F401
from kohakuterrarium.studio.targets import claude_code as _cc  # noqa: E402, F401
from kohakuterrarium.studio.targets import codex as _cx  # noqa: E402, F401
from kohakuterrarium.studio.targets import copilot as _cp  # noqa: E402, F401
from kohakuterrarium.studio.targets import gemini as _gm  # noqa: E402, F401
from kohakuterrarium.studio.targets import openclaw as _oc  # noqa: E402, F401
