# MCProbe

A conversational testing framework for MCP (Model Context Protocol) servers. MCProbe validates that MCP servers provide sufficient information for LLM agents to answer real-world questions correctly, using synthetic users and LLM judges.

## Features

- **Scenario-Based Testing**: Define test scenarios in YAML with synthetic user personas and evaluation criteria
- **Synthetic Users**: Configurable user personas with different patience levels, expertise, and communication styles
- **Automated Evaluation**: LLM-based judge evaluates correctness, tool usage, and efficiency
- **Multiple Agent Types**: Test simple LLM agents or Gemini ADK agents with MCP tools
- **Trend Analysis**: Track test performance over time and detect regressions
- **Flaky Detection**: Identify inconsistent tests automatically
- **CI/CD Integration**: pytest plugin, JUnit XML reports, GitHub Actions support
- **Scenario Generation**: Auto-generate test scenarios from MCP server tool schemas

## Quick Start

### Installation

```bash
pip install mcprobe
```

For Gemini ADK agent support:
```bash
pip install mcprobe[adk]
```

### Prerequisites

MCProbe requires an LLM for the synthetic user and judge. By default, it uses Ollama:

```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama and pull a model
ollama serve
ollama pull llama3.2
```

### Create a Scenario

Create `test-scenario.yaml`:

```yaml
name: Weather Query Test
description: Test that the agent can answer weather questions

synthetic_user:
  persona: A user planning a weekend trip
  initial_query: What's the weather like in San Francisco this weekend?
  max_turns: 5

evaluation:
  correctness_criteria:
    - Agent provides weather information for San Francisco
    - Response includes temperature or conditions
```

### Run the Test

```bash
mcprobe run test-scenario.yaml
```

### View Results

```
Result: PASSED (score: 0.85)
Reasoning: The agent successfully provided weather information...
```

## Documentation

- [Getting Started](docs/getting-started/installation.md)
- [Quickstart Guide](docs/getting-started/quickstart.md)
- [Writing Scenarios](docs/scenarios/format.md)
- [CLI Reference](docs/cli/reference.md)
- [pytest Integration](docs/pytest/integration.md)
- [Analysis & Reporting](docs/reporting/overview.md)

## CLI Commands

```bash
# Run scenarios
mcprobe run scenarios/              # Run all scenarios in directory
mcprobe run scenario.yaml -v        # Run with verbose output

# Generate scenarios from MCP server
mcprobe generate-scenarios --server "npx @example/weather-mcp" -o ./scenarios

# Generate reports
mcprobe report --format html --output report.html

# Analyze trends
mcprobe trends --window 20
mcprobe flaky --fail-on-flaky

# Validate scenarios
mcprobe validate scenarios/
```

## pytest Integration

MCProbe includes a pytest plugin for seamless test integration:

```bash
# Run scenarios as pytest tests
pytest scenarios/ -v

# Save results for analysis
pytest scenarios/ --mcprobe-save-results

# Filter by tags
pytest scenarios/ -m smoke
```

## Example Scenario

```yaml
name: Multi-City Weather Comparison
description: Test comparing weather across multiple cities

synthetic_user:
  persona: A business traveler deciding between meeting locations
  initial_query: Compare the weather in New York, Chicago, and Miami for next Tuesday
  max_turns: 8
  clarification_behavior:
    known_facts:
      - Meeting is scheduled for next Tuesday
      - Prefer outdoor lunch if weather permits
    traits:
      patience: medium
      verbosity: concise
      expertise: intermediate

evaluation:
  correctness_criteria:
    - Provides weather for all three cities
    - Includes temperature information
    - Makes a recommendation based on weather
  failure_criteria:
    - Provides weather for wrong cities
    - Gives conflicting information
  tool_usage:
    required_tools:
      - get_weather
  efficiency:
    max_tool_calls: 5
```

## Development

```bash
# Clone and install
git clone https://github.com/Liquescent-Development/mcprobe.git
cd mcprobe
uv venv
source .venv/bin/activate
uv sync --all-extras

# Run tests
pytest tests/unit/ -v

# Lint and type check
ruff check src/
mypy src/
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- [Full Documentation](docs/index.md)
- [Technical Specification](docs/SPEC.md)
- [GitHub Repository](https://github.com/Liquescent-Development/mcprobe)
