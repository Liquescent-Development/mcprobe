"""Gemini ADK agent implementation with MCP tool support."""

import importlib.util
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mcprobe.agents.base import AgentUnderTest
from mcprobe.exceptions import OrchestrationError
from mcprobe.models.conversation import AgentResponse, ToolCall

if TYPE_CHECKING:
    from google.adk.agents import LlmAgent


class GeminiADKAgent(AgentUnderTest):
    """Agent under test using Gemini ADK with MCP tools.

    Wraps a user-provided LlmAgent and executes it via Runner,
    tracking all tool calls for evaluation.
    """

    def __init__(
        self,
        agent: "LlmAgent",
        agent_name: str | None = None,
    ) -> None:
        """Initialize the Gemini ADK agent wrapper.

        Args:
            agent: A configured LlmAgent instance from google-adk.
            agent_name: Optional name override for the agent.
        """
        from google.adk.runners import Runner  # noqa: PLC0415
        from google.adk.sessions import InMemorySessionService  # noqa: PLC0415

        self._agent = agent
        self._name = agent_name or getattr(agent, "name", None) or "GeminiADKAgent"
        self._session_service = InMemorySessionService()
        self._runner = Runner(
            agent=agent,
            app_name="mcprobe",
            session_service=self._session_service,
        )
        self._session_id: str | None = None
        # Use unique user_id per instance to prevent any ADK-side caching/session leakage
        self._user_id = f"mcprobe_{uuid.uuid4().hex[:8]}"

    @property
    def name(self) -> str:
        """Human-readable agent name."""
        return self._name

    def _process_function_responses(
        self,
        function_responses: list[Any],
        pending_calls: dict[str, tuple[str, dict[str, Any], float]],
    ) -> list[ToolCall]:
        """Process function responses and create ToolCall objects."""
        tool_calls: list[ToolCall] = []
        response_time = time.time()

        for fr in function_responses:
            call_id = fr.id or fr.name or "unknown"
            if call_id in pending_calls:
                name, params, start = pending_calls.pop(call_id)
            else:
                # Response without matching call - use response info
                name = fr.name or "unknown"
                params = {}
                start = response_time

            tool_calls.append(
                ToolCall(
                    tool_name=name,
                    parameters=params,
                    called_at=start,
                    responded_at=response_time,
                    result=fr.response,
                    latency_ms=(time.time() - start) * 1000,
                )
            )
        return tool_calls

    async def send_message(self, message: str) -> AgentResponse:
        """Send message to ADK agent and collect response with tool calls.

        Args:
            message: User message to send to the agent.

        Returns:
            AgentResponse with message, tool calls, and completion status.

        Raises:
            OrchestrationError: If the ADK agent execution fails.
        """
        from google.genai.types import Content, Part  # noqa: PLC0415

        # Create session if needed
        if self._session_id is None:
            session = await self._session_service.create_session(
                app_name="mcprobe",
                user_id=self._user_id,
            )
            self._session_id = session.id

        # Prepare user message
        user_content = Content(parts=[Part(text=message)], role="user")

        # Execute and collect results
        response_text = ""
        tool_calls: list[ToolCall] = []
        pending_calls: dict[str, tuple[str, dict[str, Any], float]] = {}

        try:
            async for event in self._runner.run_async(
                user_id=self._user_id,
                session_id=self._session_id,
                new_message=user_content,
            ):
                # Track function calls (requests)
                for fc in event.get_function_calls() or []:
                    call_id = fc.id or fc.name or "unknown"
                    pending_calls[call_id] = (
                        fc.name or "unknown",
                        dict(fc.args) if fc.args else {},
                        time.time(),
                    )

                # Track function responses (results)
                responses = event.get_function_responses()
                if responses:
                    tool_calls.extend(
                        self._process_function_responses(responses, pending_calls)
                    )

                # Capture text from any event with text content
                # (not just final response - text may come in earlier events when tools are used)
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            response_text += part.text

            # Handle any calls that never got responses
            for _id, (name, params, start) in pending_calls.items():
                now = time.time()
                tool_calls.append(
                    ToolCall(
                        tool_name=name,
                        parameters=params,
                        result=None,
                        error="No response received",
                        latency_ms=(now - start) * 1000,
                        called_at=start,
                        responded_at=None,  # Never responded
                    )
                )
        except Exception as e:
            msg = f"ADK agent execution failed: {e}"
            raise OrchestrationError(msg) from e

        # Determine if complete (not asking a question)
        is_complete = bool(response_text) and not response_text.strip().endswith("?")

        return AgentResponse(
            message=response_text,
            tool_calls=tool_calls,
            is_complete=is_complete,
            metadata={"agent_type": "gemini_adk"},
        )

    async def reset(self) -> None:
        """Reset agent state for new conversation."""
        from google.adk.runners import Runner  # noqa: PLC0415
        from google.adk.sessions import InMemorySessionService  # noqa: PLC0415

        self._session_id = None
        # Generate new user_id to prevent any ADK-side caching/session leakage
        self._user_id = f"mcprobe_{uuid.uuid4().hex[:8]}"
        # Create fresh session service
        self._session_service = InMemorySessionService()
        self._runner = Runner(
            agent=self._agent,
            app_name="mcprobe",
            session_service=self._session_service,
        )

    async def close(self) -> None:
        """Clean up ADK agent resources including MCP toolset connections."""
        # Close any MCP toolset connections in the agent's tools
        if hasattr(self._agent, "tools") and self._agent.tools:
            for tool in self._agent.tools:
                # McpToolset has a close() method
                if hasattr(tool, "close"):
                    try:
                        close_result = tool.close()
                        # Handle both sync and async close methods
                        if hasattr(close_result, "__await__"):
                            await close_result
                    except Exception:
                        pass  # Best effort cleanup

    async def get_available_tools(self) -> list[dict[str, Any]]:
        """Get tool schemas from ADK agent's MCP toolsets.

        Returns:
            List of tool schemas extracted from any McpToolset instances.
        """
        tools: list[dict[str, Any]] = []

        if not hasattr(self._agent, "tools") or not self._agent.tools:
            return tools

        for toolset in self._agent.tools:
            # Check if this is an McpToolset with get_tools method
            if hasattr(toolset, "get_tools"):
                try:
                    toolset_tools = await toolset.get_tools()
                    for tool in toolset_tools:
                        tools.append({
                            "name": getattr(tool, "name", "unknown"),
                            "description": getattr(tool, "description", ""),
                            "input_schema": getattr(tool, "inputSchema", {}),
                        })
                except Exception:
                    pass  # Best effort - continue with other toolsets

        return tools

    def get_system_prompt(self) -> str | None:
        """Return ADK agent's instruction (system prompt).

        Returns:
            The instruction string if available, otherwise None.
        """
        if hasattr(self._agent, "instruction"):
            instruction = self._agent.instruction
            # instruction can be a string or a callable; we only return strings
            if isinstance(instruction, str):
                return instruction
        return None

    def get_model_name(self) -> str | None:
        """Return the model name used by this ADK agent.

        Returns:
            The model name string if available, otherwise None.
        """
        if hasattr(self._agent, "model"):
            return str(self._agent.model)
        return None


def load_agent_factory(module_path: str) -> Callable[[], "LlmAgent"]:
    """Load agent factory function from a Python module.

    Args:
        module_path: Path to Python module (e.g., "my_agent.py" or "agents/factory.py")

    Returns:
        Factory function that creates an LlmAgent.

    Raises:
        OrchestrationError: If module cannot be loaded or has no create_agent function.
    """
    path = Path(module_path)
    if not path.exists():
        msg = f"Agent factory module not found: {module_path}"
        raise OrchestrationError(msg)

    spec = importlib.util.spec_from_file_location("agent_factory", path)
    if spec is None or spec.loader is None:
        msg = f"Cannot load module: {module_path}"
        raise OrchestrationError(msg)

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "create_agent"):
        msg = f"Module {module_path} must have a create_agent() function"
        raise OrchestrationError(msg)

    factory: Callable[[], LlmAgent] = module.create_agent
    return factory
