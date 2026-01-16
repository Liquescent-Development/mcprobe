"""Judgment data models.

Defines the structure for evaluation results from the judge LLM.
"""

from typing import Any

from pydantic import BaseModel, Field


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
