"""
Phase 6 Concept: Role-Playing Chatbot Architecture

Demonstrates the RP chatbot design:
- Controller as orchestrator (turn detection, memory dispatch, response dispatch)
- Output sub-agent pattern for low-latency responses
- Memory sub-agents for context management

Run: python examples/phase6_rp_concept.py
"""

import asyncio
from pathlib import Path

project_root = Path(__file__).parent.parent


def load_env() -> None:
    """Load environment variables from .env file."""
    env_path = project_root / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    import os

                    os.environ.setdefault(key.strip(), value.strip())


async def demonstrate_turn_detection():
    """Demonstrate turn detection concepts."""
    print("=== Turn Detection Concepts ===\n")

    test_cases = [
        ("Hello!", True, "Complete greeting with punctuation"),
        ("What do you think about", False, "Incomplete sentence, no ending"),
        ("I was wondering...", False, "Trailing ellipsis indicates continuation"),
        ("Can you help me with something?", True, "Complete question"),
        ("So yesterday I went to the store and", False, "Mid-sentence, no completion"),
        ("That's interesting.", True, "Complete statement"),
        ("hmm", False, "Single interjection, user might continue"),
        (
            "I need help with my code, specifically the login function",
            True,
            "Complete request",
        ),
    ]

    for text, is_complete, reason in test_cases:
        status = "COMPLETE" if is_complete else "WAITING"
        print(f'  [{status}] "{text}"')
        print(f"           Reason: {reason}")
        print()


async def demonstrate_memory_pattern():
    """Demonstrate memory sub-agent pattern."""
    print("=== Memory Sub-Agent Pattern ===\n")

    print("Memory structure for RP chatbot:")
    print("  memory/")
    print("  ├── character.md    [READ-ONLY]  - Character definition")
    print("  ├── rules.md        [PROTECTED]  - Agent rules")
    print("  ├── context.md      [WRITABLE]   - Current session context")
    print("  ├── facts.md        [WRITABLE]   - Learned facts about user")
    print("  └── preferences.md  [WRITABLE]   - User preferences")
    print()

    print("Memory operations flow:")
    print("  1. User mentions past event")
    print(
        '     → Controller dispatches: <agent type="memory_read">yesterday\'s topics</agent>'
    )
    print("  2. Memory agent searches memory files")
    print("  3. Returns relevant context to controller")
    print("  4. Controller includes in response dispatch")
    print()


async def demonstrate_response_flow():
    """Demonstrate response sub-agent flow."""
    print("=== Response Sub-Agent Flow ===\n")

    print('Flow for user message: "Hey Luna, how are you?"')
    print()
    print("1. Controller receives user input")
    print(
        "   └── Turn detection: Complete greeting (punctuation, addressing character)"
    )
    print()
    print("2. Controller decides no memory lookup needed")
    print()
    print("3. Controller dispatches to response agent:")
    print("   ┌────────────────────────────────────────")
    print('   │ <agent type="response">')
    print("   │ ## Character Context")
    print("   │ Luna: Friendly AI, curious personality")
    print("   │")
    print("   │ ## Conversation Context")
    print("   │ User greeted Luna, asking how she is")
    print("   │")
    print("   │ ## Task")
    print("   │ Respond warmly as Luna to the greeting")
    print("   │ </agent>")
    print("   └────────────────────────────────────────")
    print()
    print('4. Response agent generates: "Hey! I\'m doing great, thanks for asking."')
    print("   └── Streamed directly to user (low latency)")
    print()


async def demonstrate_architecture():
    """Show overall architecture diagram."""
    print("=== RP Chatbot Architecture ===\n")

    print(
        """
    ┌─────────────────────────────────────────────────────────────┐
    │                     USER INPUT                              │
    │              "Hey Luna, remember yesterday?"                │
    └─────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                    CONTROLLER                               │
    │  • Turn detection (user finished speaking?)                 │
    │  • Decide: need memory? dispatch to memory_read             │
    │  • Gather context for response agent                        │
    │  • Dispatch to response agent                               │
    └────────┬─────────────────────────────────────┬──────────────┘
             │                                     │
             ▼                                     ▼
    ┌─────────────────────┐               ┌─────────────────────┐
    │   MEMORY_READ       │               │   RESPONSE          │
    │   Sub-Agent         │               │   Sub-Agent         │
    │                     │               │                     │
    │  • Search memory    │               │  • Generate reply   │
    │  • Return context   │               │  • Stream to user   │
    └─────────────────────┘               └──────────┬──────────┘
                                                     │
                                                     ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                     USER OUTPUT                             │
    │           "Hey! Oh yeah, we talked about..."                │
    └─────────────────────────────────────────────────────────────┘
    """
    )


async def show_rp_agent_files():
    """Show RP agent configuration files."""
    print("=== RP Agent Files ===\n")

    rp_path = project_root / "agents" / "rp_agent"

    if rp_path.exists():
        print(f"RP Agent location: {rp_path}\n")

        # Show files
        for file_path in sorted(rp_path.rglob("*")):
            if file_path.is_file():
                rel_path = file_path.relative_to(rp_path)
                print(f"  {rel_path}")

        # Show character definition preview
        char_file = rp_path / "memory" / "character.md"
        if char_file.exists():
            print("\nCharacter definition preview:")
            print("-" * 40)
            with open(char_file) as f:
                lines = f.readlines()[:15]
                for line in lines:
                    print(f"  {line.rstrip()}")
            print("  ...")
            print("-" * 40)
    else:
        print("RP Agent not found. Run the full example to create it.")


async def main():
    load_env()

    print("=" * 60)
    print("KohakuTerrarium Phase 6: RP Chatbot Architecture Concept")
    print("=" * 60)
    print()

    await demonstrate_architecture()
    await demonstrate_turn_detection()
    await demonstrate_memory_pattern()
    await demonstrate_response_flow()
    await show_rp_agent_files()

    print("\n" + "=" * 60)
    print("This demonstrates the 'Controller as Orchestrator' pattern:")
    print("  • Controller: Fast decisions, minimal output")
    print("  • Memory agents: Background context management")
    print("  • Response agent: User-facing output (can stream)")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
