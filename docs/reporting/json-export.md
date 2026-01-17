# JSON Export Format Guide

MCProbe can export test results as JSON for programmatic access, custom analysis, and integration with other tools. The JSON format includes complete test data, conversation transcripts, and all metrics.

## Generating JSON Reports

### Basic Usage

Generate a JSON export from saved test results:

```bash
mcprobe report --format json --output results.json
```

### Options

Specify a custom results directory:

```bash
mcprobe report \
  --format json \
  --results-dir ./my-results \
  --output results.json
```

Limit the number of results:

```bash
mcprobe report \
  --format json \
  --limit 50 \
  --output recent-results.json
```

## JSON Structure

The JSON export has two main sections: `metadata` and `results`.

### Top-Level Structure

```json
{
  "metadata": {
    "generated_at": "2025-01-15T14:30:00",
    "mcprobe_version": "0.1.0",
    "total_tests": 10,
    "passed": 7,
    "failed": 3,
    "pass_rate": 0.7,
    "total_duration_seconds": 123.45
  },
  "results": [
    { /* individual test result */ },
    { /* individual test result */ }
  ]
}
```

### Metadata Section

The `metadata` section contains summary information:

| Field | Type | Description |
|-------|------|-------------|
| `generated_at` | string | ISO 8601 timestamp of report generation |
| `mcprobe_version` | string | MCProbe version used for testing |
| `total_tests` | integer | Total number of test results |
| `passed` | integer | Number of passing tests |
| `failed` | integer | Number of failing tests |
| `pass_rate` | float | Pass rate (0.0 to 1.0) |
| `total_duration_seconds` | float | Combined duration of all tests |

### Results Section

Each entry in the `results` array represents one test run:

```json
{
  "run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2025-01-15T14:25:00",
  "scenario_name": "Weather Basic Query",
  "scenario_file": "/path/to/scenarios/weather_basic.yaml",
  "scenario_tags": ["weather", "basic"],
  "passed": true,
  "score": 85.5,
  "reasoning": "Agent correctly retrieved weather data and formatted response appropriately.",
  "duration_seconds": 12.34,
  "agent_type": "simple",
  "model_name": "llama3.2",
  "correctness_results": {
    "Retrieves weather data": true,
    "Formats response clearly": true
  },
  "failure_results": {
    "Makes up information": false,
    "Ignores user request": false
  },
  "tool_usage_results": {
    "Uses appropriate tools": true,
    "Handles tool errors": true
  },
  "efficiency_results": {
    "total_tokens": 1250,
    "total_tool_calls": 2,
    "total_turns": 4
  },
  "suggestions": [
    "Consider caching weather data for frequently requested locations"
  ],
  "quality_metrics": {
    "clarification_count": 0,
    "backtrack_count": 0,
    "turns_to_first_answer": 2,
    "final_answer_completeness": 0.95
  },
  "conversation": {
    /* conversation data (see below) */
  },
  "git_commit": "a1b2c3d",
  "git_branch": "main",
  "ci_environment": {
    "CI": "true",
    "GITHUB_ACTIONS": "true",
    "GITHUB_RUN_ID": "1234567890"
  }
}
```

### Result Fields

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | string | Unique UUID for this test run |
| `timestamp` | string | ISO 8601 timestamp when test started |
| `scenario_name` | string | Human-readable scenario name |
| `scenario_file` | string | Path to scenario YAML file |
| `scenario_tags` | array | List of scenario tags |
| `passed` | boolean | Whether the test passed |
| `score` | float | Judgment score (0-100) |
| `reasoning` | string | Judge's reasoning for the decision |
| `duration_seconds` | float | Test execution time |
| `agent_type` | string | Agent type (simple, adk, etc.) |
| `model_name` | string | LLM model used |
| `correctness_results` | object | Map of correctness criteria to pass/fail |
| `failure_results` | object | Map of failure conditions to triggered/not triggered |
| `tool_usage_results` | object | Map of tool usage criteria to pass/fail |
| `efficiency_results` | object | Efficiency metrics (tokens, tool calls, turns) |
| `suggestions` | array | List of improvement suggestions |
| `quality_metrics` | object | Quality metrics (see below) |
| `conversation` | object | Full conversation data (optional, see below) |
| `git_commit` | string | Git commit hash (if in a repo) |
| `git_branch` | string | Git branch name (if in a repo) |
| `ci_environment` | object | CI environment variables (if in CI) |

### Quality Metrics

```json
{
  "clarification_count": 0,
  "backtrack_count": 0,
  "turns_to_first_answer": 2,
  "final_answer_completeness": 0.95
}
```

| Field | Type | Description |
|-------|------|-------------|
| `clarification_count` | integer | Number of times agent asked for clarification |
| `backtrack_count` | integer | Number of times agent corrected itself |
| `turns_to_first_answer` | integer | Conversation turns before first answer |
| `final_answer_completeness` | float | Completeness score (0.0 to 1.0) |

### Conversation Data

The `conversation` object contains the complete conversation transcript:

```json
{
  "turns": [
    {
      "role": "user",
      "content": "What's the weather in San Francisco?",
      "tool_calls": [],
      "timestamp": "2025-01-15T14:25:01"
    },
    {
      "role": "assistant",
      "content": "Let me check the weather for you.",
      "tool_calls": [
        {
          "tool_name": "get_weather",
          "parameters": {
            "location": "San Francisco, CA"
          },
          "result": {
            "temperature": 65,
            "condition": "Sunny"
          },
          "latency_ms": 234.5,
          "error": null
        }
      ],
      "timestamp": "2025-01-15T14:25:02"
    }
  ],
  "final_answer": "The weather in San Francisco is currently 65°F and sunny.",
  "total_tokens": 1250,
  "termination_reason": "goal_achieved"
}
```

#### Conversation Fields

| Field | Type | Description |
|-------|------|-------------|
| `turns` | array | List of conversation turns |
| `final_answer` | string | The agent's final answer |
| `total_tokens` | integer | Total tokens used in conversation |
| `termination_reason` | string | Why the conversation ended |

#### Turn Fields

| Field | Type | Description |
|-------|------|-------------|
| `role` | string | "user" or "assistant" |
| `content` | string | Message content |
| `tool_calls` | array | List of tool calls in this turn |
| `timestamp` | string | ISO 8601 timestamp of turn |

#### Tool Call Fields

| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | string | Name of the tool called |
| `parameters` | object | Parameters passed to tool |
| `result` | any | Result returned by tool |
| `latency_ms` | float | Tool execution time in milliseconds |
| `error` | string \| null | Error message if tool call failed |

## Using JSON for Custom Analysis

### Loading JSON in Python

```python
import json
from pathlib import Path

# Load JSON report
with open("results.json") as f:
    data = json.load(f)

# Access metadata
print(f"Total tests: {data['metadata']['total_tests']}")
print(f"Pass rate: {data['metadata']['pass_rate']:.1%}")

# Analyze results
for result in data["results"]:
    print(f"{result['scenario_name']}: {'PASS' if result['passed'] else 'FAIL'}")
    print(f"  Score: {result['score']:.1f}")
    print(f"  Duration: {result['duration_seconds']:.1f}s")
```

### Filtering Failed Tests

```python
import json

with open("results.json") as f:
    data = json.load(f)

# Get all failed tests
failed = [r for r in data["results"] if not r["passed"]]

print(f"Failed tests: {len(failed)}")
for result in failed:
    print(f"\n{result['scenario_name']}")
    print(f"  Reason: {result['reasoning']}")
    print(f"  Score: {result['score']:.1f}")
```

### Analyzing Tool Usage

```python
import json
from collections import Counter

with open("results.json") as f:
    data = json.load(f)

# Count tool calls across all tests
tool_counts = Counter()

for result in data["results"]:
    if "conversation" in result:
        for turn in result["conversation"]["turns"]:
            for tool_call in turn["tool_calls"]:
                tool_counts[tool_call["tool_name"]] += 1

print("Tool usage statistics:")
for tool, count in tool_counts.most_common():
    print(f"  {tool}: {count} calls")
```

### Calculating Average Metrics

```python
import json
import statistics

with open("results.json") as f:
    data = json.load(f)

# Calculate average metrics
scores = [r["score"] for r in data["results"]]
durations = [r["duration_seconds"] for r in data["results"]]
tokens = [r["efficiency_results"]["total_tokens"] for r in data["results"]]

print(f"Average score: {statistics.mean(scores):.1f}")
print(f"Average duration: {statistics.mean(durations):.1f}s")
print(f"Average tokens: {statistics.mean(tokens):.0f}")
print(f"Score std dev: {statistics.stdev(scores):.2f}")
```

### Time Series Analysis

```python
import json
from datetime import datetime
import pandas as pd

# Load results
with open("results.json") as f:
    data = json.load(f)

# Convert to pandas DataFrame
df = pd.DataFrame(data["results"])
df["timestamp"] = pd.to_datetime(df["timestamp"])

# Group by date
daily = df.groupby(df["timestamp"].dt.date).agg({
    "passed": "sum",
    "score": "mean",
    "duration_seconds": "mean"
})

print(daily)
```

## Integration with Other Tools

### Exporting to CSV

```python
import json
import csv

with open("results.json") as f:
    data = json.load(f)

# Export summary to CSV
with open("summary.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Scenario", "Passed", "Score", "Duration"])

    for result in data["results"]:
        writer.writerow([
            result["scenario_name"],
            result["passed"],
            result["score"],
            result["duration_seconds"]
        ])
```

### Creating a Database

```python
import json
import sqlite3

# Connect to database
conn = sqlite3.connect("mcprobe_results.db")
cursor = conn.cursor()

# Create table
cursor.execute("""
CREATE TABLE IF NOT EXISTS results (
    run_id TEXT PRIMARY KEY,
    timestamp TEXT,
    scenario_name TEXT,
    passed BOOLEAN,
    score REAL,
    duration_seconds REAL,
    model_name TEXT,
    git_commit TEXT
)
""")

# Load and insert results
with open("results.json") as f:
    data = json.load(f)

for result in data["results"]:
    cursor.execute("""
    INSERT INTO results VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result["run_id"],
        result["timestamp"],
        result["scenario_name"],
        result["passed"],
        result["score"],
        result["duration_seconds"],
        result["model_name"],
        result.get("git_commit")
    ))

conn.commit()
conn.close()
```

### Jupyter Notebook Analysis

```python
import json
import pandas as pd
import matplotlib.pyplot as plt

# Load results
with open("results.json") as f:
    data = json.load(f)

# Create DataFrame
df = pd.DataFrame(data["results"])

# Plot score distribution
df["score"].hist(bins=20)
plt.xlabel("Score")
plt.ylabel("Frequency")
plt.title("Test Score Distribution")
plt.show()

# Plot pass rate by tag
tags_df = df.explode("scenario_tags")
pass_rate_by_tag = tags_df.groupby("scenario_tags")["passed"].mean()
pass_rate_by_tag.plot(kind="bar")
plt.ylabel("Pass Rate")
plt.title("Pass Rate by Tag")
plt.show()
```

## Programmatic JSON Generation

Generate JSON reports from Python:

```python
from pathlib import Path
from mcprobe.persistence import ResultLoader
from mcprobe.reporting import JsonReportGenerator

# Load results
loader = ResultLoader(Path("test-results"))
results = loader.load_all()

# Generate JSON with conversations
generator = JsonReportGenerator()
generator.generate(
    results=results,
    output_path=Path("full-results.json"),
    include_conversations=True
)

# Generate JSON without conversations (smaller file)
generator.generate(
    results=results,
    output_path=Path("summary-results.json"),
    include_conversations=False
)
```

## Best Practices

### Version Control

**Don't commit large JSON files:**
```bash
# .gitignore
results.json
*-results.json
test-results/*.json
```

**Do commit schemas:**
```bash
git add results-schema.json
```

### File Naming

Use descriptive, timestamped names:

```bash
# Good
results-2025-01-15-production.json
sprint-23-test-results.json

# Avoid
results.json
test.json
```

### Compression

For large exports, compress the JSON:

```bash
# Compress
gzip results.json

# Decompress
gunzip results.json.gz
```

Or in Python:

```python
import gzip
import json

# Write compressed JSON
with gzip.open("results.json.gz", "wt") as f:
    json.dump(data, f, indent=2)

# Read compressed JSON
with gzip.open("results.json.gz", "rt") as f:
    data = json.load(f)
```

### Security

**Avoid including sensitive data:**
- API keys
- Passwords
- Personal information
- Production secrets

Review JSON before sharing externally.

## Troubleshooting

### Large File Sizes

JSON files can become large with conversation data.

**Solutions:**
- Limit results: `--limit 50`
- Exclude conversations (programmatic generation)
- Compress files with gzip
- Use streaming JSON parsers for large files

### Missing Conversation Data

By default, `mcprobe report` includes conversations. If missing:

```bash
# Ensure results were saved during test
pytest scenarios/ --mcprobe-save-results

# Check results directory
ls -la test-results/
```

### Invalid JSON

Validate JSON structure:

```bash
# Using Python
python -m json.tool results.json

# Using jq
jq . results.json
```

## Next Steps

- [HTML Reports](html-reports.md) - Visual report format
- [CI Integration](ci-integration.md) - Using JSON in CI/CD
- [Reporting Overview](overview.md) - Other report formats
