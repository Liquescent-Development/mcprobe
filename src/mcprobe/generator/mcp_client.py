"""MCP client for extracting tool schemas from MCP servers."""

from dataclasses import dataclass, field
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


@dataclass
class ToolSchema:
    """Extracted MCP tool schema."""

    name: str
    description: str | None
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None


@dataclass
class ServerTools:
    """Collection of tools from an MCP server."""

    tools: list[ToolSchema] = field(default_factory=list)
    server_name: str | None = None


async def extract_tools_from_server(server_command: str) -> ServerTools:
    """Extract tool schemas by connecting directly to MCP server.

    Args:
        server_command: Command to start server (e.g., "npx @example/weather-mcp")

    Returns:
        ServerTools containing all tool schemas from the server

    Raises:
        ValueError: If server_command is empty
        RuntimeError: If connection to server fails
    """
    if not server_command.strip():
        msg = "Server command cannot be empty"
        raise ValueError(msg)

    parts = server_command.split()
    command = parts[0]
    args = parts[1:] if len(parts) > 1 else []

    server_params = StdioServerParameters(command=command, args=args)

    async with (
        stdio_client(server_params) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        result = await session.list_tools()

        tools = [
            ToolSchema(
                name=tool.name,
                description=tool.description,
                input_schema=tool.inputSchema,
                output_schema=getattr(tool, "outputSchema", None),
            )
            for tool in result.tools
        ]

        return ServerTools(tools=tools)
