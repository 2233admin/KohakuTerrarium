"""
Phase 3/4 Test: Controller loop with tool execution

Run: python examples/phase3_controller.py

Expected:
- Controller receives TriggerEvent
- Batches stackable events
- Runs LLM and parses output
- Detects tool calls and executes them
- Tracks job status
- Handles ##read## command
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path

from kohakuterrarium.core import (
    Controller,
    ControllerConfig,
    Executor,
    JobState,
    JobStatus,
    JobType,
    Registry,
    TriggerEvent,
)
from kohakuterrarium.llm.openai import OPENROUTER_BASE_URL, OpenAIProvider
from kohakuterrarium.modules.tool import BashTool
from kohakuterrarium.parsing import TextEvent, ToolCallEvent
from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)


def load_env() -> None:
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


async def test_job_status():
    """Test job status tracking."""
    logger.info("=== Test 1: Job Status ===")

    from kohakuterrarium.core.job import JobStore, generate_job_id

    store = JobStore()

    # Create job
    job_id = generate_job_id("bash")
    status = JobStatus(
        job_id=job_id,
        job_type=JobType.TOOL,
        type_name="bash",
        state=JobState.RUNNING,
    )
    store.register(status)

    # Check status
    retrieved = store.get_status(job_id)
    assert retrieved is not None
    assert retrieved.is_running
    logger.info(f"Created job: {retrieved}")

    # Update status
    store.update_status(
        job_id,
        state=JobState.DONE,
        output_lines=5,
        output_bytes=100,
        preview="line1\nline2\nline3",
    )

    retrieved = store.get_status(job_id)
    assert retrieved is not None
    assert retrieved.is_complete
    logger.info(f"Updated job: {retrieved.to_context_string()}")


async def test_tool_execution():
    """Test direct tool execution."""
    logger.info("=== Test 2: Tool Execution ===")

    tool = BashTool()

    # Execute simple command
    result = await tool.execute({"command": "echo hello"})
    assert result.success
    assert "hello" in result.output.lower()
    logger.info(f"Tool output: {result.output.strip()}")


async def test_executor():
    """Test background executor."""
    logger.info("=== Test 3: Background Executor ===")

    executor = Executor()
    executor.register_tool(BashTool())

    # Submit job
    job_id = await executor.submit("bash", {"command": "echo background test"})
    logger.info(f"Submitted job: {job_id}")

    # Wait for completion
    result = await executor.wait_for(job_id, timeout=10.0)
    assert result is not None
    assert result.success
    logger.info(f"Job completed: {result.output.strip()}")

    # Check status
    status = executor.get_status(job_id)
    assert status is not None
    assert status.is_complete
    logger.info(f"Final status: {status}")


async def test_controller_basic():
    """Test basic controller operation."""
    logger.info("=== Test 4: Basic Controller ===")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set, skipping LLM test")
        return

    llm = OpenAIProvider(
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        model="openai/gpt-4o-mini",
    )

    config = ControllerConfig(
        system_prompt="""You are a test assistant.
When asked to run a command, output it in this format:
##tool##
name: bash
args:
  command: <the command>
##tool##

Keep responses brief.""",
    )

    controller = Controller(llm, config)

    # Push user event
    event = TriggerEvent(type="user_input", content="Say hello!")
    await controller.push_event(event)

    # Run once
    logger.info("Running controller...")
    print("Assistant: ", end="", flush=True)

    async for parse_event in controller.run_once():
        if isinstance(parse_event, TextEvent):
            print(parse_event.text, end="", flush=True)
        elif isinstance(parse_event, ToolCallEvent):
            print(f"\n[TOOL: {parse_event.name}]", flush=True)

    print()
    logger.info("Controller run complete")

    await llm.close()


async def test_controller_with_tools():
    """Test controller with tool execution."""
    logger.info("=== Test 5: Controller with Tools ===")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set, skipping LLM test")
        return

    llm = OpenAIProvider(
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        model="openai/gpt-4o-mini",
    )

    # Setup executor with bash tool
    executor = Executor()
    executor.register_tool(BashTool())

    # Setup registry
    registry = Registry()
    registry.register_tool(BashTool())

    config = ControllerConfig(
        system_prompt="""You are a coding assistant.
When you need to run a command, use:
##tool##
name: bash
args:
  command: <command here>
##tool##

After seeing the result, summarize what happened.""",
        include_tools_list=True,
    )

    controller = Controller(llm, config, executor=executor, registry=registry)

    # First turn - user asks to run a command
    logger.info("User: List files in current directory")
    event = TriggerEvent(
        type="user_input",
        content="List the files in the current directory using ls or dir",
    )
    await controller.push_event(event)

    print("Assistant: ", end="", flush=True)
    tool_call = None

    async for parse_event in controller.run_once():
        if isinstance(parse_event, TextEvent):
            print(parse_event.text, end="", flush=True)
        elif isinstance(parse_event, ToolCallEvent):
            print(f"\n[Detected tool: {parse_event.name}]", flush=True)
            tool_call = parse_event

    print()

    if tool_call:
        # Execute the tool
        job_id = await executor.submit_from_event(tool_call)
        logger.info(f"Submitted job: {job_id}")

        # Wait for result
        result = await executor.wait_for(job_id, timeout=10.0)
        if result:
            logger.info(f"Tool output ({result.output.count(chr(10)) + 1} lines)")

            # Push completion event
            completion = TriggerEvent(
                type="tool_complete",
                job_id=job_id,
                content=result.output[:500],
            )
            await controller.push_event(completion)

            # Second turn - controller sees result
            logger.info("Controller processing result...")
            print("Assistant: ", end="", flush=True)

            async for parse_event in controller.run_once():
                if isinstance(parse_event, TextEvent):
                    print(parse_event.text, end="", flush=True)

            print()
    else:
        logger.warning("No tool call detected")

    await llm.close()
    logger.info("Test complete")


async def main():
    load_env()

    logger.info("=" * 50)
    logger.info("Phase 3/4: Controller + Tool Execution")
    logger.info("=" * 50)

    # Offline tests
    await test_job_status()
    await test_tool_execution()
    await test_executor()

    # Online tests
    await test_controller_basic()
    await test_controller_with_tools()

    logger.info("=" * 50)
    logger.info("All Phase 3/4 tests completed!")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
