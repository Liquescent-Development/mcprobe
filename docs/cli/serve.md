# MCP Server

MCProbe includes an MCP (Model Context Protocol) server that exposes test results and control capabilities to AI assistants like Claude Code.

## Overview

The `mcprobe serve` command starts an MCP server that allows AI assistants to:

- **Query test results** - View recent runs, conversations, and judgments
- **Analyze trends** - Get pass rates, score trends, and regressions
- **Run tests** - Execute scenarios and get immediate feedback
- **Get suggestions** - Retrieve MCP improvement suggestions from test runs

This enables a powerful workflow where an AI assistant can help you iteratively improve your MCP server based on test feedback.

## Quick Start

### 1. Add MCProbe to Claude Code

The easiest way is using the CLI command:

```bash
claude mcp add --transport stdio mcprobe -- mcprobe serve -r ./test-results -s ./scenarios
```

Or create `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "mcprobe": {
      "type": "stdio",
      "command": "mcprobe",
      "args": ["serve", "-r", "./test-results", "-s", "./scenarios"]
    }
  }
}
```

> **Note:** You don't need to run `mcprobe serve` manually. Claude Code automatically starts the server based on your configuration.

### 2. Verify Configuration

```bash
claude mcp list
```

### 3. Use in Claude Code

Claude Code will automatically start MCProbe when needed and can query your test results. Use `/mcp` to check server status.

## Available Tools

### Discovery Tools

#### `list_scenarios`

Lists all available test scenario files in the scenarios directory.

**Example output:**
```
## Available Scenarios in ./scenarios

- **weather-query**: `weather-query.yaml`
- **greeting-test**: `greeting-test.yaml`
- **complex-workflow**: `advanced/complex-workflow.yaml`
```

#### `list_results`

Lists recent test run results with optional filtering.

**Parameters:**
- `scenario` (optional): Filter by scenario name
- `limit` (default: 10): Maximum results to return

**Example output:**
```
## Recent Test Results

- **Weather Query Test** [PASSED] Score: 0.92 | ID: `abc12345` | 2026-01-21 14:30
- **Weather Query Test** [FAILED] Score: 0.65 | ID: `def67890` | 2026-01-21 14:15

**Summary**: 1/2 passed
```

### Inspection Tools

#### `get_result`

Returns the complete test run result as JSON, including all metadata.

**Parameters:**
- `run_id` (required): The unique identifier of the test run

#### `get_conversation`

Returns a formatted conversation transcript with tool calls and results.

**Parameters:**
- `run_id` (required): The unique identifier of the test run

**Example output:**
```
## Conversation: Weather Query Test
**Run ID**: `abc12345`
**Termination**: criteria_met
**Duration**: 2.5s

### Transcript

**[USER]**: What's the weather in Seattle?

**[ASSISTANT]**: The weather in Seattle is currently sunny and 72°F.
  > Tool: `get_weather`
  > Parameters: {"location": "Seattle"}
  > Result: {"temp": 72, "conditions": "sunny"}
  > Latency: 150ms
```

#### `get_judgment`

Returns the judge's evaluation with pass/fail status, criteria results, and reasoning.

**Parameters:**
- `run_id` (required): The unique identifier of the test run

**Example output:**
```
## Judgment: Weather Query Test
**Run ID**: `abc12345`
**Status**: PASSED
**Score**: 0.92

### Correctness Criteria
  + Mentions Temperature
  + Correct Location

### Judge Reasoning
The agent correctly identified Seattle and provided accurate weather information.

### Quality Metrics
- Clarifications asked: 0
- Backtracks: 0
- Turns to first answer: 1
- Final answer completeness: 95%
```

#### `get_suggestions`

Returns MCP improvement suggestions from the judge's analysis.

**Parameters:**
- `run_id` (required): The unique identifier of the test run

**Example output:**
```
## MCP Improvement Suggestions: Weather Query Test
**Run ID**: `abc12345`

### Structured Suggestions

**DESCRIPTION** (low)
Tool: `get_weather`
Issue: Description could be clearer about supported locations
Suggestion: Add examples of valid location formats

### General Suggestions
- Consider adding a tool for weather alerts
```

### Analysis Tools

#### `get_trends`

Returns trend analysis for a scenario including pass rates and score trends.

**Parameters:**
- `scenario` (required): Name of the scenario to analyze
- `window` (default: 10): Number of recent runs to include

**Example output:**
```
## Trend Analysis: Weather Query Test
**Window**: Last 10 runs

**Pass Rate**: 90%
**Average Score**: 0.88
**Score Trend**: TrendDirection.IMPROVING

### Performance Metrics
- Avg Duration: 2.3s
- Avg Tool Calls: 1.2
- Avg Tokens: 450

### Score Range
- Current: 0.92
- Min: 0.75
- Max: 0.95
- Variance: 0.012
```

#### `get_latest`

Returns the most recent test result with judgment and suggestions.

**Parameters:**
- `scenario` (optional): Filter by scenario name

### Control Tools

#### `run_scenario`

Runs a test scenario and returns the results. **Requires the server to be started with `--config` option.**

**Parameters:**
- `scenario_path` (required): Path to the scenario YAML file (relative to scenarios dir)
- `save_results` (default: true): Whether to save results to the results directory

**Example:**
```
Run weather-query.yaml and tell me the results
```

## Enabling Test Execution

To enable the `run_scenario` tool, you must provide a configuration file:

### 1. Create mcprobe.yaml

```yaml
llm:
  provider: ollama
  model: llama3.2
  base_url: http://localhost:11434

orchestrator:
  max_turns: 10
```

### 2. Start Server with Config

```bash
mcprobe serve -r ./test-results -s ./scenarios -c ./mcprobe.yaml
```

### 3. Update Claude Code Config

```json
{
  "mcpServers": {
    "mcprobe": {
      "command": "mcprobe",
      "args": ["serve", "-r", "./test-results", "-s", "./scenarios", "-c", "./mcprobe.yaml"]
    }
  }
}
```

## Example Workflow

Here's an example of using MCProbe with Claude Code to improve an MCP server:

1. **Run initial tests**
   ```
   You: Run the weather-query scenario
   Claude: [Calls run_scenario] The test passed with a score of 0.85...
   ```

2. **Review suggestions**
   ```
   You: What improvements does the judge suggest?
   Claude: [Calls get_suggestions] The judge suggests improving the tool description...
   ```

3. **Make improvements and retest**
   ```
   You: I've updated the tool description. Run the test again.
   Claude: [Calls run_scenario] The test now passes with a score of 0.95!
   ```

4. **Check trends**
   ```
   You: How is this scenario trending over time?
   Claude: [Calls get_trends] The pass rate has improved from 70% to 95%...
   ```

## Troubleshooting

### Server Won't Start

- Ensure you have MCProbe installed: `pip install mcprobe`
- Check that the results directory exists or can be created
- Verify the scenarios directory contains YAML files

### run_scenario Returns "Configuration Required"

- Add the `--config` option pointing to your mcprobe.yaml
- Ensure the config file has valid LLM settings

### Tools Not Appearing in Claude Code

- Restart Claude Code after updating mcp.json
- Check Claude Code's MCP server logs for errors
- Verify the mcprobe command is in your PATH

## See Also

- [Claude Code Integration](../integration/claude-code.md) - Complete setup guide for Claude Code
- [CLI Reference](reference.md#mcprobe-serve) - Complete command reference
- [Configuration Reference](../configuration/reference.md) - mcprobe.yaml format
- [Running Tests](run.md) - CLI test execution
