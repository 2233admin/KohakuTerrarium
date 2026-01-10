"""
Phase 1 Test: Basic LLM streaming with conversation + logging

Run: python examples/phase1_basic_llm.py

Expected:
- Logger outputs colored, formatted messages
- Connect to OpenRouter API (OpenAI-compatible)
- Send a simple message
- Stream response tokens to terminal
- Verify conversation history works

Prerequisites:
- Create .env file with OPENROUTER_API_KEY=your-key
- pip install -e .[dev]
"""

import asyncio
import os
import sys
from pathlib import Path

from kohakuterrarium.core.conversation import Conversation
from kohakuterrarium.core.events import TriggerEvent
from kohakuterrarium.llm.openai import OPENROUTER_BASE_URL, OpenAIProvider
from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)


def load_env() -> None:
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        logger.debug("Loading .env file", path=str(env_path))
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


async def test_logging():
    """Test logger output."""
    logger.info("=== Test 0: Logging ===")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.info("Logger test complete", extra_field="extra_value")


async def test_basic_streaming():
    """Test basic LLM streaming."""
    logger.info("=== Test 1: Basic Streaming ===")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")

    provider = OpenAIProvider(
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        model="openai/gpt-5-mini",  # OpenRouter model format
    )

    messages = [
        {"role": "system", "content": "You are helpful. Be brief."},
        {"role": "user", "content": "Say 'Hello World' and nothing else."},
    ]

    logger.info("Sending request to OpenRouter...")
    chunks = []
    async for chunk in provider.chat(messages, stream=True):
        # For streaming output, we print directly (this is user-facing output)
        print(chunk, end="", flush=True)
        chunks.append(chunk)
    print()  # newline after streaming

    full_response = "".join(chunks)
    assert len(full_response) > 0, "Expected non-empty response"
    logger.info(f"Received {len(chunks)} chunks, {len(full_response)} chars total")

    await provider.close()


async def test_conversation_class():
    """Test Conversation class."""
    logger.info("=== Test 2: Conversation Class ===")

    conv = Conversation()

    # Add messages
    conv.append("system", "You are a helpful assistant.")
    conv.append("user", "Hello!")
    conv.append("assistant", "Hi there! How can I help?")
    conv.append("user", "What is 2+2?")

    messages = conv.to_messages()
    assert len(messages) == 4, f"Expected 4 messages, got {len(messages)}"

    logger.info(f"Conversation has {len(messages)} messages")
    logger.info(f"Context length: {conv.get_context_length()} chars")

    # Test message format
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    logger.info("Message format verified")

    # Test serialization
    json_str = conv.to_json()
    restored = Conversation.from_json(json_str)
    assert len(restored) == len(conv), "Serialization round-trip failed"
    logger.info("Serialization test passed")


async def test_trigger_event():
    """Test TriggerEvent creation."""
    logger.info("=== Test 3: TriggerEvent ===")

    # Basic event
    event = TriggerEvent(type="user_input", content="Hello!")
    assert event.type == "user_input"
    assert event.content == "Hello!"
    assert event.stackable is True
    logger.info(f"Created event: type={event.type}, stackable={event.stackable}")

    # Event with context
    event2 = TriggerEvent(
        type="tool_complete",
        content="Command output here",
        job_id="job_123",
        context={"exit_code": 0},
    )
    assert event2.job_id == "job_123"
    assert event2.context["exit_code"] == 0
    logger.info(f"Event with context: job_id={event2.job_id}")

    # Test with_context method
    event3 = event2.with_context(extra_info="test")
    assert event3.context["exit_code"] == 0
    assert event3.context["extra_info"] == "test"
    logger.info("with_context method works")


async def test_full_conversation_flow():
    """Test full conversation with LLM."""
    logger.info("=== Test 4: Full Conversation Flow ===")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")

    provider = OpenAIProvider(
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        model="openai/gpt-5-mini",
    )
    conv = Conversation()

    # System setup
    conv.append("system", "You are a helpful assistant. Keep responses brief.")

    # Simulate user input via TriggerEvent
    event = TriggerEvent(type="user_input", content="What is 2+2?")
    conv.append("user", event.content)

    # Get response
    logger.info("User: What is 2+2?")
    print("Assistant: ", end="", flush=True)

    full_response = ""
    async for chunk in provider.chat(conv.to_messages(), stream=True):
        print(chunk, end="", flush=True)
        full_response += chunk
    print()

    # Add assistant response
    conv.append("assistant", full_response)

    # Verify state
    messages = conv.to_messages()
    assert len(messages) == 3
    assert messages[-1]["role"] == "assistant"
    logger.info(f"Conversation updated, now {len(messages)} messages")

    # Follow-up
    event2 = TriggerEvent(type="user_input", content="Add 3 to that")
    conv.append("user", event2.content)

    logger.info("User: Add 3 to that")
    print("Assistant: ", end="", flush=True)

    async for chunk in provider.chat(conv.to_messages(), stream=True):
        print(chunk, end="", flush=True)
    print()

    logger.info("Multi-turn conversation working!")

    await provider.close()


async def main():
    load_env()

    logger.info("=" * 50)
    logger.info("Phase 1: LLM + Events + Conversation + Logging")
    logger.info("=" * 50)

    # Always test logging first
    await test_logging()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set!")
        logger.info("Create .env file with: OPENROUTER_API_KEY=your-key")
        logger.info("Running offline tests only...")

        await test_conversation_class()
        await test_trigger_event()
        logger.info("Offline tests passed!")
        return

    await test_basic_streaming()
    await test_conversation_class()
    await test_trigger_event()
    await test_full_conversation_flow()

    logger.info("=" * 50)
    logger.info("All Phase 1 tests passed!")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
