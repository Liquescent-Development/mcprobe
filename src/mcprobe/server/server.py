"""MCP server implementation using FastMCP.

Provides tools for querying test results, analyzing trends,
and running test scenarios via Model Context Protocol.
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcprobe.analysis.trends import TrendAnalyzer
from mcprobe.config import ConfigLoader, FileConfig
from mcprobe.persistence import ResultLoader, ResultStorage, TestRunResult

# Configure logging (CRITICAL: never use print() in stdio server)
logger = logging.getLogger(__name__)

# Maximum characters for tool result truncation
_MAX_RESULT_LENGTH = 500


def _compute_hash(content: str | list[Any] | dict[str, Any] | None) -> str | None:
    """Compute SHA256 hash of content for change detection.

    Args:
        content: String, list, dict, or None to hash.

    Returns:
        First 16 characters of SHA256 hex digest, or None if content is None.
    """
    if content is None:
        return None

    text = content if isinstance(content, str) else json.dumps(content, sort_keys=True, default=str)
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _format_result_summary(result: TestRunResult) -> str:
    """Format a test result as a brief summary line."""
    status = "PASSED" if result.judgment_result.passed else "FAILED"
    score = result.judgment_result.score
    return (
        f"- **{result.scenario_name}** [{status}] "
        f"Score: {score:.2f} | "
        f"ID: `{result.run_id}` | "
        f"{result.timestamp.strftime('%Y-%m-%d %H:%M')}"
    )


def _format_conversation(result: TestRunResult) -> str:
    """Format conversation transcript for display."""
    lines = [
        f"## Conversation: {result.scenario_name}",
        f"**Run ID**: `{result.run_id}`",
        f"**Termination**: {result.conversation_result.termination_reason.value}",
        f"**Duration**: {result.conversation_result.duration_seconds:.1f}s",
        "",
        "### Transcript",
        "",
    ]

    for turn in result.conversation_result.turns:
        role = turn.role.upper()
        lines.append(f"**[{role}]**: {turn.content}")

        if turn.tool_calls:
            for tc in turn.tool_calls:
                params = json.dumps(tc.parameters, indent=2)
                lines.append(f"  > Tool: `{tc.tool_name}`")
                lines.append(f"  > Parameters: ```json\n{params}\n```")
                if tc.error:
                    lines.append(f"  > Error: {tc.error}")
                elif tc.result is not None:
                    result_str = str(tc.result)
                    if len(result_str) > _MAX_RESULT_LENGTH:
                        result_str = result_str[:_MAX_RESULT_LENGTH] + "..."
                    lines.append(f"  > Result: {result_str}")
                lines.append(f"  > Latency: {tc.latency_ms:.0f}ms")

        lines.append("")

    return "\n".join(lines)


def _format_judgment(result: TestRunResult) -> str:
    """Format judgment result for display."""
    j = result.judgment_result
    lines = [
        f"## Judgment: {result.scenario_name}",
        f"**Run ID**: `{result.run_id}`",
        f"**Status**: {'PASSED' if j.passed else 'FAILED'}",
        f"**Score**: {j.score:.2f}",
        "",
        "### Correctness Criteria",
    ]

    for criterion, passed in j.correctness_results.items():
        icon = "+" if passed else "-"
        human_name = criterion.replace("_", " ").title()
        lines.append(f"  {icon} {human_name}")

    if j.failure_results:
        lines.extend(["", "### Failure Conditions"])
        for criterion, triggered in j.failure_results.items():
            icon = "!" if triggered else " "
            human_name = criterion.replace("_", " ").title()
            lines.append(f"  {icon} {human_name}")

    lines.extend(["", "### Judge Reasoning", j.reasoning])

    if j.quality_metrics:
        qm = j.quality_metrics
        lines.extend([
            "",
            "### Quality Metrics",
            f"- Clarifications asked: {qm.clarification_count}",
            f"- Backtracks: {qm.backtrack_count}",
            f"- Turns to first answer: {qm.turns_to_first_answer}",
            f"- Final answer completeness: {qm.final_answer_completeness:.0%}",
        ])

    return "\n".join(lines)


def _format_suggestions(result: TestRunResult) -> str:
    """Format MCP improvement suggestions for display."""
    j = result.judgment_result
    lines = [
        f"## MCP Improvement Suggestions: {result.scenario_name}",
        f"**Run ID**: `{result.run_id}`",
        "",
    ]

    if not j.structured_suggestions and not j.suggestions:
        lines.append("No suggestions - the MCP server performed well!")
        return "\n".join(lines)

    if j.structured_suggestions:
        lines.append("### Structured Suggestions")
        for s in j.structured_suggestions:
            lines.extend([
                "",
                f"**{s.category.value.upper()}** ({s.severity.value})",
            ])
            if s.tool_name:
                lines.append(f"Tool: `{s.tool_name}`")
            lines.extend([
                f"Issue: {s.issue}",
                f"Suggestion: {s.suggestion}",
            ])

    if j.suggestions:
        lines.extend(["", "### General Suggestions"])
        for suggestion in j.suggestions:
            lines.append(f"- {suggestion}")

    return "\n".join(lines)


def _resolve_scenario_path(scenario_path: str, scenarios_dir: Path) -> Path | None:
    """Resolve scenario path, trying relative then absolute.

    Returns:
        Resolved Path if found, None otherwise.
    """
    full_path = scenarios_dir / scenario_path
    if full_path.exists():
        return full_path
    # Try as absolute path
    full_path = Path(scenario_path)
    if full_path.exists():
        return full_path
    return None


def _create_agent_from_config(
    agent_config: "AgentConfig",
    provider: "LLMProvider",
) -> "AgentUnderTest | str":
    """Create agent based on configuration.

    Returns:
        AgentUnderTest instance, or error string if creation fails.
    """
    from mcprobe.agents.simple import SimpleLLMAgent  # noqa: PLC0415

    if agent_config.type == "adk":
        from mcprobe.agents.adk import (  # noqa: PLC0415
            GeminiADKAgent,
            load_agent_factory,
        )

        if agent_config.factory is None:
            return (
                "Error: Agent factory is required for ADK agent type. "
                "Set 'agent.factory' in config."
            )

        factory = load_agent_factory(agent_config.factory)
        adk_agent = factory()
        return GeminiADKAgent(adk_agent)

    return SimpleLLMAgent(provider)


async def _extract_tool_schemas(
    file_config: "FileConfig",
    agent: "AgentUnderTest",
) -> list[dict[str, Any]]:
    """Extract MCP tool schemas from server config or agent.

    Prefers extracting from mcp_server config (most reliable), falls back
    to agent.get_available_tools() for ADK agents without mcp_server config.

    Args:
        file_config: Configuration with optional mcp_server settings.
        agent: The agent under test (fallback for ADK agents).

    Returns:
        List of tool schema dictionaries.
    """
    tool_schemas: list[dict[str, Any]] = []

    # Try extracting from MCP server config first
    if file_config.mcp_server:
        try:
            from mcprobe.generator.mcp_client import extract_tools  # noqa: PLC0415

            server_tools = await extract_tools(file_config.mcp_server)
            tool_schemas = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.input_schema,
                }
                for t in server_tools.tools
            ]
        except Exception as e:
            logger.warning("Failed to extract MCP tool schemas from server: %s", e)

    # Fall back to agent's tools (for ADK agents without mcp_server config)
    if not tool_schemas:
        try:
            tool_schemas = await agent.get_available_tools()
        except Exception as e:
            logger.warning("Failed to get tools from agent: %s", e)

    return tool_schemas


def _build_test_result(
    scenario: "TestScenario",
    scenario_file: Path,
    results: tuple["ConversationResult", "JudgmentResult"],
    models: tuple[str, str, str | None],  # (judge_model, synthetic_user_model, agent_model)
    agent_info: tuple[str, str | None, list[dict[str, Any]]],  # (type, system_prompt, schemas)
) -> TestRunResult:
    """Build a TestRunResult from scenario execution results."""
    import platform  # noqa: PLC0415
    import uuid  # noqa: PLC0415
    from datetime import datetime  # noqa: PLC0415

    import mcprobe  # noqa: PLC0415

    conversation_result, judgment_result = results
    judge_model, synthetic_user_model, agent_model = models
    agent_type, system_prompt, tool_schemas = agent_info

    return TestRunResult(
        run_id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        scenario_name=scenario.name,
        scenario_file=str(scenario_file),
        scenario_tags=scenario.tags,
        conversation_result=conversation_result,
        judgment_result=judgment_result,
        agent_type=agent_type,
        judge_model=judge_model,
        synthetic_user_model=synthetic_user_model,
        agent_model=agent_model,
        duration_seconds=conversation_result.duration_seconds,
        mcprobe_version=mcprobe.__version__,
        python_version=platform.python_version(),
        agent_system_prompt=system_prompt,
        agent_system_prompt_hash=_compute_hash(system_prompt),
        mcp_tool_schemas=tool_schemas,
        mcp_tool_schemas_hash=_compute_hash(tool_schemas) if tool_schemas else None,
    )


def _resolve_scenario_configs(
    file_config: "FileConfig",
    scenario: "TestScenario",
) -> tuple["LLMConfig", "LLMConfig", "AgentConfig"]:
    """Resolve LLM and agent configs with scenario overrides.

    Args:
        file_config: Global configuration from mcprobe.yaml.
        scenario: Test scenario with optional config overrides.

    Returns:
        Tuple of (judge_config, synthetic_user_config, agent_config).
    """
    from mcprobe.config import ConfigLoader  # noqa: PLC0415

    # Extract scenario-level overrides if present
    scenario_judge_override = None
    scenario_user_override = None
    if scenario.config:
        scenario_judge_override = scenario.config.judge
        scenario_user_override = scenario.config.synthetic_user

    # Resolve separate LLM configs for each component
    judge_config = ConfigLoader.resolve_llm_config(
        file_config,
        "judge",
        scenario_override=scenario_judge_override,
    )
    synthetic_user_config = ConfigLoader.resolve_llm_config(
        file_config,
        "synthetic_user",
        scenario_override=scenario_user_override,
    )
    agent_config = ConfigLoader.resolve_agent_config(file_config)

    return judge_config, synthetic_user_config, agent_config


@dataclass
class ScenarioRunResult:
    """Result of running a single scenario."""

    path: str
    passed: bool
    message: str
    score: float | None = None
    run_result: "TestRunResult | None" = None


# Type hints for lazy imports (TYPE_CHECKING pattern)
if False:
    from mcprobe.agents.base import AgentUnderTest
    from mcprobe.config import AgentConfig, FileConfig
    from mcprobe.models.config import LLMConfig
    from mcprobe.models.conversation import ConversationResult
    from mcprobe.models.judgment import JudgmentResult
    from mcprobe.models.scenario import TestScenario
    from mcprobe.persistence import TestRunResult
    from mcprobe.providers.base import LLMProvider


def create_server(  # noqa: PLR0915 - Server factory with inline tool definitions
    results_dir: Path,
    scenarios_dir: Path,
    config_file: Path | None = None,
) -> FastMCP:
    """Create and configure the MCP server.

    Args:
        results_dir: Directory containing test results.
        scenarios_dir: Directory containing test scenarios.
        config_file: Optional path to mcprobe.yaml configuration file.

    Returns:
        Configured FastMCP server instance.
    """
    mcp = FastMCP("mcprobe")
    loader = ResultLoader(results_dir)
    storage = ResultStorage(results_dir)

    # Load configuration file if provided
    file_config: FileConfig | None = None
    if config_file:
        file_config = ConfigLoader.load_config(config_file)

    # =========================================================================
    # Discovery Tools
    # =========================================================================

    @mcp.tool()
    async def list_scenarios() -> str:
        """List available test scenario files.

        Returns a list of scenario YAML files found in the scenarios directory,
        including their names and paths.
        """
        scenarios = list(scenarios_dir.glob("**/*.yaml")) + list(
            scenarios_dir.glob("**/*.yml")
        )

        if not scenarios:
            return f"No scenario files found in {scenarios_dir}"

        lines = [
            f"## Available Scenarios in {scenarios_dir}",
            "",
        ]

        for path in sorted(scenarios):
            rel_path = path.relative_to(scenarios_dir)
            name = path.stem
            lines.append(f"- **{name}**: `{rel_path}`")

        return "\n".join(lines)

    @mcp.tool()
    async def list_results(
        scenario: str | None = None,
        limit: int = 10,
    ) -> str:
        """List recent test run results.

        Args:
            scenario: Filter by scenario name (optional)
            limit: Maximum number of results to return (default: 10)

        Returns:
            Summary list of recent test results with status and IDs.
        """
        results = loader.load_all(scenario_name=scenario, limit=limit)

        if not results:
            msg = "No test results found"
            if scenario:
                msg += f" for scenario '{scenario}'"
            return msg

        lines = [
            "## Recent Test Results",
            "",
        ]

        if scenario:
            lines.insert(1, f"Filtered by scenario: **{scenario}**")
            lines.insert(2, "")

        for result in results:
            lines.append(_format_result_summary(result))

        passed = sum(1 for r in results if r.judgment_result.passed)
        lines.extend([
            "",
            f"**Summary**: {passed}/{len(results)} passed",
        ])

        return "\n".join(lines)

    # =========================================================================
    # Results Inspection Tools
    # =========================================================================

    @mcp.tool()
    async def get_result(run_id: str) -> str:
        """Get complete test run result by ID.

        Args:
            run_id: The unique identifier of the test run

        Returns:
            Full test result including scenario, conversation, judgment, and metadata.
        """
        result = loader.load(run_id)
        if not result:
            return f"No result found with ID: {run_id}"

        # Return as formatted JSON for complete data
        return json.dumps(result.model_dump(mode="json"), indent=2, default=str)

    @mcp.tool()
    async def get_conversation(run_id: str) -> str:
        """Get conversation transcript for a test run.

        Args:
            run_id: The unique identifier of the test run

        Returns:
            Formatted conversation transcript with tool calls and results.
        """
        result = loader.load(run_id)
        if not result:
            return f"No result found with ID: {run_id}"

        return _format_conversation(result)

    @mcp.tool()
    async def get_judgment(run_id: str) -> str:
        """Get judge evaluation for a test run.

        Args:
            run_id: The unique identifier of the test run

        Returns:
            Formatted judgment with pass/fail status, criteria results,
            reasoning, and quality metrics.
        """
        result = loader.load(run_id)
        if not result:
            return f"No result found with ID: {run_id}"

        return _format_judgment(result)

    @mcp.tool()
    async def get_suggestions(run_id: str) -> str:
        """Get MCP improvement suggestions from a test run.

        Args:
            run_id: The unique identifier of the test run

        Returns:
            Structured suggestions for improving the MCP server based on
            the judge's analysis of tool usage and responses.
        """
        result = loader.load(run_id)
        if not result:
            return f"No result found with ID: {run_id}"

        return _format_suggestions(result)

    # =========================================================================
    # Analysis Tools
    # =========================================================================

    @mcp.tool()
    async def get_trends(scenario: str, window: int = 10) -> str:
        """Get trend analysis for a scenario.

        Args:
            scenario: Name of the scenario to analyze
            window: Number of recent runs to include (default: 10)

        Returns:
            Trend analysis including pass rate, score trends, and
            any detected regressions.
        """
        analyzer = TrendAnalyzer(loader)
        trends = analyzer.analyze_scenario(scenario, window_size=window)

        if not trends:
            return f"Not enough data to analyze trends for '{scenario}'"

        lines = [
            f"## Trend Analysis: {scenario}",
            f"**Window**: Last {window} runs",
            "",
            f"**Pass Rate**: {trends.pass_rate:.0%}",
            f"**Average Score**: {trends.avg_score:.2f}",
            f"**Score Trend**: {trends.score_trend}",
            "",
            "### Performance Metrics",
            f"- Avg Duration: {trends.avg_duration:.1f}s",
            f"- Avg Tool Calls: {trends.avg_tool_calls:.1f}",
            f"- Avg Tokens: {trends.avg_tokens:.0f}",
            "",
            "### Score Range",
            f"- Current: {trends.current_score:.2f}",
            f"- Min: {trends.min_score:.2f}",
            f"- Max: {trends.max_score:.2f}",
            f"- Variance: {trends.score_variance:.3f}",
        ]

        return "\n".join(lines)

    @mcp.tool()
    async def get_latest(scenario: str | None = None) -> str:
        """Get the most recent test result.

        Args:
            scenario: Filter by scenario name (optional)

        Returns:
            The most recent test result judgment and suggestions.
        """
        result = loader.load_latest(scenario_name=scenario)
        if not result:
            msg = "No test results found"
            if scenario:
                msg += f" for scenario '{scenario}'"
            return msg

        # Combine judgment and suggestions
        judgment = _format_judgment(result)
        suggestions = _format_suggestions(result)

        return f"{judgment}\n\n---\n\n{suggestions}"

    # =========================================================================
    # Control Tools
    # =========================================================================

    @mcp.tool()
    async def run_scenario(
        scenario_path: str,
        save_results: bool = True,
    ) -> str:
        """Run a test scenario and return the results.

        Executes a test scenario using the configuration from the mcprobe.yaml
        config file. Requires the server to be started with --config option.

        Args:
            scenario_path: Path to the scenario YAML file (relative to scenarios dir)
            save_results: Whether to save results to the results directory (default: True)

        Returns:
            Formatted judgment and suggestions from the test run.
        """
        from mcprobe.judge.judge import ConversationJudge  # noqa: PLC0415
        from mcprobe.orchestrator.orchestrator import (  # noqa: PLC0415
            ConversationOrchestrator,
        )
        from mcprobe.parser.scenario import ScenarioParser  # noqa: PLC0415
        from mcprobe.providers.factory import create_provider  # noqa: PLC0415
        from mcprobe.synthetic_user.user import SyntheticUserLLM  # noqa: PLC0415

        # Validate prerequisites
        if not file_config:
            return (
                "Error: Cannot run scenarios without configuration. "
                "Start the server with --config option pointing to mcprobe.yaml"
            )

        full_path = _resolve_scenario_path(scenario_path, scenarios_dir)
        if full_path is None:
            return f"Error: Scenario file not found: {scenario_path}"

        # Parse scenario and resolve configs
        parser = ScenarioParser()
        try:
            scenario = parser.parse_file(full_path)
        except Exception as e:
            return f"Error parsing scenario: {e}"

        # Resolve configs with scenario overrides
        judge_config, synthetic_user_config, agent_config = _resolve_scenario_configs(
            file_config, scenario
        )

        # Create and run with proper cleanup
        try:
            judge_provider = create_provider(judge_config)
            synthetic_user_provider = create_provider(synthetic_user_config)
            agent_or_error = _create_agent_from_config(agent_config, synthetic_user_provider)
            if isinstance(agent_or_error, str):
                return agent_or_error
            agent = agent_or_error

            synthetic_user = SyntheticUserLLM(
                synthetic_user_provider,
                scenario.synthetic_user,
                extra_instructions=synthetic_user_config.extra_instructions,
            )
            judge = ConversationJudge(
                judge_provider,
                extra_instructions=judge_config.extra_instructions,
            )
            orchestrator = ConversationOrchestrator(agent, synthetic_user, judge)

            conversation_result, judgment_result = await orchestrator.run(scenario)

            # Capture agent configuration before closing
            system_prompt = agent.get_system_prompt()
            agent_model = agent.get_model_name()
            tool_schemas = await _extract_tool_schemas(file_config, agent)
        except Exception as e:
            logger.exception("Error running scenario")
            return f"Error: {e}"
        finally:
            if "agent" in locals():
                try:
                    await agent.close()
                except Exception as e:
                    logger.warning("Failed to close agent: %s", e)

        # Build and save result
        run_result = _build_test_result(
            scenario=scenario,
            scenario_file=full_path,
            results=(conversation_result, judgment_result),
            models=(judge_config.model, synthetic_user_config.model, agent_model),
            agent_info=(agent_config.type, system_prompt, tool_schemas),
        )

        if save_results:
            try:
                storage.save(run_result)
            except Exception as e:
                logger.warning("Failed to save results: %s", e)

        judgment = _format_judgment(run_result)
        suggestions = _format_suggestions(run_result)
        return f"{judgment}\n\n---\n\n{suggestions}"

    async def _execute_scenario(
        scenario_path: str,
        save: bool,
    ) -> ScenarioRunResult:
        """Execute a single scenario and return structured result."""
        from mcprobe.judge.judge import ConversationJudge  # noqa: PLC0415
        from mcprobe.orchestrator.orchestrator import (  # noqa: PLC0415
            ConversationOrchestrator,
        )
        from mcprobe.parser.scenario import ScenarioParser  # noqa: PLC0415
        from mcprobe.providers.factory import create_provider  # noqa: PLC0415
        from mcprobe.synthetic_user.user import SyntheticUserLLM  # noqa: PLC0415

        full_path = _resolve_scenario_path(scenario_path, scenarios_dir)
        if full_path is None:
            return ScenarioRunResult(scenario_path, False, "File not found")

        parser = ScenarioParser()
        try:
            scenario = parser.parse_file(full_path)
        except Exception as e:
            return ScenarioRunResult(scenario_path, False, f"Parse error: {e}")

        judge_config, synthetic_user_config, agent_config = _resolve_scenario_configs(
            file_config, scenario  # type: ignore[arg-type]
        )

        agent = None
        try:
            judge_provider = create_provider(judge_config)
            synthetic_user_provider = create_provider(synthetic_user_config)
            agent_or_error = _create_agent_from_config(
                agent_config, synthetic_user_provider
            )
            if isinstance(agent_or_error, str):
                return ScenarioRunResult(scenario_path, False, agent_or_error)
            agent = agent_or_error

            synthetic_user = SyntheticUserLLM(
                synthetic_user_provider,
                scenario.synthetic_user,
                extra_instructions=synthetic_user_config.extra_instructions,
            )
            judge = ConversationJudge(
                judge_provider,
                extra_instructions=judge_config.extra_instructions,
            )
            orchestrator = ConversationOrchestrator(agent, synthetic_user, judge)

            conversation_result, judgment_result = await orchestrator.run(scenario)

            system_prompt = agent.get_system_prompt()
            agent_model = agent.get_model_name()
            tool_schemas = await _extract_tool_schemas(file_config, agent)  # type: ignore[arg-type]
        except Exception as e:
            logger.exception("Error running scenario %s", scenario_path)
            return ScenarioRunResult(scenario_path, False, f"Error: {e}")
        finally:
            if agent is not None:
                try:
                    await agent.close()
                except Exception as e:
                    logger.warning("Failed to close agent: %s", e)

        run_result = _build_test_result(
            scenario=scenario,
            scenario_file=full_path,
            results=(conversation_result, judgment_result),
            models=(judge_config.model, synthetic_user_config.model, agent_model),
            agent_info=(agent_config.type, system_prompt, tool_schemas),
        )

        if save:
            try:
                storage.save(run_result)
            except Exception as e:
                logger.warning("Failed to save results: %s", e)

        passed = judgment_result.passed
        score = judgment_result.score
        msg = f"{'PASSED' if passed else 'FAILED'} (score: {score:.2f})"
        return ScenarioRunResult(scenario_path, passed, msg, score, run_result)

    @mcp.tool()
    async def run_scenarios(
        scenario_paths: list[str],
        save_results: bool = True,
    ) -> str:
        """Run multiple test scenarios and return aggregated results.

        Executes multiple test scenarios sequentially, providing a summary
        of pass/fail status for each. More efficient than calling run_scenario
        repeatedly when you need to test multiple scenarios.

        Args:
            scenario_paths: List of paths to scenario YAML files (relative to scenarios dir)
            save_results: Whether to save results to the results directory (default: True)

        Returns:
            Aggregated summary with pass/fail counts and per-scenario results.
        """
        if not file_config:
            return (
                "Error: Cannot run scenarios without configuration. "
                "Start the server with --config option pointing to mcprobe.yaml"
            )

        if not scenario_paths:
            return "Error: No scenario paths provided"

        results: list[ScenarioRunResult] = []
        for scenario_path in scenario_paths:
            result = await _execute_scenario(scenario_path, save_results)
            results.append(result)

        # Format summary
        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count
        total = len(results)

        lines = [
            "## Test Run Summary",
            f"**{passed_count}/{total} passed** ({failed_count} failed)",
            "",
            "### Results",
        ]

        for r in results:
            icon = "✓" if r.passed else "✗"
            lines.append(f"- {icon} `{r.path}`: {r.message}")

        return "\n".join(lines)

    @mcp.tool()
    async def generate_report(
        output_path: str | None = None,
        report_format: str = "html",
        title: str = "MCProbe Test Report",
        limit: int = 100,
    ) -> str:
        """Generate a report from stored test results.

        Creates an HTML, JSON, or JUnit report from the test results
        in the results directory.

        Args:
            output_path: Output file path (default: report.html in results dir)
            report_format: Format: 'html', 'json', or 'junit' (default: html)
            title: Title for the report (default: 'MCProbe Test Report')
            limit: Maximum number of results to include (default: 100)

        Returns:
            Path to the generated report file.
        """
        from mcprobe.reporting import (  # noqa: PLC0415
            HtmlReportGenerator,
            JsonReportGenerator,
            JunitReportGenerator,
        )

        results = loader.load_all(limit=limit)

        if not results:
            return "No test results found to generate report."

        # Determine output path
        if output_path:
            output = Path(output_path)
        else:
            ext = {"html": ".html", "json": ".json", "junit": ".xml"}.get(
                report_format, ".html"
            )
            output = results_dir / f"report{ext}"

        # Generate report based on format
        if report_format == "html":
            html_gen = HtmlReportGenerator()
            html_gen.generate(results, output, title=title)
        elif report_format == "json":
            json_gen = JsonReportGenerator()
            json_gen.generate(results, output)
        elif report_format == "junit":
            junit_gen = JunitReportGenerator()
            junit_gen.generate(results, output, suite_name=title)
        else:
            return f"Error: Unknown format '{report_format}'. Valid: html, json, junit"

        return f"Report generated: {output.absolute()}\n\nIncluded {len(results)} test result(s)."

    return mcp


def run_server(
    results_dir: Path,
    scenarios_dir: Path,
    config_file: Path | None = None,
) -> None:
    """Run the MCP server with stdio transport.

    Args:
        results_dir: Directory containing test results.
        scenarios_dir: Directory containing test scenarios.
        config_file: Optional path to mcprobe.yaml configuration file.
    """
    mcp = create_server(results_dir, scenarios_dir, config_file)
    mcp.run(transport="stdio")
