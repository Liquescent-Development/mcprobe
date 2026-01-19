"""Gemini ADK agent implementation with MCP tool support."""

import importlib.util
import time
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
        self._user_id = "mcprobe_user"

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
        for fr in function_responses:
            call_id = fr.id or fr.name or "unknown"
            if call_id in pending_calls:
                name, params, start = pending_calls.pop(call_id)
            else:
                # Response without matching call - use response info
                name = fr.name or "unknown"
                params = {}
                start = time.time()

            tool_calls.append(
                ToolCall(
                    tool_name=name,
                    parameters=params,
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

                # Get final response text
                if event.is_final_response() and event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            response_text += part.text

            # Handle any calls that never got responses
            for _id, (name, params, start) in pending_calls.items():
                tool_calls.append(
                    ToolCall(
                        tool_name=name,
                        parameters=params,
                        result=None,
                        error="No response received",
                        latency_ms=(time.time() - start) * 1000,
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
        # Create fresh session service
        self._session_service = InMemorySessionService()
        self._runner = Runner(
            agent=self._agent,
            app_name="mcprobe",
            session_service=self._session_service,
        )

    def get_available_tools(self) -> list[dict[str, Any]]:
        """Get tool schemas from ADK agent.

        Returns:
            List of tool schemas (empty for now - async introspection needed).
        """
        # ADK agents have tools attribute with McpToolset
        # Tool introspection requires async call to toolset.get_tools()
        # For now, return empty list - can be enhanced later
        return []


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
