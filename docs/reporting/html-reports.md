# HTML Reports Guide

MCProbe generates beautiful, interactive HTML reports that provide comprehensive visualizations of your test results. Reports are fully self-contained with embedded CSS and JavaScript, making them easy to share and view anywhere.

## Generating HTML Reports

### Basic Usage

Generate an HTML report from saved test results:

```bash
mcprobe report --format html --output report.html
```

### Custom Title

Set a custom title for your report:

```bash
mcprobe report \
  --format html \
  --title "Weather API Test Results" \
  --output weather-report.html
```

### Specify Results Directory

Use a custom results directory:

```bash
mcprobe report \
  --results-dir ./my-results \
  --format html \
  --output report.html
```

### Limit Results

Limit the number of recent results included:

```bash
mcprobe report \
  --format html \
  --limit 50 \
  --output report.html
```

## Report Structure

HTML reports consist of several key sections:

### Header

- Report title (customizable)
- Generation timestamp
- Clean, professional layout

### Summary Section

The summary displays key metrics in card format:

- **Total Tests**: Total number of scenarios executed
- **Passed**: Number of scenarios that passed
- **Failed**: Number of scenarios that failed
- **Pass Rate**: Percentage of tests that passed
- **Avg Score**: Average judgment score across all scenarios
- **Duration**: Total execution time

Each card is color-coded:
- Green for passed tests
- Red for failed tests
- Blue/gray for neutral metrics

### Filter Buttons

Interactive filter buttons allow you to view:
- **All**: All test results
- **Passed**: Only passing tests
- **Failed**: Only failing tests

Counters show the number of results in each category.

### Scenarios Table

A detailed table showing all test results with columns:

1. **Scenario**: Scenario name, tags, and change badges
2. **Status**: PASS or FAIL (color-coded)
3. **Score**: Numerical judgment score (0-100)
4. **Duration**: Execution time in seconds
5. **Details**: Expandable details section

#### Change Detection Badges

When configuration tracking is enabled, HTML reports display badges to indicate changes from the previous run:

**Prompt Changed Badge** (Yellow):
- Displayed when the agent's system prompt differs from the previous run
- Helps identify if test behavior changes correlate with prompt modifications
- Color: Yellow/amber background with dark text

**Schema Changed Badge** (Cyan):
- Displayed when MCP tool schemas differ from the previous run
- Helps identify if test failures correlate with tool schema changes
- Color: Cyan/teal background with dark text

These badges appear next to the scenario name in the table, making it easy to spot when configuration changes may have impacted test results.

**Example scenario row with badges:**
```
Weather Query Test  [Prompt Changed] [Schema Changed]  PASS  0.92  1.2s
```

### Details Section

Click "Details" to expand and view:

#### Reasoning
The judge's reasoning for the pass/fail decision.

#### Correctness Criteria
List of correctness criteria with pass/fail status:
- ✓ Criterion passed (green)
- ✗ Criterion failed (red)

#### Conversation Transcript
Complete conversation between the synthetic user and agent:
- **User messages** in blue
- **Assistant messages** in gray
- Clear role labels

#### Tool Calls
All MCP tool calls made during the conversation:
- Tool name
- Parameters (formatted)
- Latency in milliseconds

### Footer

Links to MCProbe documentation and GitHub repository.

## Visual Appearance

### Color Scheme

The HTML report uses a clean, professional color scheme:

- **Primary**: Blue (#2563eb) for headers and accents
- **Success**: Green (#16a34a) for passing tests
- **Failure**: Red (#dc2626) for failing tests
- **Background**: Light gray (#f8fafc) for contrast
- **Text**: Dark gray (#1e293b) for readability

### Typography

- System fonts for fast loading and native appearance
- Clear hierarchy with multiple heading levels
- Monospace font for code and technical details

### Responsive Design

Reports are fully responsive and work on:
- Desktop browsers
- Tablets
- Mobile devices

## Interactive Features

### Filtering

Click filter buttons to show/hide scenarios:

```
[All (10)] [Passed (7)] [Failed (3)]
```

- Active filter is highlighted
- Table updates instantly
- No page reload required

### Expandable Details

Each scenario has a collapsible details section:

- Click "Details" to expand
- Click again to collapse
- Only loads content when expanded for better performance

### Hover Effects

- Buttons highlight on hover
- Table rows highlight on hover
- Interactive elements have cursor changes

## Sharing Reports

### Self-Contained Files

HTML reports are completely self-contained:
- All CSS embedded in `<style>` tags
- All JavaScript embedded in `<script>` tags
- No external dependencies
- No internet connection required to view

### Sharing Options

**Email**: Attach the HTML file to emails

**File Sharing**: Upload to Dropbox, Google Drive, etc.

**Web Hosting**: Host on any web server

**CI Artifacts**: Upload as CI/CD artifacts

**Version Control**: Commit to Git (though this can be large)

## Viewing Reports

### Local Viewing

Open the HTML file in any browser:

```bash
# macOS
open report.html

# Linux
xdg-open report.html

# Windows
start report.html
```

### Web Server

Serve reports with a simple HTTP server:

```bash
# Python 3
python -m http.server 8000

# Then visit: http://localhost:8000/report.html
```

### CI/CD Artifacts

Reports are automatically viewable in CI systems:

**GitHub Actions:**
- Download from the Actions tab
- View directly in artifacts UI

**GitLab CI:**
- Available in pipeline artifacts
- Direct browser viewing

**Jenkins:**
- Published HTML reports are viewable inline
- Accessible from build pages

## Customization Examples

### Development Reports

For daily development testing:

```bash
mcprobe report \
  --format html \
  --title "Dev Tests - $(date +%Y-%m-%d)" \
  --output reports/dev-$(date +%Y%m%d).html
```

### Sprint Reports

For sprint review meetings:

```bash
mcprobe report \
  --format html \
  --title "Sprint 23 - MCP Server Tests" \
  --limit 100 \
  --output reports/sprint-23.html
```

### Environment-Specific Reports

For different environments:

```bash
# Production
mcprobe report \
  --results-dir test-results-prod \
  --format html \
  --title "Production - Weather API Tests" \
  --output reports/prod-report.html

# Staging
mcprobe report \
  --results-dir test-results-staging \
  --format html \
  --title "Staging - Weather API Tests" \
  --output reports/staging-report.html
```

## Change Tracking Configuration

To enable prompt and schema tracking in HTML reports, configure an MCP server connection in your `mcprobe.yaml`:

### Enabling Schema Tracking

```yaml
# mcprobe.yaml
llm:
  provider: ollama
  model: llama3.2

# Enable schema tracking
mcp_server:
  command: "npx @modelcontextprotocol/server-weather"
  # OR for HTTP-based MCP server:
  # url: "http://localhost:8080/mcp"
  # OR with authentication:
  # url: "http://localhost:8080/mcp"
  # headers:
  #   Authorization: "Bearer ${API_TOKEN:-dev}"

results:
  save: true
  dir: test-results
```

### How It Works

1. **During test execution**: MCProbe connects to the configured MCP server and extracts tool schemas
2. **Schema storage**: Tool schemas are stored with each test result along with a SHA256 hash
3. **Change detection**: When generating HTML reports, MCProbe compares hashes between consecutive runs
4. **Badge display**: If schemas differ, a "Schema Changed" badge appears in the report

### Supported Agents for Prompt Tracking

Prompt tracking is currently supported for:

- **SimpleLLMAgent**: Returns the configured system prompt
- **GeminiADKAgent**: Returns the agent's instruction attribute (if set as a string)

Custom agents can implement the `get_system_prompt()` method to enable prompt tracking.

### Use Cases

**Debugging regressions:**
```
Scenario: Weather Query
Status: FAIL [Schema Changed]
```
The badge indicates the failure may be due to schema changes.

**Validating improvements:**
```
Scenario: Complex Query
Status: PASS [Prompt Changed]
Score: 0.95 (was 0.72)
```
The improved score correlates with a prompt change.

**Tracking configuration drift:**
Generate periodic reports to visualize when prompts or schemas change, helping maintain configuration stability in production.

## Report Analysis Tips

### Identifying Patterns

Use the HTML report to identify patterns:

1. **Filter to failed tests** to focus on issues
2. **Check reasoning** to understand failure causes
3. **Review conversation transcripts** to see where things went wrong
4. **Analyze tool calls** to spot inefficiencies or errors
5. **Look for change badges** to correlate failures with configuration changes

### Comparing Runs

Generate reports from different time periods:

```bash
# Last 24 hours
mcprobe report --limit 50 --output today.html

# Last week
mcprobe report --limit 200 --output week.html
```

Open both and compare:
- Pass rates
- Average scores
- Common failure patterns
- Performance metrics

### Team Reviews

Use HTML reports in team meetings:

1. **Share report before meeting** - team members can review
2. **Open during meeting** - use filters to navigate
3. **Expand details** - investigate specific failures
4. **Note patterns** - identify areas for improvement

## Programmatic Generation

Generate reports from Python code:

```python
from pathlib import Path
from mcprobe.persistence import ResultLoader
from mcprobe.reporting import HtmlReportGenerator

# Load results
loader = ResultLoader(Path("test-results"))
results = loader.load_all(limit=100)

# Generate report
generator = HtmlReportGenerator()
generator.generate(
    results=results,
    output_path=Path("custom-report.html"),
    title="Custom Analysis Report"
)

print(f"Generated report with {len(results)} results")
```

## Advanced Usage

### Filtering Results Before Reporting

```python
from pathlib import Path
from mcprobe.persistence import ResultLoader
from mcprobe.reporting import HtmlReportGenerator

loader = ResultLoader(Path("test-results"))
all_results = loader.load_all()

# Filter to only failed tests
failed_results = [r for r in all_results if not r.judgment_result.passed]

# Generate failure-only report
generator = HtmlReportGenerator()
generator.generate(
    results=failed_results,
    output_path=Path("failures-only.html"),
    title="Failed Tests Analysis"
)
```

### Combining Results from Multiple Directories

```python
from pathlib import Path
from mcprobe.persistence import ResultLoader
from mcprobe.reporting import HtmlReportGenerator

# Load from multiple sources
loader1 = ResultLoader(Path("test-results-dev"))
loader2 = ResultLoader(Path("test-results-staging"))

results = loader1.load_all() + loader2.load_all()

# Sort by timestamp
results.sort(key=lambda r: r.timestamp, reverse=True)

# Generate combined report
generator = HtmlReportGenerator()
generator.generate(
    results=results,
    output_path=Path("combined-report.html"),
    title="Dev + Staging Combined Results"
)
```

## Troubleshooting

### Report Not Generated

Check that results exist:

```bash
ls -la test-results/
```

Verify the results directory:

```bash
mcprobe report --results-dir test-results --format html
```

### Empty Report

Ensure tests have been run:

```bash
pytest scenarios/ --mcprobe-save-results
```

Check result count:

```bash
mcprobe report --format html --limit 1000
```

### Report Too Large

Limit the number of results:

```bash
mcprobe report --format html --limit 50 --output report.html
```

Or generate separate reports:

```bash
# Recent results
mcprobe report --format html --limit 25 --output recent.html

# Older results (use ResultLoader in Python to filter by date)
```

## Next Steps

- [CI Integration](ci-integration.md) - Integrate HTML reports in CI/CD
- [JSON Export](json-export.md) - Export data for custom analysis
- [Reporting Overview](overview.md) - Learn about other report formats
