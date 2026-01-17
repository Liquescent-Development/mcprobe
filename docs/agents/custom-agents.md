# Custom Agent Implementation Guide

## Overview

MCProbe's extensible architecture allows you to test any agent implementation by creating a custom agent class. This guide shows you how to implement the `AgentUnderTest` interface for your own agent framework.

## When to Build a Custom Agent

Create a custom agent when:

- **Testing proprietary agent frameworks** - Internal agent systems
- **Custom tool protocols** - Non-MCP tool integrations
- **Specialized architectures** - Multi-agent systems, RAG pipelines
- **Legacy systems** - Existing agents that don't fit simple/ADK patterns
- **Research prototypes** - Novel agent architectures under development

## AgentUnderTest Interface

All agents must implement this abstract base class:

```python
from abc import ABC, abstractmethod
from mcprobe.agents.base import AgentUnderTest
from mcprobe.models.conversation import AgentResponse

class AgentUnderTest(ABC):
    """Abstract base class for agents being tested."""

    @abstractmethod
    async def send_message(self, message: str) -> AgentResponse:
        """Send a user message and get the agent's response."""
        ...

    @abstractmethod
    async def reset(self) -> None:
        """Reset conversation state for a new test."""
        ...

    @abstractmethod
    def get_available_tools(self) -> list[dict[str, object]]:
        """Return the tool schemas available to this agent."""
        ...

    @property
    def name(self) -> str:
        """Human-readable name for this agent."""
        return self.__class__.__name__
```

## Required Methods

### 1. `send_message(message: str) -> AgentResponse`

Send a user message and receive the agent's response.

**Parameters:**
- `message` (str): The user's message text

**Returns:**
- `AgentResponse` with:
  - `message` (str): Agent's text response
  - `tool_calls` (list[ToolCall]): Tools invoked during response generation
  - `is_complete` (bool): Whether the agent considers its response complete
  - `metadata` (dict): Additional response context

**Raises:**
- `OrchestrationError`: If agent fails to generate a response

**Implementation Requirements:**

1. Maintain conversation history internally
2. Generate response using your agent's logic
3. Track all tool calls made during response generation
4. Determine if response is complete (or use heuristic)
5. Return properly structured `AgentResponse`

**Example:**

```python
async def send_message(self, message: str) -> AgentResponse:
    from mcprobe.exceptions import OrchestrationError
    from mcprobe.models.conversation import AgentResponse, ToolCall

    # Add to conversation history
    self.history.append({"role": "user", "content": message})

    try:
        # Your agent's logic here
        response_text, tools_used = await self.agent.generate(self.history)
    except Exception as e:
        raise OrchestrationError(f"Agent failed: {e}") from e

    # Add response to history
    self.history.append({"role": "assistant", "content": response_text})

    # Convert tools to MCProbe format
    tool_calls = [
        ToolCall(
            tool_name=tool["name"],
            parameters=tool["params"],
            result=tool["result"],
            latency_ms=tool["duration"],
            error=tool.get("error"),
        )
        for tool in tools_used
    ]

    # Determine completion
    is_complete = not response_text.strip().endswith("?")

    return AgentResponse(
        message=response_text,
        tool_calls=tool_calls,
        is_complete=is_complete,
        metadata={"model": self.model_name},
    )
```

### 2. `reset() -> None`

Reset conversation state for a new test scenario.

**Behavior:**
- Clear conversation history
- Reset any stateful components
- Return agent to initial state
- Preserve configuration (system prompt, model, etc.)

**Must be idempotent:** Multiple calls should be safe.

**Example:**

```python
async def reset(self) -> None:
    # Clear conversation history
    self.history = []

    # Re-add system prompt if present
    if self.system_prompt:
        self.history.append({
            "role": "system",
            "content": self.system_prompt
        })

    # Reset any agent-specific state
    self.agent.reset_session()
    self.tool_cache.clear()
```

### 3. `get_available_tools() -> list[dict[str, object]]`

Return tool schemas available to this agent.

**Returns:**
- List of tool definitions in OpenAI-compatible format
- Empty list if agent has no tools

**Format:**

```python
[
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name"
                    },
                    "units": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"]
                    }
                },
                "required": ["location"]
            }
        }
    }
]
```

**Example:**

```python
def get_available_tools(self) -> list[dict[str, object]]:
    # If your agent has a tool registry
    if hasattr(self.agent, "tools"):
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters_schema,
                }
            }
            for tool in self.agent.tools
        ]

    # If no tools
    return []
```

### 4. `name` Property (Optional)

Override to provide a custom display name:

```python
@property
def name(self) -> str:
    return "MyCustomAgent-v2"
```

Default implementation returns class name: `self.__class__.__name__`

## AgentResponse Structure

Your `send_message` implementation must return this structure:

```python
from mcprobe.models.conversation import AgentResponse, ToolCall

response = AgentResponse(
    message="The weather in Paris is 18°C and sunny.",
    tool_calls=[
        ToolCall(
            tool_name="get_weather",
            parameters={"location": "Paris", "units": "celsius"},
            result={"temp": 18, "conditions": "sunny"},
            latency_ms=245.3,
            error=None,
        )
    ],
    is_complete=True,
    metadata={
        "model": "my-model-v1",
        "tokens_used": 150,
        "custom_field": "value",
    },
)
```

### ToolCall Fields

```python
ToolCall(
    tool_name: str,          # Tool identifier
    parameters: dict,        # Input parameters passed to tool
    result: Any,            # Tool's return value (any JSON-serializable type)
    latency_ms: float,      # Execution time in milliseconds
    error: str | None,      # Error message if tool failed, None if successful
)
```

## Complete Example: LangChain Agent

Here's a full implementation wrapping a LangChain agent:

```python
"""LangChain agent wrapper for MCProbe testing.

Example usage:
    from langchain_openai import ChatOpenAI
    from langchain.agents import create_openai_tools_agent

    llm = ChatOpenAI(model="gpt-4")
    agent = create_openai_tools_agent(llm, tools, prompt)

    mcprobe_agent = LangChainAgent(agent, agent_executor)
"""

import time
from typing import Any

from langchain.agents import AgentExecutor
from langchain.schema import AIMessage, HumanMessage, SystemMessage

from mcprobe.agents.base import AgentUnderTest
from mcprobe.exceptions import OrchestrationError
from mcprobe.models.conversation import AgentResponse, ToolCall


class LangChainAgent(AgentUnderTest):
    """Wrapper for LangChain agents to use with MCProbe.

    Wraps a LangChain AgentExecutor and tracks tool calls for evaluation.
    """

    def __init__(
        self,
        agent_executor: AgentExecutor,
        system_prompt: str | None = None,
        agent_name: str = "LangChainAgent",
    ) -> None:
        """Initialize the LangChain agent wrapper.

        Args:
            agent_executor: Configured LangChain AgentExecutor
            system_prompt: Optional system instructions
            agent_name: Display name for the agent
        """
        self.executor = agent_executor
        self.system_prompt = system_prompt
        self.agent_name = agent_name
        self.chat_history: list[HumanMessage | AIMessage | SystemMessage] = []

        # Add system prompt to history
        if system_prompt:
            self.chat_history.append(SystemMessage(content=system_prompt))

    @property
    def name(self) -> str:
        """Return agent display name."""
        return self.agent_name

    async def send_message(self, message: str) -> AgentResponse:
        """Send message to LangChain agent and track tool usage.

        Args:
            message: User's message text

        Returns:
            AgentResponse with message, tool calls, and metadata

        Raises:
            OrchestrationError: If agent execution fails
        """
        # Add user message to history
        self.chat_history.append(HumanMessage(content=message))

        # Track tool calls
        tool_calls: list[ToolCall] = []

        # Configure executor to track tool usage
        callbacks = [ToolTrackingCallback(tool_calls)]

        try:
            # Execute agent
            start_time = time.time()
            result = await self.executor.ainvoke(
                {
                    "input": message,
                    "chat_history": self.chat_history,
                },
                config={"callbacks": callbacks},
            )
            total_time = (time.time() - start_time) * 1000

            response_text = result["output"]

        except Exception as e:
            msg = f"LangChain agent execution failed: {e}"
            raise OrchestrationError(msg) from e

        # Add assistant response to history
        self.chat_history.append(AIMessage(content=response_text))

        # Determine if complete
        is_complete = not response_text.strip().endswith("?")

        return AgentResponse(
            message=response_text,
            tool_calls=tool_calls,
            is_complete=is_complete,
            metadata={
                "total_time_ms": total_time,
                "intermediate_steps": len(result.get("intermediate_steps", [])),
            },
        )

    async def reset(self) -> None:
        """Reset conversation history."""
        self.chat_history = []
        if self.system_prompt:
            self.chat_history.append(SystemMessage(content=self.system_prompt))

    def get_available_tools(self) -> list[dict[str, object]]:
        """Get tool schemas from LangChain agent.

        Returns:
            List of tool schemas in OpenAI format
        """
        if not hasattr(self.executor, "tools"):
            return []

        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.args_schema.schema() if tool.args_schema else {},
                },
            }
            for tool in self.executor.tools
        ]


class ToolTrackingCallback:
    """Callback to track LangChain tool executions."""

    def __init__(self, tool_calls: list[ToolCall]) -> None:
        self.tool_calls = tool_calls
        self.current_tool_start: float | None = None

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        """Track tool start time."""
        self.current_tool_start = time.time()

    def on_tool_end(
        self,
        output: str,
        **kwargs: Any,
    ) -> None:
        """Record completed tool call."""
        if self.current_tool_start is None:
            return

        latency = (time.time() - self.current_tool_start) * 1000

        tool_name = kwargs.get("name", "unknown")
        self.tool_calls.append(
            ToolCall(
                tool_name=tool_name,
                parameters={"input": kwargs.get("input_str", "")},
                result=output,
                latency_ms=latency,
                error=None,
            )
        )
        self.current_tool_start = None

    def on_tool_error(
        self,
        error: Exception,
        **kwargs: Any,
    ) -> None:
        """Record tool error."""
        if self.current_tool_start is None:
            return

        latency = (time.time() - self.current_tool_start) * 1000

        tool_name = kwargs.get("name", "unknown")
        self.tool_calls.append(
            ToolCall(
                tool_name=tool_name,
                parameters={"input": kwargs.get("input_str", "")},
                result=None,
                latency_ms=latency,
                error=str(error),
            )
        )
        self.current_tool_start = None
```

## Complete Example: OpenAI Assistant

Wrapper for OpenAI Assistants API:

```python
"""OpenAI Assistant wrapper for MCProbe testing."""

import time
from typing import Any

from openai import AsyncOpenAI
from openai.types.beta.threads import Run

from mcprobe.agents.base import AgentUnderTest
from mcprobe.exceptions import OrchestrationError
from mcprobe.models.conversation import AgentResponse, ToolCall


class OpenAIAssistantAgent(AgentUnderTest):
    """Wrapper for OpenAI Assistants API."""

    def __init__(
        self,
        assistant_id: str,
        api_key: str,
        agent_name: str | None = None,
    ) -> None:
        """Initialize OpenAI assistant wrapper.

        Args:
            assistant_id: OpenAI assistant ID
            api_key: OpenAI API key
            agent_name: Optional display name
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.assistant_id = assistant_id
        self.thread_id: str | None = None
        self._name = agent_name or f"Assistant-{assistant_id[:8]}"

    @property
    def name(self) -> str:
        return self._name

    async def send_message(self, message: str) -> AgentResponse:
        """Send message to OpenAI assistant.

        Args:
            message: User message text

        Returns:
            AgentResponse with message and tool calls

        Raises:
            OrchestrationError: If API call fails
        """
        # Create thread if needed
        if self.thread_id is None:
            thread = await self.client.beta.threads.create()
            self.thread_id = thread.id

        try:
            # Add user message
            await self.client.beta.threads.messages.create(
                thread_id=self.thread_id,
                role="user",
                content=message,
            )

            # Run assistant
            run = await self.client.beta.threads.runs.create(
                thread_id=self.thread_id,
                assistant_id=self.assistant_id,
            )

            # Wait for completion and track tools
            tool_calls = []
            run = await self._wait_for_run(run, tool_calls)

            # Get assistant's response
            messages = await self.client.beta.threads.messages.list(
                thread_id=self.thread_id,
                order="desc",
                limit=1,
            )

            response_text = messages.data[0].content[0].text.value

        except Exception as e:
            msg = f"OpenAI assistant execution failed: {e}"
            raise OrchestrationError(msg) from e

        is_complete = not response_text.strip().endswith("?")

        return AgentResponse(
            message=response_text,
            tool_calls=tool_calls,
            is_complete=is_complete,
            metadata={
                "run_id": run.id,
                "model": run.model,
            },
        )

    async def _wait_for_run(
        self,
        run: Run,
        tool_calls: list[ToolCall],
    ) -> Run:
        """Wait for run completion and track tool calls."""
        while run.status in ("queued", "in_progress", "requires_action"):
            # Handle tool calls
            if run.status == "requires_action":
                if run.required_action and run.required_action.submit_tool_outputs:
                    tool_outputs = []

                    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                        start = time.time()

                        # Execute tool (simplified - implement your logic)
                        result = await self._execute_tool(
                            tool_call.function.name,
                            tool_call.function.arguments,
                        )

                        latency = (time.time() - start) * 1000

                        tool_calls.append(
                            ToolCall(
                                tool_name=tool_call.function.name,
                                parameters=tool_call.function.arguments,
                                result=result,
                                latency_ms=latency,
                                error=None,
                            )
                        )

                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": str(result),
                        })

                    # Submit tool outputs
                    run = await self.client.beta.threads.runs.submit_tool_outputs(
                        thread_id=self.thread_id,
                        run_id=run.id,
                        tool_outputs=tool_outputs,
                    )

            # Poll for updates
            await asyncio.sleep(0.5)
            run = await self.client.beta.threads.runs.retrieve(
                thread_id=self.thread_id,
                run_id=run.id,
            )

        return run

    async def _execute_tool(self, name: str, arguments: str) -> Any:
        """Execute a tool call (implement based on your tools)."""
        # Implement your tool execution logic
        return {"status": "success"}

    async def reset(self) -> None:
        """Reset by creating new thread."""
        self.thread_id = None

    def get_available_tools(self) -> list[dict[str, object]]:
        """Get tools from assistant (requires sync call to API)."""
        # Would need to fetch assistant details
        return []
```

## Registering Custom Agents

### Option 1: Direct Instantiation

Use your custom agent directly in Python code:

```python
from mcprobe.orchestrator.orchestrator import ConversationOrchestrator
from my_agents import LangChainAgent

# Create custom agent
agent = LangChainAgent(executor, system_prompt="You are helpful")

# Create orchestrator
orchestrator = ConversationOrchestrator(
    agent=agent,
    user=synthetic_user,
    judge=judge,
)

# Run test
result = await orchestrator.run_conversation(scenario)
```

### Option 2: Factory Pattern

Create a factory module for CLI usage:

```python
# custom_agent_factory.py
from my_agents import LangChainAgent
from langchain.agents import AgentExecutor

def create_agent() -> AgentUnderTest:
    """Create custom agent for MCProbe."""
    # Set up your agent
    executor = AgentExecutor(...)

    return LangChainAgent(
        agent_executor=executor,
        system_prompt="You are a helpful assistant",
    )
```

Use with CLI by modifying MCProbe to support custom factories, or use the Python API.

## Testing Custom Agents

### Unit Tests

Test each method independently:

```python
import pytest
from my_agents import LangChainAgent

@pytest.mark.asyncio
async def test_send_message():
    agent = LangChainAgent(executor)

    response = await agent.send_message("Hello")

    assert response.message
    assert isinstance(response.tool_calls, list)
    assert isinstance(response.is_complete, bool)


@pytest.mark.asyncio
async def test_reset():
    agent = LangChainAgent(executor)

    await agent.send_message("First message")
    await agent.reset()

    # Verify history is cleared
    assert len(agent.chat_history) == 0


def test_get_available_tools():
    agent = LangChainAgent(executor)

    tools = agent.get_available_tools()

    assert isinstance(tools, list)
    for tool in tools:
        assert "type" in tool
        assert "function" in tool
```

### Integration Tests

Test with MCProbe orchestrator:

```python
@pytest.mark.asyncio
async def test_custom_agent_integration():
    from mcprobe.orchestrator.orchestrator import ConversationOrchestrator

    agent = LangChainAgent(executor)
    orchestrator = ConversationOrchestrator(
        agent=agent,
        user=synthetic_user,
        judge=judge,
    )

    result = await orchestrator.run_conversation(scenario)

    assert result.termination_reason == TerminationReason.USER_SATISFIED
    assert len(result.turns) > 0
```

## Best Practices

### 1. Error Handling

Always wrap agent execution in try/except:

```python
try:
    response = await self.agent.generate(message)
except AgentTimeoutError as e:
    raise OrchestrationError(f"Agent timeout: {e}") from e
except AgentAPIError as e:
    raise OrchestrationError(f"API error: {e}") from e
except Exception as e:
    raise OrchestrationError(f"Unexpected error: {e}") from e
```

### 2. Tool Call Tracking

Track all tool executions with accurate timing:

```python
start = time.time()
try:
    result = await tool.execute(params)
    error = None
except Exception as e:
    result = None
    error = str(e)
finally:
    latency_ms = (time.time() - start) * 1000

tool_calls.append(ToolCall(
    tool_name=tool.name,
    parameters=params,
    result=result,
    latency_ms=latency_ms,
    error=error,
))
```

### 3. Conversation History

Maintain complete history for context:

```python
# Store all messages
self.history.append({"role": "user", "content": message})
self.history.append({"role": "assistant", "content": response})

# Include tool interactions if relevant
self.history.append({
    "role": "function",
    "name": tool_name,
    "content": tool_result,
})
```

### 4. Metadata

Include useful debugging information:

```python
metadata = {
    "model": self.model_name,
    "tokens_used": response.usage.total_tokens,
    "latency_ms": response.latency,
    "finish_reason": response.finish_reason,
    "custom_metrics": {...},
}
```

### 5. Idempotent Reset

Ensure reset can be called multiple times safely:

```python
async def reset(self) -> None:
    # Clear state
    self.history = []
    self.tool_cache = {}

    # Reset external resources if needed
    if self.session_id:
        await self.api.close_session(self.session_id)
        self.session_id = None

    # Reinitialize if needed
    if self.system_prompt:
        self.history.append({"role": "system", "content": self.system_prompt})
```

## Next Steps

- [Simple Agent](simple-agent.md) - Learn from the simple implementation
- [ADK Agent](adk-agent.md) - Study the ADK wrapper
- [Agent Overview](overview.md) - Understand agent architecture
- [Scenario Writing](../scenarios/writing-scenarios.md) - Test your custom agent
- [CLI Reference](../cli/reference.md) - Understand testing workflow
