"""Integration tests for Phase 3 enhanced evaluation features."""

from unittest.mock import AsyncMock

import pytest

from mcprobe.judge.judge import (
    ConversationJudge,
    JudgeEvaluation,
    JudgeQualityMetrics,
    JudgeStructuredSuggestion,
)
from mcprobe.models.conversation import (
    ConversationResult,
    ConversationTurn,
    TerminationReason,
    ToolCall,
)
from mcprobe.models.judgment import SuggestionCategory, SuggestionSeverity
from mcprobe.models.scenario import (
    ClarificationBehavior,
    EfficiencyConfig,
    EvaluationConfig,
    SyntheticUserConfig,
    TestScenario,
    ToolCallCriterion,
    ToolUsageConfig,
)
from mcprobe.providers.base import LLMProvider


@pytest.fixture
def mock_provider() -> LLMProvider:
    """Create a mock LLM provider."""
    provider = AsyncMock(spec=LLMProvider)
    return provider


@pytest.fixture
def sample_scenario() -> TestScenario:
    """Create a sample test scenario with tool call criteria."""
    return TestScenario(
        name="Weather Query Test",
        description="Test weather tool usage",
        synthetic_user=SyntheticUserConfig(
            persona="A user planning a trip to Phoenix",
            initial_query="What's the weather in Phoenix for the next week?",
            clarification_behavior=ClarificationBehavior(),
            max_turns=5,
        ),
        evaluation=EvaluationConfig(
            correctness_criteria=[
                "Provides weather forecast for Phoenix",
                "Includes temperature information",
            ],
            failure_criteria=[
                "Provides weather for wrong city",
            ],
            tool_usage=ToolUsageConfig(
                required_tools=["get_weather_forecast"],
                prohibited_tools=["delete_data"],
                tool_call_criteria=[
                    ToolCallCriterion(
                        tool="get_weather_forecast",
                        assertions=[
                            "location parameter includes Phoenix",
                            "forecast_days >= 5",
                        ],
                    ),
                ],
            ),
            efficiency=EfficiencyConfig(
                max_tool_calls=3,
                max_conversation_turns=5,
            ),
        ),
    )


@pytest.fixture
def sample_conversation_result() -> ConversationResult:
    """Create a sample conversation result with tool calls and tokens."""
    return ConversationResult(
        turns=[
            ConversationTurn(
                role="user",
                content="What's the weather in Phoenix for the next week?",
                tool_calls=[],
                timestamp=1000.0,
            ),
            ConversationTurn(
                role="assistant",
                content="Let me check the weather forecast for Phoenix.",
                tool_calls=[
                    ToolCall(
                        tool_name="get_weather_forecast",
                        parameters={"location": "Phoenix, AZ", "forecast_days": 7},
                        result={"forecast": [{"day": 1, "temp": 95}]},
                        latency_ms=150.0,
                    ),
                ],
                timestamp=1001.0,
            ),
            ConversationTurn(
                role="assistant",
                content="The weather in Phoenix for the next week shows temperatures around 95°F.",
                tool_calls=[],
                timestamp=1002.0,
            ),
            ConversationTurn(
                role="user",
                content="Thanks, that's helpful!",
                tool_calls=[],
                timestamp=1003.0,
            ),
        ],
        final_answer="The weather in Phoenix for the next week shows temperatures around 95°F.",
        total_tool_calls=[
            ToolCall(
                tool_name="get_weather_forecast",
                parameters={"location": "Phoenix, AZ", "forecast_days": 7},
                result={"forecast": [{"day": 1, "temp": 95}]},
                latency_ms=150.0,
            ),
        ],
        total_tokens=450,
        duration_seconds=3.5,
        termination_reason=TerminationReason.CRITERIA_MET,
    )


class TestJudgeEvaluationPhase3:
    """Tests for Phase 3 judge evaluation features."""

    @pytest.mark.asyncio
    async def test_judge_returns_quality_metrics(
        self,
        mock_provider: LLMProvider,
        sample_scenario: TestScenario,
        sample_conversation_result: ConversationResult,
    ) -> None:
        """Test that judge evaluation includes quality metrics."""
        # Set up mock to return evaluation with quality metrics
        mock_evaluation = JudgeEvaluation(
            passed=True,
            score=0.9,
            correctness_results={
                "Provides weather forecast for Phoenix": True,
                "Includes temperature information": True,
            },
            failure_results={
                "Provides weather for wrong city": False,
            },
            tool_usage_results={
                "required_tools_used": ["get_weather_forecast"],
                "prohibited_tools_used": [],
                "all_required_used": True,
                "no_prohibited_used": True,
                "criteria_results": {
                    "get_weather_forecast": {
                        "location parameter includes Phoenix": True,
                        "forecast_days >= 5": True,
                    }
                },
            },
            efficiency_results={
                "tool_calls": 1,
                "conversation_turns": 4,
                "within_limits": True,
            },
            reasoning="Agent successfully retrieved weather forecast",
            suggestions=["Consider showing multiple days"],
            quality_metrics=JudgeQualityMetrics(
                clarification_count=0,
                backtrack_count=0,
                turns_to_first_answer=2,
                final_answer_completeness=0.9,
            ),
            structured_suggestions=[],
        )

        mock_provider.generate_structured = AsyncMock(return_value=mock_evaluation)

        judge = ConversationJudge(mock_provider)
        result = await judge.evaluate(sample_scenario, sample_conversation_result)

        # Verify quality metrics are in result
        assert result.quality_metrics.clarification_count == 0
        assert result.quality_metrics.backtrack_count == 0
        assert result.quality_metrics.turns_to_first_answer == 2
        assert result.quality_metrics.final_answer_completeness == 0.9

    @pytest.mark.asyncio
    async def test_judge_returns_structured_suggestions(
        self,
        mock_provider: LLMProvider,
        sample_scenario: TestScenario,
        sample_conversation_result: ConversationResult,
    ) -> None:
        """Test that judge evaluation includes structured suggestions."""
        mock_evaluation = JudgeEvaluation(
            passed=True,
            score=0.85,
            correctness_results={"criterion": True},
            failure_results={},
            tool_usage_results={
                "required_tools_used": ["get_weather_forecast"],
                "prohibited_tools_used": [],
                "all_required_used": True,
                "no_prohibited_used": True,
            },
            efficiency_results={"within_limits": True},
            reasoning="Good but could improve",
            suggestions=["Add more days"],
            quality_metrics=JudgeQualityMetrics(),
            structured_suggestions=[
                JudgeStructuredSuggestion(
                    category="parameter",
                    tool_name="get_weather_forecast",
                    issue="Default forecast_days not documented",
                    suggestion="Add default value to parameter description",
                    severity="low",
                ),
                JudgeStructuredSuggestion(
                    category="return_value",
                    tool_name="get_weather_forecast",
                    issue="Temperature units not specified",
                    suggestion="Document whether temp is in Celsius or Fahrenheit",
                    severity="medium",
                ),
            ],
        )

        mock_provider.generate_structured = AsyncMock(return_value=mock_evaluation)

        judge = ConversationJudge(mock_provider)
        result = await judge.evaluate(sample_scenario, sample_conversation_result)

        # Verify structured suggestions
        assert len(result.structured_suggestions) == 2

        # First suggestion
        assert result.structured_suggestions[0].category == SuggestionCategory.PARAMETER
        assert result.structured_suggestions[0].tool_name == "get_weather_forecast"
        assert result.structured_suggestions[0].severity == SuggestionSeverity.LOW

        # Second suggestion
        assert result.structured_suggestions[1].category == SuggestionCategory.RETURN_VALUE
        assert result.structured_suggestions[1].severity == SuggestionSeverity.MEDIUM

    @pytest.mark.asyncio
    async def test_judge_includes_token_count_in_efficiency(
        self,
        mock_provider: LLMProvider,
        sample_scenario: TestScenario,
        sample_conversation_result: ConversationResult,
    ) -> None:
        """Test that efficiency results include token count from conversation."""
        mock_evaluation = JudgeEvaluation(
            passed=True,
            score=0.9,
            correctness_results={},
            failure_results={},
            tool_usage_results={
                "required_tools_used": [],
                "all_required_used": True,
                "no_prohibited_used": True,
            },
            efficiency_results={"within_limits": True},
            reasoning="Efficient",
            suggestions=[],
            quality_metrics=JudgeQualityMetrics(),
            structured_suggestions=[],
        )

        mock_provider.generate_structured = AsyncMock(return_value=mock_evaluation)

        judge = ConversationJudge(mock_provider)
        result = await judge.evaluate(sample_scenario, sample_conversation_result)

        # Verify token count is included from conversation result
        assert result.efficiency_results["total_tokens"] == 450

    @pytest.mark.asyncio
    async def test_judge_includes_criteria_results(
        self,
        mock_provider: LLMProvider,
        sample_scenario: TestScenario,
        sample_conversation_result: ConversationResult,
    ) -> None:
        """Test that tool usage includes criteria evaluation results."""
        mock_evaluation = JudgeEvaluation(
            passed=True,
            score=0.85,
            correctness_results={},
            failure_results={},
            tool_usage_results={
                "required_tools_used": ["get_weather_forecast"],
                "prohibited_tools_used": [],
                "all_required_used": True,
                "no_prohibited_used": True,
                "criteria_results": {
                    "get_weather_forecast": {
                        "location parameter includes Phoenix": True,
                        "forecast_days >= 5": False,  # Criterion not met
                    }
                },
            },
            efficiency_results={"within_limits": True},
            reasoning="Tool used but criteria partially met",
            suggestions=[],
            quality_metrics=JudgeQualityMetrics(),
            structured_suggestions=[],
        )

        mock_provider.generate_structured = AsyncMock(return_value=mock_evaluation)

        judge = ConversationJudge(mock_provider)
        result = await judge.evaluate(sample_scenario, sample_conversation_result)

        # Verify criteria results are preserved
        criteria_results = result.tool_usage_results.get("criteria_results", {})
        assert "get_weather_forecast" in criteria_results
        assert criteria_results["get_weather_forecast"]["location parameter includes Phoenix"]
        assert not criteria_results["get_weather_forecast"]["forecast_days >= 5"]

    @pytest.mark.asyncio
    async def test_invalid_category_falls_back_to_default(
        self,
        mock_provider: LLMProvider,
        sample_scenario: TestScenario,
        sample_conversation_result: ConversationResult,
    ) -> None:
        """Test that invalid suggestion category falls back to DESCRIPTION."""
        mock_evaluation = JudgeEvaluation(
            passed=True,
            score=0.9,
            correctness_results={},
            failure_results={},
            tool_usage_results={
                "required_tools_used": [],
                "all_required_used": True,
                "no_prohibited_used": True,
            },
            efficiency_results={"within_limits": True},
            reasoning="OK",
            suggestions=[],
            quality_metrics=JudgeQualityMetrics(),
            structured_suggestions=[
                JudgeStructuredSuggestion(
                    category="invalid_category",  # Invalid category
                    tool_name=None,
                    issue="Some issue",
                    suggestion="Some fix",
                    severity="invalid_severity",  # Invalid severity
                ),
            ],
        )

        mock_provider.generate_structured = AsyncMock(return_value=mock_evaluation)

        judge = ConversationJudge(mock_provider)
        result = await judge.evaluate(sample_scenario, sample_conversation_result)

        # Should fall back to defaults
        assert len(result.structured_suggestions) == 1
        assert result.structured_suggestions[0].category == SuggestionCategory.DESCRIPTION
        assert result.structured_suggestions[0].severity == SuggestionSeverity.MEDIUM
