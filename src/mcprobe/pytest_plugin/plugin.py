"""Main pytest plugin implementation for MCProbe.

Provides pytest integration for running MCProbe test scenarios.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import pytest
from _pytest._code.code import TerminalRepr

from mcprobe import __version__
from mcprobe.agents.base import AgentUnderTest
from mcprobe.agents.simple import SimpleLLMAgent
from mcprobe.exceptions import MCProbeError
from mcprobe.judge.judge import ConversationJudge
from mcprobe.models.config import LLMConfig
from mcprobe.models.scenario import TestScenario
from mcprobe.orchestrator.orchestrator import ConversationOrchestrator
from mcprobe.parser.scenario import ScenarioParser
from mcprobe.persistence import ResultStorage, TestRunResult
from mcprobe.providers.factory import create_provider
from mcprobe.synthetic_user.user import SyntheticUserLLM

if TYPE_CHECKING:
    from mcprobe.models.conversation import ConversationResult
    from mcprobe.models.judgment import JudgmentResult


class MCProbeFile(pytest.File):
    """Pytest collector for MCProbe scenario YAML files."""

    def collect(self) -> list[MCProbeItem]:
        """Collect test items from the scenario file.

        Returns:
            List of MCProbeItem test items.
        """
        parser = ScenarioParser()
        try:
            scenario = parser.parse_file(self.path)
            return [MCProbeItem.from_parent(self, name=scenario.name, scenario=scenario)]
        except MCProbeError as e:
            pytest.fail(f"Failed to parse scenario file {self.path}: {e}")
            return []


class MCProbeItem(pytest.Item):
    """Pytest test item representing a single MCProbe scenario."""

    def __init__(
        self,
        name: str,
        parent: MCProbeFile,
        scenario: TestScenario,
    ) -> None:
        """Initialize the test item.

        Args:
            name: Test name.
            parent: Parent collector.
            scenario: The test scenario.
        """
        super().__init__(name, parent)
        self.scenario = scenario
        self.conversation_result: ConversationResult | None = None
        self.judgment_result: JudgmentResult | None = None

        # Add markers for each tag
        for tag in scenario.tags:
            self.add_marker(pytest.mark.mcprobe)
            self.add_marker(getattr(pytest.mark, tag))

    def runtest(self) -> None:
        """Execute the test scenario."""
        # Get configuration from pytest options
        config = self.config
        model = config.getoption("--mcprobe-model") or "llama3.2"
        base_url = config.getoption("--mcprobe-base-url") or "http://localhost:11434"
        agent_type = config.getoption("--mcprobe-agent-type") or "simple"
        save_results = config.getoption("--mcprobe-save-results")
        results_dir = Path(config.getoption("--mcprobe-results-dir") or "test-results")

        # Run the scenario
        asyncio.get_event_loop().run_until_complete(
            self._run_scenario(model, base_url, agent_type, save_results, results_dir)
        )

    async def _run_scenario(
        self,
        model: str,
        base_url: str,
        agent_type: str,
        save_results: bool,
        results_dir: Path,
    ) -> None:
        """Run the scenario asynchronously.

        Args:
            model: LLM model name.
            base_url: Ollama base URL.
            agent_type: Type of agent (simple or adk).
            save_results: Whether to save results.
            results_dir: Directory to save results.
        """
        # Create LLM config
        llm_config = LLMConfig(provider="ollama", model=model, base_url=base_url)
        provider = create_provider(llm_config)

        # Create agent
        agent: AgentUnderTest
        if agent_type == "adk":
            msg = "ADK agent type requires --mcprobe-agent-factory"
            raise MCProbeError(msg)
        agent = SimpleLLMAgent(provider)

        # Create components
        synthetic_user = SyntheticUserLLM(provider, self.scenario.synthetic_user)
        judge = ConversationJudge(provider)
        orchestrator = ConversationOrchestrator(agent, synthetic_user, judge)

        # Run the scenario
        self.conversation_result, self.judgment_result = await orchestrator.run(self.scenario)

        # Save results if enabled
        if save_results:
            await self._save_results(results_dir, model, agent_type)

        # Assert the test passed
        if not self.judgment_result.passed:
            msg = f"Scenario failed: {self.judgment_result.reasoning}"
            raise MCProbeAssertionError(
                msg,
                self.conversation_result,
                self.judgment_result,
            )

    async def _save_results(
        self,
        results_dir: Path,
        model: str,
        agent_type: str,
    ) -> None:
        """Save test results to storage.

        Args:
            results_dir: Directory to save results.
            model: Model name used.
            agent_type: Agent type used.
        """
        if self.conversation_result is None or self.judgment_result is None:
            return

        git_commit = self._get_git_commit()
        git_branch = self._get_git_branch()

        result = TestRunResult(
            run_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            scenario_name=self.scenario.name,
            scenario_file=str(self.path),
            scenario_tags=self.scenario.tags,
            conversation_result=self.conversation_result,
            judgment_result=self.judgment_result,
            agent_type=agent_type,
            model_name=model,
            duration_seconds=self.conversation_result.duration_seconds,
            mcprobe_version=__version__,
            python_version=sys.version.split()[0],
            git_commit=git_commit,
            git_branch=git_branch,
            ci_environment=self._get_ci_environment(),
        )

        storage = ResultStorage(results_dir)
        storage.save(result)

    def _get_git_commit(self) -> str | None:
        """Get the current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.path.parent,
            )
            return result.stdout.strip()[:7]
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def _get_git_branch(self) -> str | None:
        """Get the current git branch name."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.path.parent,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def _get_ci_environment(self) -> dict[str, str]:
        """Get CI environment variables."""
        ci_vars: dict[str, str] = {}
        ci_env_keys = [
            "CI",
            "GITHUB_ACTIONS",
            "GITHUB_RUN_ID",
            "GITHUB_RUN_NUMBER",
            "GITHUB_SHA",
            "GITHUB_REF",
            "GITLAB_CI",
            "CI_JOB_ID",
            "JENKINS_URL",
            "BUILD_ID",
        ]

        for key in ci_env_keys:
            if key in os.environ:
                ci_vars[key] = os.environ[key]

        return ci_vars

    def repr_failure(
        self,
        excinfo: pytest.ExceptionInfo[BaseException],
        style: Literal["long", "short", "line", "no", "native", "value", "auto"] | None = None,
    ) -> str | TerminalRepr:
        """Return a string representation of the failure.

        Args:
            excinfo: Exception info.
            style: Output style (unused, for compatibility).

        Returns:
            Formatted failure message.
        """
        del style  # Unused, for interface compatibility
        if isinstance(excinfo.value, MCProbeAssertionError):
            error = excinfo.value
            lines = [
                f"Scenario: {self.scenario.name}",
                f"Score: {error.judgment_result.score:.2f}",
                f"Reasoning: {error.judgment_result.reasoning}",
                "",
                "Correctness Results:",
            ]
            for criterion, passed in error.judgment_result.correctness_results.items():
                status = "PASS" if passed else "FAIL"
                lines.append(f"  {criterion}: {status}")

            if error.judgment_result.suggestions:
                lines.append("")
                lines.append("Suggestions:")
                for suggestion in error.judgment_result.suggestions:
                    lines.append(f"  - {suggestion}")

            return "\n".join(lines)
        return str(excinfo.value)

    def reportinfo(self) -> tuple[Path, int | None, str]:
        """Return information for test report.

        Returns:
            Tuple of (path, line, name).
        """
        return self.path, None, f"mcprobe: {self.name}"


class MCProbeAssertionError(AssertionError):
    """Custom assertion error for MCProbe test failures."""

    def __init__(
        self,
        message: str,
        conversation_result: ConversationResult,
        judgment_result: JudgmentResult,
    ) -> None:
        """Initialize the assertion error.

        Args:
            message: Error message.
            conversation_result: The conversation result.
            judgment_result: The judgment result.
        """
        super().__init__(message)
        self.conversation_result = conversation_result
        self.judgment_result = judgment_result


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add MCProbe CLI options to pytest.

    Args:
        parser: pytest argument parser.
    """
    group = parser.getgroup("mcprobe")
    group.addoption(
        "--mcprobe-model",
        action="store",
        default="llama3.2",
        help="LLM model name for synthetic user and judge (default: llama3.2)",
    )
    group.addoption(
        "--mcprobe-base-url",
        action="store",
        default="http://localhost:11434",
        help="Ollama base URL (default: http://localhost:11434)",
    )
    group.addoption(
        "--mcprobe-agent-type",
        action="store",
        default="simple",
        choices=["simple", "adk"],
        help="Agent type: simple or adk (default: simple)",
    )
    group.addoption(
        "--mcprobe-save-results",
        action="store_true",
        default=True,
        help="Save test results for trend analysis (default: True)",
    )
    group.addoption(
        "--mcprobe-no-save-results",
        action="store_false",
        dest="mcprobe_save_results",
        help="Do not save test results",
    )
    group.addoption(
        "--mcprobe-results-dir",
        action="store",
        default="test-results",
        help="Directory to store test results (default: test-results)",
    )


def pytest_collect_file(
    file_path: Path,
    parent: pytest.Collector,
) -> MCProbeFile | None:
    """Collect MCProbe scenario files.

    Args:
        file_path: Path to the file.
        parent: Parent collector.

    Returns:
        MCProbeFile if the file is a scenario file, None otherwise.
    """
    if file_path.suffix in (".yaml", ".yml"):
        # Check if it looks like a scenario file
        try:
            content = file_path.read_text()
            if "synthetic_user:" in content and "evaluation:" in content:
                return MCProbeFile.from_parent(parent, path=file_path)
        except Exception:
            pass
    return None


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest for MCProbe.

    Args:
        config: pytest configuration.
    """
    config.addinivalue_line("markers", "mcprobe: mark test as an MCProbe scenario test")


def pytest_collection_modifyitems(
    config: pytest.Config,  # noqa: ARG001
    items: list[pytest.Item],
) -> None:
    """Modify collected items to add mcprobe marker.

    Args:
        config: pytest configuration.
        items: List of collected items.
    """
    for item in items:
        if isinstance(item, MCProbeItem):
            item.add_marker(pytest.mark.mcprobe)


def get_mcprobe_results(item: pytest.Item) -> dict[str, Any] | None:
    """Get MCProbe results from a test item.

    Args:
        item: The test item.

    Returns:
        Dictionary with conversation and judgment results, or None.
    """
    if isinstance(item, MCProbeItem):
        return {
            "conversation": item.conversation_result,
            "judgment": item.judgment_result,
            "scenario": item.scenario,
        }
    return None
