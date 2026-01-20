"""HTML report generator for MCProbe test results.

Generates beautiful, self-contained HTML reports from test run results.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcprobe.persistence import TestRunResult


def _get_template() -> str:
    """Load the HTML template."""
    template_file = files("mcprobe.reporting.templates").joinpath("report.html")
    return template_file.read_text()


def _get_styles() -> str:
    """Load the CSS styles."""
    styles_file = files("mcprobe.reporting.templates").joinpath("styles.css")
    return styles_file.read_text()


MAX_DESCRIPTION_LENGTH = 80


class HtmlReportGenerator:
    """Generates HTML reports from test results."""

    def __init__(self) -> None:
        """Initialize the generator."""
        self._template: str | None = None
        self._styles: str | None = None

    def _load_template(self) -> str:
        """Load the HTML template lazily."""
        if self._template is None:
            self._template = _get_template()
        return self._template

    def _load_styles(self) -> str:
        """Load the CSS styles lazily."""
        if self._styles is None:
            self._styles = _get_styles()
        return self._styles

    def generate(
        self,
        results: list[TestRunResult],
        output_path: Path,
        title: str = "MCProbe Test Report",
    ) -> None:
        """Generate an HTML report from test results.

        Args:
            results: List of test run results.
            output_path: Path to write the HTML report.
            title: Report title.
        """
        # Calculate summary statistics
        total = len(results)
        passed = sum(1 for r in results if r.judgment_result.passed)
        failed = total - passed
        pass_rate = (passed / total * 100) if total > 0 else 0
        avg_score = sum(r.judgment_result.score for r in results) / total if total > 0 else 0
        total_duration = sum(r.duration_seconds for r in results)

        # Generate HTML
        html = self._generate_html(
            title=title,
            results=results,
            total=total,
            passed=passed,
            failed=failed,
            pass_rate=pass_rate,
            avg_score=avg_score,
            total_duration=total_duration,
            generated_at=datetime.now(),
        )

        output_path.write_text(html)

    def _group_by_run(
        self, results: list[TestRunResult]
    ) -> dict[str, list[TestRunResult]]:
        """Group results by run_id, preserving order."""
        groups: dict[str, list[TestRunResult]] = defaultdict(list)
        for result in results:
            groups[result.run_id].append(result)
        return dict(groups)

    def _generate_html(  # noqa: PLR0913
        self,
        title: str,
        results: list[TestRunResult],
        total: int,
        passed: int,
        failed: int,
        pass_rate: float,
        avg_score: float,
        total_duration: float,
        generated_at: datetime,
    ) -> str:
        """Generate the HTML content.

        Uses string formatting instead of Jinja2 for simplicity and to avoid
        requiring the optional dependency for basic reports.
        """
        styles = self._load_styles()

        # Group results by test run
        runs = self._group_by_run(results)
        num_runs = len(runs)

        # Build test run sections
        runs_html = self._build_runs_html(runs)

        # Build the full HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{_escape_html(title)}</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/github.min.css">
    <script src="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/highlight.min.js"></script>
    <script src="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/languages/json.min.js"></script>
    <style>
{styles}
    </style>
</head>
<body>
    <header>
        <h1>{_escape_html(title)}</h1>
        <p class="generated-at">Generated: {generated_at.strftime("%Y-%m-%d %H:%M:%S")}</p>
    </header>

    <section class="summary">
        <h2>Summary</h2>
        <div class="summary-cards">
            <div class="card">
                <div class="card-value">{num_runs}</div>
                <div class="card-label">Test Runs</div>
            </div>
            <div class="card">
                <div class="card-value">{total}</div>
                <div class="card-label">Total Tests</div>
            </div>
            <div class="card pass">
                <div class="card-value">{passed}</div>
                <div class="card-label">Passed</div>
            </div>
            <div class="card fail">
                <div class="card-value">{failed}</div>
                <div class="card-label">Failed</div>
            </div>
            <div class="card">
                <div class="card-value">{pass_rate:.1f}%</div>
                <div class="card-label">Pass Rate</div>
            </div>
            <div class="card">
                <div class="card-value">{avg_score:.2f}</div>
                <div class="card-label">Avg Score</div>
            </div>
            <div class="card">
                <div class="card-value">{total_duration:.1f}s</div>
                <div class="card-label">Duration</div>
            </div>
        </div>
    </section>

    <section class="scenarios">
        <h2>Test Results</h2>
        <div class="filters">
            <button class="filter-btn active" data-filter="all">All ({total})</button>
            <button class="filter-btn" data-filter="passed">Passed ({passed})</button>
            <button class="filter-btn" data-filter="failed">Failed ({failed})</button>
        </div>
        {runs_html}
    </section>

    <footer>
        <p>Generated by <a href="https://github.com/Liquescent-Development/mcprobe">MCProbe</a></p>
    </footer>

    <script>
        // Render markdown content
        document.querySelectorAll('.markdown-content').forEach(el => {{
            el.innerHTML = marked.parse(el.textContent || '');
        }});

        // Syntax highlighting for JSON blocks
        hljs.highlightAll();

        // Filter functionality
        document.querySelectorAll('.filter-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const filter = btn.dataset.filter;
                document.querySelectorAll('.scenario-row').forEach(row => {{
                    if (filter === 'all') {{
                        row.style.display = '';
                    }} else if (filter === 'passed') {{
                        row.style.display = row.dataset.passed === 'true' ? '' : 'none';
                    }} else if (filter === 'failed') {{
                        row.style.display = row.dataset.passed === 'false' ? '' : 'none';
                    }}
                }});
                // Update run section visibility based on visible rows
                document.querySelectorAll('.test-run').forEach(run => {{
                    const sel = '.scenario-row:not([style*="display: none"])';
                    const visibleRows = run.querySelectorAll(sel);
                    run.style.display = visibleRows.length > 0 ? '' : 'none';
                }});
            }});
        }});
    </script>
</body>
</html>
"""
        return html

    def _build_runs_html(self, runs: dict[str, list[TestRunResult]]) -> str:
        """Build HTML for all test runs grouped by run_id."""
        sections = []
        is_first = True
        prev_prompt_hash: str | None = None
        prev_schema_hash: str | None = None

        for run_id, run_results in runs.items():
            # Get metadata from first result in run
            first = run_results[0]
            run_passed = sum(1 for r in run_results if r.judgment_result.passed)
            run_failed = len(run_results) - run_passed
            run_status = "pass" if run_failed == 0 else "fail"
            run_total = len(run_results)

            # Detect changes from previous run
            current_prompt_hash = first.agent_system_prompt_hash
            current_schema_hash = first.mcp_tool_schemas_hash
            prompt_changed = (
                prev_prompt_hash is not None
                and current_prompt_hash is not None
                and current_prompt_hash != prev_prompt_hash
            )
            schema_changed = (
                prev_schema_hash is not None
                and current_schema_hash is not None
                and current_schema_hash != prev_schema_hash
            )

            # Build change badges HTML
            change_badges = self._build_change_badges(prompt_changed, schema_changed)

            # Update for next iteration
            if current_prompt_hash is not None:
                prev_prompt_hash = current_prompt_hash
            if current_schema_hash is not None:
                prev_schema_hash = current_schema_hash

            # Build scenario rows for this run
            scenario_rows = []
            for result in run_results:
                scenario_rows.append(self._build_scenario_row(result))

            scenarios_html = "\n".join(scenario_rows)

            run_time = first.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            # First run is open by default, others are collapsed
            open_attr = " open" if is_first else ""
            is_first = False

            # Build hash badges
            hash_badges = self._build_hash_badges(
                current_prompt_hash, current_schema_hash
            )

            # Build config details section
            config_details_html = self._build_config_details_html(first)

            # Build model badges
            model_badges = self._build_model_badges(
                first.judge_model, first.synthetic_user_model, first.agent_model
            )

            section = f"""
        <details class="test-run {run_status}" data-run-id="{run_id[:8]}"{open_attr}>
            <summary class="run-header">
                <div class="run-info">
                    <span class="run-id">Run {run_id[:8]}</span>
                    <span class="run-timestamp">{run_time}</span>
                    {model_badges}
                    {hash_badges}
                    {change_badges}
                </div>
                <div class="run-stats">
                    <span class="run-total">{run_total} tests</span>
                    <span class="run-passed">{run_passed} passed</span>
                    <span class="run-failed">{run_failed} failed</span>
                </div>
            </summary>
            <div class="run-content">
                {config_details_html}
                <table class="scenarios-table">
                    <thead>
                        <tr>
                            <th>Scenario</th>
                            <th>Status</th>
                            <th>Score</th>
                            <th>Duration</th>
                            <th>Details</th>
                        </tr>
                    </thead>
                    <tbody>
                        {scenarios_html}
                    </tbody>
                </table>
            </div>
        </details>
            """
            sections.append(section)

        return "\n".join(sections)

    def _build_change_badges(self, prompt_changed: bool, schema_changed: bool) -> str:
        """Build HTML for configuration change indicator badges.

        Args:
            prompt_changed: Whether the system prompt changed from previous run.
            schema_changed: Whether the MCP tool schemas changed from previous run.

        Returns:
            HTML string with change badges, or empty string if no changes.
        """
        badges = []
        if prompt_changed:
            badges.append(
                '<span class="config-badge prompt-changed" '
                'title="System prompt changed from previous run">Prompt Changed</span>'
            )
        if schema_changed:
            badges.append(
                '<span class="config-badge schema-changed" '
                'title="MCP tool schemas changed from previous run">Schema Changed</span>'
            )
        return " ".join(badges)

    def _build_model_badges(
        self,
        judge_model: str,
        synthetic_user_model: str,
        agent_model: str | None,
    ) -> str:
        """Build HTML for model badges showing all LLM components.

        Args:
            judge_model: Model name used for the judge.
            synthetic_user_model: Model name used for the synthetic user.
            agent_model: Model name used for the agent (may be None for ADK).

        Returns:
            HTML string with model badges.
        """
        agent_display = _escape_html(agent_model) if agent_model else "N/A"
        return (
            f'<span class="model-badges">'
            f'<span class="model-badge" title="Judge LLM model">'
            f'<span class="model-label">Judge:</span>{_escape_html(judge_model)}</span>'
            f'<span class="model-badge" title="Synthetic User LLM model">'
            f'<span class="model-label">User:</span>{_escape_html(synthetic_user_model)}</span>'
            f'<span class="model-badge" title="Agent LLM model">'
            f'<span class="model-label">Agent:</span>{agent_display}</span>'
            f'</span>'
        )

    def _build_hash_badges(
        self, prompt_hash: str | None, schema_hash: str | None
    ) -> str:
        """Build HTML for prompt and schema hash badges.

        Args:
            prompt_hash: SHA256 hash of the system prompt (first 16 chars).
            schema_hash: SHA256 hash of the MCP tool schemas (first 16 chars).

        Returns:
            HTML string with hash badges.
        """
        badges = []
        if prompt_hash:
            badges.append(
                f'<span class="hash-badge" title="System prompt hash: {prompt_hash}">'
                f'<span class="hash-label">Prompt:</span>{prompt_hash[:8]}</span>'
            )
        if schema_hash:
            badges.append(
                f'<span class="hash-badge" title="Schema hash: {schema_hash}">'
                f'<span class="hash-label">Schema:</span>{schema_hash[:8]}</span>'
            )
        return " ".join(badges)

    def _build_config_details_html(self, result: TestRunResult) -> str:
        """Build HTML for collapsible configuration details section.

        Args:
            result: Test run result containing config data.

        Returns:
            HTML string with collapsible config details.
        """
        # Build system prompt section (render as markdown)
        if result.agent_system_prompt:
            prompt_html = (
                f'<div class="markdown-content system-prompt-content">'
                f'{_escape_html(result.agent_system_prompt)}</div>'
            )
        else:
            prompt_html = '<p class="no-data">No system prompt captured</p>'

        # Build tool schemas section
        if result.mcp_tool_schemas:
            schema_items = []
            for schema in result.mcp_tool_schemas:
                name = _escape_html(schema.get("name", "Unknown"))
                desc = schema.get("description", "")
                desc_short = (
                    _escape_html(desc[:MAX_DESCRIPTION_LENGTH] + "...")
                    if len(desc) > MAX_DESCRIPTION_LENGTH
                    else _escape_html(desc)
                )
                # Format input_schema as JSON
                input_schema = schema.get("input_schema", {})
                schema_json = json.dumps(input_schema, indent=2)

                schema_items.append(
                    f'<details class="tool-schema-item">'
                    f"<summary>{name}"
                    f'<span class="tool-description">{desc_short}</span></summary>'
                    f'<pre><code class="language-json">{_escape_html(schema_json)}</code></pre>'
                    f"</details>"
                )
            schemas_html = "\n".join(schema_items)
            tool_count = len(result.mcp_tool_schemas)
        else:
            schemas_html = '<p class="no-data">No MCP tool schemas captured</p>'
            tool_count = 0

        return f"""
                <details class="config-details">
                    <summary>Configuration Details ({tool_count} tools)</summary>
                    <div class="config-details-content">
                        <div class="config-section">
                            <h5>System Prompt</h5>
                            {prompt_html}
                        </div>
                        <div class="config-section">
                            <h5>MCP Tool Schemas ({tool_count})</h5>
                            {schemas_html}
                        </div>
                    </div>
                </details>
        """

    def _build_scenario_row(self, result: TestRunResult) -> str:
        """Build HTML for a single scenario row."""
        status_class = "pass" if result.judgment_result.passed else "fail"
        status_text = "PASS" if result.judgment_result.passed else "FAIL"

        # Escape HTML in text fields
        name = _escape_html(result.scenario_name)
        reasoning = _escape_html(result.judgment_result.reasoning)

        # Build tags
        tags_html = " ".join(
            f'<span class="tag">{_escape_html(tag)}</span>'
            for tag in result.scenario_tags
        )

        # Build conversation transcript
        conversation_html = self._build_conversation_html(result)

        # Build correctness results
        correctness_html = self._build_correctness_html(result)

        # Build tool calls
        tool_calls_html = self._build_tool_calls_html(result)

        return f"""
            <tr class="scenario-row" data-passed="{str(result.judgment_result.passed).lower()}">
                <td>
                    <strong>{name}</strong>
                    <div class="tags">{tags_html}</div>
                </td>
                <td class="status {status_class}">{status_text}</td>
                <td>{result.judgment_result.score:.2f}</td>
                <td>{result.duration_seconds:.1f}s</td>
                <td>
                    <details>
                        <summary>Details</summary>
                        <div class="details-content">
                            <h4>Judge LLM Reasoning</h4>
                            <p>{reasoning}</p>

                            <h4>Correctness Criteria</h4>
                            {correctness_html}

                            <h4>Conversation</h4>
                            {conversation_html}

                            <h4>Tool Calls ({len(result.conversation_result.total_tool_calls)})</h4>
                            {tool_calls_html}
                        </div>
                    </details>
                </td>
            </tr>
            """

    def _build_conversation_html(self, result: TestRunResult) -> str:
        """Build HTML for conversation transcript."""
        turns = []
        for turn in result.conversation_result.turns:
            role_class = "user" if turn.role == "user" else "assistant"
            content = _escape_html(turn.content)
            # Use markdown rendering for assistant responses
            if turn.role == "assistant":
                turns.append(
                    f'<div class="turn {role_class}">'
                    f"<strong>{turn.role}:</strong>"
                    f'<div class="markdown-content">{content}</div>'
                    f"</div>"
                )
            else:
                turns.append(
                    f'<div class="turn {role_class}">'
                    f"<strong>{turn.role}:</strong> {content}"
                    f"</div>"
                )
        return '<div class="conversation">' + "\n".join(turns) + "</div>"

    def _build_correctness_html(self, result: TestRunResult) -> str:
        """Build HTML for correctness results."""
        items = []
        for criterion, passed in result.judgment_result.correctness_results.items():
            status_class = "pass" if passed else "fail"
            status_icon = "✓" if passed else "✗"
            human_criterion = _humanize_criterion(criterion)
            items.append(
                f'<li class="{status_class}">{status_icon} {_escape_html(human_criterion)}</li>'
            )
        return "<ul>" + "\n".join(items) + "</ul>" if items else "<p>No criteria</p>"

    def _build_tool_calls_html(self, result: TestRunResult) -> str:
        """Build HTML for tool calls with Request/Response labels and collapsible details."""
        if not result.conversation_result.total_tool_calls:
            return "<p>No tool calls</p>"

        items = []
        for tc in result.conversation_result.total_tool_calls:
            # Pretty-print parameters as JSON
            params_json = json.dumps(tc.parameters, indent=2)

            # Format result with proper labeling
            if tc.error:
                result_html = (
                    f'<div class="tool-response error">'
                    f'<span class="response-label">Response (Error):</span>'
                    f'<pre><code>{_escape_html(tc.error)}</code></pre>'
                    f'</div>'
                )
            elif tc.result is not None:
                result_str = _format_tool_result(tc.result)
                result_html = (
                    f'<div class="tool-response success">'
                    f'<span class="response-label">Response:</span>'
                    f'<pre><code class="language-json">{_escape_html(result_str)}</code></pre>'
                    f'</div>'
                )
            else:
                result_html = (
                    '<div class="tool-response">'
                    '<span class="response-label">Response:</span>'
                    '<span class="no-result">No result returned</span>'
                    '</div>'
                )

            items.append(
                f'<details class="tool-call">'
                f'<summary>'
                f'<strong>{_escape_html(tc.tool_name)}</strong>'
                f'<span class="latency">{tc.latency_ms:.0f}ms</span>'
                f'</summary>'
                f'<div class="tool-request">'
                f'<span class="request-label">Request:</span>'
                f'<pre><code class="language-json">{_escape_html(params_json)}</code></pre>'
                f'</div>'
                f'{result_html}'
                f'</details>'
            )
        return "\n".join(items)


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _humanize_criterion(text: str) -> str:
    """Convert snake_case criterion to human-readable format.

    Examples:
        correct_temperature_returned -> Correct temperature returned
        has_valid_response -> Has valid response
    """
    return text.replace("_", " ").capitalize()


def _format_tool_result(result: object) -> str:
    """Format a tool result for display, handling MCP response structures.

    MCP responses often have structure like:
    {"content": [{"type": "text", "text": "{\"key\": \"value\"}"}]}

    This extracts the actual content and pretty-prints it.
    """
    # Handle MCP response structure: extract text content
    if isinstance(result, dict):
        content = result.get("content")
        if isinstance(content, list) and len(content) > 0:
            first_item = content[0]
            if isinstance(first_item, dict) and first_item.get("type") == "text":
                text_content = first_item.get("text", "")
                # Try to parse and pretty-print if it's JSON
                try:
                    parsed = json.loads(text_content)
                    return json.dumps(parsed, indent=2)
                except (json.JSONDecodeError, TypeError):
                    return str(text_content)

    # Handle dict/list directly
    if isinstance(result, (dict, list)):
        return json.dumps(result, indent=2)

    # Handle string that might be JSON
    result_str = str(result)
    try:
        parsed = json.loads(result_str)
        return json.dumps(parsed, indent=2)
    except (json.JSONDecodeError, TypeError):
        return result_str
