"""Tests for CLI since parsing."""

from datetime import UTC, datetime, timedelta

import pytest
import typer

from mcprobe.cli.main import _parse_since


class TestParseSince:
    """Tests for the _parse_since function."""

    def test_parse_relative_hours(self) -> None:
        """Test parsing relative hours like '1h'."""
        now = datetime.now(UTC)
        result = _parse_since("1h")
        # Should be roughly 1 hour ago (within a few seconds)
        expected = now - timedelta(hours=1)
        assert abs((result - expected).total_seconds()) < 5

    def test_parse_relative_minutes(self) -> None:
        """Test parsing relative minutes like '30m'."""
        now = datetime.now(UTC)
        result = _parse_since("30m")
        expected = now - timedelta(minutes=30)
        assert abs((result - expected).total_seconds()) < 5

    def test_parse_relative_days(self) -> None:
        """Test parsing relative days like '1d'."""
        now = datetime.now(UTC)
        result = _parse_since("1d")
        expected = now - timedelta(days=1)
        assert abs((result - expected).total_seconds()) < 5

    def test_parse_iso_datetime(self) -> None:
        """Test parsing ISO datetime format."""
        result = _parse_since("2026-01-18T13:00:00")
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 18
        assert result.hour == 13
        assert result.minute == 0

    def test_parse_date_only(self) -> None:
        """Test parsing date-only format."""
        result = _parse_since("2026-01-18")
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 18
        assert result.hour == 0
        assert result.minute == 0

    def test_parse_invalid_format_raises(self) -> None:
        """Test that invalid format raises BadParameter."""
        with pytest.raises(typer.BadParameter) as exc_info:
            _parse_since("invalid")
        assert "Invalid time format" in str(exc_info.value)

    def test_parse_case_insensitive(self) -> None:
        """Test that relative time is case insensitive."""
        result_lower = _parse_since("1h")
        result_upper = _parse_since("1H")
        # Both should be roughly the same time
        assert abs((result_lower - result_upper).total_seconds()) < 5
