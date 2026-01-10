"""
Phase 2 Test: Stream parsing for tool calls

Run: python examples/phase2_parsing.py

Expected:
- Parser detects ##tool## blocks while streaming
- Text outside blocks emitted as TextEvent
- Complete tool blocks emitted as ToolCallEvent
- Handles partial chunks correctly
- Detects sub-agent calls and commands
"""

import asyncio

from kohakuterrarium.parsing import (
    CommandEvent,
    ParserConfig,
    StreamParser,
    SubAgentCallEvent,
    TextEvent,
    ToolCallEvent,
    extract_tool_calls,
    parse_complete,
)
from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)


def test_basic_parsing():
    """Test parsing a complete response with tool call."""
    logger.info("=== Test 1: Basic Tool Parsing ===")

    parser = StreamParser()

    # Simulate streaming chunks
    chunks = [
        "Let me check ",
        "that for you.\n\n",
        "##tool##\n",
        "name: bash\n",
        "args:\n",
        "  command: ls -la\n",
        "##tool##\n\n",
        "I'll run that command.",
    ]

    all_events = []
    for chunk in chunks:
        events = parser.feed(chunk)
        all_events.extend(events)
    all_events.extend(parser.flush())

    # Verify events
    text_events = [e for e in all_events if isinstance(e, TextEvent)]
    tool_events = [e for e in all_events if isinstance(e, ToolCallEvent)]

    assert len(tool_events) == 1, f"Expected 1 tool call, got {len(tool_events)}"
    assert tool_events[0].name == "bash"
    assert tool_events[0].args.get("command") == "ls -la"

    logger.info(f"Detected tool call: {tool_events[0].name}")
    logger.info(f"Args: {tool_events[0].args}")
    logger.info(f"Text events: {len(text_events)}")


def test_partial_chunks():
    """Test that partial tool markers are handled correctly."""
    logger.info("=== Test 2: Partial Chunks ===")

    parser = StreamParser()

    # Split marker across chunks
    chunks = ["Some text #", "#too", "l##\nname: test\n##tool##"]

    all_events = []
    for chunk in chunks:
        events = parser.feed(chunk)
        all_events.extend(events)
    all_events.extend(parser.flush())

    tool_events = [e for e in all_events if isinstance(e, ToolCallEvent)]
    assert len(tool_events) == 1, f"Expected 1 tool call, got {len(tool_events)}"
    assert tool_events[0].name == "test"
    logger.info("Handles split markers correctly")


def test_multiple_tools():
    """Test multiple tool calls in one response."""
    logger.info("=== Test 3: Multiple Tools ===")

    response = """I'll search and then fetch.

##tool##
name: web_search
args:
  query: python async
##tool##

##tool##
name: web_fetch
args:
  url: https://example.com
##tool##

Done!"""

    events = parse_complete(response)

    tool_events = extract_tool_calls(events)
    assert len(tool_events) == 2, f"Expected 2 tools, got {len(tool_events)}"
    assert tool_events[0].name == "web_search"
    assert tool_events[1].name == "web_fetch"
    logger.info(f"Detected {len(tool_events)} tool calls")


def test_subagent_parsing():
    """Test sub-agent call parsing."""
    logger.info("=== Test 4: Sub-agent Parsing ===")

    response = """Let me explore that.

##subagent:explore##
query: find authentication files
max_depth: 3
##subagent##

I'll check the results."""

    events = parse_complete(response)

    subagent_events = [e for e in events if isinstance(e, SubAgentCallEvent)]
    assert len(subagent_events) == 1
    assert subagent_events[0].name == "explore"
    assert subagent_events[0].args.get("query") == "find authentication files"
    logger.info(f"Detected sub-agent: {subagent_events[0].name}")
    logger.info(f"Args: {subagent_events[0].args}")


def test_command_parsing():
    """Test framework command parsing."""
    logger.info("=== Test 5: Command Parsing ===")

    response = "Let me check the job output: ##read job_123 --lines 50##"

    events = parse_complete(response)

    cmd_events = [e for e in events if isinstance(e, CommandEvent)]
    assert len(cmd_events) == 1
    assert cmd_events[0].command == "read"
    assert "job_123" in cmd_events[0].args
    logger.info(f"Detected command: {cmd_events[0].command}")
    logger.info(f"Args: {cmd_events[0].args}")


def test_mixed_content():
    """Test response with mixed content types."""
    logger.info("=== Test 6: Mixed Content ===")

    response = """I'll help you with that task.

First, let me search:

##tool##
name: search
args:
  query: test
##tool##

Now checking with explore agent:

##subagent:explore##
path: ./src
##subagent##

Let me read the results: ##read search_001##

All done!"""

    events = parse_complete(response)

    text_events = [e for e in events if isinstance(e, TextEvent)]
    tool_events = [e for e in events if isinstance(e, ToolCallEvent)]
    subagent_events = [e for e in events if isinstance(e, SubAgentCallEvent)]
    cmd_events = [e for e in events if isinstance(e, CommandEvent)]

    logger.info(f"Text events: {len(text_events)}")
    logger.info(f"Tool calls: {len(tool_events)}")
    logger.info(f"Sub-agent calls: {len(subagent_events)}")
    logger.info(f"Commands: {len(cmd_events)}")

    assert len(tool_events) == 1
    assert len(subagent_events) == 1
    assert len(cmd_events) == 1


def test_streaming_simulation():
    """Simulate real streaming with small chunks."""
    logger.info("=== Test 7: Streaming Simulation ===")

    full_response = """Thinking...

##tool##
name: bash
args:
  command: echo hello
##tool##

Done!"""

    # Simulate streaming with small random-ish chunks
    parser = StreamParser()
    all_events = []

    # Feed character by character (extreme case)
    for char in full_response:
        events = parser.feed(char)
        all_events.extend(events)
    all_events.extend(parser.flush())

    tool_events = extract_tool_calls(all_events)
    assert len(tool_events) == 1
    assert tool_events[0].name == "bash"
    logger.info("Character-by-character streaming works")


async def test_with_llm():
    """Test parsing real LLM output (requires API key)."""
    import os
    from pathlib import Path

    logger.info("=== Test 8: Real LLM Output ===")

    # Load env
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set, skipping LLM test")
        return

    from kohakuterrarium.llm.openai import OPENROUTER_BASE_URL, OpenAIProvider

    provider = OpenAIProvider(
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        model="openai/gpt-4o-mini",
    )

    messages = [
        {
            "role": "system",
            "content": """You are a test assistant. When asked to run a command, output it in this exact format:

##tool##
name: bash
args:
  command: <the command>
##tool##

Keep other text brief.""",
        },
        {"role": "user", "content": "Please run the 'ls' command"},
    ]

    parser = StreamParser()
    all_events = []

    logger.info("Sending request to LLM...")
    print("Response: ", end="", flush=True)

    async for chunk in provider.chat(messages, stream=True):
        print(chunk, end="", flush=True)
        events = parser.feed(chunk)
        all_events.extend(events)

    all_events.extend(parser.flush())
    print()

    tool_events = extract_tool_calls(all_events)
    if tool_events:
        logger.info(f"Detected {len(tool_events)} tool call(s) from LLM")
        for te in tool_events:
            logger.info(f"  - {te.name}: {te.args}")
    else:
        logger.warning("No tool calls detected in LLM response")

    await provider.close()


def main():
    logger.info("=" * 50)
    logger.info("Phase 2: Stream Parsing")
    logger.info("=" * 50)

    # Offline tests
    test_basic_parsing()
    test_partial_chunks()
    test_multiple_tools()
    test_subagent_parsing()
    test_command_parsing()
    test_mixed_content()
    test_streaming_simulation()

    # Online test
    asyncio.run(test_with_llm())

    logger.info("=" * 50)
    logger.info("All Phase 2 tests passed!")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
