"""MCP client for extracting tool schemas from MCP servers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import StdioServerParameters, stdio_client

if TYPE_CHECKING:
    from mcprobe.config.loader import MCPServerConfig


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


async def extract_tools_from_http(
    url: str,
    headers: dict[str, Any] | None = None,
) -> ServerTools:
    """Extract tool schemas from HTTP-based MCP server.

    Args:
        url: URL of the MCP server SSE endpoint (e.g., "http://localhost:8080/mcp")
        headers: Optional headers to include in requests (e.g., for authentication)

    Returns:
        ServerTools containing all tool schemas from the server

    Raises:
        ValueError: If URL is empty
        RuntimeError: If connection to server fails
    """
    if not url.strip():
        msg = "Server URL cannot be empty"
        raise ValueError(msg)

    async with (
        sse_client(url, headers=headers) as (read_stream, write_stream),
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


async def extract_tools(config: MCPServerConfig) -> ServerTools:
    """Extract tools from MCP server using appropriate connection method.

    Supports both stdio (command-based) and HTTP (URL-based) connections.

    Args:
        config: MCP server configuration with either command or url set.

    Returns:
        ServerTools containing all tool schemas from the server.
        Returns empty ServerTools if no connection method is configured.
    """
    if config.command:
        return await extract_tools_from_server(config.command)
    elif config.url:
        return await extract_tools_from_http(config.url, headers=config.headers)
    return ServerTools(tools=[])
