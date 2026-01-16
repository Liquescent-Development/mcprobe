"""Tests for judge prompt formatting."""

from mcprobe.judge.prompts import (
    build_judge_prompt,
    format_criteria_list,
    format_tool_call_criteria,
    format_tool_calls,
)
from mcprobe.models.conversation import (
    ConversationResult,
    ConversationTurn,
    TerminationReason,
    ToolCall,
)
from mcprobe.models.scenario import (
    ClarificationBehavior,
    EfficiencyConfig,
    EvaluationConfig,
    SyntheticUserConfig,
    TestScenario,
    ToolCallCriterion,
    ToolUsageConfig,
)


class TestFormatToolCallCriteria:
    """Tests for format_tool_call_criteria function."""

    def test_empty_criteria(self) -> None:
        """Test formatting empty criteria list."""
        result = format_tool_call_criteria([])
        assert result == "None specified"

    def test_single_criterion(self) -> None:
        """Test formatting single tool criterion."""
        criteria = [
            ToolCallCriterion(
                tool="get_weather",
                assertions=["location includes Phoenix"],
            )
        ]

        result = format_tool_call_criteria(criteria)

        assert "Tool: get_weather" in result
        assert "location includes Phoenix" in result

    def test_multiple_criteria(self) -> None:
        """Test formatting multiple tool criteria with multiple assertions."""
        criteria = [
            ToolCallCriterion(
                tool="get_weather",
                assertions=[
                    "location includes Phoenix",
                    "forecast_days >= 3",
                ],
            ),
            ToolCallCriterion(
                tool="search",
                assertions=["query is not empty"],
            ),
        ]

        result = format_tool_call_criteria(criteria)

        assert "Tool: get_weather" in result
        assert "location includes Phoenix" in result
        assert "forecast_days >= 3" in result
        assert "Tool: search" in result
        assert "query is not empty" in result


class TestFormatCriteriaList:
    """Tests for format_criteria_list function."""

    def test_empty_list(self) -> None:
        """Test formatting empty criteria list."""
        result = format_criteria_list([])
        assert result == "None specified"

    def test_single_criterion(self) -> None:
        """Test formatting single criterion."""
        result = format_criteria_list(["Agent responds politely"])
        assert result == "- Agent responds politely"

    def test_multiple_criteria(self) -> None:
        """Test formatting multiple criteria."""
        criteria = [
            "Agent responds politely",
            "Agent provides accurate information",
        ]
        result = format_criteria_list(criteria)

        assert "- Agent responds politely" in result
        assert "- Agent provides accurate information" in result


class TestFormatToolCalls:
    """Tests for format_tool_calls function."""

    def test_no_tool_calls(self) -> None:
        """Test formatting when no tool calls made."""
        result = ConversationResult(
            turns=[],
            final_answer="",
            total_tool_calls=[],
            total_tokens=0,
            duration_seconds=1.0,
            termination_reason=TerminationReason.USER_SATISFIED,
        )

        formatted = format_tool_calls(result)
        assert formatted == "No tool calls were made."

    def test_with_tool_calls(self) -> None:
        """Test formatting tool calls."""
        tool_calls = [
            ToolCall(
                tool_name="get_weather",
                parameters={"location": "Phoenix"},
                result={"temp": 95},
                latency_ms=150.5,
            ),
            ToolCall(
                tool_name="search",
                parameters={"query": "test"},
                result=["item1", "item2"],
                latency_ms=200.0,
            ),
        ]

        result = ConversationResult(
            turns=[],
            final_answer="",
            total_tool_calls=tool_calls,
            total_tokens=100,
            duration_seconds=1.0,
            termination_reason=TerminationReason.USER_SATISFIED,
        )

        formatted = format_tool_calls(result)

        assert "1. get_weather" in formatted
        assert "2. search" in formatted
        assert "Phoenix" in formatted
        assert "150.5ms" in formatted

    def test_tool_call_with_error(self) -> None:
        """Test formatting tool call with error."""
        tool_calls = [
            ToolCall(
                tool_name="get_weather",
                parameters={"location": "invalid"},
                result=None,
                latency_ms=50.0,
                error="Location not found",
            ),
        ]

        result = ConversationResult(
            turns=[],
            final_answer="",
            total_tool_calls=tool_calls,
            total_tokens=0,
            duration_seconds=1.0,
            termination_reason=TerminationReason.ERROR,
        )

        formatted = format_tool_calls(result)

        assert "Error: Location not found" in formatted


class TestBuildJudgePrompt:
    """Tests for build_judge_prompt function."""

    def test_includes_tool_call_criteria(self) -> None:
        """Test that judge prompt includes tool call criteria."""
        scenario = TestScenario(
            name="Weather Test",
            description="Test weather queries",
            synthetic_user=SyntheticUserConfig(
                persona="A user planning a trip",
                initial_query="What's the weather in Phoenix?",
                clarification_behavior=ClarificationBehavior(),
                max_turns=5,
            ),
            evaluation=EvaluationConfig(
                correctness_criteria=["Provides weather info"],
                failure_criteria=[],
                tool_usage=ToolUsageConfig(
                    required_tools=["get_weather"],
                    tool_call_criteria=[
                        ToolCallCriterion(
                            tool="get_weather",
                            assertions=[
                                "location includes Phoenix",
                                "forecast_days >= 3",
                            ],
                        ),
                    ],
                ),
                efficiency=EfficiencyConfig(max_conversation_turns=5),
            ),
        )

        conversation_result = ConversationResult(
            turns=[
                ConversationTurn(
                    role="user",
                    content="What's the weather in Phoenix?",
                    tool_calls=[],
                    timestamp=1000.0,
                ),
            ],
            final_answer="The weather is sunny",
            total_tool_calls=[],
            total_tokens=100,
            duration_seconds=2.0,
            termination_reason=TerminationReason.USER_SATISFIED,
        )

        prompt = build_judge_prompt(scenario, conversation_result)

        # Verify tool call criteria section is included
        assert "Tool Call Criteria" in prompt
        assert "get_weather" in prompt
        assert "location includes Phoenix" in prompt
        assert "forecast_days >= 3" in prompt

    def test_includes_quality_analysis_section(self) -> None:
        """Test that judge prompt includes quality analysis section."""
        scenario = TestScenario(
            name="Test",
            description="Test scenario",
            synthetic_user=SyntheticUserConfig(
                persona="User",
                initial_query="Hello",
                clarification_behavior=ClarificationBehavior(),
                max_turns=5,
            ),
            evaluation=EvaluationConfig(
                correctness_criteria=["Responds"],
                efficiency=EfficiencyConfig(),
            ),
        )

        conversation_result = ConversationResult(
            turns=[],
            final_answer="Hi",
            total_tool_calls=[],
            total_tokens=50,
            duration_seconds=1.0,
            termination_reason=TerminationReason.USER_SATISFIED,
        )

        prompt = build_judge_prompt(scenario, conversation_result)

        # Verify quality analysis section
        assert "Conversation Quality Analysis" in prompt
        assert "clarifying questions" in prompt
        assert "backtrack" in prompt

    def test_includes_structured_suggestions_format(self) -> None:
        """Test that judge prompt requests structured suggestions."""
        scenario = TestScenario(
            name="Test",
            description="Test scenario",
            synthetic_user=SyntheticUserConfig(
                persona="User",
                initial_query="Hello",
                clarification_behavior=ClarificationBehavior(),
                max_turns=5,
            ),
            evaluation=EvaluationConfig(
                correctness_criteria=["Responds"],
                efficiency=EfficiencyConfig(),
            ),
        )

        conversation_result = ConversationResult(
            turns=[],
            final_answer="Hi",
            total_tool_calls=[],
            total_tokens=50,
            duration_seconds=1.0,
            termination_reason=TerminationReason.USER_SATISFIED,
        )

        prompt = build_judge_prompt(scenario, conversation_result)

        # Verify structured suggestions format is requested
        assert "structured_suggestions" in prompt
        assert "category" in prompt
        assert "severity" in prompt
        assert "description|parameter|return_value|schema" in prompt
