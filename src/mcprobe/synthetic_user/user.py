"""Synthetic user LLM implementation.

Simulates a realistic user interacting with an AI assistant.
"""

from mcprobe.exceptions import OrchestrationError
from mcprobe.models.conversation import UserResponse
from mcprobe.models.scenario import SyntheticUserConfig
from mcprobe.providers.base import LLMProvider, Message
from mcprobe.synthetic_user.prompts import build_synthetic_user_prompt


class SyntheticUserLLM:
    """LLM-powered synthetic user for testing.

    Simulates a realistic user interacting with an agent, maintaining
    persona consistency and responding naturally to clarification requests.
    """

    def __init__(
        self,
        provider: LLMProvider,
        config: SyntheticUserConfig,
        extra_instructions: str | None = None,
    ) -> None:
        """Initialize the synthetic user.

        Args:
            provider: LLM provider to use for generating responses.
            config: Synthetic user configuration from the test scenario.
            extra_instructions: Additional instructions to append to the system prompt.
        """
        self._provider = provider
        self._config = config
        self._system_prompt = build_synthetic_user_prompt(config, extra_instructions)
        self._conversation_history: list[Message] = [
            Message(role="system", content=self._system_prompt)
        ]
        self._questions_asked = 0
        self._last_tokens_used = 0

    async def get_initial_query(self) -> str:
        """Get the initial query to start the conversation.

        Returns:
            The initial query from the scenario configuration.
        """
        return self._config.initial_query

    async def respond(self, assistant_message: str) -> UserResponse:
        """Generate a response to the assistant's message.

        The synthetic user generates natural follow-up responses. Termination
        decisions are made by the judge, not by detecting "satisfaction" phrases.

        Args:
            assistant_message: The assistant's message to respond to.

        Returns:
            UserResponse with the synthetic user's reply.

        Raises:
            OrchestrationError: If the LLM call fails.
        """
        # Handle empty agent responses - ask for clarification instead of confusing the LLM
        if not assistant_message.strip():
            response = "I didn't receive a response. Could you try again?"
            self._conversation_history.append(Message(role="assistant", content=assistant_message))
            self._conversation_history.append(Message(role="user", content=response))
            return UserResponse(message=response, tokens_used=0)

        # Add assistant message to history
        self._conversation_history.append(Message(role="assistant", content=assistant_message))

        # Check if the assistant's message is a question (asking for clarification)
        if assistant_message.strip().endswith("?"):
            self._questions_asked += 1

        # Generate a natural follow-up response
        response = await self._generate_response()

        return UserResponse(
            message=response,
            tokens_used=self._last_tokens_used,
        )

    async def _generate_response(self, guidance: str | None = None) -> str:
        """Generate a response using the LLM.

        Args:
            guidance: Optional additional guidance for the response.

        Returns:
            Generated response text.

        Raises:
            OrchestrationError: If the LLM call fails.
        """
        # Swap roles so the LLM naturally generates from the assistant position.
        # This prevents smaller models from slipping into assistant behavior when
        # they should be acting as the user. From the LLM's perspective:
        # - Agent messages (originally "assistant") become "user" (incoming)
        # - Synthetic user messages (originally "user") become "assistant" (outgoing)
        # - System prompt stays as "system"
        messages = []
        for msg in self._conversation_history:
            if msg.role == "assistant":
                messages.append(Message(role="user", content=msg.content))
            elif msg.role == "user":
                messages.append(Message(role="assistant", content=msg.content))
            else:
                messages.append(msg)  # system stays as-is

        if guidance:
            # Guidance comes from system, presented as user message in swapped context
            messages.append(Message(role="user", content=f"[Guidance: {guidance}]"))

        try:
            response = await self._provider.generate(messages=messages)
        except Exception as e:
            error_msg = f"Synthetic user failed to generate response: {e}"
            raise OrchestrationError(error_msg) from e

        # Track token usage
        self._last_tokens_used = response.usage.get("prompt_tokens", 0) + response.usage.get(
            "completion_tokens", 0
        )

        content = response.content.strip()

        # Handle empty responses - indicate satisfaction instead of sending empty message
        if not content:
            content = "Thanks, that answers my question."

        # Add our response to history
        self._conversation_history.append(Message(role="user", content=content))

        return content

    def reset(self) -> None:
        """Reset the synthetic user for a new conversation."""
        self._conversation_history = [Message(role="system", content=self._system_prompt)]
        self._questions_asked = 0
        self._last_tokens_used = 0

    @property
    def questions_asked(self) -> int:
        """Number of clarifying questions the assistant has asked."""
        return self._questions_asked

    @property
    def config(self) -> SyntheticUserConfig:
        """Get the synthetic user configuration."""
        return self._config
