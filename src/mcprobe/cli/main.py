"""MCProbe CLI implementation.

Provides the command-line interface for running MCP server tests.
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from mcprobe.agents.base import AgentUnderTest
from mcprobe.agents.simple import SimpleLLMAgent
from mcprobe.exceptions import MCProbeError
from mcprobe.judge.judge import ConversationJudge
from mcprobe.models.config import LLMConfig
from mcprobe.models.conversation import ConversationResult
from mcprobe.models.judgment import JudgmentResult
from mcprobe.orchestrator.orchestrator import ConversationOrchestrator
from mcprobe.parser.scenario import ScenarioParser
from mcprobe.providers.base import LLMProvider
from mcprobe.providers.factory import ProviderRegistry, create_provider
from mcprobe.synthetic_user.user import SyntheticUserLLM

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
    model: str
    base_url: str
    agent_type: str
    agent_factory: Path | None
    verbose: bool


@dataclass
class AgentConfig:
    """Configuration for agent creation."""

    agent_type: str
    agent_factory: Path | None


@app.command()
def run(  # noqa: PLR0913 - Typer requires CLI args as function parameters
    scenario_path: Annotated[
        Path,
        typer.Argument(
            help="Path to scenario YAML file or directory.",
            exists=True,
        ),
    ],
    model: Annotated[
        str,
        typer.Option(
            "--model",
            "-m",
            help="Model name for LLM components (synthetic user and judge).",
        ),
    ] = "llama3.2",
    base_url: Annotated[
        str,
        typer.Option(
            "--base-url",
            "-u",
            help="Base URL for Ollama API.",
        ),
    ] = "http://localhost:11434",
    agent_type: Annotated[
        str,
        typer.Option(
            "--agent-type",
            "-t",
            help="Agent type: 'simple' (Ollama LLM) or 'adk' (Gemini ADK with MCP).",
        ),
    ] = "simple",
    agent_factory: Annotated[
        Path | None,
        typer.Option(
            "--agent-factory",
            "-f",
            help="Path to Python module with create_agent() function (required for 'adk' type).",
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
    """
    # Validate agent configuration
    if agent_type == "adk" and agent_factory is None:
        console.print("[red]Error:[/red] --agent-factory is required for ADK agent type")
        raise typer.Exit(code=1)

    if agent_type not in ("simple", "adk"):
        console.print(f"[red]Error:[/red] Unknown agent type: {agent_type}")
        raise typer.Exit(code=1)

    config = RunConfig(
        scenario_path=scenario_path,
        model=model,
        base_url=base_url,
        agent_type=agent_type,
        agent_factory=agent_factory,
        verbose=verbose,
    )

    try:
        asyncio.run(_run_scenarios(config))
    except MCProbeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e


def _create_agent(agent_config: AgentConfig, provider: LLMProvider) -> AgentUnderTest:
    """Create the agent under test based on configuration.

    Args:
        agent_config: Agent configuration.
        provider: LLM provider for simple agents.

    Returns:
        Configured agent instance.
    """
    if agent_config.agent_type == "adk":
        from mcprobe.agents.adk import (  # noqa: PLC0415
            GeminiADKAgent,
            load_agent_factory,
        )

        if agent_config.agent_factory is None:
            msg = "--agent-factory is required for ADK agent type"
            raise MCProbeError(msg)

        factory = load_agent_factory(str(agent_config.agent_factory))
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

    console.print(f"[blue]Found {len(scenarios)} scenario(s)[/blue]")
    console.print(f"[blue]Agent type: {config.agent_type}[/blue]\n")

    # Create LLM config for synthetic user and judge
    llm_config = LLMConfig(provider="ollama", model=config.model, base_url=config.base_url)

    # Create provider for synthetic user and judge
    provider = create_provider(llm_config)

    # Create agent based on type
    agent_config = AgentConfig(
        agent_type=config.agent_type,
        agent_factory=config.agent_factory,
    )
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


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
