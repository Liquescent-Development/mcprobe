# Analysis Commands Guide

Comprehensive guide to MCProbe's analysis and reporting commands for tracking test performance, detecting issues, and generating reports.

## Overview

MCProbe provides four analysis commands:

| Command | Purpose |
|---------|---------|
| [mcprobe report](#mcprobe-report) | Generate HTML, JSON, or JUnit reports |
| [mcprobe trends](#mcprobe-trends) | Analyze pass rate and score trends over time |
| [mcprobe flaky](#mcprobe-flaky) | Detect inconsistent (flaky) test scenarios |
| [mcprobe stability-check](#mcprobe-stability-check) | Check stability of a specific scenario |

All analysis commands work with the results directory where MCProbe stores test results.

## Results Directory

### Default Location

By default, MCProbe stores results in:
```
./test-results/
```

### Results Storage

Each test run creates timestamped result files:
```
test-results/
├── 2024-01-15_10-30-45_weather_query.json
├── 2024-01-15_10-30-48_greeting_test.json
├── 2024-01-15_10-30-52_error_handling.json
├── 2024-01-16_09-15-22_weather_query.json
└── 2024-01-16_09-15-25_greeting_test.json
```

Each file contains:
- Scenario metadata
- Conversation transcript
- Judgment results
- Tool call details
- Quality and efficiency metrics
- Timestamps

### Custom Results Directory

Specify a different directory with `--results-dir`:
```bash
mcprobe trends --results-dir ./my-results
mcprobe report --results-dir ./historical-data
```

## mcprobe report

Generate formatted reports from test results.

### Basic Usage

```bash
mcprobe report [OPTIONS]
```

Generate default HTML report:
```bash
mcprobe report
# Creates: report.html
```

### Report Formats

#### HTML Report (Default)

Interactive HTML report with visualizations.

```bash
mcprobe report --format html --output my-report.html
```

**Features:**
- Pass/fail summary
- Score distributions
- Trend charts
- Detailed scenario breakdowns
- Tool usage statistics
- Quality metrics
- Interactive filtering
- Responsive design

**Use cases:**
- Team dashboards
- Stakeholder presentations
- Development review
- Quality tracking

**Example:**
```bash
mcprobe report \
  --format html \
  --output dashboard.html \
  --title "MCProbe Weekly Report"
```

#### JSON Report

Machine-readable JSON format.

```bash
mcprobe report --format json --output results.json
```

**Structure:**
```json
{
  "metadata": {
    "generated_at": "2024-01-16T10:30:00Z",
    "title": "MCProbe Test Report",
    "total_scenarios": 42,
    "total_runs": 128
  },
  "summary": {
    "pass_rate": 0.92,
    "average_score": 0.87,
    "total_passed": 118,
    "total_failed": 10
  },
  "scenarios": [
    {
      "name": "Weather Query Test",
      "runs": 5,
      "pass_rate": 1.0,
      "avg_score": 0.94,
      "latest_result": {...}
    }
  ],
  "details": [...]
}
```

**Use cases:**
- Custom analysis scripts
- Data pipelines
- Integration with other tools
- Long-term archival

**Example:**
```bash
mcprobe report --format json --output results.json

# Process with jq
cat results.json | jq '.summary.pass_rate'

# Custom analysis
python analyze_results.py results.json
```

#### JUnit XML Report

JUnit-compatible XML for CI/CD integration.

```bash
mcprobe report --format junit --output test-results.xml
```

**Structure:**
```xml
<?xml version="1.0" ?>
<testsuites>
  <testsuite name="MCProbe Test Report" tests="42" failures="4">
    <testcase classname="mcprobe" name="Weather Query Test" time="12.5">
      <system-out>Score: 0.94
Reasoning: Agent successfully retrieved weather data...</system-out>
    </testcase>
    <testcase classname="mcprobe" name="Error Handling" time="8.3">
      <failure message="Failed correctness criteria">
Score: 0.45
Reasoning: Agent failed to handle error gracefully...
      </failure>
    </testcase>
  </testsuite>
</testsuites>
```

**Use cases:**
- GitHub Actions integration
- Jenkins CI/CD
- GitLab CI
- Any JUnit-compatible system

**Example:**
```bash
# Generate JUnit report
mcprobe report \
  --format junit \
  --output test-results.xml \
  --title "MCProbe CI Tests"

# Use in GitHub Actions
# (automatically picked up by test reporting)
```

### Options Reference

```bash
mcprobe report \
  --results-dir ./test-results \  # Results directory
  --output report.html \           # Output file
  --format html \                  # Format: html, json, junit
  --title "My Report" \            # Report title
  --limit 100                      # Max results to include
```

### Examples

**Daily development report:**
```bash
mcprobe report \
  --format html \
  --output daily-report.html \
  --title "Daily Test Report - $(date +%Y-%m-%d)"
```

**CI/CD integration:**
```bash
# Run tests
mcprobe run scenarios/

# Generate JUnit report for CI
mcprobe report \
  --format junit \
  --output test-results.xml \
  --title "MCProbe CI Tests"

# Generate HTML for artifacts
mcprobe report \
  --format html \
  --output report.html \
  --title "CI Test Report #$BUILD_NUMBER"
```

**Multi-format reporting:**
```bash
# Generate all formats
mcprobe report --format html --output report.html
mcprobe report --format json --output report.json
mcprobe report --format junit --output report.xml
```

**Historical analysis:**
```bash
# Limit to recent results
mcprobe report --limit 50 --output recent-report.html

# Include all historical data
mcprobe report --limit 1000 --output full-history.html
```

## mcprobe trends

Analyze trends in test performance over time.

### Basic Usage

```bash
mcprobe trends [OPTIONS]
```

Analyze all scenarios:
```bash
mcprobe trends
```

Analyze specific scenario:
```bash
mcprobe trends --scenario "Weather Query Test"
```

### Understanding Trend Analysis

MCProbe analyzes trends by:
1. Loading historical results for each scenario
2. Calculating pass rates and average scores over time
3. Detecting statistical trends (improving, degrading, stable)
4. Identifying regressions

### Trend Indicators

| Indicator | Meaning | Criteria |
|-----------|---------|----------|
| `↑` (green) | Improving | Statistically significant improvement in metric |
| `↓` (red) | Degrading | Statistically significant degradation in metric |
| `→` (gray) | Stable | No significant change detected |

### Options

```bash
mcprobe trends \
  --scenario "My Scenario" \  # Analyze specific scenario (optional)
  --window 10 \               # Number of recent runs to analyze
  --results-dir ./results     # Results directory
```

### Window Size

The `--window` parameter controls how many recent runs to consider:

**Small window (5-10):**
- Detects recent changes quickly
- More sensitive to noise
- Good for active development

```bash
mcprobe trends --window 5
```

**Medium window (10-20, default):**
- Balanced sensitivity
- Good for general use
- Recommended for CI/CD

```bash
mcprobe trends --window 10
```

**Large window (20-50):**
- More stable trend detection
- Less sensitive to outliers
- Good for long-term analysis

```bash
mcprobe trends --window 30
```

### Output Examples

**All scenarios with trends:**
```
Trend Analysis
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Scenario            ┃ Runs ┃ Pass Rate ┃ Pass Trend ┃ Avg Score ┃ Score Trend ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Weather Query       │   20 │       95% │     ↑      │      0.92 │      →      │
│ Greeting Test       │   20 │      100% │     →      │      0.98 │      ↑      │
│ Error Handling      │   15 │       80% │     ↓      │      0.75 │      ↓      │
│ Complex Workflow    │   10 │       90% │     →      │      0.88 │      →      │
└─────────────────────┴──────┴───────────┴────────────┴───────────┴─────────────┘
```

**With regressions detected:**
```
⚠ Detected Regressions:
  [high] Error Handling: pass_rate dropped 15.0%
  [medium] Error Handling: avg_score dropped 12.5%
  [low] Weather Query: avg_score dropped 3.2%
```

**Single scenario analysis:**
```bash
mcprobe trends --scenario "Weather Query Test" --window 20
```
```
Trend Analysis
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Scenario            ┃ Runs ┃ Pass Rate ┃ Pass Trend ┃ Avg Score ┃ Score Trend ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Weather Query Test  │   20 │       95% │     ↑      │      0.92 │      →      │
└─────────────────────┴──────┴───────────┴────────────┴───────────┴─────────────┘

No regressions detected.
```

### Regression Detection

MCProbe automatically detects regressions with severity levels:

**High severity:**
- Pass rate drops > 10%
- Average score drops > 0.15

**Medium severity:**
- Pass rate drops 5-10%
- Average score drops 0.10-0.15

**Low severity:**
- Pass rate drops 2-5%
- Average score drops 0.05-0.10

### Use Cases

**Daily development check:**
```bash
# Check for regressions after changes
mcprobe run scenarios/
mcprobe trends
```

**Weekly review:**
```bash
# Analyze trends over past week
mcprobe trends --window 20
```

**CI/CD quality gates:**
```bash
# Run tests
mcprobe run scenarios/

# Check for regressions
mcprobe trends --window 10
if grep -q "Detected Regressions" <(mcprobe trends); then
  echo "Regressions detected!"
  exit 1
fi
```

**Long-term analysis:**
```bash
# Analyze long-term trends
mcprobe trends --window 50 > trends-report.txt
```

## mcprobe flaky

Detect flaky (inconsistent) test scenarios.

### Basic Usage

```bash
mcprobe flaky [OPTIONS]
```

Detect flaky tests:
```bash
mcprobe flaky
```

Require more runs for analysis:
```bash
mcprobe flaky --min-runs 10
```

Fail CI build if flaky tests detected:
```bash
mcprobe flaky --fail-on-flaky
```

### What is a Flaky Test?

A flaky test is one that:
- Sometimes passes, sometimes fails (without code changes)
- Has inconsistent scores across runs
- Shows unpredictable behavior

Flaky tests indicate:
- Non-deterministic behavior in your agent
- Timing issues
- Race conditions
- Environmental dependencies
- Unclear test criteria

### Detection Criteria

MCProbe considers a scenario flaky if:

**Pass rate instability:**
- Pass rate between 20% and 80%
- (Neither consistently passing nor consistently failing)

**Score variance:**
- High standard deviation in scores (> 0.15)
- Indicates inconsistent quality

**Pattern inconsistency:**
- Alternating pass/fail patterns
- Recent results differ significantly from historical

### Severity Levels

**High severity:**
```
Pass rate: 30-70%
OR Score std dev > 0.20
```
Indicates serious stability issues.

**Medium severity:**
```
Pass rate: 20-30% or 70-80%
OR Score std dev: 0.15-0.20
```
Indicates moderate instability.

**Low severity:**
```
Pass rate: slightly outside 20-80%
OR Score std dev: 0.12-0.15
```
Borderline flaky, may need monitoring.

### Options

```bash
mcprobe flaky \
  --min-runs 5 \           # Minimum runs required
  --results-dir ./results \ # Results directory
  --fail-on-flaky          # Exit with code 1 if flaky tests found
```

### Output Examples

**Flaky scenarios detected:**
```
Flaky Scenarios
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Scenario           ┃ Pass Rate ┃ Runs ┃ Severity ┃ Reason                     ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Weather Query      │       60% │   10 │   high   │ Pass rate in flaky range   │
│ Complex Workflow   │       90% │   15 │  medium  │ High score variance        │
│ Error Handling     │       75% │   12 │  medium  │ Inconsistent results       │
└────────────────────┴───────────┴──────┴──────────┴────────────────────────────┘

Found 3 flaky scenario(s)
```

**No flaky scenarios:**
```
No flaky scenarios detected.
```

**Insufficient data:**
If scenarios don't have enough runs:
```
No flaky scenarios detected.

Note: Some scenarios have fewer than 5 runs and were not analyzed:
  - New Scenario (3 runs)
  - Recent Addition (2 runs)
```

### Use Cases

**CI/CD quality gate:**
```bash
# Fail build if flaky tests exist
mcprobe flaky --min-runs 10 --fail-on-flaky
```

GitHub Actions example:
```yaml
- name: Run tests
  run: mcprobe run scenarios/

- name: Check for flaky tests
  run: mcprobe flaky --fail-on-flaky
```

**Development workflow:**
```bash
# Run scenario multiple times to check stability
for i in {1..10}; do
  mcprobe run scenarios/my-test.yaml
done

# Check if it's flaky
mcprobe flaky
```

**Regular monitoring:**
```bash
# Weekly flaky test report
mcprobe flaky --min-runs 10 > flaky-report.txt
cat flaky-report.txt
```

### Fixing Flaky Tests

When you detect flaky scenarios:

**1. Investigate the cause:**
```bash
# Run with verbose output multiple times
mcprobe run scenarios/flaky-test.yaml -v
mcprobe run scenarios/flaky-test.yaml -v
mcprobe run scenarios/flaky-test.yaml -v

# Compare the conversation transcripts
# Look for differences in:
# - Tool call patterns
# - Agent responses
# - Error conditions
```

**2. Common causes and fixes:**

**Ambiguous evaluation criteria:**
```yaml
# Bad: Vague criteria
evaluation:
  correctness_criteria:
    - Agent provides helpful answer

# Good: Specific criteria
evaluation:
  correctness_criteria:
    - Agent calls get_weather tool with correct location
    - Agent includes temperature in response
    - Agent responds within 5 turns
```

**Non-deterministic behavior:**
```yaml
# Add constraints to reduce randomness
synthetic_user:
  initial_query: "What's the weather in London?" # Specific
  max_turns: 5  # Limit

evaluation:
  tool_usage:
    expected_tools:
      - get_current_weather  # Explicit expectations
```

**Environmental dependencies:**
- Ensure MCP servers are stable
- Use consistent model/provider
- Control temperature settings

**3. Re-test after fixes:**
```bash
# Run multiple times to verify fix
for i in {1..10}; do
  mcprobe run scenarios/fixed-test.yaml
done

# Confirm it's no longer flaky
mcprobe flaky
```

## mcprobe stability-check

Check the stability of a specific scenario in detail.

### Basic Usage

```bash
mcprobe stability-check SCENARIO_NAME [OPTIONS]
```

Check scenario stability:
```bash
mcprobe stability-check "Weather Query Test"
```

Require more runs:
```bash
mcprobe stability-check "My Test" --min-runs 10
```

### Output Examples

**Stable scenario:**
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Stability Check: Weather Query Test ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Run Count          15
Pass Rate         100%
Mean Score        0.95
Score Std Dev     0.023

✓ Scenario is stable
```

**Unstable scenario:**
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Stability Check: Complex Workflow ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Run Count          12
Pass Rate          67%
Mean Score         0.73
Score Std Dev      0.182

✗ Scenario is unstable
  - Pass rate in flaky range (20-80%)
  - High score variance (std dev > 0.15)
```

**Insufficient data:**
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Stability Check: New Test     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Insufficient data for stability analysis
Run count: 3 (need at least 5)
```

### Interpreting Results

**Run Count:**
Number of times the scenario has been executed.

**Pass Rate:**
Percentage of runs that passed.
- 100%: Always passes
- 0%: Always fails (stable failure)
- 20-80%: Flaky range

**Mean Score:**
Average score across all runs.
- > 0.90: Excellent
- 0.80-0.90: Good
- 0.70-0.80: Acceptable
- < 0.70: Needs improvement

**Score Std Dev:**
Standard deviation of scores.
- < 0.05: Very consistent
- 0.05-0.10: Moderately consistent
- 0.10-0.15: Some variance
- > 0.15: High variance (flaky)

### Use Cases

**Pre-deployment check:**
```bash
# Verify critical scenario is stable
mcprobe stability-check "Critical User Flow" --min-runs 10

# Only deploy if stable
if mcprobe stability-check "Critical User Flow" | grep -q "is stable"; then
  ./deploy.sh
fi
```

**Debugging flaky tests:**
```bash
# After detecting flaky test
mcprobe flaky
# Flaky Scenarios shows "Weather Query" is flaky

# Get detailed metrics
mcprobe stability-check "Weather Query"
# Shows: Pass rate 65%, Score std dev 0.18

# Fix the test...

# Re-run multiple times
for i in {1..15}; do
  mcprobe run scenarios/weather-query.yaml
done

# Verify fix
mcprobe stability-check "Weather Query"
# Should now show: Pass rate 100%, Score std dev < 0.05
```

**Monitoring specific scenarios:**
```bash
# Monitor critical scenarios regularly
mcprobe stability-check "User Authentication" > stability.log
mcprobe stability-check "Payment Processing" >> stability.log
mcprobe stability-check "Data Export" >> stability.log
```

## Working with Results Directory

### Directory Structure

Understanding the results directory helps with analysis:

```
test-results/
├── 2024-01-15_10-30-45_weather_query_test.json
├── 2024-01-15_10-30-48_greeting_test.json
├── 2024-01-15_14-15-22_weather_query_test.json
└── 2024-01-16_09-20-15_weather_query_test.json
```

Filename format:
```
{timestamp}_{scenario_name}.json
```

### Managing Results

**View recent results:**
```bash
ls -lt test-results/ | head -10
```

**Count results per scenario:**
```bash
# On Unix/Linux/macOS
ls test-results/ | cut -d_ -f4- | sort | uniq -c
```

**Clean old results:**
```bash
# Keep only last 30 days
find test-results/ -name "*.json" -mtime +30 -delete
```

**Archive results:**
```bash
# Monthly archive
tar -czf test-results-2024-01.tar.gz test-results/
mkdir -p archives/
mv test-results-2024-01.tar.gz archives/
```

**Separate results by environment:**
```bash
# Different directories for different environments
mcprobe run scenarios/ --results-dir ./results-dev
mcprobe run scenarios/ --results-dir ./results-staging
mcprobe run scenarios/ --results-dir ./results-prod

# Analyze separately
mcprobe trends --results-dir ./results-prod
```

### Results File Format

Each result file is JSON:
```json
{
  "scenario_name": "Weather Query Test",
  "timestamp": "2024-01-16T10:30:45Z",
  "passed": true,
  "score": 0.92,
  "conversation": {
    "turns": [...]
  },
  "judgment": {
    "reasoning": "...",
    "correctness_results": {...},
    "quality_metrics": {...}
  },
  "metadata": {
    "model": "llama3.2",
    "agent_type": "simple"
  }
}
```

## CI/CD Integration

### GitHub Actions

Complete CI/CD workflow:

```yaml
name: MCProbe Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install mcprobe

      - name: Start Ollama
        run: |
          # Install and start Ollama
          curl https://ollama.ai/install.sh | sh
          ollama serve &
          ollama pull llama3.2

      - name: Validate scenarios
        run: mcprobe validate scenarios/

      - name: Run tests
        run: mcprobe run scenarios/

      - name: Check for regressions
        run: mcprobe trends --window 10

      - name: Check for flaky tests
        run: mcprobe flaky --fail-on-flaky

      - name: Generate reports
        if: always()
        run: |
          mcprobe report --format html --output report.html
          mcprobe report --format junit --output test-results.xml

      - name: Publish test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: |
            report.html
            test-results.xml

      - name: Publish JUnit results
        if: always()
        uses: mikepenz/action-junit-report@v3
        with:
          report_paths: 'test-results.xml'
```

### GitLab CI

```yaml
mcprobe:
  image: python:3.12

  before_script:
    - pip install mcprobe
    - curl https://ollama.ai/install.sh | sh
    - ollama serve &
    - ollama pull llama3.2

  script:
    - mcprobe validate scenarios/
    - mcprobe run scenarios/
    - mcprobe trends --window 10
    - mcprobe flaky --fail-on-flaky
    - mcprobe report --format junit --output test-results.xml

  artifacts:
    when: always
    reports:
      junit: test-results.xml
    paths:
      - report.html
```

### Jenkins

```groovy
pipeline {
  agent any

  stages {
    stage('Setup') {
      steps {
        sh 'pip install mcprobe'
        sh 'ollama pull llama3.2'
      }
    }

    stage('Validate') {
      steps {
        sh 'mcprobe validate scenarios/'
      }
    }

    stage('Test') {
      steps {
        sh 'mcprobe run scenarios/'
      }
    }

    stage('Analyze') {
      steps {
        sh 'mcprobe trends --window 10'
        sh 'mcprobe flaky --fail-on-flaky'
      }
    }

    stage('Report') {
      steps {
        sh 'mcprobe report --format junit --output test-results.xml'
        sh 'mcprobe report --format html --output report.html'
      }
    }
  }

  post {
    always {
      junit 'test-results.xml'
      publishHTML([
        reportDir: '.',
        reportFiles: 'report.html',
        reportName: 'MCProbe Report'
      ])
    }
  }
}
```

## Best Practices

### Regular Analysis

**Daily development:**
```bash
# After making changes
mcprobe run scenarios/
mcprobe trends --window 5
```

**Weekly review:**
```bash
# Generate comprehensive report
mcprobe report --format html --output weekly-report.html --title "Weekly Test Report"
mcprobe trends --window 20
mcprobe flaky --min-runs 10
```

**Monthly analysis:**
```bash
# Long-term trends
mcprobe trends --window 50
mcprobe report --format html --limit 500 --output monthly-report.html
```

### Quality Gates

Set up quality gates in CI:

```bash
#!/bin/bash
set -e

# Run tests
mcprobe run scenarios/

# Check for regressions
if mcprobe trends --window 10 | grep -q "high.*Regression"; then
  echo "High-severity regression detected!"
  exit 1
fi

# Check for flaky tests
mcprobe flaky --min-runs 5 --fail-on-flaky

# Generate report
mcprobe report --format junit --output test-results.xml

echo "All quality gates passed!"
```

### Monitoring Strategy

**Track key metrics:**
1. **Pass rate trends**: Are scenarios degrading?
2. **Score trends**: Is quality improving?
3. **Flaky tests**: Are tests stable?
4. **New failures**: What broke recently?

**Alerting:**
```bash
# Example: Email on regressions
mcprobe trends --window 10 > trends.txt
if grep -q "high.*Regression" trends.txt; then
  mail -s "MCProbe: Regression Detected" team@example.com < trends.txt
fi
```

## Next Steps

- [CLI Reference](reference.md) - Complete command reference
- [Running Tests](run.md) - Execute test scenarios
- [Scenario Generation](generate.md) - Auto-generate scenarios
- [Scenario Format](../scenarios/format.md) - YAML scenario structure
