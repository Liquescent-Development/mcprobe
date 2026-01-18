# Installation Guide

This guide walks you through installing MCProbe and its dependencies.

## Prerequisites

### Python 3.11 or Higher

MCProbe requires Python 3.11 or later. Check your Python version:

```bash
python --version
```

If you need to install or upgrade Python, visit [python.org](https://www.python.org/downloads/).

### LLM Provider

MCProbe requires an LLM provider for the synthetic user and judge. Choose one:

#### Option 1: Ollama (Recommended for Local Testing)

For running tests locally with open-source models, install Ollama:

**macOS**:
```bash
brew install ollama
```

**Linux**:
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows**:
Download from [ollama.ai](https://ollama.ai/download)

Start the Ollama service:
```bash
ollama serve
```

#### Option 2: OpenAI

For cloud-based LLM inference:

```bash
# Set your API key
export OPENAI_API_KEY="sk-your-key-here"

# No additional installation needed
```

The OpenAI provider works with:
- OpenAI API (gpt-4, gpt-3.5-turbo, etc.)
- Azure OpenAI (requires custom base_url)
- vLLM (self-hosted inference)
- LiteLLM (multi-provider gateway)
- Ollama (via OpenAI-compatible API mode)
- Any other OpenAI-compatible endpoint

See [Configuration Reference](../configuration/reference.md) for detailed provider setup.

## Installing MCProbe

### Basic Installation

Install MCProbe using pip:

```bash
pip install mcprobe
```

This installs the core framework with support for:
- Ollama-based LLM providers (synthetic users and judges)
- Simple agent testing
- YAML scenario parsing
- CLI commands

### Optional Dependencies

#### Gemini ADK Support

If you want to test agents built with Google's Agent Development Kit (ADK) and MCP servers:

```bash
pip install mcprobe[adk]
```

This adds:
- `google-adk>=1.22.0` for Gemini-powered agents
- MCP server integration through ADK

#### HTML Reporting

For generating rich HTML test reports:

```bash
pip install mcprobe[reporting]
```

This adds:
- `jinja2>=3.1` for HTML template rendering

#### Install All Extras

To install everything:

```bash
pip install mcprobe[adk,reporting]
```

### Development Installation

If you're contributing to MCProbe or want to run from source:

```bash
# Clone the repository
git clone https://github.com/Liquescent-Development/mcprobe.git
cd mcprobe

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[adk,reporting,dev]"
```

## Verifying Installation

Check that MCProbe is installed correctly:

```bash
mcprobe --help
```

You should see output showing available commands:

```
Usage: mcprobe [OPTIONS] COMMAND [ARGS]...

  Conversational MCP server testing framework.

Commands:
  run                Run test scenarios against the agent.
  validate           Validate scenario YAML files without running them.
  providers          List available LLM providers.
  generate-scenarios Generate test scenarios from MCP tool schemas.
  report             Generate a report from stored test results.
  trends             Show trend analysis for test scenarios.
  flaky              Detect flaky (inconsistent) test scenarios.
  stability-check    Check stability of a specific scenario.
```

## Setting Up Ollama

MCProbe uses Ollama by default for local LLM inference. Here's how to set it up:

### 1. Start Ollama Service

If not already running:

```bash
ollama serve
```

Leave this running in a terminal window. The service listens on `http://localhost:11434` by default.

### 2. Pull a Model

Download a model for running tests. We recommend starting with `llama3.2`:

```bash
ollama pull llama3.2
```

This downloads the Llama 3.2 model (about 2GB). The model is used for:
- Synthetic user simulation
- Conversation judgment
- Simple agent responses (when testing without MCP)

### 3. Verify Ollama Setup

Test that Ollama is working:

```bash
ollama list
```

You should see `llama3.2` in the output.

### Alternative Models

MCProbe works with any Ollama model. Other recommended options:

- **llama3.2:1b** - Faster, lighter (1GB)
- **llama3.1:8b** - More capable (4.7GB)
- **qwen2.5:7b** - Good reasoning (4.4GB)

Specify a different model when running tests:

```bash
mcprobe run scenario.yaml --model llama3.1:8b
```

## Using Cloud LLM Providers

While Ollama is the default for local testing, MCProbe supports cloud LLM providers for the synthetic user, judge, and agent.

### OpenAI

MCProbe includes built-in support for OpenAI and OpenAI-compatible endpoints:

```bash
# Set your API key
export OPENAI_API_KEY="sk-your-key-here"

# Run tests with OpenAI
mcprobe run scenario.yaml --provider openai --model gpt-4
```

The OpenAI provider also works with:
- **Azure OpenAI**: Use custom `base_url` in configuration
- **vLLM**: Self-hosted inference server with OpenAI API compatibility
- **LiteLLM**: Unified interface to multiple LLM providers
- **Ollama (OpenAI mode)**: Use Ollama via OpenAI-compatible API

See the [Configuration Reference](../configuration/reference.md) for examples of each setup.

### Gemini ADK Agents

To test agents that use Google's Gemini models with MCP servers:

```bash
# Install ADK support
pip install mcprobe[adk]

# Set up your agent factory (see Advanced Integration docs)
mcprobe run scenario.yaml --agent-type adk --agent-factory my_agent.py
```

You'll need a Google Cloud API key. Set it as an environment variable:

```bash
export GOOGLE_API_KEY="your-api-key"
```

### Custom Provider Configuration

For advanced setups with custom LLM providers, see the [Integration Guide](../integration/custom-agents.md).

## Configuration

MCProbe can be configured via configuration files, command-line options, or environment variables.

### Configuration Files

Create a `mcprobe.yaml` file for centralized configuration:

```yaml
# mcprobe.yaml
llm:
  provider: ollama
  model: llama3.2
  base_url: http://localhost:11434
  temperature: 0.0

orchestrator:
  max_turns: 10
  turn_timeout_seconds: 30.0

results:
  save: true
  dir: test-results
```

MCProbe automatically discovers config files in the current directory:

```bash
# Uses mcprobe.yaml if present
mcprobe run scenario.yaml
```

Or specify an explicit config file:

```bash
mcprobe run scenario.yaml --config mcprobe.yaml
```

See [Configuration Reference](../configuration/reference.md) for complete documentation including:
- Environment variable interpolation (`${VAR}` syntax)
- Component-specific configs (separate settings for judge vs synthetic user)
- Multiple provider configurations

### Environment Variables

```bash
# Ollama base URL (default: http://localhost:11434)
export OLLAMA_BASE_URL="http://localhost:11434"

# OpenAI API key (required for OpenAI provider)
export OPENAI_API_KEY="sk-your-key-here"
```

Environment variables can be used in config files:

```yaml
# mcprobe.yaml
llm:
  provider: openai
  model: gpt-4
  api_key: ${OPENAI_API_KEY}
  base_url: ${OPENAI_BASE_URL:-https://api.openai.com/v1}
```

### Command-Line Options

Override defaults when running tests:

```bash
mcprobe run scenario.yaml \
  --provider openai \
  --model gpt-4 \
  --verbose
```

CLI options override config file settings.

## Troubleshooting

### "Connection refused" when running tests

**Cause**: Ollama service is not running.

**Solution**: Start Ollama in a separate terminal:
```bash
ollama serve
```

### "Model not found" error

**Cause**: The specified model hasn't been downloaded.

**Solution**: Pull the model first:
```bash
ollama pull llama3.2
```

### Import errors with ADK

**Cause**: ADK extras not installed.

**Solution**: Install with ADK support:
```bash
pip install mcprobe[adk]
```

### Slow test execution

**Causes**:
- Large model (e.g., 70B parameter models)
- No GPU acceleration
- Network latency to cloud providers

**Solutions**:
- Use a smaller model: `--model llama3.2:1b`
- Enable GPU support in Ollama (see [Ollama GPU docs](https://github.com/ollama/ollama/blob/main/docs/gpu.md))
- Use local Ollama instead of remote/cloud LLMs for synthetic user and judge

## Next Steps

Now that MCProbe is installed, continue to the [Quickstart Guide](quickstart.md) to run your first test scenario.
