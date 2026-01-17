"""Result storage implementation.

Handles saving test run results to JSON files.
"""

import json
from datetime import datetime
from pathlib import Path

from mcprobe.persistence.models import IndexEntry, ResultIndex, TestRunResult, TrendEntry


class ResultStorage:
    """Handles saving test run results to the filesystem."""

    def __init__(self, results_dir: Path) -> None:
        """Initialize the result storage.

        Args:
            results_dir: Directory to store results in.
        """
        self._results_dir = results_dir
        self._runs_dir = results_dir / "runs"
        self._trends_dir = results_dir / "trends"
        self._index_path = results_dir / "index.json"

    def _ensure_dirs(self) -> None:
        """Ensure storage directories exist."""
        self._runs_dir.mkdir(parents=True, exist_ok=True)
        self._trends_dir.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, result: TestRunResult) -> str:
        """Generate a filename for a test run result.

        Format: YYYY-MM-DDTHH-MM-SS_runid.json
        """
        timestamp_str = result.timestamp.strftime("%Y-%m-%dT%H-%M-%S")
        short_id = result.run_id[:8]
        return f"{timestamp_str}_{short_id}.json"

    def save(self, result: TestRunResult) -> Path:
        """Save a test run result to disk.

        Args:
            result: The test run result to save.

        Returns:
            Path to the saved file.
        """
        self._ensure_dirs()

        # Save the run result
        filename = self._generate_filename(result)
        run_path = self._runs_dir / filename
        run_path.write_text(result.model_dump_json(indent=2))

        # Update index
        self._update_index(result)

        # Update per-scenario trends
        self._update_trends(result)

        return run_path

    def _update_index(self, result: TestRunResult) -> None:
        """Update the index with a new result."""
        index = self._load_index()

        entry = IndexEntry(
            run_id=result.run_id,
            timestamp=result.timestamp,
            scenario_name=result.scenario_name,
            scenario_file=result.scenario_file,
            passed=result.judgment_result.passed,
            score=result.judgment_result.score,
        )

        index.entries.append(entry)
        index.last_updated = datetime.now()

        self._index_path.write_text(index.model_dump_json(indent=2))

    def _load_index(self) -> ResultIndex:
        """Load the results index, creating if it doesn't exist."""
        if self._index_path.exists():
            data = json.loads(self._index_path.read_text())
            return ResultIndex.model_validate(data)
        return ResultIndex()

    def _update_trends(self, result: TestRunResult) -> None:
        """Update per-scenario trend file."""
        # Sanitize scenario name for filename
        safe_name = "".join(
            c if c.isalnum() or c in "-_" else "_"
            for c in result.scenario_name.lower()
        )
        trend_path = self._trends_dir / f"{safe_name}.json"

        # Load existing trend data
        trend_entries: list[TrendEntry] = []
        if trend_path.exists():
            trend_entries = json.loads(trend_path.read_text())

        # Add new entry
        new_entry: TrendEntry = {
            "run_id": result.run_id,
            "timestamp": result.timestamp.isoformat(),
            "passed": result.judgment_result.passed,
            "score": result.judgment_result.score,
            "duration_seconds": result.duration_seconds,
            "total_tool_calls": len(result.conversation_result.total_tool_calls),
            "total_tokens": result.conversation_result.total_tokens,
            "turns": len(result.conversation_result.turns),
        }
        trend_entries.append(new_entry)

        trend_path.write_text(json.dumps(trend_entries, indent=2))

    def cleanup_old_runs(
        self,
        max_age_days: int = 30,
        max_runs_per_scenario: int = 100,
    ) -> int:
        """Remove old run results.

        Args:
            max_age_days: Remove runs older than this many days.
            max_runs_per_scenario: Keep at most this many runs per scenario in trends.

        Returns:
            Number of files removed.
        """
        removed = 0
        cutoff = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)

        # Clean up old run files
        if self._runs_dir.exists():
            for run_file in self._runs_dir.glob("*.json"):
                try:
                    data = json.loads(run_file.read_text())
                    timestamp = datetime.fromisoformat(data["timestamp"]).timestamp()
                    if timestamp < cutoff:
                        run_file.unlink()
                        removed += 1
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

        # Trim trend files
        if self._trends_dir.exists():
            for trend_file in self._trends_dir.glob("*.json"):
                try:
                    entries = json.loads(trend_file.read_text())
                    if len(entries) > max_runs_per_scenario:
                        # Keep the most recent entries
                        entries = entries[-max_runs_per_scenario:]
                        trend_file.write_text(json.dumps(entries, indent=2))
                except (json.JSONDecodeError, ValueError):
                    continue

        # Rebuild index after cleanup
        self._rebuild_index()

        return removed

    def _rebuild_index(self) -> None:
        """Rebuild the index from remaining run files."""
        entries: list[IndexEntry] = []

        if self._runs_dir.exists():
            for run_file in self._runs_dir.glob("*.json"):
                try:
                    result = TestRunResult.model_validate_json(run_file.read_text())
                    entries.append(IndexEntry(
                        run_id=result.run_id,
                        timestamp=result.timestamp,
                        scenario_name=result.scenario_name,
                        scenario_file=result.scenario_file,
                        passed=result.judgment_result.passed,
                        score=result.judgment_result.score,
                    ))
                except Exception:
                    continue

        # Sort by timestamp
        entries.sort(key=lambda e: e.timestamp)

        index = ResultIndex(entries=entries, last_updated=datetime.now())
        self._index_path.write_text(index.model_dump_json(indent=2))
