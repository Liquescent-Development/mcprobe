"""Trend analysis for test results.

Analyzes historical test results to detect trends, regressions, and patterns.
"""

from __future__ import annotations

import statistics
from typing import TYPE_CHECKING

from mcprobe.analysis.models import Regression, ScenarioTrends, TrendDirection

# Constants for trend analysis
MIN_DATA_POINTS_FOR_TREND = 3
MIN_DATA_POINTS_FOR_REGRESSION = 4
MIN_DATA_POINTS_FOR_ANALYSIS = 2
SEVERITY_HIGH_THRESHOLD = 0.3
SEVERITY_MEDIUM_THRESHOLD = 0.15

if TYPE_CHECKING:
    from mcprobe.persistence import ResultLoader, TrendEntry


class TrendAnalyzer:
    """Analyzes trends in test results over time."""

    def __init__(
        self,
        loader: ResultLoader,
        slope_threshold: float = 0.05,
    ) -> None:
        """Initialize the trend analyzer.

        Args:
            loader: Result loader for accessing historical data.
            slope_threshold: Threshold for trend detection (default 0.05).
        """
        self._loader = loader
        self._slope_threshold = slope_threshold

    def analyze_scenario(
        self,
        scenario_name: str,
        window_size: int = 10,
    ) -> ScenarioTrends | None:
        """Analyze trends for a specific scenario.

        Args:
            scenario_name: Name of the scenario to analyze.
            window_size: Number of recent runs to consider.

        Returns:
            ScenarioTrends object or None if insufficient data.
        """
        trend_data: list[TrendEntry] = self._loader.load_trend_data(scenario_name)

        if len(trend_data) < MIN_DATA_POINTS_FOR_ANALYSIS:
            return None

        # Use only the most recent window
        recent_data: list[TrendEntry] = trend_data[-window_size:]

        # Extract metrics
        scores: list[float] = [d["score"] for d in recent_data]
        passed_count = sum(1 for d in recent_data if d["passed"])
        durations: list[float] = [d["duration_seconds"] for d in recent_data]
        tool_calls: list[int] = [d["total_tool_calls"] for d in recent_data]
        tokens: list[int] = [d["total_tokens"] for d in recent_data]

        # Calculate statistics
        pass_rate = passed_count / len(recent_data)
        current_score = scores[-1]
        avg_score = statistics.mean(scores)
        min_score = min(scores)
        max_score = max(scores)
        score_variance = statistics.variance(scores) if len(scores) > 1 else 0.0

        # Detect trends
        score_trend = self._detect_trend(scores)
        pass_values = [1.0 if d["passed"] else 0.0 for d in recent_data]
        pass_trend = self._detect_trend(pass_values)

        return ScenarioTrends(
            scenario_name=scenario_name,
            run_count=len(recent_data),
            pass_rate=pass_rate,
            pass_trend=pass_trend,
            current_score=current_score,
            avg_score=avg_score,
            min_score=min_score,
            max_score=max_score,
            score_trend=score_trend,
            score_variance=score_variance,
            avg_duration=statistics.mean(durations) if durations else 0.0,
            avg_tool_calls=statistics.mean(tool_calls) if tool_calls else 0.0,
            avg_tokens=statistics.mean(tokens) if tokens else 0.0,
        )

    def analyze_all(
        self,
        window_size: int = 10,
    ) -> list[ScenarioTrends]:
        """Analyze trends for all scenarios.

        Args:
            window_size: Number of recent runs to consider.

        Returns:
            List of ScenarioTrends for all scenarios with sufficient data.
        """
        scenarios = self._loader.list_scenarios()
        results: list[ScenarioTrends] = []

        for scenario_name in scenarios:
            trends = self.analyze_scenario(scenario_name, window_size)
            if trends is not None:
                results.append(trends)

        return results

    def detect_regressions(
        self,
        pass_rate_threshold: float = 0.1,
        score_threshold: float = 0.1,
    ) -> list[Regression]:
        """Detect regressions across all scenarios.

        Args:
            pass_rate_threshold: Minimum pass rate drop to flag as regression.
            score_threshold: Minimum score drop to flag as regression.

        Returns:
            List of detected regressions.
        """
        regressions: list[Regression] = []

        for scenario_name in self._loader.list_scenarios():
            trend_data: list[TrendEntry] = self._loader.load_trend_data(scenario_name)

            if len(trend_data) < MIN_DATA_POINTS_FOR_REGRESSION:
                continue

            # Compare recent half to earlier half
            mid = len(trend_data) // 2
            recent: list[TrendEntry] = trend_data[mid:]
            earlier: list[TrendEntry] = trend_data[:mid]

            # Pass rate regression
            recent_pass_rate = sum(1 for d in recent if d["passed"]) / len(recent)
            earlier_pass_rate = sum(1 for d in earlier if d["passed"]) / len(earlier)

            if earlier_pass_rate - recent_pass_rate > pass_rate_threshold:
                change = (recent_pass_rate - earlier_pass_rate) / max(earlier_pass_rate, 0.01)
                severity = self._calculate_severity(abs(change))
                regressions.append(
                    Regression(
                        scenario_name=scenario_name,
                        metric="pass_rate",
                        previous_value=earlier_pass_rate,
                        current_value=recent_pass_rate,
                        change_percent=change * 100,
                        severity=severity,
                    )
                )

            # Score regression
            recent_scores: list[float] = [d["score"] for d in recent]
            earlier_scores: list[float] = [d["score"] for d in earlier]
            recent_avg_score = statistics.mean(recent_scores)
            earlier_avg_score = statistics.mean(earlier_scores)

            if earlier_avg_score - recent_avg_score > score_threshold:
                change = (recent_avg_score - earlier_avg_score) / max(earlier_avg_score, 0.01)
                severity = self._calculate_severity(abs(change))
                regressions.append(
                    Regression(
                        scenario_name=scenario_name,
                        metric="score",
                        previous_value=earlier_avg_score,
                        current_value=recent_avg_score,
                        change_percent=change * 100,
                        severity=severity,
                    )
                )

        return regressions

    def _detect_trend(self, values: list[float]) -> TrendDirection:
        """Detect trend direction using linear regression.

        Args:
            values: List of values in chronological order.

        Returns:
            TrendDirection indicating the trend.
        """
        if len(values) < MIN_DATA_POINTS_FOR_TREND:
            return TrendDirection.STABLE

        # Simple linear regression slope
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = statistics.mean(values)

        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return TrendDirection.STABLE

        slope = numerator / denominator

        # Normalize slope by value range
        value_range = max(values) - min(values)
        normalized_slope = slope / value_range if value_range > 0 else slope

        if normalized_slope > self._slope_threshold:
            return TrendDirection.IMPROVING
        if normalized_slope < -self._slope_threshold:
            return TrendDirection.DEGRADING
        return TrendDirection.STABLE

    def _calculate_severity(self, change_magnitude: float) -> str:
        """Calculate severity based on change magnitude.

        Args:
            change_magnitude: Absolute change as a fraction (0-1+).

        Returns:
            Severity level: "low", "medium", or "high".
        """
        if change_magnitude > SEVERITY_HIGH_THRESHOLD:
            return "high"
        if change_magnitude > SEVERITY_MEDIUM_THRESHOLD:
            return "medium"
        return "low"
