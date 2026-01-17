"""HTML report generator for MCProbe test results.

Generates beautiful, self-contained HTML reports from test run results.
"""

from __future__ import annotations

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

        # Build scenarios rows
        scenario_rows = []
        for result in results:
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

            row = f"""
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
                            <h4>Reasoning</h4>
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
            scenario_rows.append(row)

        scenarios_html = "\n".join(scenario_rows)

        # Build the full HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{_escape_html(title)}</title>
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
        <h2>Scenarios</h2>
        <div class="filters">
            <button class="filter-btn active" data-filter="all">All ({total})</button>
            <button class="filter-btn" data-filter="passed">Passed ({passed})</button>
            <button class="filter-btn" data-filter="failed">Failed ({failed})</button>
        </div>
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
    </section>

    <footer>
        <p>Generated by <a href="https://github.com/mcprobe/mcprobe">MCProbe</a></p>
    </footer>

    <script>
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
            }});
        }});
    </script>
</body>
</html>
"""
        return html

    def _build_conversation_html(self, result: TestRunResult) -> str:
        """Build HTML for conversation transcript."""
        turns = []
        for turn in result.conversation_result.turns:
            role_class = "user" if turn.role == "user" else "assistant"
            content = _escape_html(turn.content)
            turns.append(
                f'<div class="turn {role_class}"><strong>{turn.role}:</strong> {content}</div>'
            )
        return '<div class="conversation">' + "\n".join(turns) + "</div>"

    def _build_correctness_html(self, result: TestRunResult) -> str:
        """Build HTML for correctness results."""
        items = []
        for criterion, passed in result.judgment_result.correctness_results.items():
            status_class = "pass" if passed else "fail"
            status_icon = "✓" if passed else "✗"
            items.append(
                f'<li class="{status_class}">{status_icon} {_escape_html(criterion)}</li>'
            )
        return "<ul>" + "\n".join(items) + "</ul>" if items else "<p>No criteria</p>"

    def _build_tool_calls_html(self, result: TestRunResult) -> str:
        """Build HTML for tool calls."""
        if not result.conversation_result.total_tool_calls:
            return "<p>No tool calls</p>"

        items = []
        for tc in result.conversation_result.total_tool_calls:
            params = str(tc.parameters)
            items.append(
                f'<div class="tool-call">'
                f'<strong>{_escape_html(tc.tool_name)}</strong>'
                f'<code>{_escape_html(params)}</code>'
                f'<span class="latency">{tc.latency_ms:.0f}ms</span>'
                f'</div>'
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
