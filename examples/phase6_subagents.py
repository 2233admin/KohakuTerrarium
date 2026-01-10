"""
Phase 6 Test: Sub-Agent System

Run: python examples/phase6_subagents.py

Expected:
- Create and configure sub-agents
- Parse agent tags from LLM output
- Demonstrate manager registration and lookup
- Show builtin sub-agent configurations
"""

import asyncio
from pathlib import Path

# Add project root for development
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"


def load_env() -> None:
    """Load environment variables from .env file."""
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    import os

                    os.environ.setdefault(key.strip(), value.strip())


async def demo_subagent_config():
    """Demonstrate sub-agent configuration."""
    from kohakuterrarium.modules.subagent import (
        OutputTarget,
        SubAgentConfig,
        SubAgentInfo,
    )

    print("=== Sub-Agent Configuration ===\n")

    # Create a custom sub-agent config
    config = SubAgentConfig(
        name="code_search",
        description="Search codebase for patterns and files",
        tools=["glob", "grep", "read"],
        system_prompt="You are a code search agent. Find relevant files and code patterns.",
        can_modify=False,
        stateless=True,
        max_turns=5,
        timeout=60.0,
    )

    print(f"Config: {config.name}")
    print(f"  Description: {config.description}")
    print(f"  Tools: {config.tools}")
    print(f"  Can modify: {config.can_modify}")
    print(f"  Stateless: {config.stateless}")
    print(f"  Output to: {config.output_to.value}")
    print()

    # Create info for system prompt
    info = SubAgentInfo.from_config(config)
    print(f"Prompt line: {info.to_prompt_line()}")
    print()


async def demo_builtin_subagents():
    """Demonstrate builtin sub-agent configurations."""
    from kohakuterrarium.builtins.subagents import (
        get_builtin_subagent_config,
        list_builtin_subagents,
    )

    print("=== Builtin Sub-Agents ===\n")

    names = list_builtin_subagents()
    print(f"Available: {names}\n")

    for name in names:
        config = get_builtin_subagent_config(name)
        if config:
            print(f"- {config.name}: {config.description}")
            print(f"    Tools: {config.tools}")
            print(f"    Can modify: {config.can_modify}")
            print()


async def demo_agent_tag_parsing():
    """Demonstrate parsing <agent> tags from LLM output."""
    from kohakuterrarium.parsing import (
        extract_subagent_calls,
        extract_tool_calls,
        parse_complete,
    )

    print("=== Agent Tag Parsing ===\n")

    # Simulated LLM output with agent tags
    llm_output = """
I'll help you understand this codebase. Let me search for the relevant files.

<agent type="explore">Find all Python files containing "async def" in the src directory</agent>

Based on what I found, I'll create a plan for the implementation.

<agent type="plan">Design the authentication system with JWT tokens</agent>

I'll also check your memory for any preferences.

<agent type="memory_read">Find user preferences about code style</agent>
"""

    print("Input (simulated LLM output):")
    print("-" * 40)
    print(llm_output.strip())
    print("-" * 40)
    print()

    # Parse the output
    events = parse_complete(llm_output)

    # Extract tool calls and sub-agent calls
    tool_calls = extract_tool_calls(events)
    subagent_calls = extract_subagent_calls(events)

    print(f"Tool calls found: {len(tool_calls)}")
    print(f"Sub-agent calls found: {len(subagent_calls)}")
    print()

    for i, call in enumerate(subagent_calls, 1):
        print(f"Sub-agent call {i}:")
        print(f"  Type: {call.name}")
        print(f"  Task: {call.args.get('task', 'N/A')}")
        print()


async def demo_subagent_manager():
    """Demonstrate SubAgentManager usage."""
    from kohakuterrarium.builtins.subagents import get_builtin_subagent_config
    from kohakuterrarium.core.registry import Registry
    from kohakuterrarium.modules.subagent import SubAgentConfig, SubAgentManager

    print("=== Sub-Agent Manager ===\n")

    # Create parent registry (would normally have tools)
    registry = Registry()

    # Create manager
    manager = SubAgentManager(
        parent_registry=registry,
        llm=None,  # No LLM for demo
    )

    # Register builtin sub-agents
    for name in ["explore", "plan", "memory_read", "memory_write"]:
        config = get_builtin_subagent_config(name)
        if config:
            manager.register(config)

    # Register a custom sub-agent
    custom_config = SubAgentConfig(
        name="summarize",
        description="Summarize code or documentation",
        tools=["read"],
        system_prompt="You are a summarization agent. Provide concise summaries.",
        max_turns=3,
    )
    manager.register(custom_config)

    print(f"Registered sub-agents: {manager.list_subagents()}")
    print()

    # Get sub-agent info
    info = manager.get_subagent_info("explore")
    if info:
        print(f"Explore agent: {info.description}")
        print(f"  Can modify: {info.can_modify}")
    print()

    # Generate prompt section
    prompt = manager.get_subagents_prompt()
    print("Generated prompt section:")
    print("-" * 40)
    print(prompt)
    print("-" * 40)


async def demo_output_subagent():
    """Demonstrate output sub-agent concept."""
    from kohakuterrarium.modules.subagent import OutputTarget, SubAgentConfig

    print("\n=== Output Sub-Agent (for RP chatbot) ===\n")

    # This demonstrates the output sub-agent pattern for low-latency responses
    response_config = SubAgentConfig(
        name="response",
        description="Generate user-facing responses",
        tools=["read"],  # Minimal tools
        system_prompt="""You are a response generation agent.
Generate appropriate responses based on context from the controller.
The controller decides WHEN to respond - you decide WHAT to say.""",
        can_modify=False,
        stateless=False,  # Maintains conversation
        interactive=True,  # Stays alive, receives updates
        output_to=OutputTarget.EXTERNAL,  # Streams directly to user
        max_turns=50,
        timeout=600.0,
    )

    print(f"Response agent configured:")
    print(f"  Output to: {response_config.output_to.value}")
    print(f"  Interactive: {response_config.interactive}")
    print(f"  Stateless: {response_config.stateless}")
    print()
    print("This pattern enables:")
    print("  1. Controller orchestrates (fast decisions)")
    print("  2. Response agent handles user-facing output (maintains tone)")
    print("  3. Low latency: controller dispatches, doesn't wait")
    print("  4. Memory agents run in background")


async def main():
    load_env()

    from kohakuterrarium.utils.logging import set_level

    set_level("WARNING")  # Quiet for demo

    print("=" * 60)
    print("KohakuTerrarium Phase 6: Sub-Agent System Demo")
    print("=" * 60)
    print()

    await demo_subagent_config()
    await demo_builtin_subagents()
    await demo_agent_tag_parsing()
    await demo_subagent_manager()
    await demo_output_subagent()

    print("\n" + "=" * 60)
    print("Demo complete! Sub-agent system is ready for integration.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
