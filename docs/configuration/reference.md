# Configuration Reference

This document provides detailed information about all configuration options available in MCProbe.

## Overview

MCProbe configuration consists of three main components:
- **LLM Configuration**: Settings for language model providers
- **Orchestrator Configuration**: Conversation flow control settings
- **MCProbe Configuration**: Complete system configuration combining all components

Configuration can be provided through:
1. CLI arguments (highest priority)
2. Environment variables
3. Default values (lowest priority)

## LLMConfig

Configuration for an LLM provider used by the agent, synthetic user, or judge.

**Import Path**: `mcprobe.models.config.LLMConfig`

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `provider` | `str` | Yes | - | Provider name (e.g., "ollama", "openai") |
| `model` | `str` | Yes | - | Model identifier (e.g., "llama3.2", "gpt-4") |
| `temperature` | `float` | No | `0.0` | Sampling temperature (0.0-2.0) |
| `max_tokens` | `int` | No | `4096` | Maximum tokens in response |
| `api_key` | `SecretStr \| None` | No | `None` | API key for authentication |
| `base_url` | `str \| None` | No | `None` | Base URL for API endpoint |

### Validation Rules

- `provider`: Must be non-empty string
- `model`: Must be non-empty string
- `temperature`: Must be between 0.0 and 2.0 (inclusive)
- `max_tokens`: Must be at least 1
- `api_key`: Stored as SecretStr for security (won't be logged or printed)

### Example

```python
from mcprobe.models.config import LLMConfig

# Ollama configuration
ollama_config = LLMConfig(
    provider="ollama",
    model="llama3.2",
    temperature=0.0,
    max_tokens=4096,
    base_url="http://localhost:11434"
)

# OpenAI configuration
openai_config = LLMConfig(
    provider="openai",
    model="gpt-4",
    temperature=0.7,
    max_tokens=2048,
    api_key="sk-..."
)
```

## OrchestratorConfig

Configuration for the conversation orchestrator that manages the interaction between the synthetic user and agent.

**Import Path**: `mcprobe.models.config.OrchestratorConfig`

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `max_turns` | `int` | No | `10` | Maximum conversation turns before timeout |
| `turn_timeout_seconds` | `float` | No | `30.0` | Timeout for each turn in seconds |
| `loop_detection_threshold` | `int` | No | `3` | Number of identical user messages before loop detection |

### Validation Rules

- `max_turns`: Must be at least 1
- `turn_timeout_seconds`: Must be greater than 0
- `loop_detection_threshold`: Must be at least 2

### Example

```python
from mcprobe.models.config import OrchestratorConfig

orchestrator_config = OrchestratorConfig(
    max_turns=20,
    turn_timeout_seconds=60.0,
    loop_detection_threshold=3
)
```

## MCProbeConfig

Global configuration combining all MCProbe components.

**Import Path**: `mcprobe.models.config.MCProbeConfig`

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `agent` | `LLMConfig` | Yes | - | Configuration for the agent under test |
| `synthetic_user` | `LLMConfig` | Yes | - | Configuration for the synthetic user |
| `judge` | `LLMConfig` | Yes | - | Configuration for the judge |
| `orchestrator` | `OrchestratorConfig` | No | `OrchestratorConfig()` | Orchestrator configuration |

### Example

```python
from mcprobe.models.config import MCProbeConfig, LLMConfig, OrchestratorConfig

config = MCProbeConfig(
    agent=LLMConfig(
        provider="ollama",
        model="llama3.2",
        base_url="http://localhost:11434"
    ),
    synthetic_user=LLMConfig(
        provider="ollama",
        model="llama3.2",
        base_url="http://localhost:11434"
    ),
    judge=LLMConfig(
        provider="ollama",
        model="llama3.2",
        base_url="http://localhost:11434"
    ),
    orchestrator=OrchestratorConfig(
        max_turns=15,
        turn_timeout_seconds=45.0
    )
)
```

## Environment Variables

MCProbe supports configuration via environment variables. These are provider-specific and typically used for API keys and base URLs.

### Ollama

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_BASE_URL` | Base URL for Ollama API | `http://localhost:11434` |

### OpenAI

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | - |
| `OPENAI_BASE_URL` | OpenAI API base URL | `https://api.openai.com/v1` |

### Usage

```bash
export OLLAMA_BASE_URL=http://localhost:11434
export OPENAI_API_KEY=sk-your-key-here

mcprobe run scenario.yaml
```

## Configuration Precedence

MCProbe follows this precedence order when resolving configuration values:

1. **CLI Arguments** (highest priority)
   - `--model`, `--base-url`, etc.

2. **Environment Variables**
   - Provider-specific variables like `OLLAMA_BASE_URL`

3. **Default Values** (lowest priority)
   - Built-in defaults from Pydantic models

### Example

```bash
# Environment variable sets default
export OLLAMA_BASE_URL=http://ollama-server:11434

# CLI argument overrides environment variable
mcprobe run scenario.yaml --base-url http://localhost:11434
# Result: Uses http://localhost:11434
```

## Common Configuration Patterns

### Development Setup

For local development with Ollama:

```bash
mcprobe run scenario.yaml \
  --model llama3.2 \
  --base-url http://localhost:11434 \
  --agent-type simple
```

### CI/CD Setup

For automated testing with remote Ollama:

```bash
export OLLAMA_BASE_URL=http://ollama-service:11434
mcprobe run scenarios/ --model llama3.2 --agent-type simple
```

### ADK Agent Setup

For testing Gemini ADK agents with MCP tools:

```bash
mcprobe run scenario.yaml \
  --agent-type adk \
  --agent-factory my_agent_factory.py \
  --model llama3.2 \
  --base-url http://localhost:11434
```

Note: The `--model` and `--base-url` are used for the synthetic user and judge, not the ADK agent.

### Custom Temperature and Tokens

```python
from mcprobe.models.config import LLMConfig

# More creative responses
creative_config = LLMConfig(
    provider="ollama",
    model="llama3.2",
    temperature=0.8,  # Higher temperature for more variation
    max_tokens=8192   # More tokens for longer responses
)

# Deterministic responses
deterministic_config = LLMConfig(
    provider="ollama",
    model="llama3.2",
    temperature=0.0,  # Zero temperature for consistent results
    max_tokens=2048
)
```

## Related Documentation

- [Architecture Overview](../architecture/overview.md) - System architecture and component interactions
- [API Reference](../api/reference.md) - Programmatic API documentation
- [CLI Reference](../cli/README.md) - Command-line interface documentation
