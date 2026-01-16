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
