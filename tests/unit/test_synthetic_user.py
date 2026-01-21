"""Tests for synthetic user token tracking."""

from unittest.mock import AsyncMock

import pytest

from mcprobe.models.scenario import (
    ClarificationBehavior,
    SyntheticUserConfig,
)
from mcprobe.providers.base import LLMProvider, LLMResponse
from mcprobe.synthetic_user.user import SyntheticUserLLM


@pytest.fixture
def mock_provider() -> LLMProvider:
    """Create a mock LLM provider."""
    provider = AsyncMock(spec=LLMProvider)
    return provider


@pytest.fixture
def user_config() -> SyntheticUserConfig:
    """Create a synthetic user config."""
    return SyntheticUserConfig(
        persona="A helpful test user",
        initial_query="Hello, can you help me?",
        clarification_behavior=ClarificationBehavior(),
        max_turns=5,
    )


class TestSyntheticUserTokenTracking:
    """Tests for token tracking in SyntheticUserLLM."""

    @pytest.mark.asyncio
    async def test_respond_returns_tokens_used(
        self,
        mock_provider: LLMProvider,
        user_config: SyntheticUserConfig,
    ) -> None:
        """Test that respond returns token count from LLM response."""
        # Mock LLM response with token usage
        mock_response = LLMResponse(
            content="Sure, I can help with that!",
            tool_calls=[],
            finish_reason="stop",
            usage={"prompt_tokens": 100, "completion_tokens": 50},
        )
        mock_provider.generate = AsyncMock(return_value=mock_response)

        user = SyntheticUserLLM(mock_provider, user_config)
        response = await user.respond("How can I assist you today?")

        # Verify tokens are tracked
        assert response.tokens_used == 150  # 100 + 50

    @pytest.mark.asyncio
    async def test_respond_tracks_clarifying_questions(
        self,
        mock_provider: LLMProvider,
        user_config: SyntheticUserConfig,
    ) -> None:
        """Test that respond tracks clarifying questions from the agent."""
        mock_response = LLMResponse(
            content="The answer is 42.",
            tool_calls=[],
            finish_reason="stop",
            usage={"prompt_tokens": 80, "completion_tokens": 30},
        )
        mock_provider.generate = AsyncMock(return_value=mock_response)

        user = SyntheticUserLLM(mock_provider, user_config)

        # Agent asks a clarifying question
        await user.respond("Can you tell me more about your request?")

        assert user.questions_asked == 1

        # Agent provides an answer (not a question)
        await user.respond("Here's your answer.")

        # Count stays at 1 since second message wasn't a question
        assert user.questions_asked == 1

    @pytest.mark.asyncio
    async def test_tokens_reset_on_reset(
        self,
        mock_provider: LLMProvider,
        user_config: SyntheticUserConfig,
    ) -> None:
        """Test that token tracking resets when user is reset."""
        mock_response = LLMResponse(
            content="Response",
            tool_calls=[],
            finish_reason="stop",
            usage={"prompt_tokens": 50, "completion_tokens": 25},
        )
        mock_provider.generate = AsyncMock(return_value=mock_response)

        user = SyntheticUserLLM(mock_provider, user_config)

        # First response
        response1 = await user.respond("Message 1")
        assert response1.tokens_used == 75

        # Reset user
        user.reset()

        # Verify internal state is reset
        assert user._last_tokens_used == 0

    @pytest.mark.asyncio
    async def test_tokens_default_to_zero_on_missing_usage(
        self,
        mock_provider: LLMProvider,
        user_config: SyntheticUserConfig,
    ) -> None:
        """Test that tokens default to 0 if usage info is missing keys."""
        mock_response = LLMResponse(
            content="Response",
            tool_calls=[],
            finish_reason="stop",
            usage={},  # Empty usage dict
        )
        mock_provider.generate = AsyncMock(return_value=mock_response)

        user = SyntheticUserLLM(mock_provider, user_config)
        response = await user.respond("Hello")

        assert response.tokens_used == 0
