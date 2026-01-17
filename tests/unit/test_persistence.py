"""Tests for persistence module."""

import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from mcprobe.models.conversation import ConversationResult, TerminationReason, ToolCall
from mcprobe.models.judgment import JudgmentResult, QualityMetrics
from mcprobe.persistence import ResultLoader, ResultStorage, TestRunResult


@pytest.fixture
def temp_results_dir(tmp_path: Path) -> Path:
    """Create a temporary results directory."""
    return tmp_path / "test-results"


@pytest.fixture
def sample_conversation_result() -> ConversationResult:
    """Create a sample conversation result."""
    return ConversationResult(
        turns=[],
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
        termination_reason=TerminationReason.USER_SATISFIED,
    )


@pytest.fixture
def sample_judgment_result() -> JudgmentResult:
    """Create a sample judgment result."""
    return JudgmentResult(
        passed=True,
        score=0.85,
        correctness_results={"mentions_temperature": True},
        failure_results={"wrong_location": False},
        tool_usage_results={"required_tools_used": True},
        efficiency_results={"within_limits": True},
        reasoning="The agent correctly answered the weather question.",
        suggestions=[],
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
        model_name="llama3.2",
        duration_seconds=2.5,
        mcprobe_version="0.1.0",
        python_version="3.12.0",
    )


class TestResultStorage:
    """Tests for ResultStorage class."""

    def test_save_creates_directories(
        self,
        temp_results_dir: Path,
        sample_test_run: TestRunResult,
    ) -> None:
        """Test that save creates the necessary directories."""
        storage = ResultStorage(temp_results_dir)
        storage.save(sample_test_run)

        assert temp_results_dir.exists()
        assert (temp_results_dir / "runs").exists()
        assert (temp_results_dir / "trends").exists()

    def test_save_creates_run_file(
        self,
        temp_results_dir: Path,
        sample_test_run: TestRunResult,
    ) -> None:
        """Test that save creates a run file."""
        storage = ResultStorage(temp_results_dir)
        path = storage.save(sample_test_run)

        assert path.exists()
        assert path.suffix == ".json"
        assert sample_test_run.run_id[:8] in path.name

    def test_save_updates_index(
        self,
        temp_results_dir: Path,
        sample_test_run: TestRunResult,
    ) -> None:
        """Test that save updates the index file."""
        storage = ResultStorage(temp_results_dir)
        storage.save(sample_test_run)

        index_path = temp_results_dir / "index.json"
        assert index_path.exists()

        loader = ResultLoader(temp_results_dir)
        index = loader.load_index()
        assert len(index.entries) == 1
        assert index.entries[0].run_id == sample_test_run.run_id

    def test_save_updates_trends(
        self,
        temp_results_dir: Path,
        sample_test_run: TestRunResult,
    ) -> None:
        """Test that save updates the trends file."""
        storage = ResultStorage(temp_results_dir)
        storage.save(sample_test_run)

        # Check trends file was created
        trends_dir = temp_results_dir / "trends"
        trend_files = list(trends_dir.glob("*.json"))
        assert len(trend_files) == 1

    def test_save_multiple_runs(
        self,
        temp_results_dir: Path,
        sample_conversation_result: ConversationResult,
        sample_judgment_result: JudgmentResult,
    ) -> None:
        """Test saving multiple test runs."""
        storage = ResultStorage(temp_results_dir)

        # Save 3 runs
        for i in range(3):
            run = TestRunResult(
                run_id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                scenario_name="Weather Query Test",
                scenario_file="scenarios/weather.yaml",
                scenario_tags=[],
                conversation_result=sample_conversation_result,
                judgment_result=sample_judgment_result,
                agent_type="simple",
                model_name="llama3.2",
                duration_seconds=2.5 + i,
                mcprobe_version="0.1.0",
                python_version="3.12.0",
            )
            storage.save(run)

        loader = ResultLoader(temp_results_dir)
        index = loader.load_index()
        assert len(index.entries) == 3

    def test_cleanup_old_runs(
        self,
        temp_results_dir: Path,
        sample_conversation_result: ConversationResult,
        sample_judgment_result: JudgmentResult,
    ) -> None:
        """Test cleanup of old run files."""
        storage = ResultStorage(temp_results_dir)

        # Create an old run
        old_run = TestRunResult(
            run_id=str(uuid.uuid4()),
            timestamp=datetime.now() - timedelta(days=60),
            scenario_name="Old Test",
            scenario_file="scenarios/old.yaml",
            scenario_tags=[],
            conversation_result=sample_conversation_result,
            judgment_result=sample_judgment_result,
            agent_type="simple",
            model_name="llama3.2",
            duration_seconds=1.0,
            mcprobe_version="0.1.0",
            python_version="3.12.0",
        )
        storage.save(old_run)

        # Create a recent run
        recent_run = TestRunResult(
            run_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            scenario_name="Recent Test",
            scenario_file="scenarios/recent.yaml",
            scenario_tags=[],
            conversation_result=sample_conversation_result,
            judgment_result=sample_judgment_result,
            agent_type="simple",
            model_name="llama3.2",
            duration_seconds=1.0,
            mcprobe_version="0.1.0",
            python_version="3.12.0",
        )
        storage.save(recent_run)

        # Cleanup with 30 day max age
        removed = storage.cleanup_old_runs(max_age_days=30)

        assert removed == 1

        loader = ResultLoader(temp_results_dir)
        index = loader.load_index()
        assert len(index.entries) == 1
        assert index.entries[0].scenario_name == "Recent Test"


class TestResultLoader:
    """Tests for ResultLoader class."""

    def test_load_by_id(
        self,
        temp_results_dir: Path,
        sample_test_run: TestRunResult,
    ) -> None:
        """Test loading a run by ID."""
        storage = ResultStorage(temp_results_dir)
        storage.save(sample_test_run)

        loader = ResultLoader(temp_results_dir)
        loaded = loader.load(sample_test_run.run_id)

        assert loaded is not None
        assert loaded.run_id == sample_test_run.run_id
        assert loaded.scenario_name == sample_test_run.scenario_name

    def test_load_nonexistent_returns_none(
        self,
        temp_results_dir: Path,
    ) -> None:
        """Test that loading nonexistent run returns None."""
        loader = ResultLoader(temp_results_dir)
        result = loader.load("nonexistent-id")

        assert result is None

    def test_load_latest(
        self,
        temp_results_dir: Path,
        sample_conversation_result: ConversationResult,
        sample_judgment_result: JudgmentResult,
    ) -> None:
        """Test loading the most recent run."""
        storage = ResultStorage(temp_results_dir)

        # Save runs with different timestamps
        for i in range(3):
            run = TestRunResult(
                run_id=str(uuid.uuid4()),
                timestamp=datetime.now() + timedelta(seconds=i),
                scenario_name=f"Test {i}",
                scenario_file=f"scenarios/test{i}.yaml",
                scenario_tags=[],
                conversation_result=sample_conversation_result,
                judgment_result=sample_judgment_result,
                agent_type="simple",
                model_name="llama3.2",
                duration_seconds=1.0,
                mcprobe_version="0.1.0",
                python_version="3.12.0",
            )
            storage.save(run)

        loader = ResultLoader(temp_results_dir)
        latest = loader.load_latest()

        assert latest is not None
        assert latest.scenario_name == "Test 2"

    def test_load_latest_by_scenario(
        self,
        temp_results_dir: Path,
        sample_conversation_result: ConversationResult,
        sample_judgment_result: JudgmentResult,
    ) -> None:
        """Test loading the most recent run for a specific scenario."""
        storage = ResultStorage(temp_results_dir)

        # Save runs for different scenarios
        for i in range(3):
            run = TestRunResult(
                run_id=str(uuid.uuid4()),
                timestamp=datetime.now() + timedelta(seconds=i),
                scenario_name="Weather Test" if i % 2 == 0 else "Other Test",
                scenario_file="scenarios/test.yaml",
                scenario_tags=[],
                conversation_result=sample_conversation_result,
                judgment_result=sample_judgment_result,
                agent_type="simple",
                model_name="llama3.2",
                duration_seconds=1.0,
                mcprobe_version="0.1.0",
                python_version="3.12.0",
            )
            storage.save(run)

        loader = ResultLoader(temp_results_dir)
        latest = loader.load_latest(scenario_name="Weather Test")

        assert latest is not None
        assert latest.scenario_name == "Weather Test"

    def test_list_scenarios(
        self,
        temp_results_dir: Path,
        sample_conversation_result: ConversationResult,
        sample_judgment_result: JudgmentResult,
    ) -> None:
        """Test listing unique scenario names."""
        storage = ResultStorage(temp_results_dir)

        scenarios = ["Weather Test", "Search Test", "Weather Test"]
        for scenario_name in scenarios:
            run = TestRunResult(
                run_id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                scenario_name=scenario_name,
                scenario_file="scenarios/test.yaml",
                scenario_tags=[],
                conversation_result=sample_conversation_result,
                judgment_result=sample_judgment_result,
                agent_type="simple",
                model_name="llama3.2",
                duration_seconds=1.0,
                mcprobe_version="0.1.0",
                python_version="3.12.0",
            )
            storage.save(run)

        loader = ResultLoader(temp_results_dir)
        scenario_list = loader.list_scenarios()

        assert len(scenario_list) == 2
        assert "Weather Test" in scenario_list
        assert "Search Test" in scenario_list

    def test_load_trend_data(
        self,
        temp_results_dir: Path,
        sample_test_run: TestRunResult,
    ) -> None:
        """Test loading lightweight trend data."""
        storage = ResultStorage(temp_results_dir)
        storage.save(sample_test_run)

        loader = ResultLoader(temp_results_dir)
        trend_data = loader.load_trend_data(sample_test_run.scenario_name)

        assert len(trend_data) == 1
        assert trend_data[0]["passed"] is True
        assert trend_data[0]["score"] == 0.85


class TestTestRunResult:
    """Tests for TestRunResult model."""

    def test_model_serialization(
        self,
        sample_test_run: TestRunResult,
    ) -> None:
        """Test that TestRunResult can be serialized and deserialized."""
        json_str = sample_test_run.model_dump_json()
        restored = TestRunResult.model_validate_json(json_str)

        assert restored.run_id == sample_test_run.run_id
        assert restored.scenario_name == sample_test_run.scenario_name
        assert restored.judgment_result.passed == sample_test_run.judgment_result.passed

    def test_model_with_git_info(
        self,
        sample_conversation_result: ConversationResult,
        sample_judgment_result: JudgmentResult,
    ) -> None:
        """Test TestRunResult with git information."""
        run = TestRunResult(
            run_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            scenario_name="Test",
            scenario_file="test.yaml",
            conversation_result=sample_conversation_result,
            judgment_result=sample_judgment_result,
            agent_type="simple",
            model_name="llama3.2",
            duration_seconds=1.0,
            mcprobe_version="0.1.0",
            python_version="3.12.0",
            git_commit="abc123",
            git_branch="main",
            ci_environment={"CI": "true", "GITHUB_ACTIONS": "true"},
        )

        assert run.git_commit == "abc123"
        assert run.git_branch == "main"
        assert run.ci_environment["CI"] == "true"
