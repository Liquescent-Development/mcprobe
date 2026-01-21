# Claude Code Integration

This guide explains how to integrate MCProbe with [Claude Code](https://claude.ai/code), enabling AI-assisted development and testing of MCP servers.

## Overview

Claude Code is Anthropic's CLI tool that brings Claude's capabilities to your terminal. By connecting MCProbe as an MCP server, you can:

- **Query test results** directly in conversation with Claude
- **Analyze failures** and get suggestions for fixing issues
- **Run tests** and see results without leaving your editor
- **Track trends** to identify regressions over time
- **Iterate quickly** on MCP server improvements with AI guidance

## Prerequisites

1. **Claude Code installed** - Follow [Claude Code installation instructions](https://claude.ai/code)
2. **MCProbe installed** - `pip install mcprobe` or `uv add mcprobe`
3. **Test results directory** - Run some tests first with `mcprobe run`

## Configuration

### Step 1: Locate Your MCP Configuration

Claude Code stores MCP server configurations in `~/.claude/mcp.json`. Create this file if it doesn't exist:

```bash
mkdir -p ~/.claude
touch ~/.claude/mcp.json
```

### Step 2: Add MCProbe Server

Edit `~/.claude/mcp.json` to add MCProbe:

```json
{
  "mcpServers": {
    "mcprobe": {
      "command": "mcprobe",
      "args": ["serve", "-r", "./test-results", "-s", "./scenarios"]
    }
  }
}
```

**Configuration options:**

| Argument | Description |
|----------|-------------|
| `-r, --results-dir` | Directory containing test results (default: `./test-results`) |
| `-s, --scenarios-dir` | Directory containing scenario files (default: `.`) |
| `-c, --config` | Path to mcprobe.yaml (required for running tests) |

### Step 3: Enable Test Execution (Optional)

To allow Claude to run tests, add a config file reference:

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

Your `mcprobe.yaml` should contain LLM settings:

```yaml
llm:
  provider: ollama
  model: llama3.2
  base_url: http://localhost:11434

orchestrator:
  max_turns: 10
```

### Step 4: Restart Claude Code

After updating `mcp.json`, restart Claude Code to load the new server:

```bash
# If using Claude Code CLI
claude --restart

# Or simply start a new session
claude
```

## Usage Examples

Once configured, you can interact with MCProbe naturally in Claude Code:

### Viewing Test Results

```
You: Show me the recent test results

Claude: [Calls list_results]
Here are your recent test results:

- **Weather Query Test** [PASSED] Score: 0.92 | 2024-01-21 14:30
- **Search API Test** [FAILED] Score: 0.45 | 2024-01-21 14:15
- **Greeting Test** [PASSED] Score: 0.98 | 2024-01-21 14:00

Summary: 2/3 passed
```

### Investigating Failures

```
You: Why did the Search API Test fail?

Claude: [Calls get_judgment with the run ID]
The Search API Test failed because:

### Correctness Criteria
  - Search Returns Results (FAILED)
  + Query Parameter Accepted

### Judge Reasoning
The agent attempted to use the search tool but received an empty result set.
The tool description doesn't specify how to handle pagination...
```

### Getting Improvement Suggestions

```
You: What does the judge suggest for improving the MCP server?

Claude: [Calls get_suggestions]
Based on the test analysis, here are suggestions:

**DESCRIPTION** (medium)
Tool: `search`
Issue: Description doesn't explain pagination
Suggestion: Add documentation about limit/offset parameters

**RETURN_VALUE** (low)
Tool: `search`
Issue: Empty results return unclear format
Suggestion: Return explicit empty array with metadata
```

### Running Tests

```
You: Run the weather-query scenario and show me the results

Claude: [Calls run_scenario]
Running weather-query.yaml...

**Result: PASSED** (Score: 0.95)

### Correctness Criteria
  + Returns Temperature
  + Correct Location
  + Includes Conditions

The agent successfully retrieved and presented the weather information.
```

### Tracking Trends

```
You: How is the Weather Query Test trending?

Claude: [Calls get_trends]
## Trend Analysis: Weather Query Test

**Pass Rate**: 95% (↑ improving)
**Average Score**: 0.91
**Last 10 runs**: 9 passed, 1 failed

The test has improved since last week when we updated the tool description.
```

## Workflow: Iterative MCP Development

Here's a recommended workflow for developing MCP servers with Claude Code:

### 1. Generate Initial Scenarios

```bash
mcprobe generate-scenarios -s "npx your-mcp-server" -o ./scenarios
```

### 2. Run Initial Tests

```bash
mcprobe run ./scenarios --config mcprobe.yaml
```

### 3. Analyze Results with Claude

```
You: Analyze the test results and identify the main issues

Claude: [Reviews results and provides analysis]
```

### 4. Implement Fixes

```
You: Can you help me improve the get_weather tool description based on the feedback?

Claude: Based on the judge's suggestions, here's an improved description...
```

### 5. Re-test and Verify

```
You: Run the weather tests again to verify the fix

Claude: [Runs tests and shows improved results]
```

### 6. Track Progress

```
You: Show me the trend for weather tests over the last week

Claude: [Shows improvement trend]
```

## Project-Specific Configuration

For project-specific settings, create `.claude/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "mcprobe": {
      "command": "mcprobe",
      "args": [
        "serve",
        "-r", "./test-results",
        "-s", "./scenarios",
        "-c", "./mcprobe.yaml"
      ]
    }
  }
}
```

This allows different projects to have different MCProbe configurations.

## Available Tools

Claude has access to these MCProbe tools:

| Tool | Description | Use Case |
|------|-------------|----------|
| `list_scenarios` | List scenario files | See what tests are available |
| `list_results` | List recent results | Get overview of test history |
| `get_result` | Get full result by ID | Deep dive into specific run |
| `get_conversation` | Get conversation transcript | See exactly what happened |
| `get_judgment` | Get judge evaluation | Understand pass/fail reasons |
| `get_suggestions` | Get improvement suggestions | Learn how to fix issues |
| `get_trends` | Get trend analysis | Track progress over time |
| `get_latest` | Get most recent result | Quick status check |
| `run_scenario` | Execute a test | Run tests on demand |

## Troubleshooting

### Server Not Appearing

1. Verify `mcp.json` syntax is valid JSON
2. Check that `mcprobe` is in your PATH: `which mcprobe`
3. Restart Claude Code after config changes

### "Configuration Required" Error

The `run_scenario` tool requires a config file. Add `-c ./mcprobe.yaml` to your args.

### Results Not Found

Ensure the results directory exists and contains test results:
```bash
ls -la ./test-results/
```

### Connection Issues

Check that MCProbe can start:
```bash
mcprobe serve -r ./test-results -s ./scenarios
# Should start without errors (Ctrl+C to stop)
```

### Viewing Server Logs

Claude Code logs MCP server output. Check for errors in Claude Code's logs or run MCProbe directly to debug.

## Best Practices

1. **Run tests before starting Claude Code** - Ensure you have results to analyze
2. **Use project-specific configs** - Keep settings with your project
3. **Include the config file** - Enable test execution for the full workflow
4. **Commit your scenarios** - Version control your test definitions
5. **Review trends regularly** - Catch regressions early

## See Also

- [MCP Server Reference](../cli/serve.md) - Complete serve command documentation
- [CLI Reference](../cli/reference.md#mcprobe-serve) - All MCProbe commands
- [Configuration Reference](../configuration/reference.md) - mcprobe.yaml format
