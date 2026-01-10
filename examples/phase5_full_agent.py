"""
Phase 5 Test: Full agent from config

Run: python examples/phase5_full_agent.py agents/swe_agent

Expected:
- Load agent from config folder
- CLI input working
- Controller orchestrates
- Tools execute
- Output routed correctly
"""

import asyncio
import sys
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


async def main():
    # Load environment
    load_env()

    from kohakuterrarium.core import Agent, load_agent_config
    from kohakuterrarium.utils.logging import get_logger

    logger = get_logger(__name__)

    # Get agent path from args or use default
    if len(sys.argv) > 1:
        agent_path = sys.argv[1]
    else:
        # Default to swe_agent
        agent_path = str(project_root / "agents" / "swe_agent")

    print(f"Loading agent from: {agent_path}")

    try:
        # Load config
        config = load_agent_config(agent_path)
        print(f"Agent: {config.name} v{config.version}")
        print(f"Model: {config.model}")
        print(f"Tools: {[t.name for t in config.tools]}")
        print()

        # Create agent
        agent = Agent(config)

        # Run agent
        print("=== Starting Agent (type 'exit' to quit) ===")
        print()

        await agent.run()

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nUsage: python examples/phase5_full_agent.py <agent_folder>")
        print("Example: python examples/phase5_full_agent.py agents/swe_agent")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nInterrupted")
    except Exception as e:
        logger.error("Agent error", error=str(e))
        raise

    print("\nAgent terminated")


if __name__ == "__main__":
    asyncio.run(main())
