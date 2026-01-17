# Reporting Overview

MCProbe provides comprehensive reporting capabilities to help you analyze, visualize, and share test results. Multiple report formats are available to suit different use cases.

## Available Report Formats

### HTML Reports

Interactive, self-contained HTML reports with filtering and detailed conversation views.

**Best for:**
- Sharing results with team members
- Visual analysis of test runs
- Quick overview of test status
- Debugging individual scenario failures

**Features:**
- Summary cards with pass/fail statistics
- Interactive filtering (all/passed/failed)
- Expandable details for each scenario
- Conversation transcripts
- Tool call tracking
- Fully styled and self-contained (no external dependencies)

[Learn more →](html-reports.md)

### JSON Export

Machine-readable JSON format containing all test data.

**Best for:**
- Custom analysis and processing
- Integration with other tools
- Data pipelines
- Long-term storage
- Programmatic access

**Features:**
- Complete test metadata
- Full conversation transcripts
- All judgment results and metrics
- Quality metrics
- Git and CI environment data

[Learn more →](json-export.md)

### JUnit XML

Standard JUnit XML format for CI/CD integration.

**Best for:**
- GitHub Actions test reporting
- GitLab CI integration
- Jenkins and other CI systems
- Test result aggregation
- Historical tracking in CI dashboards

**Features:**
- Standard XML format
- Compatible with all major CI platforms
- Test failure details
- Conversation transcripts in system-out
- Timing information

[Learn more →](ci-integration.md)

## Basic Usage

### Generate a Report

Generate reports from saved test results using the `mcprobe report` command:

```bash
# HTML report (default)
mcprobe report --format html --output report.html

# JSON export
mcprobe report --format json --output results.json

# JUnit XML
mcprobe report --format junit --output junit.xml
```

### Common Options

All report formats support these options:

```bash
# Specify results directory
mcprobe report --results-dir ./my-results --format html

# Custom report title
mcprobe report --format html --title "Sprint 23 Test Results"

# Limit number of results
mcprobe report --format html --limit 50

# Custom output path
mcprobe report --format html --output reports/latest.html
```

## When to Use Each Format

### During Development

Use **HTML reports** for quick visual feedback:

```bash
pytest scenarios/
mcprobe report --format html --output report.html
open report.html  # macOS
xdg-open report.html  # Linux
start report.html  # Windows
```

### In CI/CD Pipelines

Use **JUnit XML** for CI integration:

```bash
pytest scenarios/ --junit-xml=junit.xml
```

The pytest plugin automatically generates JUnit XML that CI systems can parse.

### For Data Analysis

Use **JSON export** for custom analysis:

```bash
mcprobe report --format json --output results.json
python analyze_results.py results.json
```

### For Stakeholders

Use **HTML reports** for sharing with non-technical stakeholders:

```bash
mcprobe report \
  --format html \
  --title "Production Readiness Tests" \
  --output stakeholder-report.html
```

## Integration Examples

### GitHub Actions

```yaml
- name: Run scenarios
  run: pytest scenarios/ -v --junit-xml=junit.xml

- name: Generate HTML report
  run: mcprobe report --format html --output report.html
  if: always()

- name: Upload reports
  uses: actions/upload-artifact@v4
  if: always()
  with:
    name: test-reports
    path: |
      junit.xml
      report.html
      test-results/
```

### GitLab CI

```yaml
script:
  - pytest scenarios/ -v --junit-xml=junit.xml
  - mcprobe report --format html --output report.html

artifacts:
  when: always
  reports:
    junit: junit.xml
  paths:
    - report.html
    - test-results/
```

### Jenkins

```groovy
post {
    always {
        junit 'junit.xml'
        publishHTML([
            reportDir: '.',
            reportFiles: 'report.html',
            reportName: 'MCProbe Test Report'
        ])
    }
}
```

## Report Customization

### HTML Report Title

Customize the report title to reflect your test run:

```bash
mcprobe report \
  --format html \
  --title "Weather API Tests - Production" \
  --output weather-prod-report.html
```

### JUnit Suite Name

Set the test suite name in JUnit XML:

```bash
mcprobe report \
  --format junit \
  --title "mcprobe.weather" \
  --output junit.xml
```

### JSON Conversation Data

Control whether to include full conversation transcripts:

The JSON generator includes conversations by default. To exclude them (smaller files):

```python
from mcprobe.reporting import JsonReportGenerator
from mcprobe.persistence import ResultLoader

loader = ResultLoader("test-results")
results = loader.load_all()

generator = JsonReportGenerator()
generator.generate(
    results,
    output_path=Path("results.json"),
    include_conversations=False  # Exclude conversation details
)
```

## Combining Multiple Reports

Generate all report formats in one command:

```bash
# Generate all formats
mcprobe report --format html --output report.html
mcprobe report --format json --output results.json
mcprobe report --format junit --output junit.xml
```

Or create a script:

```bash
#!/bin/bash
# generate-all-reports.sh

RESULTS_DIR="test-results"
OUTPUT_DIR="reports"

mkdir -p "$OUTPUT_DIR"

mcprobe report \
  --results-dir "$RESULTS_DIR" \
  --format html \
  --output "$OUTPUT_DIR/report.html"

mcprobe report \
  --results-dir "$RESULTS_DIR" \
  --format json \
  --output "$OUTPUT_DIR/results.json"

mcprobe report \
  --results-dir "$RESULTS_DIR" \
  --format junit \
  --output "$OUTPUT_DIR/junit.xml"

echo "Reports generated in $OUTPUT_DIR/"
```

## Report Storage and Organization

### Organizing Reports by Date

```bash
#!/bin/bash
DATE=$(date +%Y%m%d-%H%M%S)
OUTPUT_DIR="reports/$DATE"

mkdir -p "$OUTPUT_DIR"

mcprobe report --format html --output "$OUTPUT_DIR/report.html"
mcprobe report --format json --output "$OUTPUT_DIR/results.json"
```

### Organizing by Environment

```bash
# Development
mcprobe report \
  --results-dir test-results-dev \
  --format html \
  --output reports/dev-report.html

# Staging
mcprobe report \
  --results-dir test-results-staging \
  --format html \
  --output reports/staging-report.html

# Production
mcprobe report \
  --results-dir test-results-prod \
  --format html \
  --output reports/prod-report.html
```

## Accessing Results Programmatically

You can also access results directly in Python:

```python
from pathlib import Path
from mcprobe.persistence import ResultLoader
from mcprobe.reporting import HtmlReportGenerator, JsonReportGenerator

# Load results
loader = ResultLoader(Path("test-results"))
results = loader.load_all(limit=100)

# Generate HTML report
html_gen = HtmlReportGenerator()
html_gen.generate(
    results=results,
    output_path=Path("report.html"),
    title="My Custom Report"
)

# Generate JSON export
json_gen = JsonReportGenerator()
json_gen.generate(
    results=results,
    output_path=Path("results.json"),
    include_conversations=True
)

# Analyze results
passed = sum(1 for r in results if r.judgment_result.passed)
total = len(results)
print(f"Pass rate: {passed}/{total} ({passed/total*100:.1f}%)")
```

## Next Steps

- [HTML Reports Guide](html-reports.md) - Detailed HTML report features
- [JSON Export Guide](json-export.md) - JSON structure and usage
- [CI Integration Guide](ci-integration.md) - Complete CI/CD setup
