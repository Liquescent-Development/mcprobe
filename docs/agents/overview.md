# Agent Types Overview

## What is an Agent in MCProbe?

In MCProbe, an **agent** is the system under test - the conversational AI component that interacts with users and potentially uses tools to accomplish tasks. MCProbe tests agents by simulating realistic user conversations and evaluating their responses.

All agents in MCProbe implement the `AgentUnderTest` interface, which defines a standard contract for:

- Sending messages and receiving responses
- Resetting conversation state between tests
- Exposing available tools for introspection

## Available Agent Types

MCProbe supports two built-in agent types:

### 1. Simple LLM Agent

**Type identifier:** `simple`

A basic agent that uses an LLM for text-only conversations without tool calling capabilities.

- **Best for:** Baseline testing, LLM-only conversations, Phase 1 scenarios
- **Tools:** None
- **Backend:** Any Ollama-compatible LLM provider
- **Configuration:** Minimal - just model and base URL

[Learn more about Simple Agents →](simple-agent.md)

### 2. Gemini ADK Agent

**Type identifier:** `adk`

An advanced agent using Google's Gemini ADK with full MCP (Model Context Protocol) tool integration.

- **Best for:** MCP server testing, tool-rich scenarios, production agent validation
- **Tools:** Full MCP toolset via HTTP server connection
- **Backend:** Google Gemini models (2.0-flash, etc.)
- **Configuration:** Requires agent factory module

[Learn more about ADK Agents →](adk-agent.md)

## Agent Comparison

| Feature | Simple Agent | ADK Agent |
|---------|-------------|-----------|
| Tool Calling | ✗ No | ✓ Yes (MCP) |
| Backend | Ollama-compatible | Google Gemini |
| Setup Complexity | Low | Medium |
| Use Case | Baseline testing | MCP validation |
| Configuration | CLI flags | Python factory |
| Tool Tracking | N/A | Full tracking |
| Conversation History | ✓ Yes | ✓ Yes |
| Custom Instructions | System prompt | Agent instruction |

## Agent Lifecycle

All agents follow the same lifecycle managed by MCProbe:

### 1. Initialization

Agents are created once per test session:

```python
# Simple agent - created internally by MCProbe
agent = SimpleLLMAgent(
    provider=ollama_provider,
    system_prompt="You are a helpful assistant...",
)

# ADK agent - created via user factory
from agent_factory import create_agent
agent = GeminiADKAgent(agent=create_agent())
```

### 2. Message Exchange

During each conversation turn:

```python
response: AgentResponse = await agent.send_message("What's the weather?")

# Response contains:
# - message: str - The agent's text response
# - tool_calls: list[ToolCall] - Any tools invoked
# - is_complete: bool - Whether agent is done responding
# - metadata: dict - Additional context
```

### 3. Reset Between Tests

Before each new scenario:

```python
await agent.reset()  # Clears conversation history, resets state
```

### 4. Tool Introspection

MCProbe can inspect available tools:

```python
tools = agent.get_available_tools()
# Returns list of tool schemas in OpenAI-compatible format
```

## Core Interface Methods

All agents must implement these methods from `AgentUnderTest`:

### `async def send_message(message: str) -> AgentResponse`

Send a user message and receive the agent's response.

**Parameters:**
- `message` (str): The user's message text

**Returns:**
- `AgentResponse` containing:
  - `message` (str): Agent's text response
  - `tool_calls` (list[ToolCall]): Tools invoked during response
  - `is_complete` (bool): Whether conversation seems complete
  - `metadata` (dict): Additional response metadata

**Raises:**
- `OrchestrationError`: If agent fails to respond

### `async def reset() -> None`

Reset conversation state for a new test scenario.

Clears conversation history and returns agent to initial state. Should be idempotent.

### `def get_available_tools() -> list[dict[str, object]]`

Return tool schemas available to this agent.

**Returns:**
- List of tool definitions in OpenAI-compatible format
- Empty list if agent has no tools

## AgentResponse Structure

The `AgentResponse` model captures complete agent output:

```python
from mcprobe.models.conversation import AgentResponse, ToolCall

response = AgentResponse(
    message="The weather in San Francisco is 65°F and sunny.",
    tool_calls=[
        ToolCall(
            tool_name="get_weather",
            parameters={"location": "San Francisco"},
            result={"temp": 65, "conditions": "sunny"},
            latency_ms=245.3,
            error=None,
        )
    ],
    is_complete=True,
    metadata={
        "usage": {"prompt_tokens": 123, "completion_tokens": 45},
        "finish_reason": "stop",
    },
)
```

## ToolCall Structure

Each tool invocation is tracked:

```python
from mcprobe.models.conversation import ToolCall

tool_call = ToolCall(
    tool_name="weather_api",           # Name of the tool
    parameters={"city": "Paris"},      # Input parameters
    result={"temp": 18},               # Tool's return value
    latency_ms=342.1,                  # Execution time
    error=None,                        # Error message if failed
)
```

## Choosing the Right Agent Type

### Use Simple Agent When:

- Testing LLM conversation quality without tools
- Establishing baseline performance metrics
- Running Phase 1 scenarios (no tool requirements)
- Working with Ollama or local LLM deployments
- Prototyping scenarios before implementing tools

### Use ADK Agent When:

- Testing MCP server implementations
- Validating tool selection and parameter passing
- Measuring tool integration performance
- Running Phase 2+ scenarios with tool requirements
- Production agent validation

### Build Custom Agent When:

- Integrating with proprietary agent frameworks
- Implementing custom tool calling protocols
- Testing non-standard agent architectures
- Requiring specialized agent behaviors

[Learn how to build custom agents →](custom-agents.md)

## CLI Usage

### Simple Agent

```bash
mcprobe run scenario.yaml \
  --agent-type simple \
  --model llama3.2 \
  --base-url http://localhost:11434
```

### ADK Agent

```bash
mcprobe run scenario.yaml \
  --agent-type adk \
  --agent-factory my_agent_factory.py
```

The agent factory module must export a `create_agent()` function that returns a configured `LlmAgent` instance.

## Next Steps

- [Simple Agent Guide](simple-agent.md) - Text-only agent setup
- [ADK Agent Guide](adk-agent.md) - MCP-enabled agent setup
- [Custom Agents](custom-agents.md) - Building your own agent type
- [Scenario Writing](../scenarios/writing-scenarios.md) - Creating test scenarios
- [CLI Reference](../cli/reference.md) - Complete command reference
