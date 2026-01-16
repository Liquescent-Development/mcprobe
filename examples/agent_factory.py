"""Example agent factory for mcprobe ADK testing.

This module demonstrates how to create a Gemini ADK agent that connects
to an MCP server for use with mcprobe.

Usage:
    mcprobe run scenario.yaml -t adk -f examples/agent_factory.py

Environment variables:
    MCP_URL: MCP server URL (default: http://localhost:8080/mcp)
    MCP_TOKEN: Bearer token for auth (default: dev)
    GEMINI_MODEL: Model name (default: gemini-2.0-flash)
    GOOGLE_API_KEY: Google API key for Gemini (required)
"""

import os

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.genai.types import GenerateContentConfig


def create_agent() -> LlmAgent:
    """Create a Gemini ADK agent connected to an MCP server.

    Returns:
        Configured LlmAgent instance ready for use with mcprobe.

    Raises:
        ValueError: If required environment variables are not set.
    """
    # Check for required API key
    if not os.environ.get("GOOGLE_API_KEY"):
        msg = "GOOGLE_API_KEY environment variable is required"
        raise ValueError(msg)

    # Get configuration from environment
    mcp_url = os.environ.get("MCP_URL", "http://localhost:8080/mcp")
    mcp_token = os.environ.get("MCP_TOKEN", "dev")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

    # Build MCP connection parameters
    connection_params = StreamableHTTPConnectionParams(
        url=mcp_url,
        headers={"Authorization": f"Bearer {mcp_token}"},
    )

    # Create toolset that connects to MCP server
    toolset = McpToolset(connection_params=connection_params)

    # Create and return the agent
    return LlmAgent(
        model=model,
        name="mcprobe_test_agent",
        description="Test agent for MCP server validation",
        instruction=(
            "You are a helpful assistant with access to tools. "
            "Use the available tools to help answer questions accurately. "
            "Always prefer using tools when they can provide more accurate information."
        ),
        tools=[toolset],
        generate_content_config=GenerateContentConfig(
            temperature=0.1,
            top_p=0.9,
        ),
    )
