"""
Terrarium configuration loading.

Loads multi-agent terrarium config from YAML, resolving creature
config paths relative to the terrarium config directory.
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ChannelConfig:
    """Configuration for a single terrarium channel."""

    name: str
    channel_type: str = "queue"  # "queue" or "broadcast"
    description: str = ""


@dataclass
class CreatureConfig:
    """Configuration for a single creature (agent) in the terrarium."""

    name: str
    config_path: str  # Path to agent config folder
    listen_channels: list[str] = field(default_factory=list)
    send_channels: list[str] = field(default_factory=list)
    output_log: bool = False
    output_log_size: int = 100


@dataclass
class RootConfig:
    """Optional root agent configuration.

    The root agent sits OUTSIDE the terrarium and manages it via
    terrarium tools. It is the user-facing interface.
    """

    config_path: str  # Path to root creature config (e.g. creatures/root)
    interface: str = "cli"  # "cli" or "tui" - how user talks to root


@dataclass
class TerrariumConfig:
    """Top-level terrarium configuration."""

    name: str
    creatures: list[CreatureConfig]
    channels: list[ChannelConfig]
    root: RootConfig | None = None


def build_channel_topology_prompt(
    config: "TerrariumConfig",
    creature: CreatureConfig,
) -> str:
    """
    Build a prompt section describing channel topology and semantics.

    Teaches the creature:
    - How channels work (messages vs requests)
    - Which channels it listens on and sends to
    - The difference between queue and broadcast
    - That receiving a message does NOT require a reply
    """
    ch_by_name: dict[str, ChannelConfig] = {}
    for ch in config.channels:
        ch_by_name[ch.name] = ch

    relevant_names: set[str] = set()
    relevant_names.update(creature.listen_channels)
    relevant_names.update(creature.send_channels)
    for ch in config.channels:
        if ch.channel_type == "broadcast":
            relevant_names.add(ch.name)

    if not relevant_names:
        return ""

    listen_set = set(creature.listen_channels)
    send_set = set(creature.send_channels)

    lines: list[str] = [
        "## Team Communication",
        "",
        "You are part of a multi-agent team. You communicate through channels.",
        "",
        "IMPORTANT - How channels work:",
        "- Messages arrive on your channels automatically. A message is INFORMATION, not a request.",
        "- Receiving a message does NOT mean you must reply or send a message back.",
        "- Only send a message when YOUR WORKFLOW requires it (e.g. sending your output to the next agent).",
        "- Queue channels deliver to one recipient. Broadcast channels deliver to all team members.",
        "- After you complete your task and output your termination keyword, you are DONE. Do not process further messages.",
        "",
        "### Your Channels",
        "",
    ]

    for ch_name in sorted(relevant_names):
        ch_cfg = ch_by_name.get(ch_name)
        if ch_cfg is None:
            continue

        desc = f" - {ch_cfg.description}" if ch_cfg.description else ""
        roles: list[str] = []
        if ch_name in listen_set:
            roles.append("listen")
        if ch_name in send_set:
            roles.append("send")
        role_str = f" ({', '.join(roles)})" if roles else ""

        lines.append(f"- `{ch_name}` [{ch_cfg.channel_type}]{role_str}{desc}")

    lines.append("")

    # List other creatures for context
    other_creatures = [c.name for c in config.creatures if c.name != creature.name]
    if other_creatures:
        lines.append(f"### Team Members: {', '.join(other_creatures)}")
        lines.append("")

    return "\n".join(lines)


def _find_terrarium_config(path: Path) -> Path:
    """
    Resolve the terrarium config file path.

    If *path* is a file, return it directly.
    If it is a directory, look for ``terrarium.yaml`` or ``terrarium.yml``.

    Raises:
        FileNotFoundError: If no config file can be located.
    """
    if path.is_file():
        return path

    for name in ("terrarium.yaml", "terrarium.yml"):
        candidate = path / name
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        f"No terrarium config found at {path} "
        "(expected terrarium.yaml or terrarium.yml)"
    )


def _parse_creature(data: dict, base_dir: Path) -> CreatureConfig:
    """Parse a single creature entry from raw YAML data."""
    name = data.get("name", "")
    if not name:
        raise ValueError("Creature entry missing 'name'")

    raw_path = data.get("config", "")
    if not raw_path:
        raise ValueError(f"Creature '{name}' missing 'config' path")

    # Resolve config_path relative to the terrarium config directory
    resolved = (base_dir / raw_path).resolve()

    channels = data.get("channels", {})

    return CreatureConfig(
        name=name,
        config_path=str(resolved),
        listen_channels=list(channels.get("listen", [])),
        send_channels=list(channels.get("can_send", [])),
        output_log=bool(data.get("output_log", False)),
        output_log_size=int(data.get("output_log_size", 100)),
    )


def _parse_channels(raw: dict) -> list[ChannelConfig]:
    """Parse the channels mapping from raw YAML data."""
    result: list[ChannelConfig] = []
    for ch_name, ch_data in raw.items():
        if isinstance(ch_data, dict):
            result.append(
                ChannelConfig(
                    name=ch_name,
                    channel_type=ch_data.get("type", "queue"),
                    description=ch_data.get("description", ""),
                )
            )
        else:
            # Bare channel name with no extra config
            result.append(ChannelConfig(name=ch_name))
    return result


def load_terrarium_config(path: str | Path) -> TerrariumConfig:
    """
    Load terrarium configuration from a YAML file or directory.

    Supports both a direct file path and a directory containing
    ``terrarium.yaml``.  Creature ``config`` paths are resolved
    relative to the directory that holds the terrarium YAML file.

    Args:
        path: File or directory path.

    Returns:
        Parsed TerrariumConfig.

    Raises:
        FileNotFoundError: If config file cannot be found.
        ValueError: If required fields are missing.
    """
    path = Path(path)
    config_file = _find_terrarium_config(path)
    base_dir = config_file.parent

    logger.debug("Loading terrarium config", path=str(config_file))

    with open(config_file, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    # The top-level key is "terrarium"
    terrarium_data = raw.get("terrarium", raw)

    name = terrarium_data.get("name", "terrarium")

    # Parse creatures
    creatures_raw = terrarium_data.get("creatures", [])
    creatures = [_parse_creature(c, base_dir) for c in creatures_raw]

    # Parse channels
    channels_raw = terrarium_data.get("channels", {})
    channels = _parse_channels(channels_raw)

    # Parse optional root agent
    root: RootConfig | None = None
    root_raw = terrarium_data.get("root")
    if root_raw:
        root_path = root_raw.get("config", "")
        if not root_path:
            raise ValueError("Root agent config missing 'config' path")
        resolved_root = str((base_dir / root_path).resolve())
        root = RootConfig(
            config_path=resolved_root,
            interface=root_raw.get("interface", "cli"),
        )

    config = TerrariumConfig(
        name=name, creatures=creatures, channels=channels, root=root
    )

    logger.info(
        "Terrarium config loaded",
        terrarium_name=config.name,
        creatures=len(config.creatures),
        channels=len(config.channels),
    )
    return config
