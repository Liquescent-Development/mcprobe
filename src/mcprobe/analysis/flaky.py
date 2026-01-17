"""Flaky test detection for MCProbe.

Identifies scenarios with inconsistent behavior using statistical analysis.
"""

from __future__ import annotations

import statistics
from typing import TYPE_CHECKING

from mcprobe.analysis.models import FlakyScenario

# Constants for stability analysis
STABILITY_PASS_RATE_HIGH = 0.95
STABILITY_PASS_RATE_LOW = 0.05
STABILITY_CV_THRESHOLD = 0.15

if TYPE_CHECKING:
    from mcprobe.persistence import ResultLoader, TrendEntry


class FlakyDetector:
    """Detects flaky (inconsistent) test scenarios."""

    def __init__(self, loader: ResultLoader) -> None:
        """Initialize the flaky detector.

        Args:
            loader: Result loader for accessing historical data.
        """
        self._loader = loader

    def detect_flaky_scenarios(
        self,
        min_runs: int = 5,
        pass_fail_threshold: tuple[float, float] = (0.2, 0.8),
        cv_threshold: float = 0.25,
    ) -> list[FlakyScenario]:
        """Identify flaky scenarios based on historical data.

        A scenario is considered flaky if:
        1. Its pass rate is between the thresholds (neither always passing nor always failing)
        2. Its score has high variance (coefficient of variation > threshold)

        Args:
            min_runs: Minimum runs required for analysis.
            pass_fail_threshold: (min, max) pass rate range considered flaky.
            cv_threshold: Coefficient of variation threshold for score variance.

        Returns:
            List of detected flaky scenarios.
        """
        flaky: list[FlakyScenario] = []

        for scenario_name in self._loader.list_scenarios():
            trend_data: list[TrendEntry] = self._loader.load_trend_data(scenario_name)

            if len(trend_data) < min_runs:
                continue

            # Calculate pass rate
            pass_count = sum(1 for d in trend_data if d["passed"])
            pass_rate = pass_count / len(trend_data)

            # Check 1: Pass/Fail inconsistency
            if pass_fail_threshold[0] < pass_rate < pass_fail_threshold[1]:
                flaky.append(
                    FlakyScenario(
                        scenario_name=scenario_name,
                        pass_rate=pass_rate,
                        reason="Inconsistent pass/fail results",
                        severity="high",
                        run_count=len(trend_data),
                    )
                )
                continue

            # Check 2: Score variance (among passing runs)
            passing_scores: list[float] = [d["score"] for d in trend_data if d["passed"]]

            if len(passing_scores) >= min_runs:
                mean_score = statistics.mean(passing_scores)
                std_score = statistics.stdev(passing_scores)

                if mean_score > 0:
                    cv = std_score / mean_score

                    if cv > cv_threshold:
                        flaky.append(
                            FlakyScenario(
                                scenario_name=scenario_name,
                                pass_rate=pass_rate,
                                score_variance=statistics.variance(passing_scores),
                                coefficient_of_variation=cv,
                                reason=f"High score variance (CV={cv:.2%})",
                                severity="medium",
                                run_count=len(trend_data),
                            )
                        )

        return flaky

    def stability_check(
        self,
        scenario_name: str,
        min_runs: int = 5,
    ) -> dict[str, object]:
        """Get stability metrics for a specific scenario.

        Args:
            scenario_name: Name of the scenario to check.
            min_runs: Minimum runs required for analysis.

        Returns:
            Dictionary with stability metrics.
        """
        trend_data: list[TrendEntry] = self._loader.load_trend_data(scenario_name)

        if len(trend_data) < min_runs:
            return {
                "scenario_name": scenario_name,
                "run_count": len(trend_data),
                "is_stable": None,
                "reason": "Insufficient data",
            }

        # Calculate metrics
        pass_count = sum(1 for d in trend_data if d["passed"])
        pass_rate = pass_count / len(trend_data)
        scores: list[float] = [d["score"] for d in trend_data]
        mean_score = statistics.mean(scores)
        score_std = statistics.stdev(scores) if len(scores) > 1 else 0.0

        # Determine stability
        is_stable = True
        reasons: list[str] = []

        if pass_rate < STABILITY_PASS_RATE_HIGH and pass_rate > STABILITY_PASS_RATE_LOW:
            is_stable = False
            reasons.append(f"Unstable pass rate: {pass_rate:.0%}")

        if mean_score > 0:
            cv = score_std / mean_score
            if cv > STABILITY_CV_THRESHOLD:
                is_stable = False
                reasons.append(f"High score variance: CV={cv:.2%}")

        return {
            "scenario_name": scenario_name,
            "run_count": len(trend_data),
            "pass_rate": pass_rate,
            "mean_score": mean_score,
            "score_std": score_std,
            "is_stable": is_stable,
            "reasons": reasons if reasons else ["Scenario is stable"],
        }
