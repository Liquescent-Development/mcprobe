"""Main pytest plugin implementation for MCProbe.

Provides pytest integration for running MCProbe test scenarios.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import pytest
from _pytest._code.code import TerminalRepr

from mcprobe import __version__
from mcprobe.agents.base import AgentUnderTest
from mcprobe.agents.simple import SimpleLLMAgent
from mcprobe.config import CLIOverrides, ConfigLoader, FileConfig
from mcprobe.exceptions import MCProbeError
from mcprobe.judge.judge import ConversationJudge
from mcprobe.models.scenario import TestScenario
from mcprobe.orchestrator.orchestrator import ConversationOrchestrator
from mcprobe.parser.scenario import ScenarioParser
from mcprobe.persistence import ResultStorage, TestRunResult
from mcprobe.providers.factory import create_provider
from mcprobe.synthetic_user.user import SyntheticUserLLM

if TYPE_CHECKING:
    from mcprobe.models.conversation import ConversationResult
    from mcprobe.models.judgment import JudgmentResult


def compute_hash(content: str | list[Any] | dict[str, Any] | None) -> str | None:
    """Compute SHA256 hash of content for change detection.

    Args:
        content: String, list, dict, or None to hash.

    Returns:
        First 16 characters of SHA256 hex digest, or None if content is None.
    """
    if content is None:
        return None
    if isinstance(content, (list, dict)):
        content = json.dumps(content, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class ScenarioRunConfig:
    """Configuration for running a single scenario."""

    file_config: FileConfig | None
    cli_overrides: CLIOverrides
    cli_agent_type: str | None
    cli_agent_factory: str | None
    save_results: bool
    results_dir: Path


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

        # Add mcprobe marker and tag-based markers for filtering
        self.add_marker(pytest.mark.mcprobe)
        for tag in scenario.tags:
            # Tags become pytest markers for filtering (e.g., pytest -m smoke)
            self.add_marker(getattr(pytest.mark, tag))

    def runtest(self) -> None:
        """Execute the test scenario."""
        # Get configuration from pytest options
        pytest_config = self.config

        # Load config file if specified or discover it
        config_path = pytest_config.getoption("--mcprobe-config")
        file_config = ConfigLoader.load_config(Path(config_path) if config_path else None)

        # Build CLI overrides from pytest options
        cli_overrides = CLIOverrides(
            provider=pytest_config.getoption("--mcprobe-provider"),
            model=pytest_config.getoption("--mcprobe-model"),
            base_url=pytest_config.getoption("--mcprobe-base-url"),
        )

        # Resolve results config
        results_config = ConfigLoader.resolve_results_config(
            file_config,
            cli_save=pytest_config.getoption("--mcprobe-save-results"),
            cli_dir=pytest_config.getoption("--mcprobe-results-dir"),
        )

        run_config = ScenarioRunConfig(
            file_config=file_config,
            cli_overrides=cli_overrides,
            cli_agent_type=pytest_config.getoption("--mcprobe-agent-type"),
            cli_agent_factory=pytest_config.getoption("--mcprobe-agent-factory"),
            save_results=results_config.save,
            results_dir=Path(results_config.dir),
        )

        # Run the scenario
        asyncio.run(self._run_scenario(run_config))

    async def _run_scenario(self, config: ScenarioRunConfig) -> None:
        """Run the scenario asynchronously.

        Args:
            config: Configuration for running the scenario.
        """
        # Resolve agent configuration
        agent_config = ConfigLoader.resolve_agent_config(
            config.file_config,
            cli_agent_type=config.cli_agent_type,
            cli_agent_factory=config.cli_agent_factory,
        )

        # Extract scenario-level overrides if present
        scenario_judge_override = None
        scenario_user_override = None
        if self.scenario.config:
            scenario_judge_override = self.scenario.config.judge
            scenario_user_override = self.scenario.config.synthetic_user

        # Resolve LLM configs for each component (with scenario overrides)
        judge_config = ConfigLoader.resolve_llm_config(
            config.file_config,
            "judge",
            config.cli_overrides,
            scenario_override=scenario_judge_override,
        )
        synthetic_user_config = ConfigLoader.resolve_llm_config(
            config.file_config,
            "synthetic_user",
            config.cli_overrides,
            scenario_override=scenario_user_override,
        )

        # Create providers for each component
        judge_provider = create_provider(judge_config)
        synthetic_user_provider = create_provider(synthetic_user_config)

        # Create agent
        agent: AgentUnderTest
        if agent_config.type == "adk":
            if agent_config.factory is None:
                msg = "ADK agent requires factory path in config or --mcprobe-agent-factory"
                raise MCProbeError(msg)
            agent = self._create_adk_agent(agent_config.factory)
        else:
            # Simple agent uses synthetic_user config (shared LLM)
            agent = SimpleLLMAgent(synthetic_user_provider)

        # Extract MCP tool schemas if server configured
        mcp_schemas: list[dict[str, Any]] = []
        if config.file_config and config.file_config.mcp_server:
            try:
                from mcprobe.generator.mcp_client import extract_tools  # noqa: PLC0415

                server_tools = await extract_tools(config.file_config.mcp_server)
                mcp_schemas = [
                    {
                        "name": t.name,
                        "description": t.description,
                        "input_schema": t.input_schema,
                    }
                    for t in server_tools.tools
                ]
            except Exception:
                # Don't fail the test if schema extraction fails
                pass

        # Reset agent for new scenario
        await agent.reset()

        # Create components (with extra_instructions from resolved configs)
        synthetic_user = SyntheticUserLLM(
            synthetic_user_provider,
            self.scenario.synthetic_user,
            extra_instructions=synthetic_user_config.extra_instructions,
        )
        judge = ConversationJudge(
            judge_provider,
            extra_instructions=judge_config.extra_instructions,
        )
        orchestrator = ConversationOrchestrator(agent, synthetic_user, judge)

        # Run the scenario
        self.conversation_result, self.judgment_result = await orchestrator.run(self.scenario)

        # Save results if enabled
        if config.save_results:
            await self._save_results(
                results_dir=config.results_dir,
                agent_type=agent_config.type,
                agent=agent,
                mcp_schemas=mcp_schemas,
                judge_model=judge_config.model,
                synthetic_user_model=synthetic_user_config.model,
            )

        # Assert the test passed
        if not self.judgment_result.passed:
            msg = f"Scenario failed: {self.judgment_result.reasoning}"
            raise MCProbeAssertionError(
                msg,
                self.conversation_result,
                self.judgment_result,
            )

    def _create_adk_agent(self, factory_path: str) -> AgentUnderTest:
        """Create an ADK agent from a factory module.

        Args:
            factory_path: Path to the agent factory module.

        Returns:
            Configured ADK agent wrapper.
        """
        from mcprobe.agents.adk import (  # noqa: PLC0415
            GeminiADKAgent,
            load_agent_factory,
        )

        factory = load_agent_factory(factory_path)
        adk_agent = factory()
        return GeminiADKAgent(adk_agent)

    async def _save_results(  # noqa: PLR0913
        self,
        results_dir: Path,
        agent_type: str,
        agent: AgentUnderTest,
        mcp_schemas: list[dict[str, Any]],
        judge_model: str,
        synthetic_user_model: str,
    ) -> None:
        """Save test results to storage.

        Args:
            results_dir: Directory to save results.
            agent_type: Agent type used.
            agent: The agent under test (for extracting system prompt and model).
            mcp_schemas: MCP tool schemas extracted from server.
            judge_model: Model name used for the judge.
            synthetic_user_model: Model name used for the synthetic user.
        """
        if self.conversation_result is None or self.judgment_result is None:
            return

        git_commit = self._get_git_commit()
        git_branch = self._get_git_branch()

        # Use the session-level run_id so all tests in this run are grouped together
        run_id = getattr(self.config, "mcprobe_run_id", str(uuid.uuid4()))

        # Extract system prompt from agent
        system_prompt = agent.get_system_prompt()

        # Determine agent model: for simple agents it's the same as synthetic_user,
        # for ADK agents try to get it from the agent itself
        agent_model_name: str | None
        if agent_type == "simple":
            agent_model_name = synthetic_user_model
        else:
            agent_model_name = agent.get_model_name()

        result = TestRunResult(
            run_id=run_id,
            timestamp=datetime.now(),
            scenario_name=self.scenario.name,
            scenario_file=str(self.path),
            scenario_tags=self.scenario.tags,
            conversation_result=self.conversation_result,
            judgment_result=self.judgment_result,
            agent_type=agent_type,
            duration_seconds=self.conversation_result.duration_seconds,
            # LLM models used
            judge_model=judge_model,
            synthetic_user_model=synthetic_user_model,
            agent_model=agent_model_name,
            mcprobe_version=__version__,
            python_version=sys.version.split()[0],
            git_commit=git_commit,
            git_branch=git_branch,
            ci_environment=self._get_ci_environment(),
            # Agent configuration capture
            agent_system_prompt=system_prompt,
            agent_system_prompt_hash=compute_hash(system_prompt),
            mcp_tool_schemas=mcp_schemas,
            mcp_tool_schemas_hash=compute_hash(mcp_schemas) if mcp_schemas else None,
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
        "--mcprobe-config",
        action="store",
        default=None,
        help="Path to mcprobe.yaml configuration file",
    )
    group.addoption(
        "--mcprobe-provider",
        action="store",
        default=None,
        help="LLM provider: ollama, openai (default: from config or ollama)",
    )
    group.addoption(
        "--mcprobe-model",
        action="store",
        default=None,
        help="LLM model name for synthetic user and judge (default: from config or llama3.2)",
    )
    group.addoption(
        "--mcprobe-base-url",
        action="store",
        default=None,
        help="LLM provider base URL (default: from config or http://localhost:11434)",
    )
    group.addoption(
        "--mcprobe-agent-type",
        action="store",
        default=None,
        choices=["simple", "adk"],
        help="Agent type: simple or adk (default: from config or simple)",
    )
    group.addoption(
        "--mcprobe-agent-factory",
        action="store",
        default=None,
        help="Path to agent factory module (default: from config)",
    )
    group.addoption(
        "--mcprobe-save-results",
        action="store_true",
        default=None,
        help="Save test results for trend analysis (default: from config or True)",
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
        default=None,
        help="Directory to store test results (default: from config or test-results)",
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
    # Suppress warnings for dynamic scenario tag markers
    config.addinivalue_line(
        "filterwarnings",
        "ignore::pytest.PytestUnknownMarkWarning",
    )
    # Generate a single run_id for the entire pytest session
    config.mcprobe_run_id = str(uuid.uuid4())  # type: ignore[attr-defined]


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
