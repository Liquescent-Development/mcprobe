# Pytest Integration Guide

MCProbe includes a powerful pytest plugin that enables seamless integration with your existing testing workflows. The plugin automatically discovers scenario files and runs them as standard pytest tests.

## Installation

The pytest plugin is automatically available when you install MCProbe:

```bash
pip install mcprobe
```

No additional configuration is needed. The plugin is automatically registered via pytest's entry points system.

## Running Scenarios

### Basic Usage

Run all scenarios in a directory:

```bash
pytest scenarios/
```

Run a specific scenario file:

```bash
pytest scenarios/weather_basic.yaml
```

### Using Configuration Files

MCProbe automatically discovers `mcprobe.yaml` or `.mcprobe.yaml` files in the current directory:

```bash
# Auto-discovers config file
pytest scenarios/
```

Or specify an explicit config file:

```bash
pytest scenarios/ --mcprobe-config mcprobe.yaml
```

Example `mcprobe.yaml`:

```yaml
agent:
  type: adk  # or "simple"
  factory: my_agent_factory.py  # required for ADK agents

llm:
  provider: ollama
  model: llama3.2
  base_url: http://localhost:11434

results:
  save: true
  dir: test-results
```

**Note:** The `agent:` section is optional - it defaults to `type: simple` if not specified.

### Overriding Configuration

CLI arguments override configuration file settings:

```bash
# Config file has provider: ollama, but override to openai
pytest scenarios/ --mcprobe-config mcprobe.yaml --mcprobe-provider openai
```

### Verbose Output

Use pytest's `-v` flag for detailed test output:

```bash
pytest scenarios/ -v
```

For even more detail, use `-vv`:

```bash
pytest scenarios/ -vv
```

## Configuration Options

MCProbe adds several pytest command-line options for configuring test execution:

### `--mcprobe-config`

Specify the path to an mcprobe.yaml configuration file. If not provided, MCProbe will auto-discover configuration files in the current directory.

```bash
pytest scenarios/ --mcprobe-config mcprobe.yaml
```

**Default:** Auto-discovery (checks for `mcprobe.yaml`, `.mcprobe.yaml`, etc.)

### `--mcprobe-provider`

Specify the LLM provider to use. Common values are `ollama`, `openai`. This overrides the configuration file setting.

```bash
pytest scenarios/ --mcprobe-provider openai
```

**Default:** From config file, or `ollama` if no config

### `--mcprobe-model`

Specify the LLM model to use for the synthetic user and judge components. This overrides the configuration file setting.

```bash
pytest scenarios/ --mcprobe-model llama3.2
```

**Default:** From config file, or `llama3.2` if no config

### `--mcprobe-base-url`

Set the base URL for the LLM API server. This overrides the configuration file setting.

```bash
pytest scenarios/ --mcprobe-base-url http://localhost:11434
```

**Default:** From config file, or provider-specific default

### `--mcprobe-agent-type`

Choose the type of agent to test. Options are:
- `simple`: Simple LLM-based agent (default)
- `adk`: Gemini ADK agent with MCP tools (requires `--mcprobe-agent-factory`)

```bash
pytest scenarios/ --mcprobe-agent-type simple
```

**Can also be set in config file:**
```yaml
agent:
  type: adk
```

**Default:** `simple`

### `--mcprobe-agent-factory`

Path to Python module with `create_agent()` function. Required when using `--mcprobe-agent-type adk`.

```bash
pytest scenarios/ --mcprobe-agent-type adk --mcprobe-agent-factory my_agent.py
```

**Can also be set in config file:**
```yaml
agent:
  type: adk
  factory: my_agent_factory.py
```

**Default:** None

### `--mcprobe-save-results`

Save test results for trend analysis and reporting. This is enabled by default.

```bash
pytest scenarios/ --mcprobe-save-results
```

**Default:** From config file, or `True` if no config

To disable result saving:

```bash
pytest scenarios/ --mcprobe-no-save-results
```

### `--mcprobe-results-dir`

Specify the directory where test results should be saved.

```bash
pytest scenarios/ --mcprobe-results-dir ./my-results
```

**Default:** From config file, or `test-results` if no config

## Tag Filtering with Markers

Scenario tags are automatically converted into pytest markers, enabling powerful filtering capabilities.

### Filtering by Tag

If your scenarios have tags like this:

```yaml
name: Weather Basic
tags:
  - weather
  - basic
```

You can filter tests using pytest's `-m` option:

```bash
# Run only scenarios tagged with 'weather'
pytest scenarios/ -m weather

# Run scenarios tagged with 'basic'
pytest scenarios/ -m basic

# Combine tags with boolean logic
pytest scenarios/ -m "weather and basic"

# Exclude specific tags
pytest scenarios/ -m "not slow"
```

### Using Keyword Expressions

You can also filter by scenario names using `-k`:

```bash
# Run scenarios with 'weather' in the name
pytest scenarios/ -k weather

# Combine multiple keywords
pytest scenarios/ -k "weather or filesystem"

# Exclude by name
pytest scenarios/ -k "not integration"
```

## Parallel Execution

MCProbe scenarios can be run in parallel using [pytest-xdist](https://pytest-xdist.readthedocs.io/):

### Installation

```bash
pip install pytest-xdist
```

### Usage

Run scenarios across multiple CPUs:

```bash
# Auto-detect number of CPUs
pytest scenarios/ -n auto

# Use specific number of workers
pytest scenarios/ -n 4
```

### Important Notes

- Each worker runs scenarios independently
- Results are still saved correctly
- Some scenarios may have timing dependencies that don't work well in parallel

## CI/CD Integration

### GitHub Actions

Complete workflow example:

```yaml
name: MCProbe Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  mcprobe-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install mcprobe pytest

      - name: Install Ollama
        run: curl -fsSL https://ollama.com/install.sh | sh

      - name: Start Ollama
        run: |
          ollama serve &
          sleep 5

      - name: Pull model
        run: ollama pull llama3.2

      - name: Run scenarios
        run: |
          pytest scenarios/ -v --junit-xml=scenario-results.xml

      - name: Upload results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: scenario-results
          path: |
            scenario-results.xml
            test-results/
```

### GitLab CI

```yaml
mcprobe:
  image: python:3.12
  before_script:
    - pip install mcprobe pytest
    - curl -fsSL https://ollama.com/install.sh | sh
    - ollama serve &
    - sleep 5
    - ollama pull llama3.2
  script:
    - pytest scenarios/ -v --junit-xml=scenario-results.xml
  artifacts:
    when: always
    reports:
      junit: scenario-results.xml
    paths:
      - test-results/
```

### Jenkins

```groovy
pipeline {
    agent any
    stages {
        stage('Setup') {
            steps {
                sh 'pip install mcprobe pytest'
                sh 'curl -fsSL https://ollama.com/install.sh | sh'
                sh 'ollama serve &'
                sh 'sleep 5'
                sh 'ollama pull llama3.2'
            }
        }
        stage('Test') {
            steps {
                sh 'pytest scenarios/ -v --junit-xml=scenario-results.xml'
            }
        }
    }
    post {
        always {
            junit 'scenario-results.xml'
            archiveArtifacts artifacts: 'test-results/**', allowEmptyArchive: true
        }
    }
}
```

## Combining with Other Pytest Plugins

MCProbe works seamlessly with other pytest plugins:

### pytest-cov (Code Coverage)

```bash
pip install pytest-cov
pytest scenarios/ --cov=myagent --cov-report=html
```

### pytest-timeout (Test Timeouts)

```bash
pip install pytest-timeout
pytest scenarios/ --timeout=300
```

### pytest-html (HTML Reports)

```bash
pip install pytest-html
pytest scenarios/ --html=report.html --self-contained-html
```

## Available Fixtures

While MCProbe scenarios are self-contained, the plugin provides access to test results programmatically:

### Accessing Results in Custom Plugins

You can create custom pytest plugins that access MCProbe results:

```python
# conftest.py
from mcprobe.pytest_plugin.plugin import get_mcprobe_results

def pytest_runtest_makereport(item, call):
    if call.when == "call":
        results = get_mcprobe_results(item)
        if results:
            # Access conversation, judgment, and scenario data
            print(f"Score: {results['judgment'].score}")
            print(f"Passed: {results['judgment'].passed}")
```

## Example Workflows

### Development Workflow

Quick testing during development:

```bash
# Run specific scenarios
pytest scenarios/weather_basic.yaml -v

# Run with filters
pytest scenarios/ -m "not slow" -v

# Run in parallel for speed
pytest scenarios/ -n auto
```

### CI/CD Workflow

Comprehensive testing in CI with config file (recommended):

```yaml
# mcprobe.yaml
agent:
  type: ${AGENT_TYPE:-simple}
  factory: ${AGENT_FACTORY}  # optional, for ADK agents

llm:
  provider: ${CI_LLM_PROVIDER:-ollama}
  model: ${CI_LLM_MODEL:-llama3.2}
  base_url: ${CI_LLM_BASE_URL:-http://localhost:11434}

results:
  save: true
  dir: test-results
```

```bash
# Run all scenarios with full reporting
pytest scenarios/ \
  -v \
  --junit-xml=results.xml \
  --mcprobe-config mcprobe.yaml
```

Or without config file (more verbose):

```bash
# Run all scenarios with full reporting
pytest scenarios/ \
  -v \
  --junit-xml=results.xml \
  --mcprobe-agent-type simple \
  --mcprobe-provider ollama \
  --mcprobe-model llama3.2 \
  --mcprobe-base-url http://localhost:11434 \
  --mcprobe-save-results \
  --mcprobe-results-dir ./test-results
```

### Regression Testing

Compare results over time:

```bash
# Run tests and save results
pytest scenarios/ --mcprobe-save-results

# Analyze trends
mcprobe trends --window 20

# Check for flaky scenarios
mcprobe flaky --min-runs 5
```

## Troubleshooting

### Plugin Not Found

If pytest doesn't recognize MCProbe scenarios, verify installation:

```bash
pytest --version
pip show mcprobe
```

### Results Not Saving

Ensure the results directory is writable:

```bash
mkdir -p test-results
chmod 755 test-results
pytest scenarios/ --mcprobe-results-dir ./test-results
```

### Ollama Connection Issues

Verify Ollama is running:

```bash
curl http://localhost:11434/api/tags
```

If using a different URL:

```bash
pytest scenarios/ --mcprobe-base-url http://your-ollama-server:11434
```

## Next Steps

- [Reporting Overview](../reporting/overview.md) - Learn about generating reports
- [CI Integration](../reporting/ci-integration.md) - Deep dive into CI/CD integration
- [HTML Reports](../reporting/html-reports.md) - Create beautiful HTML reports
