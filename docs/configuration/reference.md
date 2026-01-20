# Configuration Reference

This document provides detailed information about all configuration options available in MCProbe.

## Overview

MCProbe configuration consists of four main components:
- **Agent Configuration**: Settings for the agent under test (the system being tested)
- **LLM Configuration**: Settings for language model providers (judge and synthetic user)
- **Orchestrator Configuration**: Conversation flow control settings
- **MCProbe Configuration**: Complete system configuration combining all components

### Understanding Component Roles

MCProbe has a clear separation between the **system under test** and the **testing components**:

- **Agent Under Test** (`agent:` section): The MCP server/agent you are testing. This is the subject of the evaluation.
  - Simple agents use the synthetic_user LLM configuration
  - ADK agents use their own internal LLM (Gemini) - NOT configurable via MCProbe config

- **MCProbe Testing Components** (configured via `llm:`, `judge:`, `synthetic_user:` sections):
  - **Judge**: Evaluates the conversation quality and correctness
  - **Synthetic User**: Simulates realistic user behavior and questions
  - These components use configurable LLM providers (Ollama, OpenAI, etc.)

This separation allows you to:
- Test a Gemini-based ADK agent using an OpenAI judge and Ollama synthetic user
- Mix and match providers for cost optimization (e.g., expensive models for judging, cheaper for synthetic users)
- Use different providers for different components based on their strengths

Configuration can be provided through:
1. **CLI arguments** (highest priority)
2. **Configuration file** (`mcprobe.yaml` or `.mcprobe.yaml`)
3. **Environment variables**
4. **Default values** (lowest priority)

## Configuration File

MCProbe supports YAML configuration files for centralized configuration management. The file can be named:
- `mcprobe.yaml`
- `.mcprobe.yaml`
- `mcprobe.yml`
- `.mcprobe.yml`

### File Discovery

MCProbe automatically discovers configuration files in this order:
1. **Explicit path** via `--config` CLI option or `--mcprobe-config` pytest option
2. **Current directory** - checks for config files in order listed above
3. **No config file** - uses CLI arguments, environment variables, and defaults (silent when not found)

### File Format

```yaml
# mcprobe.yaml - MCProbe Configuration File

# Agent configuration (the system being tested)
agent:
  type: adk  # or "simple"
  factory: path/to/my_agent.py  # required for ADK agents

# Shared LLM configuration (applies to judge and synthetic user)
llm:
  provider: ollama
  model: llama3.2
  base_url: ${OLLAMA_BASE_URL:-http://localhost:11434}
  temperature: 0.0
  max_tokens: 4096

# Component-specific overrides (optional)
judge:
  provider: openai
  model: gpt-4
  api_key: ${OPENAI_API_KEY}

synthetic_user:
  provider: ollama
  model: llama3.2
  base_url: http://localhost:11434

# Orchestrator settings
orchestrator:
  max_turns: 10
  turn_timeout_seconds: 30.0
  loop_detection_threshold: 3

# Results storage settings
results:
  save: true
  dir: test-results
```

### Environment Variable Interpolation

Configuration files support environment variable interpolation with two syntaxes:

**Required variable** - Raises error if not set:
```yaml
api_key: ${OPENAI_API_KEY}
```

**Optional variable with default**:
```yaml
base_url: ${OLLAMA_BASE_URL:-http://localhost:11434}
model: ${MODEL_NAME:-llama3.2}
```

Environment variables are interpolated when the configuration file is loaded, before any validation occurs.

## AgentConfig

Configuration for the agent under test - the system being evaluated by MCProbe.

**Import Path**: `mcprobe.models.config.AgentConfig`

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `type` | `str` | No | `simple` | Agent type: "simple" (LLM-based) or "adk" (Gemini ADK with MCP) |
| `factory` | `str \| None` | No | `None` | Path to Python module with create_agent() function (required for ADK agents) |

### Agent Types

#### Simple Agent

A basic LLM-based agent that uses the synthetic_user LLM configuration. Suitable for simple conversational testing without tool calling.

**Configuration:**
```yaml
agent:
  type: simple
```

**Characteristics:**
- Uses the same LLM provider/model as the synthetic_user
- No MCP tool calling capabilities
- Suitable for basic conversation testing

#### ADK Agent

A Gemini ADK agent with full MCP tool support. Requires a factory function that creates the agent instance.

**Configuration:**
```yaml
agent:
  type: adk
  factory: my_agent_factory.py
```

**Factory Module Requirements:**

The factory module must export a `create_agent()` function that returns a configured agent:

```python
# my_agent_factory.py
from google.genai.agentic import Agent

def create_agent() -> Agent:
    """Create and return a configured Gemini ADK agent."""
    return Agent(
        model="gemini-2.0-flash-exp",
        tools=[...],  # Your MCP tools
    )
```

**Characteristics:**
- Uses Gemini internally (NOT configurable via MCProbe config file)
- Full MCP tool calling support
- Suitable for testing MCP servers with real tool interactions

**Important Notes:**
- ADK agents always use Gemini regardless of `llm:` configuration
- The `llm:`, `judge:`, and `synthetic_user:` sections configure the MCProbe evaluation components, not the ADK agent
- You can test an ADK (Gemini) agent using OpenAI for judging and Ollama for the synthetic user

### Examples

**Simple agent (uses synthetic_user LLM config):**
```yaml
agent:
  type: simple

llm:
  provider: ollama
  model: llama3.2
```

**ADK agent with mixed LLM providers:**
```yaml
# Agent under test uses Gemini (via ADK)
agent:
  type: adk
  factory: my_weather_agent.py

# Judge uses OpenAI (more accurate)
judge:
  provider: openai
  model: gpt-4o
  api_key: ${OPENAI_API_KEY}

# Synthetic user uses Ollama (cost-effective)
synthetic_user:
  provider: ollama
  model: llama3.2
  base_url: http://localhost:11434
```

**Simple agent with custom LLM:**
```yaml
agent:
  type: simple

synthetic_user:
  provider: openai
  model: gpt-4o-mini
  api_key: ${OPENAI_API_KEY}
```

### Configuration Priority

When resolving configuration values, MCProbe uses this priority order (highest to lowest):

1. **CLI arguments** - `--provider`, `--model`, `--base-url`, etc.
2. **Component-specific config** - `judge:`, `synthetic_user:` sections
3. **Shared LLM config** - `llm:` section
4. **Environment variables** - Provider-specific variables
5. **Default values** - Built-in defaults

#### Example Priority Resolution

Given this config file:
```yaml
llm:
  provider: ollama
  model: llama3.2

judge:
  model: llama3.1:8b
```

And this command:
```bash
mcprobe run scenario.yaml --model qwen2.5:7b
```

Resolution for each component:
- **Judge**: Uses `qwen2.5:7b` (CLI override wins)
- **Synthetic User**: Uses `qwen2.5:7b` (CLI override wins)

Without CLI override:
- **Judge**: Uses `llama3.1:8b` (component-specific wins)
- **Synthetic User**: Uses `llama3.2` (shared config wins)

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
| `api_key` | `SecretStr \| None` | No | `None` | API key for authentication (required for OpenAI) |
| `base_url` | `str \| None` | No | `None` | Base URL for API endpoint (optional, provider-specific) |

### Validation Rules

- `provider`: Must be non-empty string
- `model`: Must be non-empty string
- `temperature`: Must be between 0.0 and 2.0 (inclusive)
- `max_tokens`: Must be at least 1
- `api_key`: Stored as SecretStr for security (won't be logged or printed)

### Supported Providers

#### Ollama

Local LLM provider using Ollama for model inference.

**Configuration:**
- `provider`: `"ollama"`
- `model`: Any Ollama model (e.g., `"llama3.2"`, `"llama3.1:8b"`, `"qwen2.5:7b"`)
- `base_url`: Ollama API endpoint (default: `http://localhost:11434`)
- `api_key`: Not required

**Environment Variables:**
- `OLLAMA_BASE_URL`: Override default base URL

#### OpenAI

OpenAI-compatible provider supporting multiple backends:
- OpenAI API
- Azure OpenAI
- vLLM
- LiteLLM
- Ollama (OpenAI compatibility mode)
- Any other OpenAI-compatible service

**Configuration:**
- `provider`: `"openai"`
- `model`: Model identifier (e.g., `"gpt-4"`, `"gpt-3.5-turbo"`)
- `api_key`: OpenAI API key (required unless using `OPENAI_API_KEY` env var)
- `base_url`: Optional custom endpoint URL (e.g., for Azure OpenAI or self-hosted)

**Environment Variables:**
- `OPENAI_API_KEY`: API key (used if not provided in config)

**Features:**
- Tool/function calling support
- Structured JSON output via `response_format`
- Compatible with any OpenAI API-compatible endpoint

### Examples

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

# OpenAI with environment variable for API key
openai_env_config = LLMConfig(
    provider="openai",
    model="gpt-3.5-turbo",
    temperature=0.5
    # API key from OPENAI_API_KEY environment variable
)

# Azure OpenAI configuration
azure_config = LLMConfig(
    provider="openai",
    model="gpt-4",
    api_key="your-azure-key",
    base_url="https://your-resource.openai.azure.com/openai/deployments/your-deployment"
)

# vLLM self-hosted endpoint
vllm_config = LLMConfig(
    provider="openai",
    model="meta-llama/Llama-3.1-8B-Instruct",
    api_key="dummy-key",  # vLLM doesn't require real API key
    base_url="http://localhost:8000/v1"
)

# Ollama with OpenAI compatibility mode
ollama_openai_config = LLMConfig(
    provider="openai",
    model="llama3.2",
    api_key="dummy-key",  # Ollama doesn't require API key
    base_url="http://localhost:11434/v1"
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

## MCPServerConfig

Configuration for connecting to an MCP (Model Context Protocol) server. This allows MCProbe to extract tool schemas from your MCP server for tracking and analysis purposes.

**Import Path**: `mcprobe.models.config.MCPServerConfig`

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `command` | `str \| None` | No | `None` | Command to start an stdio-based MCP server (e.g., "npx @example/weather-mcp") |
| `url` | `str \| None` | No | `None` | URL for HTTP-based MCP server (e.g., "http://localhost:8080/mcp") |
| `headers` | `dict[str, str] \| None` | No | `None` | Optional HTTP headers for authentication or custom headers (only applies to HTTP connections) |

### MCP Server Connection Types

#### Stdio-based MCP Server

For MCP servers that communicate via standard input/output:

```yaml
mcp_server:
  command: "npx @modelcontextprotocol/server-weather"
```

**Examples:**
```yaml
# NPM-based server
mcp_server:
  command: "npx @example/weather-mcp"

# Python server
mcp_server:
  command: "python mcp_servers/my_server.py"

# Custom executable
mcp_server:
  command: "./bin/mcp-server"
```

#### HTTP-based MCP Server

For MCP servers accessible via HTTP:

```yaml
mcp_server:
  url: "http://localhost:8080/mcp"
```

**Examples:**
```yaml
# Local MCP server
mcp_server:
  url: "http://localhost:8080/mcp"

# Remote MCP server
mcp_server:
  url: "https://api.example.com/mcp"

# MCP server in Docker
mcp_server:
  url: "http://mcp-service:8080/mcp"

# MCP server with authentication
mcp_server:
  url: "http://localhost:8080/mcp"
  headers:
    Authorization: "Bearer ${API_TOKEN:-dev}"
    X-Custom-Header: "some-value"

# MCP server with static API key
mcp_server:
  url: "https://api.example.com/mcp"
  headers:
    X-API-Key: "${MCP_API_KEY}"

# MCP server with multiple custom headers
mcp_server:
  url: "http://internal-mcp:8080/mcp"
  headers:
    Authorization: "Bearer ${SERVICE_TOKEN:-default-token}"
    X-Environment: "production"
    X-Client-ID: "${CLIENT_ID:-mcprobe}"
```

**Headers Features:**
- **Authentication**: Supports Bearer tokens, API keys, and custom authentication schemes
- **Environment Variables**: Full support for environment variable interpolation (`${VAR}` or `${VAR:-default}`)
- **Custom Headers**: Add any custom HTTP headers required by your MCP server
- **Optional**: Only needed for servers requiring authentication or custom headers

### Use Cases

The `mcp_server` configuration enables:

1. **Prompt and Schema Tracking**: Automatically extract and track MCP tool schemas across test runs
2. **Change Detection**: Identify when tool schemas change between runs
3. **HTML Report Badges**: Display "Schema Changed" badges in reports when tools are modified
4. **Correlation Analysis**: Correlate test performance changes with schema modifications

When configured, MCProbe will:
- Connect to the MCP server at test runtime
- Extract all available tool schemas
- Store schemas with test results (hashed for change detection)
- Display change badges in HTML reports when schemas differ from previous runs

### Examples

**With stdio MCP server:**
```python
from mcprobe.models.config import MCPServerConfig, MCProbeConfig, AgentConfig, LLMConfig

config = MCProbeConfig(
    agent=AgentConfig(type="simple"),
    synthetic_user=LLMConfig(provider="ollama", model="llama3.2"),
    judge=LLMConfig(provider="ollama", model="llama3.2"),
    mcp_server=MCPServerConfig(command="npx @example/weather-mcp")
)
```

**With HTTP MCP server:**
```python
config = MCProbeConfig(
    agent=AgentConfig(type="simple"),
    synthetic_user=LLMConfig(provider="ollama", model="llama3.2"),
    judge=LLMConfig(provider="ollama", model="llama3.2"),
    mcp_server=MCPServerConfig(url="http://localhost:8080/mcp")
)
```

**In YAML configuration file:**
```yaml
# mcprobe.yaml
llm:
  provider: ollama
  model: llama3.2

# For stdio-based MCP server
mcp_server:
  command: "npx @example/weather-mcp"

# OR for HTTP-based MCP server
mcp_server:
  url: "http://localhost:8080/mcp"
```

## MCProbeConfig

Global configuration combining all MCProbe components.

**Import Path**: `mcprobe.models.config.MCProbeConfig`

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `agent` | `AgentConfig` | No | `AgentConfig(type="simple")` | Configuration for the agent under test |
| `synthetic_user` | `LLMConfig` | Yes | - | Configuration for the synthetic user LLM |
| `judge` | `LLMConfig` | Yes | - | Configuration for the judge LLM |
| `orchestrator` | `OrchestratorConfig` | No | `OrchestratorConfig()` | Orchestrator configuration |
| `mcp_server` | `MCPServerConfig \| None` | No | `None` | Optional MCP server connection for schema tracking |

### Example: Simple Agent

```python
from mcprobe.models.config import MCProbeConfig, AgentConfig, LLMConfig, OrchestratorConfig

config = MCProbeConfig(
    agent=AgentConfig(type="simple"),
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

### Example: ADK Agent with Mixed Providers

```python
from mcprobe.models.config import MCProbeConfig, AgentConfig, LLMConfig

config = MCProbeConfig(
    # Agent under test: Gemini ADK with MCP tools
    agent=AgentConfig(
        type="adk",
        factory="my_agent_factory.py"
    ),
    # Synthetic user: Cost-effective Ollama
    synthetic_user=LLMConfig(
        provider="ollama",
        model="llama3.2",
        base_url="http://localhost:11434"
    ),
    # Judge: Accurate OpenAI model
    judge=LLMConfig(
        provider="openai",
        model="gpt-4",
        api_key="sk-..."
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

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key | - | Yes (unless provided in config) |

**Note**: The OpenAI provider does not use `OPENAI_BASE_URL` environment variable. Use the `base_url` field in `LLMConfig` for custom endpoints.

### Usage

```bash
# Ollama
export OLLAMA_BASE_URL=http://localhost:11434
mcprobe run scenario.yaml --provider ollama --model llama3.2

# OpenAI
export OPENAI_API_KEY=sk-your-key-here
mcprobe run scenario.yaml --provider openai --model gpt-4

# Azure OpenAI (requires base_url in config, not via env var)
export OPENAI_API_KEY=your-azure-key
# Use config file or programmatic configuration for base_url
```

## Complete Configuration Examples

### Local Development with Ollama

```yaml
# mcprobe.yaml
llm:
  provider: ollama
  model: llama3.2
  base_url: http://localhost:11434
  temperature: 0.0

orchestrator:
  max_turns: 15
  turn_timeout_seconds: 45.0

results:
  save: true
  dir: test-results
```

### Production with OpenAI

```yaml
# mcprobe.yaml
llm:
  provider: openai
  model: gpt-4
  api_key: ${OPENAI_API_KEY}
  temperature: 0.0

results:
  save: true
  dir: ci-test-results
```

### Mixed Providers (Testing ADK agent with different LLMs)

```yaml
# mcprobe.yaml
# Agent under test: Gemini ADK with MCP tools
agent:
  type: adk
  factory: my_weather_agent.py

# Default to local Ollama for MCProbe components
llm:
  provider: ollama
  model: llama3.2
  base_url: http://localhost:11434

# Use OpenAI for judge (more accurate evaluations)
judge:
  provider: openai
  model: gpt-4
  api_key: ${OPENAI_API_KEY}

# Use local Ollama for synthetic user (cost-effective)
synthetic_user:
  provider: ollama
  model: llama3.2
```

**Key Points:**
- The ADK agent uses Gemini internally (not affected by `llm:` config)
- The judge uses OpenAI for accurate evaluation
- The synthetic user uses Ollama to minimize costs
- This demonstrates full flexibility in mixing providers

### Self-Hosted vLLM Endpoint

```yaml
# mcprobe.yaml
llm:
  provider: openai
  model: meta-llama/Llama-3.1-8B-Instruct
  api_key: dummy  # vLLM doesn't require real API key
  base_url: ${VLLM_ENDPOINT:-http://localhost:8000/v1}
  temperature: 0.0
  max_tokens: 8192
```

### Development with Environment Variables

```yaml
# mcprobe.yaml
llm:
  provider: ${LLM_PROVIDER:-ollama}
  model: ${LLM_MODEL:-llama3.2}
  base_url: ${LLM_BASE_URL:-http://localhost:11434}
  api_key: ${LLM_API_KEY}  # Optional, only if provider needs it
  temperature: 0.0

orchestrator:
  max_turns: ${MAX_TURNS:-10}
  turn_timeout_seconds: 30.0

results:
  save: ${SAVE_RESULTS:-true}
  dir: ${RESULTS_DIR:-test-results}

# Optional: Track MCP schema changes
mcp_server:
  url: ${MCP_URL:-http://localhost:8080/mcp}
```

### With MCP Server Schema Tracking

Track changes to your MCP server's tool schemas over time:

```yaml
# mcprobe.yaml
llm:
  provider: ollama
  model: llama3.2
  base_url: http://localhost:11434

# Enable schema tracking by connecting to MCP server
mcp_server:
  command: "npx @modelcontextprotocol/server-weather"

results:
  save: true
  dir: test-results
```

### With Authenticated HTTP MCP Server

For MCP servers requiring authentication:

```yaml
# mcprobe.yaml
llm:
  provider: ollama
  model: llama3.2
  base_url: http://localhost:11434

# Connect to authenticated MCP server
mcp_server:
  url: "https://api.example.com/mcp"
  headers:
    Authorization: "Bearer ${API_TOKEN:-dev-token}"
    X-API-Version: "v1"

results:
  save: true
  dir: test-results
```

When schema tracking is enabled:
- Tool schemas are extracted at test runtime
- Schemas are stored with each test result (with SHA256 hash)
- HTML reports show "Schema Changed" badges when schemas differ from previous runs
- Helps correlate test performance changes with schema modifications
- For HTTP servers, authentication headers are used to connect securely

## Using Configuration Files

### CLI Usage

**Explicit config file path**:
```bash
mcprobe run scenario.yaml --config mcprobe.yaml
```

**Auto-discovery** (checks current directory):
```bash
# MCProbe will automatically find mcprobe.yaml or .mcprobe.yaml
mcprobe run scenario.yaml
```

**Override config with CLI arguments**:
```bash
# Config file sets model to llama3.2, but CLI overrides to qwen2.5
mcprobe run scenario.yaml --config mcprobe.yaml --model qwen2.5:7b
```

### Pytest Integration

**With explicit config file**:
```bash
pytest scenarios/ --mcprobe-config mcprobe.yaml
```

**With auto-discovery**:
```bash
# Uses mcprobe.yaml in current directory if present
pytest scenarios/
```

**Override config with pytest options**:
```bash
pytest scenarios/ --mcprobe-config mcprobe.yaml --mcprobe-provider openai
```

### Common Configuration Patterns

#### Development Setup (CLI)

For local development with Ollama:

```bash
mcprobe run scenario.yaml \
  --provider ollama \
  --model llama3.2 \
  --base-url http://localhost:11434 \
  --agent-type simple
```

For development with OpenAI:

```bash
export OPENAI_API_KEY=sk-your-key
mcprobe run scenario.yaml \
  --provider openai \
  --model gpt-3.5-turbo \
  --agent-type simple
```

#### Development Setup (Config File)

Create `mcprobe.yaml`:
```yaml
llm:
  provider: ollama
  model: llama3.2
  base_url: http://localhost:11434
```

Then run:
```bash
mcprobe run scenario.yaml
```

#### CI/CD Setup

For automated testing with config file:

```yaml
# mcprobe.yaml
llm:
  provider: ${CI_LLM_PROVIDER:-ollama}
  model: ${CI_LLM_MODEL:-llama3.2}
  base_url: ${CI_LLM_BASE_URL:-http://ollama-service:11434}
  api_key: ${CI_LLM_API_KEY}

results:
  save: true
  dir: ${CI_RESULTS_DIR:-test-results}
```

For CI/CD with OpenAI:

```bash
export OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }}
mcprobe run scenarios/ --config mcprobe.yaml
```

### Self-Hosted LLM Endpoints

For vLLM or other OpenAI-compatible endpoints:

```python
from mcprobe.models.config import LLMConfig, MCProbeConfig

config = MCProbeConfig(
    agent=LLMConfig(
        provider="openai",
        model="meta-llama/Llama-3.1-8B-Instruct",
        api_key="dummy",
        base_url="http://vllm-server:8000/v1"
    ),
    synthetic_user=LLMConfig(
        provider="openai",
        model="meta-llama/Llama-3.1-8B-Instruct",
        api_key="dummy",
        base_url="http://vllm-server:8000/v1"
    ),
    judge=LLMConfig(
        provider="openai",
        model="meta-llama/Llama-3.1-8B-Instruct",
        api_key="dummy",
        base_url="http://vllm-server:8000/v1"
    )
)
```

### ADK Agent Setup

For testing Gemini ADK agents with MCP tools:

**Using configuration file (recommended):**
```yaml
# mcprobe.yaml
agent:
  type: adk
  factory: my_agent_factory.py

llm:
  provider: ollama
  model: llama3.2
  base_url: http://localhost:11434
```

```bash
mcprobe run scenario.yaml
```

**Using CLI arguments:**
```bash
mcprobe run scenario.yaml \
  --agent-type adk \
  --agent-factory my_agent_factory.py \
  --model llama3.2 \
  --base-url http://localhost:11434
```

**Important Notes:**
- The `--model` and `--base-url` configure the judge and synthetic user, NOT the ADK agent
- ADK agents always use Gemini internally
- You can mix providers: test a Gemini agent with OpenAI judge and Ollama synthetic user

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
