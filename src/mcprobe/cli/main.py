"""MCProbe CLI implementation.

Provides the command-line interface for running MCP server tests.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

if TYPE_CHECKING:
    from mcprobe.generator import ComplexityLevel

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from mcprobe.agents.base import AgentUnderTest
from mcprobe.agents.simple import SimpleLLMAgent
from mcprobe.config import AgentConfig, CLIOverrides, ConfigLoader, FileConfig
from mcprobe.exceptions import MCProbeError
from mcprobe.judge.judge import ConversationJudge
from mcprobe.models.conversation import ConversationResult
from mcprobe.models.judgment import JudgmentResult
from mcprobe.orchestrator.orchestrator import ConversationOrchestrator
from mcprobe.parser.scenario import ScenarioParser
from mcprobe.providers.base import LLMProvider
from mcprobe.providers.factory import ProviderRegistry, create_provider
from mcprobe.synthetic_user.user import SyntheticUserLLM

DEFAULT_RESULTS_DIR = "test-results"

# Pattern for relative time strings like "1h", "30m", "1d"
RELATIVE_TIME_PATTERN = re.compile(r"^(\d+)([hmd])$", re.IGNORECASE)


def _parse_since(since_str: str) -> datetime:
    """Parse a since string into a datetime.

    Args:
        since_str: Time specification - ISO format, date, or relative (1h, 30m, 1d).

    Returns:
        Parsed datetime in UTC.

    Raises:
        typer.BadParameter: If the format is invalid.
    """
    # Try relative format first (1h, 30m, 1d)
    match = RELATIVE_TIME_PATTERN.match(since_str.strip())
    if match:
        amount = int(match.group(1))
        unit = match.group(2).lower()
        now = datetime.now(UTC)
        if unit == "h":
            return now - timedelta(hours=amount)
        elif unit == "m":
            return now - timedelta(minutes=amount)
        elif unit == "d":
            return now - timedelta(days=amount)

    # Try ISO format with time
    try:
        # Try full ISO format
        dt = datetime.fromisoformat(since_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError:
        pass

    # Try date-only format
    try:
        dt = datetime.strptime(since_str, "%Y-%m-%d")
        return dt.replace(tzinfo=UTC)
    except ValueError:
        pass

    msg = (
        f"Invalid time format: '{since_str}'. "
        "Use ISO format (2026-01-18T13:00:00), date (2026-01-18), "
        "or relative (1h, 30m, 1d)."
    )
    raise typer.BadParameter(msg)


app = typer.Typer(
    name="mcprobe",
    help="Conversational MCP server testing framework.",
    no_args_is_help=True,
)

console = Console()


@dataclass
class RunConfig:
    """Configuration for a test run."""

    scenario_path: Path
    file_config: FileConfig | None
    provider: str | None
    model: str | None
    base_url: str | None
    cli_agent_type: str | None
    cli_agent_factory: Path | None
    verbose: bool


@app.command()
def run(  # noqa: PLR0913 - Typer requires CLI args as function parameters
    scenario_path: Annotated[
        Path,
        typer.Argument(
            help="Path to scenario YAML file or directory.",
            exists=True,
        ),
    ],
    config_file: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Path to mcprobe.yaml configuration file.",
        ),
    ] = None,
    provider: Annotated[
        str | None,
        typer.Option(
            "--provider",
            "-p",
            help="LLM provider (e.g., 'ollama', 'openai').",
        ),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            "-m",
            help="Model name for LLM components (synthetic user and judge).",
        ),
    ] = None,
    base_url: Annotated[
        str | None,
        typer.Option(
            "--base-url",
            "-u",
            help="Base URL for LLM API.",
        ),
    ] = None,
    agent_type: Annotated[
        str | None,
        typer.Option(
            "--agent-type",
            "-t",
            help="Agent type: 'simple' or 'adk'. Overrides config file.",
        ),
    ] = None,
    agent_factory: Annotated[
        Path | None,
        typer.Option(
            "--agent-factory",
            "-f",
            help="Path to Python module with create_agent() function. Overrides config file.",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose output.",
        ),
    ] = False,
) -> None:
    """Run test scenarios against the agent.

    Executes one or more test scenarios, using a synthetic user to converse
    with the agent and a judge to evaluate the results.

    For simple agents (default):
        mcprobe run scenario.yaml -u http://ollama:11434 -m llama3.2

    For ADK agents with MCP tools:
        mcprobe run scenario.yaml -t adk -f my_agent_factory.py

    With config file:
        mcprobe run scenario.yaml --config mcprobe.yaml
    """
    # Load configuration file if available
    try:
        file_config = ConfigLoader.load_config(config_file)
    except MCProbeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e

    # Resolve agent configuration (config file + CLI overrides)
    resolved_agent = ConfigLoader.resolve_agent_config(
        file_config,
        cli_agent_type=agent_type,
        cli_agent_factory=str(agent_factory) if agent_factory else None,
    )

    # Validate agent configuration
    if resolved_agent.type == "adk" and resolved_agent.factory is None:
        console.print("[red]Error:[/red] Agent factory is required for ADK agent type")
        console.print("Set 'agent.factory' in config file or use --agent-factory")
        raise typer.Exit(code=1)

    if resolved_agent.type not in ("simple", "adk"):
        console.print(f"[red]Error:[/red] Unknown agent type: {resolved_agent.type}")
        raise typer.Exit(code=1)

    run_config = RunConfig(
        scenario_path=scenario_path,
        file_config=file_config,
        provider=provider,
        model=model,
        base_url=base_url,
        cli_agent_type=agent_type,
        cli_agent_factory=agent_factory,
        verbose=verbose,
    )

    try:
        asyncio.run(_run_scenarios(run_config))
    except MCProbeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e


def _create_agent(agent_config: AgentConfig, provider: LLMProvider) -> AgentUnderTest:
    """Create the agent under test based on configuration.

    Args:
        agent_config: Agent configuration (from config file + CLI overrides).
        provider: LLM provider for simple agents.

    Returns:
        Configured agent instance.
    """
    if agent_config.type == "adk":
        from mcprobe.agents.adk import (  # noqa: PLC0415
            GeminiADKAgent,
            load_agent_factory,
        )

        if agent_config.factory is None:
            msg = "Agent factory is required for ADK agent type"
            raise MCProbeError(msg)

        factory = load_agent_factory(agent_config.factory)
        adk_agent = factory()
        return GeminiADKAgent(adk_agent)

    return SimpleLLMAgent(provider)


async def _run_scenarios(config: RunConfig) -> None:
    """Run scenarios asynchronously.

    Args:
        config: Run configuration.
    """
    # Parse scenarios
    parser = ScenarioParser()
    scenarios = (
        parser.parse_directory(config.scenario_path)
        if config.scenario_path.is_dir()
        else [parser.parse_file(config.scenario_path)]
    )

    if not scenarios:
        console.print("[yellow]No scenarios found.[/yellow]")
        return

    # Resolve agent configuration
    agent_config = ConfigLoader.resolve_agent_config(
        config.file_config,
        cli_agent_type=config.cli_agent_type,
        cli_agent_factory=str(config.cli_agent_factory) if config.cli_agent_factory else None,
    )

    console.print(f"[blue]Found {len(scenarios)} scenario(s)[/blue]")
    console.print(f"[blue]Agent type: {agent_config.type}[/blue]\n")

    # Resolve LLM config for synthetic user and judge (they share the same config)
    cli_overrides = CLIOverrides(
        provider=config.provider,
        model=config.model,
        base_url=config.base_url,
    )
    llm_config = ConfigLoader.resolve_llm_config(
        config.file_config,
        "synthetic_user",
        cli_overrides,
    )

    console.print(f"[blue]Provider: {llm_config.provider}, Model: {llm_config.model}[/blue]\n")

    # Create provider for synthetic user and judge
    provider = create_provider(llm_config)

    # Create agent based on type
    agent = _create_agent(agent_config, provider)

    # Track results
    results: list[tuple[str, bool, float]] = []

    for scenario in scenarios:
        console.print(Panel(f"[bold]{scenario.name}[/bold]\n{scenario.description}"))

        # Reset agent for new scenario
        await agent.reset()

        # Create components for this scenario
        synthetic_user = SyntheticUserLLM(provider, scenario.synthetic_user)
        judge = ConversationJudge(provider)
        orchestrator = ConversationOrchestrator(agent, synthetic_user, judge)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Running conversation...", total=None)

            # Run the scenario
            conversation_result, judgment_result = await orchestrator.run(scenario)

        # Display results
        _display_result(judgment_result, config.verbose, conversation_result)

        results.append((scenario.name, judgment_result.passed, judgment_result.score))
        console.print()

    # Summary
    _display_summary(results)


def _display_result(
    judgment_result: JudgmentResult,
    verbose: bool,
    conversation_result: ConversationResult,
) -> None:
    """Display the result of a single scenario run.

    Args:
        judgment_result: The judgment result.
        verbose: Whether to show verbose output.
        conversation_result: The conversation result.
    """
    status = "[green]PASSED[/green]" if judgment_result.passed else "[red]FAILED[/red]"

    console.print(f"\nResult: {status} (score: {judgment_result.score:.2f})")
    console.print(f"Reasoning: {judgment_result.reasoning}")

    if verbose:
        _display_verbose_results(conversation_result, judgment_result)

    if judgment_result.suggestions:
        console.print("\n[yellow]Suggestions:[/yellow]")
        for suggestion in judgment_result.suggestions:
            console.print(f"  - {suggestion}")


def _display_verbose_results(
    conversation_result: ConversationResult,
    judgment_result: JudgmentResult,
) -> None:
    """Display verbose conversation and judgment details.

    Args:
        conversation_result: The conversation result.
        judgment_result: The judgment result.
    """
    console.print("\n[bold]Conversation:[/bold]")
    for turn in conversation_result.turns:
        role = turn.role.upper()
        console.print(f"[{role}]: {turn.content}")
        for tc in turn.tool_calls:
            console.print(f"  -> {tc.tool_name}({tc.parameters})")

    console.print("\n[bold]Correctness:[/bold]")
    for criterion, passed in judgment_result.correctness_results.items():
        status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
        console.print(f"  {criterion}: {status}")

    console.print("\n[bold]Failure Conditions:[/bold]")
    for criterion, triggered in judgment_result.failure_results.items():
        status = "[red]TRIGGERED[/red]" if triggered else "[green]OK[/green]"
        console.print(f"  {criterion}: {status}")

    console.print("\n[bold]Quality Metrics:[/bold]")
    qm = judgment_result.quality_metrics
    console.print(f"  Clarifications: {qm.clarification_count}")
    console.print(f"  Backtracks: {qm.backtrack_count}")
    console.print(f"  Turns to first answer: {qm.turns_to_first_answer}")
    console.print(f"  Answer completeness: {qm.final_answer_completeness:.0%}")

    console.print("\n[bold]Efficiency:[/bold]")
    eff = judgment_result.efficiency_results
    console.print(f"  Total tokens: {eff.get('total_tokens', 0)}")
    console.print(f"  Tool calls: {eff.get('total_tool_calls', 0)}")
    console.print(f"  Turns: {eff.get('total_turns', 0)}")

    if judgment_result.structured_suggestions:
        console.print("\n[bold]MCP Improvement Suggestions:[/bold]")
        for s in judgment_result.structured_suggestions:
            severity_color = {"low": "blue", "medium": "yellow", "high": "red"}.get(
                s.severity.value, "white"
            )
            console.print(
                f"  [{severity_color}][{s.severity.value}][/{severity_color}] "
                f"{s.category.value}: {s.tool_name or 'general'}"
            )
            console.print(f"    Issue: {s.issue}")
            console.print(f"    Suggestion: {s.suggestion}")


def _display_summary(results: list[tuple[str, bool, float]]) -> None:
    """Display summary of all scenario results.

    Args:
        results: List of (name, passed, score) tuples.
    """
    table = Table(title="Test Summary")
    table.add_column("Scenario", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Score", justify="right")

    passed_count = 0
    for name, passed, score in results:
        status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
        table.add_row(name, status, f"{score:.2f}")
        if passed:
            passed_count += 1

    console.print(table)
    console.print(f"\n[bold]Total: {passed_count}/{len(results)} passed[/bold]")


@app.command()
def validate(
    scenario_path: Annotated[
        Path,
        typer.Argument(
            help="Path to scenario YAML file or directory.",
            exists=True,
        ),
    ],
) -> None:
    """Validate scenario YAML files without running them.

    Checks that scenario files are properly formatted and contain
    all required fields.
    """
    parser = ScenarioParser()

    try:
        scenarios = (
            parser.parse_directory(scenario_path)
            if scenario_path.is_dir()
            else [parser.parse_file(scenario_path)]
        )

        console.print(f"[green]Validated {len(scenarios)} scenario(s) successfully.[/green]")
        for scenario in scenarios:
            console.print(f"  - {scenario.name}")

    except MCProbeError as e:
        console.print(f"[red]Validation failed:[/red] {e}")
        raise typer.Exit(code=1) from e


@app.command()
def providers() -> None:
    """List available LLM providers."""
    available = ProviderRegistry.list_providers()

    table = Table(title="Available Providers")
    table.add_column("Provider", style="cyan")

    for provider_name in sorted(available):
        table.add_row(provider_name)

    console.print(table)


@app.command(name="generate-scenarios")
def generate_scenarios(  # noqa: PLR0913 - Typer requires CLI args as function parameters
    server: Annotated[
        str,
        typer.Option(
            "--server",
            "-s",
            help="MCP server command (e.g., 'npx @example/weather-mcp').",
        ),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output directory for generated scenarios.",
        ),
    ] = Path("./generated-scenarios"),
    complexity: Annotated[
        str,
        typer.Option(
            "--complexity",
            help="Complexity level: simple, medium, or complex.",
        ),
    ] = "medium",
    count: Annotated[
        int,
        typer.Option(
            "--count",
            "-n",
            help="Number of scenarios to generate.",
        ),
    ] = 10,
    config_file: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Path to mcprobe.yaml configuration file.",
        ),
    ] = None,
    provider: Annotated[
        str | None,
        typer.Option(
            "--provider",
            "-p",
            help="LLM provider (e.g., 'ollama', 'openai').",
        ),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            "-m",
            help="Model for generation.",
        ),
    ] = None,
    base_url: Annotated[
        str | None,
        typer.Option(
            "--base-url",
            "-u",
            help="Base URL for LLM API.",
        ),
    ] = None,
) -> None:
    """Generate test scenarios from MCP tool schemas.

    Connects to an MCP server, extracts tool schemas, and generates
    test scenarios based on the specified complexity level.

    Example:
        mcprobe generate-scenarios --server "npx @example/weather-mcp" -o ./scenarios
    """
    from mcprobe.generator import ComplexityLevel  # noqa: PLC0415

    # Load configuration file if available
    try:
        file_config = ConfigLoader.load_config(config_file)
    except MCProbeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e

    # Validate complexity level
    try:
        complexity_level = ComplexityLevel(complexity.lower())
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid complexity level: {complexity}")
        console.print("Valid options: simple, medium, complex")
        raise typer.Exit(code=1) from None

    try:
        asyncio.run(
            _generate_scenarios_async(
                server=server,
                output=output,
                complexity=complexity_level,
                count=count,
                file_config=file_config,
                cli_provider=provider,
                cli_model=model,
                cli_base_url=base_url,
            )
        )
    except MCProbeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e


async def _generate_scenarios_async(  # noqa: PLR0913 - CLI helper needs multiple args
    server: str,
    output: Path,
    complexity: ComplexityLevel,
    count: int,
    file_config: FileConfig | None,
    cli_provider: str | None,
    cli_model: str | None,
    cli_base_url: str | None,
) -> None:
    """Generate scenarios asynchronously.

    Args:
        server: MCP server command.
        output: Output directory path.
        complexity: Complexity level.
        count: Number of scenarios to generate.
        file_config: Loaded configuration file, or None.
        cli_provider: CLI provider override.
        cli_model: CLI model override.
        cli_base_url: CLI base URL override.
    """
    import yaml  # noqa: PLC0415

    from mcprobe.generator import ScenarioGenerator, extract_tools_from_server  # noqa: PLC0415

    console.print(f"[blue]Connecting to MCP server: {server}[/blue]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Extracting tool schemas...", total=None)

        try:
            tools = await extract_tools_from_server(server)
        except Exception as e:
            console.print(f"[red]Error connecting to server:[/red] {e}")
            raise typer.Exit(code=1) from e

        progress.update(task, description=f"Found {len(tools.tools)} tools")

    console.print(f"[green]Found {len(tools.tools)} tool(s):[/green]")
    for tool in tools.tools:
        console.print(f"  - {tool.name}: {tool.description or 'No description'}")

    # Resolve LLM config
    cli_overrides = CLIOverrides(
        provider=cli_provider,
        model=cli_model,
        base_url=cli_base_url,
    )
    llm_config = ConfigLoader.resolve_llm_config(file_config, "llm", cli_overrides)
    console.print(f"[blue]Provider: {llm_config.provider}, Model: {llm_config.model}[/blue]")

    provider = create_provider(llm_config)

    # Generate scenarios
    console.print(
        f"\n[blue]Generating {count} scenario(s) at {complexity.value} complexity...[/blue]"
    )

    generator = ScenarioGenerator(provider)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Generating scenarios...", total=None)
        scenarios = await generator.generate(tools, complexity, count)

    console.print(f"[green]Generated {len(scenarios)} scenario(s)[/green]")

    # Write to output directory
    output.mkdir(parents=True, exist_ok=True)

    for scenario in scenarios:
        # Create safe filename
        safe_name = scenario.name.lower().replace(" ", "_").replace("/", "_")
        filename = f"{safe_name}.yaml"
        filepath = output / filename

        scenario_dict = scenario.model_dump(mode="json")
        filepath.write_text(yaml.dump(scenario_dict, default_flow_style=False, sort_keys=False))
        console.print(f"  [dim]Created:[/dim] {filepath}")

    console.print(f"\n[green]Scenarios written to {output}[/green]")


@app.command()
def report(  # noqa: PLR0913 - Typer requires CLI args as function parameters
    results_dir: Annotated[
        Path,
        typer.Option(
            "--results-dir",
            "-d",
            help="Directory containing test results.",
        ),
    ] = Path(DEFAULT_RESULTS_DIR),
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output file path for the report.",
        ),
    ] = Path("report.html"),
    report_format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Report format: html, json, or junit.",
        ),
    ] = "html",
    title: Annotated[
        str,
        typer.Option(
            "--title",
            "-t",
            help="Title for the report.",
        ),
    ] = "MCProbe Test Report",
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-n",
            help="Maximum number of results to include.",
        ),
    ] = 100,
    since: Annotated[
        str | None,
        typer.Option(
            "--since",
            "-s",
            help=(
                "Include only results after this time. "
                "Accepts ISO format (2026-01-18T13:00:00), date (2026-01-18), "
                "or relative (1h, 30m, 1d for hours/minutes/days ago)."
            ),
        ),
    ] = None,
) -> None:
    """Generate a report from stored test results.

    Reads test results from the results directory and generates
    a report in the specified format.

    Example:
        mcprobe report --format html --output report.html
        mcprobe report --since 1h  # Results from last hour
        mcprobe report --since 2026-01-18  # Results from specific date
    """
    from mcprobe.persistence import ResultLoader  # noqa: PLC0415
    from mcprobe.reporting import (  # noqa: PLC0415
        HtmlReportGenerator,
        JsonReportGenerator,
        JunitReportGenerator,
    )

    if not results_dir.exists():
        console.print(f"[red]Error:[/red] Results directory not found: {results_dir}")
        raise typer.Exit(code=1)

    loader = ResultLoader(results_dir)

    # Parse since option if provided
    since_dt = _parse_since(since) if since else None

    results = loader.load_all(limit=limit, since=since_dt)

    if not results:
        if since_dt:
            console.print(f"[yellow]No test results found since {since_dt.isoformat()}.[/yellow]")
        else:
            console.print("[yellow]No test results found.[/yellow]")
        raise typer.Exit(code=0)

    since_msg = f" since {since_dt.isoformat()}" if since_dt else ""
    console.print(f"[blue]Found {len(results)} test result(s){since_msg}[/blue]")

    # Generate report based on format
    if report_format == "html":
        html_generator = HtmlReportGenerator()
        html_generator.generate(results, output, title=title)
    elif report_format == "json":
        json_generator = JsonReportGenerator()
        json_generator.generate(results, output)
    elif report_format == "junit":
        junit_generator = JunitReportGenerator()
        junit_generator.generate(results, output, suite_name=title)
    else:
        console.print(f"[red]Error:[/red] Unknown format: {report_format}")
        console.print("Valid options: html, json, junit")
        raise typer.Exit(code=1)

    console.print(f"[green]Report generated: {output}[/green]")


@app.command()
def trends(
    scenario: Annotated[
        str | None,
        typer.Option(
            "--scenario",
            "-s",
            help="Scenario name to analyze (all if not specified).",
        ),
    ] = None,
    window: Annotated[
        int,
        typer.Option(
            "--window",
            "-w",
            help="Number of recent runs to consider.",
        ),
    ] = 10,
    results_dir: Annotated[
        Path,
        typer.Option(
            "--results-dir",
            "-d",
            help="Directory containing test results.",
        ),
    ] = Path(DEFAULT_RESULTS_DIR),
) -> None:
    """Show trend analysis for test scenarios.

    Analyzes historical test results to detect trends in pass rates
    and scores over time.

    Example:
        mcprobe trends --scenario "my-test" --window 20
    """
    from mcprobe.analysis import TrendAnalyzer, TrendDirection  # noqa: PLC0415
    from mcprobe.persistence import ResultLoader  # noqa: PLC0415

    if not results_dir.exists():
        console.print(f"[red]Error:[/red] Results directory not found: {results_dir}")
        raise typer.Exit(code=1)

    loader = ResultLoader(results_dir)
    analyzer = TrendAnalyzer(loader)

    if scenario:
        # Analyze single scenario
        trends_result = analyzer.analyze_scenario(scenario, window)
        if trends_result is None:
            console.print(f"[yellow]Insufficient data for scenario: {scenario}[/yellow]")
            raise typer.Exit(code=0)
        all_trends = [trends_result]
    else:
        # Analyze all scenarios
        all_trends = analyzer.analyze_all(window)

    if not all_trends:
        console.print("[yellow]No trend data available.[/yellow]")
        raise typer.Exit(code=0)

    # Display trends table
    table = Table(title="Trend Analysis")
    table.add_column("Scenario", style="cyan")
    table.add_column("Runs", justify="right")
    table.add_column("Pass Rate", justify="right")
    table.add_column("Pass Trend", justify="center")
    table.add_column("Avg Score", justify="right")
    table.add_column("Score Trend", justify="center")

    for t in all_trends:
        pass_trend_style = {
            TrendDirection.IMPROVING: "[green]↑[/green]",
            TrendDirection.DEGRADING: "[red]↓[/red]",
            TrendDirection.STABLE: "[dim]→[/dim]",
        }
        score_trend_style = pass_trend_style

        table.add_row(
            t.scenario_name,
            str(t.run_count),
            f"{t.pass_rate:.0%}",
            pass_trend_style[t.pass_trend],
            f"{t.avg_score:.2f}",
            score_trend_style[t.score_trend],
        )

    console.print(table)

    # Check for regressions
    regressions = analyzer.detect_regressions()
    if regressions:
        console.print("\n[yellow]⚠ Detected Regressions:[/yellow]")
        for r in regressions:
            severity_color = {"low": "blue", "medium": "yellow", "high": "red"}.get(
                r.severity, "white"
            )
            console.print(
                f"  [{severity_color}][{r.severity}][/{severity_color}] "
                f"{r.scenario_name}: {r.metric} dropped "
                f"{r.change_percent:.1f}%"
            )


@app.command()
def flaky(
    min_runs: Annotated[
        int,
        typer.Option(
            "--min-runs",
            "-n",
            help="Minimum runs required for analysis.",
        ),
    ] = 5,
    results_dir: Annotated[
        Path,
        typer.Option(
            "--results-dir",
            "-d",
            help="Directory containing test results.",
        ),
    ] = Path(DEFAULT_RESULTS_DIR),
    fail_on_flaky: Annotated[
        bool,
        typer.Option(
            "--fail-on-flaky",
            help="Exit with error code if flaky tests are detected.",
        ),
    ] = False,
) -> None:
    """Detect flaky (inconsistent) test scenarios.

    Identifies scenarios with inconsistent pass/fail results or
    high score variance.

    Example:
        mcprobe flaky --min-runs 10 --fail-on-flaky
    """
    from mcprobe.analysis import FlakyDetector  # noqa: PLC0415
    from mcprobe.persistence import ResultLoader  # noqa: PLC0415

    if not results_dir.exists():
        console.print(f"[red]Error:[/red] Results directory not found: {results_dir}")
        raise typer.Exit(code=1)

    loader = ResultLoader(results_dir)
    detector = FlakyDetector(loader)

    flaky_scenarios = detector.detect_flaky_scenarios(min_runs=min_runs)

    if not flaky_scenarios:
        console.print("[green]No flaky scenarios detected.[/green]")
        raise typer.Exit(code=0)

    # Display flaky scenarios
    table = Table(title="Flaky Scenarios")
    table.add_column("Scenario", style="cyan")
    table.add_column("Pass Rate", justify="right")
    table.add_column("Runs", justify="right")
    table.add_column("Severity", justify="center")
    table.add_column("Reason")

    for f in flaky_scenarios:
        severity_color = {"low": "blue", "medium": "yellow", "high": "red"}.get(
            f.severity, "white"
        )
        table.add_row(
            f.scenario_name,
            f"{f.pass_rate:.0%}",
            str(f.run_count),
            f"[{severity_color}]{f.severity}[/{severity_color}]",
            f.reason,
        )

    console.print(table)
    console.print(f"\n[yellow]Found {len(flaky_scenarios)} flaky scenario(s)[/yellow]")

    if fail_on_flaky:
        raise typer.Exit(code=1)


@app.command(name="stability-check")
def stability_check(
    scenario: Annotated[
        str,
        typer.Argument(help="Scenario name to check."),
    ],
    min_runs: Annotated[
        int,
        typer.Option(
            "--min-runs",
            "-n",
            help="Minimum runs required for analysis.",
        ),
    ] = 5,
    results_dir: Annotated[
        Path,
        typer.Option(
            "--results-dir",
            "-d",
            help="Directory containing test results.",
        ),
    ] = Path(DEFAULT_RESULTS_DIR),
) -> None:
    """Check stability of a specific scenario.

    Returns detailed stability metrics for the specified scenario.

    Example:
        mcprobe stability-check "my-test-scenario"
    """
    from mcprobe.analysis import FlakyDetector  # noqa: PLC0415
    from mcprobe.persistence import ResultLoader  # noqa: PLC0415

    if not results_dir.exists():
        console.print(f"[red]Error:[/red] Results directory not found: {results_dir}")
        raise typer.Exit(code=1)

    loader = ResultLoader(results_dir)
    detector = FlakyDetector(loader)

    result = detector.stability_check(scenario, min_runs=min_runs)

    console.print(Panel(f"[bold]Stability Check: {scenario}[/bold]"))

    if result["is_stable"] is None:
        console.print(f"[yellow]{result['reason']}[/yellow]")
        console.print(f"Run count: {result['run_count']} (need at least {min_runs})")
        raise typer.Exit(code=0)

    # Display metrics
    table = Table(show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Run Count", str(result["run_count"]))
    table.add_row("Pass Rate", f"{result['pass_rate']:.0%}")
    table.add_row("Mean Score", f"{result['mean_score']:.2f}")
    table.add_row("Score Std Dev", f"{result['score_std']:.3f}")

    console.print(table)

    # Display stability status
    if result["is_stable"]:
        console.print("\n[green]✓ Scenario is stable[/green]")
    else:
        console.print("\n[red]✗ Scenario is unstable[/red]")
        reasons = result["reasons"]
        if isinstance(reasons, list):
            for reason in reasons:
                console.print(f"  - {reason}")


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
