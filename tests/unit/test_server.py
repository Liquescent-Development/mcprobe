"""Tests for MCP server."""

import time
import uuid
from datetime import datetime
from pathlib import Path

import pytest

from mcprobe.models.conversation import (
    ConversationResult,
    ConversationTurn,
    TerminationReason,
    ToolCall,
)
from mcprobe.models.judgment import (
    JudgmentResult,
    MCPSuggestion,
    QualityMetrics,
    SuggestionCategory,
    SuggestionSeverity,
)
from mcprobe.persistence import ResultStorage, TestRunResult
from mcprobe.server.server import create_server


@pytest.fixture
def temp_results_dir(tmp_path: Path) -> Path:
    """Create a temporary results directory."""
    results = tmp_path / "test-results"
    results.mkdir()
    return results


@pytest.fixture
def temp_scenarios_dir(tmp_path: Path) -> Path:
    """Create a temporary scenarios directory with sample files."""
    scenarios = tmp_path / "scenarios"
    scenarios.mkdir()

    # Create sample scenario files
    (scenarios / "weather.yaml").write_text("name: Weather Test\n")
    (scenarios / "search.yml").write_text("name: Search Test\n")

    # Create subdirectory with scenario
    subdir = scenarios / "advanced"
    subdir.mkdir()
    (subdir / "complex.yaml").write_text("name: Complex Test\n")

    return scenarios


@pytest.fixture
def sample_conversation_result() -> ConversationResult:
    """Create a sample conversation result."""
    now = time.time()
    return ConversationResult(
        turns=[
            ConversationTurn(
                role="user",
                content="What's the weather in Seattle?",
                timestamp=now,
            ),
            ConversationTurn(
                role="assistant",
                content="The weather in Seattle is sunny and 72°F.",
                tool_calls=[
                    ToolCall(
                        tool_name="get_weather",
                        parameters={"location": "Seattle"},
                        result={"temp": 72, "conditions": "sunny"},
                        latency_ms=150.0,
                    )
                ],
                timestamp=now + 1.0,
            ),
        ],
        final_answer="The weather is sunny.",
        total_tool_calls=[
            ToolCall(
                tool_name="get_weather",
                parameters={"location": "Seattle"},
                result={"temp": 72, "conditions": "sunny"},
                latency_ms=150.0,
            )
        ],
        total_tokens=500,
        duration_seconds=2.5,
        termination_reason=TerminationReason.CRITERIA_MET,
    )


@pytest.fixture
def sample_judgment_result() -> JudgmentResult:
    """Create a sample judgment result."""
    return JudgmentResult(
        passed=True,
        score=0.85,
        correctness_results={"mentions_temperature": True, "correct_location": True},
        failure_results={"wrong_location": False},
        tool_usage_results={"required_tools_used": True},
        efficiency_results={"total_tokens": 500, "total_tool_calls": 1},
        reasoning="The agent correctly answered the weather question.",
        suggestions=["Consider caching weather data."],
        structured_suggestions=[
            MCPSuggestion(
                category=SuggestionCategory.DESCRIPTION,
                severity=SuggestionSeverity.LOW,
                tool_name="get_weather",
                issue="Description could be clearer",
                suggestion="Add more detail about supported locations",
            )
        ],
        quality_metrics=QualityMetrics(
            clarification_count=0,
            backtrack_count=0,
            turns_to_first_answer=1,
            final_answer_completeness=0.9,
        ),
    )


@pytest.fixture
def sample_test_run(
    sample_conversation_result: ConversationResult,
    sample_judgment_result: JudgmentResult,
) -> TestRunResult:
    """Create a sample test run result."""
    return TestRunResult(
        run_id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        scenario_name="Weather Query Test",
        scenario_file="scenarios/weather.yaml",
        scenario_tags=["smoke", "weather"],
        conversation_result=sample_conversation_result,
        judgment_result=sample_judgment_result,
        agent_type="simple",
        judge_model="llama3.2",
        synthetic_user_model="llama3.2",
        agent_model="llama3.2",
        duration_seconds=2.5,
        mcprobe_version="0.1.0",
        python_version="3.12.0",
    )


class TestListScenarios:
    """Tests for list_scenarios tool."""

    @pytest.mark.asyncio
    async def test_list_scenarios_returns_yaml_files(
        self,
        temp_results_dir: Path,
        temp_scenarios_dir: Path,
    ) -> None:
        """Test that list_scenarios returns all YAML files."""
        server = create_server(temp_results_dir, temp_scenarios_dir)

        # Get the tool
        tools = server._tool_manager._tools
        list_scenarios_tool = tools["list_scenarios"]

        result = await list_scenarios_tool.fn()

        assert "weather" in result.lower()
        assert "search" in result.lower()
        assert "complex" in result.lower()

    @pytest.mark.asyncio
    async def test_list_scenarios_empty_dir(
        self,
        temp_results_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Test that list_scenarios handles empty directory."""
        empty_scenarios = tmp_path / "empty"
        empty_scenarios.mkdir()

        server = create_server(temp_results_dir, empty_scenarios)
        tools = server._tool_manager._tools
        list_scenarios_tool = tools["list_scenarios"]

        result = await list_scenarios_tool.fn()

        assert "no scenario files found" in result.lower()


class TestListResults:
    """Tests for list_results tool."""

    @pytest.mark.asyncio
    async def test_list_results_returns_recent(
        self,
        temp_results_dir: Path,
        temp_scenarios_dir: Path,
        sample_test_run: TestRunResult,
    ) -> None:
        """Test that list_results returns recent results."""
        # Save a test run
        storage = ResultStorage(temp_results_dir)
        storage.save(sample_test_run)

        server = create_server(temp_results_dir, temp_scenarios_dir)
        tools = server._tool_manager._tools
        list_results_tool = tools["list_results"]

        result = await list_results_tool.fn()

        assert sample_test_run.scenario_name in result
        assert "PASSED" in result

    @pytest.mark.asyncio
    async def test_list_results_empty(
        self,
        temp_results_dir: Path,
        temp_scenarios_dir: Path,
    ) -> None:
        """Test that list_results handles no results."""
        server = create_server(temp_results_dir, temp_scenarios_dir)
        tools = server._tool_manager._tools
        list_results_tool = tools["list_results"]

        result = await list_results_tool.fn()

        assert "no test results found" in result.lower()


class TestGetResult:
    """Tests for get_result tool."""

    @pytest.mark.asyncio
    async def test_get_result_by_id(
        self,
        temp_results_dir: Path,
        temp_scenarios_dir: Path,
        sample_test_run: TestRunResult,
    ) -> None:
        """Test retrieving a result by ID."""
        storage = ResultStorage(temp_results_dir)
        storage.save(sample_test_run)

        server = create_server(temp_results_dir, temp_scenarios_dir)
        tools = server._tool_manager._tools
        get_result_tool = tools["get_result"]

        result = await get_result_tool.fn(run_id=sample_test_run.run_id)

        # Result is JSON
        assert sample_test_run.run_id in result
        assert "Weather Query Test" in result

    @pytest.mark.asyncio
    async def test_get_result_not_found(
        self,
        temp_results_dir: Path,
        temp_scenarios_dir: Path,
    ) -> None:
        """Test that get_result handles missing ID."""
        server = create_server(temp_results_dir, temp_scenarios_dir)
        tools = server._tool_manager._tools
        get_result_tool = tools["get_result"]

        result = await get_result_tool.fn(run_id="nonexistent")

        assert "no result found" in result.lower()


class TestGetConversation:
    """Tests for get_conversation tool."""

    @pytest.mark.asyncio
    async def test_get_conversation_formats_turns(
        self,
        temp_results_dir: Path,
        temp_scenarios_dir: Path,
        sample_test_run: TestRunResult,
    ) -> None:
        """Test that get_conversation formats conversation turns."""
        storage = ResultStorage(temp_results_dir)
        storage.save(sample_test_run)

        server = create_server(temp_results_dir, temp_scenarios_dir)
        tools = server._tool_manager._tools
        get_conversation_tool = tools["get_conversation"]

        result = await get_conversation_tool.fn(run_id=sample_test_run.run_id)

        assert "USER" in result
        assert "ASSISTANT" in result
        assert "Seattle" in result
        assert "get_weather" in result


class TestGetJudgment:
    """Tests for get_judgment tool."""

    @pytest.mark.asyncio
    async def test_get_judgment_formats_criteria(
        self,
        temp_results_dir: Path,
        temp_scenarios_dir: Path,
        sample_test_run: TestRunResult,
    ) -> None:
        """Test that get_judgment formats correctness criteria."""
        storage = ResultStorage(temp_results_dir)
        storage.save(sample_test_run)

        server = create_server(temp_results_dir, temp_scenarios_dir)
        tools = server._tool_manager._tools
        get_judgment_tool = tools["get_judgment"]

        result = await get_judgment_tool.fn(run_id=sample_test_run.run_id)

        assert "PASSED" in result
        assert "**Score**: 0.85" in result
        assert "Mentions Temperature" in result
        assert "Correct Location" in result


class TestGetSuggestions:
    """Tests for get_suggestions tool."""

    @pytest.mark.asyncio
    async def test_get_suggestions_formats_structured(
        self,
        temp_results_dir: Path,
        temp_scenarios_dir: Path,
        sample_test_run: TestRunResult,
    ) -> None:
        """Test that get_suggestions formats structured suggestions."""
        storage = ResultStorage(temp_results_dir)
        storage.save(sample_test_run)

        server = create_server(temp_results_dir, temp_scenarios_dir)
        tools = server._tool_manager._tools
        get_suggestions_tool = tools["get_suggestions"]

        result = await get_suggestions_tool.fn(run_id=sample_test_run.run_id)

        assert "DESCRIPTION" in result
        assert "get_weather" in result
        assert "Consider caching" in result


class TestGetLatest:
    """Tests for get_latest tool."""

    @pytest.mark.asyncio
    async def test_get_latest_returns_most_recent(
        self,
        temp_results_dir: Path,
        temp_scenarios_dir: Path,
        sample_test_run: TestRunResult,
    ) -> None:
        """Test that get_latest returns the most recent result."""
        storage = ResultStorage(temp_results_dir)
        storage.save(sample_test_run)

        server = create_server(temp_results_dir, temp_scenarios_dir)
        tools = server._tool_manager._tools
        get_latest_tool = tools["get_latest"]

        result = await get_latest_tool.fn()

        assert "Weather Query Test" in result
        assert "PASSED" in result


class TestRunScenario:
    """Tests for run_scenario tool."""

    @pytest.mark.asyncio
    async def test_run_scenario_requires_config(
        self,
        temp_results_dir: Path,
        temp_scenarios_dir: Path,
    ) -> None:
        """Test that run_scenario returns error when no config is provided."""
        server = create_server(temp_results_dir, temp_scenarios_dir)
        tools = server._tool_manager._tools
        run_scenario_tool = tools["run_scenario"]

        result = await run_scenario_tool.fn(scenario_path="weather.yaml")

        assert "error" in result.lower()
        assert "configuration" in result.lower()

    @pytest.mark.asyncio
    async def test_run_scenario_handles_missing_file(
        self,
        temp_results_dir: Path,
        temp_scenarios_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Test that run_scenario handles missing scenario file."""
        # Create a minimal config file
        config_file = tmp_path / "mcprobe.yaml"
        config_file.write_text("""
llm:
  provider: ollama
  model: llama3.2
  base_url: http://localhost:11434
""")

        server = create_server(temp_results_dir, temp_scenarios_dir, config_file)
        tools = server._tool_manager._tools
        run_scenario_tool = tools["run_scenario"]

        result = await run_scenario_tool.fn(scenario_path="nonexistent.yaml")

        assert "error" in result.lower()
        assert "not found" in result.lower()


class TestRunScenarios:
    """Tests for run_scenarios tool."""

    async def test_run_scenarios_requires_config(
        self,
        temp_results_dir: Path,
        temp_scenarios_dir: Path,
    ) -> None:
        """Test that run_scenarios requires config file."""
        server = create_server(temp_results_dir, temp_scenarios_dir)
        tools = server._tool_manager._tools
        run_scenarios_tool = tools["run_scenarios"]

        result = await run_scenarios_tool.fn(scenario_paths=["test.yaml"])

        assert "error" in result.lower()
        assert "configuration" in result.lower()

    async def test_run_scenarios_handles_empty_list(
        self,
        temp_results_dir: Path,
        temp_scenarios_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Test that run_scenarios handles empty scenario list."""
        config_file = tmp_path / "mcprobe.yaml"
        config_file.write_text("""
llm:
  provider: ollama
  model: llama3.2
  base_url: http://localhost:11434
""")

        server = create_server(temp_results_dir, temp_scenarios_dir, config_file)
        tools = server._tool_manager._tools
        run_scenarios_tool = tools["run_scenarios"]

        result = await run_scenarios_tool.fn(scenario_paths=[])

        assert "error" in result.lower()
        assert "no scenario" in result.lower()

    async def test_run_scenarios_handles_missing_files(
        self,
        temp_results_dir: Path,
        temp_scenarios_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Test that run_scenarios handles missing scenario files gracefully."""
        config_file = tmp_path / "mcprobe.yaml"
        config_file.write_text("""
llm:
  provider: ollama
  model: llama3.2
  base_url: http://localhost:11434
""")

        server = create_server(temp_results_dir, temp_scenarios_dir, config_file)
        tools = server._tool_manager._tools
        run_scenarios_tool = tools["run_scenarios"]

        result = await run_scenarios_tool.fn(
            scenario_paths=["nonexistent1.yaml", "nonexistent2.yaml"]
        )

        # Should report failures but complete
        assert "0/2 passed" in result
        assert "file not found" in result.lower()


class TestServerCreation:
    """Tests for server creation."""

    def test_create_server_returns_fastmcp(
        self,
        temp_results_dir: Path,
        temp_scenarios_dir: Path,
    ) -> None:
        """Test that create_server returns a FastMCP instance."""
        from mcp.server.fastmcp import FastMCP

        server = create_server(temp_results_dir, temp_scenarios_dir)

        assert isinstance(server, FastMCP)

    def test_create_server_registers_all_tools(
        self,
        temp_results_dir: Path,
        temp_scenarios_dir: Path,
    ) -> None:
        """Test that create_server registers all expected tools."""
        server = create_server(temp_results_dir, temp_scenarios_dir)

        tools = server._tool_manager._tools
        expected_tools = [
            "list_scenarios",
            "list_results",
            "get_result",
            "get_conversation",
            "get_judgment",
            "get_suggestions",
            "get_trends",
            "get_latest",
            "run_scenario",
            "run_scenarios",
            "generate_report",
        ]

        for tool_name in expected_tools:
            assert tool_name in tools, f"Tool {tool_name} not registered"
