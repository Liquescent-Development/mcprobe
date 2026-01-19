"""Result loader implementation.

Handles loading test run results from stored JSON files.
"""

import json
from datetime import datetime
from pathlib import Path

from mcprobe.persistence.models import IndexEntry, ResultIndex, TestRunResult, TrendEntry


class ResultLoader:
    """Handles loading test run results from the filesystem."""

    def __init__(self, results_dir: Path) -> None:
        """Initialize the result loader.

        Args:
            results_dir: Directory where results are stored.
        """
        self._results_dir = results_dir
        self._runs_dir = results_dir / "runs"
        self._trends_dir = results_dir / "trends"
        self._index_path = results_dir / "index.json"

    def load_index(self) -> ResultIndex:
        """Load the results index.

        Returns:
            The result index, or empty index if not found.
        """
        if self._index_path.exists():
            data = json.loads(self._index_path.read_text())
            return ResultIndex.model_validate(data)
        return ResultIndex()

    def load(self, run_id: str) -> TestRunResult | None:
        """Load a specific test run by ID.

        Args:
            run_id: The run ID to load.

        Returns:
            The test run result, or None if not found.
        """
        if not self._runs_dir.exists():
            return None

        # Search for the run file
        for run_file in self._runs_dir.glob("*.json"):
            if run_id[:8] in run_file.name:
                try:
                    return TestRunResult.model_validate_json(run_file.read_text())
                except Exception:
                    continue

        return None

    def load_latest(self, scenario_name: str | None = None) -> TestRunResult | None:
        """Load the most recent test run.

        Args:
            scenario_name: Optional filter by scenario name.

        Returns:
            The most recent test run result, or None if not found.
        """
        index = self.load_index()
        if not index.entries:
            return None

        # Filter by scenario if specified
        entries = index.entries
        if scenario_name:
            entries = [e for e in entries if e.scenario_name == scenario_name]

        if not entries:
            return None

        # Sort by timestamp descending and get the latest
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return self.load(entries[0].run_id)

    def load_all(
        self,
        scenario_name: str | None = None,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[TestRunResult]:
        """Load multiple test run results.

        Args:
            scenario_name: Optional filter by scenario name.
            since: Optional filter for results after this time.
            limit: Optional maximum number of results to return.

        Returns:
            List of test run results, sorted by timestamp descending.
        """
        index = self.load_index()
        entries = index.entries

        # Apply filters
        if scenario_name:
            entries = [e for e in entries if e.scenario_name == scenario_name]
        if since:
            # Normalize timezone - strip tzinfo from since if entry timestamps are naive
            since_cmp = since.replace(tzinfo=None) if since.tzinfo else since
            entries = [e for e in entries if e.timestamp >= since_cmp]

        # Sort by timestamp descending
        entries.sort(key=lambda e: e.timestamp, reverse=True)

        # Apply limit
        if limit:
            entries = entries[:limit]

        # Load full results
        results: list[TestRunResult] = []
        for entry in entries:
            result = self.load(entry.run_id)
            if result:
                results.append(result)

        return results

    def list_scenarios(self) -> list[str]:
        """List all unique scenario names.

        Returns:
            List of scenario names that have results.
        """
        index = self.load_index()
        return sorted({e.scenario_name for e in index.entries})

    def load_scenario_history(
        self,
        scenario_name: str,
        limit: int = 20,
    ) -> list[TestRunResult]:
        """Load historical results for a specific scenario.

        Args:
            scenario_name: The scenario to load history for.
            limit: Maximum number of results to return.

        Returns:
            List of results, most recent first.
        """
        return self.load_all(scenario_name=scenario_name, limit=limit)

    def load_trend_data(
        self,
        scenario_name: str,
    ) -> list[TrendEntry]:
        """Load lightweight trend data for a scenario.

        This is faster than loading full results as it uses the trend files.

        Args:
            scenario_name: The scenario to load trends for.

        Returns:
            List of trend entries with metrics.
        """
        # Sanitize scenario name for filename
        safe_name = "".join(
            c if c.isalnum() or c in "-_" else "_"
            for c in scenario_name.lower()
        )
        trend_path = self._trends_dir / f"{safe_name}.json"

        if trend_path.exists():
            return json.loads(trend_path.read_text())  # type: ignore[no-any-return]
        return []

    def get_entries_by_scenario(self) -> dict[str, list[IndexEntry]]:
        """Group index entries by scenario name.

        Returns:
            Dictionary mapping scenario names to their index entries.
        """
        index = self.load_index()
        result: dict[str, list[IndexEntry]] = {}

        for entry in index.entries:
            if entry.scenario_name not in result:
                result[entry.scenario_name] = []
            result[entry.scenario_name].append(entry)

        return result
