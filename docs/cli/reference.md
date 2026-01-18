# CLI Reference

Complete reference for all MCProbe command-line interface commands.

## Synopsis

```bash
mcprobe [COMMAND] [OPTIONS] [ARGS]
```

## Global Options

MCProbe is built on [Typer](https://typer.tiangolo.com/) and supports standard help options:

- `--help` - Show help message for any command
- `--version` - Display MCProbe version

## Commands Overview

| Command | Description |
|---------|-------------|
| [run](#mcprobe-run) | Run test scenarios against an agent |
| [validate](#mcprobe-validate) | Validate scenario YAML files |
| [generate-scenarios](#mcprobe-generate-scenarios) | Generate scenarios from MCP schemas |
| [report](#mcprobe-report) | Generate reports from test results |
| [trends](#mcprobe-trends) | Show trend analysis for scenarios |
| [flaky](#mcprobe-flaky) | Detect flaky (inconsistent) tests |
| [stability-check](#mcprobe-stability-check) | Check stability of a scenario |
| [providers](#mcprobe-providers) | List available LLM providers |

---

## mcprobe run

Execute test scenarios against the agent under test.

### Synopsis

```bash
mcprobe run SCENARIO_PATH [OPTIONS]
```

### Description

Runs one or more test scenarios, using a synthetic user to converse with the agent and a judge to evaluate the results. Can execute a single scenario file or all scenarios in a directory.

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `SCENARIO_PATH` | Path | Yes | Path to scenario YAML file or directory containing scenarios |

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--config` | `-c` | Path | None | Path to mcprobe.yaml configuration file (auto-discovers if not specified) |
| `--provider` | `-p` | string | `ollama` | LLM provider: 'ollama', 'openai', etc. (overrides config file) |
| `--model` | `-m` | string | `llama3.2` | Model name for LLM components (synthetic user and judge) (overrides config file) |
| `--base-url` | `-u` | string | None | Base URL for LLM API (overrides config file) |
| `--agent-type` | `-t` | string | `simple` | Agent type: 'simple' (LLM) or 'adk' (Gemini ADK with MCP) (can be set in config file via `agent.type`) |
| `--agent-factory` | `-f` | Path | None | Path to Python module with create_agent() function (required for 'adk' type) (can be set in config file via `agent.factory`) |
| `--verbose` | `-v` | flag | False | Enable verbose output including full conversation and detailed metrics |

### Examples

**Run a single scenario with default settings:**
```bash
mcprobe run scenarios/weather-query.yaml
```

**Run all scenarios in a directory:**
```bash
mcprobe run scenarios/
```

**Use a configuration file:**
```bash
mcprobe run scenarios/ --config mcprobe.yaml
```

**Use a specific provider and model:**
```bash
mcprobe run scenarios/greeting.yaml --provider openai --model gpt-4
```

**Use a specific model and base URL:**
```bash
mcprobe run scenarios/greeting.yaml -m llama3.1 -u http://ollama-server:11434
```

**Override config file with CLI arguments:**
```bash
# Config file sets provider to ollama, but override to openai
mcprobe run scenarios/ -c mcprobe.yaml -p openai -m gpt-4
```

**Run with verbose output:**
```bash
mcprobe run scenarios/complex-query.yaml -v
```

**Test an ADK agent with MCP tools (using CLI arguments):**
```bash
mcprobe run scenarios/ -t adk -f my_agent_factory.py
```

**Test an ADK agent with MCP tools (using config file - recommended):**
```yaml
# mcprobe.yaml
agent:
  type: adk
  factory: my_agent_factory.py

llm:
  provider: ollama
  model: llama3.2
```
```bash
mcprobe run scenarios/
```

**Use environment variables in config:**
```bash
# mcprobe.yaml contains: api_key: ${OPENAI_API_KEY}
export OPENAI_API_KEY=sk-your-key
mcprobe run scenarios/ --config mcprobe.yaml
```

### Output

The command displays:
- Number of scenarios found
- Agent type being tested
- For each scenario:
  - Scenario name and description
  - Pass/fail status with score
  - Judge reasoning
  - Suggestions for improvement (if any)
- Summary table with all results

In verbose mode, also shows:
- Complete conversation transcript
- Detailed tool call parameters
- Per-criterion correctness results
- Failure condition checks
- Quality metrics (clarifications, backtracks, etc.)
- Efficiency metrics (tokens, tool calls, turns)
- Structured MCP improvement suggestions

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All scenarios passed successfully |
| 1 | One or more scenarios failed, or command error |

---

## mcprobe validate

Validate scenario YAML files without running them.

### Synopsis

```bash
mcprobe validate SCENARIO_PATH
```

### Description

Checks that scenario files are properly formatted and contain all required fields. Does not execute the scenarios or connect to any LLM services.

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `SCENARIO_PATH` | Path | Yes | Path to scenario YAML file or directory to validate |

### Examples

**Validate a single scenario:**
```bash
mcprobe validate scenarios/greeting.yaml
```

**Validate all scenarios in a directory:**
```bash
mcprobe validate scenarios/
```

### Output

On success:
```
Validated 5 scenario(s) successfully.
  - Simple Greeting Test
  - Weather Query Test
  - Multi-Step Task
  - Error Handling
  - Tool Composition
```

On failure:
```
Validation failed: Missing required field 'synthetic_user' in scenario.yaml
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All scenarios are valid |
| 1 | One or more scenarios failed validation |

---

## mcprobe generate-scenarios

Generate test scenarios from MCP tool schemas.

### Synopsis

```bash
mcprobe generate-scenarios --server SERVER_COMMAND [OPTIONS]
```

### Description

Connects to an MCP server, extracts tool schemas, and automatically generates test scenarios based on the specified complexity level. Uses an LLM to create realistic user personas, queries, and evaluation criteria.

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--server` | `-s` | string | Required | MCP server command (e.g., 'npx @example/weather-mcp') |
| `--output` | `-o` | Path | `./generated-scenarios` | Output directory for generated scenarios |
| `--complexity` | `-c` | string | `medium` | Complexity level: simple, medium, or complex |
| `--count` | `-n` | int | 10 | Number of scenarios to generate |
| `--model` | `-m` | string | `llama3.2` | Model for generation |
| `--base-url` | `-u` | string | `http://localhost:11434` | Base URL for Ollama API |

### Complexity Levels

- **simple**: Single-tool scenarios with straightforward queries
- **medium**: Multi-step scenarios that may require 2-3 tool calls
- **complex**: Advanced scenarios with tool composition, error handling, and edge cases

### Examples

**Generate 10 medium-complexity scenarios:**
```bash
mcprobe generate-scenarios -s "npx @modelcontextprotocol/server-weather" -o ./scenarios
```

**Generate simple scenarios for testing:**
```bash
mcprobe generate-scenarios -s "npx @example/my-mcp-server" -c simple -n 5
```

**Generate complex scenarios with a specific model:**
```bash
mcprobe generate-scenarios -s "npx @example/server" -c complex -n 20 -m llama3.1
```

**Generate from a local server script:**
```bash
mcprobe generate-scenarios -s "python my_mcp_server.py" -o ./test-scenarios
```

### Output

```
Connecting to MCP server: npx @example/weather-mcp

Found 3 tool(s):
  - get_current_weather: Get current weather for a location
  - get_forecast: Get weather forecast
  - search_locations: Search for locations by name

Generating 10 scenario(s) at medium complexity...

Generated 10 scenario(s)
  Created: ./generated-scenarios/weather_query_london.yaml
  Created: ./generated-scenarios/forecast_next_week.yaml
  ...

Scenarios written to ./generated-scenarios
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Scenarios generated successfully |
| 1 | Failed to connect to server or generate scenarios |

---

## mcprobe report

Generate a report from stored test results.

### Synopsis

```bash
mcprobe report [OPTIONS]
```

### Description

Reads test results from the results directory and generates a report in the specified format (HTML, JSON, or JUnit XML).

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--results-dir` | `-d` | Path | `test-results` | Directory containing test results |
| `--output` | `-o` | Path | `report.html` | Output file path for the report |
| `--format` | `-f` | string | `html` | Report format: html, json, or junit |
| `--title` | `-t` | string | `MCProbe Test Report` | Title for the report |
| `--limit` | `-n` | int | 100 | Maximum number of results to include |

### Report Formats

- **html**: Interactive HTML report with charts and detailed breakdowns
- **json**: Machine-readable JSON format for custom processing
- **junit**: JUnit XML format for CI/CD integration

### Examples

**Generate HTML report:**
```bash
mcprobe report --format html --output report.html
```

**Generate JUnit XML for CI:**
```bash
mcprobe report --format junit --output test-results.xml --title "MCProbe CI Tests"
```

**Generate JSON report with custom limit:**
```bash
mcprobe report --format json --output results.json --limit 50
```

**Use a different results directory:**
```bash
mcprobe report -d ./my-results -f html -o my-report.html
```

### Output

```
Found 42 test result(s)
Report generated: report.html
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Report generated successfully or no results found |
| 1 | Results directory not found or invalid format specified |

---

## mcprobe trends

Show trend analysis for test scenarios.

### Synopsis

```bash
mcprobe trends [OPTIONS]
```

### Description

Analyzes historical test results to detect trends in pass rates and scores over time. Helps identify regressions, improvements, and performance patterns.

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--scenario` | `-s` | string | None | Scenario name to analyze (all scenarios if not specified) |
| `--window` | `-w` | int | 10 | Number of recent runs to consider |
| `--results-dir` | `-d` | Path | `test-results` | Directory containing test results |

### Examples

**Show trends for all scenarios:**
```bash
mcprobe trends
```

**Analyze a specific scenario with larger window:**
```bash
mcprobe trends --scenario "Weather Query Test" --window 20
```

**Use custom results directory:**
```bash
mcprobe trends -d ./historical-results -w 30
```

### Output

```
Trend Analysis
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Scenario            ┃ Runs ┃ Pass Rate ┃ Pass Trend ┃ Avg Score ┃ Score Trend ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Weather Query Test  │   20 │       95% │     ↑      │      0.92 │      →      │
│ Greeting Test       │   20 │      100% │     →      │      0.98 │      ↑      │
│ Error Handling      │   15 │       80% │     ↓      │      0.75 │      ↓      │
└─────────────────────┴──────┴───────────┴────────────┴───────────┴─────────────┘

⚠ Detected Regressions:
  [high] Error Handling: pass_rate dropped 15.0%
  [medium] Error Handling: avg_score dropped 12.5%
```

### Trend Indicators

- `↑` - Improving trend (statistically significant improvement)
- `↓` - Degrading trend (statistically significant degradation)
- `→` - Stable trend (no significant change)

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Trend analysis completed successfully or insufficient data |
| 1 | Results directory not found |

---

## mcprobe flaky

Detect flaky (inconsistent) test scenarios.

### Synopsis

```bash
mcprobe flaky [OPTIONS]
```

### Description

Identifies scenarios with inconsistent pass/fail results or high score variance, indicating potential flakiness in the test or system under test.

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--min-runs` | `-n` | int | 5 | Minimum runs required for analysis |
| `--results-dir` | `-d` | Path | `test-results` | Directory containing test results |
| `--fail-on-flaky` | | flag | False | Exit with error code if flaky tests are detected |

### Examples

**Detect flaky scenarios:**
```bash
mcprobe flaky
```

**Require more runs for analysis:**
```bash
mcprobe flaky --min-runs 10
```

**Use in CI to fail builds with flaky tests:**
```bash
mcprobe flaky --min-runs 5 --fail-on-flaky
```

### Output

When flaky tests are detected:
```
Flaky Scenarios
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Scenario           ┃ Pass Rate ┃ Runs ┃ Severity ┃ Reason                     ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Weather Query      │       60% │   10 │   high   │ Pass rate in flaky range   │
│ Complex Workflow   │       90% │   15 │  medium  │ High score variance        │
└────────────────────┴───────────┴──────┴──────────┴────────────────────────────┘

Found 2 flaky scenario(s)
```

When no flaky tests are detected:
```
No flaky scenarios detected.
```

### Flakiness Detection

MCProbe considers a scenario flaky if:
- Pass rate is between 20% and 80% (neither consistently passing nor failing)
- Score has high variance (standard deviation > 0.15)
- Results show inconsistent patterns over time

### Severity Levels

- **high**: Pass rate between 30-70% or very high score variance
- **medium**: Pass rate between 20-30% or 70-80%, moderate variance
- **low**: Borderline cases with slight inconsistency

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No flaky scenarios detected |
| 1 | Flaky scenarios detected (only when `--fail-on-flaky` is used) or results directory not found |

---

## mcprobe stability-check

Check stability of a specific scenario.

### Synopsis

```bash
mcprobe stability-check SCENARIO_NAME [OPTIONS]
```

### Description

Returns detailed stability metrics for a specified scenario, including pass rate, mean score, and score variance.

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `SCENARIO_NAME` | string | Yes | Name of scenario to check |

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--min-runs` | `-n` | int | 5 | Minimum runs required for analysis |
| `--results-dir` | `-d` | Path | `test-results` | Directory containing test results |

### Examples

**Check stability of a scenario:**
```bash
mcprobe stability-check "Weather Query Test"
```

**Require more runs for analysis:**
```bash
mcprobe stability-check "Complex Workflow" --min-runs 10
```

### Output

For a stable scenario:
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

For an unstable scenario:
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

For insufficient data:
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Stability Check: New Test     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Insufficient data for stability analysis
Run count: 3 (need at least 5)
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Check completed (regardless of stability result) |
| 1 | Results directory not found |

---

## mcprobe providers

List available LLM providers.

### Synopsis

```bash
mcprobe providers
```

### Description

Displays all registered LLM providers that can be used with MCProbe. Currently used for informational purposes.

### Examples

```bash
mcprobe providers
```

### Output

```
Available Providers
┏━━━━━━━━━━┓
┃ Provider ┃
┡━━━━━━━━━━┩
│ ollama   │
└──────────┘
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Always successful |

---

## Environment Variables

MCProbe supports environment variables in two ways:

### 1. Provider-Specific Variables

Some LLM providers use environment variables for configuration:

| Variable | Provider | Description | Default |
|----------|----------|-------------|---------|
| `OPENAI_API_KEY` | openai | OpenAI API key | Required for OpenAI |
| `OLLAMA_BASE_URL` | ollama | Ollama server URL | `http://localhost:11434` |

### 2. Configuration File Interpolation

Environment variables can be used in configuration files with `${VAR}` or `${VAR:-default}` syntax:

```yaml
# mcprobe.yaml
llm:
  provider: ${LLM_PROVIDER:-ollama}
  model: ${LLM_MODEL:-llama3.2}
  api_key: ${OPENAI_API_KEY}  # Required if not set
  base_url: ${OLLAMA_BASE_URL:-http://localhost:11434}  # Optional with default
```

## Configuration Files

MCProbe supports YAML configuration files for centralized configuration:

### File Names

MCProbe automatically discovers configuration files in this order:
- `mcprobe.yaml`
- `.mcprobe.yaml`
- `mcprobe.yml`
- `.mcprobe.yml`

### File Location

Configuration files are discovered in:
1. Explicit path via `--config` option
2. Current working directory

### File Format

```yaml
# Agent configuration (system under test)
agent:
  type: adk  # or "simple"
  factory: my_agent_factory.py  # required for ADK agents

# Shared LLM configuration (for judge and synthetic user)
llm:
  provider: ollama
  model: llama3.2
  base_url: http://localhost:11434
  temperature: 0.0
  max_tokens: 4096

# Component-specific overrides
judge:
  provider: openai
  model: gpt-4
  api_key: ${OPENAI_API_KEY}

synthetic_user:
  provider: ollama
  model: llama3.2

# Orchestrator settings
orchestrator:
  max_turns: 10
  turn_timeout_seconds: 30.0
  loop_detection_threshold: 3

# Results storage
results:
  save: true
  dir: test-results
```

**Important:** The `agent:` section configures the system being tested, while `llm:`, `judge:`, and `synthetic_user:` configure the MCProbe evaluation components. ADK agents use Gemini internally regardless of the `llm:` settings.

### Configuration Priority

1. **CLI arguments** (highest priority)
2. **Component-specific config** (`judge:`, `synthetic_user:`)
3. **Shared LLM config** (`llm:`)
4. **Environment variables**
5. **Default values** (lowest priority)

See [Configuration Reference](../configuration/reference.md) for complete documentation.

## See Also

- [Running Tests](run.md) - Detailed guide for the `run` command
- [Generating Scenarios](generate.md) - Scenario generation guide
- [Analysis Commands](analysis.md) - Trends, flaky detection, and reporting
- [Scenario Format](../scenarios/format.md) - YAML scenario specification
