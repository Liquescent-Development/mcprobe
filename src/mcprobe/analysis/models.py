"""Analysis data models."""

from enum import Enum

from pydantic import BaseModel, Field


class TrendDirection(str, Enum):
    """Direction of a metric trend."""

    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"


class ScenarioTrends(BaseModel):
    """Trend analysis for a single scenario."""

    scenario_name: str
    run_count: int

    # Pass/fail metrics
    pass_rate: float = Field(ge=0.0, le=1.0)
    pass_trend: TrendDirection = TrendDirection.STABLE

    # Score metrics
    current_score: float = Field(ge=0.0, le=1.0)
    avg_score: float = Field(ge=0.0, le=1.0)
    min_score: float = Field(ge=0.0, le=1.0)
    max_score: float = Field(ge=0.0, le=1.0)
    score_trend: TrendDirection = TrendDirection.STABLE
    score_variance: float = 0.0

    # Performance metrics
    avg_duration: float = 0.0
    avg_tool_calls: float = 0.0
    avg_tokens: float = 0.0


class Regression(BaseModel):
    """Represents a detected regression."""

    scenario_name: str
    metric: str  # "pass_rate", "score", etc.
    previous_value: float
    current_value: float
    change_percent: float
    severity: str  # "low", "medium", "high"


class FlakyScenario(BaseModel):
    """Represents a flaky scenario detection."""

    scenario_name: str
    pass_rate: float
    score_variance: float | None = None
    coefficient_of_variation: float | None = None
    reason: str
    severity: str  # "low", "medium", "high"
    run_count: int = 0
