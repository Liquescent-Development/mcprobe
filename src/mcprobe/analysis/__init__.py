"""Analysis module for trend detection and flaky test identification."""

from mcprobe.analysis.flaky import FlakyDetector
from mcprobe.analysis.models import (
    FlakyScenario,
    Regression,
    ScenarioTrends,
    TrendDirection,
)
from mcprobe.analysis.trends import TrendAnalyzer

__all__ = [
    "FlakyDetector",
    "FlakyScenario",
    "Regression",
    "ScenarioTrends",
    "TrendAnalyzer",
    "TrendDirection",
]
