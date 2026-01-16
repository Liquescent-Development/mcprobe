"""Judgment data models.

Defines the structure for evaluation results from the judge LLM.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SuggestionCategory(str, Enum):
    """Category of MCP server improvement suggestion."""

    DESCRIPTION = "description"
    PARAMETER = "parameter"
    RETURN_VALUE = "return_value"
    SCHEMA = "schema"


class SuggestionSeverity(str, Enum):
    """Severity level of an improvement suggestion."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class QualityMetrics(BaseModel):
    """Conversation quality measurements."""

    clarification_count: int = 0
    backtrack_count: int = 0
    turns_to_first_answer: int = 0
    final_answer_completeness: float = Field(default=0.0, ge=0.0, le=1.0)


class MCPSuggestion(BaseModel):
    """Structured suggestion for MCP server improvement."""

    category: SuggestionCategory
    tool_name: str | None = None
    issue: str
    suggestion: str
    severity: SuggestionSeverity = SuggestionSeverity.MEDIUM


class JudgmentResult(BaseModel):
    """Result of evaluating a conversation against test criteria."""

    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    correctness_results: dict[str, bool]  # criterion -> passed
    failure_results: dict[str, bool]  # criterion -> triggered
    tool_usage_results: dict[str, Any]
    efficiency_results: dict[str, Any]
    reasoning: str
    suggestions: list[str] = Field(default_factory=list)
    quality_metrics: QualityMetrics = Field(default_factory=QualityMetrics)
    structured_suggestions: list[MCPSuggestion] = Field(default_factory=list)
