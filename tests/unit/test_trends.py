"""Tests for trend analysis module."""

from unittest.mock import MagicMock

import pytest

from mcprobe.analysis import TrendAnalyzer, TrendDirection
from mcprobe.persistence import TrendEntry


@pytest.fixture
def mock_loader() -> MagicMock:
    """Create a mock result loader."""
    return MagicMock()


@pytest.fixture
def sample_trend_data() -> list[TrendEntry]:
    """Create sample trend data for testing."""
    return [
        {
            "run_id": f"run-{i}",
            "timestamp": f"2026-01-{10+i}T12:00:00",
            "passed": i % 5 != 0,  # 80% pass rate
            "score": 0.7 + (i * 0.02),  # Gradually improving scores
            "duration_seconds": 5.0 + (i * 0.1),
            "total_tool_calls": 3 + i,
            "total_tokens": 500 + (i * 10),
            "turns": 2,
        }
        for i in range(10)
    ]


@pytest.fixture
def declining_trend_data() -> list[TrendEntry]:
    """Create trend data showing decline."""
    return [
        {
            "run_id": f"run-{i}",
            "timestamp": f"2026-01-{10+i}T12:00:00",
            "passed": True,
            "score": 0.9 - (i * 0.05),  # Declining scores
            "duration_seconds": 5.0,
            "total_tool_calls": 3,
            "total_tokens": 500,
            "turns": 2,
        }
        for i in range(10)
    ]


class TestTrendAnalyzer:
    """Tests for TrendAnalyzer class."""

    def test_analyze_scenario_returns_none_for_insufficient_data(
        self,
        mock_loader: MagicMock,
    ) -> None:
        """Test that analyze_scenario returns None when not enough data."""
        mock_loader.load_trend_data.return_value = [
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

        analyzer = TrendAnalyzer(mock_loader)
        result = analyzer.analyze_scenario("test-scenario")

        assert result is None

    def test_analyze_scenario_returns_trends(
        self,
        mock_loader: MagicMock,
        sample_trend_data: list[TrendEntry],
    ) -> None:
        """Test that analyze_scenario returns valid trends."""
        mock_loader.load_trend_data.return_value = sample_trend_data

        analyzer = TrendAnalyzer(mock_loader)
        result = analyzer.analyze_scenario("test-scenario")

        assert result is not None
        assert result.scenario_name == "test-scenario"
        assert result.run_count == 10
        assert 0.7 <= result.pass_rate <= 0.9

    def test_analyze_scenario_calculates_scores(
        self,
        mock_loader: MagicMock,
        sample_trend_data: list[TrendEntry],
    ) -> None:
        """Test that score statistics are calculated correctly."""
        mock_loader.load_trend_data.return_value = sample_trend_data

        analyzer = TrendAnalyzer(mock_loader)
        result = analyzer.analyze_scenario("test-scenario")

        assert result is not None
        assert result.current_score == sample_trend_data[-1]["score"]
        assert result.min_score <= result.avg_score <= result.max_score

    def test_analyze_scenario_detects_improving_trend(
        self,
        mock_loader: MagicMock,
        sample_trend_data: list[TrendEntry],
    ) -> None:
        """Test that improving trends are detected."""
        mock_loader.load_trend_data.return_value = sample_trend_data

        analyzer = TrendAnalyzer(mock_loader, slope_threshold=0.01)
        result = analyzer.analyze_scenario("test-scenario")

        assert result is not None
        assert result.score_trend == TrendDirection.IMPROVING

    def test_analyze_scenario_detects_degrading_trend(
        self,
        mock_loader: MagicMock,
        declining_trend_data: list[TrendEntry],
    ) -> None:
        """Test that degrading trends are detected."""
        mock_loader.load_trend_data.return_value = declining_trend_data

        analyzer = TrendAnalyzer(mock_loader, slope_threshold=0.01)
        result = analyzer.analyze_scenario("test-scenario")

        assert result is not None
        assert result.score_trend == TrendDirection.DEGRADING

    def test_analyze_scenario_respects_window_size(
        self,
        mock_loader: MagicMock,
        sample_trend_data: list[TrendEntry],
    ) -> None:
        """Test that window_size limits data considered."""
        mock_loader.load_trend_data.return_value = sample_trend_data

        analyzer = TrendAnalyzer(mock_loader)
        result = analyzer.analyze_scenario("test-scenario", window_size=5)

        assert result is not None
        assert result.run_count == 5

    def test_analyze_all_returns_multiple_scenarios(
        self,
        mock_loader: MagicMock,
        sample_trend_data: list[TrendEntry],
    ) -> None:
        """Test that analyze_all processes multiple scenarios."""
        mock_loader.list_scenarios.return_value = ["scenario-1", "scenario-2"]
        mock_loader.load_trend_data.return_value = sample_trend_data

        analyzer = TrendAnalyzer(mock_loader)
        results = analyzer.analyze_all()

        assert len(results) == 2
        assert results[0].scenario_name == "scenario-1"
        assert results[1].scenario_name == "scenario-2"


class TestRegressionDetection:
    """Tests for regression detection."""

    def test_detect_regressions_finds_pass_rate_regression(
        self,
        mock_loader: MagicMock,
    ) -> None:
        """Test that pass rate regressions are detected."""
        # First half: 100% pass rate, second half: 50% pass rate
        trend_data: list[TrendEntry] = [
            {
                "run_id": f"run-{i}",
                "timestamp": f"2026-01-{10+i}T12:00:00",
                "passed": i < 4,  # First 4 pass, last 4 fail
                "score": 0.8,
                "duration_seconds": 5.0,
                "total_tool_calls": 3,
                "total_tokens": 500,
                "turns": 2,
            }
            for i in range(8)
        ]
        mock_loader.list_scenarios.return_value = ["test-scenario"]
        mock_loader.load_trend_data.return_value = trend_data

        analyzer = TrendAnalyzer(mock_loader)
        regressions = analyzer.detect_regressions(pass_rate_threshold=0.1)

        assert len(regressions) >= 1
        pass_rate_regressions = [r for r in regressions if r.metric == "pass_rate"]
        assert len(pass_rate_regressions) == 1
        assert pass_rate_regressions[0].scenario_name == "test-scenario"

    def test_detect_regressions_finds_score_regression(
        self,
        mock_loader: MagicMock,
    ) -> None:
        """Test that score regressions are detected."""
        # First half: high scores, second half: low scores
        trend_data: list[TrendEntry] = [
            {
                "run_id": f"run-{i}",
                "timestamp": f"2026-01-{10+i}T12:00:00",
                "passed": True,
                "score": 0.9 if i < 4 else 0.5,  # Drop from 0.9 to 0.5
                "duration_seconds": 5.0,
                "total_tool_calls": 3,
                "total_tokens": 500,
                "turns": 2,
            }
            for i in range(8)
        ]
        mock_loader.list_scenarios.return_value = ["test-scenario"]
        mock_loader.load_trend_data.return_value = trend_data

        analyzer = TrendAnalyzer(mock_loader)
        regressions = analyzer.detect_regressions(score_threshold=0.1)

        score_regressions = [r for r in regressions if r.metric == "score"]
        assert len(score_regressions) == 1
        assert score_regressions[0].severity in ["low", "medium", "high"]

    def test_detect_regressions_returns_empty_for_insufficient_data(
        self,
        mock_loader: MagicMock,
    ) -> None:
        """Test that regressions are not flagged with insufficient data."""
        # Only 3 data points (needs at least 4)
        trend_data: list[TrendEntry] = [
            {
                "run_id": f"run-{i}",
                "timestamp": f"2026-01-{10+i}T12:00:00",
                "passed": True,
                "score": 0.8,
                "duration_seconds": 5.0,
                "total_tool_calls": 3,
                "total_tokens": 500,
                "turns": 2,
            }
            for i in range(3)
        ]
        mock_loader.list_scenarios.return_value = ["test-scenario"]
        mock_loader.load_trend_data.return_value = trend_data

        analyzer = TrendAnalyzer(mock_loader)
        regressions = analyzer.detect_regressions()

        assert len(regressions) == 0

    def test_detect_regressions_calculates_severity(
        self,
        mock_loader: MagicMock,
    ) -> None:
        """Test that severity is calculated based on magnitude."""
        # Large drop from 0.9 to 0.3
        trend_data: list[TrendEntry] = [
            {
                "run_id": f"run-{i}",
                "timestamp": f"2026-01-{10+i}T12:00:00",
                "passed": True,
                "score": 0.9 if i < 4 else 0.3,
                "duration_seconds": 5.0,
                "total_tool_calls": 3,
                "total_tokens": 500,
                "turns": 2,
            }
            for i in range(8)
        ]
        mock_loader.list_scenarios.return_value = ["test-scenario"]
        mock_loader.load_trend_data.return_value = trend_data

        analyzer = TrendAnalyzer(mock_loader)
        regressions = analyzer.detect_regressions(score_threshold=0.1)

        score_regressions = [r for r in regressions if r.metric == "score"]
        assert len(score_regressions) == 1
        assert score_regressions[0].severity == "high"


class TestTrendDetection:
    """Tests for internal trend detection."""

    def test_stable_trend_for_consistent_values(
        self,
        mock_loader: MagicMock,
    ) -> None:
        """Test that stable trend is detected for consistent values."""
        trend_data: list[TrendEntry] = [
            {
                "run_id": f"run-{i}",
                "timestamp": f"2026-01-{10+i}T12:00:00",
                "passed": True,
                "score": 0.8,  # All same value
                "duration_seconds": 5.0,
                "total_tool_calls": 3,
                "total_tokens": 500,
                "turns": 2,
            }
            for i in range(5)
        ]
        mock_loader.load_trend_data.return_value = trend_data

        analyzer = TrendAnalyzer(mock_loader)
        result = analyzer.analyze_scenario("test-scenario")

        assert result is not None
        assert result.score_trend == TrendDirection.STABLE
