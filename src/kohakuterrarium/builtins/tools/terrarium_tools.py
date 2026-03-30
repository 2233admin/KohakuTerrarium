"""
Terrarium management tools for the root agent.

These tools allow the root agent to create, manage, and interact with
terrariums. They access the terrarium layer via a TerrariumToolManager
stored in the environment context.
"""

import asyncio
import json
from typing import Any
from uuid import uuid4

from kohakuterrarium.builtins.tools.registry import register_builtin
from kohakuterrarium.core.channel import ChannelMessage
from kohakuterrarium.modules.tool.base import (
    BaseTool,
    ExecutionMode,
    ToolContext,
    ToolResult,
)
from kohakuterrarium.terrarium.config import CreatureConfig, load_terrarium_config
from kohakuterrarium.terrarium.runtime import TerrariumRuntime
from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)

# Key used to store/retrieve the TerrariumToolManager in the environment
TERRARIUM_MANAGER_KEY = "terrarium_manager"


class TerrariumToolManager:
    """
    Lightweight manager for terrarium tools.

    Holds references to running TerrariumRuntimes. The root agent's
    initialization code registers an instance of this in the environment
    context so that tools can access it.
    """

    def __init__(self) -> None:
        self._runtimes: dict[str, Any] = {}  # terrarium_id -> TerrariumRuntime
        self._tasks: dict[str, asyncio.Task] = {}

    def register_runtime(self, terrarium_id: str, runtime: Any) -> None:
        """Register a running terrarium runtime."""
        self._runtimes[terrarium_id] = runtime

    def get_runtime(self, terrarium_id: str) -> Any:
        """Get a runtime by ID. Raises KeyError if not found."""
        if terrarium_id not in self._runtimes:
            available = list(self._runtimes.keys())
            raise KeyError(
                f"Terrarium '{terrarium_id}' not found. "
                f"Available: {available or '(none)'}"
            )
        return self._runtimes[terrarium_id]

    def list_terrariums(self) -> list[str]:
        """List all registered terrarium IDs."""
        return list(self._runtimes.keys())

    def register_task(self, terrarium_id: str, task: asyncio.Task) -> None:
        """Track the asyncio task running a terrarium."""
        self._tasks[terrarium_id] = task

    async def stop_terrarium(self, terrarium_id: str) -> None:
        """Stop a terrarium and clean up."""
        runtime = self.get_runtime(terrarium_id)
        await runtime.stop()
        task = self._tasks.pop(terrarium_id, None)
        if task and not task.done():
            task.cancel()
        del self._runtimes[terrarium_id]


def _get_manager(context: ToolContext | None) -> TerrariumToolManager:
    """Extract the TerrariumToolManager from tool context."""
    if not context or not context.environment:
        raise RuntimeError(
            "Terrarium tools require an environment context. "
            "The root agent must be running inside a terrarium or "
            "have a TerrariumToolManager registered in its environment."
        )
    manager = context.environment.get(TERRARIUM_MANAGER_KEY)
    if manager is None:
        raise RuntimeError(
            f"No TerrariumToolManager found in environment. "
            f"Register one with environment.register('{TERRARIUM_MANAGER_KEY}', manager)."
        )
    return manager


@register_builtin("terrarium_create")
class TerrariumCreateTool(BaseTool):
    """Create and start a terrarium from a config path or inline YAML."""

    needs_context = True

    @property
    def tool_name(self) -> str:
        return "terrarium_create"

    @property
    def description(self) -> str:
        return "Create and start a terrarium from a config path"

    @property
    def execution_mode(self) -> ExecutionMode:
        return ExecutionMode.DIRECT

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "config_path": {
                    "type": "string",
                    "description": "Path to terrarium config directory (e.g. terrariums/swe_team)",
                },
            },
            "required": ["config_path"],
        }

    async def _execute(
        self, args: dict[str, Any], context: ToolContext | None = None
    ) -> ToolResult:
        manager = _get_manager(context)

        config_path = args.get("config_path", "").strip()
        if not config_path:
            return ToolResult(error="config_path is required")

        try:
            config = load_terrarium_config(config_path)
            runtime = TerrariumRuntime(config)
            terrarium_id = f"{config.name}_{uuid4().hex[:6]}"

            await runtime.start()

            # Run creatures as background task
            task = asyncio.create_task(runtime.run())
            manager.register_runtime(terrarium_id, runtime)
            manager.register_task(terrarium_id, task)

            status = runtime.get_status()
            creature_names = list(status.get("creatures", {}).keys())
            channel_names = [ch["name"] for ch in status.get("channels", [])]

            return ToolResult(
                output=(
                    f"Terrarium '{terrarium_id}' created and running.\n"
                    f"Creatures: {', '.join(creature_names)}\n"
                    f"Channels: {', '.join(channel_names)}"
                ),
                exit_code=0,
                metadata={"terrarium_id": terrarium_id},
            )
        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to create terrarium", error=error_msg)
            return ToolResult(error=f"Failed to create terrarium: {error_msg}")


@register_builtin("terrarium_status")
class TerrariumStatusTool(BaseTool):
    """Get status of a terrarium or list all terrariums."""

    needs_context = True

    @property
    def tool_name(self) -> str:
        return "terrarium_status"

    @property
    def description(self) -> str:
        return "Get status of a terrarium or list all running terrariums"

    @property
    def execution_mode(self) -> ExecutionMode:
        return ExecutionMode.DIRECT

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "terrarium_id": {
                    "type": "string",
                    "description": "Terrarium ID (omit to list all)",
                },
            },
        }

    async def _execute(
        self, args: dict[str, Any], context: ToolContext | None = None
    ) -> ToolResult:
        manager = _get_manager(context)

        terrarium_id = args.get("terrarium_id", "").strip()

        if not terrarium_id:
            # List all terrariums
            ids = manager.list_terrariums()
            if not ids:
                return ToolResult(output="No terrariums running.", exit_code=0)

            lines = ["Running terrariums:"]
            for tid in ids:
                try:
                    runtime = manager.get_runtime(tid)
                    status = runtime.get_status()
                    creatures = list(status.get("creatures", {}).keys())
                    lines.append(
                        f"  {tid}: {len(creatures)} creatures ({', '.join(creatures)})"
                    )
                except Exception:
                    lines.append(f"  {tid}: (error reading status)")
            return ToolResult(output="\n".join(lines), exit_code=0)

        # Get specific terrarium status
        try:
            runtime = manager.get_runtime(terrarium_id)
            status = runtime.get_status()
            return ToolResult(
                output=json.dumps(status, indent=2, default=str),
                exit_code=0,
            )
        except KeyError as e:
            return ToolResult(error=str(e))


@register_builtin("terrarium_stop")
class TerrariumStopTool(BaseTool):
    """Stop a running terrarium."""

    needs_context = True

    @property
    def tool_name(self) -> str:
        return "terrarium_stop"

    @property
    def description(self) -> str:
        return "Stop a running terrarium and all its creatures"

    @property
    def execution_mode(self) -> ExecutionMode:
        return ExecutionMode.DIRECT

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "terrarium_id": {
                    "type": "string",
                    "description": "ID of the terrarium to stop",
                },
            },
            "required": ["terrarium_id"],
        }

    async def _execute(
        self, args: dict[str, Any], context: ToolContext | None = None
    ) -> ToolResult:
        manager = _get_manager(context)
        terrarium_id = args.get("terrarium_id", "").strip()

        if not terrarium_id:
            return ToolResult(error="terrarium_id is required")

        try:
            await manager.stop_terrarium(terrarium_id)
            return ToolResult(
                output=f"Terrarium '{terrarium_id}' stopped.",
                exit_code=0,
            )
        except KeyError as e:
            return ToolResult(error=str(e))


@register_builtin("terrarium_send")
class TerrariumSendTool(BaseTool):
    """Send a message to a channel in a terrarium."""

    needs_context = True

    @property
    def tool_name(self) -> str:
        return "terrarium_send"

    @property
    def description(self) -> str:
        return "Send a message to a channel in a running terrarium"

    @property
    def execution_mode(self) -> ExecutionMode:
        return ExecutionMode.DIRECT

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "terrarium_id": {
                    "type": "string",
                    "description": "Terrarium ID",
                },
                "channel": {
                    "type": "string",
                    "description": "Channel name to send to",
                },
                "message": {
                    "type": "string",
                    "description": "Message content",
                },
            },
            "required": ["terrarium_id", "channel", "message"],
        }

    async def _execute(
        self, args: dict[str, Any], context: ToolContext | None = None
    ) -> ToolResult:
        manager = _get_manager(context)

        terrarium_id = args.get("terrarium_id", "").strip()
        channel_name = args.get("channel", "").strip()
        message = args.get("message", "").strip()

        if not all([terrarium_id, channel_name, message]):
            return ToolResult(
                error="terrarium_id, channel, and message are all required"
            )

        try:
            runtime = manager.get_runtime(terrarium_id)
            ch = runtime.environment.shared_channels.get(channel_name)
            if ch is None:
                available = runtime.environment.shared_channels.list_channels()
                ch_names = [info["name"] for info in available]
                return ToolResult(
                    error=f"Channel '{channel_name}' not found. Available: {ch_names}"
                )

            sender = context.agent_name if context else "root"
            msg = ChannelMessage(sender=sender, content=message)
            await ch.send(msg)

            return ToolResult(
                output=f"Message sent to [{channel_name}] in {terrarium_id}.",
                exit_code=0,
            )
        except KeyError as e:
            return ToolResult(error=str(e))


@register_builtin("terrarium_observe")
class TerrariumObserveTool(BaseTool):
    """Read recent messages from a terrarium channel."""

    needs_context = True

    @property
    def tool_name(self) -> str:
        return "terrarium_observe"

    @property
    def description(self) -> str:
        return "Read recent messages from a channel in a terrarium"

    @property
    def execution_mode(self) -> ExecutionMode:
        return ExecutionMode.DIRECT

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "terrarium_id": {
                    "type": "string",
                    "description": "Terrarium ID",
                },
                "channel": {
                    "type": "string",
                    "description": "Channel name to read from",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max messages to read (default 10)",
                },
            },
            "required": ["terrarium_id", "channel"],
        }

    async def _execute(
        self, args: dict[str, Any], context: ToolContext | None = None
    ) -> ToolResult:
        manager = _get_manager(context)

        terrarium_id = args.get("terrarium_id", "").strip()
        channel_name = args.get("channel", "").strip()
        limit = int(args.get("limit", 10))

        if not terrarium_id or not channel_name:
            return ToolResult(error="terrarium_id and channel are required")

        try:
            runtime = manager.get_runtime(terrarium_id)
            ch = runtime.environment.shared_channels.get(channel_name)
            if ch is None:
                available = runtime.environment.shared_channels.list_channels()
                ch_names = [info["name"] for info in available]
                return ToolResult(
                    error=f"Channel '{channel_name}' not found. Available: {ch_names}"
                )

            # Read from channel history
            if hasattr(ch, "history"):
                messages = ch.history[-limit:]
            elif hasattr(ch, "_history"):
                messages = ch._history[-limit:]
            else:
                return ToolResult(
                    output=f"Channel [{channel_name}] has no readable history.",
                    exit_code=0,
                )

            if not messages:
                return ToolResult(
                    output=f"No messages in [{channel_name}].",
                    exit_code=0,
                )

            lines = [f"Recent messages in [{channel_name}] ({len(messages)}/{limit}):"]
            for msg in messages:
                sender = getattr(msg, "sender", "?")
                content = getattr(msg, "content", str(msg))
                preview = content[:200] + "..." if len(content) > 200 else content
                lines.append(f"  [{sender}]: {preview}")

            return ToolResult(output="\n".join(lines), exit_code=0)
        except KeyError as e:
            return ToolResult(error=str(e))


@register_builtin("creature_start")
class CreatureStartTool(BaseTool):
    """Add and start a new creature in a running terrarium."""

    needs_context = True

    @property
    def tool_name(self) -> str:
        return "creature_start"

    @property
    def description(self) -> str:
        return "Add a new creature to a running terrarium via hot-plug"

    @property
    def execution_mode(self) -> ExecutionMode:
        return ExecutionMode.DIRECT

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "terrarium_id": {
                    "type": "string",
                    "description": "Terrarium ID",
                },
                "name": {
                    "type": "string",
                    "description": "Name for the new creature",
                },
                "config_path": {
                    "type": "string",
                    "description": "Path to creature config (e.g. creatures/swe)",
                },
                "listen_channels": {
                    "type": "string",
                    "description": "Comma-separated channel names to listen on",
                },
                "send_channels": {
                    "type": "string",
                    "description": "Comma-separated channel names to send to",
                },
            },
            "required": ["terrarium_id", "name", "config_path"],
        }

    async def _execute(
        self, args: dict[str, Any], context: ToolContext | None = None
    ) -> ToolResult:
        manager = _get_manager(context)

        terrarium_id = args.get("terrarium_id", "").strip()
        name = args.get("name", "").strip()
        config_path = args.get("config_path", "").strip()
        listen_raw = args.get("listen_channels", "")
        send_raw = args.get("send_channels", "")

        if not all([terrarium_id, name, config_path]):
            return ToolResult(error="terrarium_id, name, and config_path are required")

        listen = (
            [ch.strip() for ch in listen_raw.split(",") if ch.strip()]
            if listen_raw
            else []
        )
        send = (
            [ch.strip() for ch in send_raw.split(",") if ch.strip()] if send_raw else []
        )

        try:
            runtime = manager.get_runtime(terrarium_id)
            creature_cfg = CreatureConfig(
                name=name,
                config_path=config_path,
                listen_channels=listen,
                send_channels=send,
            )
            handle = await runtime.add_creature(creature_cfg)

            return ToolResult(
                output=(
                    f"Creature '{name}' added to {terrarium_id}.\n"
                    f"Config: {config_path}\n"
                    f"Listening: {listen or '(none)'}\n"
                    f"Sending: {send or '(none)'}"
                ),
                exit_code=0,
            )
        except KeyError as e:
            return ToolResult(error=str(e))
        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to start creature", error=error_msg)
            return ToolResult(error=f"Failed to start creature: {error_msg}")


@register_builtin("creature_stop")
class CreatureStopTool(BaseTool):
    """Stop and remove a creature from a running terrarium."""

    needs_context = True

    @property
    def tool_name(self) -> str:
        return "creature_stop"

    @property
    def description(self) -> str:
        return "Stop and remove a creature from a running terrarium"

    @property
    def execution_mode(self) -> ExecutionMode:
        return ExecutionMode.DIRECT

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "terrarium_id": {
                    "type": "string",
                    "description": "Terrarium ID",
                },
                "name": {
                    "type": "string",
                    "description": "Name of the creature to stop",
                },
            },
            "required": ["terrarium_id", "name"],
        }

    async def _execute(
        self, args: dict[str, Any], context: ToolContext | None = None
    ) -> ToolResult:
        manager = _get_manager(context)

        terrarium_id = args.get("terrarium_id", "").strip()
        name = args.get("name", "").strip()

        if not terrarium_id or not name:
            return ToolResult(error="terrarium_id and name are required")

        try:
            runtime = manager.get_runtime(terrarium_id)
            removed = await runtime.remove_creature(name)
            if removed:
                return ToolResult(
                    output=f"Creature '{name}' removed from {terrarium_id}.",
                    exit_code=0,
                )
            else:
                return ToolResult(
                    error=f"Creature '{name}' not found in {terrarium_id}."
                )
        except KeyError as e:
            return ToolResult(error=str(e))
