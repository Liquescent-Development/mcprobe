"""JSON report generator for machine-readable export.

Exports test results as JSON for programmatic access and integration.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcprobe.persistence import TestRunResult


class JsonReportGenerator:
    """Generates JSON reports from test results."""

    def generate(
        self,
        results: list[TestRunResult],
        output_path: Path,
        include_conversations: bool = True,
    ) -> None:
        """Generate a JSON report.

        Args:
            results: List of test run results.
            output_path: Path to write the JSON report.
            include_conversations: Whether to include full conversation transcripts.
        """
        report = self._build_report(results, include_conversations)
        output_path.write_text(json.dumps(report, indent=2, default=str))

    def _build_report(
        self,
        results: list[TestRunResult],
        include_conversations: bool,
    ) -> dict[str, Any]:
        """Build the report dictionary."""
        total = len(results)
        passed = sum(1 for r in results if r.judgment_result.passed)
        failed = total - passed

        return {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "mcprobe_version": results[0].mcprobe_version if results else "unknown",
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": passed / total if total > 0 else 0,
                "total_duration_seconds": sum(r.duration_seconds for r in results),
            },
            "results": [
                self._build_result_entry(r, include_conversations) for r in results
            ],
        }

    def _build_result_entry(
        self,
        result: TestRunResult,
        include_conversations: bool,
    ) -> dict[str, Any]:
        """Build a single result entry."""
        entry: dict[str, Any] = {
            "run_id": result.run_id,
            "timestamp": result.timestamp.isoformat(),
            "scenario_name": result.scenario_name,
            "scenario_file": result.scenario_file,
            "scenario_tags": result.scenario_tags,
            "passed": result.judgment_result.passed,
            "score": result.judgment_result.score,
            "reasoning": result.judgment_result.reasoning,
            "duration_seconds": result.duration_seconds,
            "agent_type": result.agent_type,
            "judge_model": result.judge_model,
            "synthetic_user_model": result.synthetic_user_model,
            "agent_model": result.agent_model,
            "correctness_results": result.judgment_result.correctness_results,
            "failure_results": result.judgment_result.failure_results,
            "tool_usage_results": result.judgment_result.tool_usage_results,
            "efficiency_results": result.judgment_result.efficiency_results,
            "suggestions": result.judgment_result.suggestions,
            "quality_metrics": {
                "clarification_count": (
                    result.judgment_result.quality_metrics.clarification_count
                ),
                "backtrack_count": result.judgment_result.quality_metrics.backtrack_count,
                "turns_to_first_answer": (
                    result.judgment_result.quality_metrics.turns_to_first_answer
                ),
                "final_answer_completeness": (
                    result.judgment_result.quality_metrics.final_answer_completeness
                ),
            },
        }

        if include_conversations:
            entry["conversation"] = {
                "turns": [
                    {
                        "role": turn.role,
                        "content": turn.content,
                        "tool_calls": [
                            {
                                "tool_name": tc.tool_name,
                                "parameters": tc.parameters,
                                "result": tc.result,
                                "latency_ms": tc.latency_ms,
                                "error": tc.error,
                            }
                            for tc in turn.tool_calls
                        ],
                        "timestamp": turn.timestamp,
                    }
                    for turn in result.conversation_result.turns
                ],
                "final_answer": result.conversation_result.final_answer,
                "total_tokens": result.conversation_result.total_tokens,
                "termination_reason": result.conversation_result.termination_reason.value,
            }

        if result.git_commit:
            entry["git_commit"] = result.git_commit
        if result.git_branch:
            entry["git_branch"] = result.git_branch
        if result.ci_environment:
            entry["ci_environment"] = result.ci_environment

        return entry
