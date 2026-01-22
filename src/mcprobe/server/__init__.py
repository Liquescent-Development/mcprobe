"""MCP server for MCProbe results and control.

Exposes MCProbe test results, analysis, and control capabilities
via Model Context Protocol for integration with AI assistants.
"""

from mcprobe.server.server import create_server, run_server

__all__ = ["create_server", "run_server"]
