"""Abstract base class for agents under test.

Defines the interface that all agent implementations must follow.
"""

from abc import ABC, abstractmethod

from mcprobe.models.conversation import AgentResponse


class AgentUnderTest(ABC):
    """Abstract base class for agents being tested.

    An agent under test receives messages and generates responses,
    potentially using tools. This interface allows MCProbe to test
    any type of agent implementation.
    """

    @abstractmethod
    async def send_message(self, message: str) -> AgentResponse:
        """Send a user message and get the agent's response.

        Args:
            message: The user's message text.

        Returns:
            AgentResponse containing the agent's reply and any tool calls.

        Raises:
            OrchestrationError: If the agent fails to respond.
        """
        ...

    @abstractmethod
    async def reset(self) -> None:
        """Reset conversation state for a new test.

        This should clear any conversation history and return the agent
        to its initial state.
        """
        ...

    @abstractmethod
    def get_available_tools(self) -> list[dict[str, object]]:
        """Return the tool schemas available to this agent.

        Returns:
            List of tool definitions in OpenAI-compatible format.
            Empty list if the agent has no tools.
        """
        ...

    @property
    def name(self) -> str:
        """Human-readable name for this agent.

        Returns:
            Agent name for display purposes.
        """
        return self.__class__.__name__

    def get_system_prompt(self) -> str | None:
        """Return the agent's system prompt if available.

        This is used to track prompt changes that may affect test results.
        Implementations should override this if they have access to the
        agent's system prompt.

        Returns:
            The system prompt string, or None if not available.
        """
        return None

    def get_model_name(self) -> str | None:
        """Return the model name used by this agent if available.

        This is used to track which model the agent uses, which can affect
        test results. Implementations should override this if they have
        access to the model information.

        Returns:
            The model name string, or None if not available.
        """
        return None

    async def close(self) -> None:  # noqa: B027 - Default impl is intentionally empty
        """Clean up any resources held by the agent.

        This is called after test completion to close connections,
        stop background tasks, etc. Default implementation does nothing.
        Subclasses should override if they hold resources that need cleanup.
        """
