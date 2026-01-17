"""Tests for flaky test detection module."""

from unittest.mock import MagicMock

import pytest

from mcprobe.analysis import FlakyDetector
from mcprobe.persistence import TrendEntry


@pytest.fixture
def mock_loader() -> MagicMock:
    """Create a mock result loader."""
    return MagicMock()


@pytest.fixture
def flaky_pass_fail_data() -> list[TrendEntry]:
    """Create data with inconsistent pass/fail pattern (50% pass rate)."""
    return [
        {
            "run_id": f"run-{i}",
            "timestamp": f"2026-01-{10+i}T12:00:00",
            "passed": i % 2 == 0,  # Alternating pass/fail
            "score": 0.8 if i % 2 == 0 else 0.4,
            "duration_seconds": 5.0,
            "total_tool_calls": 3,
            "total_tokens": 500,
            "turns": 2,
        }
        for i in range(10)
    ]


@pytest.fixture
def high_variance_data() -> list[TrendEntry]:
    """Create data with high score variance among passing tests."""
    return [
        {
            "run_id": f"run-{i}",
            "timestamp": f"2026-01-{10+i}T12:00:00",
            "passed": True,
            "score": 0.5 + (0.4 if i % 2 == 0 else 0.0),  # Alternates between 0.5 and 0.9
            "duration_seconds": 5.0,
            "total_tool_calls": 3,
            "total_tokens": 500,
            "turns": 2,
        }
        for i in range(10)
    ]


@pytest.fixture
def stable_data() -> list[TrendEntry]:
    """Create data with stable, consistent results."""
    return [
        {
            "run_id": f"run-{i}",
            "timestamp": f"2026-01-{10+i}T12:00:00",
            "passed": True,
            "score": 0.85,
            "duration_seconds": 5.0,
            "total_tool_calls": 3,
            "total_tokens": 500,
            "turns": 2,
        }
        for i in range(10)
    ]


class TestFlakyDetector:
    """Tests for FlakyDetector class."""

    def test_detect_flaky_pass_fail_inconsistency(
        self,
        mock_loader: MagicMock,
        flaky_pass_fail_data: list[TrendEntry],
    ) -> None:
        """Test that pass/fail inconsistency is detected as flaky."""
        mock_loader.list_scenarios.return_value = ["flaky-scenario"]
        mock_loader.load_trend_data.return_value = flaky_pass_fail_data

        detector = FlakyDetector(mock_loader)
        flaky = detector.detect_flaky_scenarios(min_runs=5)

        assert len(flaky) == 1
        assert flaky[0].scenario_name == "flaky-scenario"
        assert flaky[0].reason == "Inconsistent pass/fail results"
        assert flaky[0].severity == "high"

    def test_detect_flaky_high_score_variance(
        self,
        mock_loader: MagicMock,
        high_variance_data: list[TrendEntry],
    ) -> None:
        """Test that high score variance is detected as flaky."""
        mock_loader.list_scenarios.return_value = ["variance-scenario"]
        mock_loader.load_trend_data.return_value = high_variance_data

        detector = FlakyDetector(mock_loader)
        flaky = detector.detect_flaky_scenarios(min_runs=5, cv_threshold=0.15)

        assert len(flaky) == 1
        assert flaky[0].scenario_name == "variance-scenario"
        assert "High score variance" in flaky[0].reason
        assert flaky[0].severity == "medium"
        assert flaky[0].coefficient_of_variation is not None

    def test_stable_scenario_not_flagged(
        self,
        mock_loader: MagicMock,
        stable_data: list[TrendEntry],
    ) -> None:
        """Test that stable scenarios are not flagged as flaky."""
        mock_loader.list_scenarios.return_value = ["stable-scenario"]
        mock_loader.load_trend_data.return_value = stable_data

        detector = FlakyDetector(mock_loader)
        flaky = detector.detect_flaky_scenarios(min_runs=5)

        assert len(flaky) == 0

    def test_insufficient_data_not_flagged(
        self,
        mock_loader: MagicMock,
    ) -> None:
        """Test that scenarios with insufficient data are not flagged."""
        # Only 3 runs, need at least 5
        trend_data: list[TrendEntry] = [
            {
                "run_id": f"run-{i}",
                "timestamp": f"2026-01-{10+i}T12:00:00",
                "passed": i % 2 == 0,
                "score": 0.7,
                "duration_seconds": 5.0,
                "total_tool_calls": 3,
                "total_tokens": 500,
                "turns": 2,
            }
            for i in range(3)
        ]
        mock_loader.list_scenarios.return_value = ["scenario"]
        mock_loader.load_trend_data.return_value = trend_data

        detector = FlakyDetector(mock_loader)
        flaky = detector.detect_flaky_scenarios(min_runs=5)

        assert len(flaky) == 0

    def test_always_passing_not_flagged(
        self,
        mock_loader: MagicMock,
    ) -> None:
        """Test that always-passing scenarios are not flagged for pass/fail."""
        trend_data: list[TrendEntry] = [
            {
                "run_id": f"run-{i}",
                "timestamp": f"2026-01-{10+i}T12:00:00",
                "passed": True,  # Always passes
                "score": 0.85,
                "duration_seconds": 5.0,
                "total_tool_calls": 3,
                "total_tokens": 500,
                "turns": 2,
            }
            for i in range(10)
        ]
        mock_loader.list_scenarios.return_value = ["always-pass"]
        mock_loader.load_trend_data.return_value = trend_data

        detector = FlakyDetector(mock_loader)
        flaky = detector.detect_flaky_scenarios(min_runs=5)

        assert len(flaky) == 0

    def test_always_failing_not_flagged(
        self,
        mock_loader: MagicMock,
    ) -> None:
        """Test that always-failing scenarios are not flagged for pass/fail."""
        trend_data: list[TrendEntry] = [
            {
                "run_id": f"run-{i}",
                "timestamp": f"2026-01-{10+i}T12:00:00",
                "passed": False,  # Always fails
                "score": 0.2,
                "duration_seconds": 5.0,
                "total_tool_calls": 3,
                "total_tokens": 500,
                "turns": 2,
            }
            for i in range(10)
        ]
        mock_loader.list_scenarios.return_value = ["always-fail"]
        mock_loader.load_trend_data.return_value = trend_data

        detector = FlakyDetector(mock_loader)
        flaky = detector.detect_flaky_scenarios(min_runs=5)

        # Should not be flagged as flaky (consistently failing is not flaky)
        assert len(flaky) == 0

    def test_custom_thresholds(
        self,
        mock_loader: MagicMock,
    ) -> None:
        """Test that custom thresholds are respected."""
        # 30% pass rate - within (0.2, 0.8) but not within (0.4, 0.6)
        trend_data: list[TrendEntry] = [
            {
                "run_id": f"run-{i}",
                "timestamp": f"2026-01-{10+i}T12:00:00",
                "passed": i < 3,  # First 3 pass, rest fail
                "score": 0.7,
                "duration_seconds": 5.0,
                "total_tool_calls": 3,
                "total_tokens": 500,
                "turns": 2,
            }
            for i in range(10)
        ]
        mock_loader.list_scenarios.return_value = ["scenario"]
        mock_loader.load_trend_data.return_value = trend_data

        detector = FlakyDetector(mock_loader)

        # With default threshold (0.2, 0.8), should be flagged
        flaky = detector.detect_flaky_scenarios(
            min_runs=5,
            pass_fail_threshold=(0.2, 0.8),
        )
        assert len(flaky) == 1

        # With narrow threshold (0.4, 0.6), should not be flagged
        flaky = detector.detect_flaky_scenarios(
            min_runs=5,
            pass_fail_threshold=(0.4, 0.6),
        )
        assert len(flaky) == 0


class TestStabilityCheck:
    """Tests for stability_check method."""

    def test_stability_check_with_insufficient_data(
        self,
        mock_loader: MagicMock,
    ) -> None:
        """Test stability check returns appropriate result for insufficient data."""
        trend_data: list[TrendEntry] = [
            {
                "run_id": "run-1",
                "timestamp": "2026-01-10T12:00:00",
                "passed": True,
                "score": 0.8,
                "duration_seconds": 5.0,
                "total_tool_calls": 3,
                "total_tokens": 500,
                "turns": 2,
            }
        ]
        mock_loader.load_trend_data.return_value = trend_data

        detector = FlakyDetector(mock_loader)
        result = detector.stability_check("test-scenario", min_runs=5)

        assert result["scenario_name"] == "test-scenario"
        assert result["is_stable"] is None
        assert result["reason"] == "Insufficient data"

    def test_stability_check_stable_scenario(
        self,
        mock_loader: MagicMock,
        stable_data: list[TrendEntry],
    ) -> None:
        """Test stability check identifies stable scenario."""
        mock_loader.load_trend_data.return_value = stable_data

        detector = FlakyDetector(mock_loader)
        result = detector.stability_check("stable-scenario", min_runs=5)

        assert result["scenario_name"] == "stable-scenario"
        assert result["is_stable"] is True
        assert result["pass_rate"] == 1.0
        assert "Scenario is stable" in result["reasons"]

    def test_stability_check_unstable_pass_rate(
        self,
        mock_loader: MagicMock,
        flaky_pass_fail_data: list[TrendEntry],
    ) -> None:
        """Test stability check identifies unstable pass rate."""
        mock_loader.load_trend_data.return_value = flaky_pass_fail_data

        detector = FlakyDetector(mock_loader)
        result = detector.stability_check("flaky-scenario", min_runs=5)

        assert result["is_stable"] is False
        assert any("Unstable pass rate" in r for r in result["reasons"])

    def test_stability_check_high_variance(
        self,
        mock_loader: MagicMock,
        high_variance_data: list[TrendEntry],
    ) -> None:
        """Test stability check identifies high score variance."""
        mock_loader.load_trend_data.return_value = high_variance_data

        detector = FlakyDetector(mock_loader)
        result = detector.stability_check("variance-scenario", min_runs=5)

        assert result["is_stable"] is False
        assert any("High score variance" in r for r in result["reasons"])

    def test_stability_check_returns_metrics(
        self,
        mock_loader: MagicMock,
        stable_data: list[TrendEntry],
    ) -> None:
        """Test stability check returns expected metrics."""
        mock_loader.load_trend_data.return_value = stable_data

        detector = FlakyDetector(mock_loader)
        result = detector.stability_check("scenario", min_runs=5)

        assert "run_count" in result
        assert "pass_rate" in result
        assert "mean_score" in result
        assert "score_std" in result
        assert "is_stable" in result
        assert "reasons" in result
