# Running Test Scenarios

Comprehensive guide to running MCProbe test scenarios using the `mcprobe run` command.

## Basic Usage

The `run` command executes test scenarios against your agent under test:

```bash
mcprobe run SCENARIO_PATH [OPTIONS]
```

## Running Scenarios

### Single Scenario File

Run a specific scenario file:

```bash
mcprobe run scenarios/weather-query.yaml
```

Output:
```
Found 1 scenario(s)
Agent type: simple

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Weather Query Test                            ┃
┃ Test agent can query weather information      ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Running conversation...

Result: PASSED (score: 0.92)
Reasoning: The agent successfully retrieved weather information
and provided a complete answer to the user's question.

Test Summary
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━┓
┃ Scenario           ┃ Status ┃ Score ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━┩
│ Weather Query Test │  PASS  │  0.92 │
└────────────────────┴────────┴───────┘

Total: 1/1 passed
```

### Directory of Scenarios

Run all scenario files in a directory:

```bash
mcprobe run scenarios/
```

MCProbe will:
1. Discover all `.yaml` files in the directory
2. Parse and validate each scenario
3. Execute them sequentially
4. Display a summary table with all results

```
Found 5 scenario(s)
Agent type: simple

[Runs each scenario...]

Test Summary
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━┓
┃ Scenario             ┃ Status ┃ Score ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━┩
│ Weather Query Test   │  PASS  │  0.92 │
│ Greeting Test        │  PASS  │  0.98 │
│ Error Handling       │  FAIL  │  0.45 │
│ Multi-Step Task      │  PASS  │  0.87 │
│ Tool Composition     │  PASS  │  0.91 │
└──────────────────────┴────────┴───────┘

Total: 4/5 passed
```

## Model Configuration

### Selecting a Model

MCProbe uses an LLM for both the synthetic user and the judge. By default, it uses `llama3.2`, but you can specify any model available in your Ollama instance:

```bash
mcprobe run scenarios/greeting.yaml --model llama3.1
```

Popular model choices:
- `llama3.2` (default) - Fast, good for most scenarios
- `llama3.1` - More capable for complex scenarios
- `mistral` - Alternative open-source model
- `qwen2.5` - Good multilingual support

### Base URL Configuration

If you're running Ollama on a different host or port, specify the base URL:

```bash
mcprobe run scenarios/ --base-url http://ollama-server:11434
```

Common scenarios:
- **Local Ollama**: `http://localhost:11434` (default)
- **Docker Ollama**: `http://ollama:11434`
- **Remote server**: `http://192.168.1.100:11434`

### Combined Model Configuration

```bash
mcprobe run scenarios/ \
  --model llama3.1 \
  --base-url http://ollama-server:11434
```

## Agent Types

MCProbe supports two types of agents under test:

### Simple LLM Agent (Default)

A basic LLM-based agent powered by Ollama. This is the default agent type and doesn't have access to MCP tools.

```bash
mcprobe run scenarios/greeting.yaml
# Equivalent to:
mcprobe run scenarios/greeting.yaml --agent-type simple
```

Use this for:
- Testing conversational behavior without tools
- Baseline comparisons
- Simple greeting/response scenarios
- Situations where no MCP server is needed

**See [Simple Agent Guide](../agents/simple-agent.md) for complete documentation.**

### ADK Agent with MCP Tools

An agent built with Google's Agent Development Kit (ADK) that has access to MCP tools via HTTP. Requires an agent factory module.

```bash
mcprobe run scenarios/ --agent-type adk --agent-factory my_agent.py
```

**See [ADK Agent Guide](../agents/adk-agent.md) for complete documentation.**

#### Creating an Agent Factory

Your agent factory module must export a `create_agent()` function that returns an `LlmAgent` instance:

**my_agent.py:**
```python
import os
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.genai.types import GenerateContentConfig

def create_agent():
    """Create and return an ADK LlmAgent instance."""
    # Configure MCP connection
    connection_params = StreamableHTTPConnectionParams(
        url=os.environ.get("MCP_URL", "http://localhost:8080/mcp"),
        headers={"Authorization": f"Bearer {os.environ.get('MCP_TOKEN', 'dev')}"},
    )

    # Create MCP toolset
    toolset = McpToolset(connection_params=connection_params)

    # Create agent
    return LlmAgent(
        model="gemini-2.0-flash",
        name="test_agent",
        description="Agent for testing MCP server",
        instruction="Use available tools to answer questions accurately.",
        tools=[toolset],
        generate_content_config=GenerateContentConfig(temperature=0.1),
    )
```

Then run:
```bash
export GOOGLE_API_KEY="your-api-key"
export MCP_URL="http://localhost:8080/mcp"
mcprobe run scenarios/ -t adk -f my_agent.py
```

#### Agent Factory Requirements

Your factory module:
- Must be a valid Python module (`.py` file)
- Must define a `create_agent()` function with no parameters
- The function must return a `google.adk.agents.LlmAgent` instance
- Should use environment variables for configuration
- Must connect to MCP server via HTTP (not stdio)

#### Short Form Options

```bash
# Short form for readability
mcprobe run scenarios/ -t adk -f my_agent.py

# Long form for clarity
mcprobe run scenarios/ --agent-type adk --agent-factory my_agent.py
```

## Verbose Output

Enable detailed output with the `--verbose` flag to see:
- Complete conversation transcripts
- Tool call details (name, parameters)
- Per-criterion evaluation results
- Quality metrics
- Efficiency statistics
- Structured improvement suggestions

```bash
mcprobe run scenarios/complex-task.yaml --verbose
```

Example verbose output:

```
Found 1 scenario(s)
Agent type: simple

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Complex Task                                  ┃
┃ Multi-step task requiring tool composition   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Running conversation...

Result: PASSED (score: 0.87)
Reasoning: Successfully completed all steps with appropriate tool usage.

Conversation:
[USER]: I need the weather forecast for Paris next week
[ASSISTANT]: I'll help you get the weather forecast for Paris.
  -> search_locations({'query': 'Paris'})
  -> get_forecast({'location_id': '12345', 'days': 7})
[ASSISTANT]: Here's the forecast for Paris for the next 7 days...

Correctness:
  Agent retrieved weather data: PASS
  Agent provided complete forecast: PASS
  Agent used appropriate tools: PASS

Failure Conditions:
  Agent gave up prematurely: OK
  Agent provided incorrect information: OK
  Agent failed to use available tools: OK

Quality Metrics:
  Clarifications: 0
  Backtracks: 0
  Turns to first answer: 2
  Answer completeness: 100%

Efficiency:
  Total tokens: 1247
  Tool calls: 2
  Turns: 3

MCP Improvement Suggestions:
  [medium] tool_description: search_locations
    Issue: Tool description doesn't mention it returns location IDs
    Suggestion: Add explicit note that the tool returns location_id
                needed for other weather tools
```

## Understanding Output

### Status Indicators

- `PASSED` (green) - Scenario passed all correctness criteria
- `FAILED` (red) - Scenario failed one or more criteria or triggered failure conditions

### Score Interpretation

The score (0.0 to 1.0) represents overall conversation quality:
- **0.90-1.00**: Excellent - Agent handled task optimally
- **0.80-0.89**: Good - Agent completed task with minor issues
- **0.70-0.79**: Acceptable - Agent completed task but inefficiently
- **0.60-0.69**: Poor - Agent struggled but eventually succeeded
- **Below 0.60**: Failing - Significant issues or incomplete task

The judge considers:
- **Correctness** (60% weight): Did the agent satisfy all criteria?
- **Efficiency** (20% weight): Did the agent use reasonable resources?
- **Quality** (20% weight): Was the conversation natural and appropriate?

### Reasoning

The judge provides natural language reasoning explaining the score and identifying:
- What the agent did well
- What could be improved
- Specific issues encountered
- Tool usage effectiveness

### Suggestions

When available, MCProbe provides actionable suggestions:

**General suggestions** - Natural language recommendations from the judge

**Structured suggestions** - Specific MCP improvement recommendations with:
- **Severity**: low, medium, high
- **Category**: tool_description, parameter_schema, error_handling, etc.
- **Tool name**: Which tool needs improvement
- **Issue**: What the problem is
- **Suggestion**: How to fix it

Example:
```
Suggestions:
  - Consider adding examples to tool descriptions
  - The search_locations tool could return more structured data

MCP Improvement Suggestions:
  [high] parameter_schema: search_locations
    Issue: Parameter 'query' has no description or examples
    Suggestion: Add description and example values for the query parameter
```

## Exit Codes and Error Handling

### Exit Codes

MCProbe uses standard exit codes:

```bash
mcprobe run scenarios/test.yaml
echo $?  # Check exit code
```

- **0**: All scenarios passed successfully
- **1**: One or more scenarios failed, or a command error occurred

### Common Errors

**Invalid agent configuration:**
```bash
mcprobe run scenarios/ -t adk
# Error: --agent-factory is required for ADK agent type
```

Solution: Provide the agent factory module:
```bash
mcprobe run scenarios/ -t adk -f my_agent.py
```

**Unknown agent type:**
```bash
mcprobe run scenarios/ -t unknown
# Error: Unknown agent type: unknown
```

Solution: Use `simple` or `adk`:
```bash
mcprobe run scenarios/ -t simple
```

**Scenario parsing errors:**
```bash
mcprobe run bad-scenario.yaml
# Error: Missing required field 'synthetic_user' in bad-scenario.yaml
```

Solution: Validate your scenario first:
```bash
mcprobe validate bad-scenario.yaml
```

**Connection errors:**
```bash
mcprobe run scenarios/ -u http://wrong-host:11434
# Error: Failed to connect to LLM provider
```

Solution: Check your Ollama instance is running:
```bash
# Check if Ollama is running
ollama list

# Or start Ollama
ollama serve
```

### Error Recovery

When a scenario fails:

1. **Review the reasoning**: The judge explains what went wrong
2. **Use verbose mode**: Get detailed conversation transcript
   ```bash
   mcprobe run failing-scenario.yaml -v
   ```
3. **Check suggestions**: Look for MCP improvement recommendations
4. **Validate the scenario**: Ensure it's properly formatted
   ```bash
   mcprobe validate failing-scenario.yaml
   ```
5. **Test incrementally**: Start with simpler scenarios

## Best Practices

### Running Tests Efficiently

**1. Start with validation:**
```bash
# Validate before running
mcprobe validate scenarios/
mcprobe run scenarios/
```

**2. Use appropriate models:**
```bash
# Fast model for development
mcprobe run scenarios/ -m llama3.2

# Capable model for final testing
mcprobe run scenarios/ -m llama3.1
```

**3. Test incrementally:**
```bash
# Test one scenario first
mcprobe run scenarios/greeting.yaml

# Then run the suite
mcprobe run scenarios/
```

**4. Use verbose mode for debugging:**
```bash
# Normal run
mcprobe run scenarios/

# Debug failing scenario
mcprobe run scenarios/failing-test.yaml -v
```

### CI/CD Integration

For continuous integration:

```bash
#!/bin/bash
set -e  # Exit on error

# Validate scenarios
mcprobe validate scenarios/

# Run tests
mcprobe run scenarios/ \
  --model llama3.2 \
  --base-url http://ollama:11434

# Generate report
mcprobe report --format junit --output test-results.xml
```

Exit code will be non-zero if any tests fail, failing the CI build.

### Performance Considerations

**Model selection impacts:**
- **llama3.2**: Faster, less expensive, good for most tests
- **llama3.1**: Slower, more capable, better for complex scenarios

**Parallel execution:**
MCProbe runs scenarios sequentially. For parallel execution:
```bash
# Split scenarios into directories
mcprobe run scenarios/set1/ &
mcprobe run scenarios/set2/ &
wait
```

**Agent reset:**
The agent is automatically reset between scenarios to ensure isolation.

## Advanced Usage

### Custom Agent Factories

Create sophisticated agent configurations:

```python
# advanced_agent.py
from google.adk.agents import Agent
from google.adk.llms import VertexAI

def create_agent():
    """Create an agent with custom configuration."""
    llm = VertexAI(
        model="gemini-2.0-flash-exp",
        temperature=0.7,
        max_tokens=2048
    )

    agent = Agent(
        llm=llm,
        mcp_servers=[
            "npx @modelcontextprotocol/server-weather",
            "python mcp_servers/custom_server.py"
        ],
        system_instruction="""You are a helpful weather assistant.
        Always check multiple sources when possible."""
    )

    return agent
```

### Testing Multiple Configurations

Test with different models:
```bash
for model in llama3.2 llama3.1 mistral; do
  echo "Testing with $model"
  mcprobe run scenarios/ -m $model
done
```

Test with different agents:
```bash
# Test simple agent
mcprobe run scenarios/ -t simple

# Test ADK agent
mcprobe run scenarios/ -t adk -f my_agent.py
```

### Scenario Filtering

Run specific scenario patterns:
```bash
# Run only weather scenarios
mcprobe run scenarios/weather-*.yaml

# Run scenarios in a subdirectory
mcprobe run scenarios/critical/
```

## Troubleshooting

### No scenarios found

```
No scenarios found.
```

**Cause**: Directory is empty or contains no `.yaml` files

**Solution**: Check your scenario path
```bash
ls scenarios/
mcprobe validate scenarios/
```

### Agent factory errors

```
Error: Failed to load agent factory from my_agent.py
```

**Causes**:
- Module not found
- No `create_agent()` function
- Function raises an exception

**Solution**: Test your factory module
```python
# Test it directly
python -c "from my_agent import create_agent; agent = create_agent(); print(agent)"
```

### Performance issues

If scenarios run very slowly:

1. **Check model**: Larger models are slower
2. **Check Ollama**: Ensure it's not CPU-throttled
3. **Simplify scenarios**: Reduce max_turns for testing
4. **Use appropriate hardware**: LLMs need reasonable compute

## Next Steps

- [Scenario Generation](generate.md) - Auto-generate scenarios from MCP servers
- [Analysis Commands](analysis.md) - Analyze trends and detect flaky tests
- [Scenario Format](../scenarios/format.md) - Learn YAML scenario structure
- [Evaluation Criteria](../scenarios/evaluation.md) - Define success criteria
