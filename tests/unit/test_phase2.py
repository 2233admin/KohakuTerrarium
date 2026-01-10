"""
Phase 2 Unit Tests - Stream Parsing

Tests for:
- ParseEvent types
- Pattern parsing (YAML-like)
- StreamParser state machine
- Tool, sub-agent, and command detection

These tests run offline without API keys.
"""

import pytest

from kohakuterrarium.parsing import (
    BlockPattern,
    CommandEvent,
    ParserConfig,
    ParserState,
    StreamParser,
    SubAgentCallEvent,
    TextEvent,
    ToolCallEvent,
    extract_subagent_calls,
    extract_text,
    extract_tool_calls,
    is_action_event,
    is_text_event,
    parse_command,
    parse_complete,
    parse_tool_content,
    parse_yaml_like,
)


class TestParseEvents:
    """Tests for ParseEvent types."""

    def test_text_event(self):
        """Test TextEvent creation."""
        event = TextEvent("hello")
        assert event.text == "hello"
        assert bool(event) is True

        empty = TextEvent("")
        assert bool(empty) is False

    def test_tool_call_event(self):
        """Test ToolCallEvent creation."""
        event = ToolCallEvent(name="bash", args={"command": "ls"})
        assert event.name == "bash"
        assert event.args["command"] == "ls"

    def test_subagent_call_event(self):
        """Test SubAgentCallEvent creation."""
        event = SubAgentCallEvent(name="explore", args={"query": "test"})
        assert event.name == "explore"
        assert event.args["query"] == "test"

    def test_command_event(self):
        """Test CommandEvent creation."""
        event = CommandEvent(command="read", args="job_123 --lines 50")
        assert event.command == "read"
        assert "job_123" in event.args

    def test_is_action_event(self):
        """Test is_action_event helper."""
        assert is_action_event(ToolCallEvent("test", {}))
        assert is_action_event(SubAgentCallEvent("test", {}))
        assert is_action_event(CommandEvent("test"))
        assert not is_action_event(TextEvent("hello"))

    def test_is_text_event(self):
        """Test is_text_event helper."""
        assert is_text_event(TextEvent("hello"))
        assert not is_text_event(ToolCallEvent("test", {}))


class TestYamlLikeParsing:
    """Tests for YAML-like content parsing."""

    def test_simple_key_value(self):
        """Test simple key: value parsing."""
        content = "name: bash\ncommand: ls -la"
        result = parse_yaml_like(content)
        assert result["name"] == "bash"
        assert result["command"] == "ls -la"

    def test_multiline_value(self):
        """Test multi-line value parsing."""
        content = """name: test
description: This is
  a multi-line
  description"""
        result = parse_yaml_like(content)
        assert result["name"] == "test"
        assert "multi-line" in result["description"]

    def test_nested_args(self):
        """Test nested args parsing."""
        content = """name: bash
args:
  command: ls
  flags: -la"""
        result = parse_yaml_like(content)
        assert result["name"] == "bash"
        assert "command: ls" in result["args"]

    def test_parse_tool_content(self):
        """Test parse_tool_content function."""
        content = """name: bash
args:
  command: echo hello"""
        name, args = parse_tool_content(content)
        assert name == "bash"
        assert args.get("command") == "echo hello"

    def test_parse_command(self):
        """Test parse_command function."""
        command, args = parse_command("##read job_123 --lines 50##")
        assert command == "read"
        assert "job_123" in args
        assert "--lines 50" in args


class TestBlockPattern:
    """Tests for BlockPattern."""

    def test_simple_pattern(self):
        """Test simple block pattern."""
        pattern = BlockPattern(start="##tool##", end="##tool##")
        assert pattern.matches_start("##tool##")
        assert not pattern.matches_start("##other##")

    def test_name_in_start_pattern(self):
        """Test pattern with name in start marker."""
        pattern = BlockPattern(
            start="##subagent:",
            end="##subagent##",
            name_in_start=True,
        )
        name = pattern.extract_name_from_start("##subagent:explore##")
        assert name == "explore"


class TestStreamParser:
    """Tests for StreamParser."""

    def test_empty_input(self):
        """Test parser with empty input."""
        parser = StreamParser()
        events = parser.feed("")
        events.extend(parser.flush())
        assert len(events) == 0

    def test_text_only(self):
        """Test parser with text only (no blocks)."""
        parser = StreamParser()
        events = parser.feed("Hello world!")
        events.extend(parser.flush())

        text = extract_text(events)
        assert "Hello world!" in text

    def test_single_tool_call(self):
        """Test parsing a single tool call."""
        text = """Some text before.

##tool##
name: bash
args:
  command: ls -la
##tool##

Some text after."""

        events = parse_complete(text)
        tools = extract_tool_calls(events)

        assert len(tools) == 1
        assert tools[0].name == "bash"
        assert tools[0].args.get("command") == "ls -la"

    def test_multiple_tool_calls(self):
        """Test parsing multiple tool calls."""
        text = """##tool##
name: tool1
##tool##

##tool##
name: tool2
##tool##"""

        events = parse_complete(text)
        tools = extract_tool_calls(events)

        assert len(tools) == 2
        assert tools[0].name == "tool1"
        assert tools[1].name == "tool2"

    def test_subagent_call(self):
        """Test parsing sub-agent call."""
        text = """##subagent:explore##
query: find files
##subagent##"""

        events = parse_complete(text)
        subagents = extract_subagent_calls(events)

        assert len(subagents) == 1
        assert subagents[0].name == "explore"
        assert subagents[0].args.get("query") == "find files"

    def test_command(self):
        """Test parsing framework command."""
        text = "Check this: ##read job_123##"

        events = parse_complete(text)
        commands = [e for e in events if isinstance(e, CommandEvent)]

        assert len(commands) == 1
        assert commands[0].command == "read"
        assert "job_123" in commands[0].args

    def test_streaming_chunks(self):
        """Test that streaming works correctly."""
        parser = StreamParser()

        # Feed in small chunks
        chunks = ["##to", "ol##\nna", "me: test\n##tool##"]

        all_events = []
        for chunk in chunks:
            events = parser.feed(chunk)
            all_events.extend(events)
        all_events.extend(parser.flush())

        tools = extract_tool_calls(all_events)
        assert len(tools) == 1
        assert tools[0].name == "test"

    def test_character_by_character(self):
        """Test feeding character by character."""
        text = "##tool##\nname: test\n##tool##"
        parser = StreamParser()

        all_events = []
        for char in text:
            events = parser.feed(char)
            all_events.extend(events)
        all_events.extend(parser.flush())

        tools = extract_tool_calls(all_events)
        assert len(tools) == 1

    def test_parser_state(self):
        """Test parser state tracking."""
        parser = StreamParser()

        assert parser.get_state() == ParserState.NORMAL
        assert not parser.is_in_block()

        parser.feed("##tool##\n")
        assert parser.is_in_block()

        parser.feed("name: test\n##tool##")
        parser.flush()
        assert parser.get_state() == ParserState.NORMAL

    def test_incomplete_block(self):
        """Test handling of incomplete block at stream end."""
        parser = StreamParser()

        events = parser.feed("##tool##\nname: test")
        # No tool event yet (block not closed)
        tools = extract_tool_calls(events)
        assert len(tools) == 0

        # Flush should handle incomplete block
        final_events = parser.flush()
        # Still no tool event (incomplete)
        tools = extract_tool_calls(final_events)
        assert len(tools) == 0

    def test_false_marker(self):
        """Test that false markers are handled as text."""
        text = "Use # for comments and ## for headers"

        events = parse_complete(text)
        text_content = extract_text(events)

        assert "#" in text_content or "##" in text_content

    def test_mixed_content(self):
        """Test response with all content types."""
        text = """Text before

##tool##
name: tool1
##tool##

##subagent:agent1##
query: test
##subagent##

##read job_1##

Text after"""

        events = parse_complete(text)

        tools = extract_tool_calls(events)
        subagents = extract_subagent_calls(events)
        commands = [e for e in events if isinstance(e, CommandEvent)]

        assert len(tools) == 1
        assert len(subagents) == 1
        assert len(commands) == 1


class TestParserConfig:
    """Tests for ParserConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = ParserConfig()
        assert config.tool_pattern.start == "##tool##"
        assert config.subagent_pattern.start == "##subagent:"
        assert config.emit_block_events is False

    def test_custom_config(self):
        """Test custom configuration."""
        config = ParserConfig(
            emit_block_events=True,
            buffer_text=False,
        )
        assert config.emit_block_events is True
        assert config.buffer_text is False


class TestExtractFunctions:
    """Tests for extraction helper functions."""

    def test_extract_tool_calls(self):
        """Test extract_tool_calls function."""
        events = [
            TextEvent("hello"),
            ToolCallEvent("tool1", {}),
            TextEvent("world"),
            ToolCallEvent("tool2", {}),
        ]

        tools = extract_tool_calls(events)
        assert len(tools) == 2
        assert tools[0].name == "tool1"
        assert tools[1].name == "tool2"

    def test_extract_subagent_calls(self):
        """Test extract_subagent_calls function."""
        events = [
            TextEvent("hello"),
            SubAgentCallEvent("agent1", {}),
        ]

        subagents = extract_subagent_calls(events)
        assert len(subagents) == 1
        assert subagents[0].name == "agent1"

    def test_extract_text(self):
        """Test extract_text function."""
        events = [
            TextEvent("Hello "),
            ToolCallEvent("tool", {}),
            TextEvent("World"),
        ]

        text = extract_text(events)
        assert text == "Hello World"
