"""Theme registry and utilities for kt studio."""

from dataclasses import dataclass

from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ThemeColors:
    """Color palette for a studio theme."""

    primary: str
    secondary: str
    accent: str
    background: str
    surface: str
    text: str
    dimmed: str
    success: str
    warning: str
    error: str


BUILTIN_THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "primary": "#0f3460",
        "secondary": "#16213e",
        "accent": "#0f3460",
        "background": "#1a1a2e",
        "surface": "#16213e",
        "text": "#e0e0e0",
        "dimmed": "#888888",
        "success": "#4caf50",
        "warning": "#ff9800",
        "error": "#f44336",
    },
    "light": {
        "primary": "#1976d2",
        "secondary": "#e3f2fd",
        "accent": "#1976d2",
        "background": "#fafafa",
        "surface": "#ffffff",
        "text": "#212121",
        "dimmed": "#9e9e9e",
        "success": "#388e3c",
        "warning": "#f57c00",
        "error": "#d32f2f",
    },
    "nord": {
        "primary": "#5e81ac",
        "secondary": "#81a1c1",
        "accent": "#88c0d0",
        "background": "#2e3440",
        "surface": "#3b4252",
        "text": "#eceff4",
        "dimmed": "#4c566a",
        "success": "#a3be8c",
        "warning": "#ebcb8b",
        "error": "#bf616a",
    },
    "tokyo-night": {
        "primary": "#7aa2f7",
        "secondary": "#bb9af7",
        "accent": "#7aa2f7",
        "background": "#1a1b26",
        "surface": "#24283b",
        "text": "#c0caf5",
        "dimmed": "#565f89",
        "success": "#9ece6a",
        "warning": "#e0af68",
        "error": "#f7768e",
    },
    "rose-pine": {
        "primary": "#c4a7e7",
        "secondary": "#f6c177",
        "accent": "#ebbcba",
        "background": "#191724",
        "surface": "#1f1d2e",
        "text": "#e0def4",
        "dimmed": "#6e6a86",
        "success": "#31748f",
        "warning": "#f6c177",
        "error": "#eb6f92",
    },
    "gruvbox": {
        "primary": "#d79921",
        "secondary": "#458588",
        "accent": "#fe8019",
        "background": "#282828",
        "surface": "#3c3836",
        "text": "#ebdbb2",
        "dimmed": "#928374",
        "success": "#b8bb26",
        "warning": "#fabd2f",
        "error": "#fb4934",
    },
}


def list_themes() -> list[str]:
    """Return sorted list of built-in theme names."""
    return sorted(BUILTIN_THEMES.keys())


def get_theme(name: str) -> dict[str, str] | None:
    """Look up a theme by name. Returns None if not found."""
    return BUILTIN_THEMES.get(name)


def preview_theme(name: str) -> str:
    """Generate a Rich-markup preview string for a theme.

    Returns empty string if theme not found.
    """
    theme = BUILTIN_THEMES.get(name)
    if theme is None:
        return ""

    lines: list[str] = [f"Theme: {name}", ""]
    for key, color in theme.items():
        lines.append(f"  {key:<12} {color}  [on {color}]      [/]")
    return "\n".join(lines)


def theme_to_settings(name: str) -> dict:
    """Convert a theme to Claude Code settings.json format.

    Returns empty dict if theme not found.
    """
    theme = BUILTIN_THEMES.get(name)
    if theme is None:
        return {}

    return {"theme": {"dark": dict(theme)}}
