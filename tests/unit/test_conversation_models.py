"""Tests for conversation data models."""

from mcprobe.models.conversation import (
    AgentResponse,
    ConversationResult,
    ConversationTurn,
    TerminationReason,
    ToolCall,
    UserResponse,
)


class TestUserResponse:
    """Tests for UserResponse model."""

    def test_default_tokens(self) -> None:
        """Test UserResponse has default tokens_used of 0."""
        response = UserResponse(message="Hello", is_satisfied=False)

        assert response.tokens_used == 0

    def test_with_tokens(self) -> None:
        """Test UserResponse with token count."""
        response = UserResponse(
            message="Thanks, that helps!",
            is_satisfied=True,
            tokens_used=150,
        )

        assert response.message == "Thanks, that helps!"
        assert response.is_satisfied is True
        assert response.tokens_used == 150


class TestToolCall:
    """Tests for ToolCall model."""

    def test_successful_call(self) -> None:
        """Test ToolCall for successful invocation."""
        call = ToolCall(
            tool_name="get_weather",
            parameters={"location": "Phoenix"},
            result={"temp": 95, "conditions": "sunny"},
            latency_ms=150.5,
        )

        assert call.tool_name == "get_weather"
        assert call.parameters == {"location": "Phoenix"}
        assert call.result["temp"] == 95
        assert call.latency_ms == 150.5
        assert call.error is None

    def test_failed_call(self) -> None:
        """Test ToolCall with error."""
        call = ToolCall(
            tool_name="get_weather",
            parameters={"location": "invalid"},
            result=None,
            latency_ms=50.0,
            error="Location not found",
        )

        assert call.error == "Location not found"
        assert call.result is None


class TestConversationResult:
    """Tests for ConversationResult model."""

    def test_with_token_count(self) -> None:
        """Test ConversationResult includes token count."""
        result = ConversationResult(
            turns=[
                ConversationTurn(
                    role="user",
                    content="Hello",
                    tool_calls=[],
                    timestamp=1000.0,
                ),
                ConversationTurn(
                    role="assistant",
                    content="Hi there!",
                    tool_calls=[],
                    timestamp=1001.0,
                ),
            ],
            final_answer="Hi there!",
            total_tool_calls=[],
            total_tokens=250,
            duration_seconds=1.5,
            termination_reason=TerminationReason.USER_SATISFIED,
        )

        assert result.total_tokens == 250
        assert len(result.turns) == 2
        assert result.termination_reason == TerminationReason.USER_SATISFIED

    def test_default_token_count(self) -> None:
        """Test ConversationResult default token count is 0."""
        result = ConversationResult(
            turns=[],
            final_answer="",
            total_tool_calls=[],
            duration_seconds=0.5,
            termination_reason=TerminationReason.MAX_TURNS,
        )

        assert result.total_tokens == 0


class TestAgentResponse:
    """Tests for AgentResponse model."""

    def test_with_tool_calls(self) -> None:
        """Test AgentResponse with tool calls."""
        tool_call = ToolCall(
            tool_name="search",
            parameters={"query": "test"},
            result=["result1"],
            latency_ms=100.0,
        )

        response = AgentResponse(
            message="Here's what I found",
            tool_calls=[tool_call],
            is_complete=True,
            metadata={"model": "test"},
        )

        assert response.message == "Here's what I found"
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].tool_name == "search"
        assert response.is_complete is True

    def test_defaults(self) -> None:
        """Test AgentResponse defaults."""
        response = AgentResponse(message="Hello")

        assert response.tool_calls == []
        assert response.is_complete is False
        assert response.metadata == {}
