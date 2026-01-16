"""MCProbe CLI implementation.

Provides the command-line interface for running MCP server tests.
"""

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from mcprobe.agents.simple import SimpleLLMAgent
from mcprobe.exceptions import MCProbeError
from mcprobe.judge.judge import ConversationJudge
from mcprobe.models.config import LLMConfig
from mcprobe.models.conversation import ConversationResult
from mcprobe.models.judgment import JudgmentResult
from mcprobe.orchestrator.orchestrator import ConversationOrchestrator
from mcprobe.parser.scenario import ScenarioParser
from mcprobe.providers.factory import ProviderRegistry, create_provider
from mcprobe.synthetic_user.user import SyntheticUserLLM

app = typer.Typer(
    name="mcprobe",
    help="Conversational MCP server testing framework.",
    no_args_is_help=True,
)

console = Console()


@app.command()
def run(
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
            "--model", "-m",
            help="Model name for all LLM components.",
        ),
    ] = "llama3.2",
    base_url: Annotated[
        str,
        typer.Option(
            "--base-url", "-u",
            help="Base URL for Ollama API.",
        ),
    ] = "http://localhost:11434",
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose", "-v",
            help="Enable verbose output.",
        ),
    ] = False,
) -> None:
    """Run test scenarios against the agent.

    Executes one or more test scenarios, using a synthetic user to converse
    with the agent and a judge to evaluate the results.
    """
    try:
        asyncio.run(_run_scenarios(scenario_path, model, base_url, verbose))
    except MCProbeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e


async def _run_scenarios(
    scenario_path: Path,
    model: str,
    base_url: str,
    verbose: bool,
) -> None:
    """Run scenarios asynchronously.

    Args:
        scenario_path: Path to scenario file or directory.
        model: Model name for LLM components.
        base_url: Base URL for Ollama API.
        verbose: Enable verbose output.
    """
    # Parse scenarios
    parser = ScenarioParser()
    scenarios = (
        parser.parse_directory(scenario_path)
        if scenario_path.is_dir()
        else [parser.parse_file(scenario_path)]
    )

    if not scenarios:
        console.print("[yellow]No scenarios found.[/yellow]")
        return

    console.print(f"[blue]Found {len(scenarios)} scenario(s)[/blue]\n")

    # Create LLM config
    llm_config = LLMConfig(provider="ollama", model=model, base_url=base_url)

    # Create provider for all components
    provider = create_provider(llm_config)

    # Track results
    results: list[tuple[str, bool, float]] = []

    for scenario in scenarios:
        console.print(Panel(f"[bold]{scenario.name}[/bold]\n{scenario.description}"))

        # Create components for this scenario
        agent = SimpleLLMAgent(provider)
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
        status = "[green]PASSED[/green]" if judgment_result.passed else "[red]FAILED[/red]"

        console.print(f"\nResult: {status} (score: {judgment_result.score:.2f})")
        console.print(f"Reasoning: {judgment_result.reasoning}")

        if verbose:
            _display_verbose_results(conversation_result, judgment_result)

        if judgment_result.suggestions:
            console.print("\n[yellow]Suggestions:[/yellow]")
            for suggestion in judgment_result.suggestions:
                console.print(f"  - {suggestion}")

        results.append((scenario.name, judgment_result.passed, judgment_result.score))
        console.print()

    # Summary
    _display_summary(results)


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
