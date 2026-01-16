"""Tests for MCP client module."""

import pytest

from mcprobe.generator.mcp_client import (
    ServerTools,
    ToolSchema,
    extract_tools_from_server,
)


class TestToolSchema:
    """Tests for ToolSchema dataclass."""

    def test_minimal_tool_schema(self) -> None:
        """Test creating a tool schema with minimal fields."""
        schema = ToolSchema(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {}},
        )

        assert schema.name == "test_tool"
        assert schema.description == "A test tool"
        assert schema.input_schema == {"type": "object", "properties": {}}
        assert schema.output_schema is None

    def test_full_tool_schema(self) -> None:
        """Test creating a tool schema with all fields."""
        input_schema = {
            "type": "object",
            "properties": {
                "param1": {"type": "string"},
                "param2": {"type": "integer"},
            },
            "required": ["param1"],
        }
        output_schema = {"type": "object", "properties": {"result": {"type": "string"}}}

        schema = ToolSchema(
            name="full_tool",
            description="A fully specified tool",
            input_schema=input_schema,
            output_schema=output_schema,
        )

        assert schema.name == "full_tool"
        assert schema.output_schema == output_schema
        assert "param1" in schema.input_schema["properties"]

    def test_tool_schema_with_none_description(self) -> None:
        """Test creating a tool schema with None description."""
        schema = ToolSchema(
            name="no_desc_tool",
            description=None,
            input_schema={},
        )

        assert schema.name == "no_desc_tool"
        assert schema.description is None


class TestServerTools:
    """Tests for ServerTools dataclass."""

    def test_empty_server_tools(self) -> None:
        """Test creating empty server tools."""
        tools = ServerTools()

        assert tools.tools == []
        assert tools.server_name is None

    def test_server_tools_with_tools(self) -> None:
        """Test creating server tools with tool list."""
        tool1 = ToolSchema(name="tool1", description="First tool", input_schema={})
        tool2 = ToolSchema(name="tool2", description="Second tool", input_schema={})

        tools = ServerTools(tools=[tool1, tool2], server_name="test_server")

        assert len(tools.tools) == 2
        assert tools.tools[0].name == "tool1"
        assert tools.tools[1].name == "tool2"
        assert tools.server_name == "test_server"


class TestExtractToolsFromServer:
    """Tests for extract_tools_from_server function."""

    @pytest.mark.asyncio
    async def test_empty_command_raises_error(self) -> None:
        """Test that empty server command raises ValueError."""
        with pytest.raises(ValueError, match="Server command cannot be empty"):
            await extract_tools_from_server("")

        with pytest.raises(ValueError, match="Server command cannot be empty"):
            await extract_tools_from_server("   ")
