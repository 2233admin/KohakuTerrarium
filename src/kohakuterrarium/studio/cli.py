"""CLI subparser and command dispatch for kt studio."""

import argparse
import asyncio
import json
from pathlib import Path

from kohakuterrarium.studio.config import (
    STUDIO_CONFIG_PATH,
    ProfileConfig,
    StudioConfig,
    load_studio_config,
    save_studio_config,
)
from kohakuterrarium.studio.launcher import ProfileLauncher, doctor, find_claude_cli
from kohakuterrarium.studio.profiles import (
    create_profile,
    delete_profile,
    edit_profile,
    list_profiles,
    show_profile,
)
from kohakuterrarium.studio.sessions import SessionManager
from kohakuterrarium.studio.statusline import StatusLineBuilder
from kohakuterrarium.studio.themes import (
    get_theme,
    list_themes,
    preview_theme,
)
from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)


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


def handle_studio_command(args: argparse.Namespace) -> int:
    """Dispatch studio subcommand."""
    match args.studio_command:
        case "init":
            return _handle_init()
        case "launch":
            return _handle_launch(args)
        case "apply":
            return _handle_apply(args)
        case "profiles":
            return _handle_profiles()
        case "profile":
            return _handle_profile_subcommand(args)
        case "doctor":
            return _handle_doctor()
        case "sessions":
            return _handle_sessions_list()
        case "session":
            return _handle_session_subcommand(args)
        case "statusline":
            return _handle_statusline_subcommand(args)
        case "theme":
            return _handle_theme_subcommand(args)
        case _:
            print(
                "Usage: kt studio"
                " {init,launch,apply,profiles,profile,doctor,sessions,session,statusline,theme}"
            )
            return 0


def _handle_init() -> int:
    """Create default studio.yaml if it doesn't exist."""
    if STUDIO_CONFIG_PATH.exists():
        print(f"Studio config already exists: {STUDIO_CONFIG_PATH}")
        return 0

    config = StudioConfig(
        active_profile="default",
        profiles={"default": ProfileConfig()},
    )
    save_studio_config(config)
    print(f"Created: {STUDIO_CONFIG_PATH}")
    print("Default profile: model=sonnet, effort=high")
    return 0


def _resolve_profile(
    args: argparse.Namespace,
) -> tuple[StudioConfig, str, ProfileConfig] | None:
    """Resolve a profile name from args or active_profile. Returns (config, name, profile) or None."""
    config = load_studio_config()
    profile_name = getattr(args, "profile", None) or config.active_profile

    if not profile_name:
        print("No profile specified and no active profile set.")
        print("Use: kt studio launch <profile> or kt studio profile create <name>")
        return None

    profile = config.profiles.get(profile_name)
    if profile is None:
        print(f"Profile not found: {profile_name}")
        available = ", ".join(sorted(config.profiles.keys()))
        if available:
            print(f"Available: {available}")
        return None

    return config, profile_name, profile


def _handle_launch(args: argparse.Namespace) -> int:
    """Launch claude with merged profile settings."""
    resolved = _resolve_profile(args)
    if resolved is None:
        return 1

    config, profile_name, profile = resolved

    if find_claude_cli() is None:
        print("Error: claude CLI not found on PATH")
        return 1

    launcher = ProfileLauncher(profile, config)
    logger.info("Launching profile '%s'", profile_name)
    return asyncio.run(launcher.launch())


def _handle_apply(args: argparse.Namespace) -> int:
    """Output merged settings JSON without launching."""
    resolved = _resolve_profile(args)
    if resolved is None:
        return 1

    config, profile_name, profile = resolved
    launcher = ProfileLauncher(profile, config)
    merged = launcher.build_settings_json()
    output_json = json.dumps(merged, indent=2)

    output_path = getattr(args, "output", None)
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(output_json, encoding="utf-8")
        print(f"Written to: {output_path}")
    else:
        print(output_json)

    return 0


def _handle_profiles() -> int:
    """List all profiles with formatted output."""
    entries = list_profiles()
    config = load_studio_config()

    if not entries:
        print("No profiles defined. Use: kt studio profile create <name>")
        return 0

    print(f"{'Name':<20} {'Model':<15} {'Effort':<10} {'Active'}")
    print("-" * 55)
    for name, profile in entries:
        active = " *" if name == config.active_profile else ""
        print(f"{name:<20} {profile.model:<15} {profile.effort:<10}{active}")
    return 0


def _handle_profile_subcommand(args: argparse.Namespace) -> int:
    """Dispatch profile sub-subcommand."""
    match getattr(args, "profile_action", None):
        case "create":
            try:
                p = create_profile(
                    args.name,
                    model=args.model,
                    effort=args.effort,
                    theme=args.theme,
                )
                print(
                    f"Created profile '{args.name}' (model={p.model}, effort={p.effort})"
                )
                return 0
            except ValueError as e:
                print(f"Error: {e}")
                return 1
        case "show":
            p = show_profile(args.name)
            if p is None:
                print(f"Profile not found: {args.name}")
                return 1
            print(f"Name:    {args.name}")
            print(f"Model:   {p.model}")
            print(f"Effort:  {p.effort}")
            if p.theme:
                print(f"Theme:   {p.theme}")
            if p.env:
                print(f"Env:     {p.env}")
            if p.hooks:
                print(f"Hooks:   {len(p.hooks)} event(s)")
            if p.statusline:
                print(
                    f"Status:  {p.statusline.style} ({', '.join(p.statusline.segments)})"
                )
            if p.permissions:
                print(f"Perms:   {p.permissions}")
            if p.append_system_prompt_file:
                print(f"Prompt:  {p.append_system_prompt_file}")
            if p.mcp_config:
                print(f"MCP:     {p.mcp_config}")
            if p.plugin_dirs:
                print(f"Plugins: {', '.join(p.plugin_dirs)}")
            return 0
        case "edit":
            try:
                edit_profile(args.name)
                return 0
            except KeyError as e:
                print(f"Error: {e}")
                return 1
        case "delete":
            try:
                delete_profile(args.name)
                print(f"Deleted profile '{args.name}'")
                return 0
            except KeyError as e:
                print(f"Error: {e}")
                return 1
        case _:
            print("Usage: kt studio profile {create,show,edit,delete} <name>")
            return 0


def _handle_doctor() -> int:
    """Run health checks and display results."""
    issues = doctor()
    if not issues:
        print("All good. Studio is healthy.")
        return 0

    print(f"Found {len(issues)} issue(s):")
    for issue in issues:
        print(f"  - {issue}")
    return 1


def _handle_sessions_list() -> int:
    """List all named sessions."""
    manager = SessionManager()
    entries = manager.list_sessions()

    if not entries:
        print("No named sessions. Use: kt studio session name <uuid|latest> <name>")
        return 0

    print(f"{'Name':<20} {'UUID':<10} {'Project Dir':<25} {'Created':<22} {'Tags'}")
    print("-" * 90)
    for name, entry in entries:
        uuid_short = entry.uuid[:8] if entry.uuid else ""
        tags_str = ", ".join(entry.tags) if entry.tags else ""
        created_short = entry.created[:19] if entry.created else ""
        print(
            f"{name:<20} {uuid_short:<10} {entry.project_dir:<25} {created_short:<22} {tags_str}"
        )
    return 0


def _handle_session_subcommand(args: argparse.Namespace) -> int:
    """Dispatch session sub-subcommand."""
    manager = SessionManager()

    match getattr(args, "session_action", None):
        case "name":
            try:
                entry = manager.name_session(args.identifier, args.name)
                print(f"Named session '{args.name}' -> {entry.uuid}")
                return 0
            except ValueError as e:
                print(f"Error: {e}")
                return 1
        case "resume":
            try:
                return manager.resume_session(
                    args.name, profile=getattr(args, "profile", None)
                )
            except KeyError as e:
                print(f"Error: {e}")
                return 1
        case "fork":
            try:
                return manager.fork_session(args.name, getattr(args, "new_name", None))
            except KeyError as e:
                print(f"Error: {e}")
                return 1
        case "inspect":
            try:
                info = manager.inspect_session(args.name)
                for key, value in info.items():
                    print(f"{key:<15} {value}")
                return 0
            except KeyError as e:
                print(f"Error: {e}")
                return 1
        case "delete":
            try:
                manager.delete_session(args.name)
                print(f"Deleted session '{args.name}'")
                return 0
            except KeyError as e:
                print(f"Error: {e}")
                return 1
        case "export":
            try:
                output = manager.export_session(
                    args.name, fmt=getattr(args, "format", "md")
                )
                print(output)
                return 0
            except (KeyError, FileNotFoundError) as e:
                print(f"Error: {e}")
                return 1
        case "incognito":
            return manager.launch_incognito(profile=getattr(args, "profile", None))
        case _:
            print(
                "Usage: kt studio session {name,resume,fork,inspect,delete,export,incognito}"
            )
            return 0


def _handle_statusline_subcommand(args: argparse.Namespace) -> int:
    """Dispatch statusline sub-subcommand."""
    match getattr(args, "statusline_action", None):
        case "install":
            config = load_studio_config()
            profile_name = config.active_profile
            profile = config.profiles.get(profile_name) if profile_name else None
            sl_config = (
                profile.statusline
                if profile and profile.statusline
                else StatuslineConfig()
            )
            theme_name = profile.theme if profile else None
            builder = StatusLineBuilder(sl_config, theme_name=theme_name)
            builder.install()
            print(
                f"Statusline installed (style={sl_config.style}, segments={sl_config.segments})"
            )
            return 0
        case "preview":
            config = load_studio_config()
            profile_name = config.active_profile
            profile = config.profiles.get(profile_name) if profile_name else None
            sl_config = (
                profile.statusline
                if profile and profile.statusline
                else StatuslineConfig()
            )
            builder = StatusLineBuilder(sl_config)
            print(builder.preview())
            return 0
        case "uninstall":
            builder = StatusLineBuilder(StatuslineConfig())
            builder.uninstall()
            print("Statusline uninstalled")
            return 0
        case _:
            print("Usage: kt studio statusline {install,preview,uninstall}")
            return 0


def _handle_theme_subcommand(args: argparse.Namespace) -> int:
    """Dispatch theme sub-subcommand."""
    match getattr(args, "theme_action", None):
        case "list":
            config = load_studio_config()
            profile_name = config.active_profile
            profile = config.profiles.get(profile_name) if profile_name else None
            active_theme = profile.theme if profile else None
            for name in list_themes():
                marker = " *" if name == active_theme else ""
                print(f"  {name}{marker}")
            return 0
        case "show":
            result = preview_theme(args.name)
            if not result:
                print(f"Theme not found: {args.name}")
                return 1
            print(result)
            return 0
        case "apply":
            if get_theme(args.name) is None:
                print(f"Theme not found: {args.name}")
                return 1
            config = load_studio_config()
            profile_name = getattr(args, "profile", None) or config.active_profile
            profile = config.profiles.get(profile_name)
            if profile is None:
                print(f"Profile not found: {profile_name}")
                return 1
            profile.theme = args.name
            save_studio_config(config)
            print(f"Applied theme '{args.name}' to profile '{profile_name}'")
            return 0
        case _:
            print("Usage: kt studio theme {list,show,apply}")
            return 0
