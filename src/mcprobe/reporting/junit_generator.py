"""JUnit XML report generator for CI integration.

Generates JUnit XML format compatible with CI tools like GitHub Actions.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcprobe.persistence import TestRunResult


class JunitReportGenerator:
    """Generates JUnit XML reports from test results."""

    def generate(
        self,
        results: list[TestRunResult],
        output_path: Path,
        suite_name: str = "mcprobe",
    ) -> None:
        """Generate a JUnit XML report.

        Args:
            results: List of test run results.
            output_path: Path to write the XML report.
            suite_name: Name for the test suite.
        """
        # Create root element
        testsuites = ET.Element("testsuites")

        # Create testsuite element
        testsuite = ET.SubElement(testsuites, "testsuite")
        testsuite.set("name", suite_name)
        testsuite.set("tests", str(len(results)))
        testsuite.set("failures", str(sum(1 for r in results if not r.judgment_result.passed)))
        testsuite.set("errors", "0")
        testsuite.set("time", str(sum(r.duration_seconds for r in results)))
        testsuite.set("timestamp", datetime.now().isoformat())

        # Add test cases
        for result in results:
            testcase = ET.SubElement(testsuite, "testcase")
            testcase.set("name", result.scenario_name)
            testcase.set("classname", f"mcprobe.{_sanitize_classname(result.scenario_file)}")
            testcase.set("time", str(result.duration_seconds))

            if not result.judgment_result.passed:
                failure = ET.SubElement(testcase, "failure")
                failure.set("message", result.judgment_result.reasoning)
                failure.set("type", "AssertionError")

                # Build failure content
                failure_text = self._build_failure_text(result)
                failure.text = failure_text

            # Add system-out with conversation
            system_out = ET.SubElement(testcase, "system-out")
            system_out.text = self._build_system_out(result)

        # Write to file
        tree = ET.ElementTree(testsuites)
        ET.indent(tree, space="  ")
        tree.write(output_path, encoding="unicode", xml_declaration=True)

    def _build_failure_text(self, result: TestRunResult) -> str:
        """Build failure message text."""
        lines = [
            f"Score: {result.judgment_result.score:.2f}",
            f"Reasoning: {result.judgment_result.reasoning}",
            "",
            "Correctness Results:",
        ]

        for criterion, passed in result.judgment_result.correctness_results.items():
            status = "PASS" if passed else "FAIL"
            lines.append(f"  {criterion}: {status}")

        if result.judgment_result.suggestions:
            lines.append("")
            lines.append("Suggestions:")
            for suggestion in result.judgment_result.suggestions:
                lines.append(f"  - {suggestion}")

        return "\n".join(lines)

    def _build_system_out(self, result: TestRunResult) -> str:
        """Build system output with conversation transcript."""
        lines = [
            "=== Conversation ===",
        ]

        for turn in result.conversation_result.turns:
            lines.append(f"[{turn.role.upper()}]: {turn.content}")
            for tc in turn.tool_calls:
                lines.append(f"  -> {tc.tool_name}({tc.parameters})")

        lines.append("")
        lines.append("=== Tool Calls ===")
        for tc in result.conversation_result.total_tool_calls:
            lines.append(f"{tc.tool_name}: {tc.parameters} -> {tc.result}")

        return "\n".join(lines)


def _sanitize_classname(path: str) -> str:
    """Convert a file path to a valid Java classname."""
    # Remove extension and convert path separators to dots
    name = Path(path).stem
    return name.replace("-", "_").replace(" ", "_")
