"""Simple LLM agent without tools.

A basic agent implementation that uses an LLM provider for conversation
without any tool calling. Useful for Phase 1 testing and as a baseline.
"""

from mcprobe.agents.base import AgentUnderTest
from mcprobe.exceptions import OrchestrationError
from mcprobe.models.conversation import AgentResponse
from mcprobe.providers.base import LLMProvider, Message


class SimpleLLMAgent(AgentUnderTest):
    """Simple agent that uses an LLM for conversation without tools.

    This agent maintains conversation history and sends messages to an
    LLM provider. It does not support tool calling - responses are
    purely text-based.
    """

    def __init__(
        self,
        provider: LLMProvider,
        system_prompt: str | None = None,
        agent_name: str = "SimpleLLMAgent",
    ) -> None:
        """Initialize the simple agent.

        Args:
            provider: LLM provider to use for generating responses.
            system_prompt: Optional system prompt to set agent behavior.
            agent_name: Human-readable name for this agent.
        """
        self._provider = provider
        self._system_prompt = system_prompt
        self._agent_name = agent_name
        self._conversation_history: list[Message] = []

        # Add system prompt if provided
        if system_prompt:
            self._conversation_history.append(Message(role="system", content=system_prompt))

    async def send_message(self, message: str) -> AgentResponse:
        """Send a user message and get the agent's response.

        Args:
            message: The user's message text.

        Returns:
            AgentResponse containing the agent's text reply.

        Raises:
            OrchestrationError: If the LLM call fails.
        """
        # Add user message to history
        user_msg = Message(role="user", content=message)
        self._conversation_history.append(user_msg)

        try:
            response = await self._provider.generate(
                messages=self._conversation_history,
            )
        except Exception as e:
            msg = f"Agent failed to generate response: {e}"
            raise OrchestrationError(msg) from e

        # Add assistant response to history
        assistant_msg = Message(role="assistant", content=response.content)
        self._conversation_history.append(assistant_msg)

        # Determine if the response seems complete
        # For a simple agent, we consider it complete if it's not asking a question
        is_complete = not response.content.strip().endswith("?")

        return AgentResponse(
            message=response.content,
            tool_calls=[],  # Simple agent has no tools
            is_complete=is_complete,
            metadata={
                "usage": response.usage,
                "finish_reason": response.finish_reason,
            },
        )

    async def reset(self) -> None:
        """Reset conversation state for a new test."""
        self._conversation_history = []

        # Re-add system prompt if it was set
        if self._system_prompt:
            self._conversation_history.append(Message(role="system", content=self._system_prompt))

    async def get_available_tools(self) -> list[dict[str, object]]:
        """Return empty list - simple agent has no tools."""
        return []

    @property
    def name(self) -> str:
        """Human-readable name for this agent."""
        return self._agent_name

    @property
    def conversation_history(self) -> list[Message]:
        """Get the current conversation history (read-only)."""
        return list(self._conversation_history)

    def get_system_prompt(self) -> str | None:
        """Return the agent's system prompt."""
        return self._system_prompt
