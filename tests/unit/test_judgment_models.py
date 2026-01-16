"""Tests for judgment data models."""

import pytest
from pydantic import ValidationError

from mcprobe.models.judgment import (
    JudgmentResult,
    MCPSuggestion,
    QualityMetrics,
    SuggestionCategory,
    SuggestionSeverity,
)


class TestQualityMetrics:
    """Tests for QualityMetrics model."""

    def test_default_values(self) -> None:
        """Test QualityMetrics has sensible defaults."""
        metrics = QualityMetrics()

        assert metrics.clarification_count == 0
        assert metrics.backtrack_count == 0
        assert metrics.turns_to_first_answer == 0
        assert metrics.final_answer_completeness == 0.0

    def test_custom_values(self) -> None:
        """Test QualityMetrics with custom values."""
        metrics = QualityMetrics(
            clarification_count=3,
            backtrack_count=1,
            turns_to_first_answer=2,
            final_answer_completeness=0.85,
        )

        assert metrics.clarification_count == 3
        assert metrics.backtrack_count == 1
        assert metrics.turns_to_first_answer == 2
        assert metrics.final_answer_completeness == 0.85

    def test_completeness_validation(self) -> None:
        """Test final_answer_completeness is bounded 0-1."""
        # Valid boundary values
        QualityMetrics(final_answer_completeness=0.0)
        QualityMetrics(final_answer_completeness=1.0)

        # Invalid values
        with pytest.raises(ValidationError):
            QualityMetrics(final_answer_completeness=-0.1)

        with pytest.raises(ValidationError):
            QualityMetrics(final_answer_completeness=1.1)


class TestMCPSuggestion:
    """Tests for MCPSuggestion model."""

    def test_minimal_suggestion(self) -> None:
        """Test MCPSuggestion with minimal required fields."""
        suggestion = MCPSuggestion(
            category=SuggestionCategory.DESCRIPTION,
            issue="Tool description unclear",
            suggestion="Add more detail about expected input format",
        )

        assert suggestion.category == SuggestionCategory.DESCRIPTION
        assert suggestion.tool_name is None
        assert suggestion.issue == "Tool description unclear"
        assert suggestion.suggestion == "Add more detail about expected input format"
        assert suggestion.severity == SuggestionSeverity.MEDIUM  # default

    def test_full_suggestion(self) -> None:
        """Test MCPSuggestion with all fields."""
        suggestion = MCPSuggestion(
            category=SuggestionCategory.PARAMETER,
            tool_name="get_weather",
            issue="Location parameter format not documented",
            suggestion="Specify that location should be city name or coordinates",
            severity=SuggestionSeverity.HIGH,
        )

        assert suggestion.category == SuggestionCategory.PARAMETER
        assert suggestion.tool_name == "get_weather"
        assert suggestion.severity == SuggestionSeverity.HIGH

    def test_all_categories(self) -> None:
        """Test all suggestion categories are valid."""
        for category in SuggestionCategory:
            suggestion = MCPSuggestion(
                category=category,
                issue="test issue",
                suggestion="test suggestion",
            )
            assert suggestion.category == category

    def test_all_severities(self) -> None:
        """Test all severity levels are valid."""
        for severity in SuggestionSeverity:
            suggestion = MCPSuggestion(
                category=SuggestionCategory.DESCRIPTION,
                issue="test issue",
                suggestion="test suggestion",
                severity=severity,
            )
            assert suggestion.severity == severity


class TestJudgmentResult:
    """Tests for JudgmentResult model."""

    def test_minimal_result(self) -> None:
        """Test JudgmentResult with minimal required fields."""
        result = JudgmentResult(
            passed=True,
            score=0.9,
            correctness_results={"criterion1": True},
            failure_results={"bad_thing": False},
            tool_usage_results={},
            efficiency_results={},
            reasoning="Test passed successfully",
        )

        assert result.passed is True
        assert result.score == 0.9
        assert result.suggestions == []  # default
        assert result.quality_metrics.clarification_count == 0  # default
        assert result.structured_suggestions == []  # default

    def test_full_result(self) -> None:
        """Test JudgmentResult with all fields including Phase 3 additions."""
        quality_metrics = QualityMetrics(
            clarification_count=2,
            backtrack_count=0,
            turns_to_first_answer=3,
            final_answer_completeness=0.95,
        )

        structured_suggestions = [
            MCPSuggestion(
                category=SuggestionCategory.PARAMETER,
                tool_name="search",
                issue="Limit parameter unclear",
                suggestion="Document max value",
                severity=SuggestionSeverity.LOW,
            )
        ]

        result = JudgmentResult(
            passed=True,
            score=0.85,
            correctness_results={"c1": True, "c2": True},
            failure_results={"f1": False},
            tool_usage_results={"required_tools_used": ["search"]},
            efficiency_results={"total_tokens": 500, "within_limits": True},
            reasoning="Good performance",
            suggestions=["Consider caching"],
            quality_metrics=quality_metrics,
            structured_suggestions=structured_suggestions,
        )

        assert result.quality_metrics.clarification_count == 2
        assert result.quality_metrics.final_answer_completeness == 0.95
        assert len(result.structured_suggestions) == 1
        assert result.structured_suggestions[0].tool_name == "search"

    def test_score_validation(self) -> None:
        """Test score is bounded 0-1."""
        # Valid
        JudgmentResult(
            passed=True,
            score=0.0,
            correctness_results={},
            failure_results={},
            tool_usage_results={},
            efficiency_results={},
            reasoning="",
        )
        JudgmentResult(
            passed=True,
            score=1.0,
            correctness_results={},
            failure_results={},
            tool_usage_results={},
            efficiency_results={},
            reasoning="",
        )

        # Invalid
        with pytest.raises(ValidationError):
            JudgmentResult(
                passed=True,
                score=-0.1,
                correctness_results={},
                failure_results={},
                tool_usage_results={},
                efficiency_results={},
                reasoning="",
            )

        with pytest.raises(ValidationError):
            JudgmentResult(
                passed=True,
                score=1.1,
                correctness_results={},
                failure_results={},
                tool_usage_results={},
                efficiency_results={},
                reasoning="",
            )
