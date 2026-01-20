# Gemini ADK Agent Guide

## Overview

The **Gemini ADK Agent** integrates Google's Agent Development Kit (ADK) with MCProbe to test agents that use MCP (Model Context Protocol) tools. This agent type enables full-stack testing of conversational AI systems with real tool integration.

## What is Gemini ADK?

[Google ADK](https://github.com/google/adk) is a framework for building AI agents with:

- **LlmAgent** - Conversational agent orchestration
- **MCP Integration** - Connect to MCP tool servers via HTTP
- **Session Management** - Maintain conversation state
- **Tool Execution** - Automatic tool calling and result handling

MCProbe wraps ADK's `LlmAgent` to enable testing with synthetic users and automated evaluation.

## Prerequisites

### 1. Install MCProbe with ADK Support

```bash
# Install with ADK extras
pip install mcprobe[adk]

# Or install manually
pip install mcprobe google-adk
```

### 2. Get Google API Key

ADK agents use Gemini models which require a Google API key:

```bash
# Get key from: https://aistudio.google.com/apikey
export GOOGLE_API_KEY="your-api-key-here"
```

### 3. Set Up MCP Server

Your agent will connect to an MCP server:

```bash
# Example: Run your MCP server
./run_mcp_server --port 8080

# Or use environment variable
export MCP_URL="http://localhost:8080/mcp"
```

## How it Works

### Architecture

```
┌─────────────────┐
│   MCProbe       │
│  Orchestrator   │
└────────┬────────┘
         │
         v
┌─────────────────┐      ┌──────────────┐
│ GeminiADKAgent  │─────>│  LlmAgent    │
│   (wrapper)     │      │  (ADK)       │
└─────────────────┘      └──────┬───────┘
                                │
                                v
                         ┌──────────────┐
                         │  McpToolset  │
                         └──────┬───────┘
                                │
                                v
                         ┌──────────────┐
                         │  MCP Server  │
                         │  (via HTTP)  │
                         └──────────────┘
```

### Integration Flow

1. **MCProbe** sends user message to `GeminiADKAgent`
2. **GeminiADKAgent** forwards to ADK's `LlmAgent` via `Runner`
3. **LlmAgent** decides whether to call tools
4. If tools needed, **McpToolset** sends HTTP requests to MCP server
5. **MCP server** executes tools and returns results
6. **LlmAgent** uses results to generate final response
7. **GeminiADKAgent** tracks tool calls and returns to MCProbe

## Creating an Agent Factory

ADK agents require a **factory module** - a Python file with a `create_agent()` function that returns a configured `LlmAgent`.

### Basic Agent Factory

Create a file named `agent_factory.py`:

```python
"""Agent factory for MCProbe testing."""

import os
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.genai.types import GenerateContentConfig


def create_agent() -> LlmAgent:
    """Create a Gemini ADK agent connected to MCP server.

    Returns:
        Configured LlmAgent instance.

    Raises:
        ValueError: If required environment variables are not set.
    """
    # Validate environment
    if not os.environ.get("GOOGLE_API_KEY"):
        raise ValueError("GOOGLE_API_KEY environment variable is required")

    # Get MCP server configuration
    mcp_url = os.environ.get("MCP_URL", "http://localhost:8080/mcp")
    mcp_token = os.environ.get("MCP_TOKEN", "dev")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

    # Configure MCP connection
    connection_params = StreamableHTTPConnectionParams(
        url=mcp_url,
        headers={"Authorization": f"Bearer {mcp_token}"},
    )

    # Create MCP toolset
    toolset = McpToolset(connection_params=connection_params)

    # Create and configure agent
    return LlmAgent(
        model=model,
        name="weather_assistant",
        description="Assistant that helps with weather information",
        instruction=(
            "You are a helpful weather assistant. "
            "Use the available weather tools to provide accurate information. "
            "Always specify the location when checking weather."
        ),
        tools=[toolset],
        generate_content_config=GenerateContentConfig(
            temperature=0.1,  # Low temperature for consistent behavior
            top_p=0.9,
        ),
    )
```

### Factory Configuration Options

#### LlmAgent Parameters

```python
LlmAgent(
    model: str,                    # Gemini model name
    name: str,                     # Agent identifier
    description: str,              # Agent description
    instruction: str,              # System-level instructions
    tools: list[McpToolset],       # MCP toolsets
    generate_content_config: GenerateContentConfig,  # Generation settings
)
```

**Common Models:**
- `gemini-2.0-flash` - Fast, efficient (recommended for testing)
- `gemini-2.0-pro` - More capable, slower
- `gemini-1.5-flash` - Previous generation, fast
- `gemini-1.5-pro` - Previous generation, capable

#### GenerateContentConfig

```python
from google.genai.types import GenerateContentConfig

config = GenerateContentConfig(
    temperature=0.1,      # 0.0 = deterministic, 1.0 = creative
    top_p=0.9,           # Nucleus sampling
    top_k=40,            # Top-k sampling
    max_output_tokens=2048,  # Response length limit
)
```

**Testing Recommendations:**
- Use low temperature (0.1-0.3) for predictable behavior
- Higher top_p (0.9) for better reasoning
- Adjust max_output_tokens based on expected response length

#### MCP Connection Parameters

```python
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StreamableHTTPConnectionParams
)

connection_params = StreamableHTTPConnectionParams(
    url="http://localhost:8080/mcp",  # MCP server endpoint
    headers={
        "Authorization": "Bearer dev",  # Authentication
        "X-Custom-Header": "value",     # Additional headers
    },
    timeout=30,  # Request timeout in seconds
)
```

## Complete Working Example

Here's a production-ready agent factory with error handling and documentation:

```python
"""Production agent factory for weather MCP server testing.

Environment Variables:
    GOOGLE_API_KEY: Google API key for Gemini (required)
    MCP_URL: MCP server URL (default: http://localhost:8080/mcp)
    MCP_TOKEN: Bearer token for auth (default: dev)
    GEMINI_MODEL: Model name (default: gemini-2.0-flash)
    AGENT_TEMPERATURE: Temperature 0.0-1.0 (default: 0.1)

Usage:
    export GOOGLE_API_KEY="your-key"
    export MCP_URL="http://localhost:8080/mcp"
    mcprobe run scenario.yaml -t adk -f agent_factory.py
"""

import os
import sys
from typing import NoReturn

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StreamableHTTPConnectionParams,
)
from google.genai.types import GenerateContentConfig


def _get_required_env(name: str) -> str:
    """Get required environment variable or exit."""
    value = os.environ.get(name)
    if not value:
        _error(f"{name} environment variable is required")
    return value


def _error(message: str) -> NoReturn:
    """Print error and exit."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def create_agent() -> LlmAgent:
    """Create a Gemini ADK agent for weather MCP server testing.

    Returns:
        Configured LlmAgent instance ready for MCProbe testing.

    Raises:
        SystemExit: If required environment variables are missing.
    """
    # Get required configuration
    api_key = _get_required_env("GOOGLE_API_KEY")

    # Get optional configuration with defaults
    mcp_url = os.environ.get("MCP_URL", "http://localhost:8080/mcp")
    mcp_token = os.environ.get("MCP_TOKEN", "dev")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    temperature = float(os.environ.get("AGENT_TEMPERATURE", "0.1"))

    # Configure MCP connection
    connection_params = StreamableHTTPConnectionParams(
        url=mcp_url,
        headers={"Authorization": f"Bearer {mcp_token}"},
        timeout=30,
    )

    # Create MCP toolset
    toolset = McpToolset(connection_params=connection_params)

    # Create agent with explicit configuration
    return LlmAgent(
        model=model,
        name="weather_test_agent",
        description="Test agent for weather MCP server validation",
        instruction=(
            "You are a weather information assistant with access to weather tools. "
            "When users ask about weather, use the available tools to get accurate data. "
            "Always specify the location clearly when using tools. "
            "Provide responses in a friendly, conversational tone. "
            "If a tool call fails, explain the issue to the user."
        ),
        tools=[toolset],
        generate_content_config=GenerateContentConfig(
            temperature=temperature,
            top_p=0.9,
            top_k=40,
            max_output_tokens=2048,
        ),
    )


# Optional: Test the factory when run directly
if __name__ == "__main__":
    print("Creating agent...")
    agent = create_agent()
    print(f"✓ Agent created: {agent.name}")
    print(f"✓ Model: {agent.model}")
    print(f"✓ Tools: {len(agent.tools)} toolset(s)")
```

Test the factory:
```bash
export GOOGLE_API_KEY="your-key"
python agent_factory.py
# Output:
# Creating agent...
# ✓ Agent created: weather_test_agent
# ✓ Model: gemini-2.0-flash
# ✓ Tools: 1 toolset(s)
```

## Running with ADK Agent

### Basic Usage

```bash
mcprobe run scenario.yaml \
  --agent-type adk \
  --agent-factory agent_factory.py
```

### With Environment Configuration

```bash
# Configure environment
export GOOGLE_API_KEY="your-api-key"
export MCP_URL="http://localhost:8080/mcp"
export MCP_TOKEN="dev"
export GEMINI_MODEL="gemini-2.0-flash"

# Run tests
mcprobe run scenarios/ \
  -t adk \
  -f agent_factory.py \
  --verbose
```

### Full Example with All Options

```bash
export GOOGLE_API_KEY="..."
export MCP_URL="http://mcp-server:8080/mcp"
export MCP_TOKEN="production-token"
export GEMINI_MODEL="gemini-2.0-pro"

mcprobe run weather_scenarios/ \
  --agent-type adk \
  --agent-factory ./agents/weather_agent.py \
  --model llama3.2 \
  --base-url http://localhost:11434 \
  --verbose
```

**Note:** `--model` and `--base-url` configure the synthetic user and judge (Ollama), not the ADK agent.

## Tool Call Tracking

The ADK agent automatically tracks all tool calls for evaluation:

### Tool Call Structure

```python
from mcprobe.models.conversation import ToolCall

tool_call = ToolCall(
    tool_name="get_weather",
    parameters={"location": "San Francisco", "units": "celsius"},
    result={"temperature": 18, "conditions": "partly cloudy"},
    latency_ms=342.5,
    error=None,  # Or error message if tool failed
)
```

### Accessing Tool Calls

```python
response = await agent.send_message("What's the weather in Tokyo?")

for call in response.tool_calls:
    print(f"Tool: {call.tool_name}")
    print(f"Parameters: {call.parameters}")
    print(f"Result: {call.result}")
    print(f"Latency: {call.latency_ms}ms")
    if call.error:
        print(f"Error: {call.error}")
```

### Tool Call Validation in Scenarios

```yaml
scenario:
  name: "Weather Tool Usage"
  goal: "Use weather tool correctly"

test_case:
  - user: "What's the weather in Paris?"
    expected_behavior: "Calls get_weather tool with location='Paris'"
    required_tools:
      - name: "get_weather"
        parameters:
          location: "Paris"
```

MCProbe validates that:
- Required tools were called
- Parameters match expected values
- Tool calls succeeded (no errors)

## Best Practices

### 1. Error Handling in Factory

Always validate environment variables:

```python
def create_agent() -> LlmAgent:
    # Validate required config
    if not os.environ.get("GOOGLE_API_KEY"):
        raise ValueError("GOOGLE_API_KEY is required")

    if not os.environ.get("MCP_URL"):
        raise ValueError("MCP_URL is required")

    # ... create agent
```

### 2. Clear Agent Instructions

Provide explicit tool usage guidance:

```python
instruction=(
    "Use available tools to answer questions accurately. "
    "ALWAYS call get_weather when asked about weather - do not guess. "
    "If a tool call fails, explain the error to the user. "
    "Provide units when reporting numeric values."
)
```

### 3. Appropriate Temperature

Use low temperature for testing:

```python
generate_content_config=GenerateContentConfig(
    temperature=0.1,  # More consistent for testing
    top_p=0.9,
)
```

### 4. Connection Timeouts

Set reasonable timeouts for tool calls:

```python
connection_params = StreamableHTTPConnectionParams(
    url=mcp_url,
    headers={"Authorization": f"Bearer {mcp_token}"},
    timeout=30,  # 30 seconds for slow tools
)
```

### 5. Model Selection

Choose appropriate model for your use case:

- **Development/Testing:** `gemini-2.0-flash` (fast, cheap)
- **Production Validation:** `gemini-2.0-pro` (more capable)
- **High Volume:** `gemini-2.0-flash` (cost-effective)

### 6. Model Name Tracking

MCProbe automatically captures the model name from your ADK agent for reporting. The model name is extracted from the `LlmAgent.model` attribute. To ensure your model appears in HTML reports:

```python
# The model is captured automatically from the LlmAgent
agent = LlmAgent(
    model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),  # This appears in reports
    name="my_agent",
    # ... other config
)
```

If the model is not set or cannot be determined, reports will show "N/A" for the agent model.

### 7. Environment-Based Configuration

Use environment variables for flexibility:

```python
# Different configs for different environments
# dev.env
MCP_URL=http://localhost:8080/mcp
GEMINI_MODEL=gemini-2.0-flash
AGENT_TEMPERATURE=0.3

# prod.env
MCP_URL=https://mcp.production.com/mcp
GEMINI_MODEL=gemini-2.0-pro
AGENT_TEMPERATURE=0.1
```

### 7. Multiple Toolsets

Agents can use multiple MCP servers:

```python
# Weather tools
weather_toolset = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="http://weather-mcp:8080/mcp"
    )
)

# Calendar tools
calendar_toolset = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="http://calendar-mcp:8081/mcp"
    )
)

agent = LlmAgent(
    tools=[weather_toolset, calendar_toolset],
    # ... other config
)
```

## Troubleshooting

### "GOOGLE_API_KEY not set" Error

**Problem:** Missing or invalid API key.

**Solution:**
```bash
# Get key from https://aistudio.google.com/apikey
export GOOGLE_API_KEY="your-actual-key"

# Verify it's set
echo $GOOGLE_API_KEY
```

### "Cannot connect to MCP server" Error

**Problem:** MCP server not accessible.

**Solutions:**
```bash
# Check MCP server is running
curl http://localhost:8080/mcp/health

# Verify URL in environment
echo $MCP_URL

# Check network connectivity
ping localhost

# Check firewall rules
```

### "create_agent() not found" Error

**Problem:** Agent factory module doesn't export required function.

**Solution:**
```python
# Ensure your module has this function
def create_agent() -> LlmAgent:
    # ... implementation
    return agent
```

### Tool Calls Not Being Tracked

**Problem:** `response.tool_calls` is empty even though tools were used.

**Cause:** This is a known limitation - ADK tool introspection requires async calls.

**Workaround:** Tool calls are tracked in real-time during execution, but may not appear in final response metadata.

### Slow Agent Responses

**Problem:** Agent takes too long to respond.

**Solutions:**
- Use `gemini-2.0-flash` instead of `-pro`
- Reduce `max_output_tokens`
- Check MCP server latency
- Increase connection timeout

## Next Steps

- [Custom Agents](custom-agents.md) - Build your own agent wrapper
- [Scenario Writing](../scenarios/writing-scenarios.md) - Create effective test scenarios
- [Tool Requirements](../scenarios/tool-requirements.md) - Specify tool usage expectations
- [Simple Agent](simple-agent.md) - Understand the simpler baseline agent
- [Agent Overview](overview.md) - Compare all agent types
