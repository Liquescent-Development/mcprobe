"""Tests for reporting module."""

import json
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import pytest

from mcprobe.models.conversation import ConversationResult, TerminationReason, ToolCall
from mcprobe.models.judgment import JudgmentResult, QualityMetrics
from mcprobe.persistence import TestRunResult
from mcprobe.reporting import HtmlReportGenerator, JsonReportGenerator, JunitReportGenerator


@pytest.fixture
def sample_test_results() -> list[TestRunResult]:
    """Create sample test results for testing."""
    results = []

    for i in range(3):
        passed = i != 1  # Second test fails

        conversation = ConversationResult(
            turns=[],
            final_answer=f"Test answer {i}",
            total_tool_calls=[
                ToolCall(
                    tool_name="test_tool",
                    parameters={"param": f"value{i}"},
                    result={"data": "result"},
                    latency_ms=100.0,
                )
            ],
            total_tokens=500,
            duration_seconds=2.0 + i,
            termination_reason=TerminationReason.USER_SATISFIED,
        )

        judgment = JudgmentResult(
            passed=passed,
            score=0.9 if passed else 0.4,
            correctness_results={"criterion1": passed, "criterion2": True},
            failure_results={"bad_condition": not passed},
            tool_usage_results={"required_tools_used": True},
            efficiency_results={"within_limits": True},
            reasoning=f"Test {'passed' if passed else 'failed'} for scenario {i}",
            suggestions=["Improve description"] if not passed else [],
            quality_metrics=QualityMetrics(
                clarification_count=1,
                backtrack_count=0,
                turns_to_first_answer=2,
                final_answer_completeness=0.85,
            ),
        )

        result = TestRunResult(
            run_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            scenario_name=f"Test Scenario {i}",
            scenario_file=f"scenarios/test{i}.yaml",
            scenario_tags=["smoke", "test"],
            conversation_result=conversation,
            judgment_result=judgment,
            agent_type="simple",
            model_name="llama3.2",
            duration_seconds=2.0 + i,
            mcprobe_version="0.1.0",
            python_version="3.12.0",
        )
        results.append(result)

    return results


class TestHtmlReportGenerator:
    """Tests for HtmlReportGenerator."""

    def test_generate_creates_file(
        self,
        sample_test_results: list[TestRunResult],
        tmp_path: Path,
    ) -> None:
        """Test that generate creates an HTML file."""
        generator = HtmlReportGenerator()
        output_path = tmp_path / "report.html"

        generator.generate(sample_test_results, output_path)

        assert output_path.exists()
        content = output_path.read_text()
        assert "<!DOCTYPE html>" in content

    def test_generate_includes_title(
        self,
        sample_test_results: list[TestRunResult],
        tmp_path: Path,
    ) -> None:
        """Test that generate includes the title."""
        generator = HtmlReportGenerator()
        output_path = tmp_path / "report.html"

        generator.generate(sample_test_results, output_path, title="My Test Report")

        content = output_path.read_text()
        assert "My Test Report" in content

    def test_generate_includes_summary(
        self,
        sample_test_results: list[TestRunResult],
        tmp_path: Path,
    ) -> None:
        """Test that generate includes summary statistics."""
        generator = HtmlReportGenerator()
        output_path = tmp_path / "report.html"

        generator.generate(sample_test_results, output_path)

        content = output_path.read_text()
        assert "Total Tests" in content
        assert "Passed" in content
        assert "Failed" in content
        assert "Pass Rate" in content

    def test_generate_includes_scenarios(
        self,
        sample_test_results: list[TestRunResult],
        tmp_path: Path,
    ) -> None:
        """Test that generate includes scenario details."""
        generator = HtmlReportGenerator()
        output_path = tmp_path / "report.html"

        generator.generate(sample_test_results, output_path)

        content = output_path.read_text()
        assert "Test Scenario 0" in content
        assert "Test Scenario 1" in content
        assert "Test Scenario 2" in content

    def test_generate_escapes_html(
        self,
        tmp_path: Path,
    ) -> None:
        """Test that HTML special characters are escaped."""
        conversation = ConversationResult(
            turns=[],
            final_answer="Test <script>alert('xss')</script>",
            total_tool_calls=[],
            total_tokens=0,
            duration_seconds=1.0,
            termination_reason=TerminationReason.USER_SATISFIED,
        )

        judgment = JudgmentResult(
            passed=True,
            score=0.9,
            correctness_results={},
            failure_results={},
            tool_usage_results={},
            efficiency_results={},
            reasoning="Test with <dangerous> content",
        )

        result = TestRunResult(
            run_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            scenario_name="XSS Test <script>",
            scenario_file="test.yaml",
            conversation_result=conversation,
            judgment_result=judgment,
            agent_type="simple",
            model_name="test",
            duration_seconds=1.0,
            mcprobe_version="0.1.0",
            python_version="3.12.0",
        )

        generator = HtmlReportGenerator()
        output_path = tmp_path / "report.html"
        generator.generate([result], output_path)

        content = output_path.read_text()
        # The malicious input should be escaped in the scenario name
        assert "XSS Test &lt;script&gt;" in content
        # And in the reasoning
        assert "&lt;dangerous&gt;" in content


class TestJunitReportGenerator:
    """Tests for JunitReportGenerator."""

    def test_generate_creates_valid_xml(
        self,
        sample_test_results: list[TestRunResult],
        tmp_path: Path,
    ) -> None:
        """Test that generate creates valid XML."""
        generator = JunitReportGenerator()
        output_path = tmp_path / "junit.xml"

        generator.generate(sample_test_results, output_path)

        assert output_path.exists()
        # Should parse without error
        tree = ET.parse(output_path)
        root = tree.getroot()
        assert root.tag == "testsuites"

    def test_generate_includes_testsuite(
        self,
        sample_test_results: list[TestRunResult],
        tmp_path: Path,
    ) -> None:
        """Test that generate includes testsuite element."""
        generator = JunitReportGenerator()
        output_path = tmp_path / "junit.xml"

        generator.generate(sample_test_results, output_path, suite_name="my-tests")

        tree = ET.parse(output_path)
        testsuite = tree.find(".//testsuite")
        assert testsuite is not None
        assert testsuite.get("name") == "my-tests"
        assert testsuite.get("tests") == "3"
        assert testsuite.get("failures") == "1"

    def test_generate_includes_testcases(
        self,
        sample_test_results: list[TestRunResult],
        tmp_path: Path,
    ) -> None:
        """Test that generate includes testcase elements."""
        generator = JunitReportGenerator()
        output_path = tmp_path / "junit.xml"

        generator.generate(sample_test_results, output_path)

        tree = ET.parse(output_path)
        testcases = tree.findall(".//testcase")
        assert len(testcases) == 3

    def test_generate_marks_failures(
        self,
        sample_test_results: list[TestRunResult],
        tmp_path: Path,
    ) -> None:
        """Test that failures are marked with failure element."""
        generator = JunitReportGenerator()
        output_path = tmp_path / "junit.xml"

        generator.generate(sample_test_results, output_path)

        tree = ET.parse(output_path)
        failures = tree.findall(".//failure")
        assert len(failures) == 1


class TestJsonReportGenerator:
    """Tests for JsonReportGenerator."""

    def test_generate_creates_valid_json(
        self,
        sample_test_results: list[TestRunResult],
        tmp_path: Path,
    ) -> None:
        """Test that generate creates valid JSON."""
        generator = JsonReportGenerator()
        output_path = tmp_path / "report.json"

        generator.generate(sample_test_results, output_path)

        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert "metadata" in data
        assert "results" in data

    def test_generate_includes_metadata(
        self,
        sample_test_results: list[TestRunResult],
        tmp_path: Path,
    ) -> None:
        """Test that generate includes metadata."""
        generator = JsonReportGenerator()
        output_path = tmp_path / "report.json"

        generator.generate(sample_test_results, output_path)

        data = json.loads(output_path.read_text())
        metadata = data["metadata"]
        assert metadata["total_tests"] == 3
        assert metadata["passed"] == 2
        assert metadata["failed"] == 1

    def test_generate_includes_results(
        self,
        sample_test_results: list[TestRunResult],
        tmp_path: Path,
    ) -> None:
        """Test that generate includes result details."""
        generator = JsonReportGenerator()
        output_path = tmp_path / "report.json"

        generator.generate(sample_test_results, output_path)

        data = json.loads(output_path.read_text())
        results = data["results"]
        assert len(results) == 3
        assert all("scenario_name" in r for r in results)
        assert all("passed" in r for r in results)
        assert all("score" in r for r in results)

    def test_generate_excludes_conversations_when_disabled(
        self,
        sample_test_results: list[TestRunResult],
        tmp_path: Path,
    ) -> None:
        """Test that conversations can be excluded."""
        generator = JsonReportGenerator()
        output_path = tmp_path / "report.json"

        generator.generate(sample_test_results, output_path, include_conversations=False)

        data = json.loads(output_path.read_text())
        results = data["results"]
        assert all("conversation" not in r for r in results)

    def test_generate_includes_conversations_by_default(
        self,
        sample_test_results: list[TestRunResult],
        tmp_path: Path,
    ) -> None:
        """Test that conversations are included by default."""
        generator = JsonReportGenerator()
        output_path = tmp_path / "report.json"

        generator.generate(sample_test_results, output_path)

        data = json.loads(output_path.read_text())
        results = data["results"]
        assert all("conversation" in r for r in results)
