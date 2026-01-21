"""Integration tests for pytest plugin."""

from pathlib import Path

import pytest


@pytest.fixture
def sample_scenario_file(tmp_path: Path) -> Path:
    """Create a sample scenario YAML file."""
    scenario_content = """
name: "Test Scenario"
description: "A test scenario for pytest plugin"

synthetic_user:
  persona: "A test user"
  initial_query: "Hello, how are you?"
  clarification_behavior:
    known_facts:
      - "I am a test user"
    unknown_facts: []
    traits:
      patience: high
      verbosity: concise
      expertise: novice
  max_turns: 5

evaluation:
  correctness_criteria:
    - "Responds politely"
  failure_criteria:
    - "Fails to respond"
  tool_usage:
    required_tools: []
    optional_tools: []
    prohibited_tools: []
  efficiency:
    max_tool_calls: 3
    max_conversation_turns: 5
"""
    scenario_file = tmp_path / "test_scenario.yaml"
    scenario_file.write_text(scenario_content)
    return scenario_file


@pytest.fixture
def non_scenario_file(tmp_path: Path) -> Path:
    """Create a non-scenario YAML file."""
    content = """
name: "Not a scenario"
some_other_key: "value"
"""
    non_scenario = tmp_path / "not_a_scenario.yaml"
    non_scenario.write_text(content)
    return non_scenario


class TestPytestPluginCollection:
    """Tests for pytest plugin file collection."""

    def test_imports_work(self) -> None:
        """Test that plugin module imports work."""
        from mcprobe.pytest_plugin import (
            MCProbeFile,
            MCProbeItem,
            pytest_addoption,
            pytest_collect_file,
        )

        assert MCProbeFile is not None
        assert MCProbeItem is not None
        assert pytest_addoption is not None
        assert pytest_collect_file is not None

    def test_mcprobe_file_exists(self) -> None:
        """Test MCProbeFile class is accessible."""
        from mcprobe.pytest_plugin import MCProbeFile

        assert issubclass(MCProbeFile, pytest.File)

    def test_mcprobe_item_exists(self) -> None:
        """Test MCProbeItem class is accessible."""
        from mcprobe.pytest_plugin import MCProbeItem

        assert issubclass(MCProbeItem, pytest.Item)


class TestPytestPluginOptions:
    """Tests for pytest plugin options."""

    def test_addoption_registers_options(self, pytestconfig: pytest.Config) -> None:
        """Test that plugin options are registered."""
        # These should not raise if options are registered
        pytestconfig.getoption("--mcprobe-model", default=None)
        pytestconfig.getoption("--mcprobe-base-url", default=None)
        pytestconfig.getoption("--mcprobe-agent-type", default=None)


class TestMCProbeAssertionError:
    """Tests for MCProbeAssertionError."""

    def test_assertion_error_creation(self) -> None:
        """Test creating MCProbeAssertionError."""
        from mcprobe.models.conversation import ConversationResult, TerminationReason
        from mcprobe.models.judgment import JudgmentResult
        from mcprobe.pytest_plugin import MCProbeAssertionError

        conversation = ConversationResult(
            turns=[],
            final_answer="test",
            total_tool_calls=[],
            total_tokens=0,
            duration_seconds=1.0,
            termination_reason=TerminationReason.CRITERIA_MET,
        )

        judgment = JudgmentResult(
            passed=False,
            score=0.5,
            correctness_results={"test": False},
            failure_results={},
            tool_usage_results={},
            efficiency_results={},
            reasoning="Test failed",
        )

        error = MCProbeAssertionError("Test error", conversation, judgment)

        assert str(error) == "Test error"
        assert error.conversation_result == conversation
        assert error.judgment_result == judgment
