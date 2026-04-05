"""CLI subparser definitions for kt studio."""

import argparse

from kohakuterrarium.studio.handlers import handle_studio_command  # re-export

__all__ = ["add_studio_subparser", "handle_studio_command"]


def add_studio_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Add studio subcommands to the CLI parser."""
    studio_parser = subparsers.add_parser(
        "studio",
        help="Manage AI coding CLI profiles and launch sessions",
    )
    studio_sub = studio_parser.add_subparsers(dest="studio_command")

    # studio init
    studio_sub.add_parser("init", help="Create default studio.yaml config")

    # studio launch [profile]
    launch_p = studio_sub.add_parser(
        "launch", help="Launch claude with a profile's merged settings"
    )
    launch_p.add_argument(
        "profile",
        nargs="?",
        default=None,
        help="Profile name (default: active profile)",
    )

    # studio apply [profile]
    apply_p = studio_sub.add_parser(
        "apply", help="Output merged settings JSON without launching"
    )
    apply_p.add_argument(
        "profile",
        nargs="?",
        default=None,
        help="Profile name (default: active profile)",
    )
    apply_p.add_argument(
        "-o",
        "--output",
        default=None,
        help="Write merged settings to file instead of stdout",
    )

    # studio profiles
    studio_sub.add_parser("profiles", help="List all profiles")

    # studio profile {create,show,edit,delete}
    profile_p = studio_sub.add_parser("profile", help="Manage a single profile")
    profile_sub = profile_p.add_subparsers(dest="profile_action")

    create_p = profile_sub.add_parser("create", help="Create a new profile")
    create_p.add_argument("name", help="Profile name")
    create_p.add_argument("--model", default="sonnet", help="Model (default: sonnet)")
    create_p.add_argument(
        "--effort", default="high", help="Effort level (default: high)"
    )
    create_p.add_argument("--theme", default=None, help="Theme name")

    show_p = profile_sub.add_parser("show", help="Show profile details")
    show_p.add_argument("name", help="Profile name")

    edit_p = profile_sub.add_parser("edit", help="Edit profile in $EDITOR")
    edit_p.add_argument("name", help="Profile name")

    delete_p = profile_sub.add_parser("delete", help="Delete a profile")
    delete_p.add_argument("name", help="Profile name")

    # studio doctor
    studio_sub.add_parser("doctor", help="Run health checks")

    # studio sessions (list all)
    studio_sub.add_parser("sessions", help="List named sessions")

    # studio session {name,resume,fork,inspect,delete,export,incognito}
    session_p = studio_sub.add_parser("session", help="Manage Claude Code sessions")
    session_sub = session_p.add_subparsers(dest="session_action")

    name_p = session_sub.add_parser("name", help="Name a session UUID")
    name_p.add_argument("identifier", help="Session UUID or 'latest'")
    name_p.add_argument("name", help="Human-readable name")

    resume_p = session_sub.add_parser("resume", help="Resume a named session")
    resume_p.add_argument("name", help="Session name")
    resume_p.add_argument("--profile", default=None, help="Profile to apply")

    fork_p = session_sub.add_parser("fork", help="Fork a named session")
    fork_p.add_argument("name", help="Session name to fork")
    fork_p.add_argument("new_name", nargs="?", default=None, help="New fork name")

    inspect_p = session_sub.add_parser("inspect", help="Inspect a named session")
    inspect_p.add_argument("name", help="Session name")

    del_p = session_sub.add_parser("delete", help="Delete a named session")
    del_p.add_argument("name", help="Session name")

    export_p = session_sub.add_parser("export", help="Export session transcript")
    export_p.add_argument("name", help="Session name")
    export_p.add_argument(
        "--format", default="md", choices=["md", "html"], help="Output format"
    )

    incognito_p = session_sub.add_parser("incognito", help="Launch ephemeral session")
    incognito_p.add_argument("--profile", default=None, help="Profile to apply")

    # studio statusline {install,preview,uninstall}
    statusline_p = studio_sub.add_parser("statusline", help="Manage status line")
    statusline_sub = statusline_p.add_subparsers(dest="statusline_action")
    statusline_sub.add_parser("install", help="Install statusline runner")
    statusline_sub.add_parser("preview", help="Preview statusline output")
    statusline_sub.add_parser("uninstall", help="Remove statusline runner")

    # studio theme {list,show,apply}
    theme_p = studio_sub.add_parser("theme", help="Manage themes")
    theme_sub = theme_p.add_subparsers(dest="theme_action")
    theme_sub.add_parser("list", help="List available themes")
    show_theme_p = theme_sub.add_parser("show", help="Preview a theme")
    show_theme_p.add_argument("name", help="Theme name")
    apply_theme_p = theme_sub.add_parser("apply", help="Apply a theme to profile")
    apply_theme_p.add_argument("name", help="Theme name")
    apply_theme_p.add_argument("--profile", default=None, help="Target profile")

    # studio targets (list all targets with install status)
    studio_sub.add_parser("targets", help="List all AI coding tool targets")

    # studio target <name> status
    target_p = studio_sub.add_parser("target", help="Manage a specific target")
    target_sub = target_p.add_subparsers(dest="target_action")
    target_status_p = target_sub.add_parser("status", help="Show target status")
    target_status_p.add_argument("name", help="Target name")

    # studio copilot {status,model,models,patch,unpatch}
    copilot_p = studio_sub.add_parser("copilot", help="Manage Copilot CLI")
    copilot_sub = copilot_p.add_subparsers(dest="copilot_action")
    copilot_sub.add_parser("status", help="Show Copilot CLI status")
    model_p = copilot_sub.add_parser("model", help="Set active model")
    model_p.add_argument("name", help="Model identifier")
    copilot_sub.add_parser("models", help="List available models")
    copilot_sub.add_parser("patch", help="Apply AST patch for extended models")
    copilot_sub.add_parser("unpatch", help="Restore original Copilot CLI")

    # studio cost [--period today|week|month]
    cost_p = studio_sub.add_parser("cost", help="Show API cost summary")
    cost_p.add_argument(
        "--period", default="today", choices=["today", "week", "month"]
    )

    # studio record [--target X] [--output file.jsonl]
    record_p = studio_sub.add_parser("record", help="Record a CLI session as JSONL")
    record_p.add_argument("--target", default=None, help="Target to record")
    record_p.add_argument("--output", default=None, help="Output JSONL path")

    # studio replay <file> [--speed N]
    replay_p = studio_sub.add_parser("replay", help="Replay a recorded session")
    replay_p.add_argument("recording", help="Path to recording JSONL")
    replay_p.add_argument("--speed", type=float, default=1.0, help="Playback speed")

    # studio compare "task" [--targets a,b,c] [--timeout N]
    compare_p = studio_sub.add_parser("compare", help="Run task on multiple targets")
    compare_p.add_argument("task", help="Task string or path to task file")
    compare_p.add_argument(
        "--targets", default=None, help="Comma-separated target names"
    )
    compare_p.add_argument(
        "--timeout", type=int, default=120, help="Per-target timeout (sec)"
    )

    # studio completion bash|zsh|fish|powershell
    comp_p = studio_sub.add_parser("completion", help="Generate shell completion script")
    comp_p.add_argument("shell", choices=["bash", "zsh", "fish", "powershell"])

    # studio diff <profile-a> <profile-b>
    diff_p = studio_sub.add_parser("diff", help="Compare two profiles")
    diff_p.add_argument("profile_a", help="First profile name")
    diff_p.add_argument("profile_b", help="Second profile name")
