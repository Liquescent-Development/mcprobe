# Scenario Generation Guide

Automatically generate test scenarios from MCP server tool schemas using the `mcprobe generate-scenarios` command.

## Overview

The scenario generator:
1. Connects to an MCP server
2. Extracts tool schemas (names, descriptions, parameters)
3. Uses an LLM to create realistic test scenarios
4. Generates YAML files ready to run

This dramatically reduces the effort needed to create comprehensive test coverage for your MCP server.

## Basic Usage

```bash
mcprobe generate-scenarios --server "SERVER_COMMAND" [OPTIONS]
```

## Connecting to an MCP Server

### Server Command Format

The `--server` option takes the exact command needed to start your MCP server:

**NPM-based servers:**
```bash
mcprobe generate-scenarios \
  --server "npx @modelcontextprotocol/server-weather"
```

**Node servers:**
```bash
mcprobe generate-scenarios \
  --server "node path/to/server.js"
```

**Python servers:**
```bash
mcprobe generate-scenarios \
  --server "python mcp_servers/my_server.py"
```

**Other languages:**
```bash
# Go server
mcprobe generate-scenarios --server "./mcp-server"

# Rust server
mcprobe generate-scenarios --server "cargo run --release"
```

### Server Connection Process

When you run the command, MCProbe:

1. **Starts the server** using the provided command
2. **Establishes MCP connection** via stdio
3. **Requests tool list** using the MCP protocol
4. **Extracts schemas** for all available tools
5. **Closes connection** after extraction

Example output:
```
Connecting to MCP server: npx @modelcontextprotocol/server-weather

Extracting tool schemas...

Found 3 tool(s):
  - get_current_weather: Get current weather for a location
  - get_forecast: Get weather forecast for next 7 days
  - search_locations: Search for locations by name
```

### Troubleshooting Connection Issues

**Server not found:**
```
Error connecting to server: Command not found: npx
```

**Solution**: Ensure the server command is in your PATH
```bash
# For NPX servers
npm install -g @modelcontextprotocol/server-weather

# For Python servers
pip install my-mcp-server

# For custom servers
export PATH=$PATH:/path/to/server
```

**Server fails to start:**
```
Error connecting to server: Server exited with code 1
```

**Solution**: Test the server command independently
```bash
# Run server command directly
npx @modelcontextprotocol/server-weather

# Check for error messages
python my_server.py
```

**No tools found:**
```
Found 0 tool(s)
```

**Solution**: Verify your server implements the MCP tools list endpoint
```python
# Your server should implement:
async def list_tools():
    return [
        Tool(name="my_tool", description="...", parameters=...)
    ]
```

## Output Directory

### Specifying Output Location

Use `--output` to control where scenarios are saved:

```bash
mcprobe generate-scenarios \
  --server "npx @example/server" \
  --output ./my-scenarios
```

Default: `./generated-scenarios`

### Output Structure

Generated scenarios are saved as individual YAML files:

```
./generated-scenarios/
├── weather_query_london.yaml
├── forecast_next_week.yaml
├── search_multiple_cities.yaml
├── error_invalid_location.yaml
└── complex_weather_comparison.yaml
```

Each file contains a complete, runnable scenario.

### Filename Generation

Filenames are created from scenario names:
- Converted to lowercase
- Spaces replaced with underscores
- Special characters removed
- `.yaml` extension added

Example:
- Scenario name: "Weather Query for London"
- Filename: `weather_query_for_london.yaml`

## Complexity Levels

Control the sophistication of generated scenarios with `--complexity`:

```bash
mcprobe generate-scenarios \
  --server "npx @example/server" \
  --complexity LEVEL
```

### Simple

**Characteristics:**
- Single tool usage
- Straightforward queries
- Minimal conversation turns
- Basic success criteria
- No error handling

**Example scenario:**
```yaml
name: Get Current Weather
description: Simple query for current weather

synthetic_user:
  persona: A user wanting current weather
  initial_query: "What's the weather in London?"
  max_turns: 3

evaluation:
  correctness_criteria:
    - Agent called get_current_weather with location
    - Agent returned weather information
```

**Use when:**
- Testing basic tool functionality
- Validating tool discoverability
- Creating smoke tests
- Onboarding new team members

**Command:**
```bash
mcprobe generate-scenarios -s "npx @example/server" -c simple -n 5
```

### Medium (Default)

**Characteristics:**
- Multi-step workflows (2-3 tools)
- Realistic user interactions
- Multiple conversation turns
- Comprehensive evaluation criteria
- Some edge cases

**Example scenario:**
```yaml
name: Weather Forecast Comparison
description: Compare forecasts for two cities

synthetic_user:
  persona: A user planning travel between cities
  initial_query: "I'm traveling from Paris to London next week.
                  How do the forecasts compare?"
  max_turns: 6
  knowledge:
    - The user wants forecasts, not current weather
    - The user cares about travel conditions

evaluation:
  correctness_criteria:
    - Agent retrieved forecasts for both cities
    - Agent made meaningful comparison
    - Agent used search_locations for city lookup
  failure_criteria:
    - Agent only provided one city's forecast
    - Agent confused current weather with forecast
```

**Use when:**
- Testing realistic user workflows
- Validating tool composition
- Creating production test suites
- Measuring agent capabilities

**Command:**
```bash
# Medium is default
mcprobe generate-scenarios -s "npx @example/server" -n 10
```

### Complex

**Characteristics:**
- Multi-tool composition (3+ tools)
- Advanced user personas
- Error handling scenarios
- Ambiguous queries requiring clarification
- Adversarial cases
- Efficiency testing

**Example scenario:**
```yaml
name: Ambiguous Location with Fallback
description: Handle ambiguous location gracefully

synthetic_user:
  persona: A user with an ambiguous query who doesn't know the full name
  initial_query: "What's the weather in Springfield?"
  max_turns: 8
  knowledge:
    - There are multiple cities named Springfield
    - The user actually wants Springfield, Illinois
    - The user will clarify if asked
  clarification_strategy: helpful

evaluation:
  correctness_criteria:
    - Agent recognized ambiguity
    - Agent asked for clarification
    - Agent searched for multiple Springfields
    - Agent provided correct weather after clarification
  failure_criteria:
    - Agent assumed a location without asking
    - Agent gave up when multiple matches found
    - Agent didn't use search_locations
  tool_usage:
    expected_tools:
      - search_locations
      - get_current_weather
    efficiency_threshold: 5  # Max tool calls
```

**Use when:**
- Stress-testing agent reasoning
- Testing error handling
- Validating clarification flows
- Creating comprehensive test suites
- Adversarial testing

**Command:**
```bash
mcprobe generate-scenarios -s "npx @example/server" -c complex -n 15
```

### Complexity Comparison

| Aspect | Simple | Medium | Complex |
|--------|--------|--------|---------|
| Tool calls | 1 | 2-3 | 3+ |
| Turns | 2-3 | 4-6 | 6-10 |
| Clarifications | None | Occasional | Frequent |
| Error cases | No | Some | Yes |
| Ambiguity | None | Low | High |
| Generation time | Fast | Moderate | Slow |

## Controlling Count

Specify how many scenarios to generate with `--count`:

```bash
mcprobe generate-scenarios \
  --server "npx @example/server" \
  --count 20
```

Default: 10

### Recommendations

**Small MCP servers (1-3 tools):**
```bash
# Simple: 3-5 scenarios per tool
mcprobe generate-scenarios -s "..." -c simple -n 10

# Medium: 2-3 scenarios per tool
mcprobe generate-scenarios -s "..." -c medium -n 8

# Complex: 1-2 scenarios per tool
mcprobe generate-scenarios -s "..." -c complex -n 5
```

**Medium MCP servers (4-10 tools):**
```bash
# Simple: 1-2 scenarios per tool
mcprobe generate-scenarios -s "..." -c simple -n 15

# Medium: 1 scenario per tool + compositions
mcprobe generate-scenarios -s "..." -c medium -n 15

# Complex: Select important workflows
mcprobe generate-scenarios -s "..." -c complex -n 10
```

**Large MCP servers (10+ tools):**
```bash
# Focus on critical paths
mcprobe generate-scenarios -s "..." -c medium -n 20
mcprobe generate-scenarios -s "..." -c complex -n 10
```

### Generation Time

Generation time scales with:
- **Count**: Linear scaling
- **Complexity**: Complex scenarios take 2-3x longer than simple
- **Tool count**: More tools = more context for LLM
- **Model**: Faster models generate faster

Approximate times (llama3.2):
- Simple scenario: 5-10 seconds
- Medium scenario: 10-20 seconds
- Complex scenario: 20-40 seconds

For 10 medium scenarios: ~2-3 minutes

## LLM Configuration

### Model Selection

The generation LLM creates the scenario content. Choose based on quality needs:

```bash
mcprobe generate-scenarios \
  --server "npx @example/server" \
  --model llama3.1
```

**Model recommendations:**

**llama3.2** (default)
- Fast generation
- Good for simple/medium scenarios
- May struggle with very complex scenarios

**llama3.1**
- Higher quality scenarios
- Better at complex scenarios
- Slower generation

**qwen2.5**
- Good multilingual scenarios
- Alternative to Llama models

**mistral**
- Fast and capable
- Good balance of speed/quality

### Base URL

Point to your Ollama instance:

```bash
mcprobe generate-scenarios \
  --server "npx @example/server" \
  --model llama3.1 \
  --base-url http://ollama-server:11434
```

Default: `http://localhost:11434`

### Combined LLM Configuration

```bash
mcprobe generate-scenarios \
  --server "npx @modelcontextprotocol/server-weather" \
  --output ./weather-tests \
  --complexity medium \
  --count 15 \
  --model llama3.1 \
  --base-url http://ollama:11434
```

## Generated File Format

Generated scenarios are complete, valid YAML files ready to run.

### Example Generated File

**weather_forecast_planning.yaml:**
```yaml
name: Weather Forecast Planning
description: |
  User planning a trip wants to compare weather forecasts
  for two destinations to decide which to visit.

synthetic_user:
  persona: |
    A person planning a weekend trip who wants to visit the
    location with better weather. Friendly and appreciative
    of helpful information.
  initial_query: |
    I'm planning a weekend trip and trying to decide between
    visiting Seattle or Portland. Can you help me compare the
    weather forecasts?
  max_turns: 6
  knowledge:
    - The trip is next weekend (7 days from now)
    - The user prefers sunny, dry weather
    - The user will appreciate temperature comparisons
  clarification_strategy: helpful

evaluation:
  correctness_criteria:
    - Agent searched for both Seattle and Portland
    - Agent retrieved forecasts for both locations
    - Agent provided a comparison between the two
    - Agent helped the user make a decision
  failure_criteria:
    - Agent only provided one location's forecast
    - Agent provided current weather instead of forecast
    - Agent gave up when asked to compare
  tool_usage:
    expected_tools:
      - search_locations
      - get_forecast
    min_calls: 2
    max_calls: 6
  quality_criteria:
    - Answer is helpful for decision-making
    - Information is well-organized
    - Agent shows understanding of user's goal
```

### File Structure

Generated files include:

**1. Name and Description**
- Clear, descriptive name
- Detailed description of the scenario

**2. Synthetic User**
- Realistic persona
- Natural initial query
- Relevant knowledge and constraints
- Clarification strategy

**3. Evaluation Criteria**
- Correctness criteria (what should happen)
- Failure criteria (what shouldn't happen)
- Tool usage expectations
- Quality criteria

**4. Optional Advanced Fields**
- Expected conversation flow
- Efficiency thresholds
- Multi-turn strategies

## Post-Generation Customization

Generated scenarios are a starting point. Customize them for your needs:

### Review and Refine

```bash
# Generate scenarios
mcprobe generate-scenarios -s "..." -o ./scenarios

# Validate them
mcprobe validate ./scenarios

# Review in your editor
ls ./scenarios
```

### Common Customizations

**1. Adjust max_turns:**
```yaml
synthetic_user:
  max_turns: 6  # Generated default
  max_turns: 10  # Increase for complex flows
  max_turns: 3   # Decrease for simple tests
```

**2. Add specific knowledge:**
```yaml
synthetic_user:
  knowledge:
    - The user is in timezone America/Los_Angeles
    - The user's current location is San Francisco
    - The user has a temperature preference for Celsius
```

**3. Enhance evaluation criteria:**
```yaml
evaluation:
  correctness_criteria:
    - Agent retrieved weather data
    - Agent used metric units  # Add specifics
    - Agent included wind information  # Add requirements
```

**4. Add failure conditions:**
```yaml
evaluation:
  failure_criteria:
    - Agent uses deprecated tool
    - Agent makes more than 10 tool calls
    - Agent doesn't handle errors gracefully
```

**5. Strengthen personas:**
```yaml
synthetic_user:
  persona: |
    A frustrated user who has had bad experiences with
    weather apps in the past. Skeptical but willing to
    try again. Appreciates detailed explanations.
```

### Merging Scenarios

Combine generated scenarios to create more comprehensive tests:

```yaml
# Take the persona from scenario A
synthetic_user:
  persona: From generated-scenarios/persona_a.yaml

  # Take the query from scenario B
  initial_query: From generated-scenarios/query_b.yaml

  # Add custom knowledge
  knowledge:
    - Custom fact 1
    - Custom fact 2
```

### Creating Variants

Generate variants for different conditions:

```bash
# Generate base scenarios
mcprobe generate-scenarios -s "..." -o ./base-scenarios -n 10

# Copy and customize
cp ./base-scenarios/weather_query.yaml ./scenarios/weather_query_celsius.yaml
cp ./base-scenarios/weather_query.yaml ./scenarios/weather_query_fahrenheit.yaml

# Edit each variant
# weather_query_celsius.yaml -> Add "user prefers Celsius"
# weather_query_fahrenheit.yaml -> Add "user prefers Fahrenheit"
```

## Complete Examples

### Example 1: Quick Test Suite

Generate a fast test suite for development:

```bash
mcprobe generate-scenarios \
  --server "npx @modelcontextprotocol/server-weather" \
  --output ./quick-tests \
  --complexity simple \
  --count 5 \
  --model llama3.2

# Run immediately
mcprobe run ./quick-tests
```

### Example 2: Comprehensive Production Suite

Generate thorough tests for CI/CD:

```bash
# Simple scenarios for smoke tests
mcprobe generate-scenarios \
  -s "npx @myorg/mcp-server" \
  -o ./scenarios/smoke \
  -c simple \
  -n 10

# Medium scenarios for integration tests
mcprobe generate-scenarios \
  -s "npx @myorg/mcp-server" \
  -o ./scenarios/integration \
  -c medium \
  -n 20

# Complex scenarios for edge cases
mcprobe generate-scenarios \
  -s "npx @myorg/mcp-server" \
  -o ./scenarios/edge-cases \
  -c complex \
  -n 15

# Validate all
mcprobe validate ./scenarios

# Run full suite
mcprobe run ./scenarios
```

### Example 3: Multi-Server Testing

Generate scenarios for multiple MCP servers:

```bash
# Weather server
mcprobe generate-scenarios \
  -s "npx @modelcontextprotocol/server-weather" \
  -o ./scenarios/weather \
  -c medium \
  -n 10

# Filesystem server
mcprobe generate-scenarios \
  -s "npx @modelcontextprotocol/server-filesystem" \
  -o ./scenarios/filesystem \
  -c medium \
  -n 10

# Custom server
mcprobe generate-scenarios \
  -s "python ./my_server.py" \
  -o ./scenarios/custom \
  -c medium \
  -n 10
```

### Example 4: Iterative Refinement

Generate, test, and refine:

```bash
# 1. Generate initial scenarios
mcprobe generate-scenarios \
  -s "npx @example/server" \
  -o ./scenarios-v1 \
  -c medium \
  -n 10

# 2. Run and identify issues
mcprobe run ./scenarios-v1 -v

# 3. Generate more complex scenarios for problem areas
mcprobe generate-scenarios \
  -s "npx @example/server" \
  -o ./scenarios-v2 \
  -c complex \
  -n 5

# 4. Manually refine based on results
# Edit files in ./scenarios-v2

# 5. Run final suite
mcprobe run ./scenarios-v1 ./scenarios-v2
```

## Best Practices

### Generation Strategy

**1. Start simple, increase complexity:**
```bash
# Phase 1: Validate basic functionality
mcprobe generate-scenarios -s "..." -c simple -n 5
mcprobe run ./generated-scenarios

# Phase 2: Test workflows
mcprobe generate-scenarios -s "..." -c medium -n 10
mcprobe run ./generated-scenarios

# Phase 3: Edge cases
mcprobe generate-scenarios -s "..." -c complex -n 5
mcprobe run ./generated-scenarios
```

**2. Generate in batches:**
```bash
# Don't generate 100 at once
# Instead, generate and review in batches
mcprobe generate-scenarios -s "..." -n 10 -o ./batch-1
# Review ./batch-1
mcprobe generate-scenarios -s "..." -n 10 -o ./batch-2
# Review ./batch-2
```

**3. Use descriptive output directories:**
```bash
mcprobe generate-scenarios -s "..." -o ./scenarios/smoke-tests
mcprobe generate-scenarios -s "..." -o ./scenarios/integration
mcprobe generate-scenarios -s "..." -o ./scenarios/edge-cases
```

### Quality Assurance

**1. Always validate after generation:**
```bash
mcprobe generate-scenarios -s "..." -o ./scenarios
mcprobe validate ./scenarios
```

**2. Review generated scenarios:**
```bash
# Don't blindly run generated scenarios
ls ./generated-scenarios
cat ./generated-scenarios/first-scenario.yaml
# Review and customize as needed
```

**3. Test generated scenarios:**
```bash
# Run a few to ensure quality
mcprobe run ./generated-scenarios/scenario_1.yaml -v
mcprobe run ./generated-scenarios/scenario_2.yaml -v
# If quality is good, run all
mcprobe run ./generated-scenarios
```

### Maintenance

**1. Regenerate periodically:**
```bash
# When your MCP server changes, regenerate
mcprobe generate-scenarios -s "..." -o ./new-scenarios
# Compare with old scenarios
diff ./scenarios ./new-scenarios
```

**2. Version your scenarios:**
```bash
# Keep scenarios in git
git add scenarios/
git commit -m "Add generated test scenarios for weather server v2.1"
```

**3. Document customizations:**
```yaml
# Add comments to customized scenarios
name: Custom Weather Query
description: |
  CUSTOMIZED: This scenario was generated but manually adjusted
  to test specific edge case found in production.
  Original: weather_query.yaml
  Modified: 2024-01-15
```

## Troubleshooting

### Poor Quality Scenarios

**Problem**: Generated scenarios are not realistic or don't test the right things.

**Solutions**:
1. Use a more capable model:
   ```bash
   mcprobe generate-scenarios -s "..." -m llama3.1
   ```

2. Increase complexity for more sophisticated tests:
   ```bash
   mcprobe generate-scenarios -s "..." -c complex
   ```

3. Generate more scenarios and cherry-pick the best:
   ```bash
   mcprobe generate-scenarios -s "..." -n 20
   # Review and keep the best 10
   ```

4. Manually refine generated scenarios

### Repetitive Scenarios

**Problem**: Generated scenarios are too similar.

**Solutions**:
1. Generate in smaller batches:
   ```bash
   mcprobe generate-scenarios -s "..." -n 5 -o ./batch-1
   mcprobe generate-scenarios -s "..." -n 5 -o ./batch-2
   ```

2. Mix complexity levels:
   ```bash
   mcprobe generate-scenarios -s "..." -c simple -n 3
   mcprobe generate-scenarios -s "..." -c medium -n 4
   mcprobe generate-scenarios -s "..." -c complex -n 3
   ```

3. Manually create diversity by editing

### Long Generation Times

**Problem**: Generation takes too long.

**Solutions**:
1. Use a faster model:
   ```bash
   mcprobe generate-scenarios -s "..." -m llama3.2
   ```

2. Reduce complexity:
   ```bash
   mcprobe generate-scenarios -s "..." -c simple
   ```

3. Generate fewer scenarios at once:
   ```bash
   mcprobe generate-scenarios -s "..." -n 5
   ```

4. Check Ollama performance:
   ```bash
   ollama list
   # Ensure model is loaded
   ```

## Next Steps

- [Running Tests](run.md) - Execute your generated scenarios
- [Scenario Format](../scenarios/format.md) - Understand YAML structure
- [Analysis Commands](analysis.md) - Analyze test results
- [Evaluation Criteria](../scenarios/evaluation.md) - Refine evaluation logic
