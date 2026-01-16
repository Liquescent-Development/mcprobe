"""Synthetic user LLM implementation.

Simulates a realistic user interacting with an AI assistant.
"""

from pydantic import BaseModel

from mcprobe.exceptions import OrchestrationError
from mcprobe.models.conversation import UserResponse
from mcprobe.models.scenario import SyntheticUserConfig
from mcprobe.providers.base import LLMProvider, Message
from mcprobe.synthetic_user.prompts import (
    build_satisfaction_check_prompt,
    build_synthetic_user_prompt,
)


class SatisfactionResult(BaseModel):
    """Result of checking if the user is satisfied."""

    is_satisfied: bool
    reason: str


class SyntheticUserLLM:
    """LLM-powered synthetic user for testing.

    Simulates a realistic user interacting with an agent, maintaining
    persona consistency and responding naturally to clarification requests.
    """

    def __init__(
        self,
        provider: LLMProvider,
        config: SyntheticUserConfig,
    ) -> None:
        """Initialize the synthetic user.

        Args:
            provider: LLM provider to use for generating responses.
            config: Synthetic user configuration from the test scenario.
        """
        self._provider = provider
        self._config = config
        self._system_prompt = build_synthetic_user_prompt(config)
        self._conversation_history: list[Message] = [
            Message(role="system", content=self._system_prompt)
        ]
        self._questions_asked = 0

    async def get_initial_query(self) -> str:
        """Get the initial query to start the conversation.

        Returns:
            The initial query from the scenario configuration.
        """
        return self._config.initial_query

    async def respond(
        self,
        assistant_message: str,
        *,
        is_final_answer: bool = False,
    ) -> UserResponse:
        """Generate a response to the assistant's message.

        Args:
            assistant_message: The assistant's message to respond to.
            is_final_answer: Whether the assistant considers this a final answer.

        Returns:
            UserResponse with the synthetic user's reply and satisfaction status.

        Raises:
            OrchestrationError: If the LLM call fails.
        """
        # Add assistant message to history
        self._conversation_history.append(
            Message(role="assistant", content=assistant_message)
        )

        # Check if the assistant's message is a question (asking for clarification)
        if assistant_message.strip().endswith("?"):
            self._questions_asked += 1

        # If this is a final answer, check satisfaction
        if is_final_answer:
            is_satisfied = await self._check_satisfaction(assistant_message)
            if is_satisfied:
                # Generate a satisfied response
                response = await self._generate_response(
                    "The assistant has provided a helpful answer. "
                    "Express brief thanks and indicate you're satisfied."
                )
                return UserResponse(message=response, is_satisfied=True)

        # Generate a normal response
        response = await self._generate_response()

        # Check if the response indicates satisfaction
        satisfaction_phrases = [
            "thanks",
            "thank you",
            "that's helpful",
            "that helps",
            "great",
            "perfect",
            "got it",
            "makes sense",
            "answers my question",
        ]
        is_satisfied = any(
            phrase in response.lower() for phrase in satisfaction_phrases
        )

        return UserResponse(message=response, is_satisfied=is_satisfied)

    async def _generate_response(self, guidance: str | None = None) -> str:
        """Generate a response using the LLM.

        Args:
            guidance: Optional additional guidance for the response.

        Returns:
            Generated response text.

        Raises:
            OrchestrationError: If the LLM call fails.
        """
        messages = list(self._conversation_history)

        if guidance:
            messages.append(Message(role="user", content=f"[Guidance: {guidance}]"))

        try:
            response = await self._provider.generate(messages=messages)
        except Exception as e:
            msg = f"Synthetic user failed to generate response: {e}"
            raise OrchestrationError(msg) from e

        # Add our response to history
        self._conversation_history.append(
            Message(role="user", content=response.content)
        )

        return response.content

    async def _check_satisfaction(self, assistant_response: str) -> bool:
        """Check if the user would be satisfied with the response.

        Args:
            assistant_response: The assistant's response to evaluate.

        Returns:
            True if the user would be satisfied.
        """
        prompt = build_satisfaction_check_prompt(
            persona=self._config.persona,
            initial_query=self._config.initial_query,
            assistant_response=assistant_response,
        )

        try:
            result = await self._provider.generate_structured(
                messages=[Message(role="user", content=prompt)],
                response_schema=SatisfactionResult,
            )
            # Result is guaranteed to be SatisfactionResult due to response_schema
            if isinstance(result, SatisfactionResult):
                return result.is_satisfied
            return False
        except Exception:
            # If structured generation fails, fall back to simple check
            return False

    def reset(self) -> None:
        """Reset the synthetic user for a new conversation."""
        self._conversation_history = [
            Message(role="system", content=self._system_prompt)
        ]
        self._questions_asked = 0

    @property
    def questions_asked(self) -> int:
        """Number of clarifying questions the assistant has asked."""
        return self._questions_asked

    @property
    def config(self) -> SyntheticUserConfig:
        """Get the synthetic user configuration."""
        return self._config
